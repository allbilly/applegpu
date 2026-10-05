"""Qwen3.5-0.8B text decoder on OpenCL with FP32 DeltaNet state."""

# Architecture adapted from MLX-LM's qwen3_5.py and qwen3_next.py.
# Copyright © 2025-2026 Apple Inc. See LICENSE-mlx-lm.

import importlib.metadata
import json
import math
import os
from types import SimpleNamespace

from checkpoint import Weights

os.environ["DEV"] = "CL"
from tinygrad import Device, Tensor, TinyJit, Variable, dtypes
from tinygrad.helpers import Context, GlobalCounters
from tinygrad.nn import Embedding, Linear
from tinygrad.nn.state import get_state_dict


def checked_argmax(logits):
    return logits.isfinite().all().where(logits.argmax(-1).cast(dtypes.int32), -1).realize()


class RMSNorm:
    def __init__(self, width):
        self.weight = Tensor.ones(width, dtype=dtypes.float32, device="CL")

    def __call__(self, x):
        value = x.cast(dtypes.float32)
        return (value * (value.square().mean(-1, keepdim=True) + 1e-6).rsqrt() * self.weight).cast(x.dtype)


class MLP:
    def __init__(self):
        self.gate_proj = Linear(1024, 3584, bias=False)
        self.up_proj = Linear(1024, 3584, bias=False)
        self.down_proj = Linear(3584, 1024, bias=False)

    def __call__(self, x):
        return self.down_proj(self.gate_proj(x).silu() * self.up_proj(x))


class Attention:
    def __init__(self, capacity, dtype):
        self.q_proj = Linear(1024, 4096, bias=False)
        self.k_proj = Linear(1024, 512, bias=False)
        self.v_proj = Linear(1024, 512, bias=False)
        self.o_proj = Linear(2048, 1024, bias=False)
        self.q_norm, self.k_norm = RMSNorm(256), RMSNorm(256)
        self.kv = Tensor.zeros(2, 1, capacity, 2, 256, dtype=dtype, device="CL").contiguous().realize()

    @staticmethod
    def rope(x, cosine, sine):
        left, right = x[..., :32].cast(dtypes.float32), x[..., 32:64].cast(dtypes.float32)
        return Tensor.cat((left * cosine - right * sine).cast(x.dtype),
                          (right * cosine + left * sine).cast(x.dtype), x[..., 64:], dim=-1)

    def __call__(self, x, start, cosine, sine):
        width = x.shape[1]
        q, gate = self.q_proj(x).reshape(1, width, 8, 512).split(256, dim=-1)
        q = self.q_norm(q)
        k = self.k_norm(self.k_proj(x).reshape(1, width, 2, 256))
        v = self.v_proj(x).reshape(1, width, 2, 256)
        q, k = self.rope(q, cosine, sine), self.rope(k, cosine, sine)
        self.kv[:, :, start:start + width].assign(Tensor.stack(k, v)).realize()
        end = start + width
        keys = self.kv[0][:, :end].transpose(1, 2).reshape(1, 2, 1, end, 256).expand(1, 2, 4, end, 256).reshape(1, 8, end, 256)
        values = self.kv[1][:, :end].transpose(1, 2).reshape(1, 2, 1, end, 256).expand(1, 2, 4, end, 256).reshape(1, 8, end, 256)
        queries = q.transpose(1, 2).cast(dtypes.float32)
        mask = (Tensor.full((1, 1, width, end), float("-inf"), device="CL").triu(start + 1) if width > 1 else None)
        out = queries.scaled_dot_product_attention(keys.cast(dtypes.float32), values.cast(dtypes.float32), mask)
        out = out.transpose(1, 2).reshape(1, width, 2048).cast(x.dtype)
        return self.o_proj(out * gate.reshape(1, width, 2048).sigmoid())


