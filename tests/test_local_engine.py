from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from rensheng_youji.local_engine import build_profile, render_profile  # noqa: E402


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
