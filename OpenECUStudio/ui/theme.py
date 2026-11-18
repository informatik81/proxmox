# -*- coding: utf-8 -*-
"""Thèmes sombre et clair pour OpenECU Studio (PySide6 / Fusion).

Chaque thème est décrit par un objet ``ThemeColors`` : la feuille de style QSS
est générée depuis la palette, ce qui garantit un contraste cohérent (texte
toujours lisible) dans les deux modes. Le thème actif est le dernier passé à
``apply_theme`` ; il est consultable partout via ``current_theme()``.
"""
from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication


@dataclass(frozen=True)
class ThemeColors:
    name: str
    bg: str
    panel: str
    border: str
    text: str
    text_dim: str
    accent: str
    accent_text: str
    ok: str
    error: str
    console_bg: str
    input_bg: str
    button_bg: str
    button_hover: str
    button_pressed: str
    button_disabled: str
    header_bg: str
    alt_row: str
    handle: str
    disabled: str
    selection_text: str


DARK = ThemeColors(
    name="dark",
    bg="#121417",
    panel="#1b1f24",
    border="#2c333c",
    text="#d8dee7",
    text_dim="#8b95a3",
    accent="#e8a33d",
    accent_text="#14161a",
    ok="#5cbf60",
    error="#e05555",
    console_bg="#0d0f12",
    input_bg="#0d0f12",
    button_bg="#262c34",
    button_hover="#323a45",
    button_pressed="#1f242b",
    button_disabled="#1a1e23",
    header_bg="#22272e",
    alt_row="#14181d",
    handle="#333b45",
    disabled="#5a626d",
    selection_text="#14161a",
)

LIGHT = ThemeColors(
    name="light",
    bg="#f2f5f9",
    panel="#ffffff",
    border="#c4cedb",
    text="#1d2530",
    text_dim="#5b6675",
    accent="#b26a00",
    accent_text="#ffffff",
    ok="#1f7a2e",
    error="#c22525",
    console_bg="#ffffff",
    input_bg="#ffffff",
    button_bg="#e6ebf2",
    button_hover="#d9e1ec",
    button_pressed="#c9d3e0",
    button_disabled="#eef1f5",
    header_bg="#eaeef4",
    alt_row="#f6f8fb",
    handle="#aeb9c8",
    disabled="#98a3b1",
    selection_text="#ffffff",
)

THEMES: dict = {"dark": DARK, "light": LIGHT}

_current: ThemeColors = DARK


def current_theme() -> ThemeColors:
    """Palette du thème actuellement appliqué."""
    return _current


def theme_names() -> list:
    return list(THEMES)


