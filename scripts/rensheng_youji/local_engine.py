"""把出生资料转换为免费卡片数据并在本地出图。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from .analysis import generate_card_copy
from .bazi import calculate_bazi
from .life_kline import build_kline_result
from .render_card import render_card
from .roles import ROLES
from .solar_time import adjust_to_true_solar, resolve_location


def build_profile(
    *,
    name: str,
    birth: str,
    gender: str,
    city: str,
    country: str = "中国",
    time_basis: str = "local_civil",
    longitude: float | None = None,
    timezone: str | None = None,
    center_year: int | None = None,
) -> dict[str, Any]:
    if gender not in {"male", "female"}:
        raise ValueError("gender 必须是 male 或 female")
    if time_basis not in {"local_civil", "true_solar_adjusted"}:
        raise ValueError("time_basis 必须是 local_civil 或 true_solar_adjusted")
    try:
        input_time = datetime.strptime(birth.strip().replace("T", " "), "%Y-%m-%d %H:%M")
    except ValueError as exc:
        raise ValueError("birth 必须使用 YYYY-MM-DD HH:MM 格式") from exc

    warnings: list[str] = []
    birthplace = f"{country}·{city}"
    if time_basis == "true_solar_adjusted":
        final_time = input_time
        time_info = {
            "input_local_time": birth,
            "time_basis": time_basis,
            "true_solar_time": birth,
            "correction_minutes": 0.0,
            "note": "输入时间已由用户校正为真太阳时，本地引擎未重复校正。",
        }
    else:
        location = resolve_location(city, longitude, timezone)
        final_time, correction, utc_offset = adjust_to_true_solar(input_time, location)
        time_info = {
            "input_local_time": birth,
            "time_basis": time_basis,
            "true_solar_time": final_time.strftime("%Y-%m-%d %H:%M"),
            "correction_minutes": round(correction, 2),
            "longitude": location.longitude,
            "timezone": location.timezone,
            "resolved_location": location.resolved_name,
            "utc_offset_hours": utc_offset,
            "note": "已按城市中心经度、出生地历史法定时区和均时差校正真太阳时。",
        }
        if location.resolved_name:
            birthplace = f"{country}·{location.resolved_name}"
        warnings.append("真太阳时为城市中心近似值；若接近时辰边界，建议用具体出生地址复核。")

    bazi = calculate_bazi(final_time, gender)
    role = ROLES.get(bazi["day_pillar"])
    if role is None:
        raise ValueError("日柱固定角色库缺失")
    card_copy = generate_card_copy(bazi)
    kline = build_kline_result(
        bazi,
        input_time.year,
        card_copy,
        center_year=center_year,
    )

    return {
        "version": "1.1.0-local",
        "name": name.strip(),
        "gender": "男" if gender == "male" else "女",
        "birthplace": birthplace,
        "time": time_info,
        "bazi": bazi,
        "profile": {
            "day_pillar": bazi["day_pillar"],
            "player_type": role[0],
            "talent_description": role[1],
        },
        "card_copy": card_copy,
        "life_kline": kline,
        "warnings": warnings,
        "disclaimer": "结果用于文化体验与自我观察，不构成医疗、法律或金融建议。",
    }


def render_profile(profile: dict[str, Any], output: str | Path) -> Path:
    bazi = profile["bazi"]
    copy = profile["card_copy"]
    final_birth = profile["time"]["true_solar_time"].replace("-", ".")
    card_data = {
        "name": profile["name"],
        "gender": profile["gender"],
        "birth": f"{final_birth}（真太阳时）",
        "location": profile["birthplace"],
        "pillars": bazi["pillars"],
        "talent_description": profile["profile"]["talent_description"],
        "core_mystic": copy["core_mystic"],
        "core_plain": copy["core_plain"],
        "main_task": copy["main_task"],
        "center_year": profile["life_kline"]["center_year"],
        "timeline": profile["life_kline"]["timeline"],
        "timeline_algorithm": profile["life_kline"]["timeline_algorithm"],
        "stage_label": profile["life_kline"]["stage_label"],
        "current_issue": profile["life_kline"]["current_issue"],
    }
    return Path(render_card(card_data, output))
