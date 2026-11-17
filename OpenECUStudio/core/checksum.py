# -*- coding: utf-8 -*-
"""Sommes de contrôle (checksums) pour fichiers binaires de calculateurs.

Architecture modulaire : chaque algorithme est une classe dérivée de
``ChecksumAlgorithm`` et enregistrée dans ``CHECKSUM_ALGORITHMS``. Les
algorithmes propriétaires spécifiques à une famille d'ECU (Bosch EDC17,
Siemens/Continental SID807, Delphi DCM6.2, ...) peuvent être ajoutés
simplement en créant une nouvelle classe et en l'enregistrant, sans
modifier le reste de l'application.

ATTENTION : les checksums ECU réels (CRC répartis type EDC17, checksums
Marelli, etc.) ne sont PAS tous recalculables par ces algorithmes génériques.
L'application affiche toujours un avertissement clair sur l'état du checksum
avant tout export : un fichier patché dont le checksum n'est pas corrigé peut
être refusé ou faire clignoter le voyant moteur au démarrage.
"""
from __future__ import annotations

import struct
import zlib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Optional, Type

__all__ = [
    "ChecksumAlgorithm",
    "ChecksumReport",
    "CHECKSUM_ALGORITHMS",
    "Crc32Algorithm",
    "Sum16Algorithm",
    "Sum32Algorithm",
    "TwoComplement32Algorithm",
    "evaluate_region",
    "full_file_report",
]


def _region(data: bytes, start: int, length: Optional[int]) -> bytes:
    """Extrait une région sûre du fichier (bornes vérifiées)."""
    if start < 0 or start >= len(data):
        raise ValueError(f"Offset de début invalide : {start} (taille fichier = {len(data)})")
    end = len(data) if length is None else min(len(data), start + length)
    return bytes(data[start:end])


class ChecksumAlgorithm(ABC):
    """Interface commune de tous les algorithmes de checksum."""

    name: str = "abstract"
    description: str = ""

    @abstractmethod
    def compute(self, data: bytes, start: int = 0, length: Optional[int] = None) -> int:
        """Calcule la somme de contrôle sur une région du fichier."""
        raise NotImplementedError


class Crc32Algorithm(ChecksumAlgorithm):
    """CRC-32 IEEE (poly 0x04C11DB7), très répandu sur les familles Bosch EDC/ME(D)17."""

    name = "crc32"
    description = "CRC-32 (IEEE 802.3, poly 0x04C11DB7)"

    def compute(self, data: bytes, start: int = 0, length: Optional[int] = None) -> int:
        return zlib.crc32(_region(data, start, length)) & 0xFFFFFFFF


class Sum16Algorithm(ChecksumAlgorithm):
    """Somme 16 bits (mots little-endian, modulo 0x10000)."""

    name = "sum16"
    description = "Somme 16 bits (mots LE, modulo 0x10000)"

    def compute(self, data: bytes, start: int = 0, length: Optional[int] = None) -> int:
        region = _region(data, start, length)
        if len(region) % 2:
            region += b"\x00"
        total = 0
        for (word,) in struct.iter_unpack("<H", region):
            total = (total + word) & 0xFFFF
        return total


class Sum32Algorithm(ChecksumAlgorithm):
    """Somme 32 bits (mots little-endian, modulo 2^32)."""

    name = "sum32"
    description = "Somme 32 bits (mots LE, modulo 2^32)"

    def compute(self, data: bytes, start: int = 0, length: Optional[int] = None) -> int:
        region = _region(data, start, length)
        if len(region) % 4:
            region += b"\x00" * (4 - len(region) % 4)
        total = 0
        for (word,) in struct.iter_unpack("<I", region):
            total = (total + word) & 0xFFFFFFFF
        return total


class TwoComplement32Algorithm(ChecksumAlgorithm):
    """Complément à deux 32 bits de la somme (0x100000000 - somme)."""

    name = "twos_complement32"
    description = "Complément à deux 32 bits (0x100000000 - somme)"

    def compute(self, data: bytes, start: int = 0, length: Optional[int] = None) -> int:
        region = _region(data, start, length)
        if len(region) % 4:
            region += b"\x00" * (4 - len(region) % 4)
        total = 0
        for (word,) in struct.iter_unpack("<I", region):
            total = (total + word) & 0xFFFFFFFF
        return (0x100000000 - total) & 0xFFFFFFFF


CHECKSUM_ALGORITHMS: Dict[str, Type[ChecksumAlgorithm]] = {
    algo.name: algo
    for algo in (Crc32Algorithm, Sum16Algorithm, Sum32Algorithm, TwoComplement32Algorithm)
}


@dataclass
class ChecksumReport:
    """Résultat d'évaluation d'une région de checksum."""

    algorithm: str
    start: int
    length: int
    computed_value: int
    storage_offset: Optional[int] = None
    stored_value: Optional[int] = None

    @property
    def status(self) -> str:
        """``ok`` | ``mismatch`` | ``unknown`` (valeur stockée inconnue)."""
        if self.stored_value is None:
            return "unknown"
        return "ok" if self.stored_value == self.computed_value else "mismatch"

    def summary(self) -> str:
        computed = f"0x{self.computed_value:08X}"
        if self.status == "unknown":
            return (
                f"[CHECKSUM] {self.algorithm} sur 0x{self.start:08X}"
                f" (+{self.length} octets) = {computed} — valeur stockée inconnue :"
                " vérifiez/corrigez le checksum avant flash !"
            )
        stored = f"0x{self.stored_value:08X}"
        if self.status == "ok":
            return f"[CHECKSUM] {self.algorithm} région 0x{self.start:08X} : OK ({stored})"
        return (
            f"[AVERTISSEMENT] {self.algorithm} région 0x{self.start:08X} : MISMATCH"
            f" (calculé {computed} != stocké {stored}) — checksum à corriger avant flash !"
        )


def evaluate_region(
    data: bytes,
    algorithm: str,
    start: int = 0,
    length: Optional[int] = None,
    storage_offset: Optional[int] = None,
    endianness: str = "little",
) -> ChecksumReport:
    """Évalue une région de checksum et compare avec la valeur stockée si connue."""
    if algorithm not in CHECKSUM_ALGORITHMS:
        raise ValueError(
            f"Algorithme de checksum inconnu : '{algorithm}'."
            f" Algorithmes disponibles : {sorted(CHECKSUM_ALGORITHMS)}"
        )
    region_length = len(data) - start if length is None else length
    computed = CHECKSUM_ALGORITHMS[algorithm]().compute(data, start, region_length)
    stored: Optional[int] = None
    if storage_offset is not None:
        size = 2 if algorithm == "sum16" else 4
        raw = bytes(data[storage_offset : storage_offset + size])
        stored = int.from_bytes(raw, byteorder=endianness, signed=False)
    return ChecksumReport(
        algorithm=algorithm,
        start=start,
        length=region_length,
        computed_value=computed,
        storage_offset=storage_offset,
        stored_value=stored,
    )


def full_file_report(data: bytes) -> list:
    """Rapport de contrôle rapide sur l'ensemble du fichier (valeur stockée inconnue)."""
    reports = []
    for algo_name in ("crc32", "sum32", "twos_complement32"):
        report = evaluate_region(data, algo_name, 0, None, None)
        reports.append(report)
    return reports
