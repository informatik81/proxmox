# -*- coding: utf-8 -*-
"""Onglet 1 : Diagnostic & SM2 Pro (J2534) — VBatt, UDS, DTC, console CAN."""
from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.j2534_driver import (
    BaseJ2534Device,
    CanFrame,
    J2534Device,
    MockJ2534Device,
    UdsClient,
    UdsNegativeResponseError,
    UdsTimeoutError,
    enumerate_j2534_interfaces,
)
from ui.workers import FunctionWorker

logger = logging.getLogger(__name__)


def decode_identifier(data: bytes) -> str:
    """Décode un identifiant UDS (ASCII prioritaire, sinon hexadécimal)."""
    if not data:
        return "-"
    try:
        return data.decode("ascii").strip("\x00").strip() or data.hex(" ").upper()
    except UnicodeDecodeError:
        return data.hex(" ").upper()


class DiagnosticsTab(QWidget):
    """Diagnostic temps réel via interface J2534 (SM2 Pro) ou mode simulation."""

    frame_logged = Signal(str)
    status_changed = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._device: Optional[BaseJ2534Device] = None
        self._uds: Optional[UdsClient] = None
        self._worker: Optional[FunctionWorker] = None
        self._build_ui()
        self._vbatt_timer = QTimer(self)
        self._vbatt_timer.setInterval(1000)
        self._vbatt_timer.timeout.connect(self._poll_vbatt)
        self.frame_logged.connect(self._append_frame)
        self.status_changed.connect(self._set_status)
        self._refresh_interfaces()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        interface_group = QGroupBox("Interface J2534 (SAE PassThru 04.04)")
        interface_layout = QHBoxLayout(interface_group)
        self.interface_combo = QComboBox()
        self.interface_combo.setMinimumWidth(320)
        refresh_button = QPushButton("Rafraîchir")
        refresh_button.clicked.connect(self._refresh_interfaces)
        self.connect_button = QPushButton("Se connecter")
        self.connect_button.setObjectName("primary")
        self.connect_button.clicked.connect(self._connect)
        self.disconnect_button = QPushButton("Déconnecter")
        self.disconnect_button.setEnabled(False)
        self.disconnect_button.clicked.connect(self._disconnect)
        interface_layout.addWidget(QLabel("Interface :"))
        interface_layout.addWidget(self.interface_combo, 1)
        interface_layout.addWidget(refresh_button)
        interface_layout.addWidget(self.connect_button)
        interface_layout.addWidget(self.disconnect_button)
        layout.addWidget(interface_group)

        middle_layout = QHBoxLayout()

        vbatt_group = QGroupBox("Tension batterie (VBatt — pin 16)")
        vbatt_layout = QVBoxLayout(vbatt_group)
        self.vbatt_label = QLabel("--.-- V")
        self.vbatt_label.setObjectName("vbattValue")
        self.vbatt_label.setAlignment(Qt.AlignCenter)
        self.vbatt_status = QLabel("Non connecté")
        self.vbatt_status.setObjectName("statusLabel")
        self.vbatt_status.setAlignment(Qt.AlignCenter)
        vbatt_layout.addWidget(self.vbatt_label)
        vbatt_layout.addWidget(self.vbatt_status)
        middle_layout.addWidget(vbatt_group, 1)

        uds_group = QGroupBox("Diagnostic UDS (ISO 14229 — CAN 500 kbps, 0x7E0/0x7E8)")
        uds_layout = QVBoxLayout(uds_group)
        identify_button = QPushButton("Identifier ECU (UDS)")
        identify_button.setObjectName("primary")
        identify_button.clicked.connect(self._identify_ecu)
        session_button = QPushButton("Session étendue (10 03)")
        session_button.clicked.connect(self._enter_extended_session)
        read_dtc_button = QPushButton("Lire les DTC (19 02 FF)")
        read_dtc_button.clicked.connect(self._read_dtcs)
        clear_dtc_button = QPushButton("Effacer les DTC (14 FF FF FF)")
        clear_dtc_button.setObjectName("danger")
        clear_dtc_button.clicked.connect(self._clear_dtcs)
        uds_layout.addWidget(identify_button)
        uds_layout.addWidget(session_button)
        uds_layout.addWidget(read_dtc_button)
        uds_layout.addWidget(clear_dtc_button)
        self.uds_result = QTextEdit()
        self.uds_result.setReadOnly(True)
        self.uds_result.setMinimumHeight(150)
        uds_layout.addWidget(self.uds_result)
        middle_layout.addWidget(uds_group, 2)

        layout.addLayout(middle_layout)

        console_group = QGroupBox("Console trames CAN / UDS brutes")
        console_layout = QVBoxLayout(console_group)
        self.console = QPlainTextEdit()
        self.console.setReadOnly(True)
        self.console.setMaximumBlockCount(5000)
        console_layout.addWidget(self.console)
        clear_console_button = QPushButton("Effacer la console")
        clear_console_button.clicked.connect(self.console.clear)
        console_layout.addWidget(clear_console_button)
        layout.addWidget(console_group, 1)

        self.status_label = QLabel("Aucune interface connectée.")
        self.status_label.setObjectName("statusLabel")
        layout.addWidget(self.status_label)

    # ------------------------------------------------------------ interfaces
    def _refresh_interfaces(self) -> None:
        self.interface_combo.clear()
        for info in enumerate_j2534_interfaces():
            self.interface_combo.addItem(f"{info.name}  [{info.dll_path}]", info)
        self.interface_combo.addItem("Simulation / Mock J2534 (sans matériel)", "mock")
        if self.interface_combo.count() > 1:
            # Priorité Scanmatik si présente (la liste est déjà triée pour)
            for index in range(self.interface_combo.count()):
                data = self.interface_combo.itemData(index)
                if isinstance(data, str) and data == "mock":
                    continue
                self.interface_combo.setCurrentIndex(index)
                break

    # ------------------------------------------------------------- connexion
    def _connect(self) -> None:
        if self._device is not None:
            return
        selection = self.interface_combo.currentData()
        if selection is None:
            QMessageBox.warning(self, "OpenECU Studio", "Aucune interface sélectionnée.")
            return
        try:
            device: BaseJ2534Device = (
                MockJ2534Device() if selection == "mock" else J2534Device(selection)
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(
                self,
                "Erreur J2534",
                f"Impossible de charger la DLL PassThru :\n{exc}\n\n"
                "Rappel : la DLL Scanmatik est 32 bits — utilisez Python 32 bits.",
            )
            return
        device.add_frame_listener(self._on_frame)
        self._worker = FunctionWorker(self._connect_job, device, self)
        self._worker.succeeded.connect(self._on_connected)
        self._worker.failed.connect(self._on_connect_failed)
        self._worker.start()

    @staticmethod
    def _connect_job(device: BaseJ2534Device) -> BaseJ2534Device:
        device.open()
        device.connect_can(500000, extended=False)
        return device

    def _on_connected(self, device: BaseJ2534Device) -> None:
        self._device = device
        self._uds = device.create_uds_client()
        self.connect_button.setEnabled(False)
        self.disconnect_button.setEnabled(True)
        self._vbatt_timer.start()
        self.status_changed.emit(f"Connecté : {device.name}")
        self._log(f"=== Connecté à : {device.name} ===")

    def _on_connect_failed(self, message: str) -> None:
        QMessageBox.critical(self, "Erreur de connexion J2534", message)
        self.status_changed.emit("Échec de connexion.")

    def _disconnect(self) -> None:
        self._vbatt_timer.stop()
        if self._device is not None:
            try:
                self._device.disconnect()
                self._device.close()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Déconnexion : %s", exc)
            self._device = None
            self._uds = None
        self.connect_button.setEnabled(True)
        self.disconnect_button.setEnabled(False)
        self.vbatt_label.setText("--.-- V")
        self.vbatt_status.setText("Non connecté")
        self.status_changed.emit("Déconnecté.")
        self._log("=== Déconnecté ===")

    # ----------------------------------------------------------------- VBatt
    def _poll_vbatt(self) -> None:
        if self._device is None or not self._device.is_connected:
            return
        try:
            volts = self._device.read_vbatt()
        except Exception as exc:  # noqa: BLE001
            self.vbatt_status.setText(f"Erreur VBatt : {exc}")
            return
        self.vbatt_label.setText(f"{volts:5.2f} V")
        color = "#5cbf60" if volts >= 11.5 else "#e05555"
        self.vbatt_label.setStyleSheet(f"color: {color};")
        self.vbatt_status.setText("Lecture temps réel (1 Hz)")

    # ------------------------------------------------------------------- UDS
    def _enter_extended_session(self) -> None:
        self._run_uds_job(
            lambda uds: uds.diagnostic_session_control(0x03),
            "Session étendue (10 03)",
        )

    def _identify_ecu(self) -> None:
        def job(uds: UdsClient) -> dict:
            uds.diagnostic_session_control(0x03)
            return {
                "VIN (F190)": decode_identifier(uds.read_data_by_identifier(0xF190)),
                "N° Hardware (F191)": decode_identifier(uds.read_data_by_identifier(0xF191)),
                "N° Software (F195)": decode_identifier(uds.read_data_by_identifier(0xF195)),
            }

        self._run_uds_job(job, "Identification ECU", format_dict=True)

    def _read_dtcs(self) -> None:
        def job(uds: UdsClient) -> list:
            return uds.read_dtc_by_status_mask(0xFF)

        def render(dtcs: list) -> str:
            if not dtcs:
                return "Aucun DTC présent (mémoire propre)."
            letters = "PCBU"
            lines = [f"{len(dtcs)} DTC(s) en mémoire :"]
            for code, status in dtcs:
                letter = letters[(code >> 14) & 0x03]
                code_str = f"{letter}{code & 0x3FFF:04X}"
                lines.append(f"  • {code_str}  (brut 0x{code:04X}) — statut 0x{status:02X}")
            return "\n".join(lines)

        self._run_uds_job(job, "Lecture DTC", render=render)

    def _clear_dtcs(self) -> None:
        def job(uds: UdsClient) -> str:
            uds.clear_dtc(0xFFFFFF)
            remaining = uds.read_dtc_by_status_mask(0xFF)
            return f"DTC effacés. {len(remaining)} code(s) restant(s)."

        self._run_uds_job(job, "Effacement DTC")

    def _run_uds_job(self, job: object, label: str, format_dict: bool = False, render: object = None) -> None:
        if self._uds is None:
            QMessageBox.information(self, "OpenECU Studio", "Connectez d'abord une interface.")
            return
        uds = self._uds
        worker = FunctionWorker(lambda: job(uds), self)  # type: ignore[operator]
        worker.succeeded.connect(lambda result, l=label: self._on_uds_result(l, result, format_dict, render))
        worker.failed.connect(self._on_uds_error)
        self._worker = worker
        self.status_changed.emit(f"{label} en cours...")
        worker.start()

    def _on_uds_result(self, label: str, result: object, format_dict: bool, render: object) -> None:
        if format_dict and isinstance(result, dict):
            text = "\n".join(f"{key} : {value}" for key, value in result.items())
        elif render is not None:
            text = str(render(result))
        elif isinstance(result, bytes):
            text = result.hex(" ").upper()
        else:
            text = str(result)
        self.uds_result.setPlainText(f"--- {label} ---\n{text}")
        self.status_changed.emit(f"{label} : terminé.")

    def _on_uds_error(self, message: str) -> None:
        if "0x78" in message:
            self.uds_result.setPlainText(f"ECU occupé (responsePending) : réessayez.\n{message}")
        elif isinstance(message, str) and ("UdsNegativeResponseError" in message or "UdsTimeoutError" in message):
            self.uds_result.setPlainText(f"Échec UDS : {message}")
        else:
            self.uds_result.setPlainText(f"Erreur : {message}")
        self.status_changed.emit("Erreur UDS.")

    # --------------------------------------------------------------- console
    def _on_frame(self, frame: CanFrame) -> None:
        self.frame_logged.emit(frame.format())

    def _append_frame(self, text: str) -> None:
        self.console.appendPlainText(text)

    def _log(self, message: str) -> None:
        self.console.appendPlainText(message)

    def _set_status(self, message: str) -> None:
        self.status_label.setText(message)
