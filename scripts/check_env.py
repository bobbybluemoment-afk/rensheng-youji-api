#!/usr/bin/env python3
"""检查依赖、字体、排盘与连续K线是否可用。"""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))


def main() -> int:
    try:
        import lunar_python  # noqa: F401
        from PIL import Image  # noqa: F401
    except ImportError as exc:
        print(f"MISSING: {exc.name}")
        return 2

    required = [
        ROOT / "assets/logo.png",
        ROOT / "assets/fonts/noto/NotoSansCJKsc-Regular.otf",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        print("MISSING_ASSET: " + ", ".join(missing))
        return 3

    from rensheng_youji.local_engine import build_profile

    profile = build_profile(
        name="",
        birth="1999-01-22 17:45",
        gender="male",
        city="北京",
        time_basis="true_solar_adjusted",
        center_year=2026,
    )
    if profile["bazi"]["pillars"] != ["戊寅", "乙丑", "甲戌", "癸酉"]:
        print("FAILED: known chart mismatch")
        return 4
    timeline = profile["life_kline"]["timeline"]
    if len(timeline) != 20 or timeline[5]["year"] != 2026:
        print("FAILED: timeline mismatch")
        return 5
    print("READY: dependencies, assets, chart and K-line passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
