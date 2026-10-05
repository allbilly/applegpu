"""Pinned official Qwen3.5-0.8B assets and streaming text-weight loading."""

import concurrent.futures
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import tempfile
import time
import urllib.request

import numpy as np

ROOT = Path(__file__).resolve().parent
MODEL_ID = "Qwen/Qwen3.5-0.8B"
REVISION = "2fc06364715b967f1860aea9cf38778875588b17"
WEIGHTS = "model.safetensors-00001-of-00001.safetensors"
WEIGHT_SIZE = 1746942600
FILES = {
    WEIGHTS: "04b1c301231dd422b8860db31311ab2721511346a32cb1e079c4c4e5f1fe4696",
    "config.json": "b90b86f35c8e6925ef74ee04d0e758f0a845c83a42089ad82bbaa948de9b4204",
    "tokenizer.json": "5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42",
    "tokenizer_config.json": "49e2b6e395f959f077f1e992b338919c0d4a9732fc6e613995e06557f843500c",
    "chat_template.jinja": "273d8e0e683b885071fb17e08d71e5f2a5ddfb5309756181681de4f5a1822d80",
    "LICENSE": "bbedc3fda3305820b977265f01b8619d87570a6739de3a5582c3464840f1e57a",
}


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def cache_root():
    return Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "applegpu-qwen35"


def fetch_range(fd, url, start, end, total):
    cursor = start
    for attempt in range(5):
        try:
            request = urllib.request.Request(url, headers={"Range": f"bytes={cursor}-{end}"})
            with urllib.request.urlopen(request, timeout=90) as response:
                expected_range = f"bytes {cursor}-{end}/{total}"
                if response.status != 206 or response.headers.get("Content-Range") != expected_range:
                    raise ValueError(f"server did not honor range {expected_range}")
                while block := response.read(4 << 20):
                    if cursor + len(block) > end + 1 or os.pwrite(fd, block, cursor) != len(block):
                        raise OSError("invalid or short checkpoint write")
                    cursor += len(block)
            if cursor == end + 1:
                return
        except (OSError, ValueError):
            if attempt == 4:
                raise
        time.sleep(attempt + 1)
    raise OSError(f"truncated checkpoint response: bytes {cursor}-{end} missing")


def _download(url, target, expected):
    fd, name = tempfile.mkstemp(prefix=".qwen35-", dir=target.parent)
    temporary = Path(name)
    try:
        if target.name == WEIGHTS:
            try:
                os.ftruncate(fd, WEIGHT_SIZE)
                ranges = [(n, min(n + (16 << 20) - 1, WEIGHT_SIZE - 1)) for n in range(0, WEIGHT_SIZE, 16 << 20)]
                with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
                    list(pool.map(lambda span: fetch_range(fd, url, *span, WEIGHT_SIZE), ranges))
            finally:
                os.close(fd)
        else:
            with os.fdopen(fd, "wb") as stream, urllib.request.urlopen(url, timeout=90) as response:
                while block := response.read(4 << 20):
                    stream.write(block)
        if sha256(temporary) != expected:
            raise ValueError(f"downloaded {target.name} failed SHA256 validation")
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)


def checkpoint(requested=None, download=True):
    directory = Path(requested or os.environ.get("QWEN35_MODEL", cache_root() / "model")).expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True)
    for name, expected in FILES.items():
        path = directory / name
        if not path.is_file():
            if requested or not download:
                raise ValueError(f"missing checkpoint asset: {path}")
            print(f"Downloading {MODEL_ID}: {name}", flush=True)
            _download(f"https://huggingface.co/{MODEL_ID}/resolve/{REVISION}/{name}", path, expected)
        if sha256(path) != expected:
            raise ValueError(f"{path} differs from the pinned official Qwen3.5-0.8B checkpoint")
    return directory


class Weights:
    """Read one learned text tensor at a time, with bounded BF16 conversion."""

    def __init__(self, directory):
        self.path = Path(directory) / WEIGHTS
        with self.path.open("rb") as stream:
            size = struct.unpack("<Q", stream.read(8))[0]
            if size > 16 << 20 or size + 8 > self.path.stat().st_size:
                raise ValueError("invalid safetensors header")
            self.header = json.loads(stream.read(size))
        self.offset = size + 8
        self.data = np.memmap(self.path, mode="r", dtype=np.uint8)
        self.entries = {}
        for name, spec in self.header.items():
            prefix = "model.language_model."
            if not name.startswith(prefix):
                continue
            key = name[len(prefix):]
            if spec["dtype"] not in ("BF16", "F32", "F16"):
                raise ValueError(f"unsupported tensor type: {name}")
            start, end = spec["data_offsets"]
            width = 4 if spec["dtype"] == "F32" else 2
            if start < 0 or end - start != math.prod(spec["shape"]) * width or self.offset + end > len(self.data):
                raise ValueError(f"invalid tensor span: {name}")
            self.entries[key] = spec
        if self.entries.get("embed_tokens.weight", {}).get("shape") != [248320, 1024]:
            raise ValueError("expected the Qwen3.5-0.8B text embedding")

    def tensor(self, key, dtype="float16"):
        spec = self.entries[key]
        start, end = spec["data_offsets"]
        storage = {"BF16": "<u2", "F16": "<f2", "F32": "<f4"}[spec["dtype"]]
        raw = self.data[self.offset + start:self.offset + end].view(storage).reshape(spec["shape"])
        is_norm = key.endswith(("input_layernorm.weight", "post_attention_layernorm.weight",
                                "self_attn.q_norm.weight", "self_attn.k_norm.weight")) or key == "norm.weight"
        target_dtype = "float32" if is_norm or key.endswith(("A_log", "dt_bias")) else dtype
        output = np.empty(raw.shape, dtype=target_dtype)
        flat, destination = raw.reshape(-1), output.reshape(-1)
        for offset in range(0, flat.size, 1 << 20):
            block = flat[offset:offset + (1 << 20)]
            value = (block.astype(np.uint32) << 16).view(np.float32) if spec["dtype"] == "BF16" else block
            destination[offset:offset + len(block)] = value + np.float32(1) if is_norm else value
        return output


def tokenizer(directory):
    from transformers import AutoTokenizer
    return AutoTokenizer.from_pretrained(str(directory), local_files_only=True, trust_remote_code=False)
