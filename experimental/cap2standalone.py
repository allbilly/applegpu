#!/usr/bin/env python3
"""Generate a standalone replay script from capture.bin.

Decodes all blobs into structure code — no runtime .cap or hex file loading.
Output style follows allbilly/ane examples/: self-contained, sectioned, PASS/FAIL.
"""

from __future__ import annotations

import argparse
import ast
import base64
import re
import struct
import textwrap
import zlib
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
from cap_format import (
    CAP_MEMORY_EXPECTED,
    CAP_MEMORY_RESOURCE,
    CAP_MEMORY_TRAP_AUX,
    CapCall,
    CapMemory,
    CapOpen,
    CapTrap,
    load_events,
)

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
    "result": "# ── GPU result validation ───────────────────────────────────────",
    "other": "# ── other ops ───────────────────────────────────────────────────",
}

WORKLOAD_PROFILES: dict[str, dict[str, str]] = {
    "add": {
        "workload": "add",
        "title": "AGX compute add without Metal.",
        "body": (
            "Workload: out[i] = a[i] + b[i] for 4 float elements (metal_add capture).\n"
            "Restores captured mappings, submits the decoded IOGPU sequence, then validates "
            "the CPU-visible result."
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
            "Restores captured mappings, submits the decoded IOGPU sequence, then validates "
            "the CPU-visible result."
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
            "Restores captured mappings, submits the decoded IOGPU sequence, then validates "
            "the CPU-visible center pixel."
        ),
        "expected_name": "EXPECTED_CENTER_BGRA",
        "expected_value": "(0, 0, 255, 255)",
        "expected_comment": "center pixel, metal_tri.m",
        "metal_bin": "metal_tri",
    },
}


def validate_capture(events: list, profile: dict[str, str]) -> None:
    memories = [event for event in events if isinstance(event, CapMemory)]
    expected = [event for event in memories if event.kind == CAP_MEMORY_EXPECTED]
    resources = [event for event in memories if event.kind == CAP_MEMORY_RESOURCE]
    aux = [event for event in memories if event.kind == CAP_MEMORY_TRAP_AUX]
    traps = [event for event in events if isinstance(event, CapTrap)]

    if len(expected) != 1:
        raise ValueError(f"capture must contain exactly one expected output, got {len(expected)}")
    if traps and len(aux) < 2:
        raise ValueError("trap capture is missing its userspace callback descriptors")

    result = expected[0]
    owner = next(
        (
            memory for memory in resources
            if memory.address <= result.address
            and result.address + len(result.data) <= memory.address + len(memory.data)
        ),
        None,
    )
    if owner is None:
        raise ValueError("expected output is outside every captured resource mapping")
    offset = result.address - owner.address
    initial = owner.data[offset : offset + len(result.data)]
    if initial == result.data:
        raise ValueError("captured output already matched before submission (false-positive check)")

    workload = profile["workload"]
    if workload in ("add", "mul"):
        captured_value = tuple(struct.unpack("<4f", result.data))
    elif workload == "tri":
        captured_value = tuple(result.data)
    else:
        return
    declared_value = ast.literal_eval(profile["expected_value"])
    if captured_value != declared_value:
        raise ValueError(
            f"captured result {captured_value!r} != declared result {declared_value!r}"
        )


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
        if omit_defaults and val == f.default:
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
    if op.expected_rc:
        lines.append(f"    expected_rc={op.expected_rc},")

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
    lines = [
        f"TrapOp(  # op {idx}",
        f"    trap_idx={op.trap_idx},",
        f"    p1={op.p1},",
        f"    p2={op.p2},",
        f"    p4_offset={op.p4 - op.p3 if op.p4 and op.p3 else 0},",
    ]
    if op.expected_rc:
        lines.append(f"    expected_rc={op.expected_rc},")
    lines.extend((f"    {snap_line}", "),"))
    body = "\n".join(lines)
    return textwrap.indent(body, "    ")


