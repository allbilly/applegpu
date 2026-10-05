#!/usr/bin/env python3
"""Add the pinned Qwen tokenizer dependencies to the shared environment."""

import importlib.metadata
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    requirements = Path(__file__).resolve().parent / "requirements.txt"
    for line in requirements.read_text().splitlines():
        name, expected = line.split("==")
        try:
            installed = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            installed = None
        if installed != expected:
            if shutil.which("uv"):
                command = ["uv", "pip", "install", "--python", sys.executable]
            else:
                subprocess.run([sys.executable, "-m", "ensurepip"], check=True)
                command = [sys.executable, "-m", "pip", "install", "--disable-pip-version-check"]
            subprocess.run([*command, "-r", str(requirements)], check=True)
            break


if __name__ == "__main__":
    main()
