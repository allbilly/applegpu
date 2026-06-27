"""AGX IOKit backend — ctypes ioctl layer."""

from __future__ import annotations

import ctypes
import ctypes.util

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
