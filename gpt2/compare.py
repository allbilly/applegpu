#!/usr/bin/env python3
"""Compare warmed GPT-2 inference on MLX Vulkan and tinygrad OpenCL with BEAM."""

import os
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import argparse
import datetime
import json
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time

from common import ROOT, WEIGHT_SHA256, cache_root, checkpoint, sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dtype", choices=("float32", "float16"), default="float32")
    parser.add_argument("--beams", type=int, nargs="+", default=[0, 2])
    parser.add_argument("--lengths", type=int, nargs="+", default=[2, 32, 64])
    parser.add_argument("--steps", type=int, default=64)
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--weights", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--worker-timeout", type=int, default=1800)
    parser.add_argument("--resume", action="store_true", help="reuse completed workers with matching inputs and runner code")
    args = parser.parse_args()
    if args.steps < 1 or args.trials < 1 or any(b < 0 for b in args.beams) or any(
            n < 1 or n + args.steps > 1024 for n in args.lengths):
        parser.error("invalid beam widths, context lengths or measurement counts")
    source = checkpoint(args.weights, download=True)
    output = args.output or ROOT / "results" / f"compare-{args.dtype}.json"
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    identity = sha256(ROOT / "reference.py") + sha256(ROOT / "common.py")
    reference = cache_root() / f"reference-{args.dtype}-{args.steps}-{'-'.join(map(str, args.lengths))}-{identity[:12]}"
    trace_path = reference / "trace.json"
    wanted_sources = {n: sha256(ROOT / n) for n in ("reference.py", "common.py")}
    if not trace_path.is_file() or json.loads(trace_path.read_text()).get("source_sha256") != wanted_sources:
        subprocess.run([sys.executable, str(ROOT / "reference.py"), "--weights", str(source),
                        "--dtype", args.dtype, "--steps", str(args.steps), "--lengths", *map(str, args.lengths),
                        "--output", str(reference)], check=True, timeout=600)
    modes = [("mlx", 0)] + [("tinygrad", b) for b in dict.fromkeys(args.beams)]
    records = {f"{backend}-beam{beam}": [] for backend, beam in modes}
    logs = output.parent / ".work" / output.stem
    logs.mkdir(parents=True, exist_ok=True)
    order = []
    worker_sources = {p.name: sha256(p) for p in ROOT.glob("*.py") if p.name != "compare.py"}
    reference_hashes = {n: sha256(reference / n) for n in ("trace.json", "logits.npz")}
    for trial in range(args.trials):
        rotated = modes[trial % len(modes):] + modes[:trial % len(modes)]
        for backend, beam in rotated:
            label = f"{backend}-beam{beam}"
            result_path = logs / f"{label}-trial{trial + 1}.json"
            log_path = result_path.with_suffix(".log")
            record = None
            if args.resume and result_path.is_file() and log_path.is_file():
                previous = json.loads(result_path.read_text())
                proof = previous["provenance"]
                libraries_match = all((Path("/usr/lib64") / n).is_file() and
                    sha256(Path("/usr/lib64") / n) == digest for n, digest in proof["driver_library_sha256"].items())
                if (previous["status"] == "PASS" and previous["backend"] == backend and previous["beam"] == beam
                        and previous["dtype"] == args.dtype and previous["reference_sha256"] == reference_hashes
                        and proof["kernel"] == platform.release() and libraries_match
                        and {k: v for k, v in proof["runner_sources"].items() if k != "compare.py"} == worker_sources
                        and (backend != "tinygrad" or proof["runtime"]["beam_estimate"] == int(os.environ.get("BEAM_ESTIMATE", "1")))
                        and [c["prompt_tokens"] for c in previous["cases"]] == args.lengths
                        and all(len(c["trials"]) == 1 and c["trials"][0]["decode"]["samples"] == args.steps
                                for c in previous["cases"])):
                    record = previous
            order.append(dict(trial=trial + 1, mode=label, reused=record is not None))
            if record is not None:
                record["log_sha256"] = sha256(log_path)
                records[label].append(record)
                print(f"Trial {trial + 1}/{args.trials}: {label}: reused verified worker", flush=True)
                continue
            command = [sys.executable, str(ROOT / "gpt2.py"), "worker", "--backend", backend,
                       "--beam", str(beam), "--dtype", args.dtype, "--reference", str(reference),
                       "--weights", str(source), "--steps", str(args.steps), "--trials", "1",
                       "--warmups", "2", "--output", str(result_path)]
            print(f"Trial {trial + 1}/{args.trials}: {label} (validation and tuning excluded from timing)", flush=True)
            deadline = time.monotonic() + args.worker_timeout
            while True:
                with log_path.open("w") as stream:
                    completed = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT,
                                               timeout=max(1, deadline - time.monotonic()))
                if not completed.returncode or "GPU is reserved by another job:" not in log_path.read_text():
                    break
                if time.monotonic() >= deadline:
                    break
                print(f"  {label}: waiting for the shared GPU lock", flush=True)
                time.sleep(5)
            if completed.returncode:
                print(log_path.read_text()[-6000:], file=sys.stderr)
                raise RuntimeError(f"{label} failed; see {log_path}")
            record = json.loads(result_path.read_text())
            record["log_sha256"] = sha256(log_path)
            records[label].append(record)
            print("  " + ", ".join(f"prompt={c['prompt_tokens']}: {c['trials'][0]['decode']['steps_per_second']:.2f} steps/s"
                                    for c in record["cases"]), flush=True)
            time.sleep(2)
    summaries = {}
    for label, runs in records.items():
        cases = []
        for index, length in enumerate(args.lengths):
            trials = [run["cases"][index]["trials"][0] for run in runs]
            samples = [v for trial in trials for v in trial["decode"]["raw_ms"]]
            cases.append(dict(prompt_tokens=length,
                              median_prefill_ms=statistics.median(t["prefill_ms"] for t in trials),
                              median_prefill_tokens_per_second=statistics.median(t["prefill_tokens_per_second"] for t in trials),
                              trial_prefill_ms=[t["prefill_ms"] for t in trials],
                              trial_prefill_tokens_per_second=[t["prefill_tokens_per_second"] for t in trials],
                              median_decode_steps_per_second=statistics.median(t["decode"]["steps_per_second"] for t in trials),
                              median_decode_ms_per_token=statistics.median(t["decode"]["mean_ms"] for t in trials),
                              combined_decode_steps_per_second=1000 * len(samples) / sum(samples),
                              trial_decode_steps_per_second=[t["decode"]["steps_per_second"] for t in trials],
                              verified_predictions=sum(len(run["cases"][index]["correctness"]["diagnostics"]) for run in runs)))
        summaries[label] = dict(runtime=runs[0]["provenance"]["runtime"], cases=cases)
    report = dict(status="PASS", started_at_utc=started,
                  finished_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  model="GPT-2 124M", checkpoint_sha256=WEIGHT_SHA256, dtype=args.dtype,
                  batch_size=1, context_capacity=1024, decode_steps=args.steps,
                  trials_per_mode=args.trials, run_order=order, summaries=summaries, runs=records,
                  resumed_workers=sum(item["reused"] for item in order),
                  timing_scope="Completed GPU model execution, KV update, GPU argmax and one-token host read; excludes model loading, first compilation, BEAM tuning, full-logit validation and detokenization",
                  comparison_scope="Same M1 GPU, stock Mesa, checkpoint, parameter dtype, prompt and teacher-forced decode tokens. Backend graph lowering and KV cache implementations differ.",
                  command=sys.argv, source_sha256={p.name: sha256(p) for p in ROOT.glob("*.py")})
    output.write_text(json.dumps(report, indent=2) + "\n")
    print("\nMode                     Prompt    Prefill ms    Prefill tok/s    Decode tok/s", flush=True)
    for label, summary in summaries.items():
        for case in summary["cases"]:
            print(f"{label:24} {case['prompt_tokens']:6} {case['median_prefill_ms']:13.2f} "
                  f"{case['median_prefill_tokens_per_second']:16.2f} "
                  f"{case['median_decode_steps_per_second']:17.2f}", flush=True)
    print("Saved", output, flush=True)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"GPT-2 comparison: FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
