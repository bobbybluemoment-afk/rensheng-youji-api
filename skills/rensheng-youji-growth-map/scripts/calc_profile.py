#!/usr/bin/env python3
"""根据出生地钟表时间，确定性计算真太阳时、四柱与大运。"""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from rensheng_youji.bazi import calculate_bazi
from rensheng_youji.solar_time import adjust_to_true_solar, resolve_location


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--datetime", required=True, help="出生地当地钟表时间，例如 1999-01-22 17:45")
    parser.add_argument("--gender", required=True, choices=("male", "female"))
    parser.add_argument("--city", required=True)
    parser.add_argument("--longitude", type=float)
    parser.add_argument("--timezone")
    parser.add_argument("--time-basis", choices=("local_civil", "true_solar_adjusted"), default="local_civil")
    args = parser.parse_args()

    local = datetime.strptime(args.datetime, "%Y-%m-%d %H:%M")
    if args.time_basis == "true_solar_adjusted":
        adjusted = local
        location_name = args.city
        correction = 0.0
        timezone = args.timezone or "already_adjusted"
    else:
        location = resolve_location(args.city, args.longitude, args.timezone)
        adjusted, correction, _ = adjust_to_true_solar(local, location)
        location_name = location.resolved_name
        timezone = location.timezone

    result = {
        "birthplace": location_name,
        "timezone": timezone,
        "local_civil_time": local.strftime("%Y-%m-%d %H:%M"),
        "true_solar_time": adjusted.strftime("%Y-%m-%d %H:%M"),
        "true_solar_correction_minutes": round(correction, 2),
        "bazi": calculate_bazi(adjusted, args.gender),
        "warning": "真太阳时按城市或县区中心经度近似；若接近时辰边界，建议用具体出生地址复核。",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
