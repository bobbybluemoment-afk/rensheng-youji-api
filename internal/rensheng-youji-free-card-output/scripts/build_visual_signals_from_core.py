#!/usr/bin/env python3
"""Deterministically map the frozen Core's 20-year timing semantics to card signals."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


DIRECTION = {
    "support": {"bias": 0.8, "opportunity": 2.4, "cost": 0.8, "realization": 0.8, "durable": 0.20},
    "mixed": {"bias": 0.0, "opportunity": 1.8, "cost": 1.8, "realization": 0.0, "durable": 0.00},
    "pressure": {"bias": -0.8, "opportunity": 0.8, "cost": 2.4, "realization": -0.7, "durable": -0.15},
    "consolidation": {"bias": 0.3, "opportunity": 1.4, "cost": 1.0, "realization": 0.3, "durable": 0.10},
}
INTENSITY = {"low": 0.7, "medium": 1.0, "high": 1.3}
CONFIDENCE = {"high": "high", "medium": "medium", "to_verify": "needs_validation"}


def _baseline(label: str) -> dict[str, Any]:
    return {
        "facts": 0.0, "prior_cycles": 0.0, "natal": 0.0, "social_stage": 0.0,
        "weighted_score": 0.0, "confidence": "medium",
        "basis": [f"校准前冻结Core未提供现实{label}基线，使用中性起点"],
    }


def _impact(year: dict[str, Any], names: set[str]) -> dict[str, Any] | None:
    candidates = [item for item in year.get("domain_impacts") or [] if str(item.get("domain")) in names]
    if not candidates:
        return None
    rank = {"low": 0, "medium": 1, "high": 2}
    return max(candidates, key=lambda item: rank.get(str(item.get("intensity")), -1))


def _numbers(direction: str, intensity: str) -> dict[str, float]:
    base = DIRECTION[direction]
    multiplier = INTENSITY[intensity]
    return {
        "bias": round(base["bias"] * multiplier, 2),
        "opportunity": round(min(4.0, base["opportunity"] * multiplier), 2),
        "cost": round(min(4.0, base["cost"] * multiplier), 2),
        "realization": round(max(-2.0, min(2.0, base["realization"] * multiplier)), 2),
        "durable": round(max(-1.0, min(1.0, base["durable"] * multiplier)), 2),
    }


def build(pack: dict[str, Any]) -> dict[str, Any]:
    center_year = int(pack["center_year"])
    expected = list(range(center_year - 5, center_year + 15))
    context = pack["timing_context"]
    annual = {int(item["year"]): item for item in context.get("annual_theme_activation") or []}
    missing = [year for year in expected if year not in annual]
    if missing:
        raise ValueError(f"冻结Core缺少卡片所需连续20年：{missing}")
    turning_years: set[int] = set()
    for item in context.get("turning_points") or []:
        turning_years.update(int(value) for value in re.findall(r"(?:19|20|21)\d{2}", str(item.get("year_or_range", ""))))

    signals = []
    for year_number in expected:
        year = annual[year_number]
        direction, intensity = str(year["direction"]), str(year["change_intensity"])
        overall = _numbers(direction, intensity)
        career = _impact(year, {"career", "事业", "事业发展"})
        wealth = _impact(year, {"wealth", "finance", "finance_resources", "财富", "财务与资源"})
        relationship = _impact(year, {"relationships", "relationship", "love_partner", "关系", "恋爱与伴侣"})
        learning = _impact(year, {"learning", "growth", "学习", "成长"})
        career_direction = str(career.get("direction")) if career else direction
        career_intensity = str(career.get("intensity")) if career else intensity
        career_values = _numbers(career_direction, career_intensity)
        wealth_values = _numbers(str(wealth.get("direction")), str(wealth.get("intensity"))) if wealth else overall
        relation_values = _numbers(str(relationship.get("direction")), str(relationship.get("intensity"))) if relationship else overall
        learning_values = _numbers(str(learning.get("direction")), str(learning.get("intensity"))) if learning else overall
        activation_strength = min(3, max(0, len(year.get("activation_mechanisms") or [])))
        major_transition = year_number in turning_years or (intensity == "high" and activation_strength >= 2)
        confidence = CONFIDENCE.get(str(year.get("confidence")), "needs_validation")
        career_outcome = {
            "support": "rise", "consolidation": "consolidate", "mixed": "unlanded_change", "pressure": "rebuild",
        }[career_direction]
        basis = [
            f"冻结Core年度主题：{year['year_theme']}",
            f"年度方向与强度：{direction}/{intensity}",
        ]
        signals.append({
            "year": year_number,
            "age": year["age"],
            "theme": year["year_theme"],
            "direction": direction,
            "luck_bias": overall["bias"],
            "stage_target_shift": round(overall["bias"] * 3.0, 2),
            "opportunity": overall["opportunity"],
            "cost": overall["cost"],
            "realization": overall["realization"],
            "durable_shift": overall["durable"],
            "change_intensity": intensity,
            "activation_strength": activation_strength,
            "reversal_level": 1 if direction == "mixed" else 2 if direction == "pressure" and intensity == "high" else 0,
            "major_transition": major_transition,
            "confirmed_major_event": False,
            "career_outcome": career_outcome,
            "career_strength": min(3.0, career_values["opportunity"]),
            "learning_carry": min(2.0, max(0.0, learning_values["realization"] + 0.8)),
            "wealth_inflow": min(3.0, wealth_values["opportunity"]),
            "wealth_outflow": min(3.0, wealth_values["cost"]),
            "resource_restructure": bool(wealth and wealth.get("direction") == "pressure" and wealth.get("intensity") == "high"),
            "relationship_natal_entry": 0.8,
            "relationship_luck_environment": min(2.0, relation_values["opportunity"] * 0.55),
            "relationship_opportunity": relation_values["opportunity"],
            "relationship_carry": min(1.0, max(0.0, relation_values["durable"] + 0.35)),
            "relationship_confirmed_context": 0.0,
            "relationship_conflict_only": bool(relationship and relationship.get("direction") == "pressure"),
            "confidence": confidence,
            "basis": basis,
        })
    return {
        "schema_version": "1.3.0",
        "analysis_id": pack["analysis_id"],
        "center_year": center_year,
        "evidence_mode": "birth_only",
        "window_start_state": {
            "start_year": expected[0],
            "overall": _baseline("整体"),
            "career": _baseline("事业"),
            "wealth": _baseline("财富"),
            "relationship_carry": {
                "strength": 0.0, "type": "latent", "confidence": "medium",
                "basis": ["校准前冻结Core不把现实关系经历作为已确认事实"],
            },
        },
        "annual_visual_signals": signals,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = build(json.loads(args.pack.read_text(encoding="utf-8")))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False)); return 1
    print(json.dumps({"status": "ok", "output": str(args.output), "years": 20}, ensure_ascii=False)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
