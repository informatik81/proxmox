# -*- coding: utf-8 -*-
"""Onglet 3 : Comparateur hexadécimal (Diff Viewer) — offset | original | modifié."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.patch_engine import DiffEntry, PatchError, PatchSession
from ui.theme import current_theme, mono_font

logger = logging.getLogger(__name__)


class DiffViewerTab(QWidget):
    """Visualisation côte-à-côte de tous les octets modifiés avant export."""

    def __init__(self, session: PatchSession, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.session = session
        self._diffs: List[DiffEntry] = []
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        group = QGroupBox("Octets modifiés (Offset | Original | Modifié)")
        group_layout = QVBoxLayout(group)

        toolbar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Filtrer par offset (ex : 0F3A2)...")
        self.search.textChanged.connect(self._refresh_table)
        self.count_label = QLabel("0 modification(s)")
        self.count_label.setObjectName("statusLabel")
        toolbar.addWidget(QLabel("Filtre :"))
        toolbar.addWidget(self.search, 1)
        toolbar.addWidget(self.count_label)
        group_layout.addLayout(toolbar)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Offset", "D'origine", "Modifié"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setFont(mono_font())
        group_layout.addWidget(self.table)
        layout.addWidget(group)

        export_layout = QHBoxLayout()
        export_button = QPushButton("Exporter le .bin patché")
        export_button.setObjectName("primary")
        export_button.clicked.connect(self._on_export)
        self.status_label = QLabel("Aucune modification en attente.")
        self.status_label.setObjectName("statusLabel")
        export_layout.addWidget(export_button)
        export_layout.addWidget(self.status_label, 1)
        layout.addLayout(export_layout)

    def refresh(self, diffs: List[DiffEntry]) -> None:
        """Met à jour la vue depuis la liste des différences de la session."""
        self._diffs = list(diffs)
        self._refresh_table()

    def _refresh_table(self) -> None:
        needle = self.search.text().strip().upper().replace("0X", "")
        visible = [
            diff
            for diff in self._diffs
            if not needle or f"{diff.offset:X}".upper().startswith(needle)
        ]
        self.table.setRowCount(len(visible))
        for row, diff in enumerate(visible):
            offset_item = QTableWidgetItem(f"0x{diff.offset:06X}")
            original_item = QTableWidgetItem(f"0x{diff.original:02X}")
            patched_item = QTableWidgetItem(f"0x{diff.patched:02X}")
            patched_item.setForeground(QColor(current_theme().accent))
            self.table.setItem(row, 0, offset_item)
            self.table.setItem(row, 1, original_item)
            self.table.setItem(row, 2, patched_item)
        self.count_label.setText(f"{len(visible)} modification(s) affichée(s) / {len(self._diffs)} total")
        self.status_label.setText(
            "Aucune modification en attente." if not self._diffs else "Vérifiez le checksum avant export."
        )
        self.status_label.setStyleSheet(
            f"color: {current_theme().ok};" if not self._diffs else f"color: {current_theme().error};"
        )

    def _on_export(self) -> None:
        if not self.session.is_loaded:
            QMessageBox.information(self, "OpenECU Studio", "Chargez d'abord un fichier ECU (onglet Patcher).")
            return
        if not self._diffs:
            QMessageBox.information(self, "OpenECU Studio", "Aucune modification à exporter.")
            return
        suggested = str(
            self.session.file_path.with_name(self.session.file_path.stem + "_patched.bin")
        )
        path, _ = QFileDialog.getSaveFileName(
            self, "Exporter le fichier patché", suggested, "Fichier binaire (*.bin)"
        )
        if not path:
            return
        warnings = self.session.checksum_warnings()
        if warnings:
            answer = QMessageBox.question(
                self,
                "Export — ATTENTION CHECKSUM",
                "Le calcul des checksums signale des écarts :\n- "
                + "\n- ".join(warnings)
                + "\n\nUn fichier flashé avec un checksum incorrect peut rendre le "
                "calculateur INUTILISABLE. Validez les checksums avec un outil dédié "
                "avant tout flash.\n\nConfirmez-vous l'export ?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return
        try:
            exported, warnings = self.session.export(Path(path))
        except (OSError, PatchError) as exc:
            QMessageBox.critical(self, "Erreur d'export", str(exc))
            return
        message = f"Fichier exporté :\n{exported}"
        if warnings:
            message += "\n\n⚠ AVERTISSEMENTS CHECKSUM :\n- " + "\n- ".join(warnings)
            QMessageBox.warning(self, "Export terminé", message)
        else:
            QMessageBox.information(self, "Export terminé", message)
