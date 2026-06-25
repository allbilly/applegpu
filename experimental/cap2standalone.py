#!/usr/bin/env python3
"""Generate a standalone replay script from capture.bin.

Decodes all blobs into structure code — no runtime .cap or hex file loading.
"""

from __future__ import annotations

import argparse
import textwrap
from dataclasses import fields
from datetime import datetime, timezone
from pathlib import Path

from cap_decode import (
    NewResourceIn,
    NewResourceOut,
    NotifQueueIn,
    QueueCreateIn,
    QueueFinalizeIn,
    ShmemIn,
    TrapSubmitSnap,
    decode_call_out,
    decode_call_struct,
    repr_value,
)
from cap_format import CapCall, CapOpen, CapTrap, load_events


def emit_dataclass_init(obj, *, include_raw: bool = False) -> str:
    parts = []
    for f in fields(obj):
        val = getattr(obj, f.name)
        if f.name == "raw_tail" and isinstance(val, bytes):
            continue
        if f.name == "raw" and isinstance(val, bytes):
            if include_raw and val:
                parts.append(f"raw={val!r}")
            continue
        parts.append(f"{f.name}={repr_value(val)}")
    return f"{type(obj).__name__}({', '.join(parts)})"


def emit_open(op: CapOpen, idx: int) -> str:
    return textwrap.indent(
        f"OpenOp(client_type=0x{op.client_type:x},  # op {idx}\n"
        f"),",
        "    ",
    )


def emit_call(op: CapCall, idx: int) -> str:
    lines = [f"CallOp(  # op {idx}: sel=0x{op.selector:02x}"]

    if op.scal_in:
        if op.selector == 0x10 and len(op.scal_in) == 2:
            struct_expr = emit_dataclass_init(
                NotifQueueIn(op.scal_in[0], op.scal_in[1])
            )
            lines.append(f"    selector=0x{op.selector:02x},")
            lines.append(f"    scalars={struct_expr}.as_scalars(),")
        elif op.selector == 0x1c and len(op.scal_in) == 2:
            struct_expr = emit_dataclass_init(
                QueueFinalizeIn(op.scal_in[0], op.scal_in[1])
            )
            lines.append(f"    selector=0x{op.selector:02x},")
            lines.append(f"    scalars={struct_expr}.as_scalars(),")
        elif op.selector == 0x0e and len(op.scal_in) == 2:
            struct_expr = emit_dataclass_init(
                ShmemIn(op.scal_in[0], op.scal_in[1])
            )
            lines.append(f"    selector=0x{op.selector:02x},")
            lines.append(f"    scalars={struct_expr}.as_scalars(),")
        else:
            lines.append(f"    selector=0x{op.selector:02x},")
            lines.append(f"    scalars={op.scal_in!r},")
    else:
        lines.append(f"    selector=0x{op.selector:02x},")
        lines.append("    scalars=[],")

    if op.struct_in:
        decoded = decode_call_struct(op.selector, op.struct_in)
        if hasattr(decoded, "pack"):
            lines.append(
                f"    struct_in=_with_raw({emit_dataclass_init(decoded)}, {op.struct_in!r}),"
            )
        else:
            lines.append(f"    struct_in={op.struct_in!r},")
    else:
        lines.append("    struct_in=None,")

    lines.append(f"    struct_out_sz={op.struct_out_sz},")

    if op.cap_struct:
        out = decode_call_out(op.selector, op.cap_struct)
        if hasattr(out, "rid"):
            lines.append(
                f"    cap_out={emit_dataclass_init(out, include_raw=True)},"
            )
        else:
            lines.append(f"    cap_out={op.cap_struct!r},")

    lines.append("),")
    return textwrap.indent("\n".join(lines), "    ")


def emit_trap(op: CapTrap, idx: int) -> str:
    snap = TrapSubmitSnap.from_bytes(op.snap) if op.snap else TrapSubmitSnap()
    body = (
        f"TrapOp(  # op {idx}\n"
        f"    trap_idx={op.trap_idx},\n"
        f"    p1={op.p1},\n"
        f"    p2={op.p2},\n"
        f"    use_p4={bool(op.p4)},\n"
        f"    snap=_with_raw({emit_dataclass_init(snap)}, {op.snap!r}),\n"
        f"),"
    )
    return textwrap.indent(body, "    ")