def build_stylesheet(c: ThemeColors) -> str:
    """Génère la feuille de style complète depuis la palette du thème."""
    return f"""
QWidget {{
    background-color: {c.bg};
    color: {c.text};
    font-size: 10pt;
}}
QMainWindow, QDialog {{
    background-color: {c.bg};
}}
QGroupBox {{
    background-color: {c.panel};
    border: 1px solid {c.border};
    border-radius: 8px;
    margin-top: 14px;
    padding: 10px 8px 8px 8px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 5px;
    color: {c.accent};
    font-weight: bold;
    background-color: {c.bg};
}}
QTabWidget::pane {{
    border: 1px solid {c.border};
    background-color: {c.panel};
    border-radius: 6px;
}}
QTabBar::tab {{
    background-color: transparent;
    color: {c.text_dim};
    padding: 9px 20px;
    border: 1px solid transparent;
    border-bottom: 2px solid {c.border};
    margin-right: 4px;
}}
QTabBar::tab:hover {{
    color: {c.text};
    border-bottom-color: {c.accent};
}}
QTabBar::tab:selected {{
    background-color: {c.panel};
    color: {c.accent};
    border: 1px solid {c.border};
    border-bottom: 2px solid {c.accent};
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-weight: bold;
}}
QPushButton {{
    background-color: {c.button_bg};
    border: 1px solid {c.border};
    border-radius: 6px;
    padding: 7px 16px;
    color: {c.text};
    font-weight: 600;
}}
QPushButton:hover {{
    background-color: {c.button_hover};
    border-color: {c.accent};
}}
QPushButton:pressed {{
    background-color: {c.button_pressed};
}}
QPushButton:disabled {{
    color: {c.disabled};
    background-color: {c.button_disabled};
}}
QPushButton#primary {{
    background-color: {c.accent};
    color: {c.accent_text};
    font-weight: bold;
    border: none;
}}
QPushButton#danger {{
    background-color: {c.error};
    color: #ffffff;
    font-weight: bold;
    border: none;
}}
QLineEdit, QComboBox, QSpinBox {{
    background-color: {c.input_bg};
    border: 1px solid {c.border};
    border-radius: 6px;
    padding: 5px 8px;
    color: {c.text};
    selection-background-color: {c.accent};
    selection-color: {c.accent_text};
}}
QComboBox::drop-down {{
    border: none;
    width: 22px;
}}
QComboBox QAbstractItemView {{
    background-color: {c.panel};
    color: {c.text};
    border: 1px solid {c.border};
    selection-background-color: {c.accent};
    selection-color: {c.accent_text};
}}
QPlainTextEdit, QTextEdit {{
    background-color: {c.console_bg};
    border: 1px solid {c.border};
    border-radius: 6px;
    color: {c.text};
    font-family: 'Consolas';
    font-size: 9pt;
}}
QTableWidget {{
    background-color: {c.console_bg};
    alternate-background-color: {c.alt_row};
    gridline-color: {c.border};
    border: 1px solid {c.border};
    border-radius: 6px;
    font-family: 'Consolas';
    font-size: 9pt;
    color: {c.text};
}}
QHeaderView::section {{
    background-color: {c.header_bg};
    color: {c.text};
    border: none;
    border-right: 1px solid {c.border};
    border-bottom: 1px solid {c.border};
    padding: 6px;
    font-weight: bold;
}}
QListWidget {{
    background-color: {c.console_bg};
    border: 1px solid {c.border};
    border-radius: 6px;
    color: {c.text};
}}
QLabel#statusLabel {{
    color: {c.text_dim};
}}
QLabel#vbattValue {{
    font-family: 'Consolas';
    font-size: 26pt;
    font-weight: bold;
    color: {c.ok};
}}
QCheckBox {{
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {c.border};
    border-radius: 4px;
    background-color: {c.input_bg};
}}
QCheckBox::indicator:hover {{
    border-color: {c.accent};
}}
QCheckBox::indicator:checked {{
    background-color: {c.accent};
    border-color: {c.accent};
}}
QMenuBar {{
    background-color: {c.panel};
    color: {c.text};
    border-bottom: 1px solid {c.border};
}}
QMenuBar::item:selected {{
    background-color: {c.button_hover};
    border-radius: 4px;
}}
QMenu {{
    background-color: {c.panel};
    color: {c.text};
    border: 1px solid {c.border};
    border-radius: 6px;
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 24px 6px 12px;
    border-radius: 4px;
}}
QMenu::item:selected {{
    background-color: {c.accent};
    color: {c.accent_text};
}}
QToolTip {{
    background-color: {c.panel};
    color: {c.text};
    border: 1px solid {c.border};
    padding: 5px;
    font-size: 9pt;
}}
QStatusBar {{
    background-color: {c.panel};
    color: {c.text_dim};
    border-top: 1px solid {c.border};
}}
QScrollBar:vertical {{
    background: {c.bg};
    width: 12px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {c.handle};
    border-radius: 5px;
    min-height: 25px;
}}
QScrollBar::handle:vertical:hover {{
    background: {c.accent};
}}
QScrollBar:horizontal {{
    background: {c.bg};
    height: 12px;
    margin: 2px;
}}
QScrollBar::handle:horizontal {{
    background: {c.handle};
    border-radius: 5px;
    min-width: 25px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {c.accent};
}}
QScrollBar::add-line, QScrollBar::sub-line {{
    height: 0px;
    width: 0px;
}}
"""


def apply_theme(app: QApplication, theme_name: str = "dark") -> str:
    """Applique le style Fusion + palette + QSS pour le thème demandé.

    Retourne le nom du thème réellement appliqué (retombe sur « dark » si le
    nom est inconnu). ``current_theme()`` reflète le choix effectif.
    """
    global _current
    _current = THEMES.get(theme_name, DARK)
    colors = _current

    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(colors.bg))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(colors.text))
    palette.setColor(QPalette.ColorRole.Base, QColor(colors.input_bg))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(colors.alt_row))
    palette.setColor(QPalette.ColorRole.Text, QColor(colors.text))
    palette.setColor(QPalette.ColorRole.Button, QColor(colors.button_bg))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(colors.text))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(colors.accent))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(colors.accent_text))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(colors.panel))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(colors.text))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(colors.disabled))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(colors.disabled))
    app.setPalette(palette)
    app.setStyleSheet(build_stylesheet(colors))
    return colors.name


def apply_dark_theme(app: QApplication) -> None:
    """Rétro-compatibilité : applique le thème sombre."""
    apply_theme(app, "dark")


def mono_font(point_size: int = 9) -> QFont:
    """Police monospace (journal hexadécimal, tableaux)."""
    font = QFont("Consolas", point_size)
    font.setStyleHint(QFont.StyleHint.Monospace)
    return font
