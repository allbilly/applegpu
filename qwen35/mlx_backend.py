"""Qwen3.5 text decoder from MLX-LM on the actual Asahi Vulkan GPU."""

# DeltaNet forward adapted from MLX-LM's qwen3_5.py.
# Copyright © 2026 Apple Inc. See LICENSE-mlx-lm.

import importlib.metadata
import json
import os
from pathlib import Path
import subprocess

import numpy as np

from checkpoint import Weights, sha256

if not os.environ.get("VK_DRIVER_FILES") and not os.environ.get("VK_ICD_FILENAMES"):
    candidates = sorted(Path("/usr/share/vulkan/icd.d").glob("asahi_icd*.json"))
    if len(candidates) == 1:
        os.environ["VK_DRIVER_FILES"] = str(candidates[0])

import mlx.core as mx
import mlx.nn as nn
from mlx.utils import tree_flatten
from mlx_lm.models import qwen3_5


def vulkan_delta(q, k, v, a, b, A_log, dt_bias, state=None, mask=None, use_kernel=True):
    # This wheel implements the recurrence as a Vulkan primitive. MLX-LM's
    # older helper otherwise chooses its composed path when Metal is absent.
    return mx.fast.gated_delta_update_raw(q, k, v, a, b, A_log, dt_bias, state, mask)


class PreciseRMSNorm(nn.RMSNorm):
    def __call__(self, x):
        # Preserve HF's zero-centered gamma conversion in FP32 without
        # promoting the following projection and residual stream to FP32.
        return mx.fast.rms_norm(x.astype(mx.float32), self.weight, self.eps).astype(x.dtype)


class PreciseDeltaNet(qwen3_5.GatedDeltaNet):
    """Pinned single-stream forward with Transformers' L2 epsilon convention."""

    def __call__(self, inputs, mask=None, cache=None):
        batch, count, _ = inputs.shape
        if batch != 1 or mask is not None or (cache is not None and cache.lengths is not None):
            raise ValueError("this runner requires unmasked, single-stream text input")
        qkv = self.in_proj_qkv(inputs)
        z = self.in_proj_z(inputs).reshape(batch, count, self.num_v_heads, self.head_v_dim)
        a, b = self.in_proj_a(inputs), self.in_proj_b(inputs)
        old_conv = cache[0] if cache is not None and cache[0] is not None else mx.zeros(
            (batch, self.conv_kernel_size - 1, self.conv_dim), dtype=inputs.dtype)
        conv_input = mx.concatenate((old_conv, qkv), axis=1)
        if cache is not None:
            cache[0] = mx.contiguous(conv_input[:, -(self.conv_kernel_size - 1):])
        mixed = nn.silu(self.conv1d(conv_input))
        q, k, v = [value.reshape(batch, count, heads, width)
                   for value, heads, width in zip(
                       mx.split(mixed, [self.key_dim, 2 * self.key_dim], axis=-1),
                       (self.num_k_heads, self.num_k_heads, self.num_v_heads),
                       (self.head_k_dim, self.head_k_dim, self.head_v_dim))]
        inv_scale = self.head_k_dim ** -0.5
        # RMS divides by the dimension. Dividing epsilon by the dimension
        # makes these expressions match L2's sum(x*x) + 1e-6 denominator.
        epsilon = 1e-6 / self.head_k_dim
        q = mx.fast.rms_norm(q.astype(mx.float32), None, epsilon) * (inv_scale ** 2)
        k = mx.fast.rms_norm(k.astype(mx.float32), None, epsilon) * inv_scale
        state = cache[1] if cache is not None else None
        out, state = vulkan_delta(q, k, v, a, b, self.A_log, self.dt_bias, state)
        if cache is not None:
            cache[1] = state
            cache.advance(count)
        out = self.norm(out.astype(inputs.dtype), z)
        return self.out_proj(out.reshape(batch, count, -1))


def checked_argmax(logits):
    return mx.where(mx.all(mx.isfinite(logits)), mx.argmax(logits, axis=-1).astype(mx.int32), -1)


