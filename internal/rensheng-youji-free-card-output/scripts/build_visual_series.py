#!/usr/bin/env python3
"""把已校验的语义视觉信号确定性映射为四组20年视觉数据。"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


WEIGHTS = {"facts": 0.50, "prior_cycles": 0.30, "natal": 0.15, "social_stage": 0.05}
CONFIDENCE_RANK = {"needs_validation": 0, "medium": 1, "high": 2}
VOLATILITY = {"low": 0.2, "medium": 0.5, "high": 0.8}


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def quantize_half(value: float) -> float:
    return round(value * 2.0) / 2.0


def weighted_score(evidence: dict[str, Any]) -> float:
    return sum(float(evidence[key]) * weight for key, weight in WEIGHTS.items())


def age_growth_factor(age: float) -> float:
    """年龄只提供较弱的正向增速先验，不自动制造涨跌方向。"""
    return 1.0 / (1.0 + math.exp((age - 42.0) / 8.0))


def position_growth_factor(previous_close: float) -> float:
    """当前位置越高，继续抬升略慢；下降不受此项削弱。"""
    return clamp((75.0 - previous_close) / 25.0, 0.0, 1.0)


def ingot_count(level: float) -> int:
    return round(3 + (clamp(level, 1.0, 8.0) - 1.0) * 9.0 / 7.0)


def career_age_factor(age: float) -> float:
    if age <= 24:
        return 1.15
    if age <= 34:
        return 1.08
    if age <= 44:
        return 1.00
    if age <= 54:
        return 0.90
    return 0.85


def career_position_factor(level: float) -> float:
    if level <= 4.0:
        return 1.10
    if level <= 6.0:
        return 1.00
    if level <= 8.0:
        return 0.90
    return 0.80


def career_delta(signal: dict[str, Any], previous_learning: float, current_level: float) -> float:
    outcome = signal["career_outcome"]
    strength = float(signal["career_strength"])
    realization = float(signal["realization"])
    if outcome == "rise":
        delta = clamp(0.45 + 0.12 * strength, 0.5, 0.75)
        if previous_learning >= 1.0 and realization >= 1:
            delta += 0.15
        delta = min(delta, 1.0)
    elif outcome == "consolidate":
        delta = 0.25 if strength >= 2 and realization >= 1 else 0.0
        if delta and previous_learning >= 1.0:
            delta += 0.15
        delta = min(delta, 0.5)
    elif outcome == "unlanded_change":
        delta = 0.0
    elif outcome == "rebuild":
        delta = -0.5
    else:
        delta = -1.0

    if delta > 0:
        delta *= career_age_factor(float(signal["age"]))
        delta *= career_position_factor(current_level)
        if signal["direction"] == "pressure":
            delta = min(delta, 0.5)
    limit = 1.5 if signal["change_intensity"] == "high" and signal["activation_strength"] >= 2 else 1.0
    return clamp(delta, -limit, limit)


def relationship_age_bonus(age: float, annual_opportunity: float) -> float:
    if annual_opportunity < 1.5:
        return 0.0
    if age <= 24:
        return 1.0
    if age <= 34:
        return 0.75
    if age <= 44:
        return 0.5
    return 0.25


def peach_candidates(signals: list[dict[str, Any]]) -> dict[int, float]:
    raw: list[tuple[int, float]] = []
    for signal in signals:
        annual_opportunity = float(signal["relationship_opportunity"])
        score = (
            float(signal["relationship_natal_entry"])
            + float(signal["relationship_luck_environment"])
            + annual_opportunity
            + float(signal["relationship_carry"])
            + float(signal["relationship_confirmed_context"])
            + relationship_age_bonus(float(signal["age"]), annual_opportunity)
        )
        qualifies = (
            annual_opportunity >= 1.5
            and score >= 5.5
            and CONFIDENCE_RANK[signal["confidence"]] >= CONFIDENCE_RANK["medium"]
            and not signal["relationship_conflict_only"]
        )
        raw.append((int(signal["year"]), score if qualifies else 0.0))

    selected = raw[:]
    for index in range(1, len(raw)):
        previous_year, previous_score = raw[index - 1]
        year, score = raw[index]
        if previous_score and score and not (previous_score >= 7 and score >= 7):
            if score > previous_score:
                selected[index - 1] = (previous_year, 0.0)
            else:
                selected[index] = (year, 0.0)
    return {year: score for year, score in selected if score}


def build(data: dict[str, Any]) -> dict[str, Any]:
    center_year = int(data["center_year"])
    expected = list(range(center_year - 5, center_year + 15))
    signals = sorted(data["annual_visual_signals"], key=lambda item: item["year"])
    actual = [int(item["year"]) for item in signals]
    if actual != expected:
        raise ValueError(f"年度范围必须是 {expected[0]}—{expected[-1]} 且连续，实际为 {actual}")

    start = data["window_start_state"]
    if int(start["start_year"]) != expected[0]:
        raise ValueError("window_start_state.start_year 必须等于窗口第一年")

    overall_b = weighted_score(start["overall"])
    career_b = weighted_score(start["career"])
    wealth_b = weighted_score(start["wealth"])
    kline_baseline = clamp(50.0 + 8.0 * overall_b, 32.0, 68.0)
    career_baseline = quantize_half(clamp(3.5 + 1.25 * career_b, 1.0, 6.0))
    wealth_baseline = clamp(4.5 + 2.0 * wealth_b, 1.0, 8.0)

    if data["evidence_mode"] == "birth_only":
        kline_baseline = clamp(kline_baseline, 42.0, 58.0)
        career_baseline = clamp(career_baseline, 2.5, 4.5)
        # 无现实资产资料时，只画3—6枚元宝的保守起点。
        wealth_baseline = clamp(2.30 + 0.80 * wealth_b, 1.0, 3.33)

    highlighted_peach = peach_candidates(signals)
    years: list[dict[str, Any]] = []
    previous_close = kline_baseline
    previous_delta = 0.0
    durable_offset = 0.0
    career_hidden_level = career_baseline
    previous_career_delta = 0.0
    previous_learning = 0.0
    wealth_level = wealth_baseline
    previous_ingots = ingot_count(wealth_level)

    for signal in signals:
        year = int(signal["year"])
        opportunity = float(signal["opportunity"])
        cost = float(signal["cost"])
        realization = float(signal["realization"])
        luck_bias = float(signal["luck_bias"])
        stage_target_shift = float(signal["stage_target_shift"])
        durable_shift = float(signal["durable_shift"])
        age_factor = age_growth_factor(float(signal["age"]))
        position_factor = position_growth_factor(previous_close)
        growth_multiplier = 0.65 + 0.20 * age_factor + 0.15 * position_factor

        # 大运先给出阶段目标，流年再执行；长期留存只对目标作累积修正。
        durable_delta = 0.80 * durable_shift
        if durable_delta > 0:
            durable_delta *= growth_multiplier
        durable_offset = clamp(durable_offset + durable_delta, -8.0, 8.0)

        stage_target = clamp(kline_baseline + stage_target_shift + durable_offset, 24.0, 82.0)
        annual_execution = 1.50 * luck_bias + (opportunity - cost) + realization
        annual_target = clamp(stage_target + annual_execution, 20.0, 86.0)
        gap = annual_target - previous_close
        if gap > 0:
            gap *= growth_multiplier
        raw_delta = 0.25 * previous_delta + 0.35 * gap
        strong_transition = signal["change_intensity"] == "high" and (
            signal["activation_strength"] >= 2 or signal["major_transition"]
        )
        close_limit = 5.0 if signal["confirmed_major_event"] else 4.0 if strong_transition else 3.0
        delta = clamp(raw_delta, -close_limit, close_limit)
        open_value = previous_close
        close_value = clamp(open_value + delta, 24.0, 82.0)

        body = abs(close_value - open_value)
        friction = min(opportunity, cost) / 4.0
        activation = float(signal["activation_strength"]) / 3.0
        reversal = float(signal["reversal_level"]) / 2.0
        wick_total = 1.5 + 2.0 * VOLATILITY[signal["change_intensity"]]
        wick_total += 1.5 * friction + activation + 2.0 * reversal
        if signal["major_transition"]:
            wick_total += 1.0
        if signal["confirmed_major_event"]:
            wick_total += 1.5
        if signal["reversal_level"] == 0:
            wick_total = min(wick_total, max(2.2, 2.5 * body))
        range_limit = 16.0 if data["evidence_mode"] == "birth_only" else 18.0
        total_range = clamp(body + wick_total, max(2.5, body + 1.5), range_limit)
        remaining = total_range - body
        upper_share = (opportunity + 0.5) / (opportunity + cost + 1.0)
        upper = remaining * upper_share
        lower = remaining - upper
        high_value = max(open_value, close_value) + upper
        low_value = min(open_value, close_value) - lower
        if high_value > 100.0:
            shift = high_value - 100.0
            high_value -= shift
            low_value -= shift
        if low_value < 0.0:
            shift = -low_value
            high_value += shift
            low_value += shift

        current_career_delta = career_delta(signal, previous_learning, career_hidden_level)
        career_hidden_level = clamp(career_hidden_level + current_career_delta, 1.0, 9.0)
        career_level = quantize_half(career_hidden_level)

        inflow = 0.45 * float(signal["wealth_inflow"])
        outflow = 0.45 * float(signal["wealth_outflow"])
        career_lag = 0.20 * max(previous_career_delta, 0.0)
        next_wealth = 0.90 * wealth_level + 0.10 * wealth_baseline + inflow - outflow + career_lag
        next_wealth = clamp(next_wealth, 1.0, 8.0)
        next_ingots = ingot_count(next_wealth)
        ingot_limit = 3 if signal["resource_restructure"] else 2
        next_ingots = int(clamp(next_ingots, previous_ingots - ingot_limit, previous_ingots + ingot_limit))
        wealth_level = 1.0 + (next_ingots - 3) * 7.0 / 9.0

        peach_score = highlighted_peach.get(year, 0.0)
        blossoms = 7 if peach_score >= 8 else 5 if peach_score >= 7 else 3 if peach_score >= 6.25 else 1 if peach_score >= 5.5 else 0
        display_ingots = 2 * next_ingots - 2
        years.append({
            "year": year,
            "age": signal["age"],
            "is_current": year == center_year,
            "life_kline": {
                "open": round(open_value, 1),
                "close": round(close_value, 1),
                "high": round(high_value, 1),
                "low": round(low_value, 1),
            },
            "career": {"level": career_level, "label": "步步高升"},
            "wealth": {
                "level": round(wealth_level, 1),
                "ingot_count": next_ingots,
                "display_ingot_count": display_ingots,
            },
            "peach": {
                "highlight": bool(blossoms),
                "blossoms": blossoms,
                "color_role": "peach_pink" if blossoms else "none",
            },
            "source_semantics": {
                "theme": signal["theme"],
                "direction": signal["direction"],
                "intensity": signal["change_intensity"],
                "activation_strength": signal["activation_strength"],
                "reversal_level": signal["reversal_level"],
                "major_transition": signal["major_transition"],
                "stage_target_shift": stage_target_shift,
                "durable_offset": round(durable_offset, 2),
                "stage_target": round(stage_target, 2),
                "annual_target": round(annual_target, 2),
                "age_growth_factor": round(age_factor, 3),
                "position_growth_factor": round(position_factor, 3),
                "growth_multiplier": round(growth_multiplier, 3),
                "durable_shift": durable_shift,
                "career_hidden_level": round(career_hidden_level, 2),
                "career_age_factor": career_age_factor(float(signal["age"])),
                "relationship_display_score": round(peach_score, 2),
                "confidence": signal["confidence"],
            },
        })
        previous_close = close_value
        previous_delta = close_value - open_value
        previous_career_delta = current_career_delta
        previous_learning = float(signal["learning_carry"])
        previous_ingots = next_ingots

    return {
        "window": {"start_year": expected[0], "center_year": center_year, "end_year": expected[-1]},
        "window_start_state": {
            "evidence_mode": data["evidence_mode"],
            "overall_index": round(kline_baseline, 1),
            "career_level": career_baseline,
            "wealth_level": round(wealth_baseline, 1),
            "wealth_ingot_count": ingot_count(wealth_baseline),
            "relationship_carry": start["relationship_carry"],
            "confidence": {
                "overall": start["overall"]["confidence"],
                "career": start["career"]["confidence"],
                "wealth": start["wealth"]["confidence"],
            },
        },
        "years": years,
        "render_rules": {
            "kline_connected": True,
            "kline_equal_body_width": True,
            "kline_birth_only_max_range": 16,
            "kline_calibrated_max_range": 18,
            "long_wick_requires_reversal": True,
            "show_five_year_backgrounds": False,
            "career_hollow_steps": True,
            "career_steps_separated_by_year": True,
            "wealth_ingots_only": True,
            "wealth_top_line": False,
            "wealth_ingot_scale": 0.62,
            "wealth_display_count_formula": "2 * ingot_count - 2",
            "peach_sparse": True,
            "peach_max_years": None,
            "peach_age_stage_adjustment": True,
            "career_age_stage_adjustment": True,
            "current_peach_stays_pink": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("visual_signals", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        data = json.loads(args.visual_signals.read_text(encoding="utf-8"))
        result = build(data)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "ok", "output": str(args.output), "years": 20}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