def emit_memory(op: CapMemory, idx: int, offset: int) -> str:
    kind_names = {
        CAP_MEMORY_RESOURCE: "MEMORY_RESOURCE",
        CAP_MEMORY_TRAP_AUX: "MEMORY_TRAP_AUX",
        CAP_MEMORY_EXPECTED: "MEMORY_EXPECTED",
    }
    kind = kind_names.get(op.kind, str(op.kind))
    return textwrap.indent(
        "\n".join((
            f"MemoryOp(  # op {idx}",
            f"    kind={kind},",
            f"    address=0x{op.address:x},",
            f"    offset=0x{offset:x},",
            f"    size=0x{len(op.data):x},",
            "),",
        )),
        "    ",
    )


def op_section(ev: CapCall | CapTrap | CapMemory) -> str:
    if isinstance(ev, CapMemory):
        if ev.kind == CAP_MEMORY_EXPECTED:
            return "result"
        if ev.kind == CAP_MEMORY_TRAP_AUX:
            return "submit"
        return "resource"
    if isinstance(ev, CapCall):
        if ev.selector == 0x09:
            return "resource"
        if ev.selector in (0x07, 0x10, 0x1C):
            return "queue"
        if ev.selector == 0x0E:
            return "shmem"
        return "other"
    return "submit"


def emit_ops(events: list, metal_bin: str, memory_offsets: dict[int, int]) -> str:
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
        elif isinstance(ev, CapTrap):
            lines.append(emit_trap(ev, idx))
        else:
            lines.append(emit_memory(ev, idx, memory_offsets[id(ev)]))
    return "\n".join(lines)


def emit_memory_image(events: list) -> tuple[str, dict[int, int]]:
    image = bytearray()
    offsets: dict[int, int] = {}
    for event in events:
        if not isinstance(event, CapMemory):
            continue
        offsets[id(event)] = len(image)
        image.extend(event.data)

    packed = base64.b85encode(zlib.compress(bytes(image), level=9)).decode("ascii")
    lines = [repr(packed[i : i + 100]) for i in range(0, len(packed), 100)]
    if not lines:
        lines = [repr("")]
    return "\n".join(f"    {line}" for line in lines), offsets


