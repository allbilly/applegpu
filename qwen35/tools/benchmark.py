#!/usr/bin/env python3
"""Compare warmed Qwen inference on the same independently verified history."""

import os
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import argparse
from contextlib import ExitStack, contextmanager
from datetime import datetime, timezone
import fcntl
import json
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import tempfile
import time

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from checkpoint import FILES, MODEL_ID, REVISION, ROOT, checkpoint, sha256, tokenizer
from qwen35 import base_commit, make_backend
sys.path.insert(0, str(ROOT.parent / "gpt2"))
from run_utils import machine_state, stats
sys.path.pop(0)
from reference import Reference
from verify import ATOL, RTOL, compare, source_hashes as sources


@contextmanager
def reserved_gpu(timeout):
    """Use the existing lock order, with a bounded wait for other experiments."""
    deadline = time.monotonic() + timeout
    with ExitStack() as stack:
        for path in (Path.home() / "gpu.lock", Path("/tmp/m1-gpu.lock")):
            stream = stack.enter_context(path.open("a"))
            while True:
                try:
                    fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise RuntimeError(f"GPU lock wait timed out: {path}") from None
                    time.sleep(0.25)
        yield


def execute(backend, prompt, history, synchronize, diagnostics=None):
    backend.reset()
    # tinygrad queues its reset fills asynchronously. Finish those before the
    # prefill timer, so this phase measures prediction rather than old work.
    synchronize()
    before = backend.counters()
    begin = time.perf_counter_ns()
    selected = backend.predict(prompt)
    prefill_ms = (time.perf_counter_ns() - begin) / 1e6
    choices, samples, errors = [selected], [], []
    if diagnostics is not None:
        errors.append(compare(backend.logits(), diagnostics[0], selected))
    for step, token in enumerate(history[:-1], start=1):
        begin = time.perf_counter_ns()
        selected = backend.predict([token])
        samples.append((time.perf_counter_ns() - begin) / 1e6)
        choices.append(selected)
        if diagnostics is not None:
            errors.append(compare(backend.logits(), diagnostics[step], selected))
    after = backend.counters()
    return dict(prefill_ms=prefill_ms, prefill_tokens_per_second=1000 * len(prompt) / prefill_ms,
                decode=stats(samples), predicted_token_ids=choices, diagnostics=errors,
                kernel_dispatches=after["kernels"] - before["kernels"] if "kernels" in before else None)


def prepare_reference(args, directory, destination):
    codec = tokenizer(directory)
    messages = ([dict(role="system", content=args.system)] if args.system else []) + [dict(role="user", content=args.prompt)]
    prompt = codec.encode(args.prompt, add_special_tokens=False) if args.raw else codec.apply_chat_template(
        messages, tokenize=True, add_generation_prompt=True, enable_thinking=args.thinking)
    if hasattr(prompt, "keys"):
        prompt = prompt["input_ids"]
    if not prompt or len(prompt) + args.steps > args.context:
        raise ValueError("prompt plus cached decode steps must fit the context")
    reference = Reference(directory, capacity=args.context)
    logits, history = [], []
    for step in range(args.steps + 1):
        vector = reference.predict(prompt if step == 0 else [history[-1]])
        logits.append(vector)
        history.append(int(vector.argmax()))
    np.savez(destination / "logits.npz", logits=np.stack(logits))
    trace = dict(model=MODEL_ID, revision=REVISION, checkpoint_sha256=FILES,
                 prompt=args.prompt, messages=None if args.raw else messages, thinking=args.thinking,
                 prompt_token_ids=prompt, next_token_ids=history,
                 reference="Independent NumPy FP64 decoder, original checkpoint",
                 logits_sha256=sha256(destination / "logits.npz"), runner_sources=sources())
    (destination / "trace.json").write_text(json.dumps(trace, indent=2) + "\n")
    return trace


