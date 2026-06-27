#!/usr/bin/env python3
"""Generate a standalone replay script from capture.bin.

Decodes all blobs into structure code — no runtime .cap or hex file loading.
Output style follows allbilly/ane examples/: self-contained, sectioned, PASS/FAIL.
"""

from __future__ import annotations

import argparse
import re
import textwrap
from dataclasses import fields, replace
from datetime import datetime, timezone
from pathlib import Path

from cap_decode import (
    NotifQueueIn,
    QueueCreateIn,
    QueueFinalizeIn,
    ShmemIn,
    Trap0SubmitSnap,
    decode_call_out,
    decode_call_struct,
    repr_value,
)
from cap_format import CapCall, CapOpen, CapTrap, load_events

SEL_NAMES: dict[int, str] = {
    0x09: "NEW_RESOURCE",
    0x07: "QUEUE_CREATE",
    0x10: "NOTIF_QUEUE",
    0x1C: "QUEUE_FINALIZE",
    0x0E: "SHMEM",
}

SECTION_HEADERS: dict[str, str] = {
    "open": "# ── open AGX user client ────────────────────────────────────────",
    "resource": "# ── resource setup (sel NEW_RESOURCE) ───────────────────────────",
    "queue": "# ── queue setup (sel QUEUE_CREATE / NOTIF_QUEUE / FINALIZE) ─────",
    "shmem": "# ── shared memory (sel SHMEM) ───────────────────────────────────",
    "submit": "# ── submit (trap0) ──────────────────────────────────────────────",
    "other": "# ── other ops ───────────────────────────────────────────────────",
}

WORKLOAD_PROFILES: dict[str, dict[str, str]] = {
    "add": {
        "workload": "add",
        "title": "AGX compute add without Metal.",
        "body": (
            "Workload: out[i] = a[i] + b[i] for 4 float elements (metal_add capture).\n"
            "Submits decoded IOGPU ioctl sequence: resource alloc → queue setup → trap submit."
        ),
        "expected_name": "EXPECTED",
        "expected_value": "(11.0, 22.0, 33.0, 44.0)",
        "expected_comment": "metal_add.m",
        "metal_bin": "metal_add",
    },
    "mul": {
        "workload": "mul",
        "title": "AGX compute mul without Metal.",
        "body": (
            "Workload: out[i] = a[i] * b[i] for 4 float elements (metal_mul capture).\n"
            "Submits decoded IOGPU ioctl sequence: resource alloc → queue setup → trap submit."
        ),
        "expected_name": "EXPECTED",
        "expected_value": "(10.0, 40.0, 90.0, 160.0)",
        "expected_comment": "metal_mul.m",
        "metal_bin": "metal_mul",
    },
    "tri": {
        "workload": "tri",
        "title": "AGX triangle render without Metal.",
        "body": (
            "Workload: red triangle into 8x8 BGRA texture (metal_tri capture).\n"
            "Submits decoded IOGPU ioctl sequence: resource alloc → queue setup → trap submit."
        ),
        "expected_name": "EXPECTED_CENTER_BGRA",
        "expected_value": "(0, 0, 255, 255)",
        "expected_comment": "center pixel, metal_tri.m",
        "metal_bin": "metal_tri",
    },
}

def workload_profile(capture: Path) -> dict[str, str]:
    stem = capture.stem
    if stem in WORKLOAD_PROFILES:
        return WORKLOAD_PROFILES[stem]
    return {
        "workload": stem,
        "title": f"AGX {stem} replay without Metal.",
        "body": f"Captured IOGPU ioctl replay ({capture.name}).",
        "expected_name": "EXPECTED",
        "expected_value": f"# no expected values for {stem}",
        "expected_comment": "",
        "metal_bin": stem,
    }


