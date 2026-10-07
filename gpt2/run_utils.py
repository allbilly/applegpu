"""Host-side locks and measurement helpers for the small Asahi examples."""

from contextlib import contextmanager, ExitStack
import fcntl
from pathlib import Path

import numpy as np


def machine_state():
    temperatures = {}
    for directory in Path("/sys/class/hwmon").glob("hwmon*"):
        try:
            if (directory / "name").read_text().strip() != "macsmc_hwmon":
                continue
        except OSError:
            continue
        for path in directory.glob("temp*_input"):
            try:
                label = path.with_name(path.name.replace("_input", "_label"))
                name = label.read_text().strip() if label.is_file() else path.stem
                temperatures[name] = int(path.read_text()) / 1000
            except (OSError, ValueError):
                pass
    memory = {line.split(":")[0]: int(line.split()[1]) * 1024
              for line in Path("/proc/meminfo").read_text().splitlines()
              if line.startswith(("MemAvailable:", "SwapFree:"))}
    return dict(temperatures_c=temperatures, memory=memory)


@contextmanager
def gpu_lock():
    with ExitStack() as stack:
        for path in (Path.home() / "gpu.lock", Path("/tmp/m1-gpu.lock")):
            stream = stack.enter_context(path.open("a"))
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise RuntimeError(f"GPU is reserved by another job: {path}") from None
        yield


def stats(samples):
    return dict(samples=len(samples), raw_ms=samples, mean_ms=float(np.mean(samples)),
                median_ms=float(np.median(samples)), min_ms=min(samples), max_ms=max(samples),
                steps_per_second=1000 * len(samples) / sum(samples))
