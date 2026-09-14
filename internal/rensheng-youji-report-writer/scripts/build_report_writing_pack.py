#!/usr/bin/env python3
"""Build paragraph slots so the writer AI only writes prose, not traceability metadata."""

from __future__ import annotations

import argparse
import hashlib
import json
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
    "career": "写工作、领导、同事、任务、职位、机会、收入和职责，可以适度使用职业语言。",
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


def compact_core_context(analysis: dict[str, Any]) -> dict[str, Any]:
    """Remove traceability and technical fields already enforced upstream."""
    portrait_keys = ("summary", "primary_traits", "complementary_traits", "internal_tensions", "observable_patterns", "current_shift", "boundaries")
    stage_keys = ("label", "start_age", "end_age", "theme", "social_context", "continuity")
    turning_keys = ("year_or_range", "phase", "theme", "linked_domains", "confidence")
    annual_keys = (
        "year", "age", "year_theme", "luck_theme_link", "change_intensity", "direction",
        "domain_impacts", "domain_connections", "human_actions", "social_feedback",
        "carry_in", "carry_out", "seed_for_next", "confidence",
    )
    return {
        "portrait_thesis": _pick(analysis.get("portrait_thesis"), portrait_keys),
        "interpretive_spine": analysis.get("interpretive_spine"),
        "life_stages": [_pick(item, stage_keys) for item in analysis.get("life_stages") or []],
        "turning_points": [_pick(item, turning_keys) for item in analysis.get("turning_points") or []],
        "annual_theme_activation": [_pick(item, annual_keys) for item in analysis.get("annual_theme_activation") or []],
    }


def compact_claim(item: dict[str, Any]) -> dict[str, Any]:
    """Keep only fields the prose writer can act on."""
    keys = (
        "claim_id", "domain", "reality_dimension", "claim_family", "plain_claim",
        "human_explanation", "new_information", "claim_class", "coverage_tags", "applicable_conditions",
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
    # Normal and shortened sections require at least two distinct claims per
    # paragraph whenever the section has enough source claims. Narrative-role
    # scoring must not create a 3+1 or 5+1 split that the draft validator can
    # never accept.
    if count > 1 and len(ordered) >= count * 2:
        for target in [index for index, bucket in enumerate(buckets) if len(bucket) < 2]:
            while len(buckets[target]) < 2:
                donor = max(range(count), key=lambda index: len(buckets[index]))
                if donor == target or len(buckets[donor]) <= 2:
                    break
                buckets[target].append(buckets[donor].pop())
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
        "先借助interpretive_spine解释能力、后来形成的做法、当前代价和发展方向，再说明同一个人怎样进入不同生活场景；不能写成工作方式总览。"
        if section_id == "life_overview" else DOMAIN_VOICE.get(str(domain), "直接回应当前问题，不得漂移到其他领域。")
    )
    return [{
        "slot_id": f"{section['id']}:{index + 1}", "section_id": section["id"], "paragraph_index": index,
        "delivery_mode": mode, "narrative_role": roles[index], "claim_ids": bucket,
        "claims": [compact_claim(claim_index[item]) for item in bucket if item in claim_index],
        "must_include_exact": [claim_index[item]["plain_claim"] for item in mandatory if item in bucket and item in claim_index],
        "section_guidance": section_guidance,
    } for index, bucket in enumerate(buckets)]


def build(brief: dict[str, Any], analysis: dict[str, Any] | None = None) -> dict[str, Any]:
    sections = [brief["life_overview"], *brief["dimensions"], brief["current_question"]]
    slots = [slot for section in sections for slot in section_slots(section)]
    return {
        "schema_version": "1.0.0", "brief_id": brief["brief_id"], "brief_sha256": digest(brief),
        "rules": {
            "task": "只为每个slot_id写一个自然中文段落，不输出来源映射。",
            "voice": "统一使用第二人称你。像一个很会观察人的人认真解释用户：自然、成熟、好理解，但仍像一份值得保存的正式个人报告。不要总结用户，要解释用户。",
            "boundaries": "不得添加未给出的经历、命理术语、内部编号或绝对事件保证。",
            "continuity": "严格按照narrative_role组织同一条解释链；一句只承担一个主要判断。先写现实中怎样发生，再解释形成原因、帮助或代价。相邻句必须有因果、递进或转折关系，不得把判断并排改写。",
            "abstract_language": "不用抽象词代替现实情况。遇到责任、成果、边界、归属、流程、标准、评价、路径、稳定、资源时，必须说明具体指谁做什么、发生什么或用户怎样感受。",
            "contrast": "不是、并非、不只是、真正重要的不是等对比句只在确有误解需要纠正时使用，不能作为习惯起句。",
            "high_risk_language": HIGH_RISK_LANGUAGE,
            "domain_voice": DOMAIN_VOICE,
            "paragraph_test": ["不懂命理的人第一次能否读懂", "能否立即想到生活中的一个例子", "念给朋友听是否像正常中文"],
        },
        "slots": slots,
        "supplemental_tasks": {
            "summary": ["capabilities_resources"],
            "stage_story": ["previous_foundation", "recent_development", "present_task", "next_direction", "long_range"],
            "yearly_outlook": "20年数据仍完整返回供K线使用；正文说明按连续阶段理解，只给真正明显的年份写具体日常标题。禁止评价结算、角色定型、重新归档等拼接概念。普通年份用短而中性的现实描述，不强造事件。",
            "action_guide": "写三条优先行动、一个减少项和两条传统偏好建议。每条必须直接回应前文已经说明的问题，并给一个用户能执行的动作。",
            "open_questions": "只保留仍值得用户继续观察的问题。",
        },
        "core_context": compact_core_context(analysis or {}),
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
