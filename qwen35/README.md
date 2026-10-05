# Qwen3.5-0.8B on Asahi

Text generation from the official [Qwen/Qwen3.5-0.8B checkpoint](https://huggingface.co/Qwen/Qwen3.5-0.8B),
using the Apple M1 GPU through omarchy-mlx Vulkan or tinygrad OpenCL.
The runner includes all 24 text decoder layers: 18 recurrent DeltaNet layers
and six layers with full attention. Vision inputs are not supported.

## Run

From the repository root:

```bash
qwen35/first-run.sh --backend mlx --prompt 'What is 2 + 2?' --max-tokens 32
qwen35/first-run.sh --backend tinygrad --beam 0 --prompt 'What is 2 + 2?' --max-tokens 32
```

The launcher shares the pinned Python environment and native dependencies
with [GPT-2](../gpt2/README.md). The MLX wheel requires CPython 3.14 on Linux
aarch64. First use downloads approximately 1.75 GB of model weights plus
tokenizer assets to `~/.cache/applegpu-qwen35/model`. Every asset is checked
against its pinned SHA256 on each launch. No macOS export is required.

```bash
qwen35/first-run.sh setup
qwen35/first-run.sh --backend mlx --thinking --prompt 'Explain why the sky is blue.'
qwen35/first-run.sh --backend tinygrad --beam 2 --prompt 'Write a short Python function.'
qwen35/first-run.sh --backend mlx --raw --prompt 'The capital of France is'
qwen35/first-run.sh --backend mlx --output /tmp/qwen-generation.json
```

Chat mode uses the checkpoint's template with thinking disabled by default.
Generation is greedy and stops at EOS or the configured token limit. Use
`--system`, `--max-tokens`, and `--context` to control the request. The default
cache capacity is 4096 tokens. `--model DIR` selects a local copy of the exact
pinned checkpoint; arbitrary Qwen checkpoints are not accepted.

## Implementation and timing

- The checkpoint is BF16; this runner converts projection and embedding
  matrices to FP16 by default. `--dtype float32` uses more memory.
- HF zero-centered RMSNorm weights are shifted by one in FP32. Normalization
  reductions and DeltaNet recurrent state use FP32; activations use the
  requested dtype.
- MLX uses the MLX-LM text decoder, with explicit FP32 normalization and
  `gated_delta_update_raw`. This wheel's FP16/FP32 recurrence uses composed
  Vulkan operations; the native fused DeltaNet kernel requires BF16.
- tinygrad implements the text decoder with GPU convolution state, recurrent
  state and KV caches. All 320 learned tensors reside on OpenCL. Decode uses
  symbolic positions and TinyJit; `--beam` selects kernel tuning width.
  RoPE tables are computed once on OpenCL with tinygrad's polynomial
  transcendental lowering, avoiding an unresolved `sin` in this machine's
  installed Rusticl/libclc combination.
- Both backends project only the final hidden position into the vocabulary
  and select its next token on the GPU. Every prediction checks for nonfinite
  logits on the GPU and fails before returning a token if any are found.
  Tokenization, weight conversion and text streaming run on the CPU.

The JSON receipt records checkpoint and source hashes, runtime versions,
driver hashes, memory, prompt and generated IDs, prefill latency, and decode
samples. Git commit metadata is optional when running an extracted source
archive; source hashes are always recorded. GPU timing includes completed
state updates, the finite-logit check, and the one-token read.
It excludes checkpoint loading, tokenization, printing, and optional full
logit copies. These generation timings include first-use compilation/JIT
capture and should not be compared with GPT-2's warmed benchmark tables.
`--logits-output /tmp/qwen-logits.npz` saves full vocabulary vectors outside
the timers for numerical comparison.

## Recorded inference

On the base M1 MacBook Air with Mesa 26.2.3 and Fedora Asahi kernel
`7.1.13-402.asahi.fc44.aarch64+16k`, both backends generated the same 32 tokens
for `What is 2 + 2?`, starting with:

> The answer is **4**.

[The comparison receipt](results/comparison-float16.json) compares all
7,946,240 vocabulary logits across those 32 predictions. Every vector was
finite and every greedy next-token choice matched. The maximum absolute
logit difference was 0.044922; overall RMS difference was 0.005831.
This is cross-backend agreement, without an independent CPU/macOS reference.
An additional [chat run](results/generate-mlx-eos-float16.json) returned
`Paris` and stopped at EOS; a [raw continuation run](results/generate-tinygrad-raw-float16.json)
also completed on OpenCL.
The local traces contained 43,518 Vulkan dispatch lines and 18,619 OpenCL
kernel rows. tinygrad had zero CPU kernel rows; MLX uses the pinned omarchy
build with CPU primitive evaluation unavailable.

These are **traced first-use timings**, including compilation and JIT capture:

| Backend | Prompt tokens | Prefill ms | Decode tokens/s |
| --- | ---: | ---: | ---: |
| [MLX Vulkan](results/generate-mlx-float16.json) | 20 | 720.16 | 4.31 |
| [tinygrad OpenCL, BEAM=0](results/generate-tinygrad-float16.json) | 20 | 13678.70 | 1.22 |

Decode covers 31 completed predictions after prefill. Tracing adds overhead,
and these are not warmed performance claims. Qwen's BEAM=2 mode and FP32 mode
have no recorded generation run yet. The default remains FP16 with BEAM=0.

[Focused review checks](results/review-validation.json) cover finite/NaN/
infinity selection on both GPUs and Git provenance inside a checkout,
outside a checkout, and with Git unavailable.

## Pins and licenses

- Official checkpoint revision: `2fc06364715b967f1860aea9cf38778875588b17`.
- Model file SHA256: `04b1c301231dd422b8860db31311ab2721511346a32cb1e079c4c4e5f1fe4696`.
- Model license: Apache 2.0; the checkpoint downloader includes the upstream
  `LICENSE` in the external model cache.
- MLX-LM: `0.31.3`, MIT license, using
  [`qwen3_5.py`](https://github.com/ml-explore/mlx-lm/blob/v0.31.3/mlx_lm/models/qwen3_5.py)
  and its Qwen3-Next helpers; see [LICENSE-mlx-lm](LICENSE-mlx-lm).
- omarchy-mlx: `0.32.4.dev202610041653+6edd258`; dependencies are pinned in
  [requirements-mlx.txt](../gpt2/requirements-mlx.txt).
- tinygrad: `ccae837c70301e3dab3ba8ea4db454249ad8f7e8`, MIT license;
  see [LICENSE-tinygrad](../gpt2/LICENSE-tinygrad) and
  [requirements.txt](../gpt2/requirements.txt).

Model weights, downloaded libraries, and the Python environment stay outside
version control.
