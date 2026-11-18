"""Persistance des réglages utilisateur (settings.json).

Les réglages sont stockés dans un fichier JSON simple, à côté de l'exécutable
(quand l'application est compilée avec PyInstaller) ou à la racine du projet
sinon. Le module est volontairement tolérant : un fichier corrompu ne doit
jamais empêcher l'application de démarrer.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

SETTINGS_FILENAME = "settings.json"

DEFAULTS: Dict[str, Any] = {
    "interface": "",
    "baudrate": 500000,
    "tx_id": "7E0",
    "rx_id": "7E8",
    "tester_present": False,
    "last_dir": "",
    "theme": "dark",
}


def base_dir() -> Path:
    """Répertoire racine de l'application (compatible PyInstaller onefile)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def settings_path() -> Path:
    """Chemin complet du fichier settings.json."""
    return base_dir() / SETTINGS_FILENAME


def load_settings() -> Dict[str, Any]:
    """Charge les réglages en fusionnant avec les valeurs par défaut.

    Un fichier absent, illisible ou corrompu renvoie simplement les valeurs
    par défaut : aucune exception ne doit remonter vers l'interface.
    """
    settings = dict(DEFAULTS)
    path = settings_path()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            for key in DEFAULTS:
                if key in raw:
                    settings[key] = raw[key]
        else:
            logger.warning("Réglages ignorés (structure inattendue) : %s", path)
    except FileNotFoundError:
        pass
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Réglages illisibles (%s) : %s", path, exc)
    return settings


def save_settings(settings: Dict[str, Any]) -> bool:
    """Écrit les réglages sur disque de manière non bloquante pour l'UI.

    L'écriture est atomique (fichier temporaire + os.replace) et les erreurs
    sont journalisées sans être propagées : une sauvegarde de réglages ne doit
    jamais interrompre l'utilisateur.
    """
    data = dict(DEFAULTS)
    path = settings_path()
    try:
        existing = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(existing, dict):
            data.update({k: v for k, v in existing.items() if k in DEFAULTS})
    except (OSError, json.JSONDecodeError):
        pass
    data.update({k: v for k, v in settings.items() if k in DEFAULTS})
    tmp_path = path.with_suffix(".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        os.replace(tmp_path, path)
        return True
    except OSError as exc:
        logger.warning("Impossible d'enregistrer les réglages (%s) : %s", path, exc)
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        return False
