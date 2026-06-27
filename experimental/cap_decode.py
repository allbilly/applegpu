"""Decode AGX IOKit capture blobs into named structures.

Field names follow macOS IOGPU RE (ref/agx-research): selector 0x09 ResourceCreate,
0x07 QueueCreate, 0x0e ShmemCreate, trap0 Submit fast.
"""

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
class ResourceCreateIn:
    """Selector 0x09 s_new_resource input (104 bytes)."""

    parent_handle: int = 0
    type_version: int = 0x0001_0001
    resource_class: int = 1
    create_flags: int = 0x0100_0101
    alloc_size: int = 0
    suballoc_flag: int = 0
    parent_gpu_va: int = 0
    parent_gpu_va2: int = 0
    heap_flags: int = 0
    heap_lane: int = 0
    stride_or_count: int = 0
    create_info: int = 0
    backing_ptr: int = 0
    raw_tail: bytes = field(default_factory=bytes)

    @classmethod
    def from_bytes(cls, data: bytes) -> ResourceCreateIn:
        if len(data) != 104:
            raise ValueError(f"ResourceCreateIn expects 104 bytes, got {len(data)}")
        return cls(
            parent_handle=_u64(data, 0),
            type_version=_u32(data, 8),
            resource_class=_u32(data, 12),
            create_flags=_u32(data, 16),
            alloc_size=_u32(data, 20),
            suballoc_flag=_u32(data, 0x30),
            parent_gpu_va=_u64(data, 0x38),
            parent_gpu_va2=_u64(data, 0x40),
            heap_flags=_u32(data, 0x48),
            heap_lane=_u32(data, 0x50),
            stride_or_count=_u32(data, 0x58),
            create_info=_u32(data, 0x5C),
            backing_ptr=_u64(data, 0x60),
        )

    def pack(self) -> bytes:
        if self.raw_tail:
            return bytes(self.raw_tail)
        buf = bytearray(104)
        struct.pack_into("<Q", buf, 0, self.parent_handle)
        struct.pack_into("<I", buf, 8, self.type_version)
        struct.pack_into("<I", buf, 12, self.resource_class)
        struct.pack_into("<I", buf, 16, self.create_flags)
        struct.pack_into("<I", buf, 20, self.alloc_size)
        struct.pack_into("<I", buf, 0x30, self.suballoc_flag)
        struct.pack_into("<Q", buf, 0x38, self.parent_gpu_va)
        struct.pack_into("<Q", buf, 0x40, self.parent_gpu_va2)
        struct.pack_into("<I", buf, 0x48, self.heap_flags)
        struct.pack_into("<I", buf, 0x50, self.heap_lane)
        struct.pack_into("<I", buf, 0x58, self.stride_or_count)
        struct.pack_into("<I", buf, 0x5C, self.create_info)
        struct.pack_into("<Q", buf, 0x60, self.backing_ptr)
        return bytes(buf)


@dataclass
class ResourceCreateOut:
    """Selector 0x09 output (88 bytes) — captured reference for addr-map learning."""

    rid: int = 0
    rid_tag: int = 0
    gpu_va: int = 0
    gpu_va2: int = 0
    slot_index: int = 0
    heap_size: int = 0
    cookie: int = 0
    cookie_flags: int = 0
    type_tag: int = 0
    out_heap_flags: int = 0
    raw: bytes = field(default_factory=bytes)

    @classmethod
    def from_bytes(cls, data: bytes) -> ResourceCreateOut:
        if len(data) != 88:
            raise ValueError(f"ResourceCreateOut expects 88 bytes, got {len(data)}")
        return cls(
            rid=_u32(data, 0),
            rid_tag=_u32(data, 4),
            gpu_va=_u64(data, 8),
            gpu_va2=_u64(data, 16),
            slot_index=_u32(data, 0x24),
            heap_size=_u64(data, 0x28),
            cookie=_u32(data, 0x30),
            cookie_flags=_u32(data, 0x34),
            type_tag=_u32(data, 0x38),
            out_heap_flags=_u32(data, 0x50),
        )

    def pack(self) -> bytes:
        if self.raw:
            return bytes(self.raw)
        buf = bytearray(88)
        struct.pack_into("<I", buf, 0, self.rid)
        struct.pack_into("<I", buf, 4, self.rid_tag)
        struct.pack_into("<Q", buf, 8, self.gpu_va)
        struct.pack_into("<Q", buf, 16, self.gpu_va2)
        struct.pack_into("<I", buf, 0x24, self.slot_index)
        struct.pack_into("<Q", buf, 0x28, self.heap_size)
        struct.pack_into("<I", buf, 0x30, self.cookie)
        struct.pack_into("<I", buf, 0x34, self.cookie_flags)
        struct.pack_into("<I", buf, 0x38, self.type_tag)
        struct.pack_into("<I", buf, 0x50, self.out_heap_flags)
        return bytes(buf)


