# -*- coding: utf-8 -*-
"""Moteur de patch de fichiers ECU piloté par des définitions JSON.

Fonctionnalités :
- chargement/validation de définitions (dossier ``definitions/``) ;
- patchs par signatures hexadécimales avant/après (wildcards ``??``) ;
- **DTC Remover** : localisation des tables de codes défauts (P-codes) dans
  le dump, affichage de l'adresse de chaque code et mise à 0x00 de son octet
  d'activation (switch) ;
- sauvegarde horodatée ``.bak`` **systématique avant toute modification** ;
- journal des différences (offset | original | modifié) et évaluation des
  checksums avec avertissement avant export.
"""
from __future__ import annotations

import json
import logging
import re
import shutil
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from core.checksum import ChecksumReport, evaluate_region, full_file_report
from core.ecu_analyzer import EcuAnalyzer, EcuIdentity, find_pattern, vin_check_digit_valid

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1

# Codes DTC — encodage SAE J2012 (2 octets) :
#   bits 15-14 : système (00=P, 01=C, 10=B, 11=U)
#   bits 13-12 : 1er chiffre (0-3)
#   bits 11-8  : 2e chiffre (0-9)
#   bits 7-0   : 3e et 4e chiffres (hex)
# Ex. P0401 = 0x0401, P2002 = 0x2002, U0100 = 0xC100.
DTC_SYSTEM_LETTERS = "PCBU"

# Valeurs plausibles d'un octet d'activation (switch) pour le scan brut
PLAUSIBLE_SWITCH_VALUES = frozenset(
    {0x00, 0x01, 0x02, 0x03, 0x04, 0x08, 0x0A, 0x10, 0x20, 0x2F, 0x40, 0x80, 0xFF}
)
DTC_STATUS_BITS = {
    0x01: "testFailed",
    0x02: "testFailedThisOperationCycle",
    0x04: "pendingDTC",
    0x08: "confirmedDTC",
    0x10: "testNotCompletedSinceLastClear",
    0x20: "testFailedSinceLastClear",
    0x40: "testNotCompletedThisOperationCycle",
    0x80: "warningIndicatorRequested",
}


class PatchError(Exception):
    """Erreur applicative du moteur de patch (motif introuvable, etc.)."""


class DefinitionError(ValueError):
    """Fichier de définition JSON invalide."""


# ==========================================================================
# Modèle de définition
# ==========================================================================
@dataclass
class PatternPatch:
    """Patch par signature : octets ``find`` remplacés par ``replace``."""

    name: str
    find: str
    replace: str
    description: str = ""


@dataclass
class Solution:
    """Solution appliquable (EGR Off, DPF Off, AdBlue Off, ...)."""

    id: str
    label: str
    category: str
    description: str
    patches: List[PatternPatch] = field(default_factory=list)


@dataclass
class DtcTable:
    """Description d'une table de codes défauts dans le dump."""

    name: str
    entry_size: int = 4
    code_offset: int = 0
    switch_offset: int = 3
    byte_order: str = "big"
    locator: Optional[str] = None
    min_entries: int = 8


@dataclass
class ChecksumRegionDef:
    """Région de checksum déclarée dans la définition."""

    algorithm: str
    start: int
    length: Optional[int]
    storage_offset: Optional[int]
    endianness: str = "little"


@dataclass
class EcuDefinition:
    """Définition complète d'un calculateur (fichier JSON)."""

    definition_id: str
    name: str
    manufacturer: str
    ecu_families: List[str]
    id_patterns: List[str]
    min_size: int
    max_size: int
    solutions: List[Solution] = field(default_factory=list)
    dtc_tables: List[DtcTable] = field(default_factory=list)
    checksum_regions: List[ChecksumRegionDef] = field(default_factory=list)
    checksum_notes: str = ""
    notes: str = ""


def definitions_dir() -> Path:
    """Dossier des définitions (compatible PyInstaller --onefile).

    En exécutable figé, on privilégie un dossier ``definitions/`` à côté de
    l'exe : il reste inscriptible, ce qui permet d'ajouter des définitions
    sans recompiler.
    """
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).resolve().parent
    else:
        base = Path(__file__).resolve().parent.parent
    return base / "definitions"


