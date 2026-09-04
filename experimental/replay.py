#!/usr/bin/env python3
"""Replay AGX capture.bin without Metal.

Design reference only (not imported or loaded at runtime):
  github.com/allbilly/nvgpu  — load_events + patch + queue submit
  github.com/allbilly/rk3588 — ctypes ioctl structs + submit()
  github.com/allbilly/ane    — DRM ioctl + buffer remap in Python
"""

from __future__ import annotations

import argparse
import ctypes
import sys
import time
from pathlib import Path

from agx_iokit import IOKit, alloc_aligned
from cap_format import (
    CAP_CALL,
    CAP_OPEN,
    CAP_TRAP,
    CAP_MEMORY,
    CAP_MEMORY_EXPECTED,
    CAP_MEMORY_RESOURCE,
    CAP_MEMORY_TRAP_AUX,
    AddrMap,
    CapCall,
    CapMemory,
    CapOpen,
    CapTrap,
    CaptureReader,
    load_events,
)

ROOT = Path(__file__).resolve().parent


def format_event(idx: int, event: CapOpen | CapCall | CapTrap | CapMemory) -> str:
    if isinstance(event, CapOpen):
        return f"[{idx}] OPEN type=0x{event.client_type:x} cap_conn=0x{event.cap_conn:x}"
    if isinstance(event, CapCall):
        return (
            f"[{idx}] CALL sel=0x{event.selector:02x} "
            f"sin={len(event.scal_in)} sisz={len(event.struct_in)} "
            f"sout={event.scalar_out_cnt} sosz={event.struct_out_sz}"
        )
    if isinstance(event, CapTrap):
        return (
            f"[{idx}] TRAP{event.trap_idx} p1=0x{event.p1:x} p2=0x{event.p2:x} "
            f"snap={len(event.snap)}"
        )
    return (
        f"[{idx}] MEMORY kind={event.kind} address=0x{event.address:x} "
        f"size=0x{len(event.data):x}"
    )


def replay_call(
    iokit: IOKit,
    conn: int,
    call: CapCall,
    addr_map: AddrMap,
    idx: int,
    submit: bool,
) -> bool:
    struct_in = bytearray(call.struct_in)
    addr_map.patch_u64_buf(struct_in)

    if not submit:
        print(
            f"{format_event(idx, call)} "
            f"(dry-run, would patch {len(struct_in)}-byte struct)"
        )
        return True

    rc, _scal_out, live_out, out_sz = iokit.connect_call(
        conn,
        call.selector,
        call.scal_in,
        bytes(struct_in) if struct_in else None,
        call.scalar_out_cnt,
        call.struct_out_sz,
    )
    print(
        f"[{idx}] sel=0x{call.selector:02x} rc=0x{rc:x} "
        f"(expected 0x{call.expected_rc & 0xffffffff:x}) out_sz={out_sz}"
    )
    matches = rc == call.expected_rc and out_sz == call.struct_out_sz
    if rc == 0 and call.cap_struct:
        if call.selector == 0x09:
            addr_map.learn_resource_maps(call.cap_struct, live_out)
        elif call.selector == 0x0E:
            addr_map.learn_shmem_maps(call.cap_struct, live_out)
        elif call.selector == 0x10:
            addr_map.learn_shmem_maps(call.cap_struct, live_out, 0x4000)
    return matches


def replay_trap(
    iokit: IOKit,
    conn: int,
    trap: CapTrap,
    addr_map: AddrMap,
    idx: int,
    submit: bool,
    allocations: list[tuple[ctypes.c_void_p, ctypes.CDLL]],
) -> bool:
    snap = bytearray(trap.snap)
    addr_map.patch_u64_buf(snap)

    if not submit:
        print(f"{format_event(idx, trap)} (dry-run)")
        return True

    p3 = p4 = 0
    ptr = None
    libc = None
    if snap:
        alloc_sz = len(snap) + 0x100
        ptr, libc = alloc_aligned(alloc_sz)
        dst = (ctypes.c_uint8 * alloc_sz).from_address(ptr.value)
        ctypes.memmove(dst, bytes(snap), len(snap))
        p3 = ptr.value
        p4_off = trap.p4 - trap.p3 if trap.p4 and trap.p3 else 0
        p4 = ptr.value + p4_off if 0 < p4_off < alloc_sz else 0
        allocations.append((ptr, libc))

    rc = iokit.connect_trap(conn, trap.trap_idx, trap.p1, trap.p2, p3, p4)
    print(
        f"[{idx}] trap{trap.trap_idx} rc=0x{rc:x} "
        f"(expected 0x{trap.expected_rc & 0xffffffff:x}) snap={len(snap)} bytes"
    )
    return rc == trap.expected_rc


