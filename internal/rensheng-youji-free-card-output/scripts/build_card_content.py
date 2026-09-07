#!/usr/bin/env python3
"""Deterministically extract card copy from the frozen and calibrated Core."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DOMAIN_MAP = {
    "self_growth": ("growth", "把自己的选择说清楚"),
    "love_partner": ("relationships", "关系怎样稳定推进"),
    "career": ("career", "工作怎样形成成果"),
    "finance_resources": ("wealth", "资源怎样真正留下"),
    "body_emotion": ("growth", "压力怎样及时恢复"),
    "family_growth": ("family", "家庭责任怎样分清"),
}


def _pillars(profile: dict[str, Any], baseline: dict[str, Any]) -> list[str]:
    values = profile.get("bazi", {}).get("pillars")
    if isinstance(values, list) and len(values) == 4:
        return [str(item) for item in values]
    source = baseline.get("chart_facts", {}).get("pillars", {})
    return [str(source[key].get("stem", "")) + str(source[key].get("branch", "")) for key in ("year", "month", "day", "hour")]


def _summary(value: Any, fallback: str) -> str:
    if isinstance(value, dict) and isinstance(value.get("summary"), str) and value["summary"].strip():
        return value["summary"].strip()
    if isinstance(value, str) and value.strip():
        return value.strip()
    return fallback


def build(profile: dict[str, Any], baseline: dict[str, Any], calibrated: dict[str, Any], resolved: dict[str, Any] | None = None) -> dict[str, Any]:
    baseline_meta = baseline.get("analysis_meta", {})
    calibrated_meta = calibrated.get("analysis_meta", {})
    if baseline_meta.get("analysis_id") != calibrated_meta.get("analysis_id"):
        raise ValueError("卡片内容的Baseline与校准后Core不是同一次分析")
    ledger = {item["claim_id"]: item for item in calibrated.get("report_claim_ledger") or [] if isinstance(item, dict)}
    source = (resolved or {}).get("current_question") or calibrated.get("report_source_bundle", {}).get("current_stage_source", {})
    claim_ids = source.get("mandatory_claim_ids") or source.get("claim_ids") or []
    claims = [ledger[item] for item in claim_ids if item in ledger and ledger[item].get("calibration_status") != "reject"]
    if not claims:
        claims = [item for item in ledger.values() if item.get("claim_class") not in {"weak_candidate", "calibration_pending"} and item.get("calibration_status") != "reject"][:2]
    primary = claims[0] if claims else {}
    domain = str(primary.get("domain") or "self_growth")
    card_domain, title = DOMAIN_MAP.get(domain, DOMAIN_MAP["self_growth"])
    body = str(primary.get("plain_claim") or "当前最值得观察的是，你怎样把已经形成的能力放进真实选择。")
    examples = list(primary.get("allowed_examples") or [])
    if not examples and len(claims) > 1:
        examples = list(claims[1].get("allowed_examples") or [])
    example = str(examples[0] if examples else "例如先比较投入、责任和长期结果，再决定是否继续推进。")

    structure = _summary(
        baseline.get("natal_portrait"),
        _summary(baseline.get("method_synthesis"), "你的能力由多种结构共同形成，做事时会同时考虑方向、条件与结果。"),
    )
    life_theme = _summary(
        baseline.get("portrait_thesis"),
        "你反复需要把已有能力放进现实关系和长期选择，并让投入逐步形成可以留下的结果。",
    )
    boundary = baseline.get("chart_audit", {}).get("boundary_dependencies") or []
    return {
        "identity": {
            "name": profile.get("name") or None,
            "gender_label": str(profile.get("gender", "")),
            "birth_text": str(profile.get("time", {}).get("input_local_time", "")),
            "birthplace": str(profile.get("birthplace", "")),
            "time_basis_note": str(profile.get("time", {}).get("note", "已按确定性排盘口径处理。")),
        },
        "mingju_analysis": {
            "pillars": _pillars(profile, baseline),
            "structure_text": structure,
            "life_theme_text": life_theme,
            "time_dependency_note": "出生时间接近关键边界，部分现实落点需要结合时间复核。" if boundary else None,
            "confidence": "medium",
            "basis": ["analysis-baseline.portrait_thesis", "analysis-baseline.method_synthesis"],
        },
        "current_issue": {
            "domain": card_domain, "title": title, "body": body, "example": example,
            "basis": [str(primary.get("claim_id", "baseline-current-stage"))],
            "confidence": "high" if primary.get("confidence") == "high" else "medium" if primary else "needs_validation",
        },
        "full_report_hint": {"title": "想看更长的人生轨迹？", "text": "完整版将展开更长时间范围、逐年伏笔与事业、财务、关系之间的传导。"},
        "disclaimers": {
            "trend": "趋势为相对阶段表达，不代表真实金额、职位或事件概率。",
            "general": "内容用于传统文化体验与自我观察，不构成医疗、法律或投资建议。",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--analysis", type=Path, required=True)
    parser.add_argument("--resolved-sources", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        load = lambda path: json.loads(path.read_text(encoding="utf-8"))
        result = build(load(args.profile), load(args.baseline), load(args.analysis), load(args.resolved_sources) if args.resolved_sources else None)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False)); return 1
    print(json.dumps({"status": "ok", "output": str(args.output), "ai_calls": 0}, ensure_ascii=False)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