STANDALONE_HEADER = '''#!/usr/bin/env python3
"""Standalone AGX add replay — generated, no capture.bin at runtime.

Source capture: {capture}
Generated: {when}

Decoded structure layouts: cap_decode.py
Replay engine: inline below (fork of replay.py without file loading).
"""

from __future__ import annotations

import ctypes
import ctypes.util
import struct
import sys
from dataclasses import dataclass, field
from typing import Any

# --- structure codecs (from cap_decode.py) ---

{struct_code}

# --- minimal IOKit backend ---

{iokit_code}

# --- replay ops (decoded from capture) ---

@dataclass
class OpenOp:
    client_type: int

@dataclass
class CallOp:
    selector: int
    scalars: list[int]
    struct_in: Any
    struct_out_sz: int
    cap_out: Any = None

    def pack_struct_in(self) -> bytes | None:
        if self.struct_in is None:
            return None
        if hasattr(self.struct_in, "pack"):
            return self.struct_in.pack()
        return self.struct_in


def _with_raw(obj, blob: bytes):
    if hasattr(obj, "raw_tail"):
        obj.raw_tail = blob
    if hasattr(obj, "raw"):
        obj.raw = blob
    return obj

@dataclass
class TrapOp:
    trap_idx: int
    p1: int
    p2: int
    use_p4: bool
    snap: TrapSubmitSnap

class AddrMap:
    def __init__(self) -> None:
        self._maps: dict[int, int] = {{}}

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

OPS = [
{ops}
]


def replay() -> int:
    iokit = IOKit()
    addr_map = AddrMap()
    svc = iokit.find_agx_service()
    if not svc:
        print("no AGX accelerator", file=sys.stderr)
        return 1

    conn = 0
    fails = 0
    print("replaying standalone add ({{}} ops)".format(len(OPS)))

    try:
        for idx, op in enumerate(OPS):
            if isinstance(op, OpenOp):
                if not conn:
                    kr, conn = iokit.service_open(svc, op.client_type)
                    print(f"[{{idx}}] IOServiceOpen type=0x{{op.client_type:x}} conn=0x{{conn:x}} rc=0x{{kr:x}}")
                    if kr != 0:
                        return 1
                else:
                    print(f"[{{idx}}] skip duplicate open")
                continue

            if not conn:
                print("op before open", file=sys.stderr)
                return 1

            if isinstance(op, CallOp):
                raw = op.pack_struct_in()
                buf = bytearray(raw) if raw else bytearray()
                if buf:
                    addr_map.patch_u64_buf(buf)
                rc, _so, live_out, out_sz = iokit.connect_call(
                    conn, op.selector, op.scalars,
                    bytes(buf) if buf else None,
                    0, op.struct_out_sz,
                )
                print(f"[{{idx}}] sel=0x{{op.selector:02x}} rc=0x{{rc:x}} out_sz={{out_sz}}")
                if rc == 0 and op.cap_out is not None:
                    cap_raw = getattr(op.cap_out, "raw", b"")
                    if cap_raw:
                        addr_map.learn_resource_maps(cap_raw, live_out)
                fails += rc != 0
                continue

            if isinstance(op, TrapOp):
                snap = bytearray(op.snap.pack())
                addr_map.patch_u64_buf(snap)
                p3 = p4 = 0
                ptr = None
                libc = None
                if snap:
                    alloc_sz = len(snap) + 0x100
                    ptr, libc = alloc_aligned(alloc_sz)
                    dst = (ctypes.c_uint8 * alloc_sz).from_address(ptr.value)
                    ctypes.memmove(dst, bytes(snap), len(snap))
                    p3 = ptr.value
                    p4 = ptr.value + 0x84 if op.use_p4 else 0
                rc = iokit.connect_trap(conn, op.trap_idx, op.p1, op.p2, p3, p4)
                print(f"[{{idx}}] trap{{op.trap_idx}} rc=0x{{rc:x}} snap={{len(snap)}} bytes")
                if ptr is not None and libc is not None:
                    libc.free(ptr)
                fails += rc != 0
                continue

    finally:
        if conn:
            iokit.lib.IOServiceClose(conn)
        iokit.lib.IOObjectRelease(svc)

    print(f"done: {{len(OPS)}} ops, {{fails}} failures, {{len(addr_map)}} addr maps")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(replay())
'''


STRUCT_HELPERS = '''
def _u32(buf: bytes, off: int) -> int:
    return struct.unpack_from("<I", buf, off)[0]


def _u64(buf: bytes, off: int) -> int:
    return struct.unpack_from("<Q", buf, off)[0]


def _cstr(buf: bytes, off: int, maxlen: int) -> str:
    end = buf.find(b"\\x00", off, off + maxlen)
    if end < 0:
        end = off + maxlen
    return buf[off:end].decode("utf-8", errors="replace")
'''


def extract_struct_code(path: Path) -> str:
    text = path.read_text()
    start = text.find("@dataclass\nclass NewResourceIn")
    end = text.find("\nSELECTOR_DECODERS")
    if start < 0 or end < 0:
        raise ValueError(f"could not slice struct block from {path}")
    return STRUCT_HELPERS + "\n" + text[start:end].rstrip()


def extract_iokit_code(path: Path) -> str:
    text = path.read_text()
    start = text.find("KERN_SUCCESS = 0")
    if start < 0:
        raise ValueError(f"could not slice IOKit block from {path}")
    return text[start:].rstrip()


def generate(capture: Path, output: Path) -> None:
    events = load_events(capture)
    op_lines = []
    for idx, ev in enumerate(events):
        if isinstance(ev, CapOpen):
            op_lines.append(emit_open(ev, idx))
        elif isinstance(ev, CapCall):
            op_lines.append(emit_call(ev, idx))
        elif isinstance(ev, CapTrap):
            op_lines.append(emit_trap(ev, idx))

    root = Path(__file__).resolve().parent
    struct_code = extract_struct_code(root / "cap_decode.py")
    iokit_code = extract_iokit_code(root / "agx_iokit.py")

    out = STANDALONE_HEADER.format(
        capture=capture.name,
        when=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        struct_code=struct_code.rstrip(),
        iokit_code=iokit_code.rstrip(),
        ops="\n".join(op_lines),
    )
    output.write_text(out)
    print(f"wrote {output} ({len(out)} bytes, {len(events)} ops)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Decode capture.bin into standalone replay.py")
    parser.add_argument("capture", nargs="?", default="add.cap")
    parser.add_argument("-o", "--output", default="replay_add_standalone.py")
    args = parser.parse_args()

    capture = Path(args.capture)
    if not capture.exists():
        raise SystemExit(f"{capture}: not found")
    generate(capture, Path(args.output))


if __name__ == "__main__":
    main()