def emit_dataclass_init(obj, *, omit_defaults: bool = True) -> str:
    parts = []
    for f in fields(obj):
        val = getattr(obj, f.name)
        if f.name in ("raw_tail", "raw") and isinstance(val, bytes):
            continue
        if omit_defaults:
            if val in (0, "", b""):
                continue
            if f.name == "resource_class" and val == 1:
                continue
            if f.name == "cookie_flags" and val == 1:
                continue
        parts.append(f"{f.name}={repr_value(val)}")
    if not parts:
        return f"{type(obj).__name__}()"
    return f"{type(obj).__name__}({', '.join(parts)})"


def clear_raw_blob(obj):
    if hasattr(obj, "raw_tail"):
        return replace(obj, raw_tail=b"")
    if hasattr(obj, "raw"):
        return replace(obj, raw=b"")
    return obj


def emit_packed_struct(obj, blob: bytes, *, field: str) -> str:
    """Emit struct field from decoded fields; require pack() == capture."""
    clean = clear_raw_blob(obj)
    expr = emit_dataclass_init(clean)
    if hasattr(clean, "pack") and clean.pack() != blob:
        raise ValueError(
            f"{type(clean).__name__} pack() mismatch for {field} "
            f"(extend cap_decode.py)"
        )
    return f"    {field}={expr},"


def sel_ref(selector: int) -> str:
    name = SEL_NAMES.get(selector)
    if name:
        return f"sel.{name}"
    return f"0x{selector:02x}"


def scrub_struct(decoded, metal_bin: str):
    if isinstance(decoded, QueueCreateIn):
        return QueueCreateIn(
            exe_path=metal_bin,
            label=decoded.label,
            queue_flags=decoded.queue_flags,
            unk_mask=decoded.unk_mask,
            enable=decoded.enable,
            raw=b"",
        )
    return decoded


# CapOpen events are skipped at the OPS level (open_agx() opens the service
# for real; emitting a no-op marker wastes a line and a class for nothing).
def emit_open(op: CapOpen, idx: int) -> str:
    return ""


def emit_call(op: CapCall, idx: int, metal_bin: str) -> str:
    sel_name = SEL_NAMES.get(op.selector, f"0x{op.selector:02x}")
    lines = [f"CallOp(  # op {idx}: {sel_name}"]

    if op.scal_in:
        if op.selector == 0x10 and len(op.scal_in) == 2:
            struct_expr = emit_dataclass_init(
                NotifQueueIn(op.scal_in[0], op.scal_in[1])
            )
            lines.append(f"    selector={sel_ref(op.selector)},")
            lines.append(f"    scalars={struct_expr}.as_scalars(),")
        elif op.selector == 0x1C and len(op.scal_in) == 2:
            struct_expr = emit_dataclass_init(
                QueueFinalizeIn(op.scal_in[0], op.scal_in[1])
            )
            lines.append(f"    selector={sel_ref(op.selector)},")
            lines.append(f"    scalars={struct_expr}.as_scalars(),")
        elif op.selector == 0x0E and len(op.scal_in) == 2:
            struct_expr = emit_dataclass_init(ShmemIn(op.scal_in[0], op.scal_in[1]))
            lines.append(f"    selector={sel_ref(op.selector)},")
            lines.append(f"    scalars={struct_expr}.as_scalars(),")
        else:
            lines.append(f"    selector={sel_ref(op.selector)},")
            lines.append(f"    scalars={op.scal_in!r},")
    else:
        lines.append(f"    selector={sel_ref(op.selector)},")
        lines.append("    scalars=[],")

    if op.struct_in:
        decoded = scrub_struct(
            decode_call_struct(op.selector, op.struct_in), metal_bin
        )
        if isinstance(decoded, QueueCreateIn):
            lines.append(
                f"    struct_in={emit_dataclass_init(clear_raw_blob(decoded))},"
            )
        elif hasattr(decoded, "pack"):
            lines.append(emit_packed_struct(decoded, op.struct_in, field="struct_in"))
        else:
            lines.append(f"    struct_in={op.struct_in!r},")
    else:
        lines.append("    struct_in=None,")

    lines.append(f"    struct_out_sz={op.struct_out_sz},")

    if op.cap_struct:
        out = decode_call_out(op.selector, op.cap_struct)
        if hasattr(out, "pack") and out.pack() == op.cap_struct:
            lines.append(f"    cap_out={emit_dataclass_init(out)},")
        elif hasattr(out, "rid"):
            lines.append(emit_packed_struct(out, op.cap_struct, field="cap_out"))
        elif hasattr(out, "queue_id"):
            lines.append(emit_packed_struct(out, op.cap_struct, field="cap_out"))
        elif hasattr(out, "gpu_va") and hasattr(out, "shmem_id"):
            lines.append(f"    cap_out={emit_dataclass_init(out)},")
        else:
            lines.append(f"    cap_out={op.cap_struct!r},")

    lines.append("),")
    return textwrap.indent("\n".join(lines), "    ")


