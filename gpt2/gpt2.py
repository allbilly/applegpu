#!/usr/bin/env python3
"""GPT-2 124M generation and validation on the Asahi M1 GPU."""

import os
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import argparse
import codecs
from contextlib import contextmanager, ExitStack
import fcntl
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time

import numpy as np

from common import ROOT, WEIGHT_SHA256, accuracy, checkpoint, load_state, sha256, tokenizer

SOURCE_HASHES = {p.name: sha256(p) for p in ROOT.glob("*.py")}


def machine_state():
    temperatures = {}
    for directory in Path("/sys/class/hwmon").glob("hwmon*"):
        try:
            if (directory / "name").read_text().strip() != "macsmc_hwmon":
                continue
        except OSError:
            continue
        for path in directory.glob("temp*_input"):
            try:
                label = path.with_name(path.name.replace("_input", "_label"))
                name = label.read_text().strip() if label.is_file() else path.stem
                temperatures[name] = int(path.read_text()) / 1000
            except (OSError, ValueError):
                pass
    memory = {line.split(":")[0]: int(line.split()[1]) * 1024
              for line in Path("/proc/meminfo").read_text().splitlines()
              if line.startswith(("MemAvailable:", "SwapFree:"))}
    return dict(temperatures_c=temperatures, memory=memory)


@contextmanager
def gpu_lock():
    with ExitStack() as stack:
        for path in (Path.home() / "gpu.lock", Path("/tmp/m1-gpu.lock")):
            stream = stack.enter_context(path.open("a"))
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise RuntimeError(f"GPU is reserved by another job: {path}") from None
        yield


def make_backend(name, state, dtype, beam, context):
    if name == "tinygrad":
        from tinygrad_backend import Backend
    else:
        from mlx_backend import Backend
    return Backend(state, dtype=dtype, beam=beam, capacity=context)


def provenance(backend, source, command):
    if SOURCE_HASHES != {p.name: sha256(p) for p in ROOT.glob("*.py")}:
        raise RuntimeError("runner source changed during execution; rerun with a stable checkout")
    driver_libraries = {Path(line.split()[-1]) for line in Path("/proc/self/maps").read_text().splitlines()
                        if any(name in line for name in ("libRusticlOpenCL", "libvulkan_asahi"))}
    return dict(kernel=platform.release(), machine=platform.machine(),
                driver_library_sha256={p.name: sha256(p) for p in driver_libraries},
                checkpoint_sha256=WEIGHT_SHA256, checkpoint_revision="607a30d783dfa663caf39e06633721c8d4cfcd7e",
                runtime=backend.information, command=command,
                runner_sources=SOURCE_HASHES,
                packages={n: importlib.metadata.version(n) for n in ("numpy", "safetensors", "regex")},
                tokenizer_sha256={p.name: sha256(p) for p in (ROOT / "tokenizer").iterdir()})


def stats(samples):
    return dict(samples=len(samples), raw_ms=samples, mean_ms=float(np.mean(samples)),
                median_ms=float(np.median(samples)), min_ms=min(samples), max_ms=max(samples),
                steps_per_second=1000 * len(samples) / sum(samples))


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
        report = dict(status="PASS", backend=args.backend, beam=args.beam, dtype=args.dtype,
                      model_load_seconds=load_seconds, cases=cases,
                      provenance=provenance(backend, source, sys.argv),
                      cpu_affinity=sorted(os.sched_getaffinity(0)),
                      reference_sha256={n: sha256(args.reference / n) for n in ("trace.json", "logits.npz")},
                      timing_scope="Wall time for input/graph construction, KV update, GPU execution, synchronization and GPU argmax/token read; excludes printing and full-logit diagnostics")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")
        print("Saved", args.output, flush=True)


def generate(args):
    source = checkpoint(args.weights, download=True)
    codec = tokenizer()
    prompt = codec.encode(args.prompt)
    if not prompt or args.max_tokens < 0 or len(prompt) + max(0, args.max_tokens - 1) > args.context:
        raise ValueError("nonempty prompt plus generation must fit the requested context")
    with gpu_lock():
        state = load_state(source)
        backend = make_backend(args.backend, state, args.dtype, args.beam, args.context)
        del state
        print(json.dumps(backend.information), file=sys.stderr, flush=True)
        print(args.prompt, end="", flush=True)
        decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        generated, samples, prefill = [], [], None
        if args.max_tokens:
            begin = time.perf_counter_ns()
            selected = backend.predict(prompt)
            prefill = (time.perf_counter_ns() - begin) / 1e6
            for index in range(args.max_tokens):
                generated.append(selected)
                if selected == codec.eos:
                    break
                print(decoder.decode(codec.decode_bytes([selected])), end="", flush=True)
                if index + 1 < args.max_tokens:
                    begin = time.perf_counter_ns()
                    selected = backend.predict([selected])
                    samples.append((time.perf_counter_ns() - begin) / 1e6)
        print(decoder.decode(b"", final=True), flush=True)
        report = dict(status="PASS", prompt_token_ids=prompt, generated_token_ids=generated,
                      text=codec.decode(prompt + generated), prefill_ms=prefill,
                      decode=stats(samples) if samples else None,
                      provenance=provenance(backend, source, sys.argv))
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, indent=2) + "\n")
        print(f"GPU generation: prompt={len(prompt)}; generated={len(generated)}; "
              f"prefill={prefill if prefill is not None else 0:.1f} ms", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", choices=("generate", "verify", "worker", "setup"), default="generate")
    parser.add_argument("--backend", choices=("tinygrad", "mlx"), default="tinygrad")
    parser.add_argument("--beam", type=int, default=int(os.environ.get("BEAM", "0")))
    parser.add_argument("--dtype", choices=("float32", "float16"), default="float32")
    parser.add_argument("--weights", type=Path)
    parser.add_argument("--context", type=int, default=1024)
    parser.add_argument("--prompt", default="Hello world")
    parser.add_argument("--max-tokens", type=int, default=32)
    parser.add_argument("--steps", type=int, default=64)
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--warmups", type=int, default=2)
    parser.add_argument("--reference", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not 2 <= args.context <= 1024 or args.beam < 0 or args.steps < 1 or args.trials < 1 or args.warmups < 0:
        parser.error("invalid context, BEAM width or measurement counts")
    try:
        if args.command == "setup":
            print("Verified weights:", checkpoint(args.weights, download=True))
        elif args.command == "generate":
            generate(args)
        elif args.command == "worker":
            if args.reference is None or args.output is None:
                parser.error("worker requires --reference and --output")
            worker(args)
        else:
            with tempfile.TemporaryDirectory(prefix="applegpu-gpt2-verify-") as temporary:
                args.reference = Path(temporary)
                command = [sys.executable, str(ROOT / "reference.py"), "--output", temporary,
                           "--dtype", args.dtype, "--steps", str(args.steps)]
                if args.weights:
                    command += ["--weights", str(args.weights)]
                subprocess.run(command, check=True, timeout=600)
                args.output = args.output or ROOT / "results" / f"verify-{args.backend}-beam{args.beam}-{args.dtype}.json"
                worker(args)
        return 0
    except (ImportError, OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"GPT-2: FAIL: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
