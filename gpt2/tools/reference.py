#!/usr/bin/env python3
"""Create a teacher-forced CPU reference before any GPU model is loaded."""

import os
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import argparse
import json
from pathlib import Path
import sys
import time

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import ROOT, WEIGHT_SHA256, checkpoint, load_state, sha256, tokenizer


class Reference:
    """FP32 activation math; parameters rounded to the requested GPU storage dtype."""

    def __init__(self, state, dtype="float32"):
        self.state = {k: np.asarray(v, dtype=dtype).astype(np.float32, copy=False) for k, v in state.items()}
        self.reset()

    def reset(self):
        self.position = 0
        self.keys = np.empty((12, 12, 1024, 64), dtype=np.float32)
        self.values = np.empty_like(self.keys)

    def norm(self, x, prefix):
        centered = x - x.mean(axis=-1, keepdims=True)
        return (centered / np.sqrt((centered * centered).mean(axis=-1, keepdims=True) + np.float32(1e-5))
                * self.state[prefix + ".weight"] + self.state[prefix + ".bias"])

    def linear(self, x, prefix):
        return x @ self.state[prefix + ".weight"] + self.state[prefix + ".bias"]

    def step(self, token):
        if self.position >= 1024 or not 0 <= token < 50257:
            raise ValueError("invalid token or exhausted context")
        pos = self.position
        x = self.state["wte.weight"][token] + self.state["wpe.weight"][pos]
        for i in range(12):
            p = f"h.{i}"
            q, k, v = np.split(self.linear(self.norm(x, p + ".ln_1"), p + ".attn.c_attn"), 3)
            self.keys[i, :, pos] = k.reshape(12, 64)
            self.values[i, :, pos] = v.reshape(12, 64)
            scores = np.einsum("htd,hd->ht", self.keys[i, :, :pos + 1], q.reshape(12, 64)) * np.float32(0.125)
            probability = np.exp(scores - scores.max(axis=-1, keepdims=True))
            probability /= probability.sum(axis=-1, keepdims=True)
            attended = np.einsum("ht,htd->hd", probability, self.values[i, :, :pos + 1]).reshape(768)
            x = x + self.linear(attended, p + ".attn.c_proj")
            z = self.linear(self.norm(x, p + ".ln_2"), p + ".mlp.c_fc")
            z = np.float32(0.5) * z * (np.float32(1) + np.tanh(
                np.float32(np.sqrt(2 / np.pi)) * (z + np.float32(0.044715) * z * z * z)))
            x = x + self.linear(z, p + ".mlp.c_proj")
        self.position += 1
        return self.state["wte.weight"] @ self.norm(x, "ln_f")


def accuracy(actual, expected):
    a, b = np.asarray(actual, dtype=np.float64), np.asarray(expected, dtype=np.float64)
    if a.shape != (50257,) or not np.isfinite(a).all():
        raise ValueError("GPU returned invalid logits")
    log_a, log_b = a - a.max(), b - b.max()
    log_a -= np.log(np.exp(log_a).sum())
    log_b -= np.log(np.exp(log_b).sum())
    return dict(top1=int(a.argmax()), reference_top1=int(b.argmax()),
                max_abs_error=float(np.abs(a - b).max()),
                normalized_rmse=float(np.linalg.norm(a - b) / max(np.linalg.norm(b), 1e-9)),
                kl_reference_to_gpu=float(max(0, (np.exp(log_b) * (log_b - log_a)).sum())))


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
        source_sha256={str(p.relative_to(ROOT)): sha256(p) for p in
                       (Path(__file__).resolve(), ROOT / "common.py", ROOT / "bpe.py")},
        steps=args.steps, cases=cases, preparation_seconds=time.perf_counter() - begin), indent=2) + "\n")


if __name__ == "__main__":
    main()
