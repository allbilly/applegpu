#!/usr/bin/env python3
"""AGX compute mul without Metal.

Workload: out[i] = a[i] * b[i] for 4 float elements (metal_mul capture).
Submits decoded IOGPU ioctl sequence: resource alloc → queue setup → trap submit.
"""
# generated from mul.cap — do not edit OPS by hand (2026-06-26 07:30 UTC)

import ctypes
import ctypes.util
import struct
import sys
from dataclasses import dataclass, field

WORKLOAD = "mul"
CLIENT_TYPE = 0x100005
EXPECTED = (10.0, 40.0, 90.0, 160.0)  # metal_mul.m


class sel:
    NEW_RESOURCE = 0x09
    QUEUE_CREATE = 0x07
    NOTIF_QUEUE = 0x10
    QUEUE_FINALIZE = 0x1C
    SHMEM = 0x0E


# ── IOGPU input structs (selector payloads) ──────────────────────

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


# Backward-compatible aliases (decode tooling).
NewResourceIn = ResourceCreateIn
NewResourceOut = ResourceCreateOut
TrapSubmitSnap = Trap0SubmitSnap

# ── IOKit backend ────────────────────────────────────────────────

KERN_SUCCESS = 0

AGX_NAMES = (
    "AGXAcceleratorG13G_B0",
    "AGXAcceleratorG13G",
    "AGXAcceleratorG14G",
    "AGXAcceleratorG15G",
    "AGXAcceleratorG16G",
    "AGXAcceleratorG17G",
)


class IOKit:
    def __init__(self) -> None:
        path = ctypes.util.find_library("IOKit")
        if not path:
            raise RuntimeError("IOKit not found")
        self.lib = ctypes.CDLL(path)

        self.lib.IOServiceNameMatching.argtypes = [ctypes.c_char_p]
        self.lib.IOServiceNameMatching.restype = ctypes.c_void_p

        self.lib.IOServiceMatching.argtypes = [ctypes.c_char_p]
        self.lib.IOServiceMatching.restype = ctypes.c_void_p

        self.lib.IOServiceGetMatchingService.argtypes = [ctypes.c_uint32, ctypes.c_void_p]
        self.lib.IOServiceGetMatchingService.restype = ctypes.c_uint32

        self.lib.IOServiceGetMatchingServices.argtypes = [
            ctypes.c_uint32, ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32),
        ]
        self.lib.IOServiceGetMatchingServices.restype = ctypes.c_int

        self.lib.IOIteratorNext.argtypes = [ctypes.c_uint32]
        self.lib.IOIteratorNext.restype = ctypes.c_uint32

        self.lib.IOObjectRelease.argtypes = [ctypes.c_uint32]
        self.lib.IOObjectRelease.restype = ctypes.c_int

        self.lib.IOServiceOpen.argtypes = [
            ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_uint32),
        ]
        self.lib.IOServiceOpen.restype = ctypes.c_int

        self.lib.IOServiceClose.argtypes = [ctypes.c_uint32]
        self.lib.IOServiceClose.restype = ctypes.c_int

        self.lib.IOConnectCallMethod.argtypes = [
            ctypes.c_uint32, ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_uint64), ctypes.c_uint32,
            ctypes.c_void_p, ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_uint64), ctypes.POINTER(ctypes.c_uint32),
            ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t),
        ]
        self.lib.IOConnectCallMethod.restype = ctypes.c_int

        self.lib.IOConnectTrap4.argtypes = [
            ctypes.c_uint32, ctypes.c_uint32,
            ctypes.c_uint64, ctypes.c_uint64, ctypes.c_uint64, ctypes.c_uint64,
        ]
        self.lib.IOConnectTrap4.restype = ctypes.c_int

        libc = ctypes.CDLL(None)
        self.mach_task_self = libc.mach_task_self
        self.mach_task_self.restype = ctypes.c_uint32

    def find_agx_service(self) -> int:
        for name in AGX_NAMES:
            match = self.lib.IOServiceNameMatching(name.encode())
            svc = self.lib.IOServiceGetMatchingService(0, match)
            if svc:
                return svc

        it = ctypes.c_uint32(0)
        match = self.lib.IOServiceMatching(b"AGXAccelerator")
        self.lib.IOServiceGetMatchingServices(0, match, ctypes.byref(it))
        svc = self.lib.IOIteratorNext(it.value)
        self.lib.IOObjectRelease(it.value)
        return svc

    def service_open(self, svc: int, client_type: int) -> tuple[int, int]:
        conn = ctypes.c_uint32(0)
        rc = self.lib.IOServiceOpen(
            svc, self.mach_task_self(), client_type, ctypes.byref(conn)
        )
        return rc, conn.value

    def connect_call(
        self,
        conn: int,
        selector: int,
        scal_in: list[int],
        struct_in: bytes | None,
        scalar_out_cnt: int,
        struct_out_sz: int,
    ) -> tuple[int, list[int], bytes, int]:
        n_in = len(scal_in)
        scal_in_arr = (ctypes.c_uint64 * n_in)(*scal_in) if n_in else None

        in_buf = None
        if struct_in:
            in_buf = ctypes.create_string_buffer(struct_in, len(struct_in))

        scal_out_arr = None
        scal_out_cnt = ctypes.c_uint32(scalar_out_cnt) if scalar_out_cnt else None
        if scal_out_cnt:
            scal_out_arr = (ctypes.c_uint64 * scal_out_cnt.value)()

        out_buf = None
        out_sz = ctypes.c_size_t(struct_out_sz) if struct_out_sz else None
        if struct_out_sz:
            out_buf = ctypes.create_string_buffer(struct_out_sz)

        rc = self.lib.IOConnectCallMethod(
            conn, selector,
            scal_in_arr, n_in,
            ctypes.cast(in_buf, ctypes.c_void_p) if in_buf else None,
            len(struct_in) if struct_in else 0,
            scal_out_arr,
            ctypes.byref(scal_out_cnt) if scal_out_cnt else None,
            ctypes.cast(out_buf, ctypes.c_void_p) if out_buf else None,
            ctypes.byref(out_sz) if out_sz else None,
        )

        scal_out = list(scal_out_arr) if scal_out_arr else []
        live_out = bytes(out_buf.raw[: out_sz.value]) if out_buf else b""
        return rc, scal_out, live_out, out_sz.value if out_sz else 0

    def connect_trap(
        self, conn: int, trap_idx: int, p1: int, p2: int, p3: int, p4: int
    ) -> int:
        return self.lib.IOConnectTrap4(conn, trap_idx, p1, p2, p3, p4)