def replay_memory(
    memory: CapMemory,
    addr_map: AddrMap,
    idx: int,
    allocations: list[tuple[ctypes.c_void_p, ctypes.CDLL]],
) -> bool:
    if memory.kind == CAP_MEMORY_TRAP_AUX:
        ptr, libc = alloc_aligned(len(memory.data) + 0x10)
        addr_map.add_range(memory.address, ptr.value, len(memory.data))
        buf = bytearray(memory.data)
        addr_map.patch_u64_buf(buf)
        ctypes.memmove(ptr.value, bytes(buf), len(buf))
        allocations.append((ptr, libc))
        print(
            f"[{idx}] trap aux 0x{memory.address:x} -> 0x{ptr.value:x} "
            f"({len(buf)} bytes)"
        )
        return True

    target = addr_map.remap(memory.address)
    if not addr_map.contains(memory.address):
        print(f"[{idx}] memory address 0x{memory.address:x} was not remapped")
        return False

    if memory.kind == CAP_MEMORY_RESOURCE:
        buf = bytearray(memory.data)
        addr_map.patch_u64_buf(buf)
        ctypes.memmove(target, bytes(buf), len(buf))
        print(
            f"[{idx}] restored 0x{len(buf):x} bytes "
            f"0x{memory.address:x} -> 0x{target:x}"
        )
        return True

    if memory.kind == CAP_MEMORY_EXPECTED:
        deadline = time.monotonic() + 5.0
        actual = b""
        while time.monotonic() < deadline:
            actual = ctypes.string_at(target, len(memory.data))
            if actual == memory.data:
                print(
                    f"[{idx}] output PASS @0x{target:x}: "
                    f"{actual.hex(' ')}"
                )
                return True
            time.sleep(0.001)
        print(
            f"[{idx}] output FAIL @0x{target:x}: got {actual.hex(' ')}, "
            f"expected {memory.data.hex(' ')}"
        )
        return False

    print(f"[{idx}] unknown memory kind {memory.kind}")
    return False


def replay_file(path: Path, submit: bool = True) -> int:
    events = load_events(path)
    print(f"loaded {len(events)} events from {path}")

    if not submit:
        for idx, event in enumerate(events):
            print(format_event(idx, event))
        print("dry-run only (pass without --dry-run to replay through IOKit)")
        return 0

    iokit = IOKit()
    addr_map = AddrMap()
    svc = iokit.find_agx_service()
    if not svc:
        print("no AGX accelerator", file=sys.stderr)
        return 1

    conn = 0
    idx = 0
    fails = 0
    allocations: list[tuple[ctypes.c_void_p, ctypes.CDLL]] = []

    print(f"replaying {path}")
    try:
        reader = CaptureReader(path.read_bytes())
        reader.read_hdr()
        while True:
            op_type = reader.peek_type()
            if op_type is None or op_type == 0:
                break

            if op_type == CAP_OPEN:
                open_ev = reader.read_open()
                if not conn:
                    kr, conn = iokit.service_open(svc, open_ev.client_type)
                    print(
                        f"[{idx}] IOServiceOpen type=0x{open_ev.client_type:x} "
                        f"conn=0x{conn:x} rc=0x{kr:x} "
                        f"(expected 0x{open_ev.expected_rc & 0xffffffff:x})"
                    )
                    if kr != open_ev.expected_rc:
                        fails += 1
                    if kr != 0:
                        return 1
                else:
                    print(f"[{idx}] skip duplicate open")
                idx += 1

            elif op_type == CAP_CALL:
                if not conn:
                    print("call before open", file=sys.stderr)
                    return 1
                call = reader.read_call()
                fails += not replay_call(iokit, conn, call, addr_map, idx, submit=True)
                idx += 1

            elif op_type == CAP_TRAP:
                if not conn:
                    print("trap before open", file=sys.stderr)
                    return 1
                trap = reader.read_trap()
                fails += not replay_trap(
                    iokit, conn, trap, addr_map, idx, submit=True,
                    allocations=allocations,
                )
                idx += 1

            elif op_type == CAP_MEMORY:
                memory = reader.read_memory()
                fails += not replay_memory(memory, addr_map, idx, allocations)
                idx += 1

            else:
                print(f"bad type {op_type} at op {idx}", file=sys.stderr)
                return 1
    finally:
        if conn:
            iokit.lib.IOServiceClose(conn)
        iokit.lib.IOObjectRelease(svc)
        for ptr, libc in allocations:
            libc.free(ptr)

    print(f"done: {idx} ops, {fails} failures, {len(addr_map)} addr maps")
    return 1 if fails else 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Replay captured AGX IOKit traffic."
    )
    parser.add_argument(
        "capture",
        nargs="?",
        default=str(ROOT / "add.cap"),
        help="capture.bin path (default: ./add.cap)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="parse and dump events only, no IOKit calls",
    )
    args = parser.parse_args()

    path = Path(args.capture)
    if not path.exists():
        print(f"{path}: not found", file=sys.stderr)
        sys.exit(1)

    sys.exit(replay_file(path, submit=not args.dry_run))


if __name__ == "__main__":
    main()