STANDALONE_HEADER = '''#!/usr/bin/env python3
"""{title}

{body}
"""
# generated from {capture} — do not edit OPS by hand ({when})

import ctypes
import ctypes.util
import base64
import os
import platform
import struct
import sys
import time
import zlib
from dataclasses import dataclass, field

WORKLOAD = "{workload}"
CLIENT_TYPE = 0x100005
{expected_name} = {expected_value}  # {expected_comment}

MEMORY_RESOURCE = 1
MEMORY_TRAP_AUX = 2
MEMORY_EXPECTED = 3

_MEMORY_IMAGE = zlib.decompress(base64.b85decode(
{memory_image}
))

class sel:
    NEW_RESOURCE = 0x09
    QUEUE_CREATE = 0x07
    NOTIF_QUEUE = 0x10
    QUEUE_FINALIZE = 0x1C
    SHMEM = 0x0E


# ── semantic trace (style follows allbilly/nvgpu add.py) ─────────

TRACE = int(os.environ.get("AGX_TRACE", "1") or 0)
TRACE_MAXDUMP = int(os.environ.get("AGX_TRACE_MAXDUMP", "128") or 128)

SELECTOR_NAMES = {{
    sel.NEW_RESOURCE: "NEW_RESOURCE",
    sel.QUEUE_CREATE: "QUEUE_CREATE",
    sel.NOTIF_QUEUE: "NOTIF_QUEUE",
    sel.QUEUE_FINALIZE: "QUEUE_FINALIZE",
    sel.SHMEM: "SHMEM",
}}

STAGES = (
    "IOKit Client",
    "Resource + Queue Setup",
    "Trap Submit",
    "Result Validation",
)

_TRACE_EPOCH = time.perf_counter()
_trace_event_id = 0
_trace_stage = 0
_trace_substage = 0
_trace_stage_started = _TRACE_EPOCH
_trace_status: dict[int, tuple[str, str, float]] = {{}}


def _fmt_rc(rc: int) -> str:
    return "SUCCESS" if rc == 0 else f"0x{{rc & 0xffffffff:08x}}"


def _fmt_value(value: object) -> str:
    if isinstance(value, int):
        return str(value) if 0 <= value < 10 else f"0x{{value:x}}"
    if isinstance(value, bytes):
        return f"bytes[{{len(value)}}]"
    return repr(value)


def describe_struct(value: object) -> str:
    if value is None:
        return "-"
    names = getattr(value, "__dataclass_fields__", None)
    if not names:
        return f"{{type(value).__name__}}[{{len(value)}}]" if isinstance(value, bytes) else repr(value)
    parts = []
    for name in names:
        item = getattr(value, name)
        if name in ("raw", "raw_tail"):
            if item:
                parts.append(f"{{name}}=bytes[{{len(item)}}]")
            continue
        if item not in (0, "", b"", False):
            parts.append(f"{{name}}={{_fmt_value(item)}}")
    return f"{{type(value).__name__}}({{', '.join(parts)}})"


def describe_call_input(selector: int, scalars: list[int], value: object) -> str:
    if isinstance(value, ResourceCreateIn):
        parts = [f"alloc=0x{{value.alloc_size:x}}", f"type=0x{{value.type_version:x}}"]
        if value.parent_handle:
            parts.append(f"parent=0x{{value.parent_handle:x}}")
        if value.parent_gpu_va:
            parts.append(f"parent_va=0x{{value.parent_gpu_va:x}}")
        if value.heap_flags:
            parts.append(f"heap=0x{{value.heap_flags:x}}")
        if value.backing_ptr:
            parts.append(f"backing_ptr=0x{{value.backing_ptr:x}}")
        return " ".join(parts)
    if isinstance(value, QueueCreateIn):
        return (
            f"exe={{value.exe_path!r}} label={{value.label!r}} "
            f"flags=0x{{value.queue_flags:x}} enable={{value.enable}}"
        )
    if selector == sel.NOTIF_QUEUE and len(scalars) >= 2:
        return f"ring_size=0x{{scalars[0]:x}} flags=0x{{scalars[1]:x}}"
    if selector == sel.QUEUE_FINALIZE and len(scalars) >= 2:
        return f"queue={{scalars[0]}} finalize={{scalars[1]}}"
    if selector == sel.SHMEM and len(scalars) >= 2:
        return f"size=0x{{scalars[0]:x}} flags=0x{{scalars[1]:x}}"
    return "scalars=[" + ", ".join(f"0x{{item:x}}" for item in scalars) + "]"


def describe_live_out(template: object, data: bytes) -> str:
    if isinstance(template, ResourceCreateOut) and len(data) >= 88:
        rid, rid_tag = struct.unpack_from("<II", data, 0)
        gpu_va, gpu_va2 = struct.unpack_from("<QQ", data, 8)
        slot = struct.unpack_from("<I", data, 0x24)[0]
        heap_size = struct.unpack_from("<Q", data, 0x28)[0]
        return (
            f"ResourceCreateOut(rid=0x{{rid:x}}, tag={{rid_tag}}, "
            f"gpu_va=0x{{gpu_va:x}}, gpu_va2=0x{{gpu_va2:x}}, "
            f"slot={{slot}}, heap=0x{{heap_size:x}})"
        )
    if isinstance(template, QueueCreateOut) and len(data) >= 16:
        queue_id = struct.unpack_from("<I", data, 0)[0]
        cookie = struct.unpack_from("<Q", data, 8)[0]
        return f"QueueCreateOut(queue_id={{queue_id}}, cookie=0x{{cookie:x}})"
    if isinstance(template, NotifQueueOut) and len(data) >= 16:
        ring_address, queue_id, _reserved = struct.unpack_from("<QII", data, 0)
        return f"NotifQueueOut(ring=0x{{ring_address:x}}, queue_id={{queue_id}})"
    if isinstance(template, ShmemOut) and len(data) >= 16:
        gpu_va, size, shmem_id = struct.unpack_from("<QII", data, 0)
        return f"ShmemOut(gpu_va=0x{{gpu_va:x}}, size=0x{{size:x}}, id={{shmem_id}})"
    return f"bytes[{{len(data)}}]"


def trace(tag: str, message: str, *, event: int | None = None, level: int = 1) -> None:
    if TRACE < level:
        return
    stage = f"S{{_trace_stage}}" if _trace_stage else "S-"
    if event is not None and _trace_substage:
        stage += f".{{_trace_substage}}"
    event_label = f"[E{{event:06d}}]" if event is not None else ""
    elapsed_ms = (time.perf_counter() - _TRACE_EPOCH) * 1000
    print(f"[{{stage}}]{{event_label}} {{tag:<5}} +{{elapsed_ms:9.3f}}ms {{message}}", flush=True)


def trace_blob(tag: str, data: bytes, *, event: int) -> None:
    if TRACE < 2 or not data:
        return
    shown = data[:TRACE_MAXDUMP]
    suffix = f" ... +{{len(data) - len(shown)}} bytes" if len(shown) < len(data) else ""
    trace(tag, shown.hex(" ") + suffix, event=event, level=2)


def trace_event() -> int:
    global _trace_event_id, _trace_substage
    _trace_event_id += 1
    _trace_substage += 1
    return _trace_event_id


def trace_reset() -> None:
    global _TRACE_EPOCH, _trace_event_id, _trace_stage
    global _trace_substage, _trace_stage_started
    _TRACE_EPOCH = time.perf_counter()
    _trace_event_id = 0
    _trace_stage = 0
    _trace_substage = 0
    _trace_stage_started = _TRACE_EPOCH
    _trace_status.clear()


def stage_set(number: int, note: str) -> None:
    global _trace_stage, _trace_substage, _trace_stage_started
    if TRACE and _trace_stage:
        print(flush=True)
    _trace_stage = number
    _trace_substage = 0
    _trace_stage_started = time.perf_counter()
    trace("CTX", note)


def stage_finish(ok: bool, note: str) -> None:
    elapsed_ms = (time.perf_counter() - _trace_stage_started) * 1000
    _trace_status[_trace_stage] = ("OK" if ok else "FAIL", note, elapsed_ms)


def trace_summary() -> None:
    if not TRACE:
        return
    print("\\n" + "=" * 72)
    print(f"{{'APPLE GPU REPLAY':^72}}")
    print("=" * 72)
    for number, name in enumerate(STAGES, 1):
        state, note, elapsed_ms = _trace_status.get(number, ("----", "", 0.0))
        timing = f"{{elapsed_ms:8.3f}} ms" if state != "----" else "          "
        extra = f"  {{note}}" if note else ""
        print(f"[S{{number}}] {{name:<28}} {{state:<4}} {{timing}}{{extra}}")
    print("=" * 72)


def format_result(data: bytes) -> str:
    if WORKLOAD in ("add", "mul") and len(data) % 4 == 0:
        values = struct.unpack(f"<{{len(data) // 4}}f", data)
        return "result=" + repr(tuple(round(value, 6) for value in values))
    if WORKLOAD == "tri":
        return "center_bgra=" + repr(tuple(data))
    return "result_bytes=" + data.hex(" ")


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
    iokit: IOKit, conn: int, trap_idx: int, p1: int, p2: int, snap: bytes,
    p4_offset: int, allocations: list[tuple[object, object]],
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
        p4 = ptr.value + p4_offset if 0 < p4_offset < alloc_sz else 0
        allocations.append((ptr, libc))
    return iokit.connect_trap(conn, trap_idx, p1, p2, p3, p4)


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
    expected_rc: int = 0

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
    p4_offset: int
    snap: Trap0SubmitSnap
    expected_rc: int = 0


@dataclass
class MemoryOp:
    kind: int
    address: int
    offset: int
    size: int

    def bytes(self) -> bytes:
        return _MEMORY_IMAGE[self.offset : self.offset + self.size]


class AddrMap:
    def __init__(self) -> None:
        self._maps: dict[int, int] = {{}}
        self._ranges: list[tuple[int, int, int]] = []

    def add(self, old: int, new: int) -> bool:
        if not old or not new:
            return False
        if self._maps.get(old) == new:
            return False
        self._maps[old] = new
        return True

    def add_range(self, old: int, new: int, size: int) -> bool:
        if not old or not new or not size:
            return False
        learned = self.add(old, new)
        entry = (old, new, size)
        if entry not in self._ranges:
            self._ranges.append(entry)
            learned = True
        return learned

    def remap(self, value: int) -> int:
        exact = self._maps.get(value)
        if exact is not None:
            return exact
        for old, new, size in self._ranges:
            if old <= value < old + size:
                return new + (value - old)
        return value

    def contains(self, value: int) -> bool:
        if value in self._maps:
            return True
        return any(old <= value < old + size for old, _new, size in self._ranges)

    def patch_u64_buf(self, buf: bytearray) -> list[tuple[int, int, int]]:
        patched = []
        for off in range(0, len(buf) - 7, 4):
            old, = struct.unpack_from("<Q", buf, off)
            new = self.remap(old)
            if new != old:
                struct.pack_into("<Q", buf, off, new)
                patched.append((off, old, new))
        return patched

    def learn_resource_maps(self, cap: bytes, live: bytes) -> list[tuple[int, int]]:
        if len(cap) < 24 or len(live) < 24:
            return []
        learned = []
        old = struct.unpack_from("<Q", cap, 8)[0]
        new = struct.unpack_from("<Q", live, 8)[0]
        size = struct.unpack_from("<Q", cap, 0x28)[0] if len(cap) >= 0x30 else 0
        if self.add_range(old, new, size):
            learned.append((old, new))
        old = struct.unpack_from("<Q", cap, 16)[0]
        new = struct.unpack_from("<Q", live, 16)[0]
        if self.add(old, new):
            learned.append((old, new))
        return learned

    def learn_shmem_maps(
        self, cap: bytes, live: bytes, size: int | None = None,
    ) -> list[tuple[int, int]]:
        if len(cap) < 8 or len(live) < 8:
            return []
        old = struct.unpack_from("<Q", cap, 0)[0]
        new = struct.unpack_from("<Q", live, 0)[0]
        if size is None:
            size = struct.unpack_from("<I", cap, 8)[0] if len(cap) >= 12 else 0
        return [(old, new)] if self.add_range(old, new, size) else []

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
    op: CallOp | TrapOp | MemoryOp,
    verbose: bool,
    allocations: list[tuple[object, object]],
    observed_outputs: list[bytes],
) -> int:
    """Run one captured op. Returns 1 when live behavior mismatches capture."""
    event = trace_event()
    if isinstance(op, CallOp):
        raw = op.pack_struct_in()
        prepared = prepare_call_struct(op.selector, raw)
        buf = bytearray(prepared) if prepared else bytearray()
        patched = addr_map.patch_u64_buf(buf) if buf else []
        name = SELECTOR_NAMES.get(op.selector, f"SEL_0x{{op.selector:02x}}")
        input_summary = describe_call_input(op.selector, op.scalars, op.struct_in)
        trace(
            "CALL",
            f"op={{idx + 1}} {{name}} sel=0x{{op.selector:02x}} "
            f"{{input_summary}} struct={{len(buf)}}B -> {{op.struct_out_sz}}B",
            event=event,
        )
        trace("ARGS", describe_struct(op.struct_in), event=event, level=2)
        if prepared != raw:
            trace(
                "PATCH", "macOS 27 QUEUE_CREATE tail: (0xffffffff, 1) -> (1, 0)",
                event=event,
            )
        if patched:
            details = ", ".join(
                f"+0x{{off:x}} 0x{{old:x}}->0x{{new:x}}"
                for off, old, new in patched
            )
            trace("PATCH", f"{{len(patched)}} pointer(s): {{details}}", event=event, level=2)
        trace_blob("IN", bytes(buf), event=event)
        started = time.perf_counter()
        rc, _so, live_out, out_sz = iokit.connect_call(
            conn, op.selector, op.scalars,
            bytes(buf) if buf else None, 0, op.struct_out_sz,
        )
        elapsed_ms = (time.perf_counter() - started) * 1000
        matches = rc == op.expected_rc and out_sz == op.struct_out_sz
        trace(
            "RET",
            f"{{_fmt_rc(rc)}} expected={{_fmt_rc(op.expected_rc)}} "
            f"size={{out_sz}}/{{op.struct_out_sz}}B "
            f"out={{describe_live_out(op.cap_out, live_out)}} time={{elapsed_ms:.3f}}ms "
            f"{{'OK' if matches else 'MISMATCH'}}",
            event=event,
        )
        trace_blob("OUT", live_out, event=event)
        if rc == 0 and op.cap_out is not None:
            cap_raw = getattr(op.cap_out, "raw", b"")
            if not cap_raw and hasattr(op.cap_out, "pack"):
                cap_raw = op.cap_out.pack()
            if cap_raw:
                if op.selector == sel.NEW_RESOURCE:
                    learned = addr_map.learn_resource_maps(cap_raw, live_out)
                elif op.selector == sel.SHMEM:
                    learned = addr_map.learn_shmem_maps(cap_raw, live_out)
                elif op.selector == sel.NOTIF_QUEUE:
                    learned = addr_map.learn_shmem_maps(cap_raw, live_out, 0x4000)
                else:
                    learned = []
                for old, new in learned:
                    trace("MAP", f"GPU VA 0x{{old:x}} -> 0x{{new:x}}", event=event)
        return 0 if matches else 1

    if isinstance(op, MemoryOp):
        data = op.bytes()
        if len(data) != op.size:
            trace(
                "FAIL", f"memory image truncated: {{len(data)}}/{{op.size}}B",
                event=event,
            )
            return 1

        if op.kind == MEMORY_TRAP_AUX:
            ptr, libc = alloc_aligned(op.size + 0x10)
            addr_map.add_range(op.address, ptr.value, op.size)
            buf = bytearray(data)
            patched = addr_map.patch_u64_buf(buf)
            ctypes.memmove(ptr.value, bytes(buf), len(buf))
            allocations.append((ptr, libc))
            trace(
                "AUX", f"trap descriptor 0x{{op.address:x}} -> 0x{{ptr.value:x}} "
                f"({{op.size}}B, {{len(patched)}} patches)",
                event=event,
            )
            trace_blob("MEM", bytes(buf), event=event)
            return 0

        target = addr_map.remap(op.address)
        if not addr_map.contains(op.address):
            trace("FAIL", f"unmapped memory address 0x{{op.address:x}}", event=event)
            return 1

        if op.kind == MEMORY_RESOURCE:
            buf = bytearray(data)
            patched = addr_map.patch_u64_buf(buf)
            ctypes.memmove(target, bytes(buf), len(buf))
            trace(
                "LOAD", f"0x{{op.address:x}} -> 0x{{target:x}} "
                f"size=0x{{op.size:x}} patches={{len(patched)}}",
                event=event,
            )
            trace_blob("MEM", bytes(buf), event=event)
            return 0

        if op.kind == MEMORY_EXPECTED:
            trace(
                "WAIT", f"GPU output @0x{{target:x}} size={{op.size}}B "
                f"timeout=5.0s",
                event=event,
            )
            deadline = time.monotonic() + 5.0
            actual = b""
            while time.monotonic() < deadline:
                actual = ctypes.string_at(target, op.size)
                if actual == data:
                    observed_outputs.append(actual)
                    trace("DATA", format_result(actual), event=event)
                    trace("PASS", "GPU output matched captured result", event=event)
                    return 0
                time.sleep(0.001)
            observed_outputs.append(actual)
            trace("DATA", format_result(actual), event=event)
            trace(
                "FAIL", f"expected {{format_result(data)}}",
                event=event,
            )
            return 1

        trace("FAIL", f"unknown memory kind {{op.kind}}", event=event)
        return 1

    # TrapOp
    snap = bytearray(op.snap.pack())
    patched = addr_map.patch_u64_buf(snap)
    record_type, flags = struct.unpack_from("<II", snap, 0)
    callback0, callback1 = struct.unpack_from("<QQ", snap, 0x10)
    trace(
        "TRAP",
        f"op={{idx + 1}} trap{{op.trap_idx}} p1=0x{{op.p1:x}} p2=0x{{op.p2:x}} "
        f"record_type={{record_type}} flags=0x{{flags:x}} "
        f"callback0=0x{{callback0:x}} callback1=0x{{callback1:x}}",
        event=event,
    )
    if patched:
        details = ", ".join(
            f"+0x{{off:x}} 0x{{old:x}}->0x{{new:x}}"
            for off, old, new in patched
        )
        trace("PATCH", f"{{len(patched)}} pointer(s): {{details}}", event=event, level=2)
    trace_blob("SNAP", bytes(snap), event=event)
    started = time.perf_counter()
    rc = submit_task(
        iokit, conn, op.trap_idx, op.p1, op.p2, bytes(snap),
        op.p4_offset, allocations,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000
    matches = rc == op.expected_rc
    trace(
        "RET",
        f"trap{{op.trap_idx}} {{_fmt_rc(rc)}} expected={{_fmt_rc(op.expected_rc)}} "
        f"time={{elapsed_ms:.3f}}ms {{'OK' if matches else 'MISMATCH'}}",
        event=event,
    )
    return 0 if matches else 1


def run_workload(*, verbose: bool = False, submit: bool = True) -> tuple[int, list[bytes]]:
    """Open device, replay OPS, and return (mismatches, observed outputs)."""
    global TRACE
    if verbose:
        TRACE = max(TRACE, 2)
    if not submit:
        print(f"{{WORKLOAD}}: {{len(OPS)}} ops (dry-run, no IOKit)")
        for idx, op in enumerate(OPS):
            if isinstance(op, CallOp):
                name = SELECTOR_NAMES.get(op.selector, f"SEL_0x{{op.selector:02x}}")
                print(f"  [{{idx + 1}}] CallOp {{name}} sel=0x{{op.selector:02x}}")
            elif isinstance(op, MemoryOp):
                names = {{
                    MEMORY_RESOURCE: "resource",
                    MEMORY_TRAP_AUX: "trap-aux",
                    MEMORY_EXPECTED: "expected",
                }}
                print(
                    f"  [{{idx + 1}}] MemoryOp {{names.get(op.kind, op.kind)}} "
                    f"address=0x{{op.address:x}} size=0x{{op.size:x}}"
                )
            else:
                print(f"  [{{idx + 1}}] TrapOp trap{{op.trap_idx}}")
        return 0, []

    trace_reset()
    addr_map = AddrMap()
    iokit = None
    svc = conn = 0
    setup_fails = 0
    trap_fails = 0
    result_fails = 0
    submit_started = False
    result_started = False
    allocations: list[tuple[object, object]] = []
    observed_outputs: list[bytes] = []
    print(f"{{WORKLOAD}}: replaying {{len(OPS)}} ops")

    stage_set(1, f"open AGX user client type=0x{{CLIENT_TYPE:x}}")
    try:
        iokit = IOKit()
        svc, conn = open_agx(iokit)
        trace("OPEN", f"service=0x{{svc:x}} conn=0x{{conn:x}} SUCCESS")
        stage_finish(True, f"service=0x{{svc:x}}, conn=0x{{conn:x}}")
        stage_set(2, "replay captured resource, queue, and shared-memory setup")

        for idx, op in enumerate(OPS):
            if isinstance(op, TrapOp) and not submit_started:
                stage_finish(
                    setup_fails == 0,
                    f"{{idx}} setup ops, {{setup_fails}} mismatches, {{len(addr_map)}} VA maps",
                )
                stage_set(3, "submit captured command buffer through IOConnectTrap4")
                submit_started = True
            if (
                isinstance(op, MemoryOp)
                and op.kind == MEMORY_EXPECTED
                and not result_started
            ):
                stage_finish(
                    trap_fails == 0,
                    f"{{sum(isinstance(item, TrapOp) for item in OPS)}} trap(s), "
                    f"{{trap_fails}} mismatches",
                )
                stage_set(4, "wait for and compare CPU-visible GPU output")
                result_started = True
            failed = execute_op(
                iokit, conn, addr_map, idx, op, verbose,
                allocations, observed_outputs,
            )
            if isinstance(op, TrapOp):
                trap_fails += failed
            elif isinstance(op, MemoryOp) and op.kind == MEMORY_EXPECTED:
                result_fails += failed
            else:
                setup_fails += failed

        if result_started:
            stage_finish(
                result_fails == 0,
                f"{{len(observed_outputs)}} output check(s), {{result_fails}} mismatches",
            )
        elif submit_started:
            stage_finish(trap_fails == 0, f"{{trap_fails}} trap mismatches")
            stage_set(4, "no expected output in capture")
            stage_finish(False, "missing GPU output record")
            result_fails += 1
        else:
            stage_finish(setup_fails == 0, f"{{len(OPS)}} calls, no trap captured")
            stage_set(3, "no trap operation in capture")
            stage_finish(False, "missing trap operation")
            trap_fails += 1
            stage_set(4, "no expected output in capture")
            stage_finish(False, "missing GPU output record")
            result_fails += 1
    except Exception as exc:
        stage_finish(False, f"{{type(exc).__name__}}: {{exc}}")
        raise
    finally:
        if iokit is not None:
            close_agx(iokit, svc, conn)
        for ptr, libc in allocations:
            libc.free(ptr)

    trace("CLOSE", f"released conn=0x{{conn:x}} service=0x{{svc:x}}", level=2)
    return setup_fails + trap_fails + result_fails, observed_outputs


def verify(fails: int, observed_outputs: list[bytes]) -> None:
    if observed_outputs:
        print(format_result(observed_outputs[-1]))
    if fails == 0:
        print("PASS (GPU output and all IOKit results matched)")
    else:
        print(f"expected={{list({expected_name})}}")
        print(f"FAIL ({{fails}} replay mismatch(es))")


def main() -> int:
    global TRACE
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run", action="store_true", help="list ops only, no IOKit calls",
    )
    parser.add_argument(
        "--trace", type=int, choices=(0, 1, 2),
        help="trace level (default: AGX_TRACE or 1)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="same as --trace 2",
    )
    args = parser.parse_args()

    if args.trace is not None:
        TRACE = args.trace
    if args.verbose:
        TRACE = max(TRACE, 2)

    try:
        fails, observed_outputs = run_workload(
            verbose=args.verbose, submit=not args.dry_run,
        )
        if not args.dry_run:
            verify(fails, observed_outputs)
        return 1 if fails else 0
    finally:
        if not args.dry_run:
            trace_summary()


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
    validate_capture(events, profile)
    root = Path(__file__).resolve().parent
    memory_image, memory_offsets = emit_memory_image(events)

    out = STANDALONE_HEADER.format(
        title=profile["title"],
        body=profile["body"],
        capture=capture.name,
        when=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        workload=profile["workload"],
        expected_name=profile["expected_name"],
        expected_value=profile["expected_value"],
        expected_comment=profile["expected_comment"],
        memory_image=memory_image,
        struct_code=extract_struct_code(root / "cap_decode.py"),
        iokit_code=extract_iokit_code(root / "agx_iokit.py"),
        ops=emit_ops(events, profile["metal_bin"], memory_offsets),
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
