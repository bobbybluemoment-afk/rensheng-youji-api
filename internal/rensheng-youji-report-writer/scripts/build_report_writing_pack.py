#!/usr/bin/env python3
"""Build paragraph slots so the writer AI only writes prose, not traceability metadata."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any


PARAGRAPHS = {"normal": 3, "shortened": 2, "minimal": 1, "evidence_gap": 1}

ROLE_NAMES = {
    1: ("可靠边界",),
    2: ("主要表现与形成", "现实挑战、阶段变化与应对"),
    3: ("主要表现与行为", "形成经历与现实条件", "重复挑战、阶段变化与应对"),
}

ROLE_TAGS = {
    0: {"feature", "behavior", "baseline_signals", "parent_kin_interaction"},
    1: {"formation", "support_and_constraint", "independence_and_reciprocity"},
    2: {"challenge", "current_change", "response", "stress_sequence", "recovery_pattern"},
}

DOMAIN_VOICE = {
    "self_growth": "写思考、选择、在意、犹豫、安心、要求自己和放松，不用工作项目语言代替内心经验。",
    "love_partner": "写喜欢、靠近、回应、承诺、失望、依赖、争执、陪伴和安心；必须出现具体互动。",
    "career": "写工作、领导、同事、任务、职位、机会、收入和职责。优先从allowed_examples与observable_scenes提取1—3个岗位功能、工作对象或组织环境例子；只能写成‘例如’的适配候选，不能把例子说成用户已经从事的事实。证据只到任务类别时，不擅自扩大成具体行业。",
    "finance_resources": "真正写工资、奖金、存钱、消费、价格、预算、风险、安全感或收入来源，只使用Core允许的例子。",
    "body_emotion": "写累、紧绷、睡眠、烦躁、注意力、休息和身体反应，说明压力出现的顺序。",
    "family_growth": "写父母、家人、期待、支持、压力、独立、求助和家庭决定，不能照搬事业角色。",
}

HIGH_RISK_LANGUAGE = [
    "底层逻辑", "能量场", "换轨", "赋能", "抓手", "闭环", "价值沉淀",
    "成果悬置", "评价结算", "重新归档", "长期承接", "价值留存",
]


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _pick(value: Any, keys: tuple[str, ...]) -> Any:
    if isinstance(value, dict):
        return {key: value[key] for key in keys if key in value}
    return value


EXCLUDED_CALIBRATION_STATUSES = {"reject", "weakened", "uncertain"}


def compact_core_context(analysis: dict[str, Any], allowed_claim_ids: set[str] | None = None) -> dict[str, Any]:
    """Remove traceability and technical fields already enforced upstream."""
    portrait_keys = ("summary", "primary_traits", "complementary_traits", "internal_tensions", "observable_patterns", "current_shift", "boundaries")
    stage_keys = ("label", "start_age", "end_age", "theme", "social_context", "continuity")
    turning_keys = ("year_or_range", "phase", "theme", "linked_domains", "confidence")
    annual_keys = (
        "year", "age", "year_theme", "luck_theme_link", "change_intensity", "direction",
        "domain_impacts", "domain_connections", "human_actions", "social_feedback",
        "carry_in", "carry_out", "seed_for_next", "confidence",
    )
    ledger = {
        str(item.get("claim_id")): item
        for item in analysis.get("report_claim_ledger") or []
        if isinstance(item, dict) and item.get("claim_id")
    }
    allowed = set(ledger) if allowed_claim_ids is None else set(allowed_claim_ids)
    allowed = {
        claim_id for claim_id in allowed
        if ledger.get(claim_id, {}).get("calibration_status") not in EXCLUDED_CALIBRATION_STATUSES
    }
    spine = copy.deepcopy(analysis.get("interpretive_spine") or {})
    filtered_patterns = []
    for pattern in spine.get("core_patterns") or []:
        if not isinstance(pattern, dict):
            continue
        retained_claims = [claim_id for claim_id in pattern.get("claim_ids") or [] if claim_id in allowed]
        if not retained_claims:
            continue
        retained_domains = {
            str(ledger[claim_id].get("domain"))
            for claim_id in retained_claims
            if claim_id in ledger and ledger[claim_id].get("domain")
        }
        item = copy.deepcopy(pattern)
        item["claim_ids"] = retained_claims
        item["domain_manifestations"] = {
            domain: value
            for domain, value in (item.get("domain_manifestations") or {}).items()
            if domain in retained_domains
        }
        filtered_patterns.append(item)
    if isinstance(spine, dict):
        spine["core_patterns"] = filtered_patterns
        spine.pop("card_copy", None)
    return {
        "portrait_thesis": _pick(analysis.get("portrait_thesis"), portrait_keys),
        "interpretive_spine": spine,
        "life_stages": [_pick(item, stage_keys) for item in analysis.get("life_stages") or []],
        "turning_points": [_pick(item, turning_keys) for item in analysis.get("turning_points") or []],
        "annual_theme_activation": [_pick(item, annual_keys) for item in analysis.get("annual_theme_activation") or []],
    }


def yearly_writing_plan(analysis: dict[str, Any]) -> dict[str, Any]:
    """Create deterministic stage boundaries and key-year choices.

    The writer explains these already-selected periods; it no longer invents
    twenty titles or decides which years deserve attention.
    """
    annuals = sorted(
        [item for item in analysis.get("annual_theme_activation") or [] if isinstance(item, dict)],
        key=lambda item: int(item.get("year", 0)),
    )
    if len(annuals) != 20:
        return {"stages": [], "key_years": []}
    groups: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    for item in annuals:
        luck_changed = current and item.get("luck_theme_link") != current[-1].get("luck_theme_link")
        if current and (len(current) >= 5 or (luck_changed and len(current) >= 3)):
            groups.append(current)
            current = []
        current.append(item)
    if current:
        groups.append(current)
    if len(groups) > 1 and len(groups[-1]) < 3:
        groups[-2].extend(groups.pop())
    stage_seeds = [{
        "start_year": int(group[0]["year"]),
        "end_year": int(group[-1]["year"]),
        "luck_theme": group[0].get("luck_theme_link"),
        "annual_sources": [{
            "year": item.get("year"),
            "year_theme": item.get("year_theme"),
            "direction": item.get("direction"),
            "change_intensity": item.get("change_intensity"),
            "domain_impacts": item.get("domain_impacts"),
            "human_actions": item.get("human_actions"),
            "social_feedback": item.get("social_feedback"),
        } for item in group],
    } for group in groups]
    turning_years = {
        int(year)
        for item in analysis.get("turning_points") or []
        for year in re.findall(r"(?:19|20|21)\d{2}", str(item.get("year_or_range", "")))
    }
    key_years = [item for item in annuals if item.get("change_intensity") == "high" or int(item["year"]) in turning_years]
    if len(key_years) < 3:
        key_years = sorted(annuals, key=lambda item: (item.get("change_intensity") != "high", item["year"]))[:3]
    key_years = key_years[:8]
    return {
        "stages": stage_seeds,
        "key_years": [{
            "year": item.get("year"), "year_theme": item.get("year_theme"),
            "direction": item.get("direction"), "change_intensity": item.get("change_intensity"),
            "domain_impacts": item.get("domain_impacts"), "carry_in": item.get("carry_in"),
            "carry_out": item.get("carry_out"), "seed_for_next": item.get("seed_for_next"),
            "confidence": item.get("confidence"),
        } for item in key_years],
    }


def compact_claim(item: dict[str, Any]) -> dict[str, Any]:
    """Keep only fields the prose writer can act on."""
    keys = (
        "claim_id", "domain", "reality_dimension", "claim_family", "plain_claim",
        "human_explanation", "claim_class", "coverage_tags", "applicable_conditions",
        "observable_scenes", "helpful_effects", "possible_costs", "allowed_examples",
        "counterevidence", "unsupported_extensions", "calibration_status",
    )
    return {key: item[key] for key in keys if key in item}


def _narrative_buckets(ordered: list[str], claim_index: dict[str, dict[str, Any]], count: int) -> list[list[str]]:
    if count == 1:
        return [ordered]
    groups = (
        (ROLE_TAGS[0] | ROLE_TAGS[1], ROLE_TAGS[2])
        if count == 2 else
        (ROLE_TAGS[0], ROLE_TAGS[1], ROLE_TAGS[2])
    )
    buckets: list[list[str]] = [[] for _ in range(count)]
    for fallback, claim_id in enumerate(ordered):
        tags = set(claim_index.get(claim_id, {}).get("coverage_tags") or [])
        scores = [len(tags & group) for group in groups]
        target = max(range(count), key=lambda index: (scores[index], -len(buckets[index]), -index)) if any(scores) else fallback % count
        buckets[target].append(claim_id)
    for empty in [index for index, bucket in enumerate(buckets) if not bucket]:
        donor = max(range(count), key=lambda index: len(buckets[index]))
        if len(buckets[donor]) > 1:
            buckets[empty].append(buckets[donor].pop())
    # A non-gap paragraph needs at least one real Core claim. Keep additional
    # claims with the narrative role they actually explain instead of moving
    # them merely to satisfy a hidden per-paragraph count.
    return buckets


def section_slots(section: dict[str, Any]) -> list[dict[str, Any]]:
    mode = section.get("delivery_mode", "normal")
    count = PARAGRAPHS[mode]
    ids = list(section.get("claim_ids") or [])
    mandatory = list(section.get("mandatory_claim_ids") or [])
    ordered = mandatory + [item for item in ids if item not in mandatory]
    claim_index = {item["claim_id"]: item for item in section.get("selected_claims") or []}
    buckets = _narrative_buckets(ordered, claim_index, count)
    roles = ROLE_NAMES[count]
    section_id = str(section["id"])
    domain = section.get("domain") or (section_id if section_id in DOMAIN_VOICE else None)
    section_guidance = (
        "只说明当前缺少足够可靠信息，明确本节暂不判断的范围，并提示可用哪些真实经历继续核对；不得补写具体互动、对象特质、事件或常见模板。"
        if mode == "evidence_gap" else
        "先借助interpretive_spine解释能力、后来形成的做法、当前代价和发展方向，再说明同一个人怎样进入不同生活场景；不能写成工作方式总览。"
        if section_id == "life_overview" else
        "直接回答当前问题，只写当前阶段、需要权衡的条件和下一步动作；不得重复对应领域的完整能力画像。"
        if section_id == "current_question" else
        DOMAIN_VOICE.get(str(domain), "直接回应当前问题，不得漂移到其他领域。")
    )
    return [{
        "slot_id": f"{section['id']}:{index + 1}", "section_id": section["id"], "paragraph_index": index,
        "delivery_mode": mode, "narrative_role": roles[index], "claim_ids": bucket,
        "claims": [compact_claim(claim_index[item]) for item in bucket if item in claim_index],
        "must_include_exact": [claim_index[item]["plain_claim"] for item in mandatory if item in bucket and item in claim_index],
        "evidence_gaps": list(section.get("evidence_gaps") or []) if mode == "evidence_gap" else [],
        "prohibited_claims": list(section.get("prohibited_claims") or []),
        "section_guidance": section_guidance,
    } for index, bucket in enumerate(buckets)]


def build(brief: dict[str, Any], analysis: dict[str, Any] | None = None) -> dict[str, Any]:
    sections = [brief["life_overview"], *brief["dimensions"], brief["current_question"]]
    slots = [slot for section in sections for slot in section_slots(section)]
    allowed_claim_ids = {
        str(claim_id)
        for section in sections
        for claim_id in section.get("claim_ids") or []
    }
    return {
        "schema_version": "1.1.0", "brief_id": brief["brief_id"], "brief_sha256": digest(brief),
        "rules": {
            "task": "只为每个slot_id写一个自然中文段落，不输出来源映射。",
            "voice": "统一使用第二人称你。像一个很会观察人的人认真解释用户：自然、成熟、好理解，但仍像一份值得保存的正式个人报告。不要总结用户，要解释用户。",
            "boundaries": "不得添加未给出的经历、命理术语、内部编号或绝对事件保证。",
            "continuity": "严格按照narrative_role组织同一条解释链；一句只承担一个主要判断。先写现实中怎样发生，再解释形成原因、帮助或代价。相邻句必须有因果、递进或转折关系，不得把判断并排改写。",
            "abstract_language": "不用抽象词代替现实情况。遇到责任、成果、边界、归属、流程、标准、评价、路径、稳定、资源时，必须说明具体指谁做什么、发生什么或用户怎样感受。",
            "contrast": "不是、并非、不只是、真正重要的不是等对比句只在确有误解需要纠正时使用，不能作为习惯起句。",
            "calibration_visibility": "calibration_status只用于决定语气和选材，不得在用户正文中写‘你已经确认’‘你没有确认’‘校准结果’‘选择A/B/C/D’或‘因此报告不会’。match直接写成现实表现；conditional或partial写清适用条件；weakened、reject和uncertain已由上游排除，不得补回。",
            "section_separation": "六领域解释长期模式，current_question只回答当前阶段、现实取舍和下一步动作；不得把同一能力画像在两节各写一遍。",
            "high_risk_language": HIGH_RISK_LANGUAGE,
            "domain_voice": DOMAIN_VOICE,
            "paragraph_test": ["不懂命理的人第一次能否读懂", "能否立即想到生活中的一个例子", "念给朋友听是否像正常中文"],
        },
        "slots": slots,
        "supplemental_tasks": {
            "summary": ["capabilities_resources"],
            "stage_story": ["previous_foundation", "recent_development", "present_task", "next_direction", "long_range"],
            "yearly_outlook": "严格使用yearly_writing_plan给出的阶段边界和重点年份。正文只写3—6个连续阶段和3—8个真正明显年份，不逐年制造20个标题。阶段标题和年份标题必须写普通人能立刻理解的生活变化，禁止评价结算、角色定型、重新归档等拼接概念。完整20年数据仍保留在冻结Core和卡片链中，不由写作AI重复输出。",
            "action_guide": "写三条优先行动、一个减少项和两条传统偏好建议。每条必须直接回应前文已经说明的问题，并给一个用户能执行的动作。",
            "open_questions": "只保留仍值得用户继续观察的问题。",
        },
        "core_context": compact_core_context(analysis or {}, allowed_claim_ids),
        "yearly_writing_plan": yearly_writing_plan(analysis or {}),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--brief", type=Path, required=True)
    parser.add_argument("--analysis", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = build(json.loads(args.brief.read_text(encoding="utf-8")), json.loads(args.analysis.read_text(encoding="utf-8")) if args.analysis else None)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "ok", "output": str(args.output), "slots": len(result["slots"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
