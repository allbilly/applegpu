# AppleGPU

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
