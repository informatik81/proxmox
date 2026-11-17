# -*- coding: utf-8 -*-
"""Analyse de fichiers binaires de calculateurs (ECU .bin / .ori).

Fournit :
- la détection de la famille d'ECU (Bosch EDC17, Siemens/Continental SID807 /
  PCR2.1, Delphi DCM6.2, Marelli MJ8/MJ9) par chaînes d'identification ASCII,
  regex de numéros de pièce et taille de fichier ;
- l'extraction de métadonnées (taille, entropie de Shannon, SHA-256, chaînes) ;
- un moteur de recherche de motifs hexadécimaux avec wildcards ``??``.
"""
from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

__all__ = [
    "EcuSignature",
    "EcuIdentity",
    "KNOWN_SIGNATURES",
    "EcuAnalyzer",
    "find_pattern",
    "pattern_to_regex",
]


# --------------------------------------------------------------------------
# Signatures connues
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class EcuSignature:
    """Signature d'identification d'une famille de calculateurs."""

    family: str
    manufacturer: str
    id_patterns: Tuple[str, ...]
    part_number_regex: Optional[str]
    file_sizes: Tuple[int, ...]
    notes: str = ""


KNOWN_SIGNATURES: Tuple[EcuSignature, ...] = (
    EcuSignature(
        family="EDC17C10",
        manufacturer="Bosch",
        id_patterns=("EDC17C10", "EDC17_C10"),
        part_number_regex=r"0281[0-9]{6}",
        file_sizes=(2097152,),
        notes="Diesel VAG 1.6/2.0 TDI — flash 2 Mo.",
    ),
    EcuSignature(
        family="EDC17C60",
        manufacturer="Bosch",
        id_patterns=("EDC17C60",),
        part_number_regex=r"0281[0-9]{6}",
        file_sizes=(2097152,),
        notes="Diesel PSA 1.6 HDi / Ford — flash 2 Mo.",
    ),
    EcuSignature(
        family="EDC17CP44",
        manufacturer="Bosch",
        id_patterns=("EDC17CP44",),
        part_number_regex=r"0281[0-9]{6}",
        file_sizes=(4194304,),
        notes="Diesel Mercedes/VAG — flash 4 Mo.",
    ),
    EcuSignature(
        family="SID807",
        manufacturer="Siemens/Continental",
        id_patterns=("SID807", "SID807EVO"),
        part_number_regex=r"S1[0-9]{8}",
        file_sizes=(2097152,),
        notes="Diesel PSA 1.6 HDi 8v/16v — flash 2 Mo.",
    ),
    EcuSignature(
        family="PCR2.1",
        manufacturer="Siemens/Continental",
        id_patterns=("PCR2.1", "PCR21"),
        part_number_regex=r"S1[0-9]{8}",
        file_sizes=(2097152,),
        notes="Diesel VAG 1.6/2.0 TDI CR — flash 2 Mo.",
    ),
    EcuSignature(
        family="DCM6.2",
        manufacturer="Delphi",
        id_patterns=("DCM6.2", "DCM62", "DCM3.5"),
        part_number_regex=r"0281[0-9]{6}",
        file_sizes=(4194304,),
        notes="Diesel Renault/Nissan/Opel — flash 4 Mo.",
    ),
    EcuSignature(
        family="MJD8F3",
        manufacturer="Marelli",
        id_patterns=("MJD8F3", "MJ8F3", "MJD8"),
        part_number_regex=None,
        file_sizes=(2097152,),
        notes="Diesel Fiat/Opel 1.3 Multijet — flash 2 Mo.",
    ),
    EcuSignature(
        family="MJ9",
        manufacturer="Marelli",
        id_patterns=("MJ9", "MJD9"),
        part_number_regex=None,
        file_sizes=(1048576, 2097152),
        notes="Diesel Fiat/Opel Multijet — flash 1-2 Mo.",
    ),
)

_BOSCH_PART_RE = re.compile(rb"0281[0-9]{6}")
_CONTINENTAL_PART_RE = re.compile(rb"S1[0-9]{8}")
_ASCII_STRING_RE = re.compile(rb"[\x20-\x7E]{6,}")


# --------------------------------------------------------------------------
# Résultat d'analyse
# --------------------------------------------------------------------------
@dataclass
class EcuIdentity:
    """Fiche d'identité d'un fichier ECU analysé."""

    path: Optional[str] = None
    size: int = 0
    entropy: float = 0.0
    sha256: str = ""
    detected_family: str = "Inconnu"
    manufacturer: str = "Inconnu"
    confidence: str = "Aucune"
    matched_by: str = ""
    part_numbers: List[str] = field(default_factory=list)
    id_strings: List[Tuple[int, str]] = field(default_factory=list)
    notes: str = ""

    def summary_lines(self) -> List[Tuple[str, str]]:
        """Paires (champ, valeur) prêtes à afficher dans l'UI."""
        return [
            ("Fichier", str(self.path or "-")),
            ("Taille", f"{self.size} octets (0x{self.size:X})"),
            ("Famille détectée", self.detected_family),
            ("Constructeur ECU", self.manufacturer),
            ("Confiance", self.confidence),
            ("Entropie", f"{self.entropy:.3f} bits/octet"),
            ("N° de pièce", ", ".join(self.part_numbers) if self.part_numbers else "-"),
            ("SHA-256", self.sha256 or "-"),
            ("Notes", self.notes or "-"),
        ]


