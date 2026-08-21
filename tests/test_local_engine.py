from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
import random
import sys
from pathlib import Path

from PIL import Image
import pytest


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "internal/rensheng-youji-mingli-core/scripts"))

from rensheng_youji.local_engine import build_profile, render_profile  # noqa: E402
from rensheng_youji.solar_time import resolve_location  # noqa: E402
from adapter_from_api_profile import boundary_flags  # noqa: E402


def test_jiaxu_known_case(tmp_path):
    profile = build_profile(
        name="",
        birth="1999-01-22 17:45",
        gender="male",
        city="北京",
        time_basis="true_solar_adjusted",
        center_year=2026,
    )
    assert profile["bazi"]["pillars"] == ["戊寅", "乙丑", "甲戌", "癸酉"]
    timeline = profile["life_kline"]["timeline"]
    assert len(timeline) == 20
    assert timeline[5]["year"] == 2026
    assert all(item["high"] - item["low"] <= 22 for item in timeline)
    output = render_profile(profile, tmp_path / "card.png")
    assert Image.open(output).size == (1242, 1660)


def test_jimao_beijing_case():
    profile = build_profile(
        name="",
        birth="1999-05-27 14:08",
        gender="female",
        city="北京",
        time_basis="true_solar_adjusted",
        center_year=2026,
    )
    assert profile["bazi"]["pillars"] == ["己卯", "己巳", "己卯", "辛未"]
    assert profile["life_kline"]["current_issue"]["domain"] in {
        "事业选择", "感情关系", "财务安排", "家庭关系", "学习发展", "城市与生活"
    }


def test_china_county_location_resolution():
    location = resolve_location("中国湖北宜昌夷陵区", None, None)
    assert location.timezone == "Asia/Shanghai"
    assert 111.2 < location.longitude < 111.5
    assert location.resolved_name == "湖北省·宜昌市·夷陵区"

    with pytest.raises(ValueError, match="存在重名"):
        resolve_location("朝阳区", None, None)


def test_report_boundary_flags_cover_adjacent_hour_day_and_solar_term():
    near_next_hour = {"time": {"true_solar_time": "1994-10-02 12:59", "correction_minutes": 0}, "bazi": {"nearest_solar_terms": []}}
    assert "hour_branch_boundary" in boundary_flags(near_next_hour)

    near_day_boundary = {"time": {"true_solar_time": "1994-10-02 23:10", "correction_minutes": 0}, "bazi": {"nearest_solar_terms": []}}
    flags = boundary_flags(near_day_boundary)
    assert "hour_branch_boundary" in flags
    assert "day_boundary" in flags

    near_solar_term = {
        "time": {"true_solar_time": "1994-10-08 20:20", "correction_minutes": 0},
        "bazi": {"nearest_solar_terms": [{"name": "寒露", "datetime": "1994-10-08 20:29:05", "relation": "next"}]},
    }
    assert "solar_term_boundary" in boundary_flags(near_solar_term)


def test_time_pillar_changes_core_landing_and_main_task():
    profiles = [
        build_profile(
            name="",
            birth=f"1999-05-27 {hour:02d}:30",
            gender="female",
            city="北京",
            time_basis="true_solar_adjusted",
            center_year=2026,
        )
        for hour in range(0, 24, 2)
    ]
    assert len({item["bazi"]["pillars"][3] for item in profiles}) == 12
    assert len({item["card_copy"]["core_plain"][1] for item in profiles}) >= 10
    assert len({item["card_copy"]["main_task"] for item in profiles}) >= 10
    assert len({item["life_kline"]["current_issue"]["headline"] for item in profiles}) >= 3


def test_current_issue_batch_is_not_age_template():
    random.seed(20260811)
    start = datetime(1986, 1, 1)
    domains: Counter[str] = Counter()
    headlines: Counter[str] = Counter()
    for _ in range(120):
        value = start + timedelta(
            days=random.randrange(0, 7305),
            minutes=random.randrange(0, 1440),
        )
        profile = build_profile(
            name="",
            birth=value.strftime("%Y-%m-%d %H:%M"),
            gender=random.choice(("male", "female")),
            city="北京",
            time_basis="true_solar_adjusted",
            center_year=2026,
        )
        issue = profile["life_kline"]["current_issue"]
        domains[issue["domain"]] += 1
        headlines[issue["headline"]] += 1

    assert len(domains) >= 5
    assert len(headlines) >= 24
    assert max(domains.values()) / 120 < 0.45
    assert max(headlines.values()) / 120 < 0.15