class DeltaNet:
    def __init__(self, dtype):
        self.in_proj_qkv = Linear(1024, 6144, bias=False)
        self.in_proj_z = Linear(1024, 2048, bias=False)
        self.in_proj_b = Linear(1024, 16, bias=False)
        self.in_proj_a = Linear(1024, 16, bias=False)
        self.out_proj = Linear(2048, 1024, bias=False)
        self.conv1d = SimpleNamespace(weight=Tensor.zeros(6144, 1, 4, dtype=dtype, device="CL"))
        self.A_log = Tensor.zeros(16, dtype=dtypes.float32, device="CL")
        self.dt_bias = Tensor.zeros(16, dtype=dtypes.float32, device="CL")
        self.norm = RMSNorm(128)
        self.conv_state = Tensor.zeros(1, 3, 6144, dtype=dtype, device="CL").contiguous().realize()
        self.state = Tensor.zeros(1, 16, 128, 128, dtype=dtypes.float32, device="CL").contiguous().realize()

    def reset(self):
        self.conv_state.assign(Tensor.zeros(*self.conv_state.shape, dtype=self.conv_state.dtype, device="CL")).realize()
        self.state.assign(Tensor.zeros(*self.state.shape, dtype=dtypes.float32, device="CL")).realize()

    def __call__(self, x):
        width = x.shape[1]
        qkv = self.in_proj_qkv(x)
        conv_input = self.conv_state.cat(qkv, dim=1).contiguous().realize()
        window = Tensor.stack(*(conv_input[:, i:i + width] for i in range(4)), dim=2)
        weight = self.conv1d.weight.reshape(6144, 4).T.reshape(1, 1, 4, 6144)
        mixed = (window.cast(dtypes.float32) * weight.cast(dtypes.float32)).sum(2).cast(x.dtype).silu().realize()
        self.conv_state.assign(conv_input[:, -3:]).realize()
        q, k, v = (mixed[:, :, i * 2048:(i + 1) * 2048].reshape(1, width, 16, 128) for i in range(3))
        def normalized(t, scale):
            value = t.cast(dtypes.float32)
            return ((value * (value.square().mean(-1, keepdim=True) + 1e-6).rsqrt()).cast(t.dtype) * scale).realize()
        q, k = normalized(q, 1 / 128), normalized(k, 1 / math.sqrt(128))
        beta = self.in_proj_b(x).sigmoid().cast(dtypes.float32).realize()
        a = self.in_proj_a(x).cast(dtypes.float32) + self.dt_bias
        softplus = a.maximum(0) + ((-a.abs()).exp() + 1).log()
        decay = (-self.A_log.exp() * softplus).exp().realize()
        outputs = []
        for index in range(width):
            qi, ki, vi = (t[:, index].cast(dtypes.float32) for t in (q, k, v))
            old = self.state * decay[:, index, :, None, None]
            retrieved = (old * ki[..., None, :]).sum(-1)
            delta = (vi - retrieved) * beta[:, index, :, None]
            updated = old + delta[..., None] * ki[..., None, :]
            self.state.assign(updated).realize()
            outputs.append((self.state * qi[..., None, :]).sum(-1).cast(x.dtype).realize())
        out = Tensor.stack(*outputs, dim=1)
        z = self.in_proj_z(x).reshape(1, width, 16, 128)
        out = (self.norm(out).cast(dtypes.float32) * z.cast(dtypes.float32).silu()).cast(x.dtype)
        return self.out_proj(out.reshape(1, width, 2048))


class Block:
    def __init__(self, index, capacity, dtype):
        self.is_linear = index % 4 != 3
        if self.is_linear:
            self.linear_attn = DeltaNet(dtype)
        else:
            self.self_attn = Attention(capacity, dtype)
        self.input_layernorm, self.post_attention_layernorm = RMSNorm(1024), RMSNorm(1024)
        self.mlp = MLP()

    def __call__(self, x, start, cosine, sine):
        value = self.input_layernorm(x)
        mixed = self.linear_attn(value) if self.is_linear else self.self_attn(value, start, cosine, sine)
        x = x + mixed
        return (x + self.mlp(self.post_attention_layernorm(x))).clone()


