#!/usr/bin/env python3
"""Create a teacher-forced CPU reference before any GPU model is loaded."""

import os
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import argparse
import json
from pathlib import Path
import time

import numpy as np

from common import Reference, WEIGHT_SHA256, checkpoint, load_state, sha256, tokenizer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weights", type=Path)
    parser.add_argument("--dtype", choices=("float32", "float16"), default="float32")
    parser.add_argument("--steps", type=int, default=64)
    parser.add_argument("--lengths", type=int, nargs="+", default=[2, 32, 64])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.steps < 1 or any(n < 1 or n + args.steps > 1024 for n in args.lengths):
        parser.error("reference must fit the GPT-2 context")
    source = checkpoint(args.weights)
    begin = time.perf_counter()
    state = load_state(source)
    model = Reference(state, args.dtype)
    del state
    codec = tokenizer()
    narrative = codec.encode(("The Apple Neural Engine can run language models. "
                              "This is a story about a small computer and the people who built it. ") * 50)
    cases, arrays = [], {}
    args.output.mkdir(parents=True, exist_ok=True)
    for index, length in enumerate(args.lengths):
        prompt = codec.encode("Hello world") if length == 2 else narrative[:length]
        model.reset()
        for token in prompt:
            logits = model.step(token)
        outputs, tokens = [logits], [int(logits.argmax())]
        for _ in range(args.steps):
            logits = model.step(tokens[-1])
            outputs.append(logits)
            tokens.append(int(logits.argmax()))
        arrays[f"case_{index}"] = np.stack(outputs)
        cases.append(dict(prompt_ids=prompt, prompt_text=codec.decode(prompt), next_tokens=tokens,
                          logits_key=f"case_{index}"))
        print(f"CPU reference: prompt={length}, predictions={len(outputs)}", flush=True)
    np.savez(args.output / "logits.npz", **arrays)
    (args.output / "trace.json").write_text(json.dumps(dict(checkpoint_sha256=WEIGHT_SHA256,
        parameter_dtype=args.dtype, reference_math="NumPy FP32 activations, exact stored parameter values",
        source_sha256={p.name: sha256(p) for p in (Path(__file__), Path(__file__).with_name("common.py"))},
        steps=args.steps, cases=cases, preparation_seconds=time.perf_counter() - begin), indent=2) + "\n")


if __name__ == "__main__":
    main()
