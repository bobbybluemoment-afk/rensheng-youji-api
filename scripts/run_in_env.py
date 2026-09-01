#!/usr/bin/env python3
"""Run a repository command with the Python created by setup_env.py."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def runtime_python(root: Path = ROOT, platform_name: str | None = None) -> Path:
    """Return the repository-local interpreter path without activating a shell."""

    platform_name = os.name if platform_name is None else platform_name
    relative = Path("Scripts/python.exe") if platform_name == "nt" else Path("bin/python")
    return root / "venv" / relative


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(
            "USAGE: python scripts/run_in_env.py <script-or--m> [args...]\n"
            "先运行: python scripts/setup_env.py",
            file=sys.stderr,
        )
        return 2

    python = runtime_python()
    if not python.is_file():
        print(
            "MISSING_RUNTIME: 仓库虚拟环境不存在。请先运行 "
            "python scripts/setup_env.py",
            file=sys.stderr,
        )
        return 3

    completed = subprocess.run([str(python), *argv], cwd=ROOT, check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
