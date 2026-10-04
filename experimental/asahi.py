#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Standalone M1 Asahi DRM bring-up. Python standard library only.

    python3 asahi.py add
    python3 asahi.py mul
    python3 asahi.py tri
    python3 asahi.py --dry-run

The scalar shaders were compiled offline with Mesa 25.3.6, then disassembled
with dougallj/applegpu. Compute pipelines and commands are constructed here.
The triangle retains native G13G state prepared with Mesa's no-op DRM shim.
Preparation does not execute a GPU. This file allocates GEM objects, binds their
GPU virtual addresses, submits through the stable Asahi DRM UAPI, waits on a
DRM sync object, and checks the actual output. No Mesa, EGL, Metal, IOKit, C
helper, capture files, or Python packages are required to run it.

Reference: https://docs.mesa3d.org/drivers/asahi.html
UAPI: https://docs.kernel.org/gpu/driver-uapi.html#asahi-uapi
Embedded Mesa helper shaders: Copyright The Asahi Linux Contributors,
Copyright 2022-2025 Alyssa Rosenzweig. MIT licensed:

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to
do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import argparse
import base64
import ctypes as C
import errno
import hashlib
import json
import math
import mmap
import os
from pathlib import Path
import struct
import sys
import time
import zlib


U16, U32, U64, S64 = C.c_uint16, C.c_uint32, C.c_uint64, C.c_int64
GPU_PAGE = 0x4000
BARRIER_NONE = 0xffff
TRACE = 1


def record(name, *fields):
    return type(name, (C.Structure,), {"_fields_": list(fields)})


# Stable UAPI structures, explicitly sized and naturally aligned to 8 bytes.
Version = record("Version", ("major", C.c_int), ("minor", C.c_int),
                 ("patch", C.c_int), ("name_len", C.c_size_t),
                 ("name", C.c_void_p), ("date_len", C.c_size_t),
                 ("date", C.c_void_p), ("desc_len", C.c_size_t),
                 ("desc", C.c_void_p))
Params = record("Params", ("features", U64), ("gpu_generation", U32),
                ("gpu_variant", U32), ("gpu_revision", U32), ("chip_id", U32),
                ("num_dies", U32), ("num_clusters_total", U32),
                ("num_cores_per_cluster", U32), ("max_frequency_khz", U32),
                ("core_masks", U64 * 64), ("vm_start", U64), ("vm_end", U64),
                ("vm_kernel_min_size", U64), ("max_commands_per_submission", U32),
                ("max_attachments", U32), ("command_timestamp_frequency_hz", U64))
GetParams = record("GetParams", ("param_group", U32), ("pad", U32),
                   ("pointer", U64), ("size", U64))
VMCreate = record("VMCreate", ("kernel_start", U64), ("kernel_end", U64),
                  ("vm_id", U32), ("pad", U32))
VMDestroy = record("VMDestroy", ("vm_id", U32), ("pad", U32))
BindOp = record("BindOp", ("flags", U32), ("handle", U32), ("offset", U64),
                ("range", U64), ("addr", U64))
VMBind = record("VMBind", ("vm_id", U32), ("num_binds", U32),
                ("stride", U32), ("pad", U32), ("userptr", U64))
GEMCreate = record("GEMCreate", ("size", U64), ("flags", U32),
                   ("vm_id", U32), ("handle", U32), ("pad", U32))
MmapOffset = record("MmapOffset", ("handle", U32), ("flags", U32), ("offset", U64))
QueueCreate = record("QueueCreate", ("flags", U32), ("vm_id", U32),
                     ("priority", U32), ("queue_id", U32), ("usc_exec_base", U64))
QueueDestroy = record("QueueDestroy", ("queue_id", U32), ("pad", U32))
Sync = record("Sync", ("sync_type", U32), ("handle", U32), ("timeline_value", U64))
Submit = record("Submit", ("syncs", U64), ("cmdbuf", U64), ("flags", U32),
                ("queue_id", U32), ("in_sync_count", U32), ("out_sync_count", U32),
                ("cmdbuf_size", U32), ("pad", U32))
GEMClose = record("GEMClose", ("handle", U32), ("pad", U32))
SyncCreate = record("SyncCreate", ("handle", U32), ("flags", U32))
SyncDestroy = record("SyncDestroy", ("handle", U32), ("pad", U32))
# The original 32-byte WAIT prefix is accepted by kernels with the later
# deadline_nsec extension as well; its missing deadline field is zeroed.
SyncWait = record("SyncWait", ("handles", U64), ("timeout_nsec", S64),
                  ("count_handles", U32), ("flags", U32),
                  ("first_signaled", U32), ("pad", U32))
Helper = record("Helper", ("binary", U32), ("cfg", U32), ("data", U64))
ZLSBuffer = record("ZLSBuffer", ("base", U64), ("comp_base", U64),
                   ("stride", U32), ("comp_stride", U32))
