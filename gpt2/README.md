# GPT-2 on Asahi

Full GPT-2 124M inference on the Apple M1 GPU, with two backends:

- **tinygrad / OpenCL:** Mesa Rusticl, optional BEAM kernel tuning, and TinyJit for prefill and cached decode.
- **omarchy-mlx / Vulkan:** the upstream MLX-LM GPT-2 model on Mesa Honeykrisp.

Both use the original Hugging Face checkpoint already cached by `~/ane/gpt2`,
the GPT-2 BPE tokenizer, a KV cache, and greedy generation. The default precision
is FP32. Inference kernels compile on Linux from the framework graphs.

The example's generation loop is in [gpt2.py](gpt2.py), model loading and
tokenization in [common.py](common.py), and GPU execution in the two
`*_backend.py` files. Optional CPU verification and benchmark workers live
in `tools/`. The launcher keeps the same generation, `verify` and `compare`
commands; generation imports no CPU decoder or benchmark worker.

## Run

From `~/applegpu`:

```bash
gpt2/first-run.sh --backend tinygrad --prompt 'Hello world' --max-tokens 32
gpt2/first-run.sh --backend tinygrad --beam 2 --prompt 'Hello world' --max-tokens 32
gpt2/first-run.sh --backend mlx --prompt 'Hello world' --max-tokens 32
```

BEAM tunes GPU kernels; generation still selects the most likely next token.
The first tuned run can take substantially longer than a cached run.

The launcher installs pinned dependencies into `gpt2/.venv`. Weights, the MLX
wheel, extracted native library dependencies, and reference fixtures live under
`${XDG_CACHE_HOME:-~/.cache}/applegpu-gpt2`. Existing Hugging Face weights are
reused after checking their SHA256. Otherwise it downloads the pinned 548 MB
checkpoint. Use `--weights /path/to/model.safetensors` or `GPT2_WEIGHTS` to select
another copy of that checkpoint.

The MLX wheel is pinned to omarchy-mlx v0.7.27 and requires Linux aarch64 with
CPython 3.14. The launcher uses `/usr/bin/python3`; override it with
`GPT2_PYTHON=/path/to/python3.14`. On this Fedora installation, missing
BLAS/LAPACK/OpenBLAS and Fortran libraries are downloaded as RPMs and extracted
into the user cache. The runner uses the installed Asahi Vulkan ICD. The recorded
runs used stock Mesa 26.2.3.

To save generated text, token IDs, timings, and runtime provenance:

```bash
gpt2/first-run.sh --backend mlx --prompt 'Hello world' --max-tokens 32 \
  --output gpt2/results/my-generation.json
```

## Compare and verify

```bash
gpt2/first-run.sh compare --dtype float32 --beams 0 2 --steps 64 --trials 3
gpt2/first-run.sh verify --backend tinygrad --beam 2
gpt2/first-run.sh verify --backend mlx
```

Benchmark prefill latency and throughput separately from cached decode at
longer prompt lengths:

```bash
gpt2/first-run.sh compare --dtype float32 --beams 0 2 --lengths 32 128 256 \
  --steps 64 --trials 3 --output gpt2/results/prefill-decode-float32.json
```

Add `--resume` to `compare` after an interruption to reuse workers whose
inputs, runner code, kernel, and driver hashes still match. The comparator waits
for a busy shared GPU lock within its worker timeout. The initial
`compare-float32.json` resumed seven completed workers after a lock conflict;
the longer-prompt `prefill-decode-float32.json` ran all nine workers fresh.

`compare` builds an independent NumPy reference before loading a GPU model.
Each backend checks all 50,257 logits at 65 positions for each prompt length
(2, 32, and 64). Every greedy choice must match the reference, normalized logit
RMSE must be at most 0.01, and KL divergence must be at most 0.01. Timed runs
must also produce the same token IDs after JIT replay. FP16 is available through
`--dtype float16`, but the recorded comparison validates FP32.

There are three rounds, with backend order rotated between rounds. Each worker
warms the model, then times a prefill and 64 decode steps on identical input
tokens. Timings include framework work, KV updates, completed GPU execution,
GPU argmax, and a blocking one-token read. Loading, first compilation, BEAM
tuning, full-logit checks, and text printing are excluded. KV cache allocation
and graph lowering differ between frameworks. Generation timings printed by
the ordinary CLI include first-use compilation and are not warmed benchmarks.

Workers run sequentially, acquire `~/gpu.lock` and `/tmp/m1-gpu.lock`, and use
the M1 performance CPU cores. Saved reports include raw times, numerical
errors, memory and available SMC temperature readings, source and driver
hashes, checkpoint identity, and runtime versions. Results apply to this
machine and these pinned builds.

## Prefill and decode benchmark

Fresh run on 2026-10-05: M1 MacBook Air (G13G B1), stock Mesa 26.2.3,
FP32, batch 1, context capacity 1024. Each row is the median of three runs,
with 64 cached decode steps after the specified prompt. Backend order rotates
between rounds.

