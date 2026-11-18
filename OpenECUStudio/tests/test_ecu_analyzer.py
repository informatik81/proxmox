"""Tests du module core.ecu_analyzer (entropie, patterns, VIN, signatures)."""
from __future__ import annotations

import random

import pytest

from core.ecu_analyzer import (
    EcuAnalyzer,
    _VIN_VALUES,
    _VIN_WEIGHTS,
    find_pattern,
    pattern_to_regex,
    vin_check_digit_valid,
)


def make_dump(size: int = 2 * 1024 * 1024, seed: int = 42) -> bytearray:
    rng = random.Random(seed)
    return bytearray(rng.randbytes(size))


def make_vin(prefix8: str, suffix8: str) -> str:
    """Construit un VIN de 17 caractères avec le 9e issu du contrôle ISO 3779."""
    candidate = prefix8 + "0" + suffix8
    total = sum(_VIN_VALUES[c] * w for c, w in zip(candidate, _VIN_WEIGHTS))
    check = total % 11
    check_char = "X" if check == 10 else str(check)
    return prefix8 + check_char + suffix8


# ---------------------------------------------------------------- entropie ---
def test_entropy_constant_zero() -> None:
    assert EcuAnalyzer.shannon_entropy(b"\x00" * 4096) == 0.0


def test_entropy_empty_zero() -> None:
    assert EcuAnalyzer.shannon_entropy(b"") == 0.0


def test_entropy_uniform_is_8() -> None:
    assert EcuAnalyzer.shannon_entropy(bytes(range(256)) * 4) == pytest.approx(8.0, abs=1e-9)


# ---------------------------------------------------------------- chaînes ----
def test_extract_strings() -> None:
    data = b"\x00\x00EDC17C10 ok\x00\x01\x02ab\x00"
    strings = EcuAnalyzer.extract_strings(data)
    assert (2, "EDC17C10 ok") in strings
    assert all(text == text.strip() for _, text in strings)


# ---------------------------------------------------------------- patterns ---
def test_pattern_hit_with_wildcards() -> None:
    data = b"\x48\x8B\x12\x34\x00\x00\xAA\x48\x8B\x99\x88\x00\x00\xBB"
    assert find_pattern(data, "48 8B ?? ?? 00 00") == [0, 7]


def test_pattern_miss() -> None:
    assert find_pattern(b"\x00\x01\x02", "48 8B ??") == []


def test_pattern_bad_token() -> None:
    with pytest.raises(ValueError):
        pattern_to_regex("48 8B GG")


def test_pattern_empty() -> None:
    with pytest.raises(ValueError):
        pattern_to_regex("   ")


# ------------------------------------------------------------------ VIN ------
def test_find_vins_detects_and_syncs() -> None:
    vin = make_vin("VF3MABBB", "BB123456")
    data = b"\x00" + vin.encode("ascii") + b"\x00\xFF" + vin.encode("ascii") + b"\x00"
    found = EcuAnalyzer.find_vins(data)
    assert [v for _, v in found].count(vin) == 2


def test_find_vins_rejects_ioq() -> None:
    data = b"\x00VF3MAIBB1BB123456\x00"
    assert EcuAnalyzer.find_vins(data) == []


def test_vin_check_digit_valid() -> None:
    vin = make_vin("VF3MABBB", "BB123456")
    assert len(vin) == 17
    assert vin_check_digit_valid(vin) is True


def test_vin_check_digit_invalid() -> None:
    vin = make_vin("VF3MABBB", "BB123456")
    invalid = vin[:-1] + ("7" if vin[-1] != "7" else "8")
    assert len(invalid) == 17
    assert vin_check_digit_valid(invalid) is False


def test_vin_check_digit_wrong_length() -> None:
    assert vin_check_digit_valid("VF3MABBB1BB12345") is None


# ------------------------------------------------------------- signatures ----
def test_signature_detected_on_synthetic_dump() -> None:
    dump = make_dump()
    dump[0x1000:0x1008] = b"EDC17C10"
    dump[0x2000:0x200A] = b"0281020304"
    identity = EcuAnalyzer().analyze(bytes(dump))
    assert identity.detected_family == "EDC17C10"
    assert "0281020304" in identity.part_numbers
    assert identity.confidence in ("Moyenne", "Élevée")


def test_signature_unknown_on_random_data() -> None:
    dump = make_dump(seed=1234)
    identity = EcuAnalyzer().analyze(bytes(dump))
    assert identity.detected_family == "Inconnu"
    assert identity.confidence == "Aucune"
    assert identity.size == len(dump)
