# -*- coding: utf-8 -*-
"""Onglet 4 : Gestionnaire de Définitions — import/édition des fichiers de règles JSON."""
from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSplitter,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt

from core.patch_engine import (
    DefinitionError,
    definitions_dir,
    list_definitions,
    load_definition,
    parse_definition,
    save_definition,
)
from ui.theme import COLOR_ERROR, COLOR_OK, mono_font

logger = logging.getLogger(__name__)

NEW_DEFINITION_TEMPLATE = """{
  "schema_version": 1,
  "definition_id": "nouveau_calculateur",
  "name": "Nouveau calculateur — modèle",
  "manufacturer": "Inconnu",
  "ecu_families": [],
  "match": {
    "id_patterns": [],
    "min_size": 0,
    "max_size": 8388608
  },
  "checksum": {
    "notes": "Décrivez ici l'état du checksum pour cette famille.",
    "regions": []
  },
  "solutions": [
    {
      "id": "exemple",
      "label": "Exemple de solution",
      "category": "antipollution",
      "description": "Décrivez la modification.",
      "patches": [
        {
          "name": "Signature exemple",
          "find": "48 8B ?? ?? 00 00 74 ??",
          "replace": "48 8B ?? ?? 00 00 EB ??",
          "description": "JZ remplacé par JMP."
        }
      ]
    }
  ],
  "dtc_tables": [
    {
      "name": "Table DTC principale",
      "entry_size": 4,
      "code_offset": 0,
      "switch_offset": 3,
      "byte_order": "big",
      "locator": null,
      "min_entries": 8
    }
  ],
  "notes": ""
}
"""


class DefinitionsTab(QWidget):
    """Import, édition et validation des définitions JSON (sans recompiler)."""

    definitions_changed = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._current_path: Optional[Path] = None
        self._build_ui()
        self._reload_list()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal)

        list_group = QGroupBox("Définitions installées")
        list_layout = QVBoxLayout(list_group)
        self.list_widget = QListWidget()
        self.list_widget.setFont(mono_font())
        self.list_widget.currentRowChanged.connect(self._on_select)
        list_layout.addWidget(self.list_widget)
        buttons_row = QHBoxLayout()
        reload_button = QPushButton("Recharger")
        reload_button.clicked.connect(self._reload_list)
        new_button = QPushButton("Nouveau (modèle)")
        new_button.clicked.connect(self._on_new)
        import_button = QPushButton("Importer un .json")
        import_button.clicked.connect(self._on_import)
        buttons_row.addWidget(reload_button)
        buttons_row.addWidget(new_button)
        buttons_row.addWidget(import_button)
        list_layout.addLayout(buttons_row)
        splitter.addWidget(list_group)

        editor_group = QGroupBox("Éditeur JSON (validé à l'enregistrement)")
        editor_layout = QVBoxLayout(editor_group)
        self.editor = QPlainTextEdit()
        self.editor.setFont(mono_font())
        editor_layout.addWidget(self.editor)
        self.validation_label = QLabel("")
        self.validation_label.setWordWrap(True)
        editor_layout.addWidget(self.validation_label)
        editor_buttons = QHBoxLayout()
        validate_button = QPushButton("Valider la syntaxe")
        validate_button.clicked.connect(self._on_validate)
        save_button = QPushButton("Enregistrer")
        save_button.setObjectName("primary")
        save_button.clicked.connect(self._on_save)
        editor_buttons.addWidget(validate_button)
        editor_buttons.addWidget(save_button)
        editor_layout.addLayout(editor_buttons)
        splitter.addWidget(editor_group)

        splitter.setSizes([320, 640])
        layout.addWidget(splitter)

        help_label = QLabel(
            "Astuce : les définitions sont des fichiers JSON dans le dossier 'definitions/' à côté de "
            "l'exécutable. Ajoutez-en de nouveaux pour supporter d'autres calculateurs sans recompiler."
        )
        help_label.setObjectName("statusLabel")
        help_label.setWordWrap(True)
        layout.addWidget(help_label)

    # ------------------------------------------------------------------ liste
    def _reload_list(self) -> None:
        self.list_widget.clear()
        for path in list_definitions(definitions_dir()):
            self.list_widget.addItem(path.name)
        if self.list_widget.count():
            self.list_widget.setCurrentRow(0)

    def _on_select(self, row: int) -> None:
        item = self.list_widget.item(row)
        if item is None:
            return
        path = definitions_dir() / item.text()
        try:
            self.editor.setPlainText(path.read_text(encoding="utf-8"))
            self._current_path = path
            self._set_validation(f"Chargé : {path.name}", ok=True)
        except OSError as exc:
            self._set_validation(f"Erreur de lecture : {exc}", ok=False)

    # ---------------------------------------------------------------- actions
    def _on_new(self) -> None:
        self.editor.setPlainText(NEW_DEFINITION_TEMPLATE)
        self._current_path = None
        self._set_validation("Nouvelle définition (non enregistrée) : renseignez definition_id.", ok=True)

    def _on_import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Importer une définition", "", "Définition JSON (*.json)")
        if not path:
            return
        target = definitions_dir() / Path(path).name
        try:
            load_definition(Path(path))
            definitions_dir().mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
        except (DefinitionError, OSError) as exc:
            QMessageBox.critical(self, "Import impossible", str(exc))
            return
        self._reload_list()
        self.definitions_changed.emit()
        QMessageBox.information(self, "Import", f"Définition importée : {target.name}")

    def _on_validate(self) -> None:
        try:
            definition = self._parse_editor()
        except (DefinitionError, json.JSONDecodeError) as exc:
            self._set_validation(f"✘ Invalide : {exc}", ok=False)
            return
        self._set_validation(
            f"✔ Valide : {definition.name} — {len(definition.solutions)} solution(s),"
            f" {len(definition.dtc_tables)} table(s) DTC.",
            ok=True,
        )

    def _on_save(self) -> None:
        try:
            definition = self._parse_editor()
        except (DefinitionError, json.JSONDecodeError) as exc:
            self._set_validation(f"✘ Enregistrement refusé : {exc}", ok=False)
            return
        target = self._current_path or definitions_dir() / f"{definition.definition_id}.json"
        try:
            definitions_dir().mkdir(parents=True, exist_ok=True)
            save_definition(definition, target)
        except OSError as exc:
            QMessageBox.critical(self, "Erreur d'écriture", str(exc))
            return
        self._current_path = target
        self._reload_list()
        self.definitions_changed.emit()
        self._set_validation(f"✔ Enregistré : {target}", ok=True)

    def _parse_editor(self):
        payload = json.loads(self.editor.toPlainText())
        return parse_definition(payload)

    def _set_validation(self, message: str, ok: bool) -> None:
        self.validation_label.setText(message)
        self.validation_label.setStyleSheet(f"color: {COLOR_OK};" if ok else f"color: {COLOR_ERROR};")
