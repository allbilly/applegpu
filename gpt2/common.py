"""Pinned GPT-2 checkpoint and tokenizer for the minimal example."""

import hashlib
import os
from pathlib import Path
import tempfile
import urllib.request

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
