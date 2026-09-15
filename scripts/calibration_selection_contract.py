#!/usr/bin/env python3
"""Shared eligibility and five-question feasibility contract for calibration."""

from __future__ import annotations

from collections import Counter
from itertools import combinations
from typing import Any

from calibration_question_contract import quality_errors, years_in


DOMAINS = {"self_growth", "love_partner", "career", "finance_resources", "body_emotion", "family_growth"}
CLASS_SCORE = {
    "calibration_pending": 600,
    "conditional_judgment": 500,
    "independent_supplement": 400,
    "stage_judgment": 300,
    "primary_judgment": 200,
}
FOCUS_HINTS = {
    "career": ("事业", "工作", "职业", "升职", "求职"),
    "finance_resources": ("财富", "财务", "收入", "钱"),
    "love_partner": ("恋爱", "感情", "伴侣", "婚姻"),
    "family_growth": ("家庭", "父母", "亲友"),
    "body_emotion": ("身体", "健康", "情绪", "压力"),
    "self_growth": ("性格", "成长", "自己"),
}


def focus_domain(focus: str) -> str | None:
    return next(
        (domain for domain, hints in FOCUS_HINTS.items() if any(hint in focus for hint in hints)),
        None,
    )


def claim_class_for(candidate: dict[str, Any], claims: dict[str, dict[str, Any]]) -> str | None:
    classes = [
        claims[item].get("claim_class")
        for item in candidate.get("related_claim_ids") or []
        if item in claims
    ]
    classes = [item for item in classes if item in CLASS_SCORE]
    return max(classes, key=lambda item: CLASS_SCORE[item]) if classes else None


def candidate_score(candidate: dict[str, Any], source_class: str, wanted_domain: str | None) -> int:
    score = CLASS_SCORE[source_class]
    score += {"high": 30, "medium": 20, "to_verify": 10}.get(candidate.get("confidence"), 0)
    score += {"timed_event": 25, "objective_state": 20, "current_stage": 12, "stable_pattern": 8}.get(candidate.get("candidate_kind"), 0)
    if candidate.get("domain") == wanted_domain:
        score += 40
    return score


def answerable(candidate: dict[str, Any], analysis_year: int) -> bool:
    """Calibration can only ask about evidence already observable today."""
    if quality_errors(candidate, analysis_year):
        return False
    if candidate.get("candidate_kind") == "timed_event":
        scope = candidate.get("answerable_time_scope", candidate.get("time_scope"))
        window = years_in(scope)
        return (bool(window) and min(window) <= analysis_year) or (
            not window and any(term in str(scope) for term in ("过去", "当前", "至今"))
        )
    return True


def valid_question_set(items: tuple[dict[str, Any], ...]) -> bool:
    if len(items) != 5:
        return False
    counts = Counter(item["domain"] for item in items)
    kinds = [item["candidate_kind"] for item in items]
    axes = [(item.get("domain"), item.get("reality_dimension") or item.get("label")) for item in items]
    return (
        len(counts) >= 4
        and max(counts.values(), default=0) <= 2
        and "timed_event" in kinds
        and sum(kind in {"objective_state", "timed_event"} for kind in kinds) >= 2
        and len(set(axes)) == 5
    )


def eligible_candidates(analysis: dict[str, Any], focus: str = "") -> list[dict[str, Any]]:
    claims = {
        item["claim_id"]: item
        for item in analysis.get("report_claim_ledger") or []
        if isinstance(item, dict) and isinstance(item.get("claim_id"), str)
    }
    wanted_domain = focus_domain(focus)
    analysis_year = int(str(analysis.get("analysis_meta", {}).get("analysis_as_of", "0000"))[:4])
    strict_semantics = analysis.get("analysis_meta", {}).get("core_version") in {"0.16.0", "0.17.0"}
    eligible: list[dict[str, Any]] = []
    for candidate in analysis.get("reality_candidate_pool") or []:
        if not isinstance(candidate, dict) or candidate.get("domain") not in DOMAINS:
            continue
        source_class = claim_class_for(candidate, claims)
        if source_class is None or source_class == "weak_candidate":
            continue
        if not candidate.get("validation_question") or len(candidate.get("observable_examples") or []) < 2:
            continue
        if strict_semantics:
            candidate_is_answerable = answerable(candidate, analysis_year)
        else:
            candidate_is_answerable = not quality_errors(candidate, analysis_year, strict_semantics=False)
            if candidate.get("candidate_kind") == "timed_event":
                scope = candidate.get("answerable_time_scope", candidate.get("time_scope"))
                window = years_in(scope)
                candidate_is_answerable = candidate_is_answerable and (
                    (bool(window) and min(window) <= analysis_year)
                    or (not window and any(term in str(scope) for term in ("过去", "当前", "至今")))
                )
        if not candidate_is_answerable:
            continue
        item = dict(candidate)
        item["source_class"] = source_class
        item["selection_score"] = candidate_score(item, source_class, wanted_domain)
        eligible.append(item)
    eligible.sort(key=lambda item: (-item["selection_score"], str(item["candidate_id"])))
    return eligible


def feasible_sets(analysis: dict[str, Any], focus: str = "") -> list[tuple[dict[str, Any], ...]]:
    eligible = eligible_candidates(analysis, focus)
    return [items for items in combinations(eligible, 5) if valid_question_set(items)]


def feasibility_errors(analysis: dict[str, Any], focus: str = "") -> list[str]:
    eligible = eligible_candidates(analysis, focus)
    if len(eligible) < 5:
        return [f"冻结前可校准且非弱证据的现实候选不足5条：当前{len(eligible)}条"]
    if feasible_sets(analysis, focus):
        return []
    domains = Counter(item.get("domain") for item in eligible)
    kinds = Counter(item.get("candidate_kind") for item in eligible)
    axes = {(item.get("domain"), item.get("reality_dimension") or item.get("label")) for item in eligible}
    reasons: list[str] = []
    if len(domains) < 4:
        reasons.append(f"仅覆盖{len(domains)}个领域")
    if kinds.get("timed_event", 0) < 1:
        reasons.append("缺少已发生且有时运证据的timed_event候选，无法满足时间题覆盖")
    if kinds.get("timed_event", 0) + kinds.get("objective_state", 0) < 2:
        reasons.append("objective_state与timed_event候选合计不足2条")
    if len(axes) < 5:
        reasons.append(f"不同现实问题轴不足5个：当前{len(axes)}个")
    if not reasons:
        reasons.append("候选分布无法同时满足四领域、同领域最多两题和五个不同问题轴")
    return [
        "冻结前不存在合规五题组合："
        + "；".join(reasons)
        + f"；可用领域={dict(sorted(domains.items()))}；可用类型={dict(sorted(kinds.items()))}"
    ]


def select_candidates(analysis: dict[str, Any], focus: str = "") -> list[dict[str, Any]]:
    eligible = eligible_candidates(analysis, focus)
    if len(eligible) < 5:
        raise ValueError(f"冻结Core中可校准且非弱证据的现实候选不足5条：当前{len(eligible)}条")
    valid = feasible_sets(analysis, focus)
    if not valid:
        raise ValueError(feasibility_errors(analysis, focus)[0])
    return list(max(
        valid,
        key=lambda items: (
            sum(item["selection_score"] for item in items),
            tuple(item["candidate_id"] for item in items),
        ),
    ))
