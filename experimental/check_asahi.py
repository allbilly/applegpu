#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Probe the Asahi native-example target, optionally verify it on the GPU.

The default only queries DRM VERSION/GET_PARAMS; it submits no GPU commands.
--run checks the existing standalone examples in separate child processes,
requires three agreeing results per example, and stops at the first failure.
Inspired by AGXForge's platform records and execution-validation methodology;
this implementation uses this repository's G13G Asahi bindings and fixtures.
"""

import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys

import asahi


ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "add": "add: PASS [11.0, 22.0, 33.0, 44.0]",
    "mul": "mul: PASS [10.0, 40.0, 90.0, 160.0]",
    "tri": "tri: PASS 8x8 red triangle, all 64 RGBA8 pixels checked",
}


def source_hashes():
    paths = [Path(__file__).resolve(), ROOT / "experimental/asahi.py"]
    paths += [ROOT / "examples" / f"{name}_asahi.py" for name in EXPECTED]
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in paths}


def machine():
    model = Path("/proc/device-tree/model")
    return dict(system=platform.system(), kernel=platform.release(),
                architecture=platform.machine(), python=platform.python_version(),
                cpu_page_bytes=os.sysconf("SC_PAGE_SIZE"),
                model=model.read_bytes().rstrip(b"\0").decode() if model.exists() else None)


def probe(device):
    asahi.TRACE = 0
    with asahi.Device(device) as dev:
        p = dev.params
        gpu = dict(generation=p.gpu_generation, variant=p.gpu_variant,
                   revision=p.gpu_revision, chip_id=p.chip_id,
                   clusters=p.num_clusters_total,
                   cores_per_cluster=p.num_cores_per_cluster)
        supported = ((p.gpu_generation, p.gpu_variant, p.chip_id) ==
                     (13, ord("G"), 0x8103) and p.gpu_revision in (0, 0x11))
        return str(dev.path), gpu, supported


def run_checks(device, runs, timeout, results):
    for name, expected in EXPECTED.items():
        for repetition in range(1, runs + 1):
            command = [sys.executable, str(ROOT / "examples" / f"{name}_asahi.py"),
                       "--device", device, "--trace", "0", "--timeout", str(timeout)]
            row = dict(workload=name, repetition=repetition, command=command)
            results.append(row)
            try:
                child = subprocess.run(command, capture_output=True, text=True,
                                       timeout=timeout + 5)
                row.update(returncode=child.returncode, stdout=child.stdout.strip(),
                           stderr=child.stderr.strip())
                row["passed"] = child.returncode == 0 and row["stdout"] == expected
            except subprocess.TimeoutExpired:
                row.update(passed=False, error="child exceeded its fence timeout plus 5s")
            if not row["passed"]:
                raise RuntimeError(f"{name} repetition {repetition} failed; batch stopped")


def locked_checks(device, runs, timeout, results):
    # Share the inference runners' advisory locks; avoid overlapping experiments.
    with ExitStack() as stack:
        for path in (Path.home() / "gpu.lock", Path("/tmp/m1-gpu.lock")):
            stream = stack.enter_context(path.open("a"))
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise RuntimeError(f"GPU lock is busy: {path}; retry after the other runner exits") from error
        run_checks(device, runs, timeout, results)


def drift(previous, report):
    changes = []
    for group in ("platform", "source_sha256"):
        before, now = previous[group], report[group]
        if not isinstance(before, dict):
            raise ValueError(f"comparison receipt has invalid {group}")
        for field in sorted(before.keys() | now.keys()):
            if before.get(field) != now.get(field):
                changes.append(dict(field=f"{group}.{field}",
                                    recorded=before.get(field), running=now.get(field)))
    return changes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", help="DRM node; default: discover the Asahi driver")
    parser.add_argument("--run", action="store_true", help="execute ADD, MUL and TRI on the GPU")
    parser.add_argument("--runs", type=int, default=3, help="agreeing runs per example (default: 3)")
    parser.add_argument("--timeout", type=float, default=5, help="fence timeout per run in seconds")
    parser.add_argument("--output", type=Path, help="save this JSON receipt")
    parser.add_argument("--compare", type=Path, help="report platform/source drift from a prior receipt")
    args = parser.parse_args()
    if not 1 <= args.runs <= 100 or not math.isfinite(args.timeout) or not 0 < args.timeout <= 60:
        parser.error("runs must be 1..100 and timeout must be finite and in (0, 60]")

    report = dict(schema_version=1, timestamp_utc=datetime.now(timezone.utc).isoformat(),
                  status="FAIL", gpu_tests_requested=args.run, checks=[])
    try:
        report["platform"] = machine()
        report["source_sha256"] = source_hashes()
        previous = None
        if args.compare:
            previous = json.loads(args.compare.read_text())
            if not isinstance(previous, dict) or previous.get("schema_version") != 1:
                raise ValueError("comparison requires a check_asahi.py schema_version 1 receipt")
            # Validate before any GPU dispatch.
            drift(previous, report)
        device, gpu, supported = probe(args.device)
        report["device"] = device
        report["platform"]["gpu"] = gpu
        report["native_target_supported"] = supported
        if not supported:
            raise RuntimeError("embedded commands require M1 G13G A0/B1 (T8103); "
                               "this GPU needs its own native command data")
        report["status"] = "READY"
        report["scope"] = "DRM query and target match only; GPU execution not tested"
        if args.run:
            report["scope"] = "Native GPU verification requested; inspect checks for completed results"
            locked_checks(device, args.runs, args.timeout, report["checks"])
            report["status"] = "PASS"
            report["scope"] = ("Completed DRM fences and exact outputs for ADD, MUL and TRI; "
                               "does not validate inference or measure GPU performance")
        if source_hashes() != report["source_sha256"]:
            raise RuntimeError("sources changed during the check; rerun with stable sources")
        if previous is not None:
            report["drift"] = drift(previous, report)
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        report["status"] = "FAIL"
        report["error"] = str(error)

    encoded = json.dumps(report, indent=2) + "\n"
    if args.output:
        try:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(encoded)
        except OSError as error:
            print(f"cannot write receipt: {error}", file=sys.stderr)
            return 1
    print(encoded, end="")
    return int(report["status"] == "FAIL")


if __name__ == "__main__":
    raise SystemExit(main())