def alloc_aligned(size: int, align: int = 16) -> tuple[ctypes.c_void_p, ctypes.CDLL]:
    libc = ctypes.CDLL(None)
    libc.posix_memalign.argtypes = [
        ctypes.POINTER(ctypes.c_void_p), ctypes.c_size_t, ctypes.c_size_t,
    ]
    libc.posix_memalign.restype = ctypes.c_int
    libc.free.argtypes = [ctypes.c_void_p]
    libc.free.restype = None

    ptr = ctypes.c_void_p()
    if libc.posix_memalign(ctypes.byref(ptr), align, size) != 0:
        raise MemoryError("posix_memalign failed")
    return ptr, libc


def open_agx(iokit: IOKit) -> tuple[int, int]:
    """Open AGXAccelerator user client. Returns (service, conn)."""
    svc = iokit.find_agx_service()
    if not svc:
        raise RuntimeError("no AGX accelerator")
    kr, conn = iokit.service_open(svc, CLIENT_TYPE)
    if kr != 0:
        raise RuntimeError(f"IOServiceOpen failed rc=0x{kr:x}")
    return svc, conn


def agx_call(
    iokit: IOKit,
    conn: int,
    selector: int,
    scalars: list[int],
    struct_in: bytes | None,
    struct_out_sz: int,
) -> tuple[int, bytes, int]:
    """One IOConnectCallMethod — ane allocate_buffer ioctl equivalent."""
    rc, _so, live_out, out_sz = iokit.connect_call(
        conn, selector, scalars, struct_in, 0, struct_out_sz,
    )
    return rc, live_out, out_sz


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

@dataclass
class OpenOp:
    client_type: int


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
        self._maps: dict[int, int] = {}

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
# ── open AGX user client ────────────────────────────────────────

    OpenOp(client_type=CLIENT_TYPE,  # op 0
    ),
