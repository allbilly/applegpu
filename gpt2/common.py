"""Shared GPT-2 checkpoint, tokenizer and independent NumPy reference."""

import hashlib
import json
import os
from pathlib import Path
import tempfile
import urllib.request

import numpy as np
from safetensors.numpy import load_file

from bpe import Tokenizer

ROOT = Path(__file__).resolve().parent
REVISION = "607a30d783dfa663caf39e06633721c8d4cfcd7e"
WEIGHT_SHA256 = "248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707"
WEIGHT_URL = f"https://huggingface.co/openai-community/gpt2/resolve/{REVISION}/model.safetensors"
CONFIG = dict(model_type="gpt2", n_ctx=1024, n_embd=768, n_head=12,
              n_layer=12, n_positions=1024, layer_norm_epsilon=1e-5, vocab_size=50257)


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def cache_root():
    return Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "applegpu-gpt2"


def checkpoint(requested=None, download=False):
    if requested or os.environ.get("GPT2_WEIGHTS"):
        source = Path(requested or os.environ["GPT2_WEIGHTS"]).expanduser().resolve()
        if source.is_dir():
            source /= "model.safetensors"
        if not source.is_file():
            raise ValueError(f"checkpoint missing: {source}")
    else:
        hf_home = Path(os.environ.get("HF_HOME", cache_root().parent / "huggingface"))
        hub = Path(os.environ.get("HF_HUB_CACHE", hf_home / "hub"))
        candidates = [cache_root() / "model.safetensors",
                      cache_root().parent / "orion-gpt2/model.safetensors"]
        for repo in ("models--openai-community--gpt2", "models--gpt2"):
            candidates += sorted((hub / repo).glob("snapshots/*/model.safetensors"))
        source = next((p for p in candidates if p.is_file()), None)
        if source is None:
            if not download:
                raise ValueError("GPT-2 weights missing; run first-run.sh setup or pass --weights")
            cache_root().mkdir(parents=True, exist_ok=True)
            source = cache_root() / "model.safetensors"
            fd, name = tempfile.mkstemp(prefix=".gpt2-", dir=cache_root())
            temporary = Path(name)
            try:
                with os.fdopen(fd, "wb") as stream, urllib.request.urlopen(WEIGHT_URL, timeout=90) as response:
                    while block := response.read(1024 * 1024):
                        stream.write(block)
                if sha256(temporary) != WEIGHT_SHA256:
                    raise ValueError("downloaded checkpoint SHA256 mismatch")
                temporary.replace(source)
            finally:
                temporary.unlink(missing_ok=True)
    if sha256(source) != WEIGHT_SHA256:
        raise ValueError("checkpoint differs from the pinned GPT-2 124M used by ~/ane/gpt2")
    return source


def load_state(path):
    """HF Conv1D matrices remain [input, output] in the shared state."""
    state = {key.removeprefix("transformer."): value for key, value in load_file(str(path)).items()
             if key != "lm_head.weight" and not key.endswith((".attn.bias", ".attn.masked_bias"))}
    if state["wte.weight"].shape != (50257, 768) or len(state) != 148:
        raise ValueError("expected the full GPT-2 124M checkpoint")
    return state


def tokenizer():
    return Tokenizer(ROOT / "tokenizer")


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
