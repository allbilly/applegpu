"""Independent NumPy FP64 mathematical reference for the pinned text decoder.

Reads original checkpoint values, without the GPU weight loader or either GPU
backend. Matrix parameters are decoded on demand; the vocabulary projection is
blocked so a complete FP64 copy of the model never needs to fit in memory.
The recurrence uses [head, key, value] state, as in Transformers, independently
of the GPU runners' [head, value, key] layout. This is a validation instrument,
not a production inference backend or an emulator of GPU rounding.

Architecture reference:
https://github.com/huggingface/transformers/blob/v5.18.0/src/transformers/models/qwen3_5/modeling_qwen3_5.py
"""

import json
from pathlib import Path
import sys
import struct

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from checkpoint import WEIGHTS


def sigmoid(x):
    return np.exp(-np.logaddexp(0, -x))


def rms(x, weight=None, eps=1e-6):
    out = x / np.sqrt(np.mean(x * x, axis=-1, keepdims=True) + eps)
    return out if weight is None else out * weight


def recurrent(q, k, v, decay, beta, state):
    """Sequential delta rule with an independently chosen state orientation."""
    outputs = []
    for i in range(len(q)):
        state = state * decay[i, :, None, None]
        retrieved = np.einsum("hkv,hk->hv", state, k[i])
        delta = beta[i, :, None] * (v[i] - retrieved)
        state = state + k[i, :, :, None] * delta[:, None, :]
        outputs.append(np.einsum("hkv,hk->hv", state, q[i]))
    return np.stack(outputs), state


class OriginalWeights:
    def __init__(self, directory):
        path = Path(directory) / WEIGHTS
        with path.open("rb") as stream:
            header_size = struct.unpack("<Q", stream.read(8))[0]
            if not 0 < header_size <= 16 << 20:
                raise ValueError("invalid safetensors header size")
            header = json.loads(stream.read(header_size))
        self.offset = 8 + header_size
        self.storage = np.memmap(path, mode="r", dtype=np.uint8)
        prefix = "model.language_model."
        self.entries = {name[len(prefix):]: spec for name, spec in header.items()
                        if name.startswith(prefix)}
        if len(self.entries) != 320 or self.entries["embed_tokens.weight"]["shape"] != [248320, 1024]:
            raise ValueError("reference requires the pinned Qwen3.5-0.8B text parameters")

    def raw(self, key):
        spec = self.entries[key]
        types = {"BF16": "<u2", "F16": "<f2", "F32": "<f4"}
        if spec["dtype"] not in types:
            raise ValueError(f"unsupported reference tensor dtype: {key}")
        dtype = np.dtype(types[spec["dtype"]])
        start, end = spec["data_offsets"]
        if start < 0 or end - start != int(np.prod(spec["shape"])) * dtype.itemsize or self.offset + end > self.storage.size:
            raise ValueError(f"invalid reference tensor span: {key}")
        return self.storage[self.offset + start:self.offset + end].view(dtype).reshape(spec["shape"])

    def decode(self, key, raw):
        if self.entries[key]["dtype"] == "BF16":
            raw = (raw.astype(np.uint32) << 16).view(np.float32)
        return raw.astype(np.float64)

    def tensor(self, key):
        return self.decode(key, self.raw(key))


