"""Tests du module core.checksum (algorithmes génériques)."""
from __future__ import annotations

import zlib

import pytest

from core.checksum import (
    CHECKSUM_ALGORITHMS,
    Crc32Algorithm,
    Sum16Algorithm,
    Sum32Algorithm,
    TwoComplement32Algorithm,
    evaluate_region,
    full_file_report,
)


def test_crc32_known_vector() -> None:
    assert Crc32Algorithm().compute(b"123456789") == zlib.crc32(b"123456789") == 0xCBF43926


def test_sum16_basic() -> None:
    assert Sum16Algorithm().compute(b"\x01\x00\x02\x00") == 3


def test_sum32_basic() -> None:
    assert Sum32Algorithm().compute(b"\x01\x00\x00\x00\x02\x00\x00\x00") == 3


def test_twos_complement32_basic() -> None:
    assert TwoComplement32Algorithm().compute(b"\x01\x00\x00\x00\x02\x00\x00\x00") == 0xFFFFFFFD


def test_odd_length_padding() -> None:
    assert Sum16Algorithm().compute(b"\x01\x00\x02") == 3
    assert Sum32Algorithm().compute(b"\x01\x00\x00\x00\x02\x00\x00") == 3


def test_registry_keys() -> None:
    assert set(CHECKSUM_ALGORITHMS) == {"crc32", "sum16", "sum32", "twos_complement32"}


def test_evaluate_region_storage_match_little_endian() -> None:
    data = b"\x01\x00\x02\x00" + (b"\xAA" * 8) + (3).to_bytes(2, "little")
    report = evaluate_region(data, "sum16", 0, 4, storage_offset=12, endianness="little")
    assert report.status == "ok"
    assert report.summary().startswith("[CHECKSUM]")


def test_evaluate_region_storage_mismatch_big_endian() -> None:
    data = b"\x01\x00\x02\x00" + b"\xFF\xFF"
    report = evaluate_region(data, "sum16", 0, 4, storage_offset=4, endianness="big")
    assert report.status == "mismatch"
    assert "MISMATCH" in report.summary()


def test_evaluate_region_unknown_storage() -> None:
    data = b"\x01\x00\x02\x00"
    report = evaluate_region(data, "sum16", 0, 4)
    assert report.status == "unknown"
    assert "valeur stockée inconnue" in report.summary()


def test_unknown_algorithm_raises() -> None:
    with pytest.raises(ValueError):
        evaluate_region(b"\x00\x00", "sha256 maison")


def test_out_of_bounds_start_raises() -> None:
    with pytest.raises(ValueError):
        evaluate_region(b"\x00\x00", "crc32", start=100)


def test_full_file_report_three_algorithms() -> None:
    reports = full_file_report(b"123456789")
    assert [r.algorithm for r in reports] == ["crc32", "sum32", "twos_complement32"]
    assert all(r.status == "unknown" for r in reports)
