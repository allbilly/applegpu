# AppleGPU

Apple GPU experiments with macOS IOKit replay and Asahi Linux DRM execution.
On Linux, start with the [Asahi examples and inference runners](#asahi-linux).

Inference stays at example scale: one pinned model, one prompt, and a short
greedy generation loop. Keep the loading, GPU execution and result checks
readable within each example. Setup, verification and timing commands are
optional tools for reproducing and checking the examples.
Each model's generation entry point, checkpoint loader and backends stay
together; its CPU references and benchmark workers live in `tools/`.

## macOS

```bash
uv venv --python '>=3.10'
uv run examples/add.py
uv run examples/mul.py
uv run examples/tri.py
```

The standalone examples emit an `allbilly/nvgpu`-style semantic trace
by default. Level 1 shows lifecycle stages, named IOGPU selectors, live return
fields, GPU-VA remaps, timings, and a summary. Level 2 also shows decoded input
fields, pointer patches, and bounded raw payloads.

```bash
AGX_TRACE=0 uv run examples/add.py  # concise status only
AGX_TRACE=2 uv run examples/add.py  # detailed trace
uv run examples/add.py -v           # same as --trace 2
```

The capture format records IOKit calls, CPU-visible resource/shared-memory
contents, Trap 0 callback descriptors, and the expected output bytes. The
generator compresses that memory image into each standalone script. At runtime
the script range-remaps live GPU VAs, restores the captured memory, submits the
work without Metal, waits for the CPU-visible output, and reports `PASS` only
when both the GPU result and every IOKit return value/size match.

To recapture and regenerate an example:

```bash
cd experimental
make capture standalone          # add
make capture-mul standalone-mul  # multiply
make capture-tri standalone-tri  # triangle
```

## Asahi Linux

Check this machine's native-example target without submitting GPU commands:

```bash
python3 experimental/check_asahi.py
python3 experimental/check_asahi.py --run --output /tmp/applegpu-asahi-check.json
python3 experimental/check_asahi.py --compare /tmp/applegpu-asahi-check.json
```

The checker uses only the Python standard library. `READY` means the Asahi
DRM parameter query succeeded and the GPU matches M1 G13G A0/B1 (T8103).
`--run` requires three agreeing GPU executions of each standalone example
by default, in separate processes, and stops on the first failure. It shares
the inference runners' GPU locks. Only completed fences
and exact output matches produce `PASS`. JSON receipts record the GPU,
kernel, Python version and source hashes; `--compare` reports changes without
treating them as execution failures. This check covers the native examples;
the inference backends have their own dependency and correctness checks.

The [2026-10-07 receipt](experimental/dumps/asahi_check/result.json) records
nine passing native runs on the M1 MacBook Air, G13G B1, kernel `7.1.13+`.

Standalone Python examples, standard library and direct DRM ioctls only:

```bash
python3 examples/add_asahi.py
python3 examples/mul_asahi.py
python3 examples/tri_asahi.py
AGX_TRACE=2 python3 examples/add_asahi.py
```

All three passed on an M1 MacBook Air, G13G B1, with Fedora Asahi kernel
`7.1.13-402.asahi.fc44.aarch64+16k` on 2026-10-05. ADD returns
`[11, 22, 33, 44]`, MUL returns `[10, 40, 90, 160]`, and the triangle checks
all 64 pixels of an 8x8 RGBA8 render target. Each file contains its own driver
bindings, GPU buffers, command construction, submission and result checking.

Mesa 26.2.3 ADD/MUL also passed. Their 40-byte shaders match the standalone
shaders through STOP. See the [ISA and command-state comparison](experimental/dumps/ASAHI.md)
for saved dumps and reproduction commands.

### GPT-2 inference

Run full GPT-2 124M on the M1 GPU through tinygrad OpenCL or omarchy-mlx Vulkan:

```bash
gpt2/first-run.sh --backend tinygrad --beam 0 --prompt 'Hello world'
gpt2/first-run.sh --backend mlx --prompt 'Hello world'
gpt2/first-run.sh compare --beams 0 2 --lengths 32 128 256
```

See [gpt2/README.md](gpt2/README.md) for setup, numerical verification,
and separate warmed prefill and decode benchmarks.

### Qwen3.5-0.8B inference

Run the official Qwen3.5-0.8B text decoder on the M1 GPU:

```bash
qwen35/first-run.sh --backend mlx --prompt 'What is 2 + 2?'
qwen35/first-run.sh --backend tinygrad --beam 0 --prompt 'What is 2 + 2?'
qwen35/first-run.sh verify --backend mlx --context 64 --steps 4
qwen35/first-run.sh benchmark --backend all --context 64 --steps 8 --trials 3
```

See [qwen35/README.md](qwen35/README.md) for the pinned checkpoint,
chat and thinking modes, independent numerical checks and warmed timings.

### Bring-up and capture tools

[experimental/asahi.py](experimental/asahi.py) contains the bring-up source.
ADD/MUL construct annotated shader bytes and USC/CDM commands; the triangle
embeds native render state prepared offline with Mesa 25.3.6. All target
base M1 (T8103, G13G) and require the Asahi DRM driver. `--dry-run` validates
command data without GPU execution; `PASS` requires a completed GPU result.

[experimental/mesa_compute.py](experimental/mesa_compute.py) captures ADD/MUL
through installed Mesa GLES. [experimental/compare_asahi.py](experimental/compare_asahi.py)
compares those dumps with the explicit DRM shader and dispatch state.

Regenerate the standalone examples after changing the bring-up source:

```bash
python3 experimental/asahi2standalone.py
```

### Learning from AGXForge

[AGXForge](https://github.com/sbryngelson/AGXForge) is a useful research
reference, but its compiler emits M5/G17 instructions and its runtimes use
macOS Metal or private IOGPU interfaces. This machine is M1/G13G with Linux
DRM. Its G17 binaries, tensor instructions, launch packets and Apple decoder
cannot be used by these Asahi examples. Even its compiler release checks
require Apple's macOS `GPUCompiler.framework`.

The lessons that fit these minimal examples are reproducibility, correctness
and clear measurements:

| AGXForge source | Application here |
| --- | --- |
| `tools/g17platform.py`, `docs/execution-validation.md` | Record the actual target and require completed results. `experimental/check_asahi.py` checks the small native examples repeatedly; they already check output sentinels, command layouts and fences. |
| `docs/demonstrations.md` | Compare results with an independent CPU reference. Qwen's optional `verify` check exposed and corrected a shared DeltaNet normalization error. |
| `examples/decode_study.py`, `tools/g17twin.py` | Separate first-use compilation from warmed execution and use identical inputs. GPT-2's comparator and Qwen's optional `benchmark` use shared CPU token histories and rotating backend order. |

Borrow a kernel idea only when it can be shown as a small, readable example
with a checked result. AGXForge's general inference graph and optimized
kernel collection belong in that project. The checks and timing tools here
support the examples rather than setting an inference-engine roadmap.

# Environment

Tested on:

M1 MacBook Air

```
ProductName:		macOS
ProductVersion:		26.5.1
BuildVersion:		25F80
```

M1 MacBook Air

```
ProductName:		macOS
ProductVersion:		26.6.2
BuildVersion:		25G83
```

M4 MacBook Air

```
ProductName:		macOS
ProductVersion:		26.5.1
BuildVersion:		25F80
```