BgEot = record("BgEot", ("usc", U32), ("rsrc_spec", U32))
Timestamp = record("Timestamp", ("handle", U32), ("offset", U32))
Timestamps = record("Timestamps", ("start", Timestamp), ("end", Timestamp))
Render = record("Render", ("flags", U32), ("isp_zls_pixels", U32),
                ("vdm_ctrl_stream_base", U64), ("vertex_helper", Helper),
                ("fragment_helper", Helper), ("isp_scissor_base", U64),
                ("isp_dbias_base", U64), ("isp_oclqry_base", U64),
                ("depth", ZLSBuffer), ("stencil", ZLSBuffer), ("zls_ctrl", U64),
                ("ppp_multisamplectl", U64), ("sampler_heap", U64), ("ppp_ctrl", U32),
                ("width_px", U16), ("height_px", U16), ("layers", U16),
                ("sampler_count", U16), ("utile_width_px", C.c_uint8),
                ("utile_height_px", C.c_uint8), ("samples", C.c_uint8),
                ("sample_size_B", C.c_uint8), ("isp_merge_upper_x", U32),
                ("isp_merge_upper_y", U32), ("bg", BgEot), ("eot", BgEot),
                ("partial_bg", BgEot), ("partial_eot", BgEot),
                ("isp_bgobjdepth", U32), ("isp_bgobjvals", U32),
                ("ts_vtx", Timestamps), ("ts_frag", Timestamps))


def ioc(direction, number, payload):
    return direction << 30 | C.sizeof(payload) << 16 | ord("d") << 8 | number


IOCTLS = {
    "VERSION": ioc(3, 0x00, Version),
    "GET_PARAMS": ioc(1, 0x40, GetParams),
    "VM_CREATE": ioc(3, 0x42, VMCreate),
    "VM_DESTROY": ioc(1, 0x43, VMDestroy),
    "VM_BIND": ioc(1, 0x44, VMBind),
    "GEM_CREATE": ioc(3, 0x45, GEMCreate),
    "GEM_MMAP_OFFSET": ioc(3, 0x46, MmapOffset),
    "QUEUE_CREATE": ioc(3, 0x48, QueueCreate),
    "QUEUE_DESTROY": ioc(1, 0x49, QueueDestroy),
    "SUBMIT": ioc(1, 0x4a, Submit),
    "GEM_CLOSE": ioc(1, 0x09, GEMClose),
    "SYNCOBJ_CREATE": ioc(3, 0xbf, SyncCreate),
    "SYNCOBJ_DESTROY": ioc(3, 0xc0, SyncDestroy),
    "SYNCOBJ_WAIT": ioc(3, 0xc3, SyncWait),
}


def trace(message, level=1):
    if TRACE >= level:
        print(f"[asahi] {message}", flush=True)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def commands(cmdbuf):
    offset = 0
    while offset < len(cmdbuf):
        require(offset + 8 <= len(cmdbuf), "truncated DRM command header")
        kind, size, vdm, cdm = struct.unpack_from("<4H", cmdbuf, offset)
        offset += 8
        require(size % 8 == 0 and offset + size <= len(cmdbuf),
                "invalid DRM command size")
        yield kind, vdm, cdm, cmdbuf[offset:offset + size]
        offset += size


def load_workload(name):
    if name in ("add", "mul"):
        return build_compute(name)
    fixture = FIXTURES[name]
    raw = zlib.decompress(base64.b85decode(fixture["data"]))
    require(hashlib.sha256(raw).hexdigest() == fixture["sha256"],
            "embedded command data failed its checksum")
    length, = struct.unpack_from("<I", raw)
    meta = json.loads(raw[4:4 + length])
    blob = raw[4 + length:]
    buffers = {}
    for b in meta["buffers"]:
        start, size = b["offset"], b["size"]
        require(start >= 0 and size > 0 and start + size <= len(blob),
                "invalid embedded buffer range")
        require(size % GPU_PAGE == 0, "unaligned embedded buffer size")
        require(b["id"] not in buffers, "duplicate embedded buffer ID")
        buffers[b["id"]] = bytearray(blob[start:start + size])
    cmdbuf = build_render()
    require(cmdbuf == bytes.fromhex(meta["cmdbuf"]),
            "constructed render submission differs from its native reference")
    validate_workload(name, meta, buffers, cmdbuf)
    return meta, buffers, cmdbuf


