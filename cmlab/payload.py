"""Embedded logger uplink payload (LoRaWAN application payload / BLE characteristic value).

Layout, big-endian, 6 + 2n bytes for n = 1..3 temperature channels:

    byte 0      flags and version (see below)
    bytes 1-2  u16 interval counter (wraps at 65535)
    bytes 3..   n x int16 temperature in 0.01 C (0x8000 = sensor fault), top to bottom
    next 2      u16 battery in mV
    last        CRC-8 (poly 0x07, init 0) over all preceding bytes

byte 0: bits 7-4 version (1), bits 3-2 channel count n (1..3), bit 1 reserved (0),
bit 0 low-battery flag. The JS twin is ``decoder/decoder.js`` (LoRaWAN network-server style
``decodeUplink``); both are tested against the shared vectors in ``tests/vectors.json``.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

VERSION = 1
FAULT = -32768
LOW_BATT_MV = 2600


class PayloadError(ValueError):
    pass


def crc8(data: bytes) -> int:
    crc = 0
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = ((crc << 1) ^ 0x07) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


@dataclass(frozen=True)
class Reading:
    seq: int
    temps_c: tuple[float | None, ...]
    battery_mv: int
    low_battery: bool

    @property
    def battery_v(self) -> float:
        return self.battery_mv / 1000.0


def encode(seq: int, temps_c, battery_mv: int) -> bytes:
    n = len(temps_c)
    if not 1 <= n <= 3:
        raise PayloadError("1 to 3 temperature channels supported")
    if not 0 <= battery_mv <= 0xFFFF:
        raise PayloadError("battery_mv out of range")
    raw = []
    for t in temps_c:
        if t is None:
            raw.append(FAULT)
            continue
        v = round(t * 100)
        if not -32767 <= v <= 32767:
            raise PayloadError(f"temperature {t} out of range")
        raw.append(v)
    low = 1 if battery_mv < LOW_BATT_MV else 0
    head = bytes([(VERSION << 4) | (n << 2) | low]) + struct.pack(">H", seq & 0xFFFF)
    body = head + struct.pack(f">{n}h", *raw) + struct.pack(">H", battery_mv)
    return body + bytes([crc8(body)])


def decode(data: bytes) -> Reading:
    if len(data) < 8:
        raise PayloadError("payload too short")
    ver = data[0] >> 4
    n = (data[0] >> 2) & 0x3
    if ver != VERSION:
        raise PayloadError(f"unsupported version {ver}")
    if not 1 <= n <= 3:
        raise PayloadError(f"bad channel count {n}")
    if len(data) != 6 + 2 * n:
        raise PayloadError(f"length {len(data)} does not match {n} channels")
    if crc8(data[:-1]) != data[-1]:
        raise PayloadError("CRC mismatch")
    seq = struct.unpack(">H", data[1:3])[0]
    raw = struct.unpack(f">{n}h", data[3:3 + 2 * n])
    temps = tuple(None if v == FAULT else v / 100.0 for v in raw)
    batt = struct.unpack(">H", data[3 + 2 * n:5 + 2 * n])[0]
    return Reading(seq, temps, batt, bool(data[0] & 1))
