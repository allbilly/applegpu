"""Decode AGX IOKit capture blobs into named structures."""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Any


def _u32(buf: bytes, off: int) -> int:
    return struct.unpack_from("<I", buf, off)[0]


def _u64(buf: bytes, off: int) -> int:
    return struct.unpack_from("<Q", buf, off)[0]


def _cstr(buf: bytes, off: int, maxlen: int) -> str:
    end = buf.find(b"\x00", off, off + maxlen)
    if end < 0:
        end = off + maxlen
    return buf[off:end].decode("utf-8", errors="replace")


@dataclass
class NewResourceIn:
    """Selector 0x09 s_new_resource input (104 bytes)."""

    parent_qword: int = 0
    type_version: int = 0x0001_0001
    field_0c: int = 1
    flags: int = 0x0100_0101
    size: int = 0
    parent_va_38: int = 0
    parent_va_40: int = 0
    field_48: int = 0
    field_5c: int = 0
    raw_tail: bytes = field(default_factory=bytes)

    @classmethod
    def from_bytes(cls, data: bytes) -> NewResourceIn:
        if len(data) != 104:
            raise ValueError(f"NewResourceIn expects 104 bytes, got {len(data)}")
        return cls(
            parent_qword=_u64(data, 0),
            type_version=_u32(data, 8),
            field_0c=_u32(data, 12),
            flags=_u32(data, 16),
            size=_u32(data, 20),
            parent_va_38=_u64(data, 0x38),
            parent_va_40=_u64(data, 0x40),
            field_48=_u32(data, 0x48),
            field_5c=_u32(data, 0x5C),
            raw_tail=data,
        )

    def pack(self) -> bytes:
        if self.raw_tail:
            return bytes(self.raw_tail)
        buf = bytearray(104)
        struct.pack_into("<Q", buf, 0, self.parent_qword)
        struct.pack_into("<I", buf, 8, self.type_version)
        struct.pack_into("<I", buf, 12, self.field_0c)
        struct.pack_into("<I", buf, 16, self.flags)
        struct.pack_into("<I", buf, 20, self.size)
        struct.pack_into("<Q", buf, 0x38, self.parent_va_38)
        struct.pack_into("<Q", buf, 0x40, self.parent_va_40)
        struct.pack_into("<I", buf, 0x48, self.field_48)
        struct.pack_into("<I", buf, 0x5C, self.field_5c)
        return bytes(buf)


@dataclass
class NewResourceOut:
    """Selector 0x09 output (88 bytes) — captured reference for addr-map learning."""

    rid: int = 0
    gpu_va_08: int = 0
    gpu_va_10: int = 0
    field_18: int = 0
    field_1c: int = 0
    field_20: int = 0
    field_28: int = 0
    field_30: int = 0
    field_38: int = 0
    field_40: int = 0
    field_48: int = 0
    raw: bytes = field(default_factory=bytes)

    @classmethod
    def from_bytes(cls, data: bytes) -> NewResourceOut:
        if len(data) != 88:
            raise ValueError(f"NewResourceOut expects 88 bytes, got {len(data)}")
        return cls(
            rid=_u32(data, 0),
            gpu_va_08=_u64(data, 8),
            gpu_va_10=_u64(data, 16),
            field_18=_u32(data, 0x18),
            field_1c=_u32(data, 0x1C),
            field_20=_u32(data, 0x20),
            field_28=_u64(data, 0x28),
            field_30=_u32(data, 0x30),
            field_38=_u32(data, 0x38),
            field_40=_u32(data, 0x40),
            field_48=_u32(data, 0x48),
            raw=data,
        )


