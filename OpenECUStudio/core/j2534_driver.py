# -*- coding: utf-8 -*-
"""Couche communication SAE J2534-1 (PassThru) + ISO-TP (ISO 15765-2) + UDS (ISO 14229).

IMPORTANT — COMPATIBILITÉ WINDOWS 32 BITS :
La DLL PassThru officielle Scanmatik (``smj2534.dll``) est une bibliothèque
**32 bits**, enregistrée sous
``HKLM\\SOFTWARE\\WOW6432Node\\PassThruSupport.04.04``.
Ce module doit donc impérativement être exécuté sous un interpréteur
**Python 32 bits** (x86). Sous Python 64 bits, ``ctypes.WinDLL`` lèvera :
``OSError: [WinError 193] %1 n'est pas une application Win32 valide``.

Un mode **Simulation (Mock J2534)** permet d'utiliser l'application sans
aucun matériel : les réponses UDS d'un EDC17C10 simulé sont générées
localement pour tester l'interface et les requêtes de diagnostic.
"""
from __future__ import annotations

import ctypes
import logging
import os
import random
import struct
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

IS_WINDOWS = os.name == "nt"
if IS_WINDOWS:
    import winreg  # noqa: F401  (importé ici pour centraliser la dépendance Windows)


# ==========================================================================
# Constantes SAE J2534-1
# ==========================================================================
STATUS_NOERROR = 0x0000

STATUS_MESSAGES: Dict[int, str] = {
    0x00: "STATUS_NOERROR",
    0x01: "ERR_NOT_SUPPORTED",
    0x02: "ERR_INVALID_CHANNEL_ID",
    0x03: "ERR_INVALID_PROTOCOL_ID",
    0x04: "ERR_NULL_PARAMETER",
    0x05: "ERR_INVALID_IOCTL_ID",
    0x06: "ERR_INVALID_FLAGS",
    0x07: "ERR_FAILED",
    0x08: "ERR_DEVICE_NOT_CONNECTED",
    0x09: "ERR_TIMEOUT",
    0x0A: "ERR_INVALID_MSG",
    0x0B: "ERR_INVALID_TIME_INTERVAL",
    0x0C: "ERR_EXCEEDED_LIMIT",
    0x0D: "ERR_INVALID_MSG_ID",
    0x0E: "ERR_DEVICE_IN_USE",
    0x0F: "ERR_INVALID_IOCTL_VALUE",
    0x10: "ERR_PIN_INVALID",
    0x11: "ERR_CHANNEL_IN_USE",
    0x12: "ERR_MSG_PROTOCOL_ID",
    0x13: "ERR_INVALID_FILTER_ID",
    0x14: "ERR_NO_FLOW_CONTROL",
    0x15: "ERR_NOT_UNIQUE",
    0x16: "ERR_INVALID_BAUDRATE",
    0x17: "ERR_INVALID_PIN",
}

# Protocoles
PROTOCOL_CAN = 0x05
PROTOCOL_ISO15765 = 0x06

# Connect flags
FLAG_CAN_29BIT_ID = 0x0100

# TxFlags / RxStatus
TXFLAG_ISO15765_ADDR_TYPE = 0x0080
TXFLAG_ISO15765_FRAME_PAD = 0x0040
RXSTATUS_START_OF_MESSAGE = 0x0002
RXSTATUS_TX_MSG_TYPE = 0x0100

# Types de filtres
PASS_FILTER = 0x01
BLOCK_FILTER = 0x02
FLOW_CONTROL_FILTER = 0x03

# IOCTL
IOCTL_SET_CONFIG = 0x01
IOCTL_GET_CONFIG = 0x02
IOCTL_READ_VBATT = 0x03
IOCTL_CLEAR_TX_BUFFER = 0x08
IOCTL_CLEAR_RX_BUFFER = 0x09

# Paramètres de configuration (SCONFIG)
CONFIG_DATA_RATE = 0x01
CONFIG_LOOPBACK = 0x03
CONFIG_ISO15765_WFT_MAX = 0x21

MAX_MSG_DATA_SIZE = 4128
RX_QUEUE_SIZE = 64

DEFAULT_CAN_BAUDRATE = 500000
DEFAULT_TX_ID = 0x7E0
DEFAULT_RX_ID = 0x7E8


# ==========================================================================
# Structures ctypes (ABI Win32)
# ==========================================================================
class PASSTHRU_MSG(ctypes.Structure):
    """Structure PASSTHRU_MSG de l'API SAE J2534-1 (ISO 22900-2)."""

    _fields_ = [
        ("ProtocolID", ctypes.c_ulong),
        ("RxStatus", ctypes.c_ulong),
        ("TxFlags", ctypes.c_ulong),
        ("Timestamp", ctypes.c_ulong),
        ("DataSize", ctypes.c_ulong),
        ("ExtraDataIndex", ctypes.c_ulong),
        ("Data", ctypes.c_ubyte * MAX_MSG_DATA_SIZE),
    ]


class SCONFIG(ctypes.Structure):
    """Paire paramètre/valeur pour PassThruIoctl (GET_CONFIG / SET_CONFIG)."""

    _fields_ = [
        ("Parameter", ctypes.c_ulong),
        ("Value", ctypes.c_ulong),
    ]


