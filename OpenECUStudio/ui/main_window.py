# -*- coding: utf-8 -*-
"""Fenêtre principale OpenECU Studio — assemblage des 4 onglets."""
from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtWidgets import QLabel, QMainWindow, QStatusBar, QTabWidget, QWidget

from core.patch_engine import PatchSession
from ui.tab_definitions import DefinitionsTab
from ui.tab_diagnostics import DiagnosticsTab
from ui.tab_diff import DiffViewerTab
from ui.tab_patcher import PatcherTab

logger = logging.getLogger(__name__)

APP_NAME = "OpenECU Studio"
APP_VERSION = "1.0.0"


class MainWindow(QMainWindow):
    """Fenêtre principale : 4 onglets (Diagnostic, Patcher, Diff, Définitions)."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION} — J2534 / UDS / ECU Patcher")
        self.resize(1280, 860)

        self.session = PatchSession()

        self.tabs = QTabWidget()
        self.diagnostics_tab = DiagnosticsTab()
        self.patcher_tab = PatcherTab(self.session)
        self.diff_tab = DiffViewerTab(self.session)
        self.definitions_tab = DefinitionsTab()
        self.tabs.addTab(self.diagnostics_tab, "Diagnostic & SM2 Pro (J2534)")
        self.tabs.addTab(self.patcher_tab, "Éditeur ECU & Patcher (Offline)")
        self.tabs.addTab(self.diff_tab, "Comparateur Hexadécimal")
        self.tabs.addTab(self.definitions_tab, "Gestionnaire de Définitions")
        self.setCentralWidget(self.tabs)

        self.patcher_tab.diffs_updated.connect(self.diff_tab.refresh)
        self.definitions_tab.definitions_changed.connect(self._on_definitions_changed)

        status_bar = QStatusBar()
        status_bar.addWidget(
            QLabel(
                "Diagnostic : SAE J2534-1 (ISO 15765 / ISO 14229) — Patcher : définitions JSON"
                " — Sauvegarde .bak automatique avant modification"
            )
        )
        self.setStatusBar(status_bar)
        logger.info("Fenêtre principale initialisée.")

    def _on_definitions_changed(self) -> None:
        self.patcher_tab._reload_definitions(auto_select=True)
        logger.info("Définitions rechargées depuis le Gestionnaire de Définitions.")