def worker(args):
    if args.backend == "all" or args.reference is None or args.output is None:
        raise ValueError("worker requires one backend, reference and output")
    trace_path, logits_path = args.reference / "trace.json", args.reference / "logits.npz"
    trace = json.loads(trace_path.read_text())
    snapshot = sources()
    if trace["checkpoint_sha256"] != FILES or trace["runner_sources"] != snapshot or trace["logits_sha256"] != sha256(logits_path):
        raise ValueError("reference inputs or sources changed")
    prompt, history = trace["prompt_token_ids"], trace["next_token_ids"]
    with np.load(logits_path) as archive:
        expected = archive["logits"]
    if (len(history) != args.steps + 1 or len(prompt) + args.steps > args.context or
            expected.shape != (len(history), 248320) or not np.isfinite(expected).all() or
            list(map(int, expected.argmax(axis=1))) != history):
        raise ValueError("invalid complete CPU reference history")
    if hasattr(os, "sched_setaffinity"):
        available = os.sched_getaffinity(0)
        capacities = {cpu: int(Path(f"/sys/devices/system/cpu/cpu{cpu}/cpu_capacity").read_text())
                      for cpu in available}
        os.sched_setaffinity(0, {cpu for cpu in available if capacities[cpu] == max(capacities.values())})
    directory = checkpoint(args.model)
    with reserved_gpu(args.lock_timeout):
        start_state = machine_state()
        started = time.perf_counter()
        backend = make_backend(args, directory)
        load_seconds = time.perf_counter() - started
        if args.backend == "tinygrad":
            synchronize = backend.device.synchronize
        else:
            import mlx.core as mx
            synchronize = mx.synchronize
        started = time.perf_counter()
        checked = execute(backend, prompt, history, synchronize, expected)
        if not all(row["passed"] for row in checked["diagnostics"]):
            raise RuntimeError("independent numerical check failed: " + json.dumps(checked["diagnostics"]))
        for _ in range(args.warmups):
            warmup = execute(backend, prompt, history, synchronize)
            if warmup["predicted_token_ids"] != history:
                raise RuntimeError("warmup disagrees with the verified CPU history")
        setup_seconds = time.perf_counter() - started
        timed = execute(backend, prompt, history, synchronize)
        if timed["predicted_token_ids"] != history:
            raise RuntimeError("timed predictions disagree with the verified CPU history")
        if sources() != snapshot:
            raise RuntimeError("sources changed during the worker")
        drivers = {Path(line.split()[-1]) for line in Path("/proc/self/maps").read_text().splitlines()
                   if any(name in line for name in ("libRusticlOpenCL", "libvulkan_asahi"))}
        report = dict(status="PASS", backend=args.backend, dtype=args.dtype, beam=args.beam,
                      cpu_affinity=sorted(os.sched_getaffinity(0)),
                      runtime=backend.information, model_load_seconds=load_seconds,
                      validation_and_warmup_seconds=setup_seconds, warmup_passes=args.warmups,
                      correctness=checked["diagnostics"], timed=timed, counters=backend.counters(),
                      environment_start=start_state, environment_end=machine_state(),
                      reference_sha256={"trace.json": sha256(trace_path), "logits.npz": sha256(logits_path)},
                      provenance=dict(kernel=platform.release(), machine=platform.machine(),
                                      base_commit=base_commit(), runner_sources=snapshot,
                                      driver_library_sha256={str(p): sha256(p) for p in drivers}))
        args.output.write_text(json.dumps(report, indent=2) + "\n")