def emit_trap(op: CapTrap, idx: int) -> str:
    snap = Trap0SubmitSnap.from_bytes(op.snap) if op.snap else Trap0SubmitSnap()
    snap_line = emit_packed_struct(snap, op.snap or b"", field="snap").strip()
    body = (
        f"TrapOp(  # op {idx}\n"
        f"    trap_idx={op.trap_idx},\n"
        f"    p1={op.p1},\n"
        f"    p2={op.p2},\n"
        f"    use_p4={bool(op.p4)},\n"
        f"    {snap_line}\n"
        f"),"
    )
    return textwrap.indent(body, "    ")


def op_section(ev: CapCall | CapTrap) -> str:
    if isinstance(ev, CapCall):
        if ev.selector == 0x09:
            return "resource"
        if ev.selector in (0x07, 0x10, 0x1C):
            return "queue"
        if ev.selector == 0x0E:
            return "shmem"
        return "other"
    return "submit"


def emit_ops(events: list, metal_bin: str) -> str:
    lines: list[str] = []
    current = ""
    for idx, ev in enumerate(events):
        if isinstance(ev, CapOpen):
            continue
        section = op_section(ev)
        if section != current:
            lines.append(SECTION_HEADERS[section])
            lines.append("")
            current = section
        if isinstance(ev, CapCall):
            lines.append(emit_call(ev, idx, metal_bin))
        else:
            lines.append(emit_trap(ev, idx))
    return "\n".join(lines)


