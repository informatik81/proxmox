"""Tests du module core.j2534_driver (Mock J2534, ISO-TP, UDS, structures)."""
from __future__ import annotations

import os
import time
from collections import deque

import pytest

from core.j2534_driver import (BaseJ2534Device, CanFrame, IsoTpLayer,
    IS_WINDOWS, J2534Error, J2534InterfaceInfo, MockJ2534Device, UdsClient,
    UdsNegativeResponseError, UdsTimeoutError, enumerate_j2534_interfaces,
    SCONFIG, PASSTHRU_MSG)

NATIVE_ONLY = pytest.mark.skipif(os.name != "nt", reason="Structure ABI Win32 : Windows uniquement")


# ---------------------------------------------------------------- énumération ----
@pytest.mark.skipif(IS_WINDOWS, reason="Attendu vide uniquement hors Windows")
def test_enumerate_j2534_interfaces_non_windows() -> None:
    assert enumerate_j2534_interfaces() == []


# ---------------------------------------------------------------- structures ----
@NATIVE_ONLY
def test_sconfig_size_win32() -> None:
    assert SCONFIG is not None
    import ctypes

    assert ctypes.sizeof(SCONFIG) == 8


@NATIVE_ONLY
def test_passthru_msg_size_win32() -> None:
    import ctypes

    assert ctypes.sizeof(PASSTHRU_MSG) == 24 + 4128 == 4152


# --------------------------------------------------------------- Mock UDS ----
@pytest.fixture()
def mock_device() -> MockJ2534Device:
    device = MockJ2534Device()
    device.open()
    device.connect_can(500000)
    return device


def test_mock_full_uds_flow(mock_device: MockJ2534Device) -> None:
    uds: UdsClient = mock_device.create_uds_client()

    response = uds.diagnostic_session_control(0x03)
    assert response[:2] == b"\x50\x03"

    vin = uds.read_data_by_identifier(0xF190)
    assert vin.decode("ascii") == MockJ2534Device.MOCK_VIN

    hw = uds.read_data_by_identifier(0xF191)
    assert hw == MockJ2534Device.MOCK_HW

    sw = uds.read_data_by_identifier(0xF195)
    assert sw == MockJ2534Device.MOCK_SW

    dtcs = uds.read_dtc_by_status_mask(0xFF)
    assert [code for code, _ in dtcs] == [0x0401, 0x2002, 0x2463, 0x2263]

    uds.clear_dtc(0xFFFFFF)
    assert uds.read_dtc_by_status_mask(0xFF) == []


def test_mock_unknown_did_negative_response(mock_device: MockJ2534Device) -> None:
    uds = mock_device.create_uds_client()
    with pytest.raises(UdsNegativeResponseError) as excinfo:
        uds.read_data_by_identifier(0xDEAD)
    assert excinfo.value.nrc == 0x31
    assert excinfo.value.sid == 0x22


def test_mock_tester_present(mock_device: MockJ2534Device) -> None:
    uds = mock_device.create_uds_client()
    assert uds.tester_present() == b"\x7E\x00"


def test_mock_read_vbatt_before_open_raises() -> None:
    device = MockJ2534Device()
    with pytest.raises(J2534Error):
        device.read_vbatt()


def test_mock_request_lock_serialized(mock_device: MockJ2534Device) -> None:
    uds = mock_device.create_uds_client()
    assert uds._request_lock.acquire(blocking=False), "verrou de requête disponible"
    uds._request_lock.release()


# ----------------------------------------------------------- ScriptedDevice ----
class ScriptedDevice(BaseJ2534Device):
    """Double de test : enregistre les trames émises, rejoue une file RX pré-câblée."""

    def __init__(self, scripted_rx: list = None) -> None:
        self._listeners = []
        self._connected = False
        self.sent: list = []
        self._rx_queue: deque = deque(scripted_rx or [])

    @property
    def name(self) -> str:
        return "Scripted (tests)"

    @property
    def is_connected(self) -> bool:
        return self._connected

    def open(self) -> None:
        self._connected = True

    def close(self) -> None:
        self._connected = False

    def connect_can(self, baudrate: int = 500000, extended: bool = False) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def read_vbatt(self) -> float:
        return 12.5

    def send_can(self, arb_id: int, payload: bytes, extended: bool = False) -> None:
        self.sent.append((arb_id, bytes(payload)))

    def create_uds_client(self, tx_id: int = 0x7E0, rx_id: int = 0x7E8,
                          extended: bool = False) -> UdsClient:
        return UdsClient(self, tx_id=tx_id, rx_id=rx_id, extended=extended)

    def read_msgs(self, timeout_ms: float = 50) -> list:
        time.sleep(min(timeout_ms, 20) / 1000.0)
        if self._rx_queue:
            frame = self._rx_queue.popleft()
            for listener in list(self._listeners):
                listener(frame)
            return [frame]
        return []

    def start_flow_control_filter(self, rx_id: int, fc_tx_id: int, extended: bool = False) -> None:
        pass

    def clear_rx_buffer(self) -> None:
        self._rx_queue.clear()


def _rx_sf(payload: bytes):
    return CanFrame("RX", 0x7E8, bytes([len(payload)]) + payload, False, time.time())


def test_uds_pending_nrc78_then_success() -> None:
    device = ScriptedDevice([_rx_sf(b"\x7F\x10\x78"), _rx_sf(b"\x50\x03\x00\x32\x01\xF4")])
    uds = UdsClient(device, timeout=5.0)
    response = uds.diagnostic_session_control(0x03)
    assert response[:2] == b"\x50\x03"
    assert [(arb, payload) for arb, payload in device.sent] == [(0x7E0, b"\x02\x10\x03")]


def test_uds_retry_after_pending_does_not_duplicate_send() -> None:
    device = ScriptedDevice([_rx_sf(b"\x7F\x22\x78"), _rx_sf(b"\x62\xF1\x90OK")])
    uds = UdsClient(device, timeout=5.0)
    payload = uds.read_data_by_identifier(0xF190)
    assert payload == b"OK"
    # Une seule requête émise malgré le responsePending.
    sends = [(arb, bytes(p)) for arb, p in device.sent]
    assert sends == [(0x7E0, b"\x03\x22\xF1\x90")]


def test_uds_timeout_without_response() -> None:
    device = ScriptedDevice([])
    uds = UdsClient(device, timeout=0.4)
    with pytest.raises(UdsTimeoutError):
        uds.tester_present()


def test_isotp_send_single_frame() -> None:
    device = ScriptedDevice([])
    isotp = IsoTpLayer(device, tx_id=0x7E0, rx_id=0x7E8)
    isotp.send(b"\x22\xF1\x90")
    assert device.sent == [(0x7E0, b"\x03\x22\xF1\x90")]


def test_isotp_send_multi_frame() -> None:
    device = ScriptedDevice([])
    isotp = IsoTpLayer(device, tx_id=0x7E0, rx_id=0x7E8)
    payload = bytes(range(20))
    isotp.send(payload)
    expected = [
        (0x7E0, b"\x10\x14" + payload[:6]),
        (0x7E0, b"\x21" + payload[6:13]),
        (0x7E0, b"\x22" + payload[13:20]),
    ]
    assert device.sent == expected


def test_interface_info_defaults() -> None:
    info = J2534InterfaceInfo(name="SM2 USB", dll_path="C:///smj2534.dll")
    assert info.name == "SM2 USB"
    assert info.vendor == ""
