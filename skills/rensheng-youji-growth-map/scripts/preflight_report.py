#!/usr/bin/env python3
"""在报告分析前检查输入完整度与会改变排盘的时间边界。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


FOCUS_FIELDS = {
    "事业": ["education", "occupation", "current_role", "current_concerns"],
    "关系": ["relationship_status", "relationship_history", "current_concerns"],
    "财务": ["financial_stage", "resource_context", "current_concerns"],
    "家庭": ["family_stage", "family_background", "current_concerns"],
}


def validate(data: Any, focus: str) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError("Core 输入必须是对象")
    flags = data.get("solar_terms_and_boundaries", {}).get("boundary_flags", [])
    sensitive = sorted(set(flags) - {"none", "true_solar_time_sensitive"})
    birth = data.get("person", {}).get("birth", {})
    reality = data.get("reality_context", {})
    matched_focus = next((name for name in FOCUS_FIELDS if name in focus), None)
    expected = FOCUS_FIELDS.get(matched_focus, [])
    missing = [field for field in expected if not reality.get(field)]

    blockers: list[str] = []
    followups: list[str] = []
    if sensitive:
        blockers.append("出生时间接近日界、时辰、节气或起运边界，可能改变排盘版本")
        followups.append("请确认出生时间精确到分钟，并补充出生医院或区县；若无法确认，只能生成未校准初步分析。")
    if birth.get("time_precision") not in {"minute", "second"}:
        blockers.append("出生时间精度不足")
        followups.append("请尽量提供24小时制的准确出生时间。")
    if missing:
        followups.append("为了回答当前问题，请补充或明确不知道：" + "、".join(missing))

    return {
        "status": "blocked" if blockers else "ready",
        "formal_report_allowed": not blockers,
        "boundary_flags": flags,
        "blockers": blockers,
        "focus": focus,
        "missing_focus_context": missing,
        "followups": followups,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="完整报告输入与边界预检")
    parser.add_argument("input", type=Path, help="core-input.json")
    parser.add_argument("--focus", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
        result = validate(data, args.focus)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 3 if result["status"] == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