# ── resource setup (sel NEW_RESOURCE) ───────────────────────────

    CallOp(  # op 1: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(type_version=0x10001, create_flags=0x1000101, alloc_size=33840, heap_flags=0x10000, stride_or_count=0x38000000, create_info=24),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(gpu_va=0x1008bc000, gpu_va2=0x1004900c0, slot_index=1, heap_size=0x10000, cookie=0x2e449382, type_tag=0x29c98, out_heap_flags=0x10000),
    ),
    CallOp(  # op 2: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(type_version=0x10001, create_flags=0x1000101, alloc_size=1136, suballoc_flag=1, heap_flags=0x20000, backing_ptr=0x10ace4be0),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid_tag=21, gpu_va=0x104f6c000, gpu_va2=0x100490180, slot_index=2, heap_size=0x20000, cookie=0x2e449383, type_tag=0x29c99, out_heap_flags=0x20000),
    ),
    CallOp(  # op 3: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, type_version=0x10001, create_flags=0x1000101, alloc_size=3120, parent_gpu_va=0x104f6c000, parent_gpu_va2=0x104f6c000, heap_flags=0x20000, heap_lane=2, backing_ptr=0x10ace4be0),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid_tag=21, gpu_va2=0x100490240, slot_index=3, heap_size=0x20000, cookie=0x2e449384, type_tag=0x29c99, out_heap_flags=0x20000),
    ),
    CallOp(  # op 4: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, type_version=0x10001, create_flags=0x1000101, alloc_size=3120, parent_gpu_va=0x104f6c100, parent_gpu_va2=0x104f6c000, heap_flags=0x20000, heap_lane=2, backing_ptr=0x10ace4be0),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=256, rid_tag=21, gpu_va2=0x100490300, slot_index=4, heap_size=0x20000, cookie=0x2e449385, type_tag=0x29c99, out_heap_flags=0x1ff00),
    ),
    CallOp(  # op 5: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, type_version=0x10001, create_flags=0x1000101, alloc_size=3120, parent_gpu_va=0x104f6c200, parent_gpu_va2=0x104f6c000, heap_flags=0x20000, heap_lane=2),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=512, rid_tag=21, gpu_va2=0x1004903c0, slot_index=5, heap_size=0x20000, cookie=0x2e449386, type_tag=0x29c99, out_heap_flags=0x1fe00),
    ),
# ── queue setup (sel QUEUE_CREATE / NOTIF_QUEUE / FINALIZE) ─────

    CallOp(  # op 6: QUEUE_CREATE
        selector=sel.QUEUE_CREATE,
        scalars=[],
        struct_in=QueueCreateIn(exe_path='metal_mul', queue_flags=2, unk_mask=0xffffffff, enable=1),
        struct_out_sz=16,
        cap_out=QueueCreateOut(queue_id=1, cookie=0x2e449387),
    ),
    CallOp(  # op 7: NOTIF_QUEUE
        selector=sel.NOTIF_QUEUE,
        scalars=NotifQueueIn(ring_size=256, ring_flags=40).as_scalars(),
        struct_in=None,
        struct_out_sz=16,
        cap_out=ShmemOut(gpu_va=0x1008f0000, size=1),
    ),
    CallOp(  # op 8: QUEUE_FINALIZE
        selector=sel.QUEUE_FINALIZE,
        scalars=QueueFinalizeIn(arg0=1, arg1=1).as_scalars(),
        struct_in=None,
        struct_out_sz=0,
    ),