def parse_definition(payload: dict) -> EcuDefinition:
    """Valide et convertit un dictionnaire JSON en ``EcuDefinition``."""
    if not isinstance(payload, dict):
        raise DefinitionError("La définition doit être un objet JSON.")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise DefinitionError(
            f"schema_version non supportée : {payload.get('schema_version')!r} (attendu {SCHEMA_VERSION})."
        )
    for required in ("definition_id", "name", "manufacturer"):
        if not payload.get(required):
            raise DefinitionError(f"Champ obligatoire manquant : '{required}'.")

    match = payload.get("match", {}) or {}
    solutions: List[Solution] = []
    for entry in payload.get("solutions", []) or []:
        patches = [
            PatternPatch(
                name=p.get("name", "patch"),
                find=_require_pattern(p, "find"),
                replace=_require_pattern(p, "replace"),
                description=p.get("description", ""),
            )
            for p in entry.get("patches", []) or []
        ]
        if not patches:
            raise DefinitionError(f"Solution '{entry.get('id')}' : aucune patch définie.")
        solutions.append(
            Solution(
                id=str(entry["id"]),
                label=str(entry.get("label", entry["id"])),
                category=str(entry.get("category", "divers")),
                description=str(entry.get("description", "")),
                patches=patches,
            )
        )

    dtc_tables: List[DtcTable] = []
    for entry in payload.get("dtc_tables", []) or []:
        byte_order = str(entry.get("byte_order", "big")).lower()
        if byte_order not in ("big", "little"):
            raise DefinitionError(f"byte_order invalide : {byte_order!r} (big|little).")
        dtc_tables.append(
            DtcTable(
                name=str(entry.get("name", "Table DTC")),
                entry_size=int(entry.get("entry_size", 4)),
                code_offset=int(entry.get("code_offset", 0)),
                switch_offset=int(entry.get("switch_offset", 3)),
                byte_order=byte_order,
                locator=entry.get("locator"),
                min_entries=int(entry.get("min_entries", 8)),
            )
        )

    checksum_regions: List[ChecksumRegionDef] = []
    checksum = payload.get("checksum", {}) or {}
    for entry in checksum.get("regions", []) or []:
        checksum_regions.append(
            ChecksumRegionDef(
                algorithm=str(entry.get("algorithm", "crc32")),
                start=int(entry.get("start", 0)),
                length=entry.get("length"),
                storage_offset=entry.get("storage_offset"),
                endianness=str(entry.get("endianness", "little")).lower(),
            )
        )

    return EcuDefinition(
        definition_id=str(payload["definition_id"]),
        name=str(payload["name"]),
        manufacturer=str(payload["manufacturer"]),
        ecu_families=[str(f) for f in payload.get("ecu_families", []) or []],
        id_patterns=[str(p) for p in match.get("id_patterns", []) or []],
        min_size=int(match.get("min_size", 0)),
        max_size=int(match.get("max_size", 0)) or (1 << 32),
        solutions=solutions,
        dtc_tables=dtc_tables,
        checksum_regions=checksum_regions,
        checksum_notes=str(checksum.get("notes", "")),
        notes=str(payload.get("notes", "")),
    )


def _require_pattern(patch: dict, key: str) -> str:
    value = patch.get(key)
    if not value or not isinstance(value, str):
        raise DefinitionError(f"Patch '{patch.get('name', '?')}' : champ '{key}' manquant.")
    return value


def load_definition(path: Path) -> EcuDefinition:
    """Charge et valide un fichier de définition JSON."""
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DefinitionError(f"JSON invalide ({path}) : {exc}") from exc
    return parse_definition(payload)


