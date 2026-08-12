#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


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


def require(obj, key, where="root"):
    if key not in obj or obj[key] in (None, "", []):
        raise ValueError(f"Missing required field: {where}.{key}")
    return obj[key]


def validate(data):
    for key in (
        "title", "subtitle", "generated_on", "brand", "profile", "chart",
        "calibration", "panorama", "life_thread", "dimensions",
        "prosperity_guide", "open_questions", "author", "boundaries",
    ):
        require(data, key)

    if data["title"] != "人生有迹｜成长地图":
        raise ValueError("title must be 人生有迹｜成长地图")

    for key in ("identity_option", "birth", "location", "focus", "question"):
        require(data["profile"], key, "profile")

    for key in ("pillars", "luck_start", "da_yun", "current_da_yun", "time_basis"):
        require(data["chart"], key, "chart")
    if len(data["chart"]["pillars"]) != 4:
        raise ValueError("chart.pillars must contain exactly four pillars")

    for key in ("summary", "birth_time_status"):
        require(data["calibration"], key, "calibration")

    for key in ("life_line", "reality_findings", "current_tension", "direct_answer"):
        require(data["panorama"], key, "panorama")
    if not 3 <= len(data["panorama"]["reality_findings"]) <= 5:
        raise ValueError("panorama.reality_findings must contain 3 to 5 items")

    life = data["life_thread"]
    for key in ("initial_role", "core_configuration", "main_task", "portrait", "stage_path"):
        require(life, key, "life_thread")
    for key in ("previous_foundation", "recent_development", "present_task", "next_direction"):
        require(life["stage_path"], key, "life_thread.stage_path")

    dimensions = data["dimensions"]
    if [d.get("id") for d in dimensions] != DIMENSION_IDS:
        raise ValueError("dimensions must use the six fixed ids in order")
    for index, section in enumerate(dimensions):
        where = f"dimensions[{index}]"
        for key in (
            "title", "finding", "reality_findings", "analysis", "current_focus",
            "suggestions", "confidence", "audit",
        ):
            require(section, key, where)
        if section["confidence"] not in CONFIDENCE:
            raise ValueError(f"Invalid confidence in {where}")
        for key in ("chart_basis", "life_basis", "social_basis", "needs_validation"):
            require(section["audit"], key, f"{where}.audit")

    guide = data["prosperity_guide"]
    for key in ("priority_actions", "reduce", "traditional_preferences"):
        require(guide, key, "prosperity_guide")
    if len(guide["priority_actions"]) != 3:
        raise ValueError("prosperity_guide.priority_actions must contain exactly 3 items")
    if not 2 <= len(guide["traditional_preferences"]) <= 5:
        raise ValueError("traditional_preferences must contain 2 to 5 items")
    for index, item in enumerate(guide["traditional_preferences"]):
        require(item, "area", f"traditional_preferences[{index}]")
        require(item, "advice", f"traditional_preferences[{index}]")

    author = data["author"]
    for key in ("name", "bio", "github", "web", "wechat_image", "wechat_note"):
        require(author, key, "author")

    visible = json.dumps({
        "panorama": data["panorama"],
        "life_thread": data["life_thread"],
        "dimensions": [{k: v for k, v in d.items() if k != "audit"} for d in dimensions],
        "prosperity_guide": guide,
        "consultation_note": data.get("consultation_note", ""),
    }, ensure_ascii=False)
    found = sorted(term for term in BANNED if term in visible)
    if found:
        raise ValueError("Banned language found: " + "、".join(found))
    jargon = sorted(term for term in AI_JARGON if term in visible)
    if jargon:
        raise ValueError("AI-style jargon found: " + "、".join(jargon))


def bullets(items, bold=False):
    if bold:
        return "\n".join(f"- **{item}**" for item in items)
    return "\n".join(f"- {item}" for item in items)