# G13G scalar shader. r0 is a uint thread index; r1/r2 hold float32 values.
# Uniform registers are 32-bit, so each device pointer consumes two registers.
# u0_u1 = output, u2_u3 = B, u4_u5 = A. The i32 load/store format scales
# the unsigned thread index by four bytes. Loads use separate scoreboard slots.
SHADER_PREFIX = bytes.fromhex(
    "72011004"          # get_sr r0, sr80 (thread_position_in_grid.x)
    "0509080e00c01200"  # device_load 0, i32, x, r1, u4_u5, r0, unsigned
    "0511044e00c01200"  # device_load 1, i32, x, r2, u2_u3, r0, unsigned
    "3800"              # wait 0
    "3801"              # wait 1
)
ARITHMETIC = {
    "add": bytes.fromhex("2a85c2422c00"),  # fadd32 r1, r1.discard, r2.discard
    "mul": bytes.fromhex("1a85c2422c00"),  # fmul32 r1, r1.discard, r2.discard
}
SHADER_SUFFIX = bytes.fromhex(
    "4509000e00c01200"  # device_store 0, i32, x, r1, u0_u1, r0, unsigned
    "8800"              # stop
) + bytes.fromhex("0800") * 8  # trap padding, as emitted by Mesa


def usc_uniform(start_half, count_half, address):
    # USC UNIFORM: tag[7:0], start[15:8], count[25:20], address>>2[63:26].
    require(address % 4 == 0 and 0 <= start_half < 256 and
            0 < count_half <= 64 and address < (1 << 40), "invalid USC uniform")
    return struct.pack("<Q", 0x1d | start_half << 8 |
                       (count_half & 63) << 20 | (address >> 2) << 26)


def build_compute(name):
    usc_base = 0x1100000000
    shader_va, pipeline_va = usc_base + GPU_PAGE, usc_base + 2 * GPU_PAGE
    uniform_va, cdm_va = 0x2000000000, 0x2000004000
    a_va, b_va, out_va = 0x2000008000, 0x200000c000, 0x2000010000

    shader = SHADER_PREFIX + ARITHMETIC[name] + SHADER_SUFFIX
    # USC pointers to code/pipelines are relative to the queue's usc_exec_base.
    shader_offset = shader_va - usc_base
    pipeline_offset = pipeline_va - usc_base
    pipeline = (
        usc_uniform(0, 12, uniform_va)       # 12 half registers = 3 pointers
        + struct.pack("<I", 0x904d)         # SHARED: no local memory, vertex/compute layout
        + struct.pack("<HI", 0x0c0d, shader_offset)  # SHADER: tag 0x0d, unk_2=3
        + struct.pack("<I", 0x018d)         # REGISTERS: one group of 8, no spilling
        + struct.pack("<H", 0x0088)         # NO_PRESHADER
    )
    # CDM LAUNCH word 0: one group of 64 uniform half registers, no textures,
    # samplers or preshader registers; direct mode and launch block type are 0.
    launch = 1 << 1
    cdm = (
        struct.pack("<8I", launch, pipeline_offset, 4, 1, 1, 4, 1, 1)
        + struct.pack("<I", 0x600fffff)     # Mesa's G13G post-dispatch CDM barrier
        + struct.pack("<II", 0x40000000, 0)  # STREAM_TERMINATE, padded to 8 bytes
    )
    # The stable UAPI's stream end excludes the final 8-byte terminator, matching
    # Mesa's native submit. Shader/helper/timestamp fields not used here are 0.
    compute = struct.pack("<IIQQQIIQQQ", 0, 0, cdm_va, cdm_va + len(cdm) - 8,
                          0, 0, 0, 0, 0, 0)
    cmdbuf = struct.pack("<4H", 1, len(compute), 0, 0) + compute
    contents = (
        (1, shader_va, shader, 2),
        (2, pipeline_va, pipeline, 2),
        (3, uniform_va, struct.pack("<3Q", out_va, b_va, a_va), 2),
        (4, cdm_va, cdm, 2),
        (5, a_va, struct.pack("<4f", 1, 2, 3, 4), 2),
        (6, b_va, struct.pack("<4f", 10, 20, 30, 40), 2),
        (7, out_va, bytes([0xa5]) * 16, 6),
    )
    buffers = {buffer_id: bytearray(data.ljust(GPU_PAGE, b"\0"))
               for buffer_id, _, data, _ in contents}
    meta = {
        "usc_base": usc_base,
        "maps": [{"handle": buffer_id, "addr": address, "offset": 0,
                  "range": GPU_PAGE, "flags": flags}
                 for buffer_id, address, _, flags in contents],
        "output_buffer": 7, "input_buffers": [5, 6],
    }
    validate_workload(name, meta, buffers, cmdbuf)
    return meta, buffers, cmdbuf


