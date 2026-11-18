# -*- coding: utf-8 -*-
"""Worker générique : exécute une fonction dans un QThread sans geler l'UI."""
from __future__ import annotations

import logging
import traceback
from typing import Any, Callable

from PySide2.QtCore import QThread, Signal

logger = logging.getLogger(__name__)


class FunctionWorker(QThread):
    """Exécute ``fn(*args, **kwargs)`` en arrière-plan et émet le résultat."""

    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, fn: Callable[..., Any], *args: Any, parent: Any = None, **kwargs: Any) -> None:
        super().__init__(parent)
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self) -> None:
        try:
            result = self._fn(*self._args, **self._kwargs)
        except Exception as exc:  # noqa: BLE001 — remontée volontaire vers l'UI
            logger.error("Worker échoué : %s\n%s", exc, traceback.format_exc())
            self.failed.emit(f"{exc.__class__.__name__}: {exc}")
            return
        self.succeeded.emit(result)
