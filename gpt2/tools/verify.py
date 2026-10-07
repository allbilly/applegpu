#!/usr/bin/env python3
"""Optional GPT-2 verification and warmed benchmark workers."""

import os
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import ROOT, WEIGHT_SHA256, checkpoint, load_state, sha256
from gpt2 import make_backend, provenance
from run_utils import gpu_lock, machine_state, stats
from reference import accuracy


def source_hashes():
    paths = list(ROOT.glob("*.py")) + list((ROOT / "tools").glob("*.py"))
    return {str(p.relative_to(ROOT)): sha256(p) for p in paths}


def execute(backend, case, steps, diagnostics=None):
    environment_start = machine_state()
    before = backend.counters()
    backend.reset()
    begin = time.perf_counter_ns()
    selected = backend.predict(case["prompt_ids"])
    prefill = (time.perf_counter_ns() - begin) / 1e6
    choices, samples, errors = [selected], [], []
    if diagnostics is not None:
        errors.append(accuracy(backend.logits(), diagnostics[0]))
    for index in range(steps):
        begin = time.perf_counter_ns()
        selected = backend.predict([case["next_tokens"][index]])
        samples.append((time.perf_counter_ns() - begin) / 1e6)
        choices.append(selected)
        if diagnostics is not None:
            errors.append(accuracy(backend.logits(), diagnostics[index + 1]))
    after = backend.counters()
    return dict(prompt_tokens=len(case["prompt_ids"]), prefill_ms=prefill,
                prefill_tokens_per_second=1000 * len(case["prompt_ids"]) / prefill,
                decode=stats(samples), predicted_token_ids=choices, diagnostics=errors,
                environment_start=environment_start, environment_end=machine_state(),
                kernel_dispatches=(after["kernels"] - before["kernels"]) if "kernels" in before else None)


def worker(args):
    snapshot = source_hashes()
    trace = json.loads((args.reference / "trace.json").read_text())
    if trace["parameter_dtype"] != args.dtype or trace["checkpoint_sha256"] != WEIGHT_SHA256:
        raise ValueError("benchmark reference does not match this model/precision")
    if hasattr(os, "sched_setaffinity"):
        available = os.sched_getaffinity(0)
        capacities = {cpu: int((Path(f"/sys/devices/system/cpu/cpu{cpu}/cpu_capacity")).read_text()) for cpu in available}
        os.sched_setaffinity(0, {cpu for cpu in available if capacities[cpu] == max(capacities.values())})
    reference = np.load(args.reference / "logits.npz")
    source = checkpoint(args.weights)
    with gpu_lock():
        begin = time.perf_counter()
        state = load_state(source)
        backend = make_backend(args.backend, state, args.dtype, args.beam, args.context)
        del state
        load_seconds = time.perf_counter() - begin
        print(json.dumps(backend.information), flush=True)
        cases = []
        for case in trace["cases"]:
            started = time.perf_counter()
            checked = execute(backend, case, args.steps, reference[case["logits_key"]])
            errors = checked["diagnostics"]
            gate = all(e["top1"] == e["reference_top1"] and e["normalized_rmse"] <= 0.01
                       and e["kl_reference_to_gpu"] <= 0.01 for e in errors)
            if not gate:
                raise RuntimeError("GPU numerical check failed: " + json.dumps(dict(
                    prompt_tokens=len(case["prompt_ids"]), mismatches=[e for e in errors if e["top1"] != e["reference_top1"]],
                    max_normalized_rmse=max(e["normalized_rmse"] for e in errors),
                    max_kl=max(e["kl_reference_to_gpu"] for e in errors))))
            warmups = [execute(backend, case, min(args.steps, 8)) for _ in range(args.warmups)]
            setup_seconds = time.perf_counter() - started
            trials = [execute(backend, case, args.steps) for _ in range(args.trials)]
            # Accuracy checks use full logits outside timers. Measured loops copy only one token.
            if any(t["predicted_token_ids"] != case["next_tokens"][:args.steps + 1] for t in trials):
                raise RuntimeError("warmed generation disagrees with the verified reference")
            cases.append(dict(prompt_tokens=len(case["prompt_ids"]), correctness=checked,
                              warmup_and_tuning_seconds=setup_seconds, trials=trials,
                              counters=backend.counters()))
            print(f"{backend.name} BEAM={args.beam}: prompt={len(case['prompt_ids'])}, "
                  f"decode={np.mean([t['decode']['steps_per_second'] for t in trials]):.2f} steps/s, checks PASS", flush=True)
        if source_hashes() != snapshot:
            raise RuntimeError("worker sources changed during execution")
        proof = provenance(backend, source, sys.argv)
        proof["runner_sources"] = snapshot
        report = dict(status="PASS", backend=args.backend, beam=args.beam, dtype=args.dtype,
                      model_load_seconds=load_seconds, cases=cases,
                      provenance=proof,
                      cpu_affinity=sorted(os.sched_getaffinity(0)),
                      reference_sha256={n: sha256(args.reference / n) for n in ("trace.json", "logits.npz")},
                      timing_scope="Wall time for input/graph construction, KV update, GPU execution, synchronization and GPU argmax/token read; excludes printing and full-logit diagnostics")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")
        print("Saved", args.output, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", choices=("verify", "worker"), default="verify")
    parser.add_argument("--backend", choices=("tinygrad", "mlx"), default="tinygrad")
    parser.add_argument("--beam", type=int, default=int(os.environ.get("BEAM", "0")))
    parser.add_argument("--dtype", choices=("float32", "float16"), default="float32")
    parser.add_argument("--weights", type=Path)
    parser.add_argument("--context", type=int, default=1024)
    parser.add_argument("--steps", type=int, default=64)
    parser.add_argument("--lengths", type=int, nargs="+", default=[2, 32, 64])
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--warmups", type=int, default=2)
    parser.add_argument("--reference", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if (not 2 <= args.context <= 1024 or args.beam < 0 or args.steps < 1 or args.trials < 1 or
            args.warmups < 0 or (args.command == "verify" and
                                any(n < 1 or n + args.steps > args.context for n in args.lengths))):
        parser.error("invalid context, BEAM width or measurement counts")
    try:
        if args.command == "worker":
            if args.reference is None or args.output is None:
                parser.error("worker requires --reference and --output")
            worker(args)
        else:
            with tempfile.TemporaryDirectory(prefix="applegpu-gpt2-verify-") as temporary:
                args.reference = Path(temporary)
                command = [sys.executable, str(ROOT / "tools/reference.py"), "--output", temporary,
                           "--dtype", args.dtype, "--steps", str(args.steps), "--lengths", *map(str, args.lengths)]
                if args.weights:
                    command += ["--weights", str(args.weights)]
                subprocess.run(command, check=True, timeout=600)
                args.output = args.output or ROOT / "results" / f"verify-{args.backend}-beam{args.beam}-{args.dtype}.json"
                worker(args)
        return 0
    except (ImportError, OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"GPT-2 verification: FAIL: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
