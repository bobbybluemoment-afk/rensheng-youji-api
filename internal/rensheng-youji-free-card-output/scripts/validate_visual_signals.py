#!/usr/bin/env python3
"""校验视觉信号的关键范围、起点权重与20年连续性。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


WEIGHTS = {"facts": 0.50, "prior_cycles": 0.30, "natal": 0.15, "social_stage": 0.05}
CONFIDENCE = {"high", "medium", "needs_validation"}
OUTCOMES = {"rise", "consolidate", "unlanded_change", "rebuild", "interruption"}


def in_range(value: object, low: float, high: float) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and low <= float(value) <= high


def validate(data: dict) -> list[str]:
    errors: list[str] = []
    required = ["schema_version", "analysis_id", "center_year", "evidence_mode", "window_start_state", "annual_visual_signals"]
    for key in required:
        if key not in data:
            errors.append(f"缺少顶层字段：{key}")
    if errors:
        return errors
    if data["schema_version"] != "1.3.0":
        errors.append("schema_version 必须为1.3.0")
    if data["evidence_mode"] not in {"birth_only", "reality_calibrated"}:
        errors.append("evidence_mode 无效")

    center = data["center_year"]
    start = data["window_start_state"]
    if start.get("start_year") != center - 5:
        errors.append("窗口起点必须是当前年前5年")
    for domain in ("overall", "career", "wealth"):
        evidence = start.get(domain, {})
        for key in WEIGHTS:
            if not in_range(evidence.get(key), -2, 2):
                errors.append(f"{domain}.{key} 必须在-2—2")
        if all(in_range(evidence.get(key), -2, 2) for key in WEIGHTS):
            calculated = sum(float(evidence[key]) * weight for key, weight in WEIGHTS.items())
            if not in_range(evidence.get("weighted_score"), -2, 2) or abs(float(evidence["weighted_score"]) - calculated) > 0.011:
                errors.append(f"{domain}.weighted_score 与统一权重不一致，应为{calculated:.2f}")
        if evidence.get("confidence") not in CONFIDENCE:
            errors.append(f"{domain}.confidence 无效")
        if not evidence.get("basis"):
            errors.append(f"{domain}.basis 不得为空")

    carry = start.get("relationship_carry", {})
    if not in_range(carry.get("strength"), 0, 1):
        errors.append("relationship_carry.strength 必须在0—1")
    if carry.get("type") not in {"none", "latent", "active", "recovery"}:
        errors.append("relationship_carry.type 无效")

    signals = data["annual_visual_signals"]
    if not isinstance(signals, list) or len(signals) != 20:
        errors.append("annual_visual_signals 必须恰好20条")
        return errors
    years = [item.get("year") for item in signals]
    expected = list(range(center - 5, center + 15))
    if years != expected:
        errors.append(f"年度必须按{expected[0]}—{expected[-1]}连续排列")

    ranges = {
        "luck_bias": (-2, 2), "stage_target_shift": (-15, 15), "opportunity": (0, 4), "cost": (0, 4), "realization": (-2, 2), "durable_shift": (-1, 1),
        "career_strength": (0, 3), "learning_carry": (0, 2), "wealth_inflow": (0, 3), "wealth_outflow": (0, 3),
        "relationship_natal_entry": (0, 2), "relationship_luck_environment": (0, 2),
        "relationship_opportunity": (0, 4), "relationship_carry": (0, 1), "relationship_confirmed_context": (0, 1),
    }
    for item in signals:
        year = item.get("year")
        for key, (low, high) in ranges.items():
            if not in_range(item.get(key), low, high):
                errors.append(f"{year}.{key} 必须在{low}—{high}")
        if item.get("direction") not in {"support", "mixed", "pressure", "consolidation"}:
            errors.append(f"{year}.direction 无效")
        if item.get("change_intensity") not in {"low", "medium", "high"}:
            errors.append(f"{year}.change_intensity 无效")
        if not isinstance(item.get("activation_strength"), int) or not 0 <= item["activation_strength"] <= 3:
            errors.append(f"{year}.activation_strength 必须是0—3的整数")
        if not isinstance(item.get("reversal_level"), int) or not 0 <= item["reversal_level"] <= 2:
            errors.append(f"{year}.reversal_level 必须是0—2的整数")
        if item.get("career_outcome") not in OUTCOMES:
            errors.append(f"{year}.career_outcome 无效")
        if item.get("confidence") not in CONFIDENCE:
            errors.append(f"{year}.confidence 无效")
        if not item.get("basis"):
            errors.append(f"{year}.basis 不得为空")
        for key in ("major_transition", "confirmed_major_event", "resource_restructure", "relationship_conflict_only"):
            if not isinstance(item.get(key), bool):
                errors.append(f"{year}.{key} 必须是布尔值")
        if data["evidence_mode"] == "birth_only" and item.get("confirmed_major_event"):
            errors.append(f"{year} birth_only 模式不得确认重大现实事件")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 1
    errors = validate(data)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("OK: visual signals validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