# ── resource setup (sel NEW_RESOURCE) ───────────────────────────

    CallOp(  # op 9: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, type_version=0x10001, create_flags=0x1000101, alloc_size=3120, parent_gpu_va=0x104f6c300, parent_gpu_va2=0x104f6c000, heap_flags=0x20000, heap_lane=2, create_info=24, backing_ptr=0x10ace54a0),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=768, rid_tag=21, gpu_va2=0x100490480, slot_index=6, heap_size=0x20000, cookie=0x2e44938b, type_tag=0x29c99, out_heap_flags=0x1fd00),
    ),
    CallOp(  # op 10: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, type_version=0x10001, create_flags=0x1000101, alloc_size=3120, parent_gpu_va=0x104f6c500, parent_gpu_va2=0x104f6c000, heap_flags=0x20000, heap_lane=2, create_info=24, backing_ptr=0x10ace54a0),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=1280, rid_tag=21, gpu_va2=0x100490540, slot_index=7, heap_size=0x20000, cookie=0x2e44938c, type_tag=0x29c99, out_heap_flags=0x1fb00),
    ),
    CallOp(  # op 11: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, type_version=0x10001, create_flags=0x1000101, alloc_size=3120, parent_gpu_va=0x104f6c700, parent_gpu_va2=0x104f6c000, heap_flags=0x20000, heap_lane=2, create_info=24, backing_ptr=0x10ace54a0),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=1792, rid_tag=21, gpu_va2=0x100490600, slot_index=8, heap_size=0x20000, cookie=0x2e44938d, type_tag=0x29c99, out_heap_flags=0x1f900),
    ),
    CallOp(  # op 12: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, type_version=0x10001, create_flags=0x1000101, alloc_size=3120, parent_gpu_va=0x104f6c800, parent_gpu_va2=0x104f6c000, heap_flags=0x20000, heap_lane=2, create_info=24, backing_ptr=0x75ac8e210),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=2048, rid_tag=21, gpu_va2=0x1004906c0, slot_index=9, heap_size=0x20000, cookie=0x2e44938e, type_tag=0x29c99, out_heap_flags=0x1f800),
    ),
    CallOp(  # op 13: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, type_version=0x10001, create_flags=0x1000101, alloc_size=3120, parent_gpu_va=0x104f6e800, parent_gpu_va2=0x104f6c000, heap_flags=0x20000, heap_lane=2, create_info=24, backing_ptr=0x75ac8e298),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=10240, rid_tag=21, gpu_va2=0x100490780, slot_index=10, heap_size=0x20000, cookie=0x2e44938f, type_tag=0x29c99, out_heap_flags=0x1d800),
    ),
    CallOp(  # op 14: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, type_version=0x10001, create_flags=0x1000101, alloc_size=3120, parent_gpu_va=0x104f6e900, parent_gpu_va2=0x104f6c000, heap_flags=0x20000, heap_lane=2, create_info=24, backing_ptr=0x75ac8e5b8),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=10496, rid_tag=21, gpu_va2=0x100490840, slot_index=11, heap_size=0x20000, cookie=0x2e449390, type_tag=0x29c99, out_heap_flags=0x1d700),
    ),
    CallOp(  # op 15: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, type_version=0x10001, create_flags=0x1000101, alloc_size=3120, parent_gpu_va=0x104f6f900, parent_gpu_va2=0x104f6c000, heap_flags=0x20000, heap_lane=2, create_info=24, backing_ptr=0x75ac8e8d8),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=14592, rid_tag=21, gpu_va2=0x100490900, slot_index=12, heap_size=0x20000, cookie=0x2e449391, type_tag=0x29c99, out_heap_flags=0x1c700),
    ),
    CallOp(  # op 16: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, type_version=0x10001, create_flags=0x1000101, alloc_size=3120, parent_gpu_va=0x104f6fa00, parent_gpu_va2=0x104f6c000, heap_flags=0x20000, heap_lane=2, create_info=24, backing_ptr=0x75ac8ebe0),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=14848, rid_tag=21, gpu_va2=0x1004909c0, slot_index=13, heap_size=0x20000, cookie=0x2e449392, type_tag=0x29c99, out_heap_flags=0x1c600),
    ),
    CallOp(  # op 17: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, type_version=0x10001, create_flags=0x1000101, alloc_size=3120, parent_gpu_va=0x104f6fb00, parent_gpu_va2=0x104f6c000, heap_flags=0x20000, heap_lane=2, create_info=24, backing_ptr=0x75ac8eee8),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=15104, rid_tag=21, gpu_va2=0x100490a80, slot_index=14, heap_size=0x20000, cookie=0x2e449393, type_tag=0x29c99, out_heap_flags=0x1c500),
    ),
    CallOp(  # op 18: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(type_version=0x10001, create_flags=0x1000101, alloc_size=1072, heap_flags=0x10000, stride_or_count=0x8000000, create_info=24),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x28000, rid_tag=21, gpu_va=0x104f8c000, gpu_va2=0x100490b40, slot_index=15, heap_size=0x10000, cookie=0x2e449394, type_tag=0x29c9d, out_heap_flags=0x10000),
    ),
    CallOp(  # op 19: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, type_version=0x10001, create_flags=0x1000101, alloc_size=3120, parent_gpu_va=0x104f6fc00, parent_gpu_va2=0x104f6c000, heap_flags=0x20000, heap_lane=2, create_info=24, backing_ptr=0x10ace4be0),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=15360, rid_tag=21, gpu_va2=0x100490c00, slot_index=16, heap_size=0x20000, cookie=0x2e449395, type_tag=0x29c99, out_heap_flags=0x1c400),
    ),
    CallOp(  # op 20: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(type_version=0x10001, create_flags=0x1000101, alloc_size=1136, suballoc_flag=1, heap_flags=0x20000, backing_ptr=0x10ace4be0),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x40000, rid_tag=21, gpu_va=0x104f9c000, gpu_va2=0x100490cc0, slot_index=17, heap_size=0x20000, cookie=0x2e449396, type_tag=0x29c9e, out_heap_flags=0x20000),
    ),
    CallOp(  # op 21: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(parent_handle=128, type_version=0x10001, create_flags=0x1000101, alloc_size=3120, parent_gpu_va=0x104f9c000, parent_gpu_va2=0x104f9c000, heap_flags=0x20000, heap_lane=17, create_info=24, backing_ptr=0x75ac8c000),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x40000, rid_tag=21, gpu_va2=0x100490d80, slot_index=18, heap_size=0x20000, cookie=0x2e449397, type_tag=0x29c9e, out_heap_flags=0x20000),
    ),
