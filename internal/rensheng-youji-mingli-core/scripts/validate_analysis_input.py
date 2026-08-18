#!/usr/bin/env python3
"""Validate deterministic input for the internal Rensheng Youji analysis core."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from _jsonschema_subset import validate_schema_instance


ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "schemas" / "analysis-input.schema.json"
TOP_LEVEL_KEYS = {
    "request",
    "person",
    "chart",
    "solar_terms_and_boundaries",
    "five_elements",
    "luck_cycles",
    "annual_cycles",
    "monthly_cycles",
    "reality_context",
    "calibration",
}
REQUIRED_TOP_LEVEL_KEYS = TOP_LEVEL_KEYS - {"monthly_cycles"}
PILLARS = ("year", "month", "day", "hour")
QI_LEVELS = {"main", "middle", "residual"}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def require_keys(value: Any, keys: set[str], path: str, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{path} 必须是对象")
        return
    for key in sorted(keys - value.keys()):
        errors.append(f"{path}.{key} 缺失")


def check_iso(value: Any, path: str, errors: list[str], date_only: bool = False) -> None:
    if not isinstance(value, str):
        errors.append(f"{path} 必须是字符串")
        return
    try:
        if date_only:
            datetime.strptime(value, "%Y-%m-%d")
        else:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{path} 不是有效的 ISO {'日期' if date_only else '日期时间'}")


def check_hidden_stems(value: Any, path: str, errors: list[str]) -> None:
    if not isinstance(value, list) or not 1 <= len(value) <= 3:
        errors.append(f"{path} 必须包含 1—3 个藏干")
        return
    levels: list[str] = []
    for index, item in enumerate(value):
        item_path = f"{path}[{index}]"
        require_keys(item, {"stem", "qi_level", "ten_god"}, item_path, errors)
        if not isinstance(item, dict):
            continue
        level = item.get("qi_level")
        if level not in QI_LEVELS:
            errors.append(f"{item_path}.qi_level 必须是 main/middle/residual")
        else:
            levels.append(level)
    if levels and levels[0] != "main":
        errors.append(f"{path} 第一项必须是主气 main")
    if len(levels) != len(set(levels)):
        errors.append(f"{path} 的主气/中气/余气层级不能重复")


def validate(data: Any) -> list[str]:
    errors: list[str] = []
    require_keys(data, REQUIRED_TOP_LEVEL_KEYS, "$", errors)
    if not isinstance(data, dict):
        return errors

    unknown = set(data) - TOP_LEVEL_KEYS
    if unknown:
        errors.append(f"$ 包含未定义字段：{', '.join(sorted(unknown))}")

    request = data.get("request")
    require_keys(request, {"request_id", "analysis_as_of", "locale", "calendar_basis", "target_range"}, "request", errors)
    if isinstance(request, dict):
        check_iso(request.get("analysis_as_of"), "request.analysis_as_of", errors, date_only=True)
        target = request.get("target_range")
        require_keys(target, {"start_year", "end_year"}, "request.target_range", errors)
        if isinstance(target, dict):
            start, end = target.get("start_year"), target.get("end_year")
            if not isinstance(start, int) or not isinstance(end, int):
                errors.append("request.target_range 年份必须是整数")
            elif start > end:
                errors.append("request.target_range.start_year 不能晚于 end_year")

    person = data.get("person")
    require_keys(person, {"name", "gender", "birth"}, "person", errors)
    if isinstance(person, dict):
        birth = person.get("birth")
        require_keys(
            birth,
            {"local_datetime", "place_name", "country_or_region", "timezone", "longitude", "time_source", "time_precision"},
            "person.birth",
            errors,
        )
        if isinstance(birth, dict):
            check_iso(birth.get("local_datetime"), "person.birth.local_datetime", errors)
            lat, lon = birth.get("latitude"), birth.get("longitude")
            if lat is not None and (not isinstance(lat, (int, float)) or not -90 <= lat <= 90):
                errors.append("person.birth.latitude 必须在 -90 到 90 之间")
            if not isinstance(lon, (int, float)) or not -180 <= lon <= 180:
                errors.append("person.birth.longitude 必须在 -180 到 180 之间")

    chart = data.get("chart")
    require_keys(chart, {"day_master", "pillars"}, "chart", errors)
    if isinstance(chart, dict):
        pillars = chart.get("pillars")
        require_keys(pillars, set(PILLARS), "chart.pillars", errors)
        if isinstance(pillars, dict):
            for pillar_name in PILLARS:
                pillar = pillars.get(pillar_name)
                path = f"chart.pillars.{pillar_name}"
                require_keys(pillar, {"stem", "branch", "stem_ten_god", "hidden_stems"}, path, errors)
                if isinstance(pillar, dict):
                    check_hidden_stems(pillar.get("hidden_stems"), f"{path}.hidden_stems", errors)
            day = pillars.get("day")
            if isinstance(day, dict) and chart.get("day_master") != day.get("stem"):
                errors.append("chart.day_master 必须与日柱天干一致")

    boundaries = data.get("solar_terms_and_boundaries")
    require_keys(
        boundaries,
        {"timezone_resolved", "daylight_saving_applied", "true_solar_time_applied", "nearest_solar_terms", "boundary_flags"},
        "solar_terms_and_boundaries",
        errors,
    )

    elements = data.get("five_elements")
    if elements is not None:
        require_keys(elements, {"method", "method_version", "scores", "normalized_percentages"}, "five_elements", errors)
        if isinstance(elements, dict) and isinstance(elements.get("normalized_percentages"), dict):
            values = elements["normalized_percentages"]
            required_elements = {"wood", "fire", "earth", "metal", "water"}
            require_keys(values, required_elements, "five_elements.normalized_percentages", errors)
            if all(isinstance(values.get(key), (int, float)) for key in required_elements):
                total = sum(values[key] for key in required_elements)
                if abs(total - 100) > 0.5:
                    errors.append(f"five_elements.normalized_percentages 合计应接近 100，当前为 {total}")

    luck = data.get("luck_cycles")
    require_keys(luck, {"direction", "start_age", "start_datetime", "method", "cycles"}, "luck_cycles", errors)
    if isinstance(luck, dict):
        check_iso(luck.get("start_datetime"), "luck_cycles.start_datetime", errors)
        cycles = luck.get("cycles")
        if not isinstance(cycles, list) or not cycles:
            errors.append("luck_cycles.cycles 至少包含一项")
        else:
            indexes: list[int] = []
            for index, cycle in enumerate(cycles):
                path = f"luck_cycles.cycles[{index}]"
                require_keys(cycle, {"index", "stem", "branch", "stem_ten_god", "hidden_stems", "start_datetime", "end_datetime", "start_age", "end_age"}, path, errors)
                if isinstance(cycle, dict):
                    check_hidden_stems(cycle.get("hidden_stems"), f"{path}.hidden_stems", errors)
                    check_iso(cycle.get("start_datetime"), f"{path}.start_datetime", errors)
                    check_iso(cycle.get("end_datetime"), f"{path}.end_datetime", errors)
                    if isinstance(cycle.get("index"), int):
                        indexes.append(cycle["index"])
            if len(indexes) != len(set(indexes)):
                errors.append("luck_cycles.cycles.index 不能重复")

    annuals = data.get("annual_cycles")
    if not isinstance(annuals, list) or not annuals:
        errors.append("annual_cycles 至少包含一项")
    else:
        years: list[int] = []
        for index, annual in enumerate(annuals):
            path = f"annual_cycles[{index}]"
            require_keys(annual, {"year", "age", "stem", "branch", "stem_ten_god", "hidden_stems", "luck_cycle_index"}, path, errors)
            if isinstance(annual, dict):
                check_hidden_stems(annual.get("hidden_stems"), f"{path}.hidden_stems", errors)
                if isinstance(annual.get("year"), int):
                    years.append(annual["year"])
        if len(years) != len(set(years)):
            errors.append("annual_cycles.year 不能重复")
        if isinstance(request, dict) and isinstance(request.get("target_range"), dict):
            start = request["target_range"].get("start_year")
            end = request["target_range"].get("end_year")
            if isinstance(start, int) and isinstance(end, int):
                missing_years = sorted(set(range(start, end + 1)) - set(years))
                if missing_years:
                    errors.append(f"annual_cycles 缺少目标年份：{missing_years}")

    require_keys(data.get("reality_context"), {"facts", "questions"}, "reality_context", errors)
    require_keys(data.get("calibration"), {"candidate_feedback", "confirmed_events", "rejected_claims"}, "calibration", errors)
    return errors


def self_test_fixture() -> dict[str, Any]:
    hidden = [{"stem": "甲", "qi_level": "main", "ten_god": "比肩"}]
    pillar = {"stem": "甲", "branch": "寅", "stem_ten_god": "比肩", "hidden_stems": hidden}
    day_pillar = {**pillar, "stem_ten_god": "日主"}
    data = {
        "request": {"request_id": "self-test", "analysis_as_of": "2026-08-18", "locale": "zh-CN", "calendar_basis": "local_civil", "target_range": {"start_year": 2026, "end_year": 2026}},
        "person": {"name": None, "gender": "unspecified", "birth": {"local_datetime": "1990-01-01T12:00:00+08:00", "place_name": "测试城市", "country_or_region": "中国", "timezone": "Asia/Shanghai", "latitude": 30.0, "longitude": 120.0, "time_source": "unknown", "time_precision": "minute"}},
        "chart": {"day_master": "甲", "pillars": {"year": pillar, "month": pillar, "day": day_pillar, "hour": pillar}, "calculation_engine": "self-test"},
        "solar_terms_and_boundaries": {"timezone_resolved": "Asia/Shanghai", "daylight_saving_applied": False, "true_solar_time_applied": False, "nearest_solar_terms": [], "boundary_flags": ["none"]},
        "five_elements": None,
        "luck_cycles": {"direction": "forward", "start_age": 5, "start_datetime": "1995-01-01T00:00:00+08:00", "method": "self-test", "cycles": [{"index": 0, "stem": "甲", "branch": "寅", "stem_ten_god": "比肩", "hidden_stems": hidden, "start_datetime": "1995-01-01T00:00:00+08:00", "end_datetime": "2004-12-31T23:59:59+08:00", "start_age": 5, "end_age": 14}]},
        "annual_cycles": [{"year": 2026, "age": 36, "stem": "甲", "branch": "寅", "stem_ten_god": "比肩", "hidden_stems": hidden, "luck_cycle_index": 0}],
        "reality_context": {"facts": [], "questions": []},
        "calibration": {"candidate_feedback": [], "confirmed_events": [], "rejected_claims": []}
    }
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="校验人生有迹内置分析输入 JSON")
    parser.add_argument("json_file", nargs="?", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    try:
        schema = load_json(SCHEMA_PATH)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Schema 无法读取：{exc}", file=sys.stderr)
        return 2
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        print("Schema 版本不是 JSON Schema 2020-12", file=sys.stderr)
        return 2

    if args.self_test:
        data = self_test_fixture()
        errors = validate_schema_instance(data, schema)
        errors.extend(validate(data))
    elif args.json_file:
        try:
            data = load_json(args.json_file)
            errors = validate_schema_instance(data, schema)
            errors.extend(validate(data))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"输入 JSON 无法读取：{exc}", file=sys.stderr)
            return 2
    else:
        parser.error("请提供 json_file 或 --self-test")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("OK: analysis input validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
