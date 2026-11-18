"""Tests du module core.settings (persistance tolérante aux pannes)."""
from __future__ import annotations

import json

import pytest

from core import settings


@pytest.fixture()
def settings_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "settings_path", lambda: tmp_path / "settings.json")
    return tmp_path


def test_defaults_when_missing(settings_dir) -> None:
    loaded = settings.load_settings()
    for key, value in settings.DEFAULTS.items():
        assert loaded[key] == value


def test_roundtrip(settings_dir) -> None:
    configs = {"interface": "SM2 USB", "baudrate": 250000, "tx_id": "7E0", "rx_id": "7E8", "tester_present": True}
    assert settings.save_settings(configs) is True
    loaded = settings.load_settings()
    assert loaded["interface"] == "SM2 USB"
    assert loaded["baudrate"] == 250000
    assert loaded["tester_present"] is True


def test_unknown_keys_dropped(settings_dir) -> None:
    settings.save_settings({"interface": "X", "pirate": True})
    loaded = settings.load_settings()
    assert "pirate" not in loaded


def test_corrupted_file_falls_back_to_defaults(settings_dir) -> None:
    settings_dir.joinpath("settings.json").write_text("{ceci n'est pas du json", encoding="utf-8")
    loaded = settings.load_settings()
    assert loaded == dict(settings.DEFAULTS)


def test_save_creates_json_on_disk(settings_dir) -> None:
    settings.save_settings({"interface": "Mock"})
    payload = json.loads(settings_dir.joinpath("settings.json").read_text(encoding="utf-8"))
    assert payload["interface"] == "Mock"
