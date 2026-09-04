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
