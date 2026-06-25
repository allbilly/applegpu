"""AGX capture.bin format parser and address remapping."""

from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

CAP_MAGIC = 0x43584741
CAP_OPEN = 1
CAP_CALL = 2
CAP_TRAP = 3

CAP_HDR_FMT = "<4I"
CAP_OPEN_FMT = "<B3xIiI"
CAP_CALL_HDR_FMT = "<B3xIIII"
CAP_CALL_TAIL_FMT = "<i2I"
CAP_TRAP_HDR_FMT = "<B3xII4xQQQQI4x"
CAP_TRAP_TAIL_FMT = "<i"


@dataclass
class CapOpen:
    client_type: int
    expected_rc: int
    cap_conn: int


@dataclass
class CapCall:
    cap_conn: int
    selector: int
    scal_in: list[int]
    struct_in: bytes
    expected_rc: int
    scalar_out_cnt: int
    struct_out_sz: int
    cap_scalars: list[int]
    cap_struct: bytes


@dataclass
class CapTrap:
    cap_conn: int
    trap_idx: int
    p1: int
    p2: int
    p3: int
    p4: int
    snap: bytes
    expected_rc: int


CapEvent = CapOpen | CapCall | CapTrap


class AddrMap:
    """Remap GPU handles captured in one process to live allocations."""

    def __init__(self) -> None:
        self._maps: dict[int, int] = {}

    def add(self, old: int, new: int) -> None:
        if not old or not new or old == new:
            return
        self._maps[old] = new

    def remap(self, value: int) -> int:
        return self._maps.get(value, value)

    def patch_u64_buf(self, buf: bytearray) -> None:
        for off in range(0, len(buf) - 7, 8):
            old, = struct.unpack_from("<Q", buf, off)
            struct.pack_into("<Q", buf, off, self.remap(old))

    def learn_resource_maps(self, cap: bytes, live: bytes) -> None:
        if len(cap) < 24 or len(live) < 24:
            return
        self.add(struct.unpack_from("<Q", cap, 8)[0], struct.unpack_from("<Q", live, 8)[0])
        self.add(struct.unpack_from("<Q", cap, 16)[0], struct.unpack_from("<Q", live, 16)[0])

    def __len__(self) -> int:
        return len(self._maps)


class CaptureReader:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.off = 0

    def read(self, n: int) -> bytes:
        chunk = self.data[self.off : self.off + n]
        if len(chunk) != n:
            raise EOFError
        self.off += n
        return chunk

    def peek_type(self) -> int | None:
        if self.off >= len(self.data):
            return None
        return self.data[self.off]

    def read_hdr(self) -> tuple[int, int, int, int]:
        magic, version, count, _pad = struct.unpack(CAP_HDR_FMT, self.read(16))
        if magic != CAP_MAGIC:
            raise ValueError(f"bad magic 0x{magic:08x}")
        return magic, version, count, _pad

    def read_open(self) -> CapOpen:
        rec = self.read(struct.calcsize(CAP_OPEN_FMT))
        _type, client_type, rc, conn = struct.unpack(CAP_OPEN_FMT, rec)
        return CapOpen(client_type, rc, conn)

    def read_call(self) -> CapCall:
        hdr = self.read(struct.calcsize(CAP_CALL_HDR_FMT))
        _type, conn, selector, scalar_in_cnt, struct_in_sz = struct.unpack(
            CAP_CALL_HDR_FMT, hdr
        )
        scal_in = (
            list(struct.unpack(f"<{scalar_in_cnt}Q", self.read(scalar_in_cnt * 8)))
            if scalar_in_cnt
            else []
        )
        struct_in = self.read(struct_in_sz) if struct_in_sz else b""

        tail = self.read(struct.calcsize(CAP_CALL_TAIL_FMT))
        rc, scalar_out_cnt, struct_out_sz = struct.unpack(CAP_CALL_TAIL_FMT, tail)

        cap_scalars = (
            list(struct.unpack(f"<{scalar_out_cnt}Q", self.read(scalar_out_cnt * 8)))
            if scalar_out_cnt
            else []
        )
        cap_struct = self.read(struct_out_sz) if struct_out_sz else b""

        return CapCall(
            conn, selector, scal_in, struct_in, rc,
            scalar_out_cnt, struct_out_sz, cap_scalars, cap_struct,
        )

    def read_trap(self) -> CapTrap:
        hdr = self.read(struct.calcsize(CAP_TRAP_HDR_FMT))
        _type, conn, trap_idx, p1, p2, p3, p4, snap_sz = struct.unpack(
            CAP_TRAP_HDR_FMT, hdr
        )
        snap = self.read(snap_sz) if snap_sz else b""
        (expected_rc,) = struct.unpack(CAP_TRAP_TAIL_FMT, self.read(4))
        return CapTrap(conn, trap_idx, p1, p2, p3, p4, snap, expected_rc)

    def iter_events(self) -> Iterator[CapEvent]:
        self.read_hdr()
        while True:
            op_type = self.peek_type()
            if op_type is None or op_type == 0:
                break
            if op_type == CAP_OPEN:
                yield self.read_open()
            elif op_type == CAP_CALL:
                yield self.read_call()
            elif op_type == CAP_TRAP:
                yield self.read_trap()
            else:
                raise ValueError(f"bad capture type {op_type} at offset {self.off}")


def load_events(path: Path) -> list[CapEvent]:
    """Load all capture events — mirrors nvgpu load_events()."""
    reader = CaptureReader(path.read_bytes())
    return list(reader.iter_events())