# ── shared memory (sel SHMEM) ───────────────────────────────────

    CallOp(  # op 22: SHMEM
        selector=sel.SHMEM,
        scalars=ShmemIn(size=16384).as_scalars(),
        struct_in=None,
        struct_out_sz=16,
        cap_out=ShmemOut(gpu_va=0x1008f4000, size=16384, shmem_id=1),
    ),
    CallOp(  # op 23: SHMEM
        selector=sel.SHMEM,
        scalars=ShmemIn(size=16384, map_flags=1).as_scalars(),
        struct_in=None,
        struct_out_sz=16,
        cap_out=ShmemOut(gpu_va=0x1008f8000, size=16384, shmem_id=2),
    ),
# ── resource setup (sel NEW_RESOURCE) ───────────────────────────

    CallOp(  # op 24: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(type_version=0x18000, create_flags=0x1000101, alloc_size=17456, heap_flags=32768, stride_or_count=0x8000000, create_info=72),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x68000, rid_tag=21, gpu_va=0x104fbc000, gpu_va2=0x100490e40, slot_index=19, heap_size=32768, cookie=0x2f449398, type_tag=0x29c9f, out_heap_flags=32768),
    ),
    CallOp(  # op 25: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(type_version=0x18000, create_flags=0x1000101, alloc_size=50224, heap_flags=32768, stride_or_count=0x48000000),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x18000, gpu_va=0x104fc4000, gpu_va2=0x100490f00, slot_index=20, heap_size=32768, cookie=0x2f449399, type_tag=0x29ca0, out_heap_flags=32768),
    ),
    CallOp(  # op 26: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(type_version=0x18000, create_flags=0x1000101, alloc_size=17456, heap_flags=32768, stride_or_count=0x8000000),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x78000, rid_tag=21, gpu_va=0x104fcc000, gpu_va2=0x100490fc0, slot_index=21, heap_size=32768, cookie=0x2f44939a, type_tag=0x29ca1, out_heap_flags=32768),
    ),
    CallOp(  # op 27: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(type_version=0x18000, create_flags=0x1000101, alloc_size=17456, heap_flags=32768, stride_or_count=0x8000000, create_info=64),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x88000, rid_tag=21, gpu_va=0x104fd4000, gpu_va2=0x100491080, slot_index=22, heap_size=32768, cookie=0x2f44939b, type_tag=0x29ca2, out_heap_flags=32768),
    ),
    CallOp(  # op 28: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(type_version=0x18000, create_flags=0x1000101, alloc_size=17456, heap_flags=32768, stride_or_count=0x8000000),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0x98000, rid_tag=21, gpu_va=0x104fdc000, gpu_va2=0x100491140, slot_index=23, heap_size=32768, cookie=0x2f44939c, type_tag=0x29ca3, out_heap_flags=32768),
    ),
    CallOp(  # op 29: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(type_version=0x18000, create_flags=0x1000101, alloc_size=17456, heap_flags=32768, stride_or_count=0x8000000),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0xa8000, rid_tag=21, gpu_va=0x104fe4000, gpu_va2=0x100491200, slot_index=24, heap_size=32768, cookie=0x2f44939d, type_tag=0x29ca4, out_heap_flags=32768),
    ),
    CallOp(  # op 30: NEW_RESOURCE
        selector=sel.NEW_RESOURCE,
        scalars=[],
        struct_in=ResourceCreateIn(type_version=0x1ff80, create_flags=0x1000101, alloc_size=17456, heap_flags=65408, stride_or_count=0x18000000),
        struct_out_sz=88,
        cap_out=ResourceCreateOut(rid=0xb8000, rid_tag=21, gpu_va=0x104fec000, gpu_va2=0x1004912c0, slot_index=25, heap_size=0x10000, cookie=0x2f44939e, type_tag=0x29ca5, out_heap_flags=0x10000),
    ),
