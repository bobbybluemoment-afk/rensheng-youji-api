#!/usr/bin/env python3
"""把免费版确定性排盘结果转换为内置命理 Core 的标准输入。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CORE_ROOT = ROOT / "internal" / "rensheng-youji-mingli-core"
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(CORE_ROOT / "scripts"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="排盘并生成内置命理 Core 的标准 JSON 输入。")
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
    parser.add_argument("--timezone", default=None, help="IANA 时区，例如 Asia/Shanghai")
    parser.add_argument("--center-year", type=int, default=None)
    parser.add_argument("--analysis-as-of", required=True, help="分析基准日期，格式 YYYY-MM-DD")
    parser.add_argument("--request-id", default=None)
    parser.add_argument("--latitude", type=float, default=None)
    parser.add_argument("--output", required=True, help="Core 标准输入 JSON 保存路径")
    parser.add_argument("--profile-output", default=None, help="可选：同时保存原始排盘 profile")
    return parser.parse_args()


def main() -> int:
    if not CORE_ROOT.exists():
        print(json.dumps({
            "status": "error",
            "message": "缺少 internal/rensheng-youji-mingli-core，请确认更新包已完整上传。",
        }, ensure_ascii=False))
        return 2

    try:
        from adapter_from_api_profile import adapt_profile
        from rensheng_youji.local_engine import build_profile
        from validate_analysis_input import SCHEMA_PATH, load_json, validate
        from _jsonschema_subset import validate_schema_instance
    except ImportError as exc:
        print(json.dumps({
            "status": "environment_required",
            "message": f"缺少运行依赖 {exc.name}，请先运行 scripts/setup_env.py。",
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
        result = adapt_profile(
            profile,
            analysis_as_of=args.analysis_as_of,
            request_id=args.request_id,
            latitude=args.latitude,
        )
        schema = load_json(SCHEMA_PATH)
        errors = validate_schema_instance(result, schema)
        errors.extend(validate(result))
        if errors:
            print(json.dumps({"status": "validation_error", "errors": errors}, ensure_ascii=False, indent=2))
            return 3

        output = Path(args.output).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

        if args.profile_output:
            profile_output = Path(args.profile_output).expanduser().resolve()
            profile_output.parent.mkdir(parents=True, exist_ok=True)
            profile_output.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    except (ValueError, KeyError, OSError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 4

    print(json.dumps({
        "status": "ok",
        "output": str(output),
        "request_id": result["request"]["request_id"],
        "pillars": {
            key: value["stem"] + value["branch"]
            for key, value in result["chart"]["pillars"].items()
        },
        "target_range": result["request"]["target_range"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
