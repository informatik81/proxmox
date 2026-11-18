# -*- coding: utf-8 -*-
"""Fenêtre principale OpenECU Studio — assemblage des 4 onglets."""
from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QMenuBar,
    QMessageBox,
    QStatusBar,
    QTabWidget,
    QWidget,
)

from core import settings as app_settings
from core.patch_engine import PatchSession
from ui.tab_definitions import DefinitionsTab
from ui.tab_diagnostics import DiagnosticsTab
from ui.tab_diff import DiffViewerTab
from ui.tab_patcher import PatcherTab

logger = logging.getLogger(__name__)

APP_NAME = "OpenECU Studio"
APP_VERSION = "1.2.0"

THEME_LABELS = {
    "dark": "Thème sombre",
    "light": "Thème clair",
}


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

        self._build_themes_menu()

        self._current_theme = str(app_settings.load_settings().get("theme", "dark"))

        status_bar = QStatusBar()
        status_bar.addWidget(
            QLabel(
                "Diagnostic : SAE J2534-1 (ISO 15765 / ISO 14229) — Patcher : définitions JSON"
                " — Sauvegarde .bak automatique avant modification"
            )
        )
        self.setStatusBar(status_bar)
        logger.info("Fenêtre principale initialisée.")

    def _build_themes_menu(self) -> None:
        menu_bar = QMenuBar(self)
        self.setMenuBar(menu_bar)
        display_menu = menu_bar.addMenu("Affichage")
        self._theme_actions: dict = {}
        for theme_name, label in THEME_LABELS.items():
            action = display_menu.addAction(label)
            action.setCheckable(True)
            action.triggered.connect(
                lambda checked=False, name=theme_name: self._switch_theme(name)
            )
            self._theme_actions[theme_name] = action
        self._sync_theme_actions()

    def _sync_theme_actions(self) -> None:
        for theme_name, action in self._theme_actions.items():
            action.setChecked(theme_name == self._current_theme)

    def _switch_theme(self, theme_name: str) -> None:
        app = QApplication.instance()
        if app is None:
            return
        from ui.theme import apply_theme

        self._current_theme = apply_theme(app, theme_name)
        self._sync_theme_actions()
        app_settings.save_settings({"theme": self._current_theme})
        self.statusBar().showMessage(
            f"{THEME_LABELS[self._current_theme]} appliqué — préférence enregistrée.", 5000
        )
        logger.info("Changement de thème : %s", self._current_theme)

    def _on_definitions_changed(self) -> None:
        self.patcher_tab._reload_definitions(auto_select=True)
        logger.info("Définitions rechargées depuis le Gestionnaire de Définitions.")

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.session.is_loaded and self.session.diffs:
            answer = QMessageBox.question(
                self,
                "Modifications non exportées",
                f"{len(self.session.diffs)} modification(s) en mémoire ne sont pas exportées.\n\n"
                "Elles seront perdues à la fermeture (la sauvegarde .bak du fichier "
                "d'origine est conservée).\n\nConfirmez-vous la fermeture ?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                event.ignore()
                return
        self.diagnostics_tab.shutdown()
        event.accept()
        logger.info("Application fermée proprement.")
