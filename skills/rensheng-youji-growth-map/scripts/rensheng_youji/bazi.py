"""确定性四柱与大运计算。"""

from __future__ import annotations

from datetime import datetime

from lunar_python import Solar

from .interactions import branch_relations


def calculate_bazi(value: datetime, gender: str) -> dict:
    solar = Solar.fromYmdHms(value.year, value.month, value.day, value.hour, value.minute, value.second)
    lunar = solar.getLunar()
    eight = lunar.getEightChar()
    gender_number = 1 if gender == "male" else 0
    yun = eight.getYun(gender_number)

    pillars_detail = [
        {
            "position": "year",
            "pillar": eight.getYear(),
            "stem": eight.getYearGan(),
            "branch": eight.getYearZhi(),
            "stem_ten_god": eight.getYearShiShenGan(),
            "hidden_stems": list(eight.getYearHideGan()),
            "hidden_ten_gods": list(eight.getYearShiShenZhi()),
            "five_elements": eight.getYearWuXing(),
            "growth_stage": eight.getYearDiShi(),
        },
        {
            "position": "month",
            "pillar": eight.getMonth(),
            "stem": eight.getMonthGan(),
            "branch": eight.getMonthZhi(),
            "stem_ten_god": eight.getMonthShiShenGan(),
            "hidden_stems": list(eight.getMonthHideGan()),
            "hidden_ten_gods": list(eight.getMonthShiShenZhi()),
            "five_elements": eight.getMonthWuXing(),
            "growth_stage": eight.getMonthDiShi(),
        },
        {
            "position": "day",
            "pillar": eight.getDay(),
            "stem": eight.getDayGan(),
            "branch": eight.getDayZhi(),
            "stem_ten_god": eight.getDayShiShenGan(),
            "hidden_stems": list(eight.getDayHideGan()),
            "hidden_ten_gods": list(eight.getDayShiShenZhi()),
            "five_elements": eight.getDayWuXing(),
            "growth_stage": eight.getDayDiShi(),
        },
        {
            "position": "time",
            "pillar": eight.getTime(),
            "stem": eight.getTimeGan(),
            "branch": eight.getTimeZhi(),
            "stem_ten_god": eight.getTimeShiShenGan(),
            "hidden_stems": list(eight.getTimeHideGan()),
            "hidden_ten_gods": list(eight.getTimeShiShenZhi()),
            "five_elements": eight.getTimeWuXing(),
            "growth_stage": eight.getTimeDiShi(),
        },
    ]
    da_yun = []
    for item in yun.getDaYun(10):
        if item.getIndex() < 1:
            continue
        da_yun.append({
            "pillar": item.getGanZhi(),
            "start_year": item.getStartYear(),
            "end_year": item.getEndYear(),
            "start_age": item.getStartAge(),
            "end_age": item.getEndAge(),
        })

    return {
        "input_time": solar.toYmdHms(),
        "lunar_date": lunar.toString(),
        "pillars": [eight.getYear(), eight.getMonth(), eight.getDay(), eight.getTime()],
        "day_pillar": eight.getDay(),
        "day_master": eight.getDayGan(),
        "analysis_context": {
            "month_command": eight.getMonthZhi(),
            "pillars": pillars_detail,
            "branch_relations": branch_relations([item["branch"] for item in pillars_detail]),
        },
        "luck_direction": "forward" if yun.isForward() else "reverse",
        "luck_start_offset": {
            "years": yun.getStartYear(),
            "months": yun.getStartMonth(),
            "days": yun.getStartDay(),
            "hours": yun.getStartHour(),
        },
        "luck_start_local_time": yun.getStartSolar().toYmdHms(),
        "da_yun": da_yun,
    }
