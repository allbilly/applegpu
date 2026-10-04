#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run ADD/MUL through Mesa GLES, optionally decode its native AGX submission.

    python3 mesa_compute.py add
    mkdir -p asahi_add
    python3 mesa_compute.py add --dump-dir asahi_add >asahi_add/mesa.log 2>&1

Uses ctypes and installed EGL/GLES libraries. This is a reference workload;
the standalone DRM examples do not import it or call Mesa.
"""

import argparse
import ctypes as C
import json
import os
from pathlib import Path
import struct
import sys


def bind(lib, name, result, *arguments):
    function = getattr(lib, name)
    function.restype, function.argtypes = result, arguments
    return function


def run(operation, dump_dir=None):
    source = """#version 310 es
layout(local_size_x=4) in;
layout(std430, binding=0) readonly buffer InputA { float a[]; };
layout(std430, binding=1) readonly buffer InputB { float b[]; };
layout(std430, binding=2) writeonly buffer Output { float c[]; };
void main() {
    uint i = gl_GlobalInvocationID.x;
    c[i] = a[i] OP b[i];
}
""".replace("OP", "+" if operation == "add" else "*")
    if dump_dir:
        dump_dir.mkdir(parents=True, exist_ok=True)
        (dump_dir / "shader.glsl").write_text(source)
        os.environ["ASAHI_MESA_DEBUG"] = "trace,sync"
        os.environ["AGX_MESA_DEBUG"] = "shaders,verbose"
        os.environ["AGXDECODE_DUMP_FILE"] = str((dump_dir / "commands").resolve())
        os.environ["MESA_SHADER_CACHE_DISABLE"] = "true"

    egl = C.CDLL("libEGL.so.1")
    gl = C.CDLL("libGLESv2.so.2")
    ptr, integer, uint = C.c_void_p, C.c_int, C.c_uint
    intptr = C.c_ssize_t
    get_display = bind(egl, "eglGetPlatformDisplay", ptr, uint, ptr, ptr)
    initialize = bind(egl, "eglInitialize", uint, ptr, ptr, ptr)
    choose = bind(egl, "eglChooseConfig", uint, ptr, ptr, ptr, integer, ptr)
    bind_api = bind(egl, "eglBindAPI", uint, uint)
    create = bind(egl, "eglCreateContext", ptr, ptr, ptr, ptr, ptr)
    current = bind(egl, "eglMakeCurrent", uint, ptr, ptr, ptr, ptr)
    destroy = bind(egl, "eglDestroyContext", uint, ptr, ptr)
    terminate = bind(egl, "eglTerminate", uint, ptr)
    egl_error = bind(egl, "eglGetError", uint)

    def checked(result, name):
        if not result:
            raise RuntimeError(f"{name}: EGL error {egl_error():#x}")
        return result

    display = checked(get_display(0x31DD, None, None), "surfaceless display")
    context, program, shader = None, 0, 0
    buffers = (uint * 3)()
    checked(initialize(display, None, None), "eglInitialize")
    try:
        checked(bind_api(0x30A0), "eglBindAPI(GLES)")
        attributes = (integer * 5)(0x3040, 0x40, 0x3033, 1, 0x3038)
        config, count = ptr(), integer()
        checked(choose(display, attributes, C.byref(config), 1, C.byref(count)),
                "eglChooseConfig")
        if count.value != 1:
            raise RuntimeError("no GLES3 EGL configuration")
        attributes = (integer * 5)(0x3098, 3, 0x30FB, 1, 0x3038)
        context = checked(create(display, config, None, attributes), "eglCreateContext")
        checked(current(display, None, None, context), "eglMakeCurrent")

        get_string = bind(gl, "glGetString", C.c_char_p, uint)
        information = {name: get_string(token).decode() for name, token in
                       (("vendor", 0x1F00), ("renderer", 0x1F01), ("version", 0x1F02))}
        print(json.dumps(information, indent=2), flush=True)
        if "Apple M1" not in information["renderer"]:
            raise RuntimeError("reference must execute on the M1 GPU")

        create_shader = bind(gl, "glCreateShader", uint, uint)
        shader_source = bind(gl, "glShaderSource", None, uint, integer, ptr, ptr)
        compile_shader = bind(gl, "glCompileShader", None, uint)
        get_shader = bind(gl, "glGetShaderiv", None, uint, uint, ptr)
        shader_log = bind(gl, "glGetShaderInfoLog", None, uint, integer, ptr, ptr)
        create_program = bind(gl, "glCreateProgram", uint)
        attach = bind(gl, "glAttachShader", None, uint, uint)
        link = bind(gl, "glLinkProgram", None, uint)
        get_program = bind(gl, "glGetProgramiv", None, uint, uint, ptr)
        program_log = bind(gl, "glGetProgramInfoLog", None, uint, integer, ptr, ptr)
        use = bind(gl, "glUseProgram", None, uint)
        shader = create_shader(0x91B9)
        text = (C.c_char_p * 1)(source.encode())
        shader_source(shader, 1, text, None)
        compile_shader(shader)
        status, log = integer(), C.create_string_buffer(16384)
        get_shader(shader, 0x8B81, C.byref(status))
        if not status.value:
            shader_log(shader, len(log), None, log)
            raise RuntimeError("shader compilation: " + log.value.decode())
        program = create_program()
        attach(program, shader)
        link(program)
        get_program(program, 0x8B82, C.byref(status))
        if not status.value:
            program_log(program, len(log), None, log)
            raise RuntimeError("program linking: " + log.value.decode())
        use(program)

        gen_buffers = bind(gl, "glGenBuffers", None, integer, ptr)
        bind_buffer = bind(gl, "glBindBuffer", None, uint, uint)
        buffer_data = bind(gl, "glBufferData", None, uint, intptr, ptr, uint)
        bind_base = bind(gl, "glBindBufferBase", None, uint, uint, uint)
        dispatch = bind(gl, "glDispatchCompute", None, uint, uint, uint)
        barrier = bind(gl, "glMemoryBarrier", None, uint)
        finish = bind(gl, "glFinish", None)
        map_buffer = bind(gl, "glMapBufferRange", ptr, uint, intptr, intptr, uint)
        unmap = bind(gl, "glUnmapBuffer", C.c_ubyte, uint)
        get_error = bind(gl, "glGetError", uint)
        target = 0x90D2  # GL_SHADER_STORAGE_BUFFER
        gen_buffers(3, buffers)
        inputs = (struct.pack("<4f", 1, 2, 3, 4), struct.pack("<4f", 10, 20, 30, 40),
                  bytes([0xA5]) * 16)
        for index, contents in enumerate(inputs):
            data = C.create_string_buffer(contents)
            bind_buffer(target, buffers[index])
            buffer_data(target, len(contents), data, 0x88E4)
            bind_base(target, index, buffers[index])
        dispatch(1, 1, 1)
        barrier(0x2200)  # SHADER_STORAGE_BARRIER_BIT | BUFFER_UPDATE_BARRIER_BIT
        finish()
        error = get_error()
        if error:
            raise RuntimeError(f"compute dispatch: GL error {error:#x}")
        bind_buffer(target, buffers[2])
        address = map_buffer(target, 0, 16, 1)  # GL_MAP_READ_BIT
        if not address:
            raise RuntimeError(f"output mapping: GL error {get_error():#x}")
        actual = struct.unpack("<4f", C.string_at(address, 16))
        if not unmap(target):
            raise RuntimeError("output mapping became invalid")
        expected = (11.0, 22.0, 33.0, 44.0) if operation == "add" else (10.0, 40.0, 90.0, 160.0)
        if actual != expected:
            raise RuntimeError(f"output {actual}, expected {expected}")
        result = {**information, "operation": operation, "output": actual, "expected": expected,
                  "kernel": os.uname().release, "passed": True}
        if dump_dir:
            (dump_dir / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        print(f"Mesa {operation}: PASS {list(actual)}", flush=True)
        return result
    finally:
        if context:
            if buffers[0]:
                bind(gl, "glDeleteBuffers", None, integer, ptr)(3, buffers)
            if program:
                bind(gl, "glDeleteProgram", None, uint)(program)
            if shader:
                bind(gl, "glDeleteShader", None, uint)(shader)
            current(display, None, None, None)
            destroy(display, context)
        terminate(display)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", nargs="?", default="add", choices=("add", "mul"))
    parser.add_argument("--dump-dir", type=Path, help="enable Mesa's shader and native packet dumps")
    args = parser.parse_args()
    try:
        run(args.operation, args.dump_dir)
    except (OSError, RuntimeError) as error:
        print(f"Mesa: FAIL: {error}", file=sys.stderr)
        sys.exit(1)