class Backend:
    name = "MLX Vulkan"

    def __init__(self, directory, dtype="float16", capacity=4096, beam=0):
        if importlib.metadata.version("mlx-omarchy") != "0.32.4.dev202610041653+6edd258":
            raise RuntimeError("requires the pinned omarchy-mlx wheel")
        if os.environ.get("MLX_OMARCHY_CAPS_SIM"):
            raise RuntimeError("capability simulation is not hardware inference")
        mx.set_default_device(mx.gpu)
        package = Path(mx.__file__).resolve().parent
        reporter = package / "bin/mlx-omarchy-info"
        report = json.loads(subprocess.check_output([str(reporter), "--json"], text=True, timeout=30))
        if "Apple M1" not in report.get("device_name", ""):
            raise RuntimeError(f"requires the M1 Vulkan GPU: {report}")
        libraries = {Path(line.split()[-1]) for line in Path("/proc/self/maps").read_text().splitlines() if "libmlx.so" in line}
        hashes = {p.name: sha256(p) for p in libraries}
        if hashes.get("libmlx.so") != "1e82df97df9f3fd1cbc5830d8408317892522305c0e8d4ba772df8e42227600f":
            raise RuntimeError("MLX native library differs from the verified release wheel")
        config = json.loads((Path(directory) / "config.json").read_text())
        qwen3_5.gated_delta_update = vulkan_delta
        qwen3_5.GatedDeltaNet = PreciseDeltaNet
        self.model = qwen3_5.Model(qwen3_5.ModelArgs.from_dict(config))
        text = self.model.language_model.model
        text.norm = PreciseRMSNorm(1024, eps=1e-6)
        for layer in text.layers:
            layer.input_layernorm = PreciseRMSNorm(1024, eps=1e-6)
            layer.post_attention_layernorm = PreciseRMSNorm(1024, eps=1e-6)
            if not layer.is_linear:
                layer.self_attn.q_norm = PreciseRMSNorm(256, eps=1e-6)
                layer.self_attn.k_norm = PreciseRMSNorm(256, eps=1e-6)
        self.model.eval()
        reader = Weights(directory)
        expected = dict(tree_flatten(self.model.parameters()))
        loaded = set()
        for key in reader.entries:
            target = "language_model.model." + key
            if target not in expected:
                raise ValueError(f"unexpected text parameter: {key}")
            value = reader.tensor(key, dtype)
            if key.endswith("conv1d.weight"):
                value = np.ascontiguousarray(value.swapaxes(1, 2))
            tensor = mx.array(value)
            if tensor.shape != expected[target].shape:
                raise ValueError(f"parameter shape mismatch: {key}")
            self.model.load_weights([(target, tensor)], strict=False)
            mx.eval(tensor)
            loaded.add(target)
        if loaded != set(expected):
            raise ValueError(f"missing text weights: {set(expected) - loaded}")
        del reader, expected, value, tensor
        self.capacity, self.dtype = capacity, dtype
        self.last_logits = None
        self.reset()
        self.information = dict(backend=self.name, device=report["device_name"], dtype=dtype,
            mlx_omarchy_version=importlib.metadata.version("mlx-omarchy"),
            mlx_lm_version=importlib.metadata.version("mlx-lm"), libmlx_sha256=hashes,
            text_parameters=len(loaded), recurrent_layers=18, full_attention_layers=6,
            recurrence="Vulkan gated_delta_update_raw; composed GPU recurrence for FP16/FP32; FP32 state",
            delta_qk_normalization="FP32 L2 sum + 1e-6; query scaled by head_dim**-0.5",
            vulkan={k: v for k, v in report.items() if k not in ("ane", "coreml", "trace")},
            model_source_sha256=sha256(Path(qwen3_5.__file__)))

    def reset(self):
        self.cache = self.model.language_model.make_cache()
        self.position = 0

    def predict(self, tokens):
        if not tokens or self.position + len(tokens) > self.capacity:
            raise ValueError("empty input or exhausted context")
        hidden = self.model.language_model.model(mx.array([tokens], dtype=mx.int32), self.cache)
        logits = self.model.language_model.model.embed_tokens.as_linear(hidden[:, -1, :])
        chosen = checked_argmax(logits)
        buffers = [v for c in self.cache for _, v in tree_flatten(c.state) if isinstance(v, mx.array)]
        mx.eval(logits, chosen, *buffers)
        selected = int(chosen.item())
        if selected < 0:
            raise RuntimeError("model produced nonfinite logits")
        self.last_logits = logits
        self.position += len(tokens)
        return selected

    def logits(self):
        return np.asarray(self.last_logits).reshape(-1)

    def counters(self):
        return dict(active_memory_bytes=mx.get_active_memory(), peak_memory_bytes=mx.get_peak_memory())
