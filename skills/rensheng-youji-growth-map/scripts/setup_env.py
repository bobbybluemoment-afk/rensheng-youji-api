#!/usr/bin/env python3
"""为人生有迹完整报告创建隔离运行环境。"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", default=str(ROOT / "venv"))
    args = parser.parse_args()
    target = Path(args.target).expanduser().resolve()
    if sys.version_info < (3, 11):
        raise SystemExit("需要 Python 3.11 或更高版本。")
    python = target / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.exists():
        venv.EnvBuilder(with_pip=True).create(target)
    env = os.environ.copy()
    env["PIP_CACHE_DIR"] = str(target / ".pip-cache")
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    subprocess.run([str(python), "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")], check=True, env=env)
    subprocess.run([str(python), str(ROOT / "scripts/check_env.py")], check=True)
    print(f"READY: {python}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
