#!/usr/bin/env python3
"""检查完整报告与统一 Core 的文件和运行依赖。"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
SKILL_ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    required = [
        REPO_ROOT / "internal/core-manifest.json",
        REPO_ROOT / "internal/rensheng-youji-mingli-core/SKILL.md",
        REPO_ROOT / "scripts/prepare_core_input.py",
        SKILL_ROOT / "references/report-schema.md",
        SKILL_ROOT / "scripts/render_report.py",
        SKILL_ROOT / "scripts/render_report_pdf.py",
        SKILL_ROOT / "scripts/generate_full_report.py",
        SKILL_ROOT / "scripts/validate_calibration_questions.py",
        REPO_ROOT / "assets/fonts/noto/NotoSansCJKsc-Regular.otf",
        REPO_ROOT / "assets/wechat-contact.jpg",
        REPO_ROOT / "assets/asset-manifest.json",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        print("MISSING: " + ", ".join(missing))
        return 2
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts/check_env.py")],
        cwd=REPO_ROOT,
        check=False,
    )
    if result.returncode:
        return result.returncode
    print("READY: shared chart, Core and full-report renderer found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
