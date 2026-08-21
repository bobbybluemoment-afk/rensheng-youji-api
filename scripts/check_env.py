#!/usr/bin/env python3
"""检查依赖、字体、排盘与新版免费卡片链路是否可用。"""

from __future__ import annotations

import sys
from pathlib import Path
import subprocess


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
        ROOT / "assets/icon.svg",
        ROOT / "assets/fonts/noto/NotoSansCJKsc-Regular.otf",
        ROOT / "internal/rensheng-youji-mingli-core/SKILL.md",
        ROOT / "internal/rensheng-youji-free-card-output/SKILL.md",
        ROOT / "internal/rensheng-youji-free-card-renderer/SKILL.md",
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
    report_test = subprocess.run(
        [
            sys.executable,
            "-m",
            "unittest",
            "tests.test_full_report_pipeline.FullReportPipelineTest.test_new_card_and_fixed_ten_page_pdf",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if report_test.returncode:
        print("FAILED: v2 card -> fixed 10-page report pipeline")
        print(report_test.stdout or report_test.stderr)
        return 6
    print("READY: dependencies, chart, v2 card and fixed 10-page report pipeline passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