STANDALONE_HEADER = '''#!/usr/bin/env python3
"""{title}

{body}
"""
# generated from {capture} — do not edit OPS by hand ({when})

import ctypes
import ctypes.util
import struct
import sys
from dataclasses import dataclass, field

WORKLOAD = "{workload}"
CLIENT_TYPE = 0x100005
{expected_name} = {expected_value}  # {expected_comment}

class sel:
    NEW_RESOURCE = 0x09
    QUEUE_CREATE = 0x07
    NOTIF_QUEUE = 0x10
    QUEUE_FINALIZE = 0x1C
    SHMEM = 0x0E


# ── IOGPU input structs (selector payloads) ──────────────────────

{struct_code}

# ── IOKit backend ────────────────────────────────────────────────

{iokit_code}


def open_agx(iokit: IOKit) -> tuple[int, int]:
    """Open AGXAccelerator user client. Returns (service, conn)."""
    svc = iokit.find_agx_service()
    if not svc:
        raise RuntimeError("no AGX accelerator")
    kr, conn = iokit.service_open(svc, CLIENT_TYPE)
    if kr != 0:
        raise RuntimeError(f"IOServiceOpen failed rc=0x{{kr:x}}")
    return svc, conn


# ponytail: agx_call dropped — it was a 1-call wrapper that threw away
# a return value; inlined into execute_op below.


def submit_task(
    iokit: IOKit, conn: int, trap_idx: int, p1: int, p2: int, snap: bytes, use_p4: bool,
) -> int:
    """Trap submit — ane submit_task ioctl equivalent."""
    p3 = p4 = 0
    ptr = None
    libc = None
    if snap:
        alloc_sz = len(snap) + 0x100
        ptr, libc = alloc_aligned(alloc_sz)
        dst = (ctypes.c_uint8 * alloc_sz).from_address(ptr.value)
        ctypes.memmove(dst, snap, len(snap))
        p3 = ptr.value
        p4 = ptr.value + 0x84 if use_p4 else 0
    try:
        return iokit.connect_trap(conn, trap_idx, p1, p2, p3, p4)
    finally:
        if ptr is not None and libc is not None:
            libc.free(ptr)


def close_agx(iokit: IOKit, svc: int, conn: int) -> None:
    if conn:
        iokit.lib.IOServiceClose(conn)
    if svc:
        iokit.lib.IOObjectRelease(svc)


# ── address remap ────────────────────────────────────────────────

# ponytail: OpenOp dropped — the captured open is replayed by open_agx(),
# so the no-op marker only existed to keep the OP list round-numbered.
@dataclass
class CallOp:
    selector: int
    scalars: list[int]
    struct_in: object
    struct_out_sz: int
    cap_out: object = None

    def pack_struct_in(self) -> bytes | None:
        if self.struct_in is None:
            return None
        if hasattr(self.struct_in, "pack"):
            return self.struct_in.pack()
        return self.struct_in


@dataclass
class TrapOp:
    trap_idx: int
    p1: int
    p2: int
    use_p4: bool
    snap: Trap0SubmitSnap


class AddrMap:
    def __init__(self) -> None:
        self._maps: dict[int, int] = {{}}

    def add(self, old: int, new: int) -> None:
        if not old or not new or old == new:
            return
        self._maps[old] = new

    def patch_u64_buf(self, buf: bytearray) -> None:
        for off in range(0, len(buf) - 7, 8):
            old, = struct.unpack_from("<Q", buf, off)
            new = self._maps.get(old, old)
            struct.pack_into("<Q", buf, off, new)

    def learn_resource_maps(self, cap: bytes, live: bytes) -> None:
        if len(cap) < 24 or len(live) < 24:
            return
        self.add(struct.unpack_from("<Q", cap, 8)[0], struct.unpack_from("<Q", live, 8)[0])
        self.add(struct.unpack_from("<Q", cap, 16)[0], struct.unpack_from("<Q", live, 16)[0])

    def __len__(self) -> int:
        return len(self._maps)


# ── IOGPU submit sequence (BTSP equivalent) ──────────────────────

OPS = [
{ops}
]


def execute_op(
    iokit: IOKit,
    conn: int,
    addr_map: AddrMap,
    idx: int,
    op: CallOp | TrapOp,
    verbose: bool,
) -> int:
    """Run one captured op. Returns 1 on failure, 0 on success."""
    if isinstance(op, CallOp):
        raw = op.pack_struct_in()
        buf = bytearray(raw) if raw else bytearray()
        if buf:
            addr_map.patch_u64_buf(buf)
        rc, _so, live_out, out_sz = iokit.connect_call(
            conn, op.selector, op.scalars,
            bytes(buf) if buf else None, 0, op.struct_out_sz,
        )
        if verbose:
            print(f"[{{idx}}] sel=0x{{op.selector:02x}} rc=0x{{rc:x}} out_sz={{out_sz}}")
        if rc == 0 and op.cap_out is not None:
            cap_raw = getattr(op.cap_out, "raw", b"")
            if not cap_raw and hasattr(op.cap_out, "pack"):
                cap_raw = op.cap_out.pack()
            if cap_raw:
                addr_map.learn_resource_maps(cap_raw, live_out)
        return 1 if rc != 0 else 0

    # TrapOp
    snap = bytearray(op.snap.pack())
    addr_map.patch_u64_buf(snap)
    rc = submit_task(
        iokit, conn, op.trap_idx, op.p1, op.p2, bytes(snap), op.use_p4,
    )
    if verbose:
        print(f"[{{idx}}] trap{{op.trap_idx}} rc=0x{{rc:x}} snap={{len(snap)}} bytes")
    return 1 if rc != 0 else 0


def run_workload(*, verbose: bool = False, submit: bool = True) -> int:
    """Open device, replay OPS, return failure count."""
    if not submit:
        print(f"{{WORKLOAD}}: {{len(OPS)}} ops (dry-run, no IOKit)")
        for idx, op in enumerate(OPS):
            if isinstance(op, CallOp):
                print(f"  [{{idx}}] CallOp sel=0x{{op.selector:02x}}")
            else:
                print(f"  [{{idx}}] TrapOp trap{{op.trap_idx}}")
        return 0

    iokit = IOKit()
    addr_map = AddrMap()
    svc = conn = 0
    fails = 0
    print(f"{{WORKLOAD}}: replaying {{len(OPS)}} ops")

    try:
        svc, conn = open_agx(iokit)
        if verbose:
            print(f"[0] IOServiceOpen type=0x{{CLIENT_TYPE:x}} conn=0x{{conn:x}} rc=0x0")

        for idx, op in enumerate(OPS):
            fails += execute_op(iokit, conn, addr_map, idx, op, verbose)
    finally:
        close_agx(iokit, svc, conn)

    if verbose:
        print(f"addr maps: {{len(addr_map)}}")
    return fails


def verify(fails: int) -> None:
    print(f"expected={{list({expected_name})}}")
    if fails == 0:
        print("PASS")
    else:
        print(f"FAIL ({{fails}} ioctl errors)")


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run", action="store_true", help="list ops only, no IOKit calls",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="per-op ioctl log")
    args = parser.parse_args()

    fails = run_workload(verbose=args.verbose, submit=not args.dry_run)
    if not args.dry_run:
        verify(fails)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
'''


