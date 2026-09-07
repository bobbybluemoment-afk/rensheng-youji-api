#!/usr/bin/env python3
"""把 Core 元数据、卡片文字和确定性趋势序列组合成标准输出。"""

from __future__ import annotations

import argparse
import hashlib
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
    parser.add_argument("--baseline", help="校准前冻结的analysis-baseline.json")
    parser.add_argument("--baseline-lock", help="analysis-baseline-lock.json")
    parser.add_argument("--resolved-sources", help="校准后确定性报告选材；只影响可见摘要与当前课题")
    parser.add_argument("--content", required=True, help="确定性提取器生成的 card-content.json")
    parser.add_argument("--series", required=True, help="build_visual_series.py 的输出")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    try:
        analysis, content, series = load(args.analysis), load(args.content), load(args.series)
        baseline = load(args.baseline) if args.baseline else analysis
        lock = load(args.baseline_lock) if args.baseline_lock else None
        resolved = load(args.resolved_sources) if args.resolved_sources else None
        meta = analysis["analysis_meta"]
        if meta.get("status") not in {"complete", "pass_with_flags"}:
            raise ValueError("Core analysis_meta.status 必须为 complete 或 pass_with_flags")
        if analysis.get("method_execution_audit", {}).get("delivery_decision") == "preliminary_only":
            raise ValueError("preliminary_only Core 不得生成带20年趋势的正式卡片")
        baseline_bytes = json.dumps(baseline, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        baseline_sha = hashlib.sha256(baseline_bytes).hexdigest()
        if lock and (lock.get("baseline_sha256") != baseline_sha or lock.get("analysis_id") != baseline.get("analysis_meta", {}).get("analysis_id")):
            raise ValueError("卡片使用的Baseline与锁文件不一致")
        if baseline.get("analysis_meta", {}).get("analysis_id") != meta.get("analysis_id"):
            raise ValueError("卡片的冻结Core与校准后Core不是同一次分析")
        if lock and series.get("window_start_state", {}).get("evidence_mode") != "birth_only":
            raise ValueError("完整报告卡片的人生K线必须来自校准前冻结Core，不得使用校准事实改写")
        calibrated_sha = hashlib.sha256(json.dumps(analysis, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        result = {
            "schema_version": "1.2.0",
            "source": {
                "analysis_id": meta["analysis_id"],
                "core_version": meta["core_version"],
                "analysis_as_of": meta["analysis_as_of"],
                "baseline_sha256": baseline_sha,
                "calibrated_sha256": calibrated_sha,
                "resolved_source_sha256": resolved.get("resolved_sha256") if resolved else None,
                "trend_source": "frozen_baseline",
                "visible_selection_source": "post_calibration" if resolved else "frozen_baseline",
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
