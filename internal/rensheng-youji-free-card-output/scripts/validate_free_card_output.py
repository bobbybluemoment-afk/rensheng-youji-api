#!/usr/bin/env python3
"""对 free-card-output.json 做不依赖第三方包的关键规则校验。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def validate(data: dict) -> list[str]:
    errors: list[str] = []
    required = ["schema_version", "source", "identity", "mingju_analysis", "trend_panel", "current_issue", "full_report_hint", "disclaimers"]
    for key in required:
        if key not in data:
            errors.append(f"缺少顶层字段：{key}")
    if errors:
        return errors

    if data["schema_version"] != "1.1.0":
        errors.append("schema_version 必须为1.1.0")

    pillars = data["mingju_analysis"].get("pillars", [])
    if len(pillars) != 4 or any(not isinstance(value, str) or len(value) != 2 for value in pillars):
        errors.append("mingju_analysis.pillars 必须是按年、月、日、时排列的四个干支")

    start_state = data["trend_panel"].get("window_start_state")
    if not isinstance(start_state, dict):
        errors.append("trend_panel.window_start_state 缺失")
    else:
        if start_state.get("evidence_mode") not in {"birth_only", "reality_calibrated"}:
            errors.append("window_start_state.evidence_mode 无效")
        if start_state.get("evidence_mode") == "birth_only":
            if not 42 <= float(start_state.get("overall_index", -999)) <= 58:
                errors.append("birth_only 总体起点应收缩在42—58")
            if not 2.5 <= float(start_state.get("career_level", -999)) <= 4.5:
                errors.append("birth_only 事业起点应收缩在2.5—4.5")
            if not 3 <= int(start_state.get("wealth_ingot_count", -999)) <= 6:
                errors.append("birth_only 财富起点应收缩在3—6枚元宝")

    years = data["trend_panel"].get("years", [])
    if len(years) != 20:
        errors.append("trend_panel.years 必须恰好20年")
    else:
        year_values = [item.get("year") for item in years]
        if year_values != list(range(year_values[0], year_values[0] + 20)):
            errors.append("20个年份必须连续")
        current_positions = [index for index, item in enumerate(years) if item.get("is_current")]
        if current_positions != [5]:
            errors.append("当前年必须且只能位于第6个位置")
        previous_close = None
        previous_career = None
        previous_ingots = None
        for item in years:
            candle = item.get("life_kline", {})
            try:
                low, high = float(candle["low"]), float(candle["high"])
                open_value, close = float(candle["open"]), float(candle["close"])
            except (KeyError, TypeError, ValueError):
                errors.append(f"{item.get('year')} K线字段无效")
                continue
            if not low <= min(open_value, close) <= max(open_value, close) <= high:
                errors.append(f"{item.get('year')} K线高低开收关系无效")
            span = high - low
            body = abs(close - open_value)
            range_limit = 16 if start_state.get("evidence_mode") == "birth_only" else 18
            if span > range_limit + 0.0001:
                errors.append(f"{item.get('year')} 单年跨度超过{range_limit}")
            semantics = item.get("source_semantics", {})
            if semantics.get("reversal_level") == 0:
                wick_total = span - body
                if wick_total > max(2.5, 3 * body) + 0.21:
                    errors.append(f"{item.get('year')} 无明显折返却出现过长影线")
            if previous_close is not None and abs(open_value - previous_close) > 0.11:
                errors.append(f"{item.get('year')} 开盘未承接上一年收盘")
            previous_close = close
            career_level = float(item.get("career", {}).get("level", -999))
            ingots = int(item.get("wealth", {}).get("ingot_count", -999))
            display_ingots = int(item.get("wealth", {}).get("display_ingot_count", -999))
            if previous_career is not None:
                career_limit = 1.5
                if abs(career_level - previous_career) > career_limit + 0.001:
                    errors.append(f"{item.get('year')} 事业台阶变化超过1.5级")
            if previous_ingots is not None and abs(ingots - previous_ingots) > 3:
                errors.append(f"{item.get('year')} 元宝变化超过3枚")
            previous_career = career_level
            previous_ingots = ingots
            if display_ingots != 2 * ingots - 2:
                errors.append(f"{item.get('year')} 元宝显示数量与统一尺度不一致")
            peach = item.get("peach", {})
            if peach.get("highlight"):
                if peach.get("color_role") != "peach_pink":
                    errors.append(f"{item.get('year')} 桃花未使用粉色")
                if peach.get("blossoms") not in {1, 3, 5, 7}:
                    errors.append(f"{item.get('year')} 桃花朵数必须为1、3、5或7")
            elif peach.get("blossoms") != 0 or peach.get("color_role") != "none":
                errors.append(f"{item.get('year')} 未突出桃花时朵数和颜色必须归零")

        render_rules = data["trend_panel"].get("render_rules", {})
        if render_rules.get("wealth_display_count_formula") != "2 * ingot_count - 2":
            errors.append("元宝显示尺度公式未固定")
        if render_rules.get("peach_max_years", "missing") is not None:
            errors.append("桃花不得再设置20年总数量上限")
        if render_rules.get("career_age_stage_adjustment") is not True:
            errors.append("事业年龄阶段修正未启用")
        if render_rules.get("peach_age_stage_adjustment") is not True:
            errors.append("桃花年龄阶段修正未启用")

    issue = data["current_issue"]
    title = str(issue.get("title", ""))
    if not 4 <= len(title) <= 20:
        errors.append("current_issue.title 应为4—20字")
    if issue.get("domain") not in {"career", "wealth", "relationships", "family", "learning", "mobility", "growth"}:
        errors.append("current_issue.domain 无效")
    forbidden = ("换轨", "抓手", "赋能", "内耗", "能量场", "人生副本", "显化")
    rendered_text = json.dumps({"mingju": data["mingju_analysis"], "issue": issue}, ensure_ascii=False)
    for word in forbidden:
        if word in rendered_text:
            errors.append(f"出现禁用黑话：{word}")
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
    print("OK: free card output validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
