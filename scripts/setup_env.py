#!/usr/bin/env python3
"""为人生有迹免费卡片创建隔离的本地运行环境。"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import venv
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", default=str(ROOT / "venv"))
    args = parser.parse_args()
    target = Path(args.target).expanduser().resolve()
    if sys.version_info < (3, 11):
        raise SystemExit("需要 Python 3.11 或更高版本。")
    if not (target / ("Scripts/python.exe" if os.name == "nt" else "bin/python")).exists():
        print("正在创建人生有迹本地运行环境……")
        venv.EnvBuilder(with_pip=True).create(target)
    python = target / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    install_env = os.environ.copy()
    install_env["PIP_CACHE_DIR"] = str(target / ".pip-cache")
    install_env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    subprocess.run(
        [str(python), "-m", "pip", "install", "--disable-pip-version-check", "-r", str(ROOT / "requirements.txt")],
        check=True,
        env=install_env,
    )
    subprocess.run([str(python), str(ROOT / "scripts/check_env.py")], check=True)
    print(f"READY: {python}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
