# -*- coding: utf-8 -*-
"""OpenECU Studio — point d'entrée de l'application.

Initialise le journal (logs/ + console), installe un gestionnaire global
d'exceptions, applique le thème sombre puis lance la fenêtre principale.
"""
from __future__ import annotations

import logging
import sys
import traceback
from pathlib import Path

APP_NAME = "OpenECU Studio"


def setup_logging() -> Path:
    """Configure le journal : fichier horodaté + sortie console."""
    base_dir = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
    logs_dir = base_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / f"opencu_studio_{__import__('time').strftime('%Y%m%d_%H%M%S')}.log"

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)-7s] %(name)s : %(message)s", "%Y-%m-%d %H:%M:%S"
    )
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)
    logging.getLogger("PySide6").setLevel(logging.WARNING)
    return log_file


def install_excepthook() -> None:
    """Journalise toute exception non gérée et affiche une boîte de dialogue."""

    def handle(exc_type, exc_value, exc_tb) -> None:
        text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        logging.getLogger(APP_NAME).critical("Exception non gérée :\n%s", text)
        try:
            from PySide6.QtWidgets import QApplication, QMessageBox

            if QApplication.instance() is not None:
                QMessageBox.critical(
                    None,
                    f"{APP_NAME} — erreur fatale",
                    f"Une erreur inattendue s'est produite :\n\n{exc_value}\n\n"
                    f"Le détail complet a été écrit dans le journal (dossier logs/).",
                )
        except Exception:  # pragma: no cover — l'UI peut elle-même être cassée
            pass
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = handle


def main() -> int:
    log_file = setup_logging()
    logging.getLogger(APP_NAME).info("Démarrage — journal : %s", log_file)
    install_excepthook()

    from PySide6.QtWidgets import QApplication

    from core import settings as app_settings
    from ui.main_window import MainWindow
    from ui.theme import apply_theme

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    theme_name = str(app_settings.load_settings().get("theme", "dark"))
    applied = apply_theme(app, theme_name)
    logging.getLogger(APP_NAME).info("Thème appliqué : %s", applied)
    window = MainWindow()
    window.show()
    logging.getLogger(APP_NAME).info("Interface affichée. Boucle d'événements Qt démarrée.")
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