def summarize(runs):
    return dict(median_prefill_ms=statistics.median(r["timed"]["prefill_ms"] for r in runs),
                median_prefill_tokens_per_second=statistics.median(r["timed"]["prefill_tokens_per_second"] for r in runs),
                median_decode_tokens_per_second=statistics.median(r["timed"]["decode"]["steps_per_second"] for r in runs),
                trial_prefill_ms=[r["timed"]["prefill_ms"] for r in runs],
                trial_decode_tokens_per_second=[r["timed"]["decode"]["steps_per_second"] for r in runs],
                trial_kernel_dispatches=[r["timed"]["kernel_dispatches"] for r in runs])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=("mlx", "tinygrad", "all"), default="all")
    parser.add_argument("--dtype", choices=("float16", "float32"), default="float16")
    parser.add_argument("--beam", type=int, default=0)
    parser.add_argument("--model", type=Path)
    parser.add_argument("--prompt", default="What is 2 + 2?")
    parser.add_argument("--system")
    parser.add_argument("--raw", action="store_true")
    parser.add_argument("--thinking", action="store_true")
    parser.add_argument("--context", type=int, default=4096)
    parser.add_argument("--steps", type=int, default=8, help="cached decode steps after prefill (default: 8)")
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--warmups", type=int, default=2, help="complete untimed passes after validation (minimum: 2)")
    parser.add_argument("--lock-timeout", type=float, default=120)
    parser.add_argument("--worker-timeout", type=float, default=900)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--reference", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if (args.beam < 0 or not 1 <= args.steps <= 128 or not 1 <= args.trials <= 30 or
            not 2 <= args.warmups <= 30 or not 2 <= args.context <= 262144 or
            not 0 < args.lock_timeout <= 3600 or not 0 < args.worker_timeout <= 3600):
        parser.error("invalid counts, context or timeout; warmups must be at least 2")
    if args.worker:
        worker(args)
        return 0
    snapshot = sources()
    started = datetime.now(timezone.utc).isoformat()
    directory = checkpoint(args.model)
    output = (args.output or ROOT / "results" / f"benchmark-{args.dtype}.json").resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    modes = ("mlx", "tinygrad") if args.backend == "all" else (args.backend,)
    runs, order = {name: [] for name in modes}, []
    log_dir = output.parent / ".work" / output.stem
    log_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="applegpu-qwen-benchmark-") as temporary:
        reference = Path(temporary)
        print("Preparing one independent CPU token history...", flush=True)
        trace = prepare_reference(args, directory, reference)
        for trial in range(args.trials):
            rotated = modes[trial % len(modes):] + modes[:trial % len(modes)]
            for name in rotated:
                result_path = reference / "worker.json"
                result_path.unlink(missing_ok=True)
                command = [sys.executable, str(Path(__file__).resolve()), "--worker", "--backend", name,
                           "--dtype", args.dtype, "--beam", str(args.beam), "--model", str(directory),
                           "--context", str(args.context), "--steps", str(args.steps),
                           "--warmups", str(args.warmups), "--lock-timeout", str(args.lock_timeout),
                           "--reference", str(reference), "--output", str(result_path)]
                log_path = log_dir / f"{name}-trial{trial + 1}.log"
                print(f"Trial {trial + 1}/{args.trials}: {name} (validation and warmup excluded)", flush=True)
                with log_path.open("w") as stream:
                    completed = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, timeout=args.worker_timeout)
                if completed.returncode:
                    raise RuntimeError(f"{name} failed; {log_path}\n" + log_path.read_text()[-3000:])
                record = json.loads(result_path.read_text())
                if (record["status"] != "PASS" or record["backend"] != name or record["dtype"] != args.dtype or
                        record["provenance"]["runner_sources"] != snapshot or
                        record["timed"]["predicted_token_ids"] != trace["next_token_ids"] or
                        len(record["correctness"]) != args.steps + 1 or
                        not all(row["passed"] for row in record["correctness"]) or
                        record["timed"]["decode"]["samples"] != args.steps):
                    raise RuntimeError("worker returned unverified timings")
                record["log_sha256"] = sha256(log_path)
                runs[name].append(record)
                order.append(dict(trial=trial + 1, backend=name))
                print(f"  prefill {record['timed']['prefill_ms']:.2f} ms; decode "
                      f"{record['timed']['decode']['steps_per_second']:.2f} tok/s", flush=True)
    if sources() != snapshot:
        raise RuntimeError("sources changed during the benchmark")
    report = dict(schema_version=1, status="PASS", started_at_utc=started,
                  finished_at_utc=datetime.now(timezone.utc).isoformat(), model=MODEL_ID,
                  revision=REVISION, dtype=args.dtype, batch_size=1, context_capacity=args.context,
                  cached_decode_steps=args.steps, trials_per_backend=args.trials, tinygrad_beam=args.beam,
                  contract=dict(absolute_tolerance=ATOL, relative_tolerance=RTOL, identical_top1_required=True),
                  reference=trace, run_order=order, runs=runs,
                  summaries={name: summarize(records) for name, records in runs.items()},
                  source_sha256=snapshot, command=sys.argv,
                  timing_scope="Completed GPU prediction, recurrent/KV updates, finite-logit check, GPU argmax and one-token read. Excludes reset fills, loading, compilation, JIT capture, tuning, full-logit copies, tokenization and printing.",
                  comparison_scope="Same checkpoint, dtype, prompt and independent CPU token history. Fresh sequential worker processes; backend order rotates each round; clocks are not fixed.")
    output.write_text(json.dumps(report, indent=2) + "\n")
    for name, row in report["summaries"].items():
        print(f"{name}: median prefill {row['median_prefill_ms']:.2f} ms; "
              f"median decode {row['median_decode_tokens_per_second']:.2f} tok/s")
    print("Saved", output)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ImportError, OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        print(f"Qwen benchmark: FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
