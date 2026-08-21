#!/usr/bin/env python3
"""兼容旧命令：转交仓库根目录统一排盘并生成 Core 输入。"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]


def main() -> int:
    parser = argparse.ArgumentParser(description="使用统一排盘生成 Core 输入")
    parser.add_argument("--datetime", required=True, help="出生时间 YYYY-MM-DD HH:MM")
    parser.add_argument("--gender", required=True, choices=("male", "female"))
    parser.add_argument("--city", required=True)
    parser.add_argument("--country", default="中国")
    parser.add_argument("--longitude", type=float)
    parser.add_argument("--timezone")
    parser.add_argument("--time-basis", choices=("local_civil", "true_solar_adjusted"), default="local_civil")
    parser.add_argument("--analysis-as-of", default=date.today().isoformat())
    parser.add_argument("--output", required=True)
    parser.add_argument("--profile-output")
    args = parser.parse_args()

    command = [
        sys.executable,
        str(REPO_ROOT / "scripts/prepare_core_input.py"),
        "--birth", args.datetime,
        "--gender", args.gender,
        "--city", args.city,
        "--country", args.country,
        "--time-basis", args.time_basis,
        "--analysis-as-of", args.analysis_as_of,
        "--output", args.output,
    ]
    if args.longitude is not None:
        command.extend(["--longitude", str(args.longitude)])
    if args.timezone:
        command.extend(["--timezone", args.timezone])
    if args.profile_output:
        command.extend(["--profile-output", args.profile_output])
    return subprocess.run(command, cwd=REPO_ROOT, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