class Reference:
    def __init__(self, directory, capacity=4096):
        config = json.loads((Path(directory) / "config.json").read_text())["text_config"]
        expected = dict(hidden_size=1024, intermediate_size=3584, num_hidden_layers=24,
                        num_attention_heads=8, num_key_value_heads=2, head_dim=256,
                        linear_num_key_heads=16, linear_num_value_heads=16,
                        linear_key_head_dim=128, linear_value_head_dim=128,
                        linear_conv_kernel_dim=4, vocab_size=248320,
                        rms_norm_eps=1e-6, tie_word_embeddings=True)
        if any(config.get(k) != v for k, v in expected.items()) or config["layer_types"] != [
                "full_attention" if i % 4 == 3 else "linear_attention" for i in range(24)]:
            raise ValueError("unsupported CPU reference architecture")
        rope = config["rope_parameters"]
        if rope["rope_theta"] != 1e7 or rope["partial_rotary_factor"] != 0.25 or rope["rope_type"] != "default":
            raise ValueError("unsupported CPU reference RoPE")
        self.weights = OriginalWeights(directory)
        self.capacity = capacity
        self.reset()

    def reset(self):
        self.position = 0
        self.convolution = {i: np.zeros((3, 6144), np.float64) for i in range(24) if i % 4 != 3}
        self.states = {i: np.zeros((16, 128, 128), np.float64) for i in self.convolution}
        self.keys, self.values = {}, {}

    def linear(self, x, key):
        return x @ self.weights.tensor(key).T

    def norm(self, x, key, zero_centered=True):
        weight = self.weights.tensor(key)
        return rms(x, weight + 1 if zero_centered else weight)

    @staticmethod
    def rope(x, positions):
        angle = positions[:, None, None] * (1e7 ** (-np.arange(32, dtype=np.float64) / 32))
        cosine, sine = np.cos(angle), np.sin(angle)
        left, right = x[..., :32], x[..., 32:64]
        return np.concatenate((left * cosine - right * sine, right * cosine + left * sine, x[..., 64:]), axis=-1)

    def attention(self, x, index):
        p = f"layers.{index}.self_attn."
        count = len(x)
        query_gate = self.linear(x, p + "q_proj.weight").reshape(count, 8, 512)
        query, gate = np.split(query_gate, 2, axis=-1)
        query = self.norm(query, p + "q_norm.weight")
        key = self.norm(self.linear(x, p + "k_proj.weight").reshape(count, 2, 256), p + "k_norm.weight")
        value = self.linear(x, p + "v_proj.weight").reshape(count, 2, 256)
        positions = np.arange(self.position, self.position + count)
        query, key = self.rope(query, positions), self.rope(key, positions)
        if index in self.keys:
            key = np.concatenate((self.keys[index], key))
            value = np.concatenate((self.values[index], value))
        self.keys[index], self.values[index] = key, value
        head_map = np.arange(8) // 4
        scores = np.einsum("thd,shd->hts", query, key[:, head_map]) / np.sqrt(256)
        valid = np.arange(len(key))[None, :] <= positions[:, None]
        scores = np.where(valid[None], scores, -np.inf)
        probability = np.exp(scores - scores.max(axis=-1, keepdims=True))
        probability /= probability.sum(axis=-1, keepdims=True)
        attended = np.einsum("hts,shd->thd", probability, value[:, head_map])
        return self.linear((attended * sigmoid(gate)).reshape(count, 2048), p + "o_proj.weight")

    def delta(self, x, index):
        p = f"layers.{index}.linear_attn."
        count = len(x)
        projected = self.linear(x, p + "in_proj_qkv.weight")
        history = np.concatenate((self.convolution[index], projected))
        kernel = self.weights.tensor(p + "conv1d.weight")[:, 0, :]
        windows = np.stack([history[i:i + count] for i in range(4)], axis=-1)
        convolved = np.einsum("tck,ck->tc", windows, kernel)
        convolved *= sigmoid(convolved)
        self.convolution[index] = history[-3:].copy()
        q, k, v = (a.reshape(count, 16, 128) for a in np.split(convolved, 3, axis=-1))
        # Transformers/FLA L2 normalization: epsilon is added to the sum.
        q = q / np.sqrt(np.sum(q * q, axis=-1, keepdims=True) + 1e-6) / np.sqrt(128)
        k = k / np.sqrt(np.sum(k * k, axis=-1, keepdims=True) + 1e-6)
        beta = sigmoid(self.linear(x, p + "in_proj_b.weight"))
        a = self.linear(x, p + "in_proj_a.weight") + self.weights.tensor(p + "dt_bias")
        decay = np.exp(-np.exp(self.weights.tensor(p + "A_log")) * np.logaddexp(0, a))
        out, self.states[index] = recurrent(q, k, v, decay, beta, self.states[index])
        gate = self.linear(x, p + "in_proj_z.weight").reshape(count, 16, 128)
        out = self.norm(out, p + "norm.weight", zero_centered=False) * gate * sigmoid(gate)
        return self.linear(out.reshape(count, 2048), p + "out_proj.weight")

    def predict(self, tokens):
        if not tokens or any(not isinstance(t, (int, np.integer)) or not 0 <= t < 248320 for t in tokens):
            raise ValueError("invalid CPU reference token IDs")
        if self.position + len(tokens) > self.capacity:
            raise ValueError("exhausted CPU reference context")
        embed_key = "embed_tokens.weight"
        embedding = self.weights.raw(embed_key)
        x = self.weights.decode(embed_key, embedding[tokens])
        for i in range(24):
            p = f"layers.{i}."
            normalized = self.norm(x, p + "input_layernorm.weight")
            x = x + (self.attention(normalized, i) if i % 4 == 3 else self.delta(normalized, i))
            normalized = self.norm(x, p + "post_attention_layernorm.weight")
            gate = self.linear(normalized, p + "mlp.gate_proj.weight")
            up = self.linear(normalized, p + "mlp.up_proj.weight")
            x = x + self.linear(gate * sigmoid(gate) * up, p + "mlp.down_proj.weight")
        last = self.norm(x[-1], "norm.weight")
        logits = np.empty(248320, np.float64)
        for start in range(0, len(logits), 4096):
            block = self.weights.decode(embed_key, embedding[start:start + 4096])
            logits[start:start + len(block)] = block @ last
        if not np.isfinite(logits).all():
            raise RuntimeError("CPU reference produced nonfinite logits")
        self.position += len(tokens)
        return logits
