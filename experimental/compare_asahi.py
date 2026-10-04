#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare Mesa's live shader/packet dump with our standalone DRM construction.

    python3 experimental/compare_asahi.py experimental/dumps/asahi_add

These are decoded GPU command fields and shader registers, not MMIO reads.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct

import asahi


def compare(directory):
    result = json.loads((directory / "result.json").read_text())
    if not result["passed"] or "Apple M1 (G13G B1)" != result["renderer"]:
        raise RuntimeError("expected a passing hardware reference on M1 B1")
    operation = result["operation"]
    trace = (directory / "commands.0000").read_text()
    instructions = re.findall(r"^\s*([0-9a-f]+): ([0-9a-f]+)\s+(.+)$", trace, re.M)
    shader = bytearray()
    for offset, encoded, _ in instructions:
        if int(offset, 16) != len(shader):
            raise RuntimeError("shader dump has discontinuous instruction offsets")
        shader.extend(bytes.fromhex(encoded))
    reference = asahi.SHADER_PREFIX + asahi.ARITHMETIC[operation] + asahi.SHADER_SUFFIX
    if not shader or bytes(shader) != reference[:len(shader)]:
        raise RuntimeError("Mesa's hardware shader differs from our shader")
    if not instructions[-1][2].strip().startswith("stop"):
        raise RuntimeError("shader dump does not end at STOP")

    def field(section, key):
        match = re.search(r"^" + re.escape(section) + r"\n((?:  .*\n)+)", trace, re.M)
        if not match:
            raise RuntimeError("missing decoded section " + section)
        value = re.search(r"^  " + re.escape(key) + r": (.+)$", match[1], re.M)
        if not value:
            raise RuntimeError(f"missing decoded field {section}.{key}")
        return value[1]

    _, buffers, _ = asahi.build_compute(operation)
    cdm = buffers[4]
    words = struct.unpack_from("<9I", cdm)
    native_grid = tuple(int(field("Global size", axis)) for axis in "XYZ")
    native_local = tuple(int(field("Local size", axis)) for axis in "XYZ")
    registers = int(field("Registers", "Register count"))
    uniform_halfs = int(field("Uniform", "Size (halfs)"))
    if native_grid != words[2:5] or native_local != words[5:8]:
        raise RuntimeError("native grid/local size differs")
    if registers != 8 or uniform_halfs != 12 or "No preshader" not in trace:
        raise RuntimeError("native register/uniform/preshader state differs")
    if field("Shared", "Uses shared memory") != "false":
        raise RuntimeError("unexpected native shared memory")
    expected = (11.0, 22.0, 33.0, 44.0) if operation == "add" else (10.0, 40.0, 90.0, 160.0)
    if tuple(result["output"]) != expected:
        raise RuntimeError("Mesa reference output differs")

    comparison = {
        "operation": operation,
        "shader_bytes_through_stop": len(shader),
        "shader_sha256": hashlib.sha256(shader).hexdigest(),
        "shader_matches": True, "standalone_trap_padding_bytes": len(reference)-len(shader),
        "shader_registers": registers, "uniform_halfs": uniform_halfs,
        "global_size": native_grid, "local_size": native_local,
        "native_launch": {key: field("Compute", key) for key in
                          ("Uniform register count", "Texture state register count",
                           "Sampler state register count", "Preshader register count", "Mode")},
        "standalone_launch": {"uniform_register_count": ((words[0] >> 1) & 7) * 64,
                              "texture_state_register_count": ((words[0] >> 4) & 31) * 8,
                              "sampler_state_register_count": 0,
                              "preshader_register_count": ((words[0] >> 12) & 15) * 16,
                              "mode": "Direct"},
        "output": result["output"],
    }
    (directory / "comparison.json").write_text(json.dumps(comparison, indent=2) + "\n")
    print(f"{operation}: MATCH {len(shader)} shader bytes through STOP; {registers} registers; "
          f"grid={native_grid}, local={native_local}")
    return comparison


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    compare(parser.parse_args().directory)
