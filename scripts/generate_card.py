#!/usr/bin/env python3
"""校验 free-card-output.json 并生成新版人生有迹 PNG 卡片。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
OUTPUT_SKILL = ROOT / "internal/rensheng-youji-free-card-output"
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(OUTPUT_SKILL / "scripts"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="由标准免费卡片 JSON 生成1242×1660 PNG。")
    parser.add_argument("--input", required=True, help="已完成的 free-card-output.json")
    parser.add_argument("--output", default="rensheng-youji-card.png")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        from rensheng_youji.render_free_card_v2 import render_free_card
        from validate_free_card_output import validate
    except ImportError as exc:
        print(json.dumps({
            "status": "environment_required",
            "message": f"缺少运行依赖 {exc.name}，请由AI运行 scripts/setup_env.py 后重试。",
        }, ensure_ascii=False))
        return 2

    try:
        input_path = Path(args.input).expanduser().resolve()
        data = json.loads(input_path.read_text(encoding="utf-8"))
        errors = validate(data)
        if errors:
            print(json.dumps({"status": "validation_error", "errors": errors}, ensure_ascii=False, indent=2))
            return 3
        output = render_free_card(data, Path(args.output))
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 4

    print(json.dumps({
        "status": "ok",
        "output": str(output),
        "width": 1242,
        "height": 1660,
        "cloud_used": False,
        "verification_code_used": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
