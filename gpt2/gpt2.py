#!/usr/bin/env python3
"""Minimal GPT-2 124M generation example on the Asahi M1 GPU."""

import os
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import argparse
import codecs
import importlib.metadata
import json
from pathlib import Path
import platform
import sys
import time


from common import ROOT, WEIGHT_SHA256, checkpoint, load_state, sha256, tokenizer
from run_utils import gpu_lock, stats

SOURCE_HASHES = {p.name: sha256(p) for p in ROOT.glob("*.py")}


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
    parser.add_argument("command", nargs="?", choices=("generate", "setup"), default="generate")
    parser.add_argument("--backend", choices=("tinygrad", "mlx"), default="tinygrad")
    parser.add_argument("--beam", type=int, default=int(os.environ.get("BEAM", "0")))
    parser.add_argument("--dtype", choices=("float32", "float16"), default="float32")
    parser.add_argument("--weights", type=Path)
    parser.add_argument("--context", type=int, default=1024)
    parser.add_argument("--prompt", default="Hello world")
    parser.add_argument("--max-tokens", type=int, default=32)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not 2 <= args.context <= 1024 or args.beam < 0:
        parser.error("invalid context or BEAM width")
    try:
        if args.command == "setup":
            print("Verified weights:", checkpoint(args.weights, download=True))
        else:
            generate(args)
        return 0
    except (ImportError, OSError, ValueError, RuntimeError) as error:
        print(f"GPT-2: FAIL: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
