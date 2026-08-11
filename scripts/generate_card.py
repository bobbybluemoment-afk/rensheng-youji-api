#!/usr/bin/env python3
"""在本地生成一张人生有迹免费PNG卡片。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="本地生成含20年连续人生K线的人生有迹免费卡片。")
    parser.add_argument("--name", default="", help="姓名，可留空")
    parser.add_argument("--birth", required=True, help="出生时间，格式 YYYY-MM-DD HH:MM")
    parser.add_argument("--gender", required=True, choices=("male", "female"))
    parser.add_argument("--city", required=True)
    parser.add_argument("--country", default="中国")
    parser.add_argument(
        "--time-basis",
        choices=("local_civil", "true_solar_adjusted"),
        default="local_civil",
    )
    parser.add_argument("--longitude", type=float, default=None)
    parser.add_argument("--timezone", default=None, help="IANA时区，例如 Asia/Shanghai")
    parser.add_argument("--center-year", type=int, default=None, help="仅供复现历史版本或测试")
    parser.add_argument("--output", default="rensheng-youji-card.png")
    parser.add_argument("--profile-output", default=None, help="可选：保存审计JSON")
    return parser.parse_args()


def main() -> int:
    try:
        from rensheng_youji.local_engine import build_profile, render_profile
    except ImportError as exc:
        print(json.dumps({
            "status": "environment_required",
            "message": f"缺少运行依赖 {exc.name}，请由AI运行 scripts/setup_env.py 后重试。",
        }, ensure_ascii=False))
        return 2

    args = parse_args()
    try:
        profile = build_profile(
            name=args.name,
            birth=args.birth,
            gender=args.gender,
            city=args.city,
            country=args.country,
            time_basis=args.time_basis,
            longitude=args.longitude,
            timezone=args.timezone,
            center_year=args.center_year,
        )
        output = render_profile(profile, Path(args.output).expanduser().resolve())
    except (ValueError, KeyError, OSError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 3

    if args.profile_output:
        profile_path = Path(args.profile_output).expanduser().resolve()
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": "ok",
        "output": str(output),
        "pillars": profile["bazi"]["pillars"],
        "true_solar_time": profile["time"]["true_solar_time"],
        "warnings": profile["warnings"],
        "timeline_algorithm": profile["life_kline"]["timeline_algorithm"],
        "cloud_used": False,
        "verification_code_used": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
