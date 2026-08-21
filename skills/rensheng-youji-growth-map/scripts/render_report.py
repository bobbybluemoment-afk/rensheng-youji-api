#!/usr/bin/env python3
"""校验并渲染人生有迹完整报告 Markdown。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DIMENSION_IDS = [
    "self_growth",
    "love_partner",
    "career",
    "finance_resources",
    "body_emotion",
    "family_growth",
]

CONFIDENCE = {"高置信", "中等置信", "待验证"}
BANNED = {
    "百分之百准确", "保证发财", "保证复合", "必然离婚", "命中注定",
    "改命消灾", "克夫", "克妻", "婚灾", "大凶",
}
AI_JARGON = {
    "卡点", "卡住", "换轨", "兑现", "承接", "赛道", "抓手", "底层逻辑", "显化",
}
OLD_FIELDS = {"initial_role", "core_configuration", "main_task", "portrait"}


def require(obj: dict[str, Any], key: str, where: str = "root") -> Any:
    if key not in obj or obj[key] in (None, "", []):
        raise ValueError(f"Missing required field: {where}.{key}")
    return obj[key]


def validate(data: dict[str, Any]) -> None:
    required = (
        "schema_version", "source", "title", "subtitle", "generated_on", "brand",
        "profile", "chart", "calibration", "executive_summary", "stage_story",
        "dimensions", "yearly_outlook", "action_guide", "open_questions",
        "author", "boundaries",
    )
    for key in required:
        require(data, key)

    if data["schema_version"] != "2.0.0":
        raise ValueError("schema_version must be 2.0.0")
    if data["title"] != "人生有迹｜完整报告":
        raise ValueError("title must be 人生有迹｜完整报告")

    source = data["source"]
    for key in ("analysis_id", "core_version", "analysis_as_of", "calibration_status"):
        require(source, key, "source")
    if source["calibration_status"] not in {"calibrated", "skipped"}:
        raise ValueError("source.calibration_status must be calibrated or skipped")

    for key in ("identity_option", "birth", "location", "focus", "question"):
        require(data["profile"], key, "profile")

    chart = data["chart"]
    for key in ("pillars", "luck_start", "current_luck_cycle", "time_basis"):
        require(chart, key, "chart")
    if len(chart["pillars"]) != 4:
        raise ValueError("chart.pillars must contain exactly four pillars")

    calibration = data["calibration"]
    for key in ("summary", "birth_time_status", "confirmed", "partial", "rejected", "uncertain"):
        if key not in calibration:
            raise ValueError(f"Missing required field: calibration.{key}")

    summary = data["executive_summary"]
    for key in ("life_theme", "capabilities_resources", "formation", "current_situation", "direct_answer"):
        require(summary, key, "executive_summary")
    if not 3 <= len(summary["capabilities_resources"]) <= 5:
        raise ValueError("executive_summary.capabilities_resources must contain 3 to 5 items")

    stage = data["stage_story"]
    for key in ("previous_foundation", "recent_development", "present_task", "next_direction", "long_range"):
        require(stage, key, "stage_story")

    dimensions = data["dimensions"]
    if [section.get("id") for section in dimensions] != DIMENSION_IDS:
        raise ValueError("dimensions must use the six fixed ids in order")
    for index, section in enumerate(dimensions):
        where = f"dimensions[{index}]"
        for key in ("title", "finding", "reality_findings", "analysis", "current_focus", "suggestions", "confidence", "audit"):
            require(section, key, where)
        if section["confidence"] not in CONFIDENCE:
            raise ValueError(f"Invalid confidence in {where}")
        for key in ("core_sections", "user_facts", "social_priors", "needs_validation"):
            if key not in section["audit"]:
                raise ValueError(f"Missing required field: {where}.audit.{key}")

    outlook = data["yearly_outlook"]
    for key in ("start_year", "end_year", "summary", "years"):
        require(outlook, key, "yearly_outlook")
    years = outlook["years"]
    expected = list(range(int(outlook["start_year"]), int(outlook["end_year"]) + 1))
    actual = [item.get("year") for item in years]
    if actual != expected:
        raise ValueError("yearly_outlook.years must be continuous and match start_year/end_year")
    for index, item in enumerate(years):
        for key in ("year", "theme", "carry_in", "likely_expression", "seed_for_next", "confidence"):
            require(item, key, f"yearly_outlook.years[{index}]")
        if item["confidence"] not in CONFIDENCE:
            raise ValueError(f"Invalid confidence in yearly_outlook.years[{index}]")

    guide = data["action_guide"]
    for key in ("priority_actions", "reduce", "traditional_preferences"):
        require(guide, key, "action_guide")
    if len(guide["priority_actions"]) != 3:
        raise ValueError("action_guide.priority_actions must contain exactly 3 items")
    if not 2 <= len(guide["traditional_preferences"]) <= 5:
        raise ValueError("traditional_preferences must contain 2 to 5 items")
    for index, item in enumerate(guide["traditional_preferences"]):
        require(item, "area", f"traditional_preferences[{index}]")
        require(item, "advice", f"traditional_preferences[{index}]")

    author = data["author"]
    for key in ("name", "bio", "github", "web", "wechat_image", "wechat_note"):
        require(author, key, "author")

    serialized = json.dumps(data, ensure_ascii=False)
    for old_field in OLD_FIELDS:
        if f'"{old_field}"' in serialized:
            raise ValueError(f"Old report field found: {old_field}")

    visible = json.dumps({
        "executive_summary": summary,
        "stage_story": stage,
        "dimensions": [{key: value for key, value in section.items() if key != "audit"} for section in dimensions],
        "yearly_outlook": outlook,
        "action_guide": guide,
        "assisted_service_note": data.get("assisted_service_note", ""),
    }, ensure_ascii=False)
    found = sorted(term for term in BANNED if term in visible)
    if found:
        raise ValueError("Banned language found: " + "、".join(found))
    jargon = sorted(term for term in AI_JARGON if term in visible)
    if jargon:
        raise ValueError("AI-style jargon found: " + "、".join(jargon))


def bullets(items: list[str], bold: bool = False) -> str:
    if bold:
        return "\n".join(f"- **{item}**" for item in items)
    return "\n".join(f"- {item}" for item in items)


def render(data: dict[str, Any]) -> str:
    profile = data["profile"]
    chart = data["chart"]
    calibration = data["calibration"]
    summary = data["executive_summary"]
    stage = data["stage_story"]
    name = profile.get("name") or "未署名"
    uncertainty = chart.get("uncertainty") or "未发现需要额外提示的时间边界问题"

    lines = [
        f"# {data['title']}", "", f"> {data['subtitle']}", "", f"**{data['brand']}**", "",
        "## 基本信息", "", "| 项目 | 内容 |", "|---|---|",
        f"| 姓名 | {name} |",
        f"| 身份选项 | {profile['identity_option']} |",
        f"| 出生时间 | {profile['birth']} |",
        f"| 出生地点 | {profile['location']} |",
        f"| 最想了解 | {profile['focus']} |",
        f"| 当前问题 | {profile['question']} |",
        f"| 报告日期 | {data['generated_on']} |", "",
        "## 排盘口径", "", "| 项目 | 内容 |", "|---|---|",
        f"| 四柱 | {'　'.join(chart['pillars'])} |",
        f"| 起运时间 | {chart['luck_start']} |",
        f"| 当前大运 | {chart['current_luck_cycle']} |",
        f"| 时间口径 | {chart['time_basis']} |",
        f"| 时间提示 | {uncertainty} |", "",
        f"**校准结果：** {calibration['summary']}（生时状态：{calibration['birth_time_status']}）", "",
        "## 能力与可用资源", "", summary["life_theme"], "",
        bullets(summary["capabilities_resources"], bold=True), "",
        "## 这些方式怎样形成", "", summary["formation"], "",
        "## 你现在所处的阶段", "", f"**当前最需要处理的是：{summary['current_situation']}**", "",
        f"**对你当前问题的直接回应：{summary['direct_answer']}**", "",
        "### 阶段怎样一步步发展", "",
        f"- **上一阶段留下的条件：** {stage['previous_foundation']}",
        f"- **近几年的发展：** {stage['recent_development']}",
        f"- **现在正在处理：** {stage['present_task']}",
        f"- **未来两三年的可能方向：** {stage['next_direction']}",
        f"- **更长阶段的主线：** {stage['long_range']}", "",
    ]

    for section in data["dimensions"]:
        lines.extend([
            f"## {section['title']}", "", f"**核心判断：{section['finding']}**", "",
            bullets(section["reality_findings"], bold=True), "",
        ])
        for paragraph in section["analysis"]:
            lines.extend([paragraph, ""])
        lines.extend([
            f"**现阶段重点：** {section['current_focus']}", "", "**可以尝试：**", "",
            bullets(section["suggestions"]), "", f"*判断等级：{section['confidence']}*", "",
        ])

    outlook = data["yearly_outlook"]
    lines.extend([
        "## 阶段与逐年观察", "", outlook["summary"], "",
        "| 年份 | 年度主题 | 从上一年带入 | 现实中可能怎样表现 | 留给下一年 | 判断等级 |",
        "|---|---|---|---|---|---|",
    ])
    for item in outlook["years"]:
        lines.append(
            f"| {item['year']} | {item['theme']} | {item['carry_in']} | "
            f"{item['likely_expression']} | {item['seed_for_next']} | {item['confidence']} |"
        )
    lines.append("")

    guide = data["action_guide"]
    lines.extend([
        "## 现实行动建议", "", "### 现在最值得做的三件事", "",
        bullets(guide["priority_actions"]), "", "### 需要减少的一种消耗", "", guide["reduce"], "",
        "### 传统生活偏好", "",
    ])
    for item in guide["traditional_preferences"]:
        lines.extend([f"**{item['area']}**", "", item["advice"], ""])

    lines.extend(["## 仍需继续验证", "", bullets(data["open_questions"]), ""])
    if data.get("assisted_service_note"):
        lines.extend([f"> {data['assisted_service_note']}", ""])

    author = data["author"]
    lines.extend([
        "## 关于景行", "", author["bio"], "",
        f"- GitHub：{author['github']}",
        f"- 免费网页：{author['web']}",
        f"- 工作微信：{author['wechat_image']}（{author['wechat_note']}）", "",
        "## 阅读边界", "", bullets(data["boundaries"]), "", "---", "",
        "人生有迹 by 景行｜看见你带来的能力，理解你走过的路，也寻找新的可能", "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and render 人生有迹｜完整报告")
    parser.add_argument("input", type=Path, help="UTF-8 report.json")
    parser.add_argument("--out", type=Path, required=True, help="输出 Markdown 路径")
    args = parser.parse_args()
    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
        validate(data)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(render(data), encoding="utf-8")
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "ok", "output": str(args.out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