@dataclass
class QueueCreateIn:
    """Selector 0x07 queue_create input (1040 bytes)."""

    exe_path: str = ""
    label: str = ""
    field_400: int = 2
    field_408: int = 0xFFFFFFFF
    field_40c: int = 1
    raw: bytes = field(default_factory=bytes)

    @classmethod
    def from_bytes(cls, data: bytes) -> QueueCreateIn:
        if len(data) != 0x410:
            raise ValueError(f"QueueCreateIn expects 1040 bytes, got {len(data)}")
        return cls(
            exe_path=_cstr(data, 0x000, 0x3C7),
            label=_cstr(data, 0x3C8, 0x37),
            field_400=_u64(data, 0x400),
            field_408=_u32(data, 0x408),
            field_40c=_u32(data, 0x40C),
            raw=data,
        )

    def pack(self) -> bytes:
        if self.raw:
            return bytes(self.raw)
        buf = bytearray(0x410)
        ep = self.exe_path.encode("utf-8")[:0x3C7]
        lb = self.label.encode("utf-8")[:0x37]
        buf[0x000 : 0x000 + len(ep)] = ep
        buf[0x3C8 : 0x3C8 + len(lb)] = lb
        struct.pack_into("<Q", buf, 0x400, self.field_400)
        struct.pack_into("<I", buf, 0x408, self.field_408)
        struct.pack_into("<I", buf, 0x40C, self.field_40c)
        return bytes(buf)


@dataclass
class QueueCreateOut:
    queue_id: int = 0
    extra: int = 0

    @classmethod
    def from_bytes(cls, data: bytes) -> QueueCreateOut:
        return cls(_u64(data, 0), _u64(data, 8))


@dataclass
class NotifQueueIn:
  size: int = 0x100
  flags: int = 0x28

  def as_scalars(self) -> list[int]:
      return [self.size, self.flags]


@dataclass
class QueueFinalizeIn:
    a: int = 1
    b: int = 1

    def as_scalars(self) -> list[int]:
      return [self.a, self.b]


@dataclass
class ShmemIn:
    size: int = 0x4000
    flags: int = 0

    def as_scalars(self) -> list[int]:
        return [self.size, self.flags]


@dataclass
class ShmemOut:
    vaddr: int = 0
    size: int = 0
    handle: int = 0

    @classmethod
    def from_bytes(cls, data: bytes) -> ShmemOut:
        return cls(_u64(data, 0), _u32(data, 8), _u32(data, 12))


@dataclass
class TrapSubmitSnap:
    """Trap0 fast-path submit buffer (64 bytes)."""

    field_00: int = 0
    field_04: int = 0
    field_08: int = 0
    field_10: int = 0
    field_18: int = 0
    raw: bytes = field(default_factory=bytes)

    @classmethod
    def from_bytes(cls, data: bytes) -> TrapSubmitSnap:
        return cls(
            field_00=_u32(data, 0),
            field_04=_u32(data, 4),
            field_08=_u64(data, 8),
            field_10=_u64(data, 0x10),
            field_18=_u64(data, 0x18),
            raw=data,
        )

    def pack(self) -> bytes:
        if self.raw:
            return bytes(self.raw)
        buf = bytearray(64)
        struct.pack_into("<I", buf, 0, self.field_00)
        struct.pack_into("<I", buf, 4, self.field_04)
        struct.pack_into("<Q", buf, 8, self.field_08)
        struct.pack_into("<Q", buf, 0x10, self.field_10)
        struct.pack_into("<Q", buf, 0x18, self.field_18)
        return bytes(buf)


SELECTOR_DECODERS = {
    0x09: ("NewResourceIn", NewResourceIn),
    0x07: ("QueueCreateIn", QueueCreateIn),
}

SELECTOR_OUT_DECODERS = {
    0x09: ("NewResourceOut", NewResourceOut),
    0x07: ("QueueCreateOut", QueueCreateOut),
    0x0e: ("ShmemOut", ShmemOut),
}


def decode_call_struct(selector: int, data: bytes) -> Any:
    if selector in SELECTOR_DECODERS:
        _name, cls = SELECTOR_DECODERS[selector]
        return cls.from_bytes(data)
    return data


def decode_call_out(selector: int, data: bytes) -> Any:
    if selector in SELECTOR_OUT_DECODERS:
        _name, cls = SELECTOR_OUT_DECODERS[selector]
        return cls.from_bytes(data)
    return data


def repr_value(v: Any) -> str:
    if isinstance(v, str):
        return repr(v)
    if isinstance(v, bytes):
        return repr(v)
    if isinstance(v, int) and v > 0xFFFF:
        return f"0x{v:x}"
    return repr(v)