class Model:
    def __init__(self, capacity, dtype):
        self.embed_tokens = Embedding(248320, 1024)
        self.layers = [Block(i, capacity, dtype) for i in range(24)]
        self.norm = RMSNorm(1024)
        positions = Tensor.arange(capacity).to("CL").cast(dtypes.float32).reshape(capacity, 1)
        inv_freq = (Tensor.arange(32).to("CL").cast(dtypes.float32) * (-math.log(1e7) / 32)).exp()
        # Rusticl's installed libclc cannot link its sin implementation.
        # Compute reusable RoPE tables on OpenCL using tinygrad's polynomial
        # lowering, which avoids that library call entirely.
        with Context(TRANSCENDENTAL=2):
            angles = positions * inv_freq.reshape(1, 32)
            self.cosine = Tensor.empty(capacity, 32, dtype=dtypes.float32, device="CL").realize()
            self.sine = Tensor.empty(capacity, 32, dtype=dtypes.float32, device="CL").realize()
            self.cosine.assign(angles.cos()).realize()
            self.sine.assign(angles.sin()).realize()
        self.decode = TinyJit(self.forward)

    def forward(self, tokens, start):
        if isinstance(tokens, Tensor):
            width, x = tokens.shape[1], self.embed_tokens(tokens)
        else:
            width = 1
            x = self.embed_tokens.weight.shrink(((tokens, tokens + 1), None)).reshape(1, 1, 1024)
        cosine = self.cosine.shrink(((start, start + width), None)).reshape(1, width, 1, 32)
        sine = self.sine.shrink(((start, start + width), None)).reshape(1, width, 1, 32)
        for layer in self.layers:
            x = layer(x, start, cosine, sine)
        logits = (self.norm(x[:, -1, :]) @ self.embed_tokens.weight.T).realize()
        return logits, checked_argmax(logits)


class Backend:
    name = "tinygrad OpenCL"

    def __init__(self, directory, dtype="float16", capacity=4096, beam=0):
        distribution = importlib.metadata.distribution("tinygrad")
        origin = json.loads(distribution.read_text("direct_url.json") or "{}")
        if "ccae837c70301e3dab3ba8ea4db454249ad8f7e8" not in origin.get("url", ""):
            raise RuntimeError("requires the pinned tinygrad source")
        self.device = Device["CL"]
        if "Apple M1" not in self.device.device_name:
            raise RuntimeError(f"requires the M1 OpenCL GPU: {self.device.device_name}")
        self.capacity, self.beam = capacity, beam
        with Context(BEAM=0):
            self.model = Model(capacity, getattr(dtypes, dtype))
            parameters = get_state_dict(self.model)
            reader = Weights(directory)
            for key in reader.entries:
                value = reader.tensor(key, dtype)
                if key not in parameters or parameters[key].shape != value.shape:
                    raise ValueError(f"parameter shape mismatch: {key}")
                tensor = Tensor(value, device="CL").realize()
                parameters[key].replace(tensor)
                self.device.synchronize()
            learned_devices = sorted({parameters[k].device for k in reader.entries})
            count = len(reader.entries)
        del reader, parameters, value, tensor
        if learned_devices != ["CL"]:
            raise RuntimeError("all learned parameters must reside on OpenCL")
        self.prefill = {}
        self.position, self.last_logits = 0, None
        self.information = dict(backend=self.name, device=self.device.device_name, driver=self.device.driver_version,
            dtype=dtype, beam=beam, beam_estimate=int(os.environ.get("BEAM_ESTIMATE", "1")),
            tinygrad_version=importlib.metadata.version("tinygrad"),
            tinygrad_commit="ccae837c70301e3dab3ba8ea4db454249ad8f7e8",
            parameter_devices=learned_devices, text_parameters=count, recurrent_layers=18, full_attention_layers=6,
            recurrence="OpenCL tensor operations; FP32 recurrent state", prefill_jit=True)

    def reset(self):
        with Context(BEAM=0):
            for layer in self.model.layers:
                if layer.is_linear:
                    layer.linear_attn.reset()
        self.position = 0

    def predict(self, tokens):
        if not tokens or self.position + len(tokens) > self.capacity:
            raise ValueError("empty input or exhausted context")
        with Context(BEAM=self.beam):
            if len(tokens) == 1 and self.position:
                token = Variable("token", 0, 248319).bind(tokens[0])
                position = Variable("start", 1, self.capacity - 1).bind(self.position)
                logits, selected = self.model.decode(token, position)
            else:
                key = (len(tokens), self.position)
                if key not in self.prefill:
                    self.prefill[key] = TinyJit(self.model.forward)
                logits, selected = self.prefill[key](Tensor([tokens], dtype=dtypes.int32, device="CL"), self.position)
            chosen = int(selected.item())
        if chosen < 0:
            raise RuntimeError("model produced nonfinite logits")
        if logits.device != "CL" or selected.device != "CL":
            raise RuntimeError("model outputs must be evaluated on OpenCL")
        self.last_logits = logits
        self.position += len(tokens)
        return chosen

    def logits(self):
        return self.last_logits.numpy().reshape(-1)

    def counters(self):
        return dict(kernels=GlobalCounters.kernel_count, allocated_bytes=GlobalCounters.mem_used)
