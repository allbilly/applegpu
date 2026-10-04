# Native Asahi hardware comparison

Recorded on 2026-10-05, M1 MacBook Air (T8103), GPU **G13G B1**.

- Linux: `7.1.13-402.asahi.fc44.aarch64+16k`
- Mesa: `26.2.3`, OpenGL ES 3.2
- Device: `/dev/dri/renderD128`, driver `asahi`

`mesa_compute.py` executes a GLSL compute shader through the installed Mesa
driver. Mesa's decoder reads the submitted GPU buffers and dumps the shader
ISA, USC pipeline, CDM launch and barrier fields. The dump describes command
state and shader register allocation; it does not read physical MMIO registers.

## Results

| Workload | Mesa reference | Standalone DRM | Shader comparison |
| --- | --- | --- | --- |
| ADD | `[11, 22, 33, 44]` | `[11, 22, 33, 44]` | All 40 bytes through STOP match |
| MUL | `[10, 40, 90, 160]` | `[10, 40, 90, 160]` | All 40 bytes through STOP match |
| Triangle | Offline prepared Mesa render state | All 64 pixels equal `ff0000ff` | Render execution/readback passed |

Both compute shaders use `r0` for the thread index, `r1/r2` for float operands,
`u4:u5` for A, `u2:u3` for B, and `u0:u1` for the output pointer. Their only
instruction difference is at byte offset `0x18`:

```text
ADD  2a85c2422c00  fadd r1, ^r1, ^r2
MUL  1a85c2422c00  fmul r1, ^r1, ^r2
```

The standalone shader includes 16 bytes of trap padding after STOP. The live
decoder stops at STOP, so this comparison does not claim those padding bytes
were checked against Mesa's buffer.

## State comparison

| Field | Live Mesa | Standalone compute |
| --- | --- | --- |
| Shader registers | 8 | 8 |
| Bound uniform half registers | 12, three 64-bit pointers | 12, three 64-bit pointers |
| Global size | `4 × 1 × 1` | `4 × 1 × 1` |
| Local size | `4 × 1 × 1` | `4 × 1 × 1` |
| Shared memory used | No | No |
| Preshader | None | None |
| Launch uniform register count | 64 | 64 |
| Launch texture register count | 8 | 0 |
| Launch sampler register count | 4 compact | 0 |
| Launch preshader register count | 16 | 0 |

Mesa includes a default sampler and reserves resources the scalar shader does
not use. The smaller standalone pipeline executes correctly with those fields
zeroed. Addresses differ because the two programs allocate their own buffers.

The existing macOS `add.py`/`mul.py` use the same input values and expected
arithmetic results. They retain the IOKit capture/replay path. This report
compares the native Mesa ISA with the Asahi builder; it does not claim the
macOS capture is byte-identical or executable through DRM.

## Reproduce

From the repository root:

```bash
mkdir -p experimental/dumps/asahi_add experimental/dumps/asahi_mul experimental/dumps/asahi_tri
python3 experimental/mesa_compute.py add --dump-dir experimental/dumps/asahi_add \
  > experimental/dumps/asahi_add/mesa.log 2>&1
python3 experimental/mesa_compute.py mul --dump-dir experimental/dumps/asahi_mul \
  > experimental/dumps/asahi_mul/mesa.log 2>&1
python3 experimental/compare_asahi.py experimental/dumps/asahi_add
python3 experimental/compare_asahi.py experimental/dumps/asahi_mul
AGX_TRACE=2 python3 examples/add_asahi.py > experimental/dumps/asahi_add/drm.log
AGX_TRACE=2 python3 examples/mul_asahi.py > experimental/dumps/asahi_mul/drm.log
AGX_TRACE=2 python3 examples/tri_asahi.py > experimental/dumps/asahi_tri/drm.log
```

Each compute directory contains the GLSL source, Mesa compiler log, native
command/ISA decode, JSON comparison and standalone ioctl trace.
`result.json` records the Mesa result and environment.
The triangle directory contains its standalone ioctl trace.
