"""Tests du module core.patch_engine (sessions, patches, DTC, VIN, export)."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from core.checksum import evaluate_region
from core.ecu_analyzer import _VIN_VALUES, _VIN_WEIGHTS
from core.patch_engine import (
    DtcTable,
    EcuDefinition,
    PatternPatch,
    PatchError,
    PatchSession,
    DefinitionError,
    Solution,
    load_definition,
    parse_definition,
    save_definition,
)
from core.patch_engine import definitions_dir

DUMP_SIZE = 2 * 1024 * 1024
PATTERN_OFFSET = 0x20000
PATTERN = bytes(b"\x48\x8B\x12\x34\x00\x00\x66\x85\x9A\x74\x11")
DTC_OFFSET = 0x80000
DTC_CODES = [0x0401, 0x2002, 0x2463, 0x2263, 0x0100, 0x0305, 0x1234, 0x4567, 0x2503, 0x3099, 0x4001, 0x5210]


def make_vin(prefix8: str, suffix8: str) -> str:
    candidate = prefix8 + "0" + suffix8
    total = sum(_VIN_VALUES[c] * w for c, w in zip(candidate, _VIN_WEIGHTS))
    check = total % 11
    return prefix8 + ("X" if check == 10 else str(check)) + suffix8


def make_dump(tmp_path: Path, name: str = "dump.bin") -> Path:
    rng = random.Random(42)
    dump = bytearray(rng.randbytes(DUMP_SIZE))
    dump[PATTERN_OFFSET : PATTERN_OFFSET + len(PATTERN)] = PATTERN

    for index, code in enumerate(DTC_CODES):
        offset = DTC_OFFSET + index * 4
        dump[offset : offset + 4] = code.to_bytes(2, "big") + b"\x12\x2F"
    dump[DTC_OFFSET + len(DTC_CODES) * 4 : DTC_OFFSET + (len(DTC_CODES) + 2) * 4] = b"\x00" * 8

    vin = make_vin("VF3MABBB", "BB123456")
    dump[0x40000] = 0x00
    dump[0x40001 : 0x40012] = vin.encode("ascii")
    dump[0x40012] = 0x00
    dump[0x50000] = 0x00
    dump[0x50001 : 0x50012] = vin.encode("ascii")
    dump[0x50012] = 0x00

    path = tmp_path / name
    path.write_bytes(bytes(dump))
    return path


@pytest.fixture()
def session(tmp_path: Path) -> PatchSession:
    session = PatchSession()
    session.load(make_dump(tmp_path))
    return session


# ------------------------------------------------------------------ load ----
def test_load_creates_backup(tmp_path: Path) -> None:
    path = make_dump(tmp_path)
    session = PatchSession()
    session.load(path)
    assert session.backup_path is not None
    assert session.backup_path.exists()
    assert session.backup_path.suffix == ".bak" and session.backup_path.name != path.name
    assert session.backup_path.read_bytes() == path.read_bytes()


# ------------------------------------------------------------- identité ----
def test_identity_detected(session: PatchSession) -> None:
    identity = session.identity
    assert identity is not None
    assert identity.size == DUMP_SIZE


# ------------------------------------------------------------- best def ----
def test_best_definition(session: PatchSession) -> None:
    best = session.best_definition(definitions_dir())
    assert best is not None


# ---------------------------------------------------------------- patch ----
def test_apply_pattern_patch_with_wildcards(session: PatchSession) -> None:
    patch = PatternPatch(
        name="test_jz_jmp",
        find="48 8B ?? ?? 00 00 66 85 9A 74",
        replace="48 8B ?? ?? 00 00 66 85 9A EB",
    )
    diffs = session.apply_pattern_patch(patch)
    assert len(diffs) == 1
    assert diffs[0].offset == PATTERN_OFFSET + 9
    assert diffs[0].original == 0x74
    assert diffs[0].patched == 0xEB
    assert session.data[PATTERN_OFFSET + 9] == 0xEB
    assert session.data[PATTERN_OFFSET : PATTERN_OFFSET + 6] == PATTERN[:6]


def test_apply_pattern_patch_not_found_raises(session: PatchSession) -> None:
    patch = PatternPatch(name="absent", find="DE AD BE EF 00 11", replace="DE AD BE EF 00 22")
    with pytest.raises(PatchError):
        session.apply_pattern_patch(patch)


def test_apply_pattern_patch_length_mismatch(session: PatchSession) -> None:
    patch = PatternPatch(name="mauvais", find="48 8B ?? ?? 00 00", replace="48 8B 90 ?? 00 00 11")
    with pytest.raises(PatchError):
        session.apply_pattern_patch(patch)


# ------------------------------------------------------------------ DTC ----
def test_dtc_table_definition_and_scan(session: PatchSession) -> None:
    definition = EcuDefinition(
        definition_id="test_ecu",
        name="ECU de test",
        manufacturer="Test",
        ecu_families=["EDC17C10"],
        id_patterns=["EDC17C10"],
        min_size=0,
        max_size=8 * 1024 * 1024,
        dtc_tables=[
            DtcTable(
                name="Table test",
                entry_size=4,
                code_offset=0,
                switch_offset=3,
                byte_order="big",
                locator="04 01 12 2F",
            )
        ],
    )
    entries = session._scan_dtc_table(definition.dtc_tables[0])
    assert [e.code for e in entries] == DTC_CODES
    assert entries[0].code_str == "P0401"
    assert entries[1].code_str == "P2002"
    assert entries[2].code_str == "P2463"


def test_disable_dtc_entries(session: PatchSession) -> None:
    definition = EcuDefinition(
        definition_id="test_ecu",
        name="ECU de test",
        manufacturer="Test",
        ecu_families=[],
        id_patterns=[],
        min_size=0,
        max_size=8 * 1024 * 1024,
        dtc_tables=[
            DtcTable(
                name="Table test",
                entry_size=4,
                switch_offset=3,
                byte_order="big",
                locator="04 01 12 2F",
            )
        ],
    )
    session.definition = definition
    entries = session._scan_dtc_table(definition.dtc_tables[0])[:2]
    diffs = session.disable_dtc_entries(entries)
    assert len(diffs) == 2
    for entry in entries:
        assert session.data[entry.switch_offset] == 0x00
    rescanned = session._scan_dtc_table(definition.dtc_tables[0])
    assert all(e.code_str != "P0401" or not e.active for e in rescanned)


# ----------------------------------------------------------- reload / bak ----
def test_reload_original_restores(session: PatchSession) -> None:
    patch = PatternPatch(name="test", find="48 8B ?? ?? 00 00 66 85 9A 74", replace="48 8B ?? ?? 00 00 66 85 9A EB")
    session.apply_pattern_patch(patch)
    assert session.diffs
    session.reload_original()
    assert session.diffs == []
    assert session.data[PATTERN_OFFSET : PATTERN_OFFSET + len(PATTERN)] == PATTERN


def test_restore_backup(tmp_path: Path) -> None:
    path = make_dump(tmp_path)
    session = PatchSession()
    session.load(path)
    session.apply_pattern_patch(
        PatternPatch(name="t", find="48 8B ?? ?? 00 00 66 85 9A 74", replace="48 8B ?? ?? 00 00 66 85 9A EB")
    )
    session.export(tmp_path / "patched.bin")
    restored = session.restore_backup(session.backup_path)
    assert restored.size == DUMP_SIZE
    assert session.data[PATTERN_OFFSET : PATTERN_OFFSET + len(PATTERN)] == PATTERN


# ------------------------------------------------------------------ VIN ----
def test_find_vins_in_dump(session: PatchSession) -> None:
    vin = make_vin("VF3MABBB", "BB123456")
    offsets = [offset for offset, found in session.find_vins() if found == vin]
    assert offsets == [0x40001, 0x50001]


def test_replace_vin_syncs_all_occurrences(session: PatchSession) -> None:
    vin = make_vin("VF3MABBB", "BB123456")
    new_vin = make_vin("VF3XYZZZ", "ZZ987654")
    diffs = session.replace_vin(new_vin)
    replaced = [e for e in diffs if 0x40000 <= e.offset <= 0x50012]
    assert replaced
    for offset in (0x40001, 0x50001):
        assert bytes(session.data[offset : offset + 17]) == new_vin.encode("ascii")
        assert vin not in bytes(session.data[offset - 1 : offset + 18]).decode("ascii", errors="ignore")


def test_replace_vin_invalid_length(session: PatchSession) -> None:
    with pytest.raises(PatchError):
        session.replace_vin("VF3MABBB1BB12345")  # 16 caractères


def test_replace_vin_rejects_ioq(session: PatchSession) -> None:
    with pytest.raises(PatchError):
        session.replace_vin("VF3MQBBB1BB123456")


def test_replace_vin_rejects_18_chars(session: PatchSession) -> None:
    with pytest.raises(PatchError):
        session.replace_vin("VF3MABBB1BB1234567")


# -------------------------------------------------------- export/checksum ----
def test_export_patched_file(session: PatchSession, tmp_path: Path) -> None:
    session.apply_pattern_patch(
        PatternPatch(name="t", find="48 8B ?? ?? 00 00 66 85 9A 74", replace="48 8B ?? ?? 00 00 66 85 9A EB")
    )
    target = tmp_path / "out.bin"
    exported, warnings = session.export(target)
    assert exported == target
    assert target.read_bytes() == bytes(session.data)
    assert warnings
    target2 = tmp_path / "out.bin"
    target2.write_bytes(b"x")
    exported2, _ = session.export(target2)
    assert exported2 == target2


def test_checksum_region_matches_engine(session: PatchSession) -> None:
    report = evaluate_region(bytes(session.data), "crc32", 0, 1024)
    assert report.status == "unknown"


# ------------------------------------------------------------ définitions ----
def test_definition_roundtrip(tmp_path: Path) -> None:
    definition = EcuDefinition(
        definition_id="def1",
        name="Définition test",
        manufacturer="Bosch",
        ecu_families=["EDC17C10"],
        id_patterns=["EDC17C10"],
        min_size=1024,
        max_size=4 * 1024 * 1024,
        solutions=[
            Solution(
                id="egr_off",
                label="EGR Off",
                category="antipollution",
                description="Test",
                patches=[PatternPatch(name="p", find="11 22", replace="11 33")],
            )
        ],
        dtc_tables=[DtcTable(name="T", entry_size=4, byte_order="little")],
    )
    path = tmp_path / "def1.json"
    save_definition(definition, path)
    loaded = load_definition(path)
    assert loaded.definition_id == "def1"
    assert loaded.solutions[0].patches[0].find == "11 22"
    assert loaded.dtc_tables[0].byte_order == "little"


def test_parse_definition_invalid_schema_version() -> None:
    with pytest.raises(DefinitionError):
        parse_definition({"schema_version": 99, "definition_id": "x", "name": "x", "manufacturer": "x"})


def test_parse_definition_missing_name() -> None:
    with pytest.raises(DefinitionError):
        parse_definition({"schema_version": 1, "definition_id": "x", "manufacturer": "x"})


def test_parse_definition_empty_solution() -> None:
    with pytest.raises(DefinitionError):
        parse_definition(
            {
                "schema_version": 1,
                "definition_id": "x",
                "name": "x",
                "manufacturer": "x",
                "solutions": [{"id": "egr_off", "patches": []}],
            }
        )
