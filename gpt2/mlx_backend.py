"""Upstream MLX-LM GPT-2 using omarchy-mlx's Vulkan tensor backend."""

import importlib.metadata
import json
import os
from pathlib import Path
import subprocess

import numpy as np

from common import CONFIG, sha256

# Select the actual Apple ICD. A software Vulkan device must never pass as GPU inference.
if not os.environ.get("VK_DRIVER_FILES") and not os.environ.get("VK_ICD_FILENAMES"):
    candidates = sorted(Path("/usr/share/vulkan/icd.d").glob("asahi_icd*.json"))
    if len(candidates) == 1:
        os.environ["VK_DRIVER_FILES"] = str(candidates[0])

import mlx.core as mx
from mlx.utils import tree_flatten
from mlx_lm.models.cache import make_prompt_cache
from mlx_lm.models.gpt2 import Model, ModelArgs


class Backend:
    name = "MLX Vulkan"

    def __init__(self, state, dtype="float32", capacity=1024, beam=0):
        if importlib.metadata.version("mlx-omarchy") != "0.32.4.dev202610041653+6edd258":
            raise RuntimeError("MLX differs from the pinned Vulkan wheel; reinstall requirements-mlx.txt")
        if os.environ.get("MLX_OMARCHY_CAPS_SIM"):
            raise RuntimeError("capability simulation is not valid for hardware inference")
        mx.set_default_device(mx.gpu)
        package = Path(mx.__file__).resolve().parent
        reporter = package / "bin/mlx-omarchy-info"
        report = json.loads(subprocess.check_output([str(reporter), "--json"], text=True, timeout=30))
        device_name = report.get("device_name", report.get("name", ""))
        if "Apple M1" not in device_name:
            raise RuntimeError(f"requires the M1 Vulkan GPU, got {report}")
        self.model = Model(ModelArgs.from_dict(CONFIG))
        dt = getattr(mx, dtype)
        weights = {k: mx.array(v, dtype=dt) for k, v in state.items()}
        self.model.load_weights(list(self.model.sanitize(weights).items()), strict=True)
        self.model.eval()
        mx.eval(self.model.parameters())
        self.capacity, self.dtype = capacity, dtype
        self.reset()
        self.last_logits = None
        self.information = dict(backend=self.name, device=device_name,
                                dtype=dtype, beam=None,
                                mlx_omarchy_version=importlib.metadata.version("mlx-omarchy"),
                                mlx_lm_version=importlib.metadata.version("mlx-lm"),
                                vulkan={k: v for k, v in report.items() if k not in ("ane", "coreml", "trace")})
        libraries = {Path(line.split()[-1]) for line in Path("/proc/self/maps").read_text().splitlines()
                     if "libmlx.so" in line}
        self.information["libmlx_sha256"] = {p.name: sha256(p) for p in libraries}
        if self.information["libmlx_sha256"].get("libmlx.so") != "1e82df97df9f3fd1cbc5830d8408317892522305c0e8d4ba772df8e42227600f":
            raise RuntimeError("loaded MLX shared library differs from the verified release wheel")
        model_path = Path(__import__("mlx_lm.models.gpt2", fromlist=["__file__"]).__file__)
        self.information["gpt2_model_source_sha256"] = sha256(model_path)

    def reset(self):
        self.cache = make_prompt_cache(self.model)
        self.position = 0

    def predict(self, tokens):
        if not tokens or self.position + len(tokens) > self.capacity:
            raise ValueError("invalid prompt or exhausted context")
        hidden = self.model.model(mx.array([tokens], dtype=mx.int32), cache=self.cache)
        logits = self.model.model.wte.as_linear(hidden[:, -1, :])
        selected = mx.argmax(logits, axis=-1)
        buffers = [v for c in self.cache for _, v in tree_flatten(c.state) if isinstance(v, mx.array)]
        mx.eval(logits, selected, *buffers)
        chosen = int(selected.item())
        self.last_logits = logits
        self.position += len(tokens)
        return chosen

    def logits(self):
        return np.asarray(self.last_logits).reshape(-1)

    def synchronize(self):
        mx.synchronize()

    def counters(self):
        return dict(active_memory_bytes=mx.get_active_memory(), peak_memory_bytes=mx.get_peak_memory())