# --------------------------------------------------------------------------
# Moteur de motifs hexadécimaux avec wildcards
# --------------------------------------------------------------------------
def pattern_to_regex(pattern: str) -> bytes:
    """Convertit un motif hexadécimal (ex. ``48 8B ?? ?? 00 00``) en regex bytes.

    Les jetons acceptés sont des octets hexadécimaux (``4A``) et les wildcards
    ``??`` (ou ``?``). Les séparateurs acceptés sont l'espace et la virgule.
    """
    tokens = pattern.replace(",", " ").split()
    if not tokens:
        raise ValueError("Motif hexadécimal vide.")
    parts = []
    for token in tokens:
        if token in ("??", "?", "**"):
            parts.append(b".")
            continue
        if len(token) != 2:
            raise ValueError(f"Jeton hexadécimal invalide : '{token}'")
        try:
            parts.append(re.escape(bytes([int(token, 16)])))
        except ValueError as exc:
            raise ValueError(f"Jeton hexadécimal invalide : '{token}'") from exc
    return b"".join(parts)


def find_pattern(data: bytes, pattern: str) -> List[int]:
    """Recherche toutes les occurrences d'un motif hexadécimal (avec wildcards).

    Retourne la liste des offsets (index du premier octet du motif).
    """
    regex = pattern_to_regex(pattern)
    return [match.start() for match in re.finditer(regex, data, re.DOTALL)]


# --------------------------------------------------------------------------
# Analyseur
# --------------------------------------------------------------------------
class EcuAnalyzer:
    """Analyseur de dumps ECU : détection de famille et métadonnées."""

    def __init__(self, signatures: Sequence[EcuSignature] = KNOWN_SIGNATURES) -> None:
        self._signatures = tuple(signatures)

    # -- métadonnées -------------------------------------------------------
    @staticmethod
    def shannon_entropy(data: bytes) -> float:
        """Entropie de Shannon en bits/octet (0 = constant, 8 = aléatoire)."""
        if not data:
            return 0.0
        counts = [0] * 256
        for byte in data:
            counts[byte] += 1
        total = float(len(data))
        entropy = 0.0
        for count in counts:
            if count:
                probability = count / total
                entropy -= probability * math.log2(probability)
        return entropy

    @staticmethod
    def extract_strings(data: bytes, min_length: int = 6, limit: int = 400) -> List[Tuple[int, str]]:
        """Extrait les chaînes ASCII imprimables (offset, texte)."""
        results: List[Tuple[int, str]] = []
        for match in _ASCII_STRING_RE.finditer(data):
            text = match.group(0).decode("ascii", errors="replace")
            if len(text) >= min_length:
                results.append((match.start(), text))
                if len(results) >= limit:
                    break
        return results

    @staticmethod
    def extract_part_numbers(data: bytes) -> List[str]:
        """Recherche les numéros de pièce Bosch (02810xxxxxx) / Continental (S1xxxxxxxx)."""
        found: List[str] = []
        for regex in (_BOSCH_PART_RE, _CONTINENTAL_PART_RE):
            for match in regex.finditer(data):
                value = match.group(0).decode("ascii", errors="replace")
                if value not in found:
                    found.append(value)
        return found

    # -- détection ---------------------------------------------------------
    def analyze(self, data: bytes, path: Optional[str] = None) -> EcuIdentity:
        """Analyse complète d'un dump : famille, métadonnées, chaînes."""
        identity = EcuIdentity(
            path=path,
            size=len(data),
            entropy=self.shannon_entropy(data),
            sha256=hashlib.sha256(data).hexdigest() if data else "",
            part_numbers=self.extract_part_numbers(data),
            id_strings=self.extract_strings(data),
        )
        best_score = 0
        best: Optional[EcuSignature] = None
        reasons: List[str] = []
        upper_data = data.upper()
        for signature in self._signatures:
            score = 0
            reason: List[str] = []
            if identity.size in signature.file_sizes:
                score += 2
                reason.append(f"taille {identity.size} octets")
            for pattern in signature.id_patterns:
                if pattern.upper().encode("ascii") in upper_data:
                    score += 3
                    reason.append(f"chaîne '{pattern}'")
            if signature.part_number_regex and re.search(signature.part_number_regex.encode(), data):
                score += 1
                reason.append("numéro de pièce")
            if score > best_score:
                best_score = score
                best = signature
                reasons = reason
        if best is not None and best_score >= 3:
            identity.detected_family = best.family
            identity.manufacturer = best.manufacturer
            identity.notes = best.notes
            identity.matched_by = ", ".join(reasons)
            identity.confidence = "Élevée" if best_score >= 5 else "Moyenne"
        else:
            identity.matched_by = "aucune signature fiable"
            identity.confidence = "Aucune"
        return identity
