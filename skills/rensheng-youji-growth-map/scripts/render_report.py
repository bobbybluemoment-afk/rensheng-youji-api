#!/usr/bin/env python3
"""校验并渲染人生有迹完整报告 Markdown。"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


DIMENSION_IDS = ["self_growth", "love_partner", "career", "finance_resources", "body_emotion", "family_growth"]
CONFIDENCE = {"高置信", "中等置信", "待验证"}
BANNED = {"百分之百准确", "保证发财", "保证复合", "必然离婚", "命中注定", "改命消灾", "克夫", "克妻", "婚灾", "大凶"}
AI_JARGON = {"卡点", "卡住", "换轨", "兑现", "承接", "赛道", "抓手", "底层逻辑", "显化", "能量场"}
MINGLI_TERMS = {"日主", "身强", "身弱", "比肩", "劫财", "食神", "伤官", "正印", "偏印", "正财", "偏财", "正官", "七杀", "格局", "喜用", "忌神", "大运", "流年", "藏干", "刑冲合害", "根苗花果"}
OLD_FIELDS = {"initial_role", "core_configuration", "main_task", "portrait"}
PREFERRED_LENSES = {"root_seed_flower_fruit_map", "cross_method_analysis", "resource_relationship", "luck_cycle_themes", "annual_theme_activation", "domain_connections"}


def require(obj: dict[str, Any], key: str, where: str = "root") -> Any:
    if key not in obj or obj[key] in (None, "", []):
        raise ValueError(f"Missing required field: {where}.{key}")
    return obj[key]


def cjk_count(value: Any) -> int:
    return len(re.findall(r"[\u3400-\u9fff]", str(value)))


def length(value: str, minimum: int, maximum: int, where: str) -> None:
    count = cjk_count(value)
    if not minimum <= count <= maximum:
        raise ValueError(f"{where} 应为{minimum}—{maximum}个汉字，当前{count}")


def list_length(items: Any, minimum: int, maximum: int, where: str) -> list[Any]:
    if not isinstance(items, list) or not minimum <= len(items) <= maximum:
        raise ValueError(f"{where} 必须包含{minimum}—{maximum}项")
    return items


def visible_payload(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "executive_summary": data["executive_summary"],
        "stage_story": data["stage_story"],
        "dimensions": [{key: value for key, value in section.items() if key != "audit"} for section in data["dimensions"]],
        "yearly_outlook": data["yearly_outlook"],
        "action_guide": data["action_guide"],
        "open_questions": data["open_questions"],
        "assisted_service_note": data.get("assisted_service_note", ""),
        "boundaries": data["boundaries"],
    }


def validate(data: dict[str, Any]) -> None:
    required = ("schema_version", "document_mode", "source", "title", "subtitle", "generated_on", "brand", "profile", "chart", "calibration", "executive_summary", "stage_story", "dimensions", "yearly_outlook", "action_guide", "open_questions", "author", "boundaries")
    for key in required:
        require(data, key)
    if data["schema_version"] != "2.1.0":
        raise ValueError("schema_version must be 2.1.0")
    mode = data["document_mode"]
    if mode not in {"full_calibrated", "preliminary_uncalibrated"}:
        raise ValueError("document_mode 值无效")
    expected_title = "人生有迹｜完整报告" if mode == "full_calibrated" else "人生有迹｜初步分析"
    if data["title"] != expected_title:
        raise ValueError(f"title must be {expected_title}")

    source = data["source"]
    for key in ("analysis_id", "core_version", "analysis_as_of", "calibration_status"):
        require(source, key, "source")
    expected_status = "calibrated" if mode == "full_calibrated" else "skipped"
    if source["calibration_status"] != expected_status:
        raise ValueError(f"{mode} 必须使用 calibration_status={expected_status}")

    for key in ("identity_option", "birth", "location", "focus", "question"):
        require(data["profile"], key, "profile")
    if data["profile"].get("name"):
        length(data["profile"]["name"], 1, 20, "profile.name")
    length(data["profile"]["focus"], 2, 20, "profile.focus")
    length(data["profile"]["question"], 8, 80, "profile.question")
    chart = data["chart"]
    for key in ("pillars", "luck_start", "current_luck_cycle", "time_basis"):
        require(chart, key, "chart")
    if len(chart["pillars"]) != 4:
        raise ValueError("chart.pillars must contain exactly four pillars")
    if mode == "full_calibrated" and chart.get("formal_report_allowed") is not True:
        raise ValueError("正式报告必须通过时间边界预检")

    calibration = data["calibration"]
    for key in ("summary", "birth_time_status", "confirmed", "partial", "rejected", "uncertain"):
        if key not in calibration:
            raise ValueError(f"Missing required field: calibration.{key}")
    answers = sum(len(calibration[key]) for key in ("confirmed", "partial", "rejected", "uncertain"))
    if mode == "full_calibrated" and answers != 5:
        raise ValueError("正式报告必须记录五条校准结果")
    for key in ("confirmed", "partial", "rejected", "uncertain"):
        for index, item in enumerate(calibration[key]):
            length(item, 6, 80, f"calibration.{key}[{index}]")

    summary = data["executive_summary"]
    for key in ("life_theme", "capabilities_resources", "formation", "current_situation", "direct_answer"):
        require(summary, key, "executive_summary")
    length(summary["life_theme"], 35, 120, "executive_summary.life_theme")
    for index, item in enumerate(list_length(summary["capabilities_resources"], 3, 5, "executive_summary.capabilities_resources")):
        length(item, 16, 65, f"executive_summary.capabilities_resources[{index}]")
    length(summary["formation"], 70, 240, "executive_summary.formation")
    length(summary["current_situation"], 25, 110, "executive_summary.current_situation")
    length(summary["direct_answer"], 35, 150, "executive_summary.direct_answer")

    stage = data["stage_story"]
    for key in ("previous_foundation", "recent_development", "present_task", "next_direction", "long_range"):
        require(stage, key, "stage_story")
        length(stage[key], 25, 110, f"stage_story.{key}")

    dimensions = data["dimensions"]
    if [section.get("id") for section in dimensions] != DIMENSION_IDS:
        raise ValueError("dimensions must use the six fixed ids in order")
    all_core_sections: set[str] = set()
    for index, section in enumerate(dimensions):
        where = f"dimensions[{index}]"
        for key in ("title", "finding", "reality_findings", "analysis", "current_focus", "suggestions", "confidence", "audit"):
            require(section, key, where)
        if section["confidence"] not in CONFIDENCE:
            raise ValueError(f"Invalid confidence in {where}")
        length(section["finding"], 20, 95, f"{where}.finding")
        for item_index, item in enumerate(list_length(section["reality_findings"], 1, 3, f"{where}.reality_findings")):
            length(item, 15, 75, f"{where}.reality_findings[{item_index}]")
        for paragraph_index, paragraph in enumerate(list_length(section["analysis"], 2, 3, f"{where}.analysis")):
            length(paragraph, 70, 190, f"{where}.analysis[{paragraph_index}]")
        length(section["current_focus"], 20, 85, f"{where}.current_focus")
        for item_index, item in enumerate(list_length(section["suggestions"], 1, 3, f"{where}.suggestions")):
            length(item, 15, 70, f"{where}.suggestions[{item_index}]")
        visible_section = {key: value for key, value in section.items() if key not in {"audit", "id", "title", "confidence"}}
        section_count = cjk_count(json.dumps(visible_section, ensure_ascii=False))
        if not 330 <= section_count <= 520:
            raise ValueError(f"{where} 可见正文应为330—520个汉字，当前{section_count}")
        audit = section["audit"]
        for key in ("core_sections", "evidence_lenses", "user_facts", "social_priors", "needs_validation"):
            if key not in audit:
                raise ValueError(f"Missing required field: {where}.audit.{key}")
        core_sections = set(audit["core_sections"])
        lenses = set(audit["evidence_lenses"])
        all_core_sections.update(core_sections)
        if len(core_sections) < 2 or len(lenses) < 2:
            raise ValueError(f"{where}.audit 必须包含至少两个 Core 来源和两个独立证据视角")
        if not (core_sections | lenses) & PREFERRED_LENSES:
            raise ValueError(f"{where}.audit 缺少根苗花果、交叉方法、资源关系或时运证据")
    for needed in ("root_seed_flower_fruit_map", "cross_method_analysis"):
        if needed not in all_core_sections:
            raise ValueError(f"六个领域的来源审计必须实际使用 {needed}")

    outlook = data["yearly_outlook"]
    for key in ("start_year", "end_year", "summary", "years"):
        require(outlook, key, "yearly_outlook")
    length(outlook["summary"], 45, 160, "yearly_outlook.summary")
    years = outlook["years"]
    expected = list(range(int(outlook["start_year"]), int(outlook["end_year"]) + 1))
    actual = [item.get("year") for item in years]
    if actual != expected or len(years) != 20:
        raise ValueError("yearly_outlook.years 必须是连续20年并匹配起止年份")
    for index, item in enumerate(years):
        where = f"yearly_outlook.years[{index}]"
        for key in ("year", "theme", "carry_in", "likely_expression", "seed_for_next", "confidence"):
            require(item, key, where)
        if item["confidence"] not in CONFIDENCE:
            raise ValueError(f"Invalid confidence in {where}")
        length(item["theme"], 4, 14, f"{where}.theme")
        length(item["carry_in"], 10, 50, f"{where}.carry_in")
        length(item["likely_expression"], 22, 80, f"{where}.likely_expression")
        length(item["seed_for_next"], 10, 50, f"{where}.seed_for_next")
        if any(term in item["theme"] for term in MINGLI_TERMS):
            raise ValueError(f"{where}.theme 必须使用现实主题，不得直接使用命理术语")

    guide = data["action_guide"]
    for key in ("priority_actions", "reduce", "traditional_preferences"):
        require(guide, key, "action_guide")
    for index, item in enumerate(list_length(guide["priority_actions"], 3, 3, "action_guide.priority_actions")):
        length(item, 18, 75, f"action_guide.priority_actions[{index}]")
    length(guide["reduce"], 18, 80, "action_guide.reduce")
    for index, item in enumerate(list_length(guide["traditional_preferences"], 2, 5, "traditional_preferences")):
        require(item, "area", f"traditional_preferences[{index}]")
        require(item, "advice", f"traditional_preferences[{index}]")
        length(item["advice"], 18, 80, f"traditional_preferences[{index}].advice")
    for index, item in enumerate(list_length(data["open_questions"], 2, 5, "open_questions")):
        length(item, 10, 80, f"open_questions[{index}]")

    author = data["author"]
    for key in ("name", "bio", "github", "web", "wechat_image", "wechat_note"):
        require(author, key, "author")
    length(author["bio"], 12, 100, "author.bio")
    for index, item in enumerate(list_length(data["boundaries"], 2, 3, "boundaries")):
        length(item, 20, 90, f"boundaries[{index}]")
    if data.get("assisted_service_note"):
        length(data["assisted_service_note"], 25, 100, "assisted_service_note")
    serialized = json.dumps(data, ensure_ascii=False)
    for old_field in OLD_FIELDS:
        if f'"{old_field}"' in serialized:
            raise ValueError(f"Old report field found: {old_field}")
    visible = json.dumps(visible_payload(data), ensure_ascii=False)
    found = sorted(term for term in BANNED if term in visible)
    if found:
        raise ValueError("Banned language found: " + "、".join(found))
    jargon = sorted(term for term in AI_JARGON if term in visible)
    if jargon:
        raise ValueError("AI-style jargon found: " + "、".join(jargon))
    if re.search(r"\b(?:c\d+|candidate[_-]?\w*)\b", visible, re.IGNORECASE):
        raise ValueError("用户可见正文泄露内部候选编号")
    term_hits = sum(visible.count(term) for term in MINGLI_TERMS)
    if term_hits > 12:
        raise ValueError(f"正文命理术语过多：{term_hits}次，最多12次")
    total_cjk = cjk_count(visible)
    if mode == "full_calibrated" and not 4500 <= total_cjk <= 6500:
        raise ValueError(f"正式报告正文应为4500—6500个汉字，当前{total_cjk}")


def bullets(items: list[str], bold: bool = False) -> str:
    return "\n".join(f"- {'**' if bold else ''}{item}{'**' if bold else ''}" for item in items)


def render(data: dict[str, Any]) -> str:
    profile, chart, calibration = data["profile"], data["chart"], data["calibration"]
    summary, stage = data["executive_summary"], data["stage_story"]
    name = profile.get("name") or "未署名"
    lines = [
        f"# {data['title']}", "", f"> {data['subtitle']}", "", f"**{data['brand']}**", "",
        "## 基本信息与排盘口径", "", "| 项目 | 内容 |", "|---|---|",
        f"| 姓名 | {name} |", f"| 身份选项 | {profile['identity_option']} |", f"| 出生时间 | {profile['birth']} |",
        f"| 出生地点 | {profile['location']} |", f"| 最想了解 | {profile['focus']} |", f"| 当前问题 | {profile['question']} |",
        f"| 四柱 | {'　'.join(chart['pillars'])} |", f"| 当前阶段 | {chart['current_luck_cycle']} |", f"| 时间口径 | {chart['time_basis']} |", "",
        f"**校准结果：** {calibration['summary']}（生时状态：{calibration['birth_time_status']}）", "",
        "## 能力与可用资源", "", summary["life_theme"], "", bullets(summary["capabilities_resources"], True), "",
        "## 这些方式怎样形成", "", summary["formation"], "", "## 你现在所处的阶段", "",
        f"**当前最需要处理的是：{summary['current_situation']}**", "", f"**对你当前问题的直接回应：{summary['direct_answer']}**", "",
        "### 阶段怎样一步步发展", "", f"- **上一阶段留下的条件：** {stage['previous_foundation']}", f"- **近几年的发展：** {stage['recent_development']}",
        f"- **现在正在处理：** {stage['present_task']}", f"- **未来两三年的可能方向：** {stage['next_direction']}", f"- **更长阶段的主线：** {stage['long_range']}", "",
    ]
    for section in data["dimensions"]:
        lines.extend([f"## {section['title']}", "", f"**核心判断：{section['finding']}**", "", bullets(section["reality_findings"], True), ""])
        for paragraph in section["analysis"]:
            lines.extend([paragraph, ""])
        lines.extend([f"**现阶段重点：** {section['current_focus']}", "", "**可以尝试：**", "", bullets(section["suggestions"]), "", f"*判断等级：{section['confidence']}*", ""])
    outlook = data["yearly_outlook"]
    lines.extend(["## 阶段与逐年观察", "", outlook["summary"], "", "| 年份 | 年度主题 | 从上一年带入 | 现实中可能怎样表现 | 留给下一年 | 判断等级 |", "|---|---|---|---|---|---|"])
    for item in outlook["years"]:
        lines.append(f"| {item['year']} | {item['theme']} | {item['carry_in']} | {item['likely_expression']} | {item['seed_for_next']} | {item['confidence']} |")
    guide = data["action_guide"]
    lines.extend(["", "## 现实行动建议", "", "### 现在最值得做的三件事", "", bullets(guide["priority_actions"]), "", "### 需要减少的一种消耗", "", guide["reduce"], "", "### 传统生活偏好", ""])
    for item in guide["traditional_preferences"]:
        lines.extend([f"**{item['area']}**", "", item["advice"], ""])
    lines.extend(["## 仍需继续验证", "", bullets(data["open_questions"]), ""])
    if data.get("assisted_service_note"):
        lines.extend([f"> {data['assisted_service_note']}", ""])
    author = data["author"]
    lines.extend(["## 关于景行", "", author["bio"], "", f"- GitHub：{author['github']}", f"- 免费网页：{author['web']}", f"- 工作微信：{author['wechat_note']}", "", "## 阅读边界", "", bullets(data["boundaries"]), "", "---", "", "人生有迹 by 景行｜看见你带来的能力，理解你走过的路，也寻找新的可能", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and render 人生有迹报告 Markdown")
    parser.add_argument("input", type=Path, help="UTF-8 report.json")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
        validate(data)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(render(data), encoding="utf-8")
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "ok", "output": str(args.out), "mode": data["document_mode"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
