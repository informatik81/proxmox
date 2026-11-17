# -*- coding: utf-8 -*-
"""Onglet 2 : Éditeur ECU & Patcher (offline) — définitions, solutions, DTC Remover."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFormLayout,
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

from core.patch_engine import (
    DtcEntry,
    DefinitionError,
    EcuDefinition,
    PatchError,
    PatchSession,
    definitions_dir,
    list_definitions,
    load_definition,
)
from ui.theme import COLOR_ERROR, COLOR_OK, mono_font

logger = logging.getLogger(__name__)


class PatcherTab(QWidget):
    """Chargement d'un dump, application des solutions et DTC Remover."""

    diffs_updated = Signal(list)
    definition_changed = Signal(object)

    def __init__(self, session: PatchSession, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.session = session
        self._dtc_entries: List[DtcEntry] = []
        self._solution_checks: List[tuple] = []
        self._build_ui()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        file_group = QGroupBox("Fichier ECU (.bin / .ori)")
        file_layout = QVBoxLayout(file_group)
        file_buttons = QHBoxLayout()
        load_button = QPushButton("Charger un fichier ECU")
        load_button.setObjectName("primary")
        load_button.clicked.connect(self._on_load_file)
        restore_button = QPushButton("Restaurer une sauvegarde .bak")
        restore_button.setToolTip("Recharge un fichier de sauvegarde (retour à l'état d'origine d'un dump).")
        restore_button.clicked.connect(self._on_restore_backup)
        revert_button = QPushButton("Annuler les modifications (session)")
        revert_button.setToolTip("Revenir au fichier tel que chargé, en annulant tous les patchs de la session.")
        revert_button.clicked.connect(self._on_revert_original)
        file_buttons.addWidget(load_button)
        file_buttons.addWidget(restore_button)
        file_buttons.addWidget(revert_button)
        self.file_label = QLabel("Aucun fichier chargé.")
        self.file_label.setObjectName("statusLabel")
        file_buttons.addWidget(self.file_label, 1)
        file_layout.addLayout(file_buttons)

        self.identity_form = QFormLayout()
        self.identity_fields: dict = {}
        for key in ("Famille détectée", "Constructeur ECU", "Taille", "Entropie", "N° de pièce", "SAUVEGARDE"):
            field = QLineEdit()
            field.setReadOnly(True)
            field.setFont(mono_font())
            self.identity_fields[key] = field
            self.identity_form.addRow(key + " :", field)
        file_layout.addLayout(self.identity_form)
        layout.addWidget(file_group)

        definition_group = QGroupBox("Définition de calculateur (JSON)")
        definition_layout = QHBoxLayout(definition_group)
        self.definition_combo = QComboBox()
        self.definition_combo.currentIndexChanged.connect(self._on_definition_selected)
        reload_button = QPushButton("Recharger")
        reload_button.clicked.connect(self._reload_definitions)
        self.match_label = QLabel("")
        self.match_label.setObjectName("statusLabel")
        definition_layout.addWidget(QLabel("Définition :"))
        definition_layout.addWidget(self.definition_combo, 1)
        definition_layout.addWidget(reload_button)
        definition_layout.addWidget(self.match_label)
        layout.addWidget(definition_group)

        columns = QHBoxLayout()

        solutions_group = QGroupBox("Solutions disponibles")
        self.solutions_layout = QVBoxLayout(solutions_group)
        self.solutions_hint = QLabel("Chargez un fichier pour afficher les solutions.")
        self.solutions_hint.setObjectName("statusLabel")
        self.solutions_layout.addWidget(self.solutions_hint)
        apply_button = QPushButton("Appliquer les solutions cochées")
        apply_button.setObjectName("primary")
        apply_button.clicked.connect(self._on_apply_solutions)
        self.solutions_layout.addWidget(apply_button)
        columns.addWidget(solutions_group, 1)

        dtc_group = QGroupBox("DTC détectés dans le dump (DTC Remover)")
        dtc_layout = QVBoxLayout(dtc_group)
        search_row = QHBoxLayout()
        self.dtc_search = QLineEdit()
        self.dtc_search.setPlaceholderText("Rechercher un code (ex : P0401, P2002, P2463)...")
        self.dtc_search.textChanged.connect(self._filter_dtc_table)
        scan_button = QPushButton("Scanner")
        scan_button.clicked.connect(self._on_scan_dtcs)
        search_row.addWidget(self.dtc_search, 1)
        search_row.addWidget(scan_button)
        dtc_layout.addLayout(search_row)

        self.dtc_table = QTableWidget(0, 5)
        self.dtc_table.setHorizontalHeaderLabels(["Offset", "Code", "Table", "État", "Switch"])
        self.dtc_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.dtc_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.dtc_table.setEditTriggers(QTableWidget.NoEditTriggers)
        dtc_layout.addWidget(self.dtc_table)

        dtc_buttons = QHBoxLayout()
        disable_button = QPushButton("Désactiver les DTC sélectionnés")
        disable_button.setObjectName("danger")
        disable_button.clicked.connect(self._on_disable_selected)
        dtc_buttons.addWidget(disable_button)
        self.dtc_count_label = QLabel("0 DTC")
        self.dtc_count_label.setObjectName("statusLabel")
        dtc_buttons.addWidget(self.dtc_count_label)
        dtc_layout.addLayout(dtc_buttons)
        columns.addWidget(dtc_group, 2)

        layout.addLayout(columns)

        export_row = QHBoxLayout()
        export_button = QPushButton("Exporter le .bin patché")
        export_button.setObjectName("primary")
        export_button.clicked.connect(self._on_export)
        self.checksum_label = QLabel("")
        self.checksum_label.setWordWrap(True)
        export_row.addWidget(export_button)
        export_row.addWidget(self.checksum_label, 1)
        layout.addLayout(export_row)

        self._reload_definitions()

    # ------------------------------------------------------------- chargement
    def _on_load_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Ouvrir un fichier ECU", "", "Fichiers ECU (*.bin *.ori *.mpc);;Tous les fichiers (*)"
        )
        if not path:
            return
        self._load_path(Path(path))

    def _on_restore_backup(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Restaurer une sauvegarde", "", "Sauvegardes (*.bak);;Tous les fichiers (*)"
        )
        if not path:
            return
        self._load_path(Path(path))

    def _on_revert_original(self) -> None:
        if not self.session.is_loaded:
            QMessageBox.information(self, "OpenECU Studio", "Chargez d'abord un fichier ECU.")
            return
        if not self.session.diffs:
            QMessageBox.information(self, "OpenECU Studio", "Aucune modification à annuler.")
            return
        self.session.reload_original()
        self._on_scan_dtcs()
        self._update_checksum_label()
        self.diffs_updated.emit(list(self.session.diffs))
        QMessageBox.information(self, "OpenECU Studio", "Fichier revenu à son état d'origine (0 modification).")

    def _load_path(self, path: Path) -> None:
        try:
            identity = self.session.load(path)
        except (OSError, PatchError) as exc:
            QMessageBox.critical(self, "Erreur de chargement", str(exc))
            return
        self.file_label.setText(f"{path}")
        fields = self.identity_fields
        fields["Famille détectée"].setText(f"{identity.detected_family} ({identity.confidence})")
        fields["Constructeur ECU"].setText(identity.manufacturer)
        fields["Taille"].setText(f"{identity.size} octets (0x{identity.size:X})")
        fields["Entropie"].setText(f"{identity.entropy:.3f} bits/octet")
        fields["N° de pièce"].setText(", ".join(identity.part_numbers) if identity.part_numbers else "-")
        fields["SAUVEGARDE"].setText(str(self.session.backup_path))
        self._reload_definitions(auto_select=True)
        self._on_scan_dtcs()
        self._update_checksum_label()

    # -------------------------------------------------------------- définition
    def _reload_definitions(self, auto_select: bool = False) -> None:
        self.definition_combo.blockSignals(True)
        self.definition_combo.clear()
        self.definition_combo.addItem("— Aucune —", None)
        for path in list_definitions(definitions_dir()):
            try:
                definition = load_definition(path)
            except DefinitionError as exc:
                logger.warning("Définition invalide (%s) : %s", path.name, exc)
                continue
            self.definition_combo.addItem(f"{definition.name}", (definition, path))
        self.definition_combo.blockSignals(False)
        if auto_select and self.session.is_loaded:
            best_index, best_score = 0, 0
            for index in range(1, self.definition_combo.count()):
                definition = self.definition_combo.itemData(index)[0]
                score = self.session.match_score(definition)
                if score > best_score:
                    best_index, best_score = index, score
            if best_score > 0:
                self.definition_combo.setCurrentIndex(best_index)
        else:
            self._on_definition_selected(self.definition_combo.currentIndex())

    def _on_definition_selected(self, index: int) -> None:
        data = self.definition_combo.itemData(index)
        definition = data[0] if isinstance(data, tuple) else None
        self.session.definition = definition
        self._rebuild_solutions(definition)
        score = self.session.match_score(definition) if definition else 0
        if definition is None:
            self.match_label.setText("")
        elif not self.session.is_loaded:
            self.match_label.setText("Chargez un fichier pour vérifier la compatibilité.")
        else:
            self.match_label.setText(
                "✔ Compatible avec le dump chargé" if score >= 3 else "⚠ Faible compatibilité avec ce dump"
            )
            self.match_label.setStyleSheet(
                f"color: {COLOR_OK};" if score >= 3 else f"color: {COLOR_ERROR};"
            )
        self.definition_changed.emit(definition)

    def _rebuild_solutions(self, definition: Optional[EcuDefinition]) -> None:
        while self.solutions_layout.count() > 1:
            item = self.solutions_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._solution_checks = []
        if definition is None:
            self.solutions_hint.setText("Chargez un fichier pour afficher les solutions.")
            self.solutions_hint.show()
            return
        self.solutions_hint.hide()
        for solution in definition.solutions:
            checkbox = QCheckBox(f"{solution.label}  ({solution.category})")
            checkbox.setToolTip(solution.description)
            self.solutions_layout.addWidget(checkbox)
            self._solution_checks.append((checkbox, solution))

    # --------------------------------------------------------------- solutions
    def _on_apply_solutions(self) -> None:
        if not self.session.is_loaded:
            QMessageBox.information(self, "OpenECU Studio", "Chargez d'abord un fichier ECU.")
            return
        applied, errors, total = 0, [], 0
        for checkbox, solution in self._solution_checks:
            if not checkbox.isChecked():
                continue
            count, solution_errors = self.session.apply_solution(solution)
            applied += 1
            total += count
            errors.extend(solution_errors)
        if applied == 0:
            QMessageBox.information(self, "OpenECU Studio", "Aucune solution cochée.")
            return
        message = f"{applied} solution(s) appliquée(s) — {total} octet(s) modifié(s)."
        if errors:
            message += "\n\nErreurs :\n- " + "\n- ".join(errors)
        self._update_checksum_label()
        self.diffs_updated.emit(list(self.session.diffs))
        QMessageBox.information(self, "Patcher", message)

    # --------------------------------------------------------------------- DTC
    def _on_scan_dtcs(self) -> None:
        if not self.session.is_loaded:
            return
        try:
            self._dtc_entries = self.session.scan_dtcs()
        except PatchError as exc:
            QMessageBox.critical(self, "Erreur DTC", str(exc))
            return
        self._populate_dtc_table(self._dtc_entries)

    def _populate_dtc_table(self, entries: List[DtcEntry]) -> None:
        self.dtc_table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            offset_item = QTableWidgetItem(f"0x{entry.entry_offset:06X}")
            code_item = QTableWidgetItem(entry.code_str)
            table_item = QTableWidgetItem(entry.table_name)
            status_item = QTableWidgetItem(entry.status_text())
            switch_item = QTableWidgetItem(f"0x{entry.switch_value:02X} @ 0x{entry.switch_offset:06X}")
            if entry.active:
                status_item.setForeground(self.palette().brush(self.foregroundRole()))
            for column, item in enumerate((offset_item, code_item, table_item, status_item, switch_item)):
                self.dtc_table.setItem(row, column, item)
        self.dtc_count_label.setText(f"{len(entries)} DTC")

    def _filter_dtc_table(self, text: str) -> None:
        needle = text.strip().upper()
        if not needle:
            self._populate_dtc_table(self._dtc_entries)
            return
        filtered = [entry for entry in self._dtc_entries if needle in entry.code_str.upper()]
        self._populate_dtc_table(filtered)

    def _on_disable_selected(self) -> None:
        if not self.session.is_loaded:
            QMessageBox.information(self, "OpenECU Studio", "Chargez d'abord un fichier ECU.")
            return
        rows = sorted({index.row() for index in self.dtc_table.selectedIndexes()})
        if not rows:
            QMessageBox.information(self, "OpenECU Studio", "Sélectionnez au moins un DTC dans la liste.")
            return
        entries = [entry for row in rows if (entry := self._entry_at_row(row)) is not None]
        diffs = self.session.disable_dtc_entries(entries)
        self._on_scan_dtcs()
        self.dtc_search.setText(self.dtc_search.text())
        self._update_checksum_label()
        self.diffs_updated.emit(list(self.session.diffs))
        QMessageBox.information(
            self, "DTC Remover", f"{len(diffs)} octet(s) d'activation mis à 0x00."
        )

    def _entry_at_row(self, row: int) -> Optional[DtcEntry]:
        offset_item = self.dtc_table.item(row, 0)
        if offset_item is None:
            return None
        offset = int(offset_item.text(), 16)
        for entry in self._dtc_entries:
            if entry.entry_offset == offset:
                return entry
        return None

    # ------------------------------------------------------------------ export
    def _update_checksum_label(self) -> None:
        warnings = self.session.checksum_warnings()
        if not self.session.is_loaded:
            self.checksum_label.setText("")
            return
        if warnings:
            self.checksum_label.setText("⚠ " + " | ".join(warnings))
            self.checksum_label.setStyleSheet(f"color: {COLOR_ERROR};")
        else:
            self.checksum_label.setText("Checksums : OK")
            self.checksum_label.setStyleSheet(f"color: {COLOR_OK};")

    def _on_export(self) -> None:
        if not self.session.is_loaded:
            QMessageBox.information(self, "OpenECU Studio", "Chargez d'abord un fichier ECU.")
            return
        suggested = str(self.session.file_path.with_name(self.session.file_path.stem + "_patched.bin"))
        path, _ = QFileDialog.getSaveFileName(self, "Exporter le fichier patché", suggested, "Fichier binaire (*.bin)")
        if not path:
            return
        try:
            exported, warnings = self.session.export(Path(path))
        except (OSError, PatchError) as exc:
            QMessageBox.critical(self, "Erreur d'export", str(exc))
            return
        message = f"Fichier exporté :\n{exported}\n\n{len(self.session.diffs)} modification(s) appliquée(s)."
        if warnings:
            message += "\n\n⚠ AVERTISSEMENTS CHECKSUM :\n- " + "\n- ".join(warnings)
            QMessageBox.warning(self, "Export terminé", message)
        else:
            QMessageBox.information(self, "Export terminé", message)
