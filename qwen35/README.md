# Qwen3.5-0.8B on Asahi

Text generation from the official [Qwen/Qwen3.5-0.8B checkpoint](https://huggingface.co/Qwen/Qwen3.5-0.8B),
using the Apple M1 GPU through omarchy-mlx Vulkan or tinygrad OpenCL.
The runner includes all 24 text decoder layers: 18 recurrent DeltaNet layers
and six layers with full attention. Vision inputs are not supported.

This is a minimal inference example for one pinned checkpoint and one prompt.
The `verify` and `benchmark` commands are optional developer checks; the
generation example runs directly through the existing MLX or tinygrad backend.
Read [qwen35.py](qwen35.py) for the generation loop,
[checkpoint.py](checkpoint.py) for model loading, and the two `*_backend.py`
files for GPU execution. CPU references and measurement workers live in
`tools/`; the launcher dispatches their optional commands separately.

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

## Independent numerical verification

```bash
qwen35/first-run.sh verify --backend mlx --context 64 --steps 4
qwen35/first-run.sh verify --backend tinygrad --beam 0 --context 64 --steps 4
qwen35/first-run.sh verify --backend mlx --dtype float32 --context 64 --steps 4
```

[reference.py](tools/reference.py) implements all 24 text layers independently in
NumPy, using FP64 mathematical operations on the original BF16 checkpoint.
It decodes parameters without either GPU weight loader and processes the
vocabulary projection in blocks to avoid keeping an FP64 model copy in memory.
The reference follows the [official Transformers architecture](https://github.com/huggingface/transformers/blob/v5.18.0/src/transformers/models/qwen3_5/modeling_qwen3_5.py),
including L2-normalized DeltaNet queries and keys, causal convolution, recurrent
state, gated full attention and partial RoPE. It shares checkpoint identity and
tokenization with generation; it does not use MLX, tinygrad or PyTorch to compute
reference logits.

`verify` first computes a CPU greedy history, then checks the GPU against that
same history. It checks whole-prompt and split-prompt processing, resets the
caches between these phases, and checks subsequent cached decode predictions.
Every one of the 248,320 logits per prediction must be finite and satisfy
`abs(gpu - reference) <= 0.05 + 0.003 * abs(reference)`. The GPU argmax must
also equal the CPU argmax. These limits are fixed before dispatch and include
FP16 activation rounding; this is not a bit-exact GPU emulator.

Receipts include per-vector errors, the acceptance contract, CPU token history,
checkpoint/source hashes, loaded driver hashes and runtime information. They
default to `results/verify-BACKEND-DTYPE.json`; `--output` selects another file.
`--logits-output /tmp/qwen-verify.npz` saves `reference_logits` and `gpu_logits`
for inspection. This command makes no performance claim.

This AGXForge-inspired independent check exposed a shared normalization error:
both GPU paths added `1e-6` to the mean of 128 squared coordinates, whereas
Transformers adds it to their sum. The old formula effectively used a sum
epsilon of `128e-6`. Both paths now use the sum convention and retain FP32
normalized queries and keys through recurrence. The fixed verification keeps
the original acceptance bounds. Earlier generation/comparison receipts below
describe the implementation before this correction.

Recorded on 2026-10-07 on the M1 G13G B1, kernel `7.1.13+`, Mesa 26.2.3,
using `What is 2 + 2?`, 20 prompt tokens, four predictions and context capacity
64. Each row checks eight complete vocabulary vectors across the two prompt
processing phases. All four rows pass the same fixed bounds and CPU argmax
checks, covering 7,946,240 vocabulary values in total.

| Backend | Precision | Maximum absolute logit error | Receipt |
| --- | --- | ---: | --- |
| MLX Vulkan | FP16 | 0.0289743 | [PASS](results/verify-mlx-float16.json) |
| tinygrad OpenCL | FP16 | 0.0283710 | [PASS](results/verify-tinygrad-float16.json) |
| MLX Vulkan | FP32 | 0.00004316 | [PASS](results/verify-mlx-float32.json) |
| tinygrad OpenCL | FP32 | 0.00003890 | [PASS](results/verify-tinygrad-float32.json) |

The retained [FP16](results/verify-mlx-float16-before-normalization.json) and
[FP32](results/verify-mlx-float32-before-normalization.json) controls from before
the correction fail those bounds despite identical top-token choices. The FP32
maximum error falls from 0.0634902 to 0.00004316 with the correction. These are
checks of this prompt and history, not a guarantee for all inputs or contexts.

CPU-only controls cover the delta update with unequal key/value dimensions,
state carry across chunks, original BF16 decoding, and rejection of incorrect
tokens, out-of-bound logits, nonfinite values and incomplete vectors:

```bash
gpt2/.venv/bin/python -m unittest discover -s qwen35/tests -v
```

## Warmed benchmark

```bash
qwen35/first-run.sh benchmark --backend all --context 64 --steps 8 --trials 3
```

[benchmark.py](tools/benchmark.py) computes one independent CPU history and uses
it for both GPU paths. Each trial starts a fresh worker, checks every logit
against that reference, runs two complete untimed warmup passes, and then
times prefill and cached decode separately. Backend order rotates between
rounds. `--steps 8` means eight decode predictions **after** prefill, for nine
predictions per pass; `verify --steps` counts total predictions instead.
Benchmark passes continue for the requested number of steps, including past
EOS, to keep the measured workload equal.

Workers use the M1 performance CPU cores and wait for the shared GPU locks
with a bounded timeout. Timing includes completed GPU prediction, recurrent
and KV updates, finite-logit checks, argmax and the one-token read. It excludes
loading, compilation, JIT capture, tuning, reset fills, full-logit copies,
tokenization and printing. The receipt retains raw timings, numerical checks,
source and driver hashes, CPU affinity, memory and available temperatures.
GPU clocks are not fixed. tinygrad's dispatch counts cover the timed prefill
and decode together; MLX has no dispatch counter through this interface.

Use `--backend tinygrad` or `--backend mlx` for one backend, `--dtype float32`
for FP32, and `--output FILE` to select a receipt. The default receipt is
`results/benchmark-DTYPE.json`. `--warmups` must be at least two so tinygrad's
prefill JIT has completed its initial execution and capture before timing.

Recorded on 2026-10-07 on this M1 G13G B1, kernel `7.1.13+`, Mesa 26.2.3,
FP16, batch size one, BEAM=0, context capacity 64 and the 20-token prompt
`What is 2 + 2?`. These are medians of three fresh trials per backend:

| Backend | Prefill ms | Decode tokens/s | Trial decode range |
| --- | ---: | ---: | ---: |
| MLX Vulkan | 641.36 | 5.00 | 4.98–5.01 |
| tinygrad OpenCL | 591.45 | 6.99 | 6.93–7.05 |

The [saved receipt](results/benchmark-float16.json) passes all 54 complete
vocabulary comparisons, covering 13,409,280 values, and all timed token
choices match the CPU history. tinygrad's median decode throughput is about
40% higher in this short warmed workload. Each tinygrad trial records 6,134
timed dispatches. These measurements describe this example's warmed execution;
they do not measure an implementation speedup against the historical first-use
runs below or establish performance for longer contexts.

## Implementation and timing

- The checkpoint is BF16; this runner converts projection and embedding
  matrices to FP16 by default. `--dtype float32` uses more memory.
- HF zero-centered RMSNorm weights are shifted by one in FP32. Normalization
  reductions and DeltaNet recurrent state use FP32; activations use the
  requested dtype.
- DeltaNet query/key L2 normalization uses `sum(x*x) + 1e-6` in FP32,
  with the query additionally scaled by `1 / sqrt(128)`.
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
capture and should not be compared with the warmed tables here or in GPT-2.
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
This historical receipt is cross-backend agreement; the independent CPU
verification command above checks the corrected implementation.
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
