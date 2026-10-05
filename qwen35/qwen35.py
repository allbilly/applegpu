#!/usr/bin/env python3
"""Qwen3.5-0.8B text generation on the M1 GPU under Asahi Linux."""

import os
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import argparse
from collections.abc import Mapping
import json
from pathlib import Path
import platform
import sys
import subprocess
import time

import numpy as np

from checkpoint import FILES, MODEL_ID, REVISION, ROOT, checkpoint, sha256, tokenizer

sys.path.insert(0, str(ROOT.parent / "gpt2"))
from gpt2 import gpu_lock, machine_state, stats
sys.path.pop(0)

SOURCE_HASHES = {p.name: sha256(p) for p in ROOT.glob("*.py")}


def base_commit():
    try:
        return subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                                       stderr=subprocess.DEVNULL, text=True, timeout=5).strip()
    except (OSError, subprocess.SubprocessError):
        return None


def make_backend(args, directory):
    if args.backend == "mlx":
        from mlx_backend import Backend
    else:
        from tinygrad_backend import Backend
    return Backend(directory, dtype=args.dtype, capacity=args.context, beam=args.beam)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", choices=("generate", "setup"), default="generate")
    parser.add_argument("--backend", choices=("mlx", "tinygrad"), default="mlx")
    parser.add_argument("--model", type=Path)
    parser.add_argument("--dtype", choices=("float16", "float32"), default="float16")
    parser.add_argument("--beam", type=int, default=int(os.environ.get("BEAM", "0")))
    parser.add_argument("--prompt", default="What is 2 + 2?")
    parser.add_argument("--system")
    parser.add_argument("--raw", action="store_true", help="use the prompt directly without a chat template")
    parser.add_argument("--thinking", action="store_true", help="enable Qwen's thinking chat template")
    parser.add_argument("--max-tokens", type=int, default=64)
    parser.add_argument("--context", type=int, default=4096)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--logits-output", type=Path, help="save full logits outside inference timers for numerical comparison")
    args = parser.parse_args()
    if args.max_tokens < 1 or args.beam < 0 or not 2 <= args.context <= 262144:
        parser.error("invalid token count, beam width or context capacity")
    try:
        directory = checkpoint(args.model)
        if args.command == "setup":
            print("Verified official checkpoint:", directory)
            return 0
        codec = tokenizer(directory)
        messages = ([dict(role="system", content=args.system)] if args.system else []) + [dict(role="user", content=args.prompt)]
        prompt = codec.encode(args.prompt, add_special_tokens=False) if args.raw else codec.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True, enable_thinking=args.thinking)
        if isinstance(prompt, Mapping):
            prompt = prompt["input_ids"]
        if not prompt or len(prompt) + args.max_tokens - 1 > args.context:
            raise ValueError("prompt plus generation must fit the requested context")
        stop = {248044, 248046}
        with gpu_lock():
            start_state = machine_state()
            started = time.perf_counter()
            backend = make_backend(args, directory)
            load_seconds = time.perf_counter() - started
            print(json.dumps(backend.information), file=sys.stderr, flush=True)
            generated, samples, logits = [], [], []
            begin = time.perf_counter_ns()
            selected = backend.predict(prompt)
            prefill_ms = (time.perf_counter_ns() - begin) / 1e6
            if args.logits_output:
                logits.append(backend.logits())
            printed = ""
            for index in range(args.max_tokens):
                generated.append(selected)
                if selected in stop:
                    break
                text = codec.decode(generated, skip_special_tokens=True)
                # Wait for complete UTF-8 sequences before streaming their text.
                if not text.endswith("\ufffd") and text.startswith(printed):
                    print(text[len(printed):], end="", flush=True)
                    printed = text
                if index + 1 < args.max_tokens:
                    begin = time.perf_counter_ns()
                    selected = backend.predict([selected])
                    samples.append((time.perf_counter_ns() - begin) / 1e6)
                    if args.logits_output:
                        logits.append(backend.logits())
            text = codec.decode(generated, skip_special_tokens=True)
            if text.startswith(printed):
                print(text[len(printed):], end="")
            print(flush=True)
            if SOURCE_HASHES != {p.name: sha256(p) for p in ROOT.glob("*.py")}:
                raise RuntimeError("runner source changed during execution; rerun with stable sources")
            if logits and not all(np.isfinite(vector).all() for vector in logits):
                raise RuntimeError("model produced nonfinite logits")
            drivers = {Path(line.split()[-1]) for line in Path("/proc/self/maps").read_text().splitlines()
                       if any(n in line for n in ("libRusticlOpenCL", "libvulkan_asahi"))}
            report = dict(status="PASS", model=MODEL_ID, revision=REVISION, mode="text-only", dtype=args.dtype,
                prompt=args.prompt, messages=None if args.raw else messages, thinking=args.thinking,
                prompt_token_ids=prompt, generated_token_ids=generated, text=text,
                stopped_on_eos=generated[-1] in stop, model_load_seconds=load_seconds,
                prefill_ms=prefill_ms, prefill_tokens_per_second=1000 * len(prompt) / prefill_ms,
                decode=stats(samples) if samples else None, counters=backend.counters(),
                environment_start=start_state, environment_end=machine_state(),
                timing_scope="Completed GPU prediction, state updates and one-token read; excludes tokenization, printing and full-logit copies. Includes first-use compilation/JIT capture; use warmed runs for performance comparisons.",
                provenance=dict(runtime=backend.information, kernel=platform.release(), machine=platform.machine(),
                    base_commit=base_commit(),
                    checkpoint_sha256=FILES, runner_sources=SOURCE_HASHES,
                    driver_library_sha256={p.name: sha256(p) for p in drivers}, command=sys.argv))
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(json.dumps(report, indent=2) + "\n")
            if args.logits_output:
                args.logits_output.parent.mkdir(parents=True, exist_ok=True)
                np.savez(args.logits_output, logits=np.stack(logits))
            print(f"GPU generation: prompt={len(prompt)}, generated={len(generated)}, prefill={prefill_ms:.1f} ms, "
                  f"decode={report['decode']['steps_per_second'] if samples else 0:.2f} tok/s (first use)", file=sys.stderr)
        return 0
    except (ImportError, OSError, ValueError, RuntimeError) as error:
        print(f"Qwen3.5: FAIL: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
