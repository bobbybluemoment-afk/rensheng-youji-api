#!/usr/bin/env python3
"""校验并渲染人生有迹完整报告 Markdown。"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Iterable
from datetime import date
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from report_source_contract import BASE_COVERAGE, delivery_rule, required_coverage  # noqa: E402

DIMENSION_IDS = ["self_growth", "love_partner", "career", "finance_resources", "body_emotion", "family_growth"]
DIMENSION_PARAGRAPHS = {
    "self_growth": ["behavior_and_decision", "formation_and_experience", "recurring_challenge_and_change", "response"],
    "love_partner": ["attraction_and_needs", "interaction_and_experience", "conflict_and_change", "response"],
    "career": ["ability_and_formation", "organization_role_environment", "recurring_problem_and_change", "response"],
    "finance_resources": ["resource_start_and_attitude", "income_and_accumulation", "leakage_and_change", "response"],
    "body_emotion": ["trigger_and_signal", "coping_and_cycle", "impact_and_change", "response"],
    "family_growth": ["climate_and_resources", "role_and_boundary", "repeated_issue_and_change", "response"],
}
DIMENSION_HEADINGS = {
    "self_growth": ["你怎样做决定", "这些习惯怎样形成", "容易反复遇到的情况", "可以怎样调整"],
    "love_partner": ["你会被什么样的人吸引", "你怎样建立和维持关系", "关系里容易出现的问题", "可以怎样处理"],
    "career": ["能力怎样形成", "更适合的单位、岗位与环境", "工作中容易反复出现的问题", "接下来的应对"],
    "finance_resources": ["你怎样看待和使用钱", "钱主要从哪里来", "最容易出现损耗的地方", "接下来的积累方式"],
    "body_emotion": ["压力通常从哪里开始", "你怎样反应和恢复", "容易形成的循环与变化", "可以怎样照顾自己"],
    "family_growth": ["家庭提供的资源与影响", "你在家庭中的角色和边界", "容易反复出现的问题", "可以怎样处理"],
}
FOCUS_EMPHASIS_SECTIONS = [
    "executive_summary.current_situation", "executive_summary.direct_answer",
    "stage_story.present_task", "stage_story.next_direction", "yearly_outlook",
    "action_guide.priority_actions",
]
FOCUS_EXCLUDED_SECTIONS = [
    "executive_summary.life_theme", "executive_summary.capabilities_resources",
    "executive_summary.formation", "stage_story.previous_foundation", "stage_story.long_range",
    "dimensions",
]
FIXED_REPORT_INTRO = "这份报告根据你的出生信息、整体分析和现实校准生成。它会从性格、家庭、事业、财务、亲密关系与人生阶段之间的联系，梳理你反复出现的能力、选择和课题。请结合自己的真实经历阅读；如果之后还有想继续了解的问题，可以在报告末页找到联系方式。"
FOCUS_TERMS = {
    "relationship": ("感情", "情感", "恋爱", "伴侣", "婚姻", "对象", "亲密关系"),
    "career": ("事业", "工作", "职业", "岗位", "职位", "职场"),
    "finance": ("财务", "财富", "收入", "金钱", "资产", "工资"),
    "family": ("家庭", "父母", "家人", "成长环境"),
    "health": ("身体", "情绪", "健康", "休息"),
}
CONFIDENCE = {"高置信", "中等置信", "待验证"}
BANNED = {"百分之百准确", "保证发财", "保证复合", "必然离婚", "命中注定", "改命消灾", "克夫", "克妻", "婚灾", "大凶"}
AI_JARGON = {"卡点", "卡住", "换轨", "兑现", "承接", "赛道", "抓手", "底层逻辑", "显化", "能量场"}
EDITORIAL_BANNED = {"现实落点", "核对点", "好处是", "代价是", "资源持续", "平台节奏", "稳定位置", "能力变现", "组织化过劳型", "先扎根后显声", "表达窗口", "能力输出", "可见度", "物质与经营底色", "资源伴随期待", "表达被规训", "花不显"}
MINGLI_TERMS = {
    "命盘", "命局", "原局", "年柱", "月柱", "日柱", "时柱", "天干", "地支", "干支",
    "日主", "身强", "身弱", "比肩", "劫财", "食神", "伤官", "食伤", "正印", "偏印",
    "正财", "偏财", "正官", "七杀", "格局", "调候", "喜用", "忌神", "大运", "流年",
    "藏干", "透干", "透出", "得令", "刑冲合害", "刑冲合会", "根苗花果", "根气", "冲根",
    "引动", "财多身弱",
}
MINGLI_PATTERN = re.compile(r"(?:[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]|[甲乙丙丁戊己庚辛壬癸子丑寅卯辰巳午未申酉戌亥][木火土金水])")
FOCUS_GENERIC_KEYWORDS = {"事业", "工作", "职业", "感情", "关系", "恋爱", "财务", "财富", "收入", "家庭", "健康", "身体", "情绪", "发展", "方向", "问题", "未来", "当前", "进展", "选择"}
UNSUPPORTED_GLYPHS = {"□", "�"}
OLD_FIELDS = {"initial_role", "core_configuration", "main_task", "portrait"}
PREFERRED_LENSES = {"root_seed_flower_fruit_map", "cross_method_analysis", "resource_relationship", "luck_cycle_themes", "annual_theme_activation", "domain_connections"}
GENERIC_ANCHORS = {"能力", "专业", "技术", "业务", "管理", "表达", "创意", "资源", "稳定", "成长", "方向", "平台", "岗位", "组织", "关系", "责任", "节奏", "机会", "相关行业", "综合岗位", "一般岗位"}
ANCHOR_PRECISION = {"user_confirmed", "multi_method", "category_only"}
HEDGE_TERMS = ("可能", "更可能", "倾向", "容易", "较像", "更像", "适合")
HEDGE_PATTERN = re.compile("|".join(sorted(map(re.escape, HEDGE_TERMS), key=len, reverse=True)))
TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "references" / "calibration-question-templates.json"
CALIBRATION_TEMPLATES = {
    item["id"]: item
    for item in json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))["templates"]
}


def require(obj: dict[str, Any], key: str, where: str = "root") -> Any:
    if key not in obj or obj[key] in (None, "", []):
        raise ValueError(f"Missing required field: {where}.{key}")
    return obj[key]


def cjk_count(value: Any) -> int:
    return len(re.findall(r"[\u3400-\u9fff]", str(value)))


def length(value: str, minimum: int, maximum: int, where: str) -> None:
    if not isinstance(value, str):
        raise ValueError(f"{where} 必须是字符串，不得把数组或对象直接交给渲染器")
    count = cjk_count(value)
    if not minimum <= count <= maximum:
        raise ValueError(f"{where} 应为{minimum}—{maximum}个汉字，当前{count}")


def list_length(items: Any, minimum: int, maximum: int, where: str) -> list[Any]:
    if not isinstance(items, list) or not minimum <= len(items) <= maximum:
        raise ValueError(f"{where} 必须包含{minimum}—{maximum}项")
    return items


def reject_past_years(value: Any, current_year: int, where: str) -> None:
    years = [int(item) for item in re.findall(r"(?<!\d)(20\d{2})(?!\d)", json.dumps(value, ensure_ascii=False))]
    past = sorted({year for year in years if year < current_year})
    if past:
        raise ValueError(f"{where} 属于当前或未来行动，不得使用过去年份：{past}")


def flattened_texts(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from flattened_texts(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from flattened_texts(item)


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


def _validate_v26(data: dict[str, Any]) -> None:
    required = ("schema_version", "document_mode", "source", "title", "subtitle", "generated_on", "brand", "profile", "focus_scope", "cross_output_consistency", "chart", "calibration", "editorial_review", "executive_summary", "stage_story", "dimensions", "yearly_outlook", "action_guide", "open_questions", "author", "boundaries")
    for key in required:
        require(data, key)
    if data["schema_version"] != "2.6.0":
        raise ValueError("schema_version must be 2.6.0")
    try:
        generated_on = date.fromisoformat(data["generated_on"])
    except (TypeError, ValueError) as exc:
        raise ValueError("generated_on 必须为YYYY-MM-DD") from exc
    mode = data["document_mode"]
    if mode not in {"full_calibrated", "preliminary_uncalibrated"}:
        raise ValueError("document_mode 值无效")
    expected_title = "人生有迹｜完整报告" if mode == "full_calibrated" else "人生有迹｜初步分析"
    if data["title"] != expected_title:
        raise ValueError(f"title must be {expected_title}")

    source = data["source"]
    for key in ("analysis_id", "core_version", "analysis_as_of", "calibration_status"):
        require(source, key, "source")
    if source["core_version"] != "0.4.0":
        raise ValueError("完整报告必须来自 core_version=0.4.0 的母稿")
    if source["analysis_as_of"] != data["generated_on"]:
        raise ValueError("source.analysis_as_of 必须与 generated_on 为同一天，避免行动建议使用过期年份")
    expected_status = "calibrated" if mode == "full_calibrated" else "skipped"
    if source["calibration_status"] != expected_status:
        raise ValueError(f"{mode} 必须使用 calibration_status={expected_status}")

    for key in ("identity_option", "birth", "location", "focus", "question"):
        require(data["profile"], key, "profile")
    if data["profile"].get("name"):
        length(data["profile"]["name"], 1, 20, "profile.name")
    length(data["profile"]["focus"], 2, 20, "profile.focus")
    length(data["profile"]["question"], 8, 80, "profile.question")
    focus_scope = data["focus_scope"]
    if focus_scope.get("selected_focus") != data["profile"]["focus"]:
        raise ValueError("focus_scope.selected_focus 必须与 profile.focus 一致")
    if focus_scope.get("emphasis_sections") != FOCUS_EMPHASIS_SECTIONS:
        raise ValueError("focus_scope.emphasis_sections 必须使用固定关注范围")
    if focus_scope.get("excluded_sections") != FOCUS_EXCLUDED_SECTIONS:
        raise ValueError("focus_scope.excluded_sections 必须保护完整人生主线与长期判断")
    if focus_scope.get("overview_domains") != DIMENSION_IDS:
        raise ValueError("focus_scope.overview_domains 必须完整覆盖六个生活领域")
    topic_keywords = list_length(focus_scope.get("topic_keywords"), 1, 4, "focus_scope.topic_keywords")
    for index, keyword in enumerate(topic_keywords):
        length(keyword, 2, 8, f"focus_scope.topic_keywords[{index}]")
        if keyword in FOCUS_GENERIC_KEYWORDS:
            raise ValueError(f"focus_scope.topic_keywords[{index}] 过于宽泛，必须提取当前问题中的具体对象或选择")
    chart = data["chart"]
    for key in ("pillars", "luck_start", "current_luck_cycle", "time_basis"):
        require(chart, key, "chart")
    if len(chart["pillars"]) != 4:
        raise ValueError("chart.pillars must contain exactly four pillars")
    if mode == "full_calibrated" and chart.get("formal_report_allowed") is not True:
        raise ValueError("正式报告必须通过时间边界预检")

    calibration = data["calibration"]
    for key in ("question_schema_version", "template_version", "summary", "birth_time_status", "responses", "confirmed", "partial", "rejected", "uncertain"):
        if key not in calibration:
            raise ValueError(f"Missing required field: calibration.{key}")
    if calibration["question_schema_version"] not in {"2.1.0", "2.2.0"} or calibration["template_version"] != "1.0.0":
        raise ValueError("calibration 必须来自2.1.0或2.2.0固定题型校准链路")
    answers = sum(len(calibration[key]) for key in ("confirmed", "partial", "rejected", "uncertain"))
    if mode == "full_calibrated" and answers != 5:
        raise ValueError("正式报告必须记录五条校准结果")
    for key in ("confirmed", "partial", "rejected", "uncertain"):
        for index, item in enumerate(calibration[key]):
            length(item, 6, 80, f"calibration.{key}[{index}]")
    responses = list_length(calibration["responses"], 5, 5, "calibration.responses") if mode == "full_calibrated" else list_length(calibration["responses"], 0, 5, "calibration.responses")
    response_numbers: list[int] = []
    reported_user_notes: set[str] = set()
    for index, response in enumerate(responses):
        where = f"calibration.responses[{index}]"
        if not isinstance(response, dict):
            raise ValueError(f"{where} 必须是对象")
        for key in ("question_number", "template_id", "domain", "choice", "selected_text", "selected_value", "candidate_updates", "user_note"):
            if key not in response:
                raise ValueError(f"Missing required field: {where}.{key}")
        response_numbers.append(response["question_number"])
        if response["choice"] not in {"A", "B", "C", "D"}:
            raise ValueError(f"{where}.choice 必须为A、B、C或D")
        template = CALIBRATION_TEMPLATES.get(response["template_id"])
        if template is None or response["domain"] != template["domain"]:
            raise ValueError(f"{where}.template_id或domain不属于固定题型")
        template_choices = {item["key"]: item for item in template["choices"]}
        if response["choice"] == "D":
            if response["selected_text"] != "都不符合／不确定（可补充）" or response["selected_value"] != "uncertain" or response["candidate_updates"] != []:
                raise ValueError(f"{where} 选择D时必须记录固定不确定文本、uncertain和空更新")
        else:
            expected_choice = template_choices[response["choice"]]
            if response["selected_text"] != expected_choice["text"] or response["selected_value"] != expected_choice["value_code"]:
                raise ValueError(f"{where} 的选择文本和值编码必须来自固定题型")
            updates = list_length(response["candidate_updates"], 1, 3, f"{where}.candidate_updates")
            for update_index, update in enumerate(updates):
                if not isinstance(update, dict) or set(update) != {"candidate_id", "status"}:
                    raise ValueError(f"{where}.candidate_updates[{update_index}] 必须只含candidate_id和status")
                if not re.fullmatch(r"c\d+", str(update["candidate_id"])) or update["status"] not in {"match", "partial", "reject"}:
                    raise ValueError(f"{where}.candidate_updates[{update_index}] 值无效")
        if not isinstance(response["user_note"], str):
            raise ValueError(f"{where}.user_note 必须是字符串")
        if response["user_note"]:
            length(response["user_note"], 4, 100, f"{where}.user_note")
            reported_user_notes.add(response["user_note"])
    if mode == "full_calibrated" and response_numbers != [1, 2, 3, 4, 5]:
        raise ValueError("calibration.responses.question_number 必须依次为1—5")

    editorial = data["editorial_review"]
    expected_editorial = {
        "version": "1.0.0",
        "fact_preservation_checked": True,
        "calibration_paraphrased": True,
        "natural_chinese_checked": True,
        "template_repetition_checked": True,
    }
    if editorial != expected_editorial:
        raise ValueError("editorial_review 必须完成事实保留、校准改写、自然中文和重复句式四项检查")

    summary = data["executive_summary"]
    for key in ("life_theme", "capabilities_resources", "formation", "current_situation", "direct_answer"):
        require(summary, key, "executive_summary")
    length(summary["life_theme"], 35, 120, "executive_summary.life_theme")
    for index, item in enumerate(list_length(summary["capabilities_resources"], 2, 3, "executive_summary.capabilities_resources")):
        length(item, 16, 65, f"executive_summary.capabilities_resources[{index}]")
    length(summary["formation"], 70, 240, "executive_summary.formation")
    length(summary["current_situation"], 25, 110, "executive_summary.current_situation")
    length(summary["direct_answer"], 35, 150, "executive_summary.direct_answer")
    reject_past_years(summary["direct_answer"], generated_on.year, "executive_summary.direct_answer")
    selected_focus = data["profile"]["focus"]
    for terms in FOCUS_TERMS.values():
        if any(term in selected_focus for term in terms):
            theme_hits = sum(summary["life_theme"].count(term) for term in terms)
            if theme_hits > 2:
                raise ValueError("关注方向过度进入完整人生主线；请先写全盘主线，再在第4页回应用户问题")
            protected = "".join(summary["capabilities_resources"]) + summary["formation"]
            if sum(protected.count(term) for term in terms) > 4:
                raise ValueError("关注方向过度进入能力与形成过程；这些章节必须保持全盘视角")
            break

    stage = data["stage_story"]
    for key in ("previous_foundation", "recent_development", "present_task", "next_direction", "long_range"):
        require(stage, key, "stage_story")
        length(stage[key], 25, 110, f"stage_story.{key}")
    reject_past_years(stage["present_task"], generated_on.year, "stage_story.present_task")
    reject_past_years(stage["next_direction"], generated_on.year, "stage_story.next_direction")

    dimensions = data["dimensions"]
    if [section.get("id") for section in dimensions] != DIMENSION_IDS:
        raise ValueError("dimensions must use the six fixed ids in order")
    all_core_sections: set[str] = set()
    all_anchor_terms: list[str] = []
    audited_user_facts: set[str] = set()
    for index, section in enumerate(dimensions):
        where = f"dimensions[{index}]"
        for key in ("title", "overview", "paragraphs", "confidence", "audit"):
            require(section, key, where)
        if section["confidence"] not in CONFIDENCE:
            raise ValueError(f"Invalid confidence in {where}")
        length(section["overview"], 45, 95, f"{where}.overview")
        if len(HEDGE_PATTERN.findall(section["overview"])) > 2:
            raise ValueError(f"{where}.overview 条件词过多，判断被连续弱化")
        paragraphs = section["paragraphs"]
        expected_paragraphs = DIMENSION_PARAGRAPHS[section["id"]]
        if not isinstance(paragraphs, dict) or list(paragraphs) != expected_paragraphs:
            raise ValueError(f"{where}.paragraphs 必须按领域固定顺序完整填写：{expected_paragraphs}")
        for paragraph_key, paragraph in paragraphs.items():
            length(paragraph, 45, 105, f"{where}.paragraphs.{paragraph_key}")
            sentences = [part for part in re.split(r"[。！？；]", paragraph) if cjk_count(part)]
            if any(cjk_count(sentence) > 68 for sentence in sentences):
                raise ValueError(f"{where}.paragraphs.{paragraph_key} 存在超过68个汉字的长句，请改成自然短句")
        visible_text = section["overview"] + "".join(paragraphs.values())
        section_count = cjk_count(visible_text)
        if not 270 <= section_count <= 500:
            raise ValueError(f"{where} 可见正文应为270—500个汉字，当前{section_count}")
        if section["id"] == "body_emotion" and not any(term in visible_text for term in ("不能据此诊断", "不构成疾病诊断", "应以正规医疗评估为准")):
            raise ValueError(f"{where} 必须明确身体与情绪判断不构成疾病诊断")
        audit = section["audit"]
        for key in ("core_sections", "evidence_lenses", "verdict_sources", "reality_anchor_terms", "reality_anchor_sources", "anchor_precision", "user_facts", "social_priors", "needs_validation"):
            if key not in audit:
                raise ValueError(f"Missing required field: {where}.audit.{key}")
        core_sections = set(audit["core_sections"])
        lenses = set(audit["evidence_lenses"])
        all_core_sections.update(core_sections)
        if len(core_sections) < 2 or len(lenses) < 2:
            raise ValueError(f"{where}.audit 必须包含至少两个 Core 来源和两个独立证据视角")
        if not (core_sections | lenses) & PREFERRED_LENSES:
            raise ValueError(f"{where}.audit 缺少根苗花果、交叉方法、资源关系或时运证据")
        if not isinstance(audit["verdict_sources"], list) or len(set(audit["verdict_sources"])) < 2:
            raise ValueError(f"{where}.audit.verdict_sources 至少包含两个独立来源")
        precision = audit["anchor_precision"]
        if precision not in ANCHOR_PRECISION:
            raise ValueError(f"{where}.audit.anchor_precision 值无效")
        anchor_terms = list_length(audit["reality_anchor_terms"], 1, 4, f"{where}.audit.reality_anchor_terms")
        anchor_sources = audit["reality_anchor_sources"]
        if not isinstance(anchor_sources, dict) or set(anchor_sources) != set(anchor_terms):
            raise ValueError(f"{where}.audit.reality_anchor_sources 必须逐项覆盖现实名词")
        for term_index, term in enumerate(anchor_terms):
            length(term, 2, 14, f"{where}.audit.reality_anchor_terms[{term_index}]")
            if re.sub(r"[\s、，。]", "", term) in GENERIC_ANCHORS:
                raise ValueError(f"{where}.audit.reality_anchor_terms[{term_index}] 过于宽泛，必须写可核对的组织、任务、收入、关系安排或生活场景")
            if term not in visible_text:
                raise ValueError(f"{where} 正文必须实际出现审计中的现实名词“{term}”")
            sources = anchor_sources[term]
            needed_sources = 1 if precision == "user_confirmed" else 2
            if not isinstance(sources, list) or len(set(sources)) < needed_sources:
                raise ValueError(f"{where}.audit.reality_anchor_sources.{term} 至少包含{needed_sources}个来源")
        if precision == "user_confirmed" and not audit["user_facts"]:
            raise ValueError(f"{where}.audit.anchor_precision=user_confirmed 时必须有用户明确事实")
        if precision == "category_only" and not any(term in audit["needs_validation"] for term in ("不足以", "暂不", "还需", "需要", "只能", "不能继续缩小")):
            raise ValueError(f"{where}.audit.needs_validation 在证据只到类别层时必须明确收窄边界")
        all_anchor_terms.extend(re.sub(r"[\W_]+", "", term) for term in anchor_terms)
        audited_user_facts.update(item for item in audit["user_facts"] if isinstance(item, str))
    for needed in ("root_seed_flower_fruit_map", "cross_method_analysis"):
        if needed not in all_core_sections:
            raise ValueError(f"六个领域的来源审计必须实际使用 {needed}")
    repeated = {item for item in all_anchor_terms if all_anchor_terms.count(item) > 1}
    if repeated:
        raise ValueError("不同领域重复使用完全相同的现实名词，疑似套用模板")
    missing_notes = reported_user_notes - audited_user_facts
    if missing_notes:
        raise ValueError("用户在校准中补充的具体事实没有进入相关章节来源审计")
    protected_focus_text = json.dumps({
        "life_theme": summary["life_theme"],
        "capabilities_resources": summary["capabilities_resources"],
        "formation": summary["formation"],
        "previous_foundation": stage["previous_foundation"],
        "long_range": stage["long_range"],
        "dimensions": [{key: value for key, value in section.items() if key not in {"audit", "id", "title", "confidence"}} for section in dimensions],
    }, ensure_ascii=False)
    for keyword in topic_keywords:
        if protected_focus_text.count(keyword) > 2:
            raise ValueError(f"用户当前问题关键词“{keyword}”过度进入六领域基础分析；请只在第4页、逐年观察与行动建议中重点回应")

    outlook = data["yearly_outlook"]
    for key in ("start_year", "end_year", "summary", "years"):
        require(outlook, key, "yearly_outlook")
    length(outlook["summary"], 45, 160, "yearly_outlook.summary")
    years = outlook["years"]
    expected = list(range(int(outlook["start_year"]), int(outlook["end_year"]) + 1))
    actual = [item.get("year") for item in years]
    if actual != expected or len(years) != 20:
        raise ValueError("yearly_outlook.years 必须是连续20年并匹配起止年份")
    consistency = data["cross_output_consistency"]
    relationship_years = consistency.get("relationship_opportunity_years")
    if not isinstance(relationship_years, list) or relationship_years != sorted(set(relationship_years)):
        raise ValueError("cross_output_consistency.relationship_opportunity_years 必须是升序且不重复的年份列表")
    if any(not isinstance(year, int) or year not in expected for year in relationship_years):
        raise ValueError("cross_output_consistency.relationship_opportunity_years 必须位于报告20年范围内")
    for index, item in enumerate(years):
        where = f"yearly_outlook.years[{index}]"
        for key in ("year", "theme", "carry_in", "real_world_signal", "signal_terms", "key_year", "seed_for_next", "confidence"):
            require(item, key, where)
        if item["confidence"] not in CONFIDENCE:
            raise ValueError(f"Invalid confidence in {where}")
        length(item["theme"], 4, 14, f"{where}.theme")
        length(item["carry_in"], 10, 50, f"{where}.carry_in")
        length(item["real_world_signal"], 22, 90, f"{where}.real_world_signal")
        signal_terms = list_length(item["signal_terms"], 1, 3, f"{where}.signal_terms")
        for term_index, term in enumerate(signal_terms):
            length(term, 2, 14, f"{where}.signal_terms[{term_index}]")
            if term not in item["real_world_signal"]:
                raise ValueError(f"{where}.real_world_signal 必须实际出现年度现实载体“{term}”")
        if not isinstance(item["key_year"], bool):
            raise ValueError(f"{where}.key_year 必须是布尔值")
        length(item["seed_for_next"], 10, 50, f"{where}.seed_for_next")
        if any(term in item["theme"] for term in MINGLI_TERMS):
            raise ValueError(f"{where}.theme 必须使用现实主题，不得直接使用命理术语")

    guide = data["action_guide"]
    for key in ("priority_actions", "reduce", "traditional_preferences"):
        require(guide, key, "action_guide")
    for index, item in enumerate(list_length(guide["priority_actions"], 3, 3, "action_guide.priority_actions")):
        length(item, 18, 75, f"action_guide.priority_actions[{index}]")
    reject_past_years(guide["priority_actions"], generated_on.year, "action_guide.priority_actions")
    length(guide["reduce"], 18, 80, "action_guide.reduce")
    for index, item in enumerate(list_length(guide["traditional_preferences"], 2, 5, "traditional_preferences")):
        require(item, "area", f"traditional_preferences[{index}]")
        require(item, "advice", f"traditional_preferences[{index}]")
        length(item["advice"], 18, 80, f"traditional_preferences[{index}].advice")
    reject_past_years(guide["traditional_preferences"], generated_on.year, "action_guide.traditional_preferences")
    for index, item in enumerate(list_length(data["open_questions"], 2, 5, "open_questions")):
        length(item, 10, 80, f"open_questions[{index}]")

    author = data["author"]
    for key in ("name", "bio", "github", "web", "wechat_image", "wechat_note"):
        require(author, key, "author")
    length(author["bio"], 12, 100, "author.bio")
    if author["wechat_image"] != "assets/wechat-contact.jpg":
        raise ValueError("author.wechat_image 必须使用仓库正式资源 assets/wechat-contact.jpg")
    for index, item in enumerate(list_length(data["boundaries"], 2, 3, "boundaries")):
        length(item, 20, 90, f"boundaries[{index}]")
    if data.get("assisted_service_note"):
        length(data["assisted_service_note"], 25, 100, "assisted_service_note")
    serialized = json.dumps(data, ensure_ascii=False)
    for old_field in OLD_FIELDS:
        if f'"{old_field}"' in serialized:
            raise ValueError(f"Old report field found: {old_field}")
    visible = json.dumps(visible_payload(data), ensure_ascii=False)
    bad_glyphs = sorted(glyph for glyph in UNSUPPORTED_GLYPHS if glyph in visible)
    if bad_glyphs:
        raise ValueError("用户可见正文包含缺字或替代方框：" + "、".join(bad_glyphs))
    found = sorted(term for term in BANNED if term in visible)
    if found:
        raise ValueError("Banned language found: " + "、".join(found))
    jargon = sorted(term for term in AI_JARGON if term in visible)
    if jargon:
        raise ValueError("AI-style jargon found: " + "、".join(jargon))
    editorial_terms = sorted(term for term in EDITORIAL_BANNED if term in visible)
    if editorial_terms:
        raise ValueError("用户可见正文含有生硬模板词，请改成自然中文：" + "、".join(editorial_terms))
    copied_calibration = sorted({
        response["selected_text"] for response in responses
        if response["choice"] != "D" and len(response["selected_text"]) >= 8 and response["selected_text"] in visible
    })
    if copied_calibration:
        raise ValueError("校准选项只能用于更新判断，不能原句复制进报告正文")
    if re.search(r"\b(?:c\d+|candidate[_-]?\w*)\b", visible, re.IGNORECASE):
        raise ValueError("用户可见正文泄露内部候选编号")
    found_mingli = sorted(term for term in MINGLI_TERMS if term in visible)
    pattern_hits = sorted(set(MINGLI_PATTERN.findall(visible)))
    if found_mingli or pattern_hits:
        raise ValueError("用户可见正文不得直接出现内部命理术语：" + "、".join(found_mingli + pattern_hits))
    total_cjk = cjk_count(visible)
    if mode == "full_calibrated" and not 4300 <= total_cjk <= 6500:
        raise ValueError(f"正式报告正文应为4300—6500个汉字，当前{total_cjk}")


def _validate_narrative(section: Any, minimum: int, maximum: int, where: str, errors: list[str], require_map: bool = False, use_delivery_mode: bool = False) -> None:
    if not isinstance(section, dict):
        errors.append(f"{where} 必须是对象")
        return
    mode = section.get("delivery_mode") if use_delivery_mode else None
    rule = delivery_rule(mode) if mode in {"normal", "shortened", "minimal", "evidence_gap"} else None
    if use_delivery_mode and rule is None:
        errors.append(f"{where}.delivery_mode 无效")
    if rule:
        minimum, maximum = rule["cjk"]
        minimum_paragraphs, maximum_paragraphs = rule["paragraphs"]
    else:
        minimum_paragraphs, maximum_paragraphs = 2, 4
    paragraphs = section.get("paragraphs")
    if not isinstance(paragraphs, list) or not minimum_paragraphs <= len(paragraphs) <= maximum_paragraphs or any(not isinstance(item, str) for item in paragraphs):
        errors.append(f"{where}.paragraphs 必须包含{minimum_paragraphs}—{maximum_paragraphs}个自然段")
        return
    count = cjk_count("".join(paragraphs))
    if not minimum <= count <= maximum:
        errors.append(f"{where} 应为{minimum}—{maximum}个汉字，当前{count}")
    for index, paragraph in enumerate(paragraphs):
        sentences = [part for part in re.split(r"[。！？]", paragraph) if cjk_count(part)]
        if any(cjk_count(sentence) > 70 for sentence in sentences):
            errors.append(f"{where}.paragraphs[{index}] 存在超过70个汉字的长句")
    claim_ids = section.get("source_claim_ids")
    minimum_claims = rule["minimum_claims"] if rule else 6 if require_map else 4
    if not isinstance(claim_ids, list) or len(set(claim_ids)) < minimum_claims:
        errors.append(f"{where}.source_claim_ids 至少包含{minimum_claims}个不同判断来源")
    if require_map:
        paragraph_map = section.get("paragraph_claim_map")
        if not isinstance(paragraph_map, list) or len(paragraph_map) != len(paragraphs):
            errors.append(f"{where}.paragraph_claim_map 必须与自然段逐项对应")
        else:
            minimum_mapped = 2 if not rule or mode in {"normal", "shortened"} else 1 if mode == "minimal" else 0
            for index, mapped in enumerate(paragraph_map):
                if not isinstance(mapped, list) or len(set(mapped)) < minimum_mapped or set(mapped) - set(claim_ids or []):
                    errors.append(f"{where}.paragraph_claim_map[{index}] 必须引用本节至少{minimum_mapped}个不同判断")


def _validate_emphasis(section: Any, minimum: int, maximum: int, where: str, errors: list[str]) -> None:
    if not isinstance(section, dict):
        return
    paragraphs = section.get("paragraphs") or []
    paragraph_map = section.get("paragraph_claim_map") or []
    spans = section.get("emphasis_spans")
    if not isinstance(spans, list) or not minimum <= len(spans) <= maximum:
        errors.append(f"{where}.emphasis_spans 必须包含{minimum}—{maximum}条重点判断")
        return
    seen: set[int] = set()
    for index, span in enumerate(spans):
        path = f"{where}.emphasis_spans[{index}]"
        if not isinstance(span, dict) or set(span) != {"paragraph_index", "text", "claim_ids"}:
            errors.append(f"{path} 结构无效")
            continue
        paragraph_index = span.get("paragraph_index")
        if not isinstance(paragraph_index, int) or not 0 <= paragraph_index < len(paragraphs):
            errors.append(f"{path}.paragraph_index 无效")
            continue
        if paragraph_index in seen:
            errors.append(f"{where} 每个自然段最多一条重点判断")
        seen.add(paragraph_index)
        text = span.get("text")
        complete_sentence = isinstance(text, str) and bool(re.search(r"[。！？]$", text.strip()))
        if not complete_sentence or text not in paragraphs[paragraph_index] or not 16 <= cjk_count(text) <= 70 or "**" in text:
            errors.append(f"{path}.text 必须是正文中16—70字、包含句末标点的完整判断句")
        mapped = set(paragraph_map[paragraph_index]) if paragraph_index < len(paragraph_map) and isinstance(paragraph_map[paragraph_index], list) else set()
        if not isinstance(span.get("claim_ids"), list) or not span["claim_ids"] or not set(span["claim_ids"]).issubset(mapped):
            errors.append(f"{path}.claim_ids 必须来自对应自然段的Core判断")


def _validate_realizations(section: Any, where: str, errors: list[str]) -> None:
    if not isinstance(section, dict):
        return
    paragraphs = section.get("paragraphs") or []
    mandatory = section.get("mandatory_claim_ids")
    records = section.get("claim_realization_map")
    minimum = 0 if section.get("delivery_mode") == "evidence_gap" else 1
    maximum = 2 if section.get("delivery_mode") in {None, "normal"} else 1
    if not isinstance(mandatory, list) or not minimum <= len(mandatory) <= maximum:
        errors.append(f"{where}.mandatory_claim_ids 必须包含{minimum}—{maximum}条校准后锁定判断")
        return
    if not isinstance(records, list) or {item.get("claim_id") for item in records if isinstance(item, dict)} != set(mandatory):
        errors.append(f"{where}.claim_realization_map 必须逐条覆盖Core锁定判断")
        return
    for item in records:
        if not isinstance(item, dict) or set(item) != {"claim_id", "paragraph_index", "exact_span"}:
            errors.append(f"{where}.claim_realization_map 含无效记录")
            continue
        paragraph_index, exact_span = item["paragraph_index"], item["exact_span"]
        if not isinstance(paragraph_index, int) or not 0 <= paragraph_index < len(paragraphs) or not isinstance(exact_span, str) or exact_span not in paragraphs[paragraph_index]:
            errors.append(f"{where}.{item.get('claim_id')} 未真实出现在声明的正文段落")


def _validate_v27(data: dict[str, Any]) -> None:
    required = ("schema_version", "report_id", "document_mode", "source", "source_artifacts", "title", "subtitle", "generated_on", "brand", "profile", "focus_scope", "cross_output_consistency", "chart", "calibration", "editorial_review", "executive_summary", "current_question_narrative", "stage_story", "dimensions", "yearly_outlook", "action_guide", "open_questions", "author", "boundaries")
    errors: list[str] = []
    for key in required:
        if key not in data or data[key] in (None, "", []):
            errors.append(f"缺少字段：{key}")
    if data.get("document_mode") not in {"full_calibrated", "preliminary_uncalibrated"}:
        errors.append("document_mode 值无效")
    source = data.get("source", {})
    expected_cores = {"0.9.0", "0.10.0"} if data.get("schema_version") == "2.13.0" else {"0.8.1"} if data.get("schema_version") == "2.12.0" else {"0.8.0"} if data.get("schema_version") in {"2.10.0", "2.11.0"} else {"0.7.0"} if data.get("schema_version") == "2.9.0" else {"0.6.0"} if data.get("schema_version") == "2.8.0" else {"0.5.0"}
    if source.get("core_version") not in expected_cores:
        errors.append(f"{data.get('schema_version')}报告必须来自core_version={sorted(expected_cores)}之一")
    if source.get("analysis_as_of") != data.get("generated_on"):
        errors.append("source.analysis_as_of 必须与generated_on一致")
    artifacts = data.get("source_artifacts", {})
    for key in ("content_brief_id", "report_draft_id", "editorial_review_id"):
        if not artifacts.get(key):
            errors.append(f"source_artifacts.{key} 不能为空")
    if data.get("schema_version") == "2.13.0" and not artifacts.get("resolved_source_sha256"):
        errors.append("source_artifacts.resolved_source_sha256 不能为空")
    profile = data.get("profile", {})
    for key in ("identity_option", "birth", "location", "focus", "question"):
        if not profile.get(key):
            errors.append(f"profile.{key} 不能为空")
    chart = data.get("chart", {})
    for key in ("pillars", "luck_start", "current_luck_cycle", "time_basis"):
        if not chart.get(key):
            errors.append(f"chart.{key} 不能为空")
    if not isinstance(chart.get("pillars"), list) or len(chart.get("pillars") or []) != 4:
        errors.append("chart.pillars 必须恰好包含四柱")
    if data.get("document_mode") == "full_calibrated" and chart.get("formal_report_allowed") is not True:
        errors.append("正式报告必须通过出生时间边界预检")
    focus = data.get("focus_scope", {})
    if focus.get("selected_focus") != data.get("profile", {}).get("focus"):
        errors.append("关注方向来源不一致")
    if focus.get("protected_sections") != ["life_overview", "dimensions"]:
        errors.append("完整人生主线和六个领域必须免受关注方向改写")
    if focus.get("emphasis_sections") != ["current_question_narrative", "stage_story.present_task", "stage_story.next_direction", "yearly_outlook", "action_guide.priority_actions"]:
        errors.append("关注方向只能进入当前问题、相关年度和行动建议")
    calibration = data.get("calibration", {})
    responses = calibration.get("responses")
    if data.get("document_mode") == "full_calibrated" and (not isinstance(responses, list) or len(responses) != 5):
        errors.append("正式报告必须保留五道内部校准响应供交付核对")
    editorial = data.get("editorial_review", {})
    expected_editor = "2.4.0" if data.get("schema_version") == "2.13.0" else "2.3.0" if data.get("schema_version") == "2.12.0" else "2.2.0" if data.get("schema_version") in {"2.10.0", "2.11.0"} else "2.1.0" if data.get("schema_version") in {"2.8.0", "2.9.0"} else "2.0.0"
    if editorial.get("version") != expected_editor or editorial.get("review_id") != artifacts.get("editorial_review_id"):
        errors.append(f"报告必须引用{expected_editor}可追溯中文编辑记录")
    summary = data.get("executive_summary", {})
    narrative_min, narrative_max = ((500, 700) if data.get("schema_version") in {"2.8.0", "2.9.0", "2.10.0", "2.11.0", "2.12.0", "2.13.0"} else (350, 550))
    require_map = data.get("schema_version") in {"2.8.0", "2.9.0", "2.10.0", "2.11.0", "2.12.0", "2.13.0"}
    is_v213 = data.get("schema_version") == "2.13.0"
    _validate_narrative(summary.get("life_overview"), narrative_min, narrative_max, "executive_summary.life_overview", errors, require_map, is_v213)
    capabilities = summary.get("capabilities_resources")
    if not isinstance(capabilities, list) or not 2 <= len(capabilities) <= 4:
        errors.append("executive_summary.capabilities_resources 必须包含2—4项")
    else:
        for index, item in enumerate(capabilities):
            try:
                length(item, 16, 75, f"executive_summary.capabilities_resources[{index}]")
            except ValueError as exc:
                errors.append(str(exc))
    current_min, current_max = ((320, 650) if data.get("schema_version") in {"2.8.0", "2.9.0", "2.10.0", "2.11.0", "2.12.0", "2.13.0"} else (280, 600))
    _validate_narrative(data.get("current_question_narrative"), current_min, current_max, "current_question_narrative", errors, require_map, is_v213)
    stage = data.get("stage_story", {})
    for key in ("previous_foundation", "recent_development", "present_task", "next_direction", "long_range"):
        if not stage.get(key):
            errors.append(f"stage_story.{key} 不能为空")
    dimensions = data.get("dimensions")
    if not isinstance(dimensions, list) or [item.get("id") for item in dimensions if isinstance(item, dict)] != DIMENSION_IDS:
        errors.append("dimensions 必须按固定顺序完整包含六个现实领域")
    else:
        claim_usage: dict[str, int] = {}
        for item in dimensions:
            where = f"dimensions.{item.get('id')}"
            _validate_narrative(item, narrative_min, narrative_max, where, errors, require_map, is_v213)
            expected_missing = set(required_coverage(item.get("id")) if is_v213 else BASE_COVERAGE) - set(item.get("coverage") or [])
            if is_v213 and set(item.get("missing_coverage") or []) != expected_missing:
                errors.append(f"{where}.missing_coverage 与实际覆盖不一致")
            if (not is_v213 or item.get("delivery_mode") == "normal") and expected_missing:
                errors.append(f"{where}.coverage 缺少完整人物描述要素")
            if item.get("confidence") not in CONFIDENCE:
                errors.append(f"{where}.confidence 值无效")
            if item.get("id") == "body_emotion" and not any(term in "".join(item.get("paragraphs") or []) for term in ("不构成疾病诊断", "不能据此诊断", "应以正规医疗评估为准")):
                errors.append("身体与情绪章节必须说明不构成疾病诊断")
            if data.get("schema_version") in {"2.10.0", "2.11.0", "2.12.0", "2.13.0"}:
                source_ids = set(item.get("source_claim_ids") or [])
                specific = set(item.get("domain_specific_claim_ids") or [])
                mainline = set(item.get("mainline_claim_ids") or [])
                minimum_specific = delivery_rule(item.get("delivery_mode"))["minimum_specific"] if is_v213 and item.get("delivery_mode") in {"normal", "shortened", "minimal", "evidence_gap"} else 4
                if len(specific) < minimum_specific or not specific.issubset(source_ids):
                    errors.append(f"{where} 至少需要{minimum_specific}个领域专属判断")
                if len(mainline) / max(len(source_ids), 1) > 0.30 or not mainline.issubset(source_ids):
                    errors.append(f"{where} 人生主线判断不得超过30%")
                minimum_mechanisms = 2 if not is_v213 or item.get("delivery_mode") in {"normal", "shortened"} else 1 if item.get("delivery_mode") == "minimal" else 0
                if len(set(item.get("domain_mechanisms") or [])) < minimum_mechanisms or (item.get("delivery_mode") == "normal" and item.get("survives_without_mainline") is not True):
                    errors.append(f"{where} 缺少领域机制，或去掉主线后不能独立成立")
                for claim_id in source_ids:
                    claim_usage[claim_id] = claim_usage.get(claim_id, 0) + 1
        if data.get("schema_version") in {"2.10.0", "2.11.0", "2.12.0", "2.13.0"}:
            overused = sorted(item for item, count in claim_usage.items() if count > 2)
            if overused:
                errors.append(f"同一Core判断最多进入两个现实领域：{overused}")
    if data.get("schema_version") in {"2.10.0", "2.11.0", "2.12.0", "2.13.0"}:
        sparse = data.get("schema_version") in {"2.11.0", "2.12.0", "2.13.0"}
        _validate_emphasis(summary.get("life_overview"), 0 if sparse else 3, 2 if sparse else 4, "executive_summary.life_overview", errors)
        _validate_emphasis(data.get("current_question_narrative"), 0 if sparse else 2, 1 if sparse else 3, "current_question_narrative", errors)
        for item in dimensions or []:
            if isinstance(item, dict):
                _validate_emphasis(item, 0 if sparse else 1, 1 if sparse else 2, f"dimensions.{item.get('id')}", errors)
        narrative_text = json.dumps([
            summary.get("life_overview", {}).get("paragraphs", []),
            data.get("current_question_narrative", {}).get("paragraphs", []),
            *[item.get("paragraphs", []) for item in dimensions or [] if isinstance(item, dict)],
        ], ensure_ascii=False)
        if "**" in narrative_text:
            errors.append("正文必须保存纯文本；重点样式只由emphasis_spans和渲染器生成")
    if data.get("schema_version") in {"2.12.0", "2.13.0"}:
        _validate_realizations(summary.get("life_overview"), "executive_summary.life_overview", errors)
        _validate_realizations(data.get("current_question_narrative"), "current_question_narrative", errors)
        for item in dimensions or []:
            if isinstance(item, dict):
                _validate_realizations(item, f"dimensions.{item.get('id')}", errors)
    outlook = data.get("yearly_outlook", {})
    years = outlook.get("years")
    if not isinstance(years, list) or len(years) != 20:
        errors.append("逐年观察必须恰好包含连续20年")
    elif [item.get("year") for item in years] != list(range(years[0].get("year"), years[0].get("year") + 20)):
        errors.append("逐年观察年份必须连续")
    else:
        for index, item in enumerate(years):
            for key in ("year", "theme", "carry_in", "real_world_signal", "signal_terms", "key_year", "seed_for_next", "confidence"):
                if key not in item:
                    errors.append(f"yearly_outlook.years[{index}].{key} 缺失")
            for key in ("theme", "carry_in", "real_world_signal", "seed_for_next"):
                if not isinstance(item.get(key), str):
                    errors.append(f"yearly_outlook.years[{index}].{key} 必须是字符串，禁止数组或对象直接进入正文")
            if not isinstance(item.get("signal_terms"), list) or any(not isinstance(term, str) for term in item.get("signal_terms") or []):
                errors.append(f"yearly_outlook.years[{index}].signal_terms 必须是字符串数组")
            rendered_year = "".join(str(item.get(key, "")) for key in ("theme", "carry_in", "real_world_signal", "seed_for_next"))
            if "['" in rendered_year or "']" in rendered_year or '{"' in rendered_year:
                errors.append(f"yearly_outlook.years[{index}] 含未转换的数据结构文本")
    relationship_years = data.get("cross_output_consistency", {}).get("relationship_opportunity_years")
    if not isinstance(relationship_years, list):
        errors.append("关系机会年份必须是数组")
    guide = data.get("action_guide", {})
    if not isinstance(guide.get("priority_actions"), list) or len(guide.get("priority_actions") or []) != 3:
        errors.append("action_guide.priority_actions 必须恰好三项")
    for key in ("reduce", "traditional_preferences"):
        if not guide.get(key):
            errors.append(f"action_guide.{key} 不能为空")
    if not isinstance(data.get("open_questions"), list) or not 2 <= len(data.get("open_questions") or []) <= 5:
        errors.append("open_questions 必须包含2—5项")
    author = data.get("author", {})
    for key in ("name", "bio", "github", "web", "wechat_image", "wechat_note"):
        if not author.get(key):
            errors.append(f"author.{key} 不能为空")
    if author.get("wechat_image") != "assets/wechat-contact.jpg":
        errors.append("微信二维码必须使用仓库正式资源")
    if not isinstance(data.get("boundaries"), list) or not 2 <= len(data.get("boundaries") or []) <= 3:
        errors.append("boundaries 必须包含2—3项")
    visible_data = {
        "executive_summary": {
            "life_overview": summary.get("life_overview", {}).get("paragraphs", []),
            "capabilities_resources": summary.get("capabilities_resources", []),
        },
        "current_question_narrative": data.get("current_question_narrative", {}).get("paragraphs", []),
        "stage_story": data.get("stage_story"),
        "dimensions": [
            {"title": item.get("title"), "paragraphs": item.get("paragraphs")}
            for item in dimensions or [] if isinstance(item, dict)
        ],
        "yearly_outlook": outlook,
        "action_guide": data.get("action_guide"),
        "open_questions": data.get("open_questions"),
        "boundaries": data.get("boundaries"),
    }
    visible = json.dumps(visible_data, ensure_ascii=False)
    for term in BANNED | AI_JARGON | EDITORIAL_BANNED:
        if term in visible:
            errors.append(f"用户可见正文含禁用表达：{term}")
    if re.search(r"校准后的现实线索|校准确认|符合.{0,10}判断", visible):
        errors.append("用户可见正文不得展示校准过程")
    if data.get("schema_version") in {"2.8.0", "2.9.0", "2.10.0", "2.11.0", "2.12.0", "2.13.0"} and visible.count("经营") > 2:
        errors.append("用户可见正文中“经营”出现过多；仅可用于真实经商、创业或利润责任语境")
    found_mingli = sorted(term for term in MINGLI_TERMS if term in visible)
    if found_mingli or MINGLI_PATTERN.search(visible):
        errors.append("用户可见正文不得直接出现内部命理术语")
    visible_sentences = [
        paragraph.strip()
        for section in [summary.get("life_overview", {}), data.get("current_question_narrative", {}), *(dimensions or [])]
        if isinstance(section, dict)
        for paragraph in section.get("paragraphs") or []
        if isinstance(paragraph, str)
    ]
    for index, paragraph in enumerate(visible_sentences):
        if re.search(r"(?:与此同时|因为|但是|但|而|其中|意味着|例如|包括)[，：；]?\s*$", paragraph):
            errors.append(f"用户可见正文第{index + 1}段以未完成连接语结束")
        fragments = [part.strip() for part in re.split(r"[。！？]", paragraph) if part.strip()]
        suspicious = {"引", "的", "有", "但", "而", "与", "和", "或", "并", "是", "为"}
        if any(re.sub(r"[^\u3400-\u9fff]", "", part) in suspicious for part in fragments):
            errors.append(f"用户可见正文第{index + 1}段含疑似残字或残句")
    if errors:
        raise ValueError("；".join(errors))


def validate(data: dict[str, Any]) -> None:
    if data.get("schema_version") in {"2.7.0", "2.8.0", "2.9.0", "2.10.0", "2.11.0", "2.12.0", "2.13.0"}:
        _validate_v27(data)
    else:
        _validate_v26(data)


def bullets(items: list[str], bold: bool = False) -> str:
    return "\n".join(f"- {'**' if bold else ''}{item}{'**' if bold else ''}" for item in items)


def emphasized_paragraph(section: dict[str, Any], paragraph_index: int) -> str:
    paragraph = section["paragraphs"][paragraph_index]
    spans = [item for item in section.get("emphasis_spans") or [] if item.get("paragraph_index") == paragraph_index]
    if not spans:
        return paragraph
    text = spans[0]["text"]
    return paragraph.replace(text, f"**{text}**", 1)


def _render_v26(data: dict[str, Any]) -> str:
    profile, chart = data["profile"], data["chart"]
    summary, stage = data["executive_summary"], data["stage_story"]
    name = profile.get("name") or "未署名"
    lines = [
        f"# {data['title']}", "", f"> {data['subtitle']}", "", f"**{data['brand']}**", "",
        "## 关于这份报告", "", FIXED_REPORT_INTRO, "", "> 阅读后如果还有想继续了解的问题，请查看第10页联系方式。", "",
        "## 基本信息与排盘口径", "", "| 项目 | 内容 |", "|---|---|",
        f"| 姓名 | {name} |", f"| 身份选项 | {profile['identity_option']} |", f"| 出生时间 | {profile['birth']} |",
        f"| 出生地点 | {profile['location']} |", f"| 最想了解 | {profile['focus']} |", f"| 当前问题 | {profile['question']} |",
        f"| 四柱 | {'　'.join(chart['pillars'])} |", f"| 当前阶段 | {chart['current_luck_cycle']} |", f"| 时间口径 | {chart['time_basis']} |", "",
        "## 完整人生主线", "", summary["life_theme"], "", "## 能力与可用资源", "", bullets(summary["capabilities_resources"], True), "",
        "## 这些方式怎样形成", "", summary["formation"], "", "## 你现在所处的阶段", "",
        f"**当前最需要处理的是：{summary['current_situation']}**", "", f"**对你当前问题的直接回应：{summary['direct_answer']}**", "",
        "### 阶段怎样一步步发展", "", f"- **上一阶段留下的条件：** {stage['previous_foundation']}", f"- **近几年的发展：** {stage['recent_development']}",
        f"- **现在正在处理：** {stage['present_task']}", f"- **未来两三年的可能方向：** {stage['next_direction']}", f"- **更长阶段的主线：** {stage['long_range']}", "",
    ]
    for section in data["dimensions"]:
        lines.extend([f"## {section['title']}", "", f"**{section['overview']}**", ""])
        for key, heading in zip(DIMENSION_PARAGRAPHS[section["id"]], DIMENSION_HEADINGS[section["id"]]):
            lines.extend([f"### {heading}", "", section["paragraphs"][key], ""])
    outlook = data["yearly_outlook"]
    lines.extend(["## 阶段与逐年观察", "", outlook["summary"], "", "| 年份 | 年度主题 | 上一年带来的影响 | 这一年的主要表现 | 给下一年留下什么 |", "|---|---|---|---|---|"])
    for item in outlook["years"]:
        year_label = f"★ {item['year']}" if item["key_year"] else str(item["year"])
        lines.append(f"| {year_label} | {item['theme']} | {item['carry_in']} | {item['real_world_signal']} | {item['seed_for_next']} |")
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


def _render_v27(data: dict[str, Any]) -> str:
    profile, chart = data["profile"], data["chart"]
    summary, stage = data["executive_summary"], data["stage_story"]
    name = profile.get("name") or "未署名"
    lines = [
        f"# {data['title']}", "", f"> {data['subtitle']}", "", f"**{data['brand']}**", "",
        "## 关于这份报告", "", FIXED_REPORT_INTRO, "", "> 阅读后如果还有想继续了解的问题，请查看第10页联系方式。", "",
        "## 基本信息与排盘口径", "", "| 项目 | 内容 |", "|---|---|",
        f"| 姓名 | {name} |", f"| 身份选项 | {profile['identity_option']} |", f"| 出生时间 | {profile['birth']} |",
        f"| 出生地点 | {profile['location']} |", f"| 最想了解 | {profile['focus']} |", f"| 当前问题 | {profile['question']} |",
        f"| 四柱 | {'　'.join(chart['pillars'])} |", f"| 当前阶段 | {chart['current_luck_cycle']} |", f"| 时间口径 | {chart['time_basis']} |", "",
        "## 完整人生主线", "",
    ]
    for index, _ in enumerate(summary["life_overview"]["paragraphs"]):
        lines.extend([emphasized_paragraph(summary["life_overview"], index), ""])
    lines.extend(["## 能力与可用资源", "", bullets(summary["capabilities_resources"], True), "", "## 当前阶段与问题回应", ""])
    for index, _ in enumerate(data["current_question_narrative"]["paragraphs"]):
        lines.extend([emphasized_paragraph(data["current_question_narrative"], index), ""])
    lines.extend(["### 阶段怎样一步步发展", "", f"- **上一阶段留下的条件：** {stage['previous_foundation']}", f"- **近几年的发展：** {stage['recent_development']}", f"- **现在正在处理：** {stage['present_task']}", f"- **未来两三年的可能方向：** {stage['next_direction']}", f"- **更长阶段的主线：** {stage['long_range']}", ""])
    for section in data["dimensions"]:
        lines.extend([f"## {section['title']}", ""])
        for index, _ in enumerate(section["paragraphs"]):
            lines.extend([emphasized_paragraph(section, index), ""])
    outlook = data["yearly_outlook"]
    lines.extend(["## 阶段与逐年观察", "", outlook["summary"], "", "| 年份 | 年度主题 | 上一年带来的影响 | 这一年的主要表现 | 给下一年留下什么 |", "|---|---|---|---|---|"])
    for item in outlook["years"]:
        year_label = f"★ {item['year']}" if item["key_year"] else str(item["year"])
        lines.append(f"| {year_label} | {item['theme']} | {item['carry_in']} | {item['real_world_signal']} | {item['seed_for_next']} |")
    guide = data["action_guide"]
    lines.extend(["", "## 现实行动建议", "", "### 现在最值得做的三件事", "", bullets(guide["priority_actions"]), "", "### 需要减少的一种消耗", "", guide["reduce"], "", "## 仍需继续验证", "", bullets(data["open_questions"]), ""])
    if data.get("assisted_service_note"):
        lines.extend([f"> {data['assisted_service_note']}", ""])
    author = data["author"]
    lines.extend(["## 关于景行", "", author["bio"], "", f"- GitHub：{author['github']}", f"- 免费网页：{author['web']}", f"- 工作微信：{author['wechat_note']}", "", "## 阅读边界", "", bullets(data["boundaries"]), "", "---", "", "人生有迹 by 景行｜看见你带来的能力，理解你走过的路，也寻找新的可能", ""])
    return "\n".join(lines)


def render(data: dict[str, Any]) -> str:
    return _render_v27(data) if data.get("schema_version") in {"2.7.0", "2.8.0", "2.9.0", "2.10.0", "2.11.0", "2.12.0", "2.13.0"} else _render_v26(data)


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