def save_definition(definition: EcuDefinition, path: Path) -> None:
    """Sérialise une définition vers un fichier JSON lisible."""
    payload = {
        "schema_version": SCHEMA_VERSION,
        "definition_id": definition.definition_id,
        "name": definition.name,
        "manufacturer": definition.manufacturer,
        "ecu_families": definition.ecu_families,
        "match": {
            "id_patterns": definition.id_patterns,
            "min_size": definition.min_size,
            "max_size": definition.max_size,
        },
        "checksum": {
            "notes": definition.checksum_notes,
            "regions": [
                {
                    "algorithm": r.algorithm,
                    "start": r.start,
                    "length": r.length,
                    "storage_offset": r.storage_offset,
                    "endianness": r.endianness,
                }
                for r in definition.checksum_regions
            ],
        },
        "solutions": [
            {
                "id": s.id,
                "label": s.label,
                "category": s.category,
                "description": s.description,
                "patches": [
                    {"name": p.name, "find": p.find, "replace": p.replace, "description": p.description}
                    for p in s.patches
                ],
            }
            for s in definition.solutions
        ],
        "dtc_tables": [
            {
                "name": t.name,
                "entry_size": t.entry_size,
                "code_offset": t.code_offset,
                "switch_offset": t.switch_offset,
                "byte_order": t.byte_order,
                "locator": t.locator,
                "min_entries": t.min_entries,
            }
            for t in definition.dtc_tables
        ],
        "notes": definition.notes,
    }
    Path(path).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def list_definitions(directory: Optional[Path] = None) -> List[Path]:
    """Liste les fichiers de définitions JSON disponibles."""
    directory = directory or definitions_dir()
    if not directory.exists():
        return []
    return sorted(directory.glob("*.json"))


# ==========================================================================
# Résultats de patch
# ==========================================================================
@dataclass
class DiffEntry:
    """Un octet modifié (comparateur hexadécimal)."""

    offset: int
    original: int
    patched: int

    @property
    def changed(self) -> bool:
        return self.original != self.patched


@dataclass
class DtcEntry:
    """Un code défaut localisé dans le dump."""

    table_name: str
    entry_offset: int
    code: int
    switch_offset: int
    switch_value: int
    byte_order: str = "big"

    @property
    def code_str(self) -> str:
        letter = DTC_SYSTEM_LETTERS[(self.code >> 14) & 0x03]
        return f"{letter}{self.code & 0x3FFF:04X}"

    @property
    def active(self) -> bool:
        return self.switch_value != 0x00

    def status_text(self) -> str:
        return "ACTIF" if self.active else "désactivé"


