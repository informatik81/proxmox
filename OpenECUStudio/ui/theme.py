# -*- coding: utf-8 -*-
"""Thème sombre « industriel » pour OpenECU Studio (PySide6 / Fusion)."""
from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication

COLOR_BG = "#121417"
COLOR_PANEL = "#1b1f24"
COLOR_BORDER = "#2c333c"
COLOR_TEXT = "#d8dee7"
COLOR_TEXT_DIM = "#8b95a3"
COLOR_ACCENT = "#e8a33d"
COLOR_OK = "#5cbf60"
COLOR_ERROR = "#e05555"
COLOR_CONSOLE_BG = "#0d0f12"

DARK_STYLESHEET = f"""
QWidget {{
    background-color: {COLOR_BG};
    color: {COLOR_TEXT};
    font-size: 10pt;
}}
QMainWindow, QDialog {{
    background-color: {COLOR_BG};
}}
QGroupBox {{
    background-color: {COLOR_PANEL};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    margin-top: 12px;
    padding: 8px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: {COLOR_ACCENT};
    font-weight: bold;
}}
QTabWidget::pane {{
    border: 1px solid {COLOR_BORDER};
    background-color: {COLOR_PANEL};
    border-radius: 4px;
}}
QTabBar::tab {{
    background-color: {COLOR_BG};
    color: {COLOR_TEXT_DIM};
    padding: 8px 18px;
    border: 1px solid {COLOR_BORDER};
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    margin-right: 3px;
}}
QTabBar::tab:selected {{
    background-color: {COLOR_PANEL};
    color: {COLOR_ACCENT};
    font-weight: bold;
}}
QPushButton {{
    background-color: #262c34;
    border: 1px solid {COLOR_BORDER};
    border-radius: 4px;
    padding: 6px 14px;
    color: {COLOR_TEXT};
}}
QPushButton:hover {{
    background-color: #323a45;
    border-color: {COLOR_ACCENT};
}}
QPushButton:pressed {{
    background-color: #1f242b;
}}
QPushButton:disabled {{
    color: #5a626d;
    background-color: #1a1e23;
}}
QPushButton#primary {{
    background-color: {COLOR_ACCENT};
    color: #14161a;
    font-weight: bold;
    border: none;
}}
QPushButton#primary:hover {{
    background-color: #f4b455;
}}
QPushButton#danger {{
    background-color: {COLOR_ERROR};
    color: #ffffff;
    font-weight: bold;
    border: none;
}}
QLineEdit, QComboBox, QSpinBox {{
    background-color: {COLOR_CONSOLE_BG};
    border: 1px solid {COLOR_BORDER};
    border-radius: 4px;
    padding: 4px 6px;
    color: {COLOR_TEXT};
    selection-background-color: {COLOR_ACCENT};
}}
QPlainTextEdit, QTextEdit {{
    background-color: {COLOR_CONSOLE_BG};
    border: 1px solid {COLOR_BORDER};
    border-radius: 4px;
    color: #9fd49f;
    font-family: 'Consolas';
    font-size: 9pt;
}}
QTableWidget {{
    background-color: {COLOR_CONSOLE_BG};
    alternate-background-color: #14181d;
    gridline-color: {COLOR_BORDER};
    border: 1px solid {COLOR_BORDER};
    border-radius: 4px;
    font-family: 'Consolas';
    font-size: 9pt;
}}
QHeaderView::section {{
    background-color: #22272e;
    color: {COLOR_ACCENT};
    border: none;
    border-right: 1px solid {COLOR_BORDER};
    border-bottom: 1px solid {COLOR_BORDER};
    padding: 5px;
    font-weight: bold;
}}
QListWidget {{
    background-color: {COLOR_CONSOLE_BG};
    border: 1px solid {COLOR_BORDER};
    border-radius: 4px;
}}
QLabel#statusLabel {{
    color: {COLOR_TEXT_DIM};
}}
QLabel#vbattValue {{
    font-family: 'Consolas';
    font-size: 26pt;
    font-weight: bold;
    color: {COLOR_OK};
}}
QCheckBox::indicator {{
    width: 15px;
    height: 15px;
    border: 1px solid {COLOR_BORDER};
    border-radius: 3px;
    background-color: {COLOR_CONSOLE_BG};
}}
QCheckBox::indicator:checked {{
    background-color: {COLOR_ACCENT};
}}
QStatusBar {{
    background-color: {COLOR_PANEL};
    color: {COLOR_TEXT_DIM};
    border-top: 1px solid {COLOR_BORDER};
}}
QScrollBar:vertical {{
    background: {COLOR_BG};
    width: 11px;
}}
QScrollBar::handle:vertical {{
    background: #333b45;
    border-radius: 5px;
    min-height: 25px;
}}
QScrollBar::add-line, QScrollBar::sub-line {{
    height: 0px;
}}
"""


def apply_dark_theme(app: QApplication) -> None:
    """Applique le style Fusion + palette sombre + feuille de style industrielle."""
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(COLOR_BG))
    palette.setColor(QPalette.WindowText, QColor(COLOR_TEXT))
    palette.setColor(QPalette.Base, QColor(COLOR_CONSOLE_BG))
    palette.setColor(QPalette.AlternateBase, QColor(COLOR_PANEL))
    palette.setColor(QPalette.Text, QColor(COLOR_TEXT))
    palette.setColor(QPalette.Button, QColor(COLOR_PANEL))
    palette.setColor(QPalette.ButtonText, QColor(COLOR_TEXT))
    palette.setColor(QPalette.Highlight, QColor(COLOR_ACCENT))
    palette.setColor(QPalette.HighlightedText, QColor("#14161a"))
    palette.setColor(QPalette.ToolTipBase, QColor(COLOR_PANEL))
    palette.setColor(QPalette.ToolTipText, QColor(COLOR_TEXT))
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor("#5a626d"))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor("#5a626d"))
    app.setPalette(palette)
    app.setStyleSheet(DARK_STYLESHEET)


def mono_font(point_size: int = 9) -> QFont:
    """Police monospace (journal hexadécimal, tableaux)."""
    font = QFont("Consolas", point_size)
    font.setStyleHint(QFont.Monospace)
    return font