def build_render():
    # G13G native 8x8 render pass. The embedded BOs contain Mesa's VDM/PPP
    # stream, vertex/fragment programs, and BG/EOT pipelines at these fixed VAs.
    # Register constants below retain their captured values and UAPI names.
    render = Render(
        flags=2,                        # PROCESS_EMPTY_TILES for the clear
        vdm_ctrl_stream_base=0x2ffff00000,
        isp_scissor_base=0x2ffff84d40,
        isp_dbias_base=0x2ffff84d80,
        ppp_multisamplectl=0x88,
        ppp_ctrl=0x202,
        width_px=8, height_px=8, layers=1,
        utile_width_px=32, utile_height_px=32, samples=1, sample_size_B=8,
        isp_merge_upper_x=0x3e5db3d9, isp_merge_upper_y=0x3e5db3d9,
        bg=BgEot(usc=0xfff68104, rsrc_spec=0xffff1012),
        eot=BgEot(usc=0xfff68204, rsrc_spec=0x1012),
        partial_bg=BgEot(usc=0xfff68184, rsrc_spec=0xffff1212),
        partial_eot=BgEot(usc=0xfff68204, rsrc_spec=0x1012),
        isp_bgobjvals=0x300,
    )
    # Optional attachment hint: output GPU VA, allocation size, MBZ pad/flags.
    attachment = struct.pack("<QQII", 0x2ffffc8000, GPU_PAGE, 0, 0)
    return (struct.pack("<4H", 3, len(attachment), BARRIER_NONE, BARRIER_NONE)
            + attachment + struct.pack("<4H", 0, C.sizeof(render), 0, 0) + bytes(render))


def mapped(meta, buffers, address, size):
    for b in meta["maps"]:
        if b["addr"] <= address and address + size <= b["addr"] + b["range"]:
            offset = b["offset"] + address - b["addr"]
            require(offset + size <= len(buffers[b["handle"]]),
                    "GPU access exceeds its backing buffer")
            return bytes(buffers[b["handle"]][offset:offset + size])
    raise RuntimeError(f"unmapped embedded GPU range {address:#x}+{size:#x}")


def validate_workload(name, meta, buffers, cmdbuf):
    require(meta["usc_base"] % (1 << 32) == 0, "USC base must be 4 GiB aligned")
    ranges = []
    for b in meta["maps"]:
        require(b["handle"] in buffers, "GPU binding has no backing buffer")
        require(b["flags"] in (2, 6), "unsupported embedded binding flags")
        require(b["range"] > 0 and all(b[f] % GPU_PAGE == 0
                    for f in ("addr", "offset", "range")), "unaligned GPU binding")
        require(b["offset"] + b["range"] <= len(buffers[b["handle"]]),
                "GPU binding exceeds buffer size")
        start, end = b["addr"], b["addr"] + b["range"]
        require(all(end <= lo or start >= hi for lo, hi in ranges),
                "overlapping embedded GPU bindings")
        ranges.append((start, end))

    hardware_count = 0
    for kind, vdm, cdm, payload in commands(cmdbuf):
        require(kind in (0, 1, 3), "unsupported embedded command type")
        if kind == 3:
            require(vdm == cdm == BARRIER_NONE and len(payload) % 24 == 0,
                    "invalid fragment attachments")
            for off in range(0, len(payload), 24):
                address, size, pad, flags = struct.unpack_from("<QQII", payload, off)
                require(pad == flags == 0, "nonzero attachment flags/padding")
                mapped(meta, buffers, address, size)
            continue
        hardware_count += 1
        require(vdm == cdm == 0, "unexpected hardware command barriers")
        if kind == 1:
            require(name in ("add", "mul") and len(payload) == 64,
                    "invalid compute command")
            start, end = struct.unpack_from("<QQ", payload, 8)
            require(end > start and (end - start) == 36, "invalid compute stream")
            stream = mapped(meta, buffers, start, end - start + 8)
            launch, pipeline, gx, gy, gz, lx, ly, lz, barrier = struct.unpack_from(
                "<9I", stream)
            require((gx, gy, gz, lx, ly, lz) == (4, 1, 1, 4, 1, 1),
                    "compute stream must dispatch exactly four threads")
            require(launch == 2 and barrier == 0x600fffff and
                    stream[36:44] == bytes.fromhex("0000004000000000"),
                    "invalid compute launch/barrier/terminator")
            usc = mapped(meta, buffers, meta["usc_base"] + pipeline, 24)
            uniform, shared, tag, code, registers, preshader = struct.unpack("<QIHIIH", usc)
            require((uniform & 255, uniform >> 8 & 255, uniform >> 20 & 63) ==
                    (0x1d, 0, 12) and (shared, tag, registers, preshader) ==
                    (0x904d, 0x0c0d, 0x018d, 0x0088), "invalid compute USC bindings")
            out_va, b_va, a_va = struct.unpack("<3Q", mapped(meta, buffers, (uniform >> 26) << 2, 24))
            require(mapped(meta, buffers, a_va, 16) == struct.pack("<4f", 1, 2, 3, 4)
                    and mapped(meta, buffers, b_va, 16) == struct.pack("<4f", 10, 20, 30, 40)
                    and any(b["addr"] == out_va and b["handle"] == meta["output_buffer"]
                            for b in meta["maps"]), "incorrect shader pointer bindings")
            expected_shader = SHADER_PREFIX + ARITHMETIC[name] + SHADER_SUFFIX
            require(mapped(meta, buffers, meta["usc_base"] + code, len(expected_shader)) == expected_shader,
                    "USC does not bind the expected scalar shader")
            require(payload[48:] == bytes(16), "unexpected compute timestamps")
        else:
            require(name == "tri" and len(payload) == 240, "invalid render command")
            start, = struct.unpack_from("<Q", payload, 8)
            mapped(meta, buffers, start, 72)
            render = Render.from_buffer_copy(payload)
            require((render.width_px, render.height_px, render.layers) == (8, 8, 1),
                    "render stream must have an 8x8 single-layer framebuffer")
            require(payload[208:] == bytes(32), "unexpected render timestamps")
    require(hardware_count == 1, "expected exactly one hardware command")

    output = buffers[meta["output_buffer"]]
    if name in ("add", "mul"):
        require(bytes(buffers[meta["input_buffers"][0]][:16]) ==
                struct.pack("<4f", 1, 2, 3, 4), "incorrect first input buffer")
        require(bytes(buffers[meta["input_buffers"][1]][:16]) ==
                struct.pack("<4f", 10, 20, 30, 40), "incorrect second input buffer")
        require(output[:16] == bytes([0xa5]) * 16, "missing output sentinel")
    else:
        # The captured EOT PBE is uncompressed RGBA8, one 8x8 Morton tile.
        # Its layout is checked here instead of guessing a CPU row stride.
        pbe = mapped(meta, buffers, meta["pbe_address"], 24)
        word = int.from_bytes(pbe, "little")
        require((word & 15) == 2 and (word >> 4 & 3) == 2 and
                (word >> 6 & 127) == 40 and (word >> 13 & 7) == 0 and
                (word >> 16 & 255) == 0xe4 and
                (word >> 24 & 16383) == 7 and (word >> 38 & 16383) == 7 and
                (word >> 59 & 1) == 0 and (word >> 100 & 15) == 0 and
                (word >> 155 & 15) == (word >> 159 & 15) == 3,
                "unexpected render target format/layout")
        address = (word >> 64 & ((1 << 36) - 1)) << 4
        require(address == meta["output_address"] and
                any(b["addr"] == address and b["handle"] == meta["output_buffer"]
                    for b in meta["maps"]),
                "PBE does not reference the output buffer")
        require(output[:256] == bytes(256), "render output must start cleared")