# ==========================================================================
# Session de patch
# ==========================================================================
class PatchSession:
    """État d'une session d'édition binaire (fichier, diffs, définition)."""

    def __init__(self) -> None:
        self.file_path: Optional[Path] = None
        self.original: bytes = b""
        self.data: bytearray = bytearray()
        self.backup_path: Optional[Path] = None
        self.definition: Optional[EcuDefinition] = None
        self.diffs: List[DiffEntry] = []
        self.checksum_reports: List[ChecksumReport] = []
        self._analyzer = EcuAnalyzer()
        self.identity: Optional[EcuIdentity] = None

    # -- état ------------------------------------------------------------------
    @property
    def is_loaded(self) -> bool:
        return bool(self.data)

    # -- chargement / sauvegarde -------------------------------------------------
    def load(self, path: Path) -> EcuIdentity:
        """Charge un dump et crée **immédiatement** une sauvegarde .bak horodatée."""
        path = Path(path)
        raw = path.read_bytes()
        if not raw:
            raise PatchError(f"Fichier vide : {path}")
        self.file_path = path
        self.original = raw
        self.data = bytearray(raw)
        self.diffs = []
        self.checksum_reports = []
        self.backup_path = self._create_backup(path, raw)
        self.identity = self._analyzer.analyze(raw, str(path))
        logger.info(
            "Fichier chargé : %s (%d octets) — sauvegarde : %s",
            path,
            len(raw),
            self.backup_path,
        )
        return self.identity

    @staticmethod
    def _create_backup(path: Path, raw: bytes) -> Path:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup = path.with_name(f"{path.stem}_{timestamp}.bak")
        shutil.copy2(path, backup)
        logger.info("Sauvegarde créée : %s", backup)
        return backup

    def reload_original(self) -> None:
        """Annule toutes les modifications de la session (retour au fichier tel que chargé)."""
        if not self.is_loaded:
            raise PatchError("Aucun fichier chargé.")
        self.data = bytearray(self.original)
        self.diffs = []
        logger.info("Retour au fichier d'origine : modifications de session annulées.")

    def restore_backup(self, path: Path) -> EcuIdentity:
        """Restaure une sauvegarde ``.bak`` : la charge comme nouveau fichier courant.

        Une nouvelle sauvegarde du fichier courant est créée au passage, ce qui
        rend l'opération réversible à tout moment.
        """
        return self.load(Path(path))

    # -- réemploi d'ECU (VIN) -------------------------------------------------
    def find_vins(self) -> List[Tuple[int, str]]:
        """Détecte tous les VIN potentiels du dump (offset, VIN)."""
        if not self.is_loaded:
            raise PatchError("Aucun fichier chargé.")
        return self._analyzer.find_vins(bytes(self.data))

    def replace_vin(self, new_vin: str, occurrences: Optional[List[int]] = None) -> List[DiffEntry]:
        """Remplace le VIN du dump (réemploi d'un calculateur d'occasion).

        Par défaut, **toutes** les occurrences détectées sont remplacées de
        façon synchronisée (flash + zones d'appairage) afin de conserver la
        cohérence interne du fichier.
        """
        if not self.is_loaded:
            raise PatchError("Aucun fichier chargé.")
        new_vin = new_vin.strip().upper()
        if len(new_vin) != 17:
            raise PatchError(f"Le VIN doit contenir exactement 17 caractères (reçu : {len(new_vin)}).")
        if not re.fullmatch(r"[A-HJ-NPR-Z0-9]{17}", new_vin):
            raise PatchError("VIN invalide : caractères autorisés = chiffres et lettres sauf I, O, Q.")
        check = vin_check_digit_valid(new_vin)
        if check is False:
            logger.warning("VIN saisi : caractère de contrôle ISO 3779 (position 9) invalide — vérifiez la saisie.")
        vins = self.find_vins()
        if not vins:
            raise PatchError("Aucun VIN détecté dans le dump : remplacement impossible.")
        targets = vins if occurrences is None else [v for v in vins if v[0] in occurrences]
        if not targets:
            raise PatchError("Aucune des occurrences sélectionnées n'existe dans le dump.")
        diffs: List[DiffEntry] = []
        for offset, old_vin in targets:
            new_bytes = new_vin.encode("ascii")
            for index in range(17):
                position = offset + index
                if self.data[position] != new_bytes[index]:
                    entry = DiffEntry(offset=position, original=self.data[position], patched=new_bytes[index])
                    self.data[position] = new_bytes[index]
                    diffs.append(entry)
                    self.diffs.append(entry)
            logger.info("VIN @ 0x%06X : %s -> %s", offset, old_vin, new_vin)
        logger.info("VIN remplacé sur %d occurrence(s), %d octet(s) modifié(s).", len(targets), len(diffs))
        return diffs

    def match_score(self, definition: EcuDefinition) -> int:
        """Score de compatibilité entre le dump chargé et une définition."""
        if not self.is_loaded:
            return 0
        score = 0
        if definition.min_size <= len(self.data) <= definition.max_size:
            score += 2
        upper = bytes(self.data).upper()
        for pattern in definition.id_patterns:
            if pattern.upper().encode("ascii") in upper:
                score += 3
        if self.identity is not None and self.identity.detected_family in definition.ecu_families:
            score += 4
        return score

    def best_definition(self, directory: Optional[Path] = None) -> Optional[EcuDefinition]:
        """Retourne la définition la plus compatible avec le dump chargé."""
        best: Optional[EcuDefinition] = None
        best_score = 0
        for path in list_definitions(directory):
            try:
                definition = load_definition(path)
            except DefinitionError as exc:
                logger.warning("Définition ignorée (%s) : %s", path.name, exc)
                continue
            score = self.match_score(definition)
            if score > best_score:
                best, best_score = definition, score
        return best

    # -- patches ------------------------------------------------------------------
    def apply_pattern_patch(self, patch: PatternPatch) -> List[DiffEntry]:
        """Applique un patch par signature et retourne les différences créées."""
        if not self.is_loaded:
            raise PatchError("Aucun fichier chargé.")
        occurrences = find_pattern(bytes(self.data), patch.find)
        if not occurrences:
            raise PatchError(
                f"Signature introuvable pour '{patch.name}' : {patch.find}"
            )
        find_tokens = patch.find.replace(",", " ").split()
        replace_tokens = patch.replace.replace(",", " ").split()
        if len(find_tokens) != len(replace_tokens):
            raise PatchError(
                f"Patch '{patch.name}' : longueurs find/replace différentes "
                f"({len(find_tokens)} vs {len(replace_tokens)})."
            )
        diffs: List[DiffEntry] = []
        for offset in occurrences:
            for index, token in enumerate(replace_tokens):
                if token in ("??", "?", "**"):
                    continue  # wildcard : l'octet d'origine est conservé
                new_value = int(token, 16)
                position = offset + index
                original = self.data[position]
                if original == new_value:
                    continue
                self.data[position] = new_value
                entry = DiffEntry(offset=position, original=original, patched=new_value)
                diffs.append(entry)
                self.diffs.append(entry)
        if not diffs:
            logger.info("Patch '%s' : signature trouvée mais octets déjà identiques (aucun changement).", patch.name)
        else:
            logger.info(
                "Patch '%s' appliqué : %d occurrence(s), %d octet(s) modifié(s).",
                patch.name,
                len(occurrences),
                len(diffs),
            )
        return diffs

    def apply_solution(self, solution: Solution) -> Tuple[int, List[str]]:
        """Applique toutes les patches d'une solution. Retourne (nb diffs, erreurs)."""
        diffs = 0
        errors: List[str] = []
        for patch in solution.patches:
            try:
                diffs += len(self.apply_pattern_patch(patch))
            except PatchError as exc:
                errors.append(str(exc))
                logger.warning(str(exc))
        return diffs, errors

    # -- DTC ------------------------------------------------------------------------
    def scan_dtcs(self) -> List[DtcEntry]:
        """Localise les tables DTC et retourne la liste des codes trouvés."""
        if not self.is_loaded:
            raise PatchError("Aucun fichier chargé.")
        results: List[DtcEntry] = []
        seen_offsets: set = set()
        if self.definition and self.definition.dtc_tables:
            for table in self.definition.dtc_tables:
                for entry in self._scan_dtc_table(table):
                    if entry.entry_offset not in seen_offsets:
                        seen_offsets.add(entry.entry_offset)
                        results.append(entry)
        if not results:
            for entry in self._raw_dtc_scan():
                if entry.entry_offset not in seen_offsets:
                    seen_offsets.add(entry.entry_offset)
                    results.append(entry)
        results.sort(key=lambda e: e.entry_offset)
        logger.info("Scan DTC : %d code(s) trouvé(s).", len(results))
        return results

    def _scan_dtc_table(self, table: DtcTable) -> List[DtcEntry]:
        entries: List[DtcEntry] = []
        starts: List[int] = [0]
        if table.locator:
            starts = find_pattern(bytes(self.data), table.locator)
            if not starts:
                logger.warning("Table DTC '%s' : localisateur introuvable (%s).", table.name, table.locator)
                return entries
        for start in starts:
            offset = start
            count = 0
            while count < 512 and offset + table.entry_size <= len(self.data):
                entry = self._read_dtc_entry(table, offset)
                if entry is None:
                    break
                entries.append(entry)
                offset += table.entry_size
                count += 1
            if count < table.min_entries and table.locator:
                entries = entries[: max(0, len(entries) - count)]
        return entries

    def _raw_dtc_scan(self) -> List[DtcEntry]:
        """Scan brut : recherche des séquences d'entrées DTC plausibles."""
        results: List[DtcEntry] = []
        for byte_order in ("big", "little"):
            table = DtcTable(name=f"Scan brut ({byte_order})", byte_order=byte_order)
            results = self._scan_runs(table)
            if results:
                break
        return results

    def _scan_runs(self, table: DtcTable) -> List[DtcEntry]:
        entries: List[DtcEntry] = []
        entry_size = table.entry_size
        limit = len(self.data) - entry_size
        index = 0
        while index <= limit:
            if self._valid_dtc_entry(index, table):
                run: List[int] = []
                cursor = index
                while cursor <= limit and self._valid_dtc_entry(cursor, table):
                    run.append(cursor)
                    cursor += entry_size
                if len(run) >= table.min_entries:
                    for offset in run:
                        entry = self._read_dtc_entry(table, offset)
                        if entry is not None:
                            entries.append(entry)
                    index = cursor
                    continue
                index += 1
            else:
                index += 1
        return entries

    def _valid_dtc_code(self, offset: int, byte_order: str, strict: bool = False) -> bool:
        if offset + 2 > len(self.data):
            return False
        code = int.from_bytes(self.data[offset : offset + 2], byteorder=byte_order)
        if code == 0:
            return False
        if (code >> 8) & 0x0F > 9:  # 2e chiffre d'un DTC : 0-9
            return False
        return True

    def _valid_dtc_entry(self, offset: int, table: DtcTable) -> bool:
        """Validation d'une entrée complète : code valide + octet switch plausible."""
        if not self._valid_dtc_code(offset + table.code_offset, table.byte_order):
            return False
        switch_offset = offset + table.switch_offset
        if switch_offset >= len(self.data):
            return False
        return self.data[switch_offset] in PLAUSIBLE_SWITCH_VALUES

    def _read_dtc_entry(self, table: DtcTable, offset: int) -> Optional[DtcEntry]:
        code_offset = offset + table.code_offset
        switch_offset = offset + table.switch_offset
        if code_offset + 2 > len(self.data) or switch_offset >= len(self.data):
            return None
        if not self._valid_dtc_code(code_offset, table.byte_order):
            return None
        code = int.from_bytes(self.data[code_offset : code_offset + 2], byteorder=table.byte_order)
        return DtcEntry(
            table_name=table.name,
            entry_offset=offset,
            code=code,
            switch_offset=switch_offset,
            switch_value=self.data[switch_offset],
            byte_order=table.byte_order,
        )

    def disable_dtc_entries(self, entries: List[DtcEntry]) -> List[DiffEntry]:
        """DTC Remover : met l'octet d'activation (switch) de chaque code à 0x00."""
        if not self.is_loaded:
            raise PatchError("Aucun fichier chargé.")
        diffs: List[DiffEntry] = []
        for entry in entries:
            if not entry.active:
                continue
            original = self.data[entry.switch_offset]
            self.data[entry.switch_offset] = 0x00
            diff = DiffEntry(offset=entry.switch_offset, original=original, patched=0x00)
            diffs.append(diff)
            self.diffs.append(diff)
            logger.info(
                "DTC %s désactivé : switch @ 0x%06X : 0x%02X -> 0x00",
                entry.code_str,
                entry.switch_offset,
                original,
            )
        return diffs

    # -- checksums / export -----------------------------------------------------------
    def evaluate_checksums(self) -> List[ChecksumReport]:
        """Évalue les checksums (régions de la définition, sinon fichier entier)."""
        if not self.is_loaded:
            return []
        reports: List[ChecksumReport] = []
        data = bytes(self.data)
        if self.definition and self.definition.checksum_regions:
            for region in self.definition.checksum_regions:
                try:
                    reports.append(
                        evaluate_region(
                            data,
                            region.algorithm,
                            region.start,
                            region.length,
                            region.storage_offset,
                            region.endianness,
                        )
                    )
                except (ValueError, KeyError) as exc:
                    logger.warning("Région de checksum ignorée : %s", exc)
        else:
            reports = full_file_report(data)
        self.checksum_reports = reports
        return reports

    def checksum_warnings(self) -> List[str]:
        """Avertissements checksum à présenter avant export."""
        warnings = []
        for report in self.evaluate_checksums():
            if report.status != "ok":
                warnings.append(report.summary())
        if self.definition and self.definition.checksum_notes:
            warnings.append(f"[CHECKSUM] {self.definition.checksum_notes}")
        return warnings

    def export(self, path: Path) -> Tuple[Path, List[str]]:
        """Exporte le .bin patché (avec sauvegarde du fichier existant) + warnings checksum."""
        if not self.is_loaded:
            raise PatchError("Aucun fichier chargé.")
        path = Path(path)
        if path.exists():
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            backup = path.with_name(f"{path.stem}_{timestamp}.bak")
            shutil.copy2(path, backup)
            logger.info("Export : fichier existant sauvegardé sous %s", backup)
        path.write_bytes(bytes(self.data))
        logger.info("Export écrit : %s (%d octets)", path, len(self.data))
        warnings = self.checksum_warnings()
        for warning in warnings:
            logger.warning(warning)
        return path, warnings

    def diff_map(self) -> Dict[int, DiffEntry]:
        """Dernière valeur modifiée par offset (pour le comparateur)."""
        result: Dict[int, DiffEntry] = {}
        for entry in self.diffs:
            result[entry.offset] = entry
        return result