@dataclass
class QueueCreateIn:
    """Selector 0x07 queue_create input (1040 bytes)."""

    exe_path: str = ""
    label: str = ""
    queue_flags: int = 2
    unk_mask: int = 0xFFFFFFFF
    enable: int = 1
    raw: bytes = field(default_factory=bytes)

    @classmethod
    def from_bytes(cls, data: bytes) -> QueueCreateIn:
        if len(data) != 0x410:
            raise ValueError(f"QueueCreateIn expects 1040 bytes, got {len(data)}")
        return cls(
            exe_path=_cstr(data, 0x000, 0x3C7),
            label=_cstr(data, 0x3C8, 0x37),
            queue_flags=_u64(data, 0x400),
            unk_mask=_u32(data, 0x408),
            enable=_u32(data, 0x40C),
        )

    def pack(self) -> bytes:
        if self.raw:
            return bytes(self.raw)
        buf = bytearray(0x410)
        ep = self.exe_path.encode("utf-8")[:0x3C7]
        lb = self.label.encode("utf-8")[:0x37]
        buf[0x000 : 0x000 + len(ep)] = ep
        buf[0x3C8 : 0x3C8 + len(lb)] = lb
        struct.pack_into("<Q", buf, 0x400, self.queue_flags)
        struct.pack_into("<I", buf, 0x408, self.unk_mask)
        struct.pack_into("<I", buf, 0x40C, self.enable)
        return bytes(buf)


@dataclass
class QueueCreateOut:
    queue_id: int = 0
    cookie: int = 0

    @classmethod
    def from_bytes(cls, data: bytes) -> QueueCreateOut:
        return cls(_u32(data, 0), _u64(data, 8))

    def pack(self) -> bytes:
        buf = bytearray(16)
        struct.pack_into("<I", buf, 0, self.queue_id)
        struct.pack_into("<Q", buf, 8, self.cookie)
        return bytes(buf)


@dataclass
class NotifQueueIn:
    ring_size: int = 0x100
    ring_flags: int = 0x28

    def as_scalars(self) -> list[int]:
        return [self.ring_size, self.ring_flags]


@dataclass
class QueueFinalizeIn:
    arg0: int = 1
    arg1: int = 1

    def as_scalars(self) -> list[int]:
        return [self.arg0, self.arg1]


@dataclass
class ShmemIn:
    size: int = 0x4000
    map_flags: int = 0

    def as_scalars(self) -> list[int]:
        return [self.size, self.map_flags]


@dataclass
class ShmemOut:
    gpu_va: int = 0
    size: int = 0
    shmem_id: int = 0

    @classmethod
    def from_bytes(cls, data: bytes) -> ShmemOut:
        return cls(_u64(data, 0), _u32(data, 8), _u32(data, 12))

    def pack(self) -> bytes:
        buf = bytearray(16)
        struct.pack_into("<Q", buf, 0, self.gpu_va)
        struct.pack_into("<I", buf, 8, self.size)
        struct.pack_into("<I", buf, 12, self.shmem_id)
        return bytes(buf)


@dataclass
class Trap0SubmitSnap:
    """Trap0 fast-path submit buffer (64 bytes)."""

    buf_count: int = 0
    submit_flags: int = 0
    reserved: int = 0
    cmdbuf_gpu_va: int = 0
    cmdbuf_aux_va: int = 0
    raw: bytes = field(default_factory=bytes)

    @classmethod
    def from_bytes(cls, data: bytes) -> Trap0SubmitSnap:
        return cls(
            buf_count=_u32(data, 0),
            submit_flags=_u32(data, 4),
            reserved=_u64(data, 8),
            cmdbuf_gpu_va=_u64(data, 0x10),
            cmdbuf_aux_va=_u64(data, 0x18),
        )

    def pack(self) -> bytes:
        if self.raw:
            return bytes(self.raw)
        buf = bytearray(64)
        struct.pack_into("<I", buf, 0, self.buf_count)
        struct.pack_into("<I", buf, 4, self.submit_flags)
        struct.pack_into("<Q", buf, 8, self.reserved)
        struct.pack_into("<Q", buf, 0x10, self.cmdbuf_gpu_va)
        struct.pack_into("<Q", buf, 0x18, self.cmdbuf_aux_va)
        return bytes(buf)


SELECTOR_DECODERS = {
    0x09: ("ResourceCreateIn", ResourceCreateIn),
    0x07: ("QueueCreateIn", QueueCreateIn),
}

SELECTOR_OUT_DECODERS = {
    0x09: ("ResourceCreateOut", ResourceCreateOut),
    0x07: ("QueueCreateOut", QueueCreateOut),
    0x0E: ("ShmemOut", ShmemOut),
    0x10: ("ShmemOut", ShmemOut),
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
