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
        "life_stages": [_pick(item, stage_keys) for item in analysis.get("life_stages") or []],
        "turning_points": [_pick(item, turning_keys) for item in analysis.get("turning_points") or []],
        "annual_theme_activation": [_pick(item, annual_keys) for item in analysis.get("annual_theme_activation") or []],
    }


def compact_claim(item: dict[str, Any]) -> dict[str, Any]:
    """Keep only fields the prose writer can act on."""
    keys = (
        "claim_id", "domain", "reality_dimension", "claim_family", "plain_claim",
        "new_information", "claim_class", "coverage_tags", "applicable_conditions",
        "allowed_examples", "counterevidence", "unsupported_extensions", "calibration_status",
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
    return [{
        "slot_id": f"{section['id']}:{index + 1}", "section_id": section["id"], "paragraph_index": index,
        "delivery_mode": mode, "narrative_role": roles[index], "claim_ids": bucket,
        "claims": [compact_claim(claim_index[item]) for item in bucket if item in claim_index],
        "must_include_exact": [claim_index[item]["plain_claim"] for item in mandatory if item in bucket and item in claim_index],
    } for index, bucket in enumerate(buckets)]


def build(brief: dict[str, Any], analysis: dict[str, Any] | None = None) -> dict[str, Any]:
    sections = [brief["life_overview"], *brief["dimensions"], brief["current_question"]]
    slots = [slot for section in sections for slot in section_slots(section)]
    return {
        "schema_version": "1.0.0", "brief_id": brief["brief_id"], "brief_sha256": digest(brief),
        "rules": {
            "task": "只为每个slot_id写一个自然中文段落，不输出来源映射。",
            "voice": "统一使用第二人称你，先肯定表达，再写条件和例子。",
            "boundaries": "不得添加未给出的经历、命理术语、内部编号或绝对事件保证。",
            "continuity": "严格按照narrative_role组织同一条叙事线；先说明表现，再交代形成与条件，最后写挑战、阶段变化和应对。相邻句必须有因果、递进或转折关系，不得把不相干领域并排罗列。",
        },
        "slots": slots,
        "supplemental_tasks": {
            "summary": ["capabilities_resources"],
            "stage_story": ["previous_foundation", "recent_development", "present_task", "next_direction", "long_range"],
            "yearly_outlook": "根据冻结Core的20年连续年度材料逐年写现实信号，不写绝对吉凶；carry_in与seed_for_next直接写实际承接内容，不要每年重复‘上一年留下’‘传给下一年’等模板句。",
            "action_guide": "写三条优先行动、一个减少项和两条传统偏好建议。",
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
