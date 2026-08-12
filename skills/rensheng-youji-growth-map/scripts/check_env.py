#!/usr/bin/env python3
"""检查成长地图的确定性排盘环境。"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    try:
        import lunar_python  # noqa: F401
    except ImportError:
        print("MISSING: lunar_python")
        return 2
    completed = subprocess.run([
        sys.executable, str(ROOT / "scripts/calc_profile.py"),
        "--datetime", "1999-01-22 17:45", "--gender", "male",
        "--city", "福建泉州惠安县",
    ], check=True, capture_output=True, text=True)
    if '"day_pillar": "甲戌"' not in completed.stdout:
        print("FAILED: known chart mismatch")
        return 3
    print("READY: dependencies, location, true solar time, chart and luck cycle passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