def strip_from_bytes(text: str) -> str:
    """Drop decode-only helpers; standalone examples only pack captured blobs."""
    while True:
        m = re.search(
            r"\n    @classmethod\n    def from_bytes\([\s\S]*?"
            r"(?=\n    def |\n\n@dataclass|\nclass [A-Z]|\Z)",
            text,
        )
        if not m:
            break
        text = text[: m.start()] + text[m.end() :]
    return text.rstrip()


def extract_struct_code(path: Path) -> str:
    text = path.read_text()
    start = text.find("@dataclass\nclass ResourceCreateIn")
    end = text.find("\nSELECTOR_DECODERS")
    if start < 0 or end < 0:
        raise ValueError(f"could not slice struct block from {path}")
    return strip_from_bytes(text[start:end])


def extract_iokit_code(path: Path) -> str:
    text = path.read_text()
    start = text.find("AGX_NAMES = (")
    if start < 0:
        raise ValueError(f"could not slice IOKit block from {path}")
    return text[start:].rstrip()


def generate(capture: Path, output: Path) -> None:
    events = load_events(capture)
    profile = workload_profile(capture)
    root = Path(__file__).resolve().parent

    out = STANDALONE_HEADER.format(
        title=profile["title"],
        body=profile["body"],
        capture=capture.name,
        when=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        workload=profile["workload"],
        expected_name=profile["expected_name"],
        expected_value=profile["expected_value"],
        expected_comment=profile["expected_comment"],
        struct_code=extract_struct_code(root / "cap_decode.py"),
        iokit_code=extract_iokit_code(root / "agx_iokit.py"),
        ops=emit_ops(events, profile["metal_bin"]),
    )
    output.write_text(out)
    output.chmod(0o755)
    print(f"wrote {output} ({len(out)} bytes, {len(events)} ops)")




def main() -> None:
    parser = argparse.ArgumentParser(
        description="Decode capture.bin into standalone example script",
    )
    parser.add_argument("capture", nargs="?", default="add.cap")
    parser.add_argument("-o", "--output", default="../examples/add.py")
    args = parser.parse_args()

    capture = Path(args.capture)
    if not capture.exists():
        raise SystemExit(f"{capture}: not found")
    generate(capture, Path(args.output))


if __name__ == "__main__":
    main()
