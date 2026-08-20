#!/usr/bin/env python3
"""把 Core 元数据、卡片文字和确定性趋势序列组合成标准输出。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
OUTPUT_SKILL = ROOT / "internal/rensheng-youji-free-card-output"
sys.path.insert(0, str(OUTPUT_SKILL / "scripts"))


def load(path: str) -> dict:
    return json.loads(Path(path).expanduser().resolve().read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--analysis", required=True, help="已校验 analysis-output.json")
    parser.add_argument("--content", required=True, help="AI按提取规则生成的 card-content.json")
    parser.add_argument("--series", required=True, help="build_visual_series.py 的输出")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    try:
        analysis, content, series = load(args.analysis), load(args.content), load(args.series)
        meta = analysis["analysis_meta"]
        if meta.get("status") != "complete":
            raise ValueError("Core analysis_meta.status 必须为 complete")
        result = {
            "schema_version": "1.1.0",
            "source": {
                "analysis_id": meta["analysis_id"],
                "core_version": meta["core_version"],
                "analysis_as_of": meta["analysis_as_of"],
            },
            "identity": content["identity"],
            "mingju_analysis": content["mingju_analysis"],
            "trend_panel": series,
            "current_issue": content["current_issue"],
            "full_report_hint": content["full_report_hint"],
            "disclaimers": content["disclaimers"],
        }
        from validate_free_card_output import validate
        errors = validate(result)
        if errors:
            print(json.dumps({"status": "validation_error", "errors": errors}, ensure_ascii=False, indent=2))
            return 3
        output = Path(args.output).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    except (KeyError, ValueError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 4

    print(json.dumps({"status": "ok", "output": str(output), "years": 20}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
