"""GPT-2 on OpenCL, adapted from tinygrad examples/gpt2.py (MIT).

Upstream source: ccae837c70301e3dab3ba8ea4db454249ad8f7e8.
Decode uses symbolic positions and TinyJit so BEAM tuning is reused across tokens.
"""

import importlib.metadata
import json
import os
from pathlib import Path

import numpy as np

os.environ["DEV"] = "CL"

from tinygrad import Device, Tensor, TinyJit, Variable, dtypes
from tinygrad.helpers import Context, GlobalCounters
from tinygrad.nn import Embedding, LayerNorm, Linear
from tinygrad.nn.state import get_state_dict
from common import sha256


class Attention:
    def __init__(self, capacity):
        self.c_attn = Linear(768, 2304, bias=True)
        self.c_proj = Linear(768, 768, bias=True)
        self.capacity = capacity

    def __call__(self, x, start, mask):
        qkv = self.c_attn(x).reshape(1, x.shape[1], 3, 12, 64)
        q, k, v = (qkv[:, :, i] for i in range(3))
        if not hasattr(self, "cache_kv"):
            self.cache_kv = Tensor.zeros(2, 1, self.capacity, 12, 64,
                                         dtype=x.dtype, device="CL").contiguous().realize()
        self.cache_kv[:, :, start:start + x.shape[1]].assign(Tensor.stack(k, v)).realize()
        keys = self.cache_kv[0][:, :start + x.shape[1]].transpose(1, 2)
        values = self.cache_kv[1][:, :start + x.shape[1]].transpose(1, 2)
        attended = q.transpose(1, 2).scaled_dot_product_attention(keys, values, mask)
        return self.c_proj(attended.transpose(1, 2).reshape(1, x.shape[1], 768))


class MLP:
    def __init__(self):
        self.c_fc = Linear(768, 3072, bias=True)
        self.c_proj = Linear(3072, 768, bias=True)

    def __call__(self, x):
        return self.c_proj(self.c_fc(x).gelu())


class Block:
    def __init__(self, capacity):
        self.attn = Attention(capacity)
        self.mlp = MLP()
        self.ln_1 = LayerNorm(768, 1e-5)
        self.ln_2 = LayerNorm(768, 1e-5)

    def __call__(self, x, start, mask):
        x = x + self.attn(self.ln_1(x), start, mask)
        return (x + self.mlp(self.ln_2(x))).clone()


class Model:
    def __init__(self, capacity):
        self.capacity = capacity
        self.wte = Embedding(50257, 768)
        self.wpe = Embedding(1024, 768)
        self.h = [Block(capacity) for _ in range(12)]
        self.ln_f = LayerNorm(768, 1e-5)
        self.allpos = Tensor.arange(capacity).to("CL").reshape(1, -1).realize()
        self.decode = TinyJit(self.forward)

    def forward(self, tokens, start):
        if isinstance(tokens, Tensor):
            width = tokens.shape[1]
            embedded = self.wte(tokens)
        else:
            width = 1
            embedded = self.wte.weight.shrink(((tokens, tokens + 1), None)).reshape(1, 1, 768)
        positions = self.allpos.shrink((None, (start, start + width)))
        x = embedded + self.wpe(positions)
        mask = (Tensor.full((1, 1, width, start + width), float("-inf"),
                            dtype=x.dtype, device="CL").triu(start + 1) if width > 1 else None)
        for block in self.h:
            x = block(x, start, mask)
        logits = self.ln_f(x[:, -1, :]) @ self.wte.weight.T
        return logits.realize(), logits.argmax(-1).realize()


class Backend:
    name = "tinygrad OpenCL"

    def __init__(self, state, dtype="float32", capacity=1024, beam=0):
        distribution = importlib.metadata.distribution("tinygrad")
        origin = json.loads(distribution.read_text("direct_url.json") or "{}")
        if "ccae837c70301e3dab3ba8ea4db454249ad8f7e8" not in origin.get("url", ""):
            raise RuntimeError("tinygrad differs from the pinned source; reinstall requirements.txt")
        self.device = Device["CL"]
        if "Apple M1" not in self.device.device_name:
            raise RuntimeError(f"requires the M1 GPU, got {self.device.device_name}")
        self.capacity, self.beam = capacity, beam
        dt = dtypes.float16 if dtype == "float16" else dtypes.float32
        with Context(BEAM=0):
            self.model = Model(capacity)
            parameters = get_state_dict(self.model)
            for key, value in state.items():
                if key.endswith(("attn.c_attn.weight", "attn.c_proj.weight", "mlp.c_fc.weight", "mlp.c_proj.weight")):
                    value = value.T
                value = np.ascontiguousarray(value, dtype=dtype)
                tensor = Tensor(value, dtype=dt, device="CL").realize()
                if tensor.shape != parameters[key].shape:
                    raise ValueError(f"parameter shape mismatch: {key}")
                parameters[key].replace(tensor)
                self.device.synchronize()  # release staging copies after each parameter
        self.last_logits = None
        self.position = 0
        self.prefill = {}
        source_dir = Path(__import__("tinygrad").__file__).parent
        self.information = dict(backend=self.name, device=self.device.device_name,
                                driver=self.device.driver_version, dtype=dtype, beam=beam,
                                beam_estimate=int(os.environ.get("BEAM_ESTIMATE", "1")),
                                prefill_jit=True,
                                tinygrad_version=importlib.metadata.version("tinygrad"),
                                tinygrad_commit="ccae837c70301e3dab3ba8ea4db454249ad8f7e8",
                                runtime_source_sha256={n: sha256(source_dir / n) for n in
                                    ("tensor.py", "runtime/ops_cl.py", "engine/realize.py", "codegen/opt/search.py")},
                                parameter_devices=sorted({parameters[k].device for k in state}))
        if self.information["parameter_devices"] != ["CL"]:
            raise RuntimeError("all parameters must reside on OpenCL")

    def reset(self):
        # Prefix writes replace old cache entries; only the written prefix is read.
        self.position = 0

    def predict(self, tokens):
        width = len(tokens)
        if not width or self.position + width > self.capacity:
            raise ValueError("invalid prompt or exhausted context")
        with Context(BEAM=self.beam):
            if width == 1 and self.position:
                token = Variable("token", 0, 50256).bind(tokens[0])
                position = Variable("start", 1, self.capacity - 1).bind(self.position)
                logits, selected = self.model.decode(token, position)
            else:
                inputs = Tensor([tokens], dtype=dtypes.int32, device="CL")
                key = (width, self.position)
                if key not in self.prefill:
                    self.prefill[key] = TinyJit(self.model.forward)
                logits, selected = self.prefill[key](inputs, self.position)
            chosen = int(selected.item())  # blocking read; includes completed GPU work
        if logits.device != "CL" or selected.device != "CL":
            raise RuntimeError("inference outputs must be evaluated on OpenCL")
        self.last_logits = logits
        self.position += width
        return chosen

    def logits(self):
        return self.last_logits.numpy().reshape(-1)

    def synchronize(self):
        self.device.synchronize()

    def counters(self):
        return dict(kernels=GlobalCounters.kernel_count, allocated_bytes=GlobalCounters.mem_used)