class SCONFIG_LIST(ctypes.Structure):
    """Liste de SCONFIG passée à PassThruIoctl pour GET/SET_CONFIG."""

    _fields_ = [
        ("NumOfArgs", ctypes.c_ulong),
        ("ConfigPtr", ctypes.POINTER(SCONFIG)),
    ]


# ==========================================================================
# Exceptions
# ==========================================================================
class J2534Error(Exception):
    """Erreur générique de l'API J2534."""

    def __init__(self, function: str, status: int) -> None:
        text = STATUS_MESSAGES.get(status, f"ERREUR_INCONNUE_0x{status:02X}")
        super().__init__(f"{function} a échoué : {text} (0x{status:02X})")
        self.function = function
        self.status = status


class UdsNegativeResponseError(Exception):
    """Réponse négative UDS (0x7F SID NRC)."""

    NRC_NAMES: Dict[int, str] = {
        0x10: "generalReject",
        0x11: "serviceNotSupported",
        0x12: "subFunctionNotSupported",
        0x13: "incorrectMessageLengthOrInvalidFormat",
        0x14: "responseTooLong",
        0x21: "busyRepeatRequest",
        0x22: "conditionsNotCorrect",
        0x24: "requestSequenceError",
        0x31: "requestOutOfRange",
        0x33: "securityAccessDenied",
        0x35: "invalidKey",
        0x36: "exceedNumberOfAttempts",
        0x37: "requiredTimeDelayNotExpired",
        0x72: "generalProgrammingFailure",
        0x78: "requestCorrectlyReceived-ResponsePending",
        0x7E: "subFunctionNotSupportedInActiveSession",
        0x7F: "serviceNotSupportedInActiveSession",
    }

    def __init__(self, sid: int, nrc: int) -> None:
        name = self.NRC_NAMES.get(nrc, f"NRC_0x{nrc:02X}")
        super().__init__(
            f"Réponse négative UDS : SID 0x{sid:02X}, NRC 0x{nrc:02X} ({name})"
        )
        self.sid = sid
        self.nrc = nrc


class UdsTimeoutError(Exception):
    """Aucune réponse UDS reçue avant l'échéance."""


# ==========================================================================
# Énumération des interfaces PassThru (registre Windows)
# ==========================================================================
@dataclass
class J2534InterfaceInfo:
    """Interface J2534 détectée dans le registre Windows."""

    name: str
    dll_path: str
    vendor: str = ""
    registry_key: str = ""


def enumerate_j2534_interfaces() -> List[J2534InterfaceInfo]:
    """Énumère toutes les interfaces PassThru 04.04 installées.

    Les clés sont lues en priorité dans ``WOW6432Node`` (DLL 32 bits) puis
    dans la vue native. Les interfaces dont le nom contient ``SM2`` ou
    ``Scanmatik`` sont placées en tête de liste.
    """
    interfaces: List[J2534InterfaceInfo] = []
    if not IS_WINDOWS:
        logger.info("Énumération J2534 ignorée : système non-Windows.")
        return interfaces

    roots = (
        r"SOFTWARE\WOW6432Node\PassThruSupport.04.04",
        r"SOFTWARE\PassThruSupport.04.04",
    )
    seen: set = set()
    for root in roots:
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, root)
        except OSError:
            continue
        with key:
            index = 0
            while True:
                try:
                    device_name = winreg.EnumKey(key, index)
                    index += 1
                except OSError:
                    break
                if device_name in seen:
                    continue
                seen.add(device_name)
                try:
                    subkey = winreg.OpenKey(key, device_name)
                except OSError:
                    continue
                with subkey:
                    dll_path = ""
                    vendor = ""
                    try:
                        dll_path = winreg.QueryValueEx(subkey, "FunctionType")[0]
                    except OSError:
                        pass
                    try:
                        vendor = winreg.QueryValueEx(subkey, "Vendor")[0]
                    except OSError:
                        pass
                    if not dll_path:
                        # Repli : chercher une valeur REG_SZ pointant vers une .dll
                        value_index = 0
                        while True:
                            try:
                                value_name, value_data, _ = winreg.EnumValue(subkey, value_index)
                                value_index += 1
                            except OSError:
                                break
                            if (
                                isinstance(value_data, str)
                                and value_data.lower().endswith(".dll")
                                and os.path.exists(value_data)
                            ):
                                dll_path = value_data
                                break
                    if dll_path:
                        interfaces.append(
                            J2534InterfaceInfo(
                                name=device_name,
                                dll_path=dll_path,
                                vendor=vendor,
                                registry_key=f"HKLM\\{root}\\{device_name}",
                            )
                        )
                        logger.info(
                            "Interface J2534 détectée : %s (%s)", device_name, dll_path
                        )

    interfaces.sort(key=lambda info: (0 if _is_scanmatik(info) else 1, info.name.lower()))
    return interfaces


def _is_scanmatik(info: J2534InterfaceInfo) -> bool:
    haystack = f"{info.name} {info.vendor} {info.dll_path}".lower()
    return "sm2" in haystack or "scanmatik" in haystack