| Backend | Prompt tokens | Prefill ms | Prefill tokens/s | Decode tokens/s |
| --- | ---: | ---: | ---: | ---: |
| MLX Vulkan | 32 | 63.55 | 503.53 | 23.05 |
| MLX Vulkan | 128 | 175.95 | 727.46 | 22.85 |
| MLX Vulkan | 256 | 329.01 | 778.09 | 21.19 |
| tinygrad OpenCL, BEAM=0 | 32 | 47.09 | 679.50 | 24.21 |
| tinygrad OpenCL, BEAM=0 | 128 | 113.95 | 1123.31 | 22.58 |
| tinygrad OpenCL, BEAM=0 | 256 | 190.09 | 1346.70 | 22.62 |
| tinygrad OpenCL, BEAM=2 | 32 | 585.86 | 54.62 | 16.71 |
| tinygrad OpenCL, BEAM=2 | 128 | 1920.51 | 66.65 | 16.68 |
| tinygrad OpenCL, BEAM=2 | 256 | 2147.73 | 119.20 | 16.29 |

Prefill processes the entire prompt and returns its first next-token choice.
Its throughput counts input tokens (`1000 * prompt_tokens / prefill_ms`).
Decode measures the following 64 single-token steps with a KV cache; each
trial's throughput is `1000 * 64 / sum(step_ms)`. Both phases include completed
GPU execution and the selected-token read. Compilation and BEAM tuning are
excluded. The initial BEAM=2 validation/warmup took about 71 seconds at 128
tokens and 147 seconds at 256 tokens; those durations are separate from the
warmed prefill times above.

Untuned tinygrad was faster at longer prefills: about **1.54× at 128 tokens**
and **1.73× at 256 tokens** compared with MLX. Decode was close between these
two backends. BEAM=2 with the default `BEAM_ESTIMATE=1` regressed in both
phases on this build. Clocks were not fixed and background CPU activity was
present, so small decode differences should be interpreted with the recorded
trial variation.

All **1,755 full-logit checks** and **1,755 timed token checks** passed.
The same reference, checkpoint, runner sources, and driver hashes were verified
across the nine fresh workers. Raw per-trial timings, numerical errors, and
runtime provenance are in
[prefill-decode-float32.json](results/prefill-decode-float32.json); the final
audit is [prefill-decode-validation-float32.json](results/prefill-decode-validation-float32.json).

## Initial shorter-prompt results

M1 MacBook Air (G13G B1), Fedora Asahi, Mesa 26.2.3, FP32, batch 1,
2026-10-05. Median of three runs, with 64 decode steps per run:

| Backend | 2-token prompt | 32-token prompt | 64-token prompt |
| --- | ---: | ---: | ---: |
| MLX Vulkan | 23.84 tokens/s | 22.72 tokens/s | 22.66 tokens/s |
| tinygrad OpenCL, BEAM=0 | 22.12 tokens/s | 24.14 tokens/s | 22.60 tokens/s |
| tinygrad OpenCL, BEAM=2 | 17.32 tokens/s | 16.94 tokens/s | 16.99 tokens/s |

| Backend | Prefill: 2 tokens | Prefill: 32 tokens | Prefill: 64 tokens |
| --- | ---: | ---: | ---: |
| MLX Vulkan | 42.63 ms | 66.28 ms | 101.19 ms |
| tinygrad OpenCL, BEAM=0 | 63.49 ms | 71.37 ms | 77.99 ms |
| tinygrad OpenCL, BEAM=2 | 67.30 ms | 580.35 ms | 755.93 ms |

MLX and untuned tinygrad trade places across prompt lengths. BEAM=2 with the
default `BEAM_ESTIMATE=1` was slower in this comparison. Keep BEAM disabled
for ordinary generation with this build. Other search settings were not measured.

All 1,755 full-logit checks passed, as did the token checks in timed JIT replays.
MLX and both tinygrad modes generated identical 32-token continuations of `Hello world`.
See [compare-float32.json](results/compare-float32.json) for raw results and
[generate-mlx-float32.json](results/generate-mlx-float32.json) /
[generate-tinygrad-float32.json](results/generate-tinygrad-float32.json) for
generation receipts. [validation-float32.json](results/validation-float32.json)
records the final audit and dispatch trace hashes: 8,368 Vulkan compute
dispatches and 8,152 OpenCL kernel executions in each 32-token generation.

Clocks were not fixed and background builds were active. MLX's third run at
prompt lengths 32 and 64 dropped to 12.40/12.83 tokens/s; untuned tinygrad also
varied from 16.63 to 25.59 tokens/s across trials and prompts. The small median
differences between those two backends are not decisive. Rusticl emitted a
warning about unpatched libclc; the recorded numerical checks passed with the
installed libraries.

## Sources

- tinygrad model adaptation: commit `ccae837c70301e3dab3ba8ea4db454249ad8f7e8`, `examples/gpt2.py`; see [LICENSE-tinygrad](LICENSE-tinygrad).
- MLX-LM model: `mlx-lm==0.31.3`, `mlx_lm/models/gpt2.py`.
- Checkpoint: `openai-community/gpt2`, revision `607a30d783dfa663caf39e06633721c8d4cfcd7e`, SHA256 `248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707`.
- Tokenizer implementation copied from `~/ane/gpt2/bpe.py`; original GPT-2 assets: [LICENSE-openai-gpt2](LICENSE-openai-gpt2).