# ── submit (trap0) ──────────────────────────────────────────────

    TrapOp(  # op 31
        trap_idx=0,
        p1=1,
        p2=64,
        use_p4=True,
        snap=Trap0SubmitSnap(buf_count=2, submit_flags=1, cmdbuf_gpu_va=0x75b044e10, cmdbuf_aux_va=0x75b044e40),
    ),
]


def execute_op(
    iokit: IOKit,
    conn: int,
    addr_map: AddrMap,
    idx: int,
    op: OpenOp | CallOp | TrapOp,
    verbose: bool,
) -> int:
    """Run one captured op. Returns 1 on failure, 0 on success."""
    if isinstance(op, OpenOp):
        if verbose:
            print(f"[{idx}] IOServiceOpen type=0x{op.client_type:x} (already open)")
        return 0

    if isinstance(op, CallOp):
        raw = op.pack_struct_in()
        buf = bytearray(raw) if raw else bytearray()
        if buf:
            addr_map.patch_u64_buf(buf)
        rc, live_out, out_sz = agx_call(
            iokit, conn, op.selector, op.scalars,
            bytes(buf) if buf else None, op.struct_out_sz,
        )
        if verbose:
            print(f"[{idx}] sel=0x{op.selector:02x} rc=0x{rc:x} out_sz={out_sz}")
        if rc == 0 and op.cap_out is not None:
            cap_raw = getattr(op.cap_out, "raw", b"")
            if not cap_raw and hasattr(op.cap_out, "pack"):
                cap_raw = op.cap_out.pack()
            if cap_raw:
                addr_map.learn_resource_maps(cap_raw, live_out)
        return 1 if rc != 0 else 0

    if isinstance(op, TrapOp):
        snap = bytearray(op.snap.pack())
        addr_map.patch_u64_buf(snap)
        rc = submit_task(
            iokit, conn, op.trap_idx, op.p1, op.p2, bytes(snap), op.use_p4,
        )
        if verbose:
            print(f"[{idx}] trap{op.trap_idx} rc=0x{rc:x} snap={len(snap)} bytes")
        return 1 if rc != 0 else 0

    return 1


def run_workload(*, verbose: bool = False, submit: bool = True) -> int:
    """Open device, replay OPS, return failure count."""
    if not submit:
        print(f"{WORKLOAD}: {len(OPS)} ops (dry-run, no IOKit)")
        for idx, op in enumerate(OPS):
            kind = type(op).__name__
            if isinstance(op, CallOp):
                print(f"  [{idx}] {kind} sel=0x{op.selector:02x}")
            elif isinstance(op, TrapOp):
                print(f"  [{idx}] {kind} trap{op.trap_idx}")
            else:
                print(f"  [{idx}] {kind}")
        return 0

    iokit = IOKit()
    addr_map = AddrMap()
    svc = conn = 0
    fails = 0
    print(f"{WORKLOAD}: replaying {len(OPS)} ops")

    try:
        svc, conn = open_agx(iokit)
        if verbose:
            print(f"[0] IOServiceOpen type=0x{CLIENT_TYPE:x} conn=0x{conn:x} rc=0x0")

        for idx, op in enumerate(OPS):
            if isinstance(op, OpenOp):
                continue
            fails += execute_op(iokit, conn, addr_map, idx, op, verbose)
    finally:
        close_agx(iokit, svc, conn)

    if verbose:
        print(f"addr maps: {len(addr_map)}")
    return fails


def verify(fails: int) -> None:
    if WORKLOAD in ("add", "mul"):
        print(f"expected={list(EXPECTED)}")
    elif WORKLOAD == "tri":
        print(f"expected_center_BGRA={EXPECTED_CENTER_BGRA}")
    if fails == 0:
        print("PASS")
    else:
        print(f"FAIL ({fails} ioctl errors)")


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