# ==========================================================================
# Trames CAN
# ==========================================================================
@dataclass
class CanFrame:
    """Trame CAN (avec identifiant arbitré et payload ISO-TP brut)."""

    direction: str  # "TX" ou "RX"
    arb_id: int
    data: bytes
    is_extended: bool = False
    timestamp: float = 0.0

    def format(self) -> str:
        ident = f"{self.arb_id:08X}" if self.is_extended else f"{self.arb_id:03X}"
        payload = " ".join(f"{byte:02X}" for byte in self.data)
        ts = time.strftime("%H:%M:%S", time.localtime(self.timestamp or time.time()))
        return f"[{ts}] {self.direction} ID=0x{ident} [{len(self.data):02d}] {payload}"


FrameListener = Callable[[CanFrame], None]


# ==========================================================================
# Classe de base (matériel réel ou mock)
# ==========================================================================
class BaseJ2534Device(ABC):
    """Interface commune : matériel J2534 réel ou simulation."""

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def open(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def connect_can(self, baudrate: int = DEFAULT_CAN_BAUDRATE, extended: bool = False) -> None:
        raise NotImplementedError

    @abstractmethod
    def disconnect(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def read_vbatt(self) -> float:
        raise NotImplementedError

    @abstractmethod
    def send_can(self, arb_id: int, payload: bytes, extended: bool = False) -> None:
        raise NotImplementedError

    @abstractmethod
    def read_msgs(self, timeout_ms: float = 50) -> List[CanFrame]:
        raise NotImplementedError

    @abstractmethod
    def start_flow_control_filter(self, rx_id: int, fc_tx_id: int, extended: bool = False) -> None:
        raise NotImplementedError

    @abstractmethod
    def clear_rx_buffer(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def create_uds_client(
        self, tx_id: int = DEFAULT_TX_ID, rx_id: int = DEFAULT_RX_ID, extended: bool = False
    ) -> "UdsClient":
        raise NotImplementedError

    def add_frame_listener(self, listener: FrameListener) -> None:
        self._listeners.append(listener)  # type: ignore[attr-defined]

    def remove_frame_listener(self, listener: FrameListener) -> None:
        if listener in getattr(self, "_listeners", []):  # type: ignore[attr-defined]
            self._listeners.remove(listener)  # type: ignore[attr-defined]


# ==========================================================================
# Périphérique J2534 réel (ctypes / WinDLL)
# ==========================================================================
class J2534Device(BaseJ2534Device):
    """Wrapper ctypes autour d'une DLL PassThru J2534-1 (ex. smj2534.dll)."""

    def __init__(self, info: J2534InterfaceInfo) -> None:
        if not IS_WINDOWS:
            raise RuntimeError("J2534Device requiert Windows (DLL PassThru 32 bits).")
        self._info = info
        self._dll = ctypes.WinDLL(info.dll_path)
        self._device_id: Optional[int] = None
        self._channel_id: Optional[int] = None
        self._protocol: int = PROTOCOL_ISO15765
        self._extended: bool = False
        self._lock = threading.Lock()
        self._listeners: List[FrameListener] = []
        self._configure_prototypes()

    # -- configuration des prototypes --------------------------------------
    def _configure_prototypes(self) -> None:
        dll = self._dll
        c_ulong_p = ctypes.POINTER(ctypes.c_ulong)
        msg_p = ctypes.POINTER(PASSTHRU_MSG)

        dll.PassThruOpen.argtypes = [ctypes.c_char_p, c_ulong_p]
        dll.PassThruOpen.restype = ctypes.c_long
        dll.PassThruClose.argtypes = [ctypes.c_ulong]
        dll.PassThruClose.restype = ctypes.c_long
        dll.PassThruConnect.argtypes = [ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, c_ulong_p]
        dll.PassThruConnect.restype = ctypes.c_long
        dll.PassThruDisconnect.argtypes = [ctypes.c_ulong]
        dll.PassThruDisconnect.restype = ctypes.c_long
        dll.PassThruReadMsgs.argtypes = [ctypes.c_ulong, msg_p, c_ulong_p, ctypes.c_ulong]
        dll.PassThruReadMsgs.restype = ctypes.c_long
        dll.PassThruWriteMsgs.argtypes = [ctypes.c_ulong, msg_p, c_ulong_p, ctypes.c_ulong]
        dll.PassThruWriteMsgs.restype = ctypes.c_long
        dll.PassThruStartMsgFilter.argtypes = [
            ctypes.c_ulong,
            ctypes.c_ulong,
            msg_p,
            msg_p,
            msg_p,
            c_ulong_p,
        ]
        dll.PassThruStartMsgFilter.restype = ctypes.c_long
        dll.PassThruStopMsgFilter.argtypes = [ctypes.c_ulong, ctypes.c_ulong]
        dll.PassThruStopMsgFilter.restype = ctypes.c_long
        dll.PassThruIoctl.argtypes = [ctypes.c_ulong, ctypes.c_ulong, ctypes.c_void_p, ctypes.c_void_p]
        dll.PassThruIoctl.restype = ctypes.c_long
        dll.PassThruGetLastError.argtypes = [ctypes.c_char_p]
        dll.PassThruGetLastError.restype = ctypes.c_long

    # -- utilitaires --------------------------------------------------------
    def _check(self, status: int, function: str) -> None:
        if status != STATUS_NOERROR:
            if function == "PassThruReadMsgs" and status == 0x09:
                return  # ERR_TIMEOUT : lecture sans message = comportement normal
            raise J2534Error(function, status)

    def _last_error_text(self) -> str:
        buffer = ctypes.create_string_buffer(256)
        try:
            self._dll.PassThruGetLastError(buffer)
            return buffer.value.decode("mbcs", errors="replace")
        except Exception:  # pragma: no cover - défensif
            return "?"

    @staticmethod
    def _make_msg(protocol: int, tx_flags: int, data: bytes) -> PASSTHRU_MSG:
        if len(data) > MAX_MSG_DATA_SIZE:
            raise ValueError(f"Trame trop longue : {len(data)} octets (max {MAX_MSG_DATA_SIZE}).")
        msg = PASSTHRU_MSG()
        msg.ProtocolID = protocol
        msg.RxStatus = 0
        msg.TxFlags = tx_flags
        msg.Timestamp = 0
        msg.DataSize = len(data)
        msg.ExtraDataIndex = 0
        for index, byte in enumerate(data):
            msg.Data[index] = byte
        return msg

    @staticmethod
    def _id_bytes(arb_id: int, extended: bool) -> bytes:
        if extended:
            return arb_id.to_bytes(4, byteorder="big")
        return arb_id.to_bytes(3, byteorder="big")

    # -- cycle de vie --------------------------------------------------------
    @property
    def name(self) -> str:
        return self._info.name

    @property
    def is_connected(self) -> bool:
        return self._channel_id is not None

    def open(self) -> None:
        name_buffer = self._info.name.encode("mbcs") + b"\x00"
        device_id = ctypes.c_ulong(0xFFFFFFFF)
        status = self._dll.PassThruOpen(name_buffer, ctypes.byref(device_id))
        self._check(status, "PassThruOpen")
        self._device_id = device_id.value
        logger.info("PassThruOpen OK : %s (DeviceID=0x%X)", self._info.name, self._device_id)

    def close(self) -> None:
        if self._device_id is not None:
            status = self._dll.PassThruClose(ctypes.c_ulong(self._device_id))
            self._device_id = None
            self._check(status, "PassThruClose")
            logger.info("PassThruClose OK")

    def connect_can(self, baudrate: int = DEFAULT_CAN_BAUDRATE, extended: bool = False) -> None:
        if self._device_id is None:
            raise J2534Error("PassThruConnect", 0x08)
        flags = FLAG_CAN_29BIT_ID if extended else 0
        channel_id = ctypes.c_ulong(0xFFFFFFFF)
        status = self._dll.PassThruConnect(
            ctypes.c_ulong(self._device_id),
            ctypes.c_ulong(PROTOCOL_ISO15765),
            ctypes.c_ulong(flags),
            ctypes.c_ulong(baudrate),
            ctypes.byref(channel_id),
        )
        self._check(status, "PassThruConnect")
        self._channel_id = channel_id.value
        self._extended = extended
        logger.info(
            "PassThruConnect OK : ISO15765 @ %d bauds (ChannelID=0x%X, 29 bits=%s)",
            baudrate,
            self._channel_id,
            extended,
        )
        self._set_config(CONFIG_LOOPBACK, 0)
        self._set_config(CONFIG_ISO15765_WFT_MAX, 4)

    def disconnect(self) -> None:
        if self._channel_id is not None:
            status = self._dll.PassThruDisconnect(ctypes.c_ulong(self._channel_id))
            self._channel_id = None
            self._check(status, "PassThruDisconnect")
            logger.info("PassThruDisconnect OK")

    # -- configuration / IOCTL ------------------------------------------------
    def _set_config(self, parameter: int, value: int) -> None:
        if self._channel_id is None:
            return
        config = SCONFIG(Parameter=parameter, Value=value)
        config_list = SCONFIG_LIST(NumOfArgs=1, ConfigPtr=ctypes.pointer(config))
        status = self._dll.PassThruIoctl(
            ctypes.c_ulong(self._channel_id),
            ctypes.c_ulong(IOCTL_SET_CONFIG),
            ctypes.byref(config_list),
            None,
        )
        self._check(status, "PassThruIoctl(SET_CONFIG)")

    def _get_config(self, parameter: int) -> int:
        if self._channel_id is None:
            raise J2534Error("PassThruIoctl(GET_CONFIG)", 0x08)
        config = SCONFIG(Parameter=parameter, Value=0)
        config_list = SCONFIG_LIST(NumOfArgs=1, ConfigPtr=ctypes.pointer(config))
        status = self._dll.PassThruIoctl(
            ctypes.c_ulong(self._channel_id),
            ctypes.c_ulong(IOCTL_GET_CONFIG),
            ctypes.byref(config_list),
            ctypes.byref(config_list),
        )
        self._check(status, "PassThruIoctl(GET_CONFIG)")
        return config.Value

    def read_vbatt(self) -> float:
        """Lit la tension batterie (pin 16 OBD) en volts."""
        if self._channel_id is None and self._device_id is None:
            raise J2534Error("PassThruIoctl(READ_VBATT)", 0x08)
        target = self._channel_id if self._channel_id is not None else self._device_id
        millivolts = ctypes.c_ulong(0)
        status = self._dll.PassThruIoctl(
            ctypes.c_ulong(target),  # type: ignore[arg-type]
            ctypes.c_ulong(IOCTL_READ_VBATT),
            None,
            ctypes.byref(millivolts),
        )
        self._check(status, "PassThruIoctl(READ_VBATT)")
        return millivolts.value / 1000.0

    def clear_rx_buffer(self) -> None:
        if self._channel_id is None:
            return
        status = self._dll.PassThruIoctl(
            ctypes.c_ulong(self._channel_id),
            ctypes.c_ulong(IOCTL_CLEAR_RX_BUFFER),
            None,
            None,
        )
        self._check(status, "PassThruIoctl(CLEAR_RX_BUFFER)")

    # -- filtres ---------------------------------------------------------------
    def start_flow_control_filter(self, rx_id: int, fc_tx_id: int, extended: bool = False) -> None:
        """Filtre Flow Control : l'interface répond automatiquement aux trames FF.

        Le message de flow control (0x30 00 00) est transmis automatiquement
        par le boîtier dès réception d'une First Frame de l'ECU (rx_id),
        avec l'identifiant fc_tx_id (adresse du testeur).
        """
        if self._channel_id is None:
            raise J2534Error("PassThruStartMsgFilter", 0x08)
        id_size = 4 if extended else 3
        tx_flags = TXFLAG_ISO15765_ADDR_TYPE if extended else 0
        mask = self._make_msg(PROTOCOL_ISO15765, tx_flags, b"\xFF" * id_size)
        pattern = self._make_msg(PROTOCOL_ISO15765, tx_flags, rx_id.to_bytes(id_size, "big"))
        flow = self._make_msg(
            PROTOCOL_ISO15765, tx_flags, fc_tx_id.to_bytes(id_size, "big") + b"\x30\x00\x00"
        )
        filter_id = ctypes.c_ulong(0xFFFFFFFF)
        status = self._dll.PassThruStartMsgFilter(
            ctypes.c_ulong(self._channel_id),
            ctypes.c_ulong(FLOW_CONTROL_FILTER),
            ctypes.byref(mask),
            ctypes.byref(pattern),
            ctypes.byref(flow),
            ctypes.byref(filter_id),
        )
        self._check(status, "PassThruStartMsgFilter")
        logger.info(
            "Filtre Flow Control actif : RX=0x%03X, FC TX=0x%03X (ID filtre 0x%X)",
            rx_id,
            fc_tx_id,
            filter_id.value,
        )

    # -- lecture / écriture ------------------------------------------------------
    def send_can(self, arb_id: int, payload: bytes, extended: bool = False) -> None:
        if self._channel_id is None:
            raise J2534Error("PassThruWriteMsgs", 0x08)
        tx_flags = TXFLAG_ISO15765_ADDR_TYPE if extended else 0
        data = self._id_bytes(arb_id, extended) + payload
        msg = self._make_msg(PROTOCOL_ISO15765, tx_flags, data)
        count = ctypes.c_ulong(1)
        with self._lock:
            status = self._dll.PassThruWriteMsgs(
                ctypes.c_ulong(self._channel_id),
                ctypes.byref(msg),
                ctypes.byref(count),
                ctypes.c_ulong(1000),
            )
        self._check(status, "PassThruWriteMsgs")
        frame = CanFrame(
            direction="TX", arb_id=arb_id, data=payload, is_extended=extended, timestamp=time.time()
        )
        self._notify(frame)

    def read_msgs(self, timeout_ms: float = 50) -> List[CanFrame]:
        if self._channel_id is None:
            return []
        msgs = (PASSTHRU_MSG * RX_QUEUE_SIZE)()
        count = ctypes.c_ulong(RX_QUEUE_SIZE)
        with self._lock:
            status = self._dll.PassThruReadMsgs(
                ctypes.c_ulong(self._channel_id),
                ctypes.cast(msgs, ctypes.POINTER(PASSTHRU_MSG)),
                ctypes.byref(count),
                ctypes.c_ulong(int(timeout_ms)),
            )
        self._check(status, "PassThruReadMsgs")
        frames: List[CanFrame] = []
        for index in range(count.value):
            msg = msgs[index]
            if msg.RxStatus & RXSTATUS_TX_MSG_TYPE:
                continue  # écho de nos propres émissions
            if msg.RxStatus & RXSTATUS_START_OF_MESSAGE:
                continue  # notification SOM sans payload utile
            data = bytes(msg.Data[: msg.DataSize])
            extended = bool(msg.RxStatus & TXFLAG_ISO15765_ADDR_TYPE)
            id_size = 4 if (extended or self._extended) else 3
            if len(data) < id_size:
                continue
            arb_id = int.from_bytes(data[:id_size], byteorder="big")
            payload = data[id_size:]
            frame = CanFrame(
                direction="RX",
                arb_id=arb_id,
                data=payload,
                is_extended=extended,
                timestamp=time.time(),
            )
            frames.append(frame)
            self._notify(frame)
        return frames

    def _notify(self, frame: CanFrame) -> None:
        for listener in list(self._listeners):
            try:
                listener(frame)
            except Exception:  # pragma: no cover - défensif
                logger.exception("Erreur dans un écouteur de trames.")

    # -- UDS ----------------------------------------------------------------------
    def create_uds_client(
        self, tx_id: int = DEFAULT_TX_ID, rx_id: int = DEFAULT_RX_ID, extended: bool = False
    ) -> "UdsClient":
        return UdsClient(self, tx_id=tx_id, rx_id=rx_id, extended=extended)


# ==========================================================================
# ISO-TP (ISO 15765-2)
# ==========================================================================
class IsoTpLayer:
    """Segmentation/réassemblage ISO-TP au-dessus d'un périphérique J2534.

    Remarque : avec un filtre Flow Control actif, le boîtier J2534 transmet
    automatiquement le message de flow control (0x30 ...) à l'ECU dès
    réception d'une First Frame ; cette couche n'a donc pas à le faire.
    """

    def __init__(self, device: BaseJ2534Device, tx_id: int, rx_id: int, extended: bool = False) -> None:
        self._device = device
        self._tx_id = tx_id
        self._rx_id = rx_id
        self._extended = extended
        self._cf_delay = 0.005  # délai inter trames consécutives (s)

    @property
    def rx_id(self) -> int:
        return self._rx_id

    def send(self, payload: bytes) -> None:
        if not payload:
            raise ValueError("Payload ISO-TP vide.")
        if len(payload) <= 7:
            frame = bytes([len(payload)]) + payload
            self._device.send_can(self._tx_id, frame, self._extended)
            return
        if len(payload) > 0xFFF:
            raise ValueError("Payload ISO-TP > 4095 octets non supporté (mode 'long' non implémenté).")
        header = struct.pack(">H", 0x1000 | len(payload))
        self._device.send_can(self._tx_id, header + payload[:6], self._extended)
        rest = payload[6:]
        sequence = 1
        for index in range(0, len(rest), 7):
            chunk = rest[index : index + 7]
            frame = bytes([0x20 | sequence]) + chunk
            self._device.send_can(self._tx_id, frame, self._extended)
            sequence = (sequence + 1) & 0x0F
            time.sleep(self._cf_delay)

    def receive(self, timeout: float) -> Optional[bytes]:
        """Attend et réassemble une réponse ISO-TP. ``None`` en cas d'échéance."""
        deadline = time.monotonic() + timeout
        buffer = bytearray()
        expected = 0
        while time.monotonic() < deadline:
            frames = self._device.read_msgs(50)
            for frame in frames:
                if frame.arb_id != self._rx_id or not frame.data:
                    continue
                pci_type = frame.data[0] >> 4
                if pci_type == 0:  # Single Frame
                    length = frame.data[0] & 0x0F
                    return bytes(frame.data[1 : 1 + length])
                if pci_type == 1:  # First Frame
                    expected = ((frame.data[0] & 0x0F) << 8) | frame.data[1]
                    buffer = bytearray(frame.data[2:])
                elif pci_type == 2:  # Consecutive Frame
                    buffer.extend(frame.data[1:])
                    if expected and len(buffer) >= expected:
                        return bytes(buffer[:expected])
                elif pci_type == 3:  # Flow Control (de l'ECU) : ignoré ici
                    continue
        return None


# ==========================================================================
# UDS (ISO 14229)
# ==========================================================================
SID_DIAGNOSTIC_SESSION_CONTROL = 0x10
SID_ECU_RESET = 0x11
SID_CLEAR_DIAGNOSTIC_INFORMATION = 0x14
SID_READ_DTC_INFORMATION = 0x19
SID_READ_DATA_BY_IDENTIFIER = 0x22
SID_TESTER_PRESENT = 0x3E

DID_VIN = 0xF190
DID_HARDWARE_NUMBER = 0xF191
DID_SOFTWARE_NUMBER = 0xF195


class UdsClient:
    """Client UDS minimal (0x10, 0x14, 0x19, 0x22, 0x3E) au-dessus d'ISO-TP."""

    def __init__(
        self,
        device: BaseJ2534Device,
        tx_id: int = DEFAULT_TX_ID,
        rx_id: int = DEFAULT_RX_ID,
        extended: bool = False,
        timeout: float = 3.0,
    ) -> None:
        self._device = device
        self._isotp = IsoTpLayer(device, tx_id=tx_id, rx_id=rx_id, extended=extended)
        self._timeout = timeout
        self._filter_started = False

    def _ensure_filter(self) -> None:
        if not self._filter_started:
            self._device.start_flow_control_filter(
                rx_id=self._isotp.rx_id, fc_tx_id=DEFAULT_TX_ID, extended=False
            )
            self._filter_started = True

    def request(self, data: bytes, timeout: Optional[float] = None) -> bytes:
        """Envoie une requête UDS et retourne la réponse positive.

        Lève ``UdsNegativeResponseError`` sur réponse 0x7F (sauf NRC 0x78
        « responsePending », qui prolonge l'attente) et ``UdsTimeoutError``
        si aucune réponse n'arrive.
        """
        self._ensure_filter()
        effective_timeout = timeout if timeout is not None else self._timeout
        sid = data[0] if data else 0x00
        logger.debug("UDS TX : %s", " ".join(f"{b:02X}" for b in data))
        self._isotp.send(data)
        deadline = time.monotonic() + effective_timeout
        while time.monotonic() < deadline:
            response = self._isotp.receive(0.25)
            if response is None:
                continue
            logger.debug("UDS RX : %s", " ".join(f"{b:02X}" for b in response))
            if response and response[0] == 0x7F and len(response) >= 3:
                nrc = response[2]
                if nrc == 0x78:  # responsePending : on prolonge l'attente
                    deadline = time.monotonic() + effective_timeout
                    continue
                raise UdsNegativeResponseError(sid, nrc)
            return response
        raise UdsTimeoutError(f"Aucune réponse UDS pour SID 0x{sid:02X} (délai {effective_timeout:.1f}s).")

    # -- services --------------------------------------------------------------
    def diagnostic_session_control(self, session: int = 0x03) -> bytes:
        """0x10 : Diagnostic Session Control (0x01 défaut, 0x02/0x03 étendue)."""
        return self.request(bytes([SID_DIAGNOSTIC_SESSION_CONTROL, session]))

    def read_data_by_identifier(self, did: int) -> bytes:
        """0x22 : ReadDataByIdentifier — retourne la charge utile après le DID."""
        response = self.request(
            bytes([SID_READ_DATA_BY_IDENTIFIER, (did >> 8) & 0xFF, did & 0xFF])
        )
        if not response or response[0] != 0x62 or len(response) < 3:
            raise UdsNegativeResponseError(SID_READ_DATA_BY_IDENTIFIER, 0x10)
        return bytes(response[3:])

    def read_dtc_by_status_mask(self, status_mask: int = 0xFF) -> List[tuple]:
        """0x19 0x02 : reportDTCByStatusMask — liste de (code, statut)."""
        response = self.request(
            bytes([SID_READ_DTC_INFORMATION, 0x02, status_mask])
        )
        if not response or response[0] != 0x59 or len(response) < 3:
            raise UdsNegativeResponseError(SID_READ_DTC_INFORMATION, 0x10)
        dtcs: List[tuple] = []
        index = 3
        while index + 3 <= len(response):
            code = int.from_bytes(response[index : index + 2], byteorder="big")
            status = response[index + 2]
            dtcs.append((code, status))
            index += 3
        return dtcs

    def clear_dtc(self, group: int = 0xFFFFFF) -> None:
        """0x14 : ClearDiagnosticInformation (0xFFFFFF = tous les groupes)."""
        response = self.request(
            bytes([SID_CLEAR_DIAGNOSTIC_INFORMATION, (group >> 16) & 0xFF, (group >> 8) & 0xFF, group & 0xFF])
        )
        if response and response[0] != 0x54:
            raise UdsNegativeResponseError(SID_CLEAR_DIAGNOSTIC_INFORMATION, 0x10)

    def tester_present(self) -> bytes:
        """0x3E 0x00 : maintient la session de diagnostic active."""
        return self.request(bytes([SID_TESTER_PRESENT, 0x00]))


# ==========================================================================
# Périphérique simulé (Mock J2534) — sans matériel
# ==========================================================================
class MockJ2534Device(BaseJ2534Device):
    """Simulateur d'interface J2534 + ECU (Bosch EDC17C10 fictif).

    Permet de tester l'interface graphique, la couche ISO-TP et les requêtes
    UDS sans aucun matériel branché. Les réponses sont générées localement.
    """

    MOCK_VIN = "VF3MOCKEDCU000000"
    MOCK_HW = b"0281020304"
    MOCK_SW = b"1037501234"
    MOCK_DTCS: tuple = (
        (0x0401, 0x2F),  # P0401 — débit EGR insuffisant
        (0x2002, 0x2F),  # P2002 — efficacité FAP sous seuil
        (0x2463, 0x2F),  # P2463 — saturation FAP suie
        (0x2263, 0x08),  # P2263 — débit turbocompresseur
    )

    def __init__(self) -> None:
        self._listeners: List[FrameListener] = []
        self._rx_queue: List[CanFrame] = []
        self._connected = False
        self._opened = False
        self._tx_id = DEFAULT_TX_ID
        self._rx_id = DEFAULT_RX_ID
        self._extended = False
        self._lock = threading.Lock()
        self._dtcs: List[tuple] = list(self.MOCK_DTCS)

    # -- propriétés ------------------------------------------------------------
    @property
    def name(self) -> str:
        return "Simulation / Mock J2534 (sans matériel)"

    @property
    def is_connected(self) -> bool:
        return self._connected

    # -- cycle de vie ------------------------------------------------------------
    def open(self) -> None:
        self._opened = True
        logger.info("[MOCK] PassThruOpen OK")

    def close(self) -> None:
        self._opened = False
        self._connected = False
        logger.info("[MOCK] PassThruClose OK")

    def connect_can(self, baudrate: int = DEFAULT_CAN_BAUDRATE, extended: bool = False) -> None:
        self._connected = True
        self._extended = extended
        logger.info("[MOCK] Connecté en ISO15765 @ %d bauds", baudrate)

    def disconnect(self) -> None:
        self._connected = False

    # -- IOCTL simulés --------------------------------------------------------------
    def read_vbatt(self) -> float:
        if not self._opened:
            raise J2534Error("PassThruIoctl(READ_VBATT)", 0x08)
        return round(12.3 + random.uniform(-0.25, 0.45), 2)

    def clear_rx_buffer(self) -> None:
        with self._lock:
            self._rx_queue.clear()

    # -- CAN / ISO-TP ------------------------------------------------------------------
    def start_flow_control_filter(self, rx_id: int, fc_tx_id: int, extended: bool = False) -> None:
        logger.info("[MOCK] Filtre Flow Control : RX=0x%03X, FC=0x%03X", rx_id, fc_tx_id)

    def send_can(self, arb_id: int, payload: bytes, extended: bool = False) -> None:
        self._emit(CanFrame("TX", arb_id, payload, extended, time.time()))
        if arb_id != self._tx_id or not payload:
            return
        uds_payload = self._reassemble_request(payload)
        if uds_payload is None:
            return
        response = self._handle_uds(uds_payload)
        self._queue_response(response)

    def read_msgs(self, timeout_ms: float = 50) -> List[CanFrame]:
        time.sleep(min(timeout_ms, 20) / 1000.0)
        with self._lock:
            frames, self._rx_queue = self._rx_queue, []
        for frame in frames:
            self._emit(frame)
        return frames

    # -- internes mock --------------------------------------------------------------
    def _reassemble_request(self, payload: bytes) -> Optional[bytes]:
        pci_type = payload[0] >> 4
        if pci_type == 0:
            return payload[1 : 1 + (payload[0] & 0x0F)]
        if pci_type == 1:
            logger.warning("[MOCK] Requête multi-trames du testeur non simulée.")
        return None

    def _queue_response(self, payload: bytes) -> None:
        if len(payload) <= 7:
            self._rx_queue.append(
                CanFrame("RX", self._rx_id, bytes([len(payload)]) + payload, self._extended, time.time())
            )
            return
        first = struct.pack(">H", 0x1000 | len(payload)) + payload[:6]
        self._rx_queue.append(CanFrame("RX", self._rx_id, first, self._extended, time.time()))
        rest = payload[6:]
        sequence = 1
        for index in range(0, len(rest), 7):
            chunk = rest[index : index + 7]
            self._rx_queue.append(
                CanFrame("RX", self._rx_id, bytes([0x20 | sequence]) + chunk, self._extended, time.time())
            )
            sequence = (sequence + 1) & 0x0F

    def _handle_uds(self, request: bytes) -> bytes:
        sid = request[0]
        if sid == SID_DIAGNOSTIC_SESSION_CONTROL and len(request) >= 2:
            return bytes([0x50, request[1], 0x00, 0x32, 0x01, 0xF4])
        if sid == SID_READ_DATA_BY_IDENTIFIER and len(request) >= 3:
            did = (request[1] << 8) | request[2]
            if did == DID_VIN:
                return bytes([0x62, request[1], request[2]]) + self.MOCK_VIN.encode("ascii")
            if did == DID_HARDWARE_NUMBER:
                return bytes([0x62, request[1], request[2]]) + self.MOCK_HW
            if did == DID_SOFTWARE_NUMBER:
                return bytes([0x62, request[1], request[2]]) + self.MOCK_SW
            return bytes([0x62, request[1], request[2]]) + b"UNKNOWN-DID"
        if sid == SID_READ_DTC_INFORMATION and len(request) >= 2 and request[1] == 0x02:
            payload = bytearray([0x59, 0x02, 0xFF])
            for code, status in self._dtcs:
                payload += code.to_bytes(2, "big") + bytes([status])
            return bytes(payload)
        if sid == SID_CLEAR_DIAGNOSTIC_INFORMATION:
            logger.info("[MOCK] DTC effacés (0x14 FF FF FF).")
            self._dtcs = []
            return bytes([0x54])
        if sid == SID_TESTER_PRESENT:
            return bytes([0x7E, 0x00])
        logger.warning("[MOCK] SID 0x%02X non simulé : réponse positive générique.", sid)
        return bytes([(sid + 0x40) & 0xFF]) + request[1:]

    def _emit(self, frame: CanFrame) -> None:
        for listener in list(self._listeners):
            try:
                listener(frame)
            except Exception:  # pragma: no cover - défensif
                logger.exception("Erreur dans un écouteur de trames (mock).")

    # -- UDS ----------------------------------------------------------------------
    def create_uds_client(
        self, tx_id: int = DEFAULT_TX_ID, rx_id: int = DEFAULT_RX_ID, extended: bool = False
    ) -> "UdsClient":
        self._tx_id = tx_id
        self._rx_id = rx_id
        return UdsClient(self, tx_id=tx_id, rx_id=rx_id, extended=extended)