class Device:
    def __init__(self, path=None):
        require(sys.platform == "linux" and C.sizeof(C.c_void_p) == 8 and
                sys.byteorder == "little", "live execution requires 64-bit little-endian Linux")
        self.libc = C.CDLL(None, use_errno=True)
        self.libc.ioctl.argtypes = (C.c_int, C.c_ulong, C.c_void_p)
        self.libc.ioctl.restype = C.c_int
        self.fd = None
        self.vm = self.queue = self.sync = None
        self.buffers = {}
        self.params = Params()
        candidates = [Path(path)] if path else sorted(Path("/dev/dri").glob("renderD*"))
        if not path:
            candidates += sorted(Path("/dev/dri").glob("card*"))
        examined = []
        for candidate in candidates:
            try:
                fd = os.open(candidate, os.O_RDWR | os.O_CLOEXEC)
            except OSError as exc:
                examined.append(f"{candidate}: {exc.strerror}")
                continue
            self.fd = fd
            try:
                name = C.create_string_buffer(128)
                v = Version(name_len=len(name), name=C.addressof(name))
                self.ioctl("VERSION", v)
                driver = name.raw[:min(v.name_len, len(name))].rstrip(b"\0").decode(
                    "ascii", errors="replace")
                if driver != "asahi":
                    examined.append(f"{candidate}: driver {driver}")
                    continue
                self.ioctl("GET_PARAMS", GetParams(pointer=C.addressof(self.params),
                           size=C.sizeof(self.params)))
                self.path = candidate
                trace(f"device {candidate}, asahi {v.major}.{v.minor}.{v.patch}, "
                      f"G{self.params.gpu_generation}{chr(self.params.gpu_variant)} "
                      f"revision {self.params.gpu_revision:#x}, chip {self.params.chip_id:#x}")
                return
            except OSError as exc:
                examined.append(f"{candidate}: {exc}")
            finally:
                if not hasattr(self, "path"):
                    os.close(fd)
                    self.fd = None
        details = "; ".join(examined) or "no DRM device nodes"
        raise RuntimeError("no usable Asahi GPU device; the stable Asahi DRM UAPI is required. "
                           + details)

    def ioctl(self, name, payload):
        while self.libc.ioctl(self.fd, IOCTLS[name], C.byref(payload)) < 0:
            error = C.get_errno()
            if error == errno.EINTR:
                continue
            raise OSError(error, f"DRM_IOCTL_{name}: {os.strerror(error)}")
        trace(f"{name} OK", 2)
        return payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        errors = []
        for name, payload in (
                ("SYNCOBJ_DESTROY", SyncDestroy(handle=self.sync or 0)),
                ("QUEUE_DESTROY", QueueDestroy(queue_id=self.queue or 0)),
                ("VM_DESTROY", VMDestroy(vm_id=self.vm or 0))):
            if (self.sync if name == "SYNCOBJ_DESTROY" else
                    self.queue if name == "QUEUE_DESTROY" else self.vm) is None:
                continue
            try:
                self.ioctl(name, payload)
            except OSError as error:
                errors.append(str(error))
        for handle, cpu in reversed(list(self.buffers.values())):
            try:
                if cpu is not None:
                    cpu.close()
                self.ioctl("GEM_CLOSE", GEMClose(handle=handle))
            except (OSError, BufferError) as error:
                errors.append(str(error))
        os.close(self.fd)
        self.fd = None
        if errors:
            if exc is None:
                raise RuntimeError("cleanup failed: " + "; ".join(errors))
            print("[asahi] cleanup: " + "; ".join(errors), file=sys.stderr)

    def run(self, name, meta, data, cmdbuf, timeout):
        p = self.params
        # Mesa's live B1 dump uses the same G13G shader and packet encodings
        # as the offline A0 reference. Revision values are BCD (B1 = 0x11).
        require((p.gpu_generation, p.gpu_variant, p.chip_id) ==
                (13, ord("G"), 0x8103) and p.gpu_revision in (0x00, 0x11),
                "embedded shaders/packets target M1 G13G A0/B1 (T8103); "
                "this GPU needs its own native command data")
        require(p.max_commands_per_submission >= 1, "device cannot submit a command")
        if name == "tri":
            require(p.max_attachments >= 1, "device cannot accept a render attachment")
        kernel_size = max(p.vm_kernel_min_size, 32 << 30)
        kernel_start = (p.vm_end - kernel_size) & -GPU_PAGE
        require(p.vm_start < kernel_start < p.vm_end and p.vm_end % GPU_PAGE == 0,
                "insufficient/aligned GPU address space for kernel reservation")
        for b in meta["maps"]:
            require(p.vm_start <= b["addr"] and b["addr"] + b["range"] <= kernel_start,
                    "embedded GPU virtual address conflicts with the device VM window")
        require(p.vm_start <= meta["usc_base"] and
                meta["usc_base"] + (1 << 32) <= kernel_start,
                "device VM window cannot contain the USC heap")
        vm = self.ioctl("VM_CREATE", VMCreate(kernel_start=kernel_start,
                                             kernel_end=p.vm_end))
        self.vm = vm.vm_id
        require(self.vm != 0, "VM_CREATE returned an invalid VM ID")
        trace(f"VM {self.vm}, kernel reservation {kernel_start:#x}..{p.vm_end:#x}")
        for buffer_id, contents in data.items():
            # VM_PRIVATE; default write-combine CPU mapping avoids cached readback.
            gem = self.ioctl("GEM_CREATE", GEMCreate(size=len(contents), flags=2,
                                                    vm_id=self.vm))
            require(gem.handle != 0, "GEM_CREATE returned an invalid handle")
            self.buffers[buffer_id] = (gem.handle, None)
            offset = self.ioctl("GEM_MMAP_OFFSET", MmapOffset(handle=gem.handle)).offset
            cpu = mmap.mmap(self.fd, len(contents), flags=mmap.MAP_SHARED,
                            prot=mmap.PROT_READ | mmap.PROT_WRITE, offset=offset)
            self.buffers[buffer_id] = (gem.handle, cpu)
            cpu[:] = contents
            trace(f"buffer {buffer_id} -> GEM {gem.handle}, {len(contents):#x} bytes", 2)
        binds = (BindOp * len(meta["maps"]))()
        for dest, source in zip(binds, meta["maps"]):
            dest.flags = source["flags"]
            dest.handle = self.buffers[source["handle"]][0]
            dest.offset, dest.range, dest.addr = (source[f] for f in ("offset", "range", "addr"))
            trace(f"bind GEM {dest.handle}: {dest.addr:#x}+{dest.range:#x}, "
                  f"flags {dest.flags:#x}", 2)
        self.ioctl("VM_BIND", VMBind(vm_id=self.vm, num_binds=len(binds),
                   stride=C.sizeof(BindOp), userptr=C.addressof(binds)))
        queue = self.ioctl("QUEUE_CREATE", QueueCreate(vm_id=self.vm, priority=0,
                           usc_exec_base=meta["usc_base"]))
        self.queue = queue.queue_id
        require(self.queue != 0, "QUEUE_CREATE returned an invalid queue ID")
        self.sync = self.ioctl("SYNCOBJ_CREATE", SyncCreate()).handle
        require(self.sync != 0, "SYNCOBJ_CREATE returned an invalid handle")
        syncs = (Sync * 1)(Sync(sync_type=0, handle=self.sync))
        command_data = C.create_string_buffer(cmdbuf)
        start = time.monotonic_ns()
        self.ioctl("SUBMIT", Submit(syncs=C.addressof(syncs), cmdbuf=C.addressof(command_data),
                   queue_id=self.queue, out_sync_count=1, cmdbuf_size=len(cmdbuf)))
        trace(f"submitted {name}, queue {self.queue}, {len(cmdbuf)} command bytes")
        handles = (U32 * 1)(self.sync)
        try:
            self.ioctl("SYNCOBJ_WAIT", SyncWait(handles=C.addressof(handles),
                       timeout_nsec=start + int(timeout * 1e9), count_handles=1, flags=1))
        except OSError as error:
            if error.errno in (errno.ETIME, errno.ETIMEDOUT):
                raise RuntimeError(f"{name}: GPU completion fence timed out after {timeout:g}s") from error
            raise
        elapsed_ms = (time.monotonic_ns() - start) / 1e6
        trace(f"completion fence signaled in {elapsed_ms:.3f} ms (host submit/wait time)")
        output = self.buffers[meta["output_buffer"]][1]
        if name in ("add", "mul"):
            actual = struct.unpack("<4f", output[:16])
            expected = (11.0, 22.0, 33.0, 44.0) if name == "add" else (10.0, 40.0, 90.0, 160.0)
            require(actual == expected, f"{name}: output {actual}, expected {expected}")
            return f"{name}: PASS {list(actual)}"
        pixels = []
        for y in range(8):
            for x in range(8):
                morton = sum(((x >> bit & 1) << (2 * bit)) |
                             ((y >> bit & 1) << (2 * bit + 1)) for bit in range(3))
                pixels.append(bytes(output[4 * morton:4 * morton + 4]))
        bad = [(i % 8, i // 8, p.hex()) for i, p in enumerate(pixels)
               if p != b"\xff\0\0\xff"]
        require(not bad, f"tri: {len(bad)} incorrect pixels, first {bad[:4]}")
        return "tri: PASS 8x8 red triangle, all 64 RGBA8 pixels checked"


def main():
    global TRACE
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("workload", nargs="?", default="all", choices=("add", "mul", "tri", "all"))
    parser.add_argument("--device", help="Asahi DRM device (otherwise discovered by driver name)")
    parser.add_argument("--dry-run", action="store_true", help="check embedded commands without opening a device")
    parser.add_argument("--timeout", type=float, default=10.0, help="GPU fence timeout in seconds (default: 10)")
    parser.add_argument("--trace", type=int, choices=(0, 1, 2), help="trace level; default AGX_TRACE or 1")
    parser.add_argument("-v", action="store_true", help="detailed ioctl/buffer trace")
    args = parser.parse_args()
    require(math.isfinite(args.timeout) and 0 < args.timeout <= 3600,
            "timeout must be finite and between 0 and 3600 seconds")
    TRACE = 2 if args.v else args.trace if args.trace is not None else int(os.environ.get("AGX_TRACE", "1"))
    require(TRACE in (0, 1, 2), "AGX_TRACE must be 0, 1, or 2")
    workloads = ("add", "mul", "tri") if args.workload == "all" else (args.workload,)
    for name in workloads:
        meta, buffers, cmdbuf = load_workload(name)
        if args.dry_run:
            print(f"{name}: PREPARED G13G, {len(buffers)} buffers, "
                  f"{len(meta['maps'])} GPU bindings, {len(cmdbuf)} command bytes; GPU not executed")
            continue
        # A fresh VM per workload lets the fixed GPU VAs retain their meaning
        # without patching packed addresses or depending on another capture.
        with Device(args.device) as dev:
            result = dev.run(name, meta, buffers, cmdbuf, args.timeout)
        print(result)
    return 0


# Native triangle fixture: three vertices (-1,-1), (3,-1), (-1,3), a constant
# red fragment shader, and an 8x8 RGBA8 target. BO snapshots preserve the VDM,
# PPP, BG/EOT and shader state prepared by Mesa 25.3.6 for G13G A0. This
# offline-prepared state passed on M1 G13G B1 on 2026-10-05. ADD/MUL use the
# explicit shader and USC/CDM constructors above and do not load this blob.
FIXTURES = {
    "tri": {
        "sha256": "56d1a5b9b597bff2b79d7c9dc4c0ae2082b86e9deb7725bd3f4239045e737eea",
        "data": (
            "c-rmUUu#?E836ECj@{V#S1YVzr7IX+7So(R($P_FB3NOeZD5y$QG#7tO`+|wI2mIl=A;e73^LMQ^=7b(et~^}u?%`K"
            "_7%q17-N^CFd70YXh)JQ$*z?sn-_=r_Y*qrk<O#%ectoF=UBOjetj~84{A3y-nzWHvawz}-%O*pUW(FWx%S@5)s5Qu"
            "AAV5lyu0#txtA^1uB^Pj_HG#$FV}w5>1?cDubq#UYu8rZf4lc)mge>4+RED6wc7b4%Hl?zwwh(K<=VzOKidhoxjamm"
            "JWj%T(yF(zX41+gr5md+nYO;HUZy;dg#G%;gn2YYx^&w5(zq4X4<uohH{({lnKjdCPGEh?0+UuNo+@Euzl2Gal*?@="
            "W3ya+Wws=bhNo~4uz$vE+7h#@oRuj`Y)+dnO|xj4S<WAsa4_U3>R)e<%-5POUsNvXY??(AN7Iftit?!{jN?a7b3bLX"
            "l_cqCWj}15<7B#}lQ;8xY;iv{<-V6oBdI5OzPrpcFGo8Z`5<CK&iyZ$sGc{P*{-Bn8fW8ook7Titc|JWJa0A{t*I7y"
            "oK2Z9Nt3A-dEA^XVOHMA_O78f%a7i;e)Y!n%d0m!o%L&jC3$sq{c`Vv>l+)R)zaus!*=xUqr>I-)_ZGZp4$0Zltxip"
            "-bOmx%HvVztxhK?_Xg_Gqjbh!B>Np7&-cHnNA<N%KFXKxd41UO{1E}k_8H2zpYhn+ag?vMR@25>y1vtvD?aXIolcy@"
            "{W&UMCp)kEX-3DB{f>`G4`O_^<=S8Y4!-Zav)2DYGPY93mU!<f=mjJb0*04LFDRW5lqStA-wCQu2&%W@MzRys*nM9c"
            "MP-dfn(aho59@DOdUH}#`CTm=)}Bv_%A$IGSbS?zRM}xVtUit=g|*To9+n@+lSWyOTIJu|VO%otY&7F$eK>?T-F@dC"
            "#kJBj&xeDE>w9j-W7Ao0<Z*LUVPnETl1BMwcQjpbHZd+q<I#l0&53botC2)E-@F+B000000000000000004kP_eTH#"
            "0000000000000000N~Kg`w0X9000000000000000004LjoVoIXlK=n!0000000000000000EcR`a(kf&n{z+!Z5OtB"
            "+ta@&w+odp`^8t`*jAX|^Eg=7!s6_;nd<D1EA0^e_H4+XSkD8imEQI@MJU3nA)E+LrdI#}00000000000000000000"
            "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
            "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
            "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
            "0000000000000000000000000000000000000000000000000000000000000001<c5{`_&V<jCkcVn0it6mG;-y<B"
            "D`BP@J}g!%Aru#?;iF=+vb9izkHhU^E6neC000000000000000000002cx)fSUqo6KPi7%VDq`Vz3ub8EdT%j00000"
            "0000000000000000000000000000009Jb;@2$gSl|M91nr~k~ED=&<_YPTPB&-Hfh{bkS|QQtY_{-f=AII1oG-Srz@"
            "asHkLfBoKI9*$~z)O8QpP8~}Z_n(g+JmNmPxX*p0a>Uz1)!we-pxejv>GvnCo8rRO*y=AgdAB=r_~-5PsKBvW+q<8G"
            "`n%zu3t^@_E4{LxT{>Rg&5oBNIkRg&%#O0mmDg9<o;_Rc7x%m4-Of!}UhTxzPr`S57izbAvOg=2>zAQ@?C9QSYbXAG"
            "{9bP%|DnIy7JEyyGCTd}=eM7ue?I{L000000000000000000000000000000000000000000000000000000000000"
            "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
            "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
            "0000000000000000000000000000000000000000000000000000000000000000000000z&F>g!eYDqpnLAc+4dX#"
            "c7AE=)n0pI>C;|&>23(8Pla&5duJw8w*DXehgW+2h4x~<oh^Ra@BdVL>0+;4Y=`2@ZuQb{7ne@Yhwx?hPAyd4_}5H0"
            "m|DvILT}vt{2|=?clS;ugsmrb{{I{n@4Z&`-#ZVl59=tNSRG~m;nHaQzkkx>2LJ#70000000000000000000000000"
            "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
            "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
            "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
            "0000000000000000O08~AHvePXF^zPKj^+3Li_C5^3CFYcWy3(neCW!C(EGM9(2!rD}>j}Hav50<yiTCWt8TgGYJ3y"
            "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
            "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
            "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
            "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
            "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
            "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
            "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
            "0N-TA?*`9yd-py7000000000000000000000000000000000000000000000000000000000000000000000000000"
            "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
            "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
            "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
            "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
            "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
            "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
            "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
            "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
            "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
            "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
            "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
            "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
            "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
            "00000000000000000000006*r<|?0^37;n+57kf<)!AFcOSeu|!b~-MSgck;C@xgPN5y7kYoQ1qhug(gnBVgN00000"
            "00000000000000EMseY=dfu#lQvR~Q=5u#@+vj^*0000000000000000000udcOYu?^j>!{T{%@Qz0x=!|WGdg=1S`"
            "e$N8{000000000000000001~h{{j3nq;v"
        ),
    },
}


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, RuntimeError, ValueError, KeyError, zlib.error) as error:
        print(f"asahi: FAIL: {error}", file=sys.stderr)
        sys.exit(1)
