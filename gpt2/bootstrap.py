#!/usr/bin/env python3
"""Install the local runner environment; keep Fedora math libraries in the user cache."""

import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parent
CACHE = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "applegpu-gpt2"


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def cached_mlx_wheel(requirement):
    url = requirement.split(" @ ", 1)[1]
    clean_url, fragment = urllib.parse.urldefrag(url)
    expected = fragment.removeprefix("sha256=")
    target = CACHE / urllib.parse.unquote(urllib.parse.urlparse(clean_url).path.rsplit("/", 1)[1])
    CACHE.mkdir(parents=True, exist_ok=True)
    if target.is_file() and digest(target) == expected:
        return target
    fd, name = tempfile.mkstemp(prefix=".mlx-wheel-", dir=CACHE)
    temporary = Path(name)
    try:
        print("Downloading the pinned MLX Vulkan wheel to the external cache...", flush=True)
        with os.fdopen(fd, "wb") as stream, urllib.request.urlopen(clean_url, timeout=90) as response:
            while block := response.read(4 * 1024 * 1024):
                stream.write(block)
        if digest(temporary) != expected:
            raise RuntimeError("MLX wheel SHA256 mismatch")
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return target


def native_libraries():
    library_dir = CACHE / "runtime/usr/lib64"
    names = ("libblas.so.3", "liblapack.so.3", "libgfortran.so.5", "libopenblas.so.0")
    missing = []
    for name in names:
        try:
            ctypes.CDLL(name)
        except OSError:
            if not (library_dir / name).is_file():
                missing.append(name)
    if not missing:
        return
    release = Path("/etc/os-release").read_text()
    if "fedora" not in release.lower() or not shutil.which("dnf"):
        raise RuntimeError("MLX needs BLAS/LAPACK and libgfortran installed by the system package manager")
    destination = CACHE / "rpms"
    destination.mkdir(parents=True, exist_ok=True)
    subprocess.run(["dnf", "download", f"--destdir={destination}", "blas", "lapack", "libgfortran", "openblas-serial"], check=True)
    runtime = CACHE / "runtime"
    runtime.mkdir(exist_ok=True)
    records = {}
    for rpm in destination.glob("*.rpm"):
        # RPM payload extraction only; package scripts and system installation never run.
        with subprocess.Popen(["rpm2cpio", str(rpm)], stdout=subprocess.PIPE) as producer:
            subprocess.run(["cpio", "--quiet", "-idm", "-D", str(runtime)], stdin=producer.stdout, check=True)
            producer.stdout.close()
            if producer.wait():
                raise RuntimeError("RPM extraction failed")
        records[rpm.name] = hashlib.sha256(rpm.read_bytes()).hexdigest()
    if not all((library_dir / n).is_file() for n in names):
        raise RuntimeError("math library extraction did not provide all required files")
    (runtime / "packages.json").write_text(json.dumps(records, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=("tinygrad", "mlx", "all"), default="tinygrad")
    args = parser.parse_args()
    if args.backend != "tinygrad" and (sys.version_info[:2] != (3, 14) or platform.machine() != "aarch64"):
        parser.error("this pinned MLX wheel requires CPython 3.14 on Linux aarch64; set GPT2_PYTHON accordingly")
    environment = ROOT / ".venv"
    python = environment / "bin/python"
    if not python.is_file():
        subprocess.run([sys.executable, "-m", "venv", str(environment)], check=True)
    requirements = [ROOT / "requirements.txt"]
    if args.backend != "tinygrad":
        requirements.append(ROOT / "requirements-mlx.txt")
    fingerprint = hashlib.sha256(b"".join(p.read_bytes() for p in requirements)).hexdigest()
    stamp = environment / f".installed-{args.backend}"
    check = "import numpy, regex, safetensors, tinygrad"
    if args.backend != "tinygrad":
        native_libraries()
        check += ", mlx.core, mlx_lm"
    if not stamp.is_file() or stamp.read_text().strip() != fingerprint or subprocess.run(
            [str(python), "-c", check], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
        if shutil.which("uv"):
            command = ["uv", "pip", "install", "--python", str(python)]
        else:
            subprocess.run([str(python), "-m", "ensurepip"], check=True)
            command = [str(python), "-m", "pip", "install", "--disable-pip-version-check"]
        command += ["-r", str(ROOT / "requirements.txt")]
        if args.backend != "tinygrad":
            lines = [line for line in (ROOT / "requirements-mlx.txt").read_text().splitlines()
                     if line and not line.startswith("#")]
            command += [str(cached_mlx_wheel(lines[0])), *lines[1:]]
        subprocess.run(command, check=True)
        stamp.write_text(fingerprint + "\n")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"GPT-2 setup failed: {error}", file=sys.stderr)
        raise SystemExit(1)