def render(data):
    p = data["profile"]
    c = data["chart"]
    name = p.get("name") or "未署名"
    uncertainty = c.get("uncertainty") or "未发现需要额外提示的时间边界问题"
    calibration = data["calibration"]
    panorama = data["panorama"]
    thread = data["life_thread"]
    stage = thread["stage_path"]

    lines = [
        f"# {data['title']}", "", f"> {data['subtitle']}", "", f"**{data['brand']}**", "",
        "## 基本信息", "", "| 项目 | 内容 |", "|---|---|",
        f"| 姓名 | {name} |",
        f"| 身份选项 | {p['identity_option']} |",
        f"| 出生时间 | {p['birth']} |",
        f"| 出生地点 | {p['location']} |",
        f"| 最想了解 | {p['focus']} |",
        f"| 当前问题 | {p['question']} |",
        f"| 报告日期 | {data['generated_on']} |", "",
        "## 排盘口径", "", "| 项目 | 内容 |", "|---|---|",
        f"| 四柱 | {'　'.join(c['pillars'])} |",
        f"| 起运时间 | {c['luck_start']} |",
        f"| 当前大运 | {c['current_da_yun']} |",
        f"| 时间口径 | {c['time_basis']} |",
        f"| 时间提示 | {uncertainty} |", "",
        "**大运：** " + "；".join(c["da_yun"]), "",
        f"**校准结果：** {calibration['summary']}（生时状态：{calibration['birth_time_status']}）", "",
        "## 全景分析", "", panorama["life_line"], "",
        bullets(panorama["reality_findings"], bold=True), "",
        f"**你现在最需要处理的是：{panorama['current_tension']}**", "",
        f"**对你当前问题的直接回应：{panorama['direct_answer']}**", "",
        "## 你的人生主线", "",
        f"### 初始角色\n\n{thread['initial_role']}\n",
        f"### 核心配置\n\n{thread['core_configuration']}\n",
        f"### 主线任务\n\n{thread['main_task']}\n",
        f"### 人物小传\n\n{thread['portrait']}\n",
        "### 现阶段怎样一步步形成", "",
        f"- **上一阶段留下的条件：** {stage['previous_foundation']}",
        f"- **近三年的发展：** {stage['recent_development']}",
        f"- **现在正在处理：** {stage['present_task']}",
        f"- **未来两三年的可能方向：** {stage['next_direction']}", "",
    ]

    for section in data["dimensions"]:
        lines.extend([
            f"## {section['title']}", "",
            f"**核心判断：{section['finding']}**", "",
            bullets(section["reality_findings"], bold=True), "",
        ])
        for paragraph in section["analysis"]:
            lines.extend([paragraph, ""])
        lines.extend([
            f"**现阶段重点：** {section['current_focus']}", "",
            "**可以尝试：**", "", bullets(section["suggestions"]), "",
            f"*判断等级：{section['confidence']}*", "",
        ])

    guide = data["prosperity_guide"]
    lines.extend([
        "## 旺运指南", "", "### 现在最值得做的三件事", "",
        bullets(guide["priority_actions"]), "",
        "### 需要减少的一种消耗", "", guide["reduce"], "",
        "### 传统生活偏好", "",
    ])
    for item in guide["traditional_preferences"]:
        lines.extend([f"**{item['area']}**", "", item["advice"], ""])

    lines.extend(["## 仍需继续验证", "", bullets(data["open_questions"]), ""])
    if data.get("consultation_note"):
        lines.extend([f"> {data['consultation_note']}", ""])

    author = data["author"]
    lines.extend([
        "## 关于景行", "", author["bio"], "",
        f"- GitHub：{author['github']}",
        f"- 免费网页：{author['web']}",
        f"- 工作微信：{author['wechat_image']}（{author['wechat_note']}）", "",
        "## 阅读边界", "", bullets(data["boundaries"]), "", "---", "",
        "人生有迹 by 景行｜看见反复出现的人生轨迹，也寻找新的可能", "",
    ])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Validate and render 人生有迹｜成长地图")
    parser.add_argument("input", help="UTF-8 JSON report spec")
    parser.add_argument("--out", required=True, help="Output Markdown path")
    args = parser.parse_args()
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    validate(data)
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render(data), encoding="utf-8")
    print(f"Rendered {output}")


if __name__ == "__main__":
    main()
