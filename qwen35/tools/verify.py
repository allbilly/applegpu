"""Full-vocabulary checks against the independent CPU mathematical decoder."""

import gc
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import platform
import sys
import time

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from checkpoint import FILES, MODEL_ID, REVISION, ROOT, sha256
from reference import Reference


# Fixed before GPU execution; original checkpoint, FP64 math. These bounds
# include FP16 activation transport and are not a bit-exact rounding contract.
ATOL, RTOL = 0.05, 0.003


def source_hashes():
    paths = list(ROOT.glob("*.py")) + list((ROOT / "tools").glob("*.py"))
    paths += [ROOT / "first-run.sh", ROOT.parent / "gpt2/run_utils.py"]
    return {str(p.relative_to(ROOT.parent)): sha256(p) for p in paths}


def compare(actual, expected, selected):
    a, b = np.asarray(actual, dtype=np.float64), np.asarray(expected, dtype=np.float64)
    if a.shape != (248320,) or b.shape != a.shape or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError("verification requires finite full-vocabulary logits")
    error = np.abs(a - b)
    bound = ATOL + RTOL * np.abs(b)
    actual_top, reference_top = int(a.argmax()), int(b.argmax())
    return dict(passed=bool(np.all(error <= bound) and selected == actual_top == reference_top),
                selected=int(selected), actual_top1=actual_top, reference_top1=reference_top,
                max_abs_error=float(error.max()), max_bound_ratio=float((error / bound).max()),
                values_outside_bound=int(np.count_nonzero(error > bound)),
                normalized_rmse=float(np.linalg.norm(a - b) / max(np.linalg.norm(b), 1e-12)))


def run(args, directory, prompt):
    # Import the CLI helpers only here; importing this module never loads a GPU.
    from qwen35 import base_commit, make_backend
    sys.path.insert(0, str(ROOT.parent / "gpt2"))
    from run_utils import gpu_lock, machine_state
    sys.path.pop(0)
    sources = source_hashes()
    report = dict(schema_version=1, timestamp_utc=datetime.now(timezone.utc).isoformat(),
                  status="FAIL", model=MODEL_ID, revision=REVISION, dtype=args.dtype,
                  prompt_token_ids=prompt, steps=args.steps,
                  contract=dict(absolute_tolerance=ATOL, relative_tolerance=RTOL,
                                every_logit_within_bound=True, identical_top1_required=True),
                  reference="Original checkpoint, independent NumPy FP64 mathematical decoder",
                  scope="Whole and split prompt processing followed by CPU-history-forced decode; no performance claim",
                  checks=[])
    with gpu_lock():
        report["environment_start"] = machine_state()
        begin = time.perf_counter()
        print("Computing independent CPU reference...", file=sys.stderr, flush=True)
        reference = Reference(directory, capacity=args.context)
        expected, history = [], []
        for i in range(args.steps):
            logits = reference.predict(prompt if i == 0 else [history[-1]])
            expected.append(logits)
            history.append(int(logits.argmax()))
        report["reference_seconds"] = time.perf_counter() - begin
        report["reference_token_ids"] = history
        del reference
        gc.collect()
        print("Checking GPU logits on the CPU reference history...", file=sys.stderr, flush=True)
        backend = make_backend(args, directory)
        report["runtime"] = backend.information
        split = max(1, len(prompt) // 2)
        phases = ["whole_prompt"] + (["split_prompt"] if len(prompt) > 1 else [])
        captured = []
        for phase in phases:
            backend.reset()
            if phase == "split_prompt":
                backend.predict(prompt[:split])
            for step, target in enumerate(expected):
                tokens = (prompt[split:] if phase == "split_prompt" else prompt) if step == 0 else [history[step - 1]]
                selected = backend.predict(tokens)
                actual = backend.logits()
                if args.logits_output:
                    captured.append(actual.copy())
                row = dict(phase=phase, step=step, **compare(actual, target, selected))
                report["checks"].append(row)
                print(f"{phase} step {step}: {'PASS' if row['passed'] else 'FAIL'}, "
                      f"max error {row['max_abs_error']:.6g}", file=sys.stderr, flush=True)
        if sources != source_hashes():
            raise RuntimeError("runner source changed during verification")
        drivers = {Path(line.split()[-1]) for line in Path("/proc/self/maps").read_text().splitlines()
                   if any(name in line for name in ("libRusticlOpenCL", "libvulkan_asahi"))}
        report["provenance"] = dict(base_commit=base_commit(), kernel=platform.release(),
                                    machine=platform.machine(), checkpoint_sha256=FILES,
                                    runner_sources=sources, command=sys.argv,
                                    numpy_version=importlib.metadata.version("numpy"),
                                    driver_library_sha256={p.name: sha256(p) for p in drivers})
        report["environment_end"] = machine_state()
        report["vocabulary_values_compared"] = len(report["checks"]) * 248320
        report["status"] = "PASS" if all(row["passed"] for row in report["checks"]) else "FAIL"
        if args.logits_output:
            args.logits_output.parent.mkdir(parents=True, exist_ok=True)
            np.savez(args.logits_output, reference_logits=np.stack(expected), gpu_logits=np.stack(captured))
    destination = args.output or ROOT / "results" / f"verify-{args.backend}-{args.dtype}.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Qwen3.5 verification: {report['status']} ({len(report['checks'])} vectors); receipt: {destination}")
    return int(report["status"] != "PASS")


def main():
    import argparse
    import os
    from collections.abc import Mapping
    from checkpoint import checkpoint, tokenizer

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=("mlx", "tinygrad"), default="mlx")
    parser.add_argument("--model", type=Path)
    parser.add_argument("--dtype", choices=("float16", "float32"), default="float16")
    parser.add_argument("--beam", type=int, default=int(os.environ.get("BEAM", "0")))
    parser.add_argument("--prompt", default="What is 2 + 2?")
    parser.add_argument("--system")
    parser.add_argument("--raw", action="store_true")
    parser.add_argument("--thinking", action="store_true")
    parser.add_argument("--steps", type=int, default=4)
    parser.add_argument("--context", type=int, default=4096)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--logits-output", type=Path)
    args = parser.parse_args()
    if args.beam < 0 or not 1 <= args.steps <= 128 or not 2 <= args.context <= 262144:
        parser.error("invalid steps, BEAM width or context")
    try:
        directory = checkpoint(args.model)
        codec = tokenizer(directory)
        messages = ([dict(role="system", content=args.system)] if args.system else []) + [dict(role="user", content=args.prompt)]
        prompt = codec.encode(args.prompt, add_special_tokens=False) if args.raw else codec.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True, enable_thinking=args.thinking)
        if isinstance(prompt, Mapping):
            prompt = prompt["input_ids"]
        if not prompt or len(prompt) + args.steps - 1 > args.context:
            raise ValueError("prompt plus checked predictions must fit the requested context")
        return run(args, directory, prompt)
    except (ImportError, OSError, ValueError, RuntimeError) as error:
        print(f"Qwen3.5 verification: FAIL: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
