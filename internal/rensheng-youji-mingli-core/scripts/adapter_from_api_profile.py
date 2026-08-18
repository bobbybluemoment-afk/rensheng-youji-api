#!/usr/bin/env python3
"""Convert rensheng-youji-api build_profile output into core analysis input."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from _jsonschema_subset import validate_schema_instance
from validate_analysis_input import SCHEMA_PATH, load_json, validate


STEM_ELEMENT = {
    "甲": "wood", "乙": "wood", "丙": "fire", "丁": "fire", "戊": "earth",
    "己": "earth", "庚": "metal", "辛": "metal", "壬": "water", "癸": "water",
}
STEM_YANG = {"甲", "丙", "戊", "庚", "壬"}
GENERATES = {"wood": "fire", "fire": "earth", "earth": "metal", "metal": "water", "water": "wood"}
CONTROLS = {"wood": "earth", "earth": "water", "water": "fire", "fire": "metal", "metal": "wood"}
HIDDEN_STEMS = {
    "子": ["癸"], "丑": ["己", "癸", "辛"], "寅": ["甲", "丙", "戊"],
    "卯": ["乙"], "辰": ["戊", "乙", "癸"], "巳": ["丙", "庚", "戊"],
    "午": ["丁", "己"], "未": ["己", "丁", "乙"], "申": ["庚", "壬", "戊"],
    "酉": ["辛"], "戌": ["戊", "辛", "丁"], "亥": ["壬", "甲"],
}


def ten_god(day_master: str, other: str) -> str:
    dm_element = STEM_ELEMENT[day_master]
    other_element = STEM_ELEMENT[other]
    same_polarity = (day_master in STEM_YANG) == (other in STEM_YANG)
    if dm_element == other_element:
        return "比肩" if same_polarity else "劫财"
    if GENERATES[dm_element] == other_element:
        return "食神" if same_polarity else "伤官"
    if CONTROLS[dm_element] == other_element:
        return "偏财" if same_polarity else "正财"
    if CONTROLS[other_element] == dm_element:
        return "七杀" if same_polarity else "正官"
    if GENERATES[other_element] == dm_element:
        return "偏印" if same_polarity else "正印"
    raise ValueError(f"无法计算十神：{day_master}/{other}")


def hidden_stem_records(branch: str, day_master: str) -> list[dict[str, str]]:
    stems = HIDDEN_STEMS[branch]
    levels = ["main", "middle", "residual"][:len(stems)]
    return [
        {"stem": stem, "qi_level": level, "ten_god": ten_god(day_master, stem)}
        for stem, level in zip(stems, levels)
    ]


def parse_pillar(value: str) -> tuple[str, str]:
    if not isinstance(value, str) or len(value) != 2:
        raise ValueError(f"干支格式无效：{value!r}")
    return value[0], value[1]


def iso_local(value: str, timezone_name: str) -> str:
    parsed = datetime.strptime(value, "%Y-%m-%d %H:%M")
    return parsed.replace(tzinfo=ZoneInfo(timezone_name)).isoformat()


def boundary_flags(profile: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    time_info = profile["time"]
    true_solar = datetime.strptime(time_info["true_solar_time"], "%Y-%m-%d %H:%M")
    # 地支时辰边界位于奇数整点；20分钟内标记为敏感，不擅自改柱。
    distance = min(abs(true_solar.minute), abs(60 - true_solar.minute))
    if true_solar.hour % 2 == 1 and distance <= 20:
        flags.append("hour_branch_boundary")
    if abs(float(time_info.get("correction_minutes", 0))) >= 10:
        flags.append("true_solar_time_sensitive")
    return flags or ["none"]


def adapt_profile(
    profile: dict[str, Any],
    *,
    analysis_as_of: str,
    request_id: str | None = None,
    latitude: float | None = None,
) -> dict[str, Any]:
    bazi = profile["bazi"]
    time_info = profile["time"]
    day_master = bazi["day_master"]
    timezone_name = time_info.get("timezone", "Asia/Shanghai")
    local_birth = time_info["input_local_time"]
    birth_year = int(local_birth[:4])
    timeline = profile["life_kline"]["timeline"]
    start_year = min(item["year"] for item in timeline)
    end_year = max(item["year"] for item in timeline)
    if request_id is None:
        digest = hashlib.sha256(f"{local_birth}|{profile.get('birthplace')}|{profile.get('gender')}|{start_year}|{end_year}".encode()).hexdigest()[:12]
        request_id = f"rsy-{digest}"

    pillar_details: dict[str, Any] = {}
    for item in bazi["analysis_context"]["pillars"]:
        position = "hour" if item["position"] == "time" else item["position"]
        hidden = [
            {"stem": stem, "qi_level": ["main", "middle", "residual"][index], "ten_god": item["hidden_ten_gods"][index]}
            for index, stem in enumerate(item["hidden_stems"])
        ]
        pillar_details[position] = {
            "stem": item["stem"],
            "branch": item["branch"],
            "stem_ten_god": "日主" if position == "day" else item["stem_ten_god"],
            "hidden_stems": hidden,
        }

    start_time = datetime.strptime(bazi["luck_start_local_time"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZoneInfo(timezone_name))
    luck_cycles: list[dict[str, Any]] = []
    for index, item in enumerate(bazi["da_yun"], start=1):
        stem, branch = parse_pillar(item["pillar"])
        cycle_start = start_time.replace(year=start_time.year + (index - 1) * 10)
        cycle_end = cycle_start.replace(year=cycle_start.year + 10)
        luck_cycles.append({
            "index": index,
            "stem": stem,
            "branch": branch,
            "stem_ten_god": ten_god(day_master, stem),
            "hidden_stems": hidden_stem_records(branch, day_master),
            "start_datetime": cycle_start.isoformat(),
            "end_datetime": cycle_end.isoformat(),
            "start_age": item["start_age"],
            "end_age": item["end_age"],
        })

    annual_cycles: list[dict[str, Any]] = []
    for item in timeline:
        stem, branch = parse_pillar(item["ganzhi"])
        cycle = next(
            (
                cycle
                for cycle in luck_cycles
                if bazi["da_yun"][cycle["index"] - 1]["start_year"]
                <= item["year"]
                <= bazi["da_yun"][cycle["index"] - 1]["end_year"]
            ),
            None,
        )
        annual_cycles.append({
            "year": item["year"],
            "age": item["year"] - birth_year,
            "stem": stem,
            "branch": branch,
            "stem_ten_god": ten_god(day_master, stem),
            "hidden_stems": hidden_stem_records(branch, day_master),
            "luck_cycle_index": cycle["index"] if cycle else None,
        })

    place_parts = str(profile.get("birthplace", "中国·未提供")).split("·", 1)
    country = place_parts[0] or "中国"
    place = place_parts[1] if len(place_parts) > 1 else place_parts[0]
    offset = bazi["luck_start_offset"]
    start_age = offset["years"] + offset["months"] / 12 + offset["days"] / 365 + offset["hours"] / 8760

    return {
        "request": {
            "request_id": request_id,
            "analysis_as_of": analysis_as_of,
            "locale": "zh-CN",
            "calendar_basis": "local_civil" if time_info.get("time_basis") == "local_civil" else "true_solar_time",
            "target_range": {"start_year": start_year, "end_year": end_year},
            "include_monthly": False,
            "source": "rensheng-youji-api/build_profile",
        },
        "person": {
            "name": profile.get("name") or None,
            "gender": "male" if profile.get("gender") == "男" else "female",
            "gender_label": profile.get("gender"),
            "birth": {
                "local_datetime": iso_local(local_birth, timezone_name),
                "place_name": place,
                "country_or_region": country,
                "timezone": timezone_name,
                "latitude": latitude,
                "longitude": float(time_info["longitude"]),
                "time_source": "unknown",
                "time_precision": "minute",
                "raw_input": local_birth,
            },
        },
        "chart": {
            "day_master": day_master,
            "pillars": pillar_details,
            "nayin": None,
            "calculation_engine": "rensheng-youji-api/lunar_python",
            "calculation_version": str(profile.get("version")),
        },
        "solar_terms_and_boundaries": {
            "timezone_resolved": timezone_name,
            "utc_offset": f"{float(time_info.get('utc_offset_hours', 8)):+.1f}",
            "daylight_saving_applied": False,
            "true_solar_time_applied": time_info.get("time_basis") == "local_civil",
            "true_solar_datetime": iso_local(time_info["true_solar_time"], timezone_name),
            "nearest_solar_terms": [],
            "boundary_flags": boundary_flags(profile),
            "notes": list(profile.get("warnings", [])) + ["现有 API profile 未暴露邻近节气精确时间；由 chart_audit 保留此项。"],
        },
        "five_elements": None,
        "luck_cycles": {
            "direction": "forward" if bazi["luck_direction"] == "forward" else "backward",
            "start_age": round(start_age, 4),
            "start_datetime": start_time.isoformat(),
            "method": "lunar_python EightChar.getYun",
            "cycles": luck_cycles,
        },
        "annual_cycles": annual_cycles,
        "monthly_cycles": None,
        "reality_context": {
            "facts": [],
            "questions": [],
            "current_location": None,
            "occupation": None,
            "education": None,
            "relationship_status": None,
            "family_stage": None,
        },
        "calibration": {
            "candidate_feedback": [],
            "confirmed_events": [],
            "rejected_claims": [],
            "notes": [],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="把 rensheng-youji-api profile 转为 Core 输入")
    parser.add_argument("profile_json", type=Path)
    parser.add_argument("--analysis-as-of", required=True)
    parser.add_argument("--request-id")
    parser.add_argument("--latitude", type=float)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    profile = load_json(args.profile_json)
    result = adapt_profile(profile, analysis_as_of=args.analysis_as_of, request_id=args.request_id, latitude=args.latitude)
    schema = load_json(SCHEMA_PATH)
    errors = validate_schema_instance(result, schema)
    errors.extend(validate(result))
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
