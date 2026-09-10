#!/usr/bin/env python3
"""Shared report-source contract and post-calibration selection rules."""

from __future__ import annotations

from typing import Any


DIMENSIONS = (
    "self_growth",
    "love_partner",
    "career",
    "finance_resources",
    "body_emotion",
    "family_growth",
)
BASE_COVERAGE = (
    "feature",
    "behavior",
    "formation",
    "challenge",
    "current_change",
    "response",
)
SPECIAL_COVERAGE = {
    "family_growth": (
        "parent_kin_interaction",
        "support_and_constraint",
        "independence_and_reciprocity",
    ),
    "body_emotion": (
        "baseline_signals",
        "stress_sequence",
        "recovery_pattern",
    ),
}
DELIVERY_RULES = {
    "normal": {"minimum_claims": 6, "minimum_specific": 4, "paragraphs": (2, 4), "cjk": (500, 700)},
    "shortened": {"minimum_claims": 4, "minimum_specific": 3, "paragraphs": (2, 3), "cjk": (320, 500)},
    "minimal": {"minimum_claims": 2, "minimum_specific": 1, "paragraphs": (1, 2), "cjk": (180, 320)},
    "evidence_gap": {"minimum_claims": 0, "minimum_specific": 0, "paragraphs": (1, 1), "cjk": (60, 180)},
}
MANDATORY_CANDIDATE_MAX = 2

FOCUS_ALIASES = {
    "career": ("career", "事业", "职业", "工作", "职场", "求职", "转岗", "晋升", "升职", "创业", "学习", "考试", "专业"),
    "finance_resources": ("finance", "财务", "财富", "收入", "赚钱", "金钱", "资产", "理财"),
    "love_partner": ("love", "relationship", "恋爱", "感情", "伴侣", "婚姻", "桃花", "亲密关系"),
    "family_growth": ("family", "家庭", "父母", "亲友", "家人", "成长环境"),
    "body_emotion": ("body", "health", "emotion", "身体", "健康", "情绪", "压力", "睡眠"),
    "self_growth": ("self", "growth", "性格", "成长", "自我", "内在"),
}


def focus_domain(value: Any) -> str | None:
    """Map a user-facing focus phrase to one report domain.

    Longest aliases win so that phrases such as ``亲密关系`` are not reduced to
    a shorter accidental match. Unknown or empty focuses remain unfiltered.
    """
    text = str(value or "").strip().lower()
    if not text:
        return None
    matches = [
        (len(alias), domain)
        for domain, aliases in FOCUS_ALIASES.items()
        for alias in aliases
        if alias.lower() in text
    ]
    return max(matches)[1] if matches else None


def evidence_retention_gaps(data: dict[str, Any]) -> list[str]:
    """Find severe method-to-Core information loss without imposing quotas.

    Sparse evidence is legal.  This check only activates when at least three
    completed methods supplied four or more heterogeneous hypotheses for the
    same domain.  In that situation one Core claim cannot carry several genuinely
    different reality axes.  Two or more claims may still consolidate related
    hypotheses under the ordinary source validators.  This is evidence-triggered
    retention, not a per-domain quota.
    """
    upstream: dict[str, list[tuple[str, str, str]]] = {domain: [] for domain in DIMENSIONS}
    for method in data.get("independent_method_analyses") or []:
        if not isinstance(method, dict) or method.get("status") != "complete":
            continue
        method_id = str(method.get("method_id", ""))
        for item in method.get("reality_hypotheses") or []:
            if not isinstance(item, dict) or item.get("domain") not in upstream:
                continue
            upstream[item["domain"]].append((
                str(item.get("hypothesis_id", "")),
                method_id,
                str(item.get("normalized_direction", "")).strip(),
            ))
    claims = [item for item in data.get("report_claim_ledger") or [] if isinstance(item, dict)]
    gaps: list[str] = []
    for domain, hypotheses in upstream.items():
        methods = {item[1] for item in hypotheses if item[1]}
        directions = {item[2] for item in hypotheses if item[2]}
        domain_claims = [item for item in claims if item.get("domain") == domain]
        if len(hypotheses) < 4 or len(methods) < 3 or len(directions) < 2:
            continue
        upstream_ids = {item[0] for item in hypotheses if item[0]}
        retained_ids = {
            str(identifier)
            for claim in domain_claims
            for identifier in (claim.get("method_hypothesis_ids") or [])
            if str(identifier) in upstream_ids
        }
        retained_methods = {item[1] for item in hypotheses if item[0] in retained_ids}
        if len(domain_claims) < 2:
            gaps.append(
                f"{domain}: {len(hypotheses)}条上游候选来自{len(methods)}个方法，"
                f"Core仅保留{len(domain_claims)}条判断并覆盖"
                f"{len(retained_ids)}/{len(upstream_ids)}条候选、"
                f"{len(retained_methods)}/{len(methods)}个方法；请保留不同现实信息轴或明确完整归并"
            )
    return gaps


def mandatory_candidate_bounds(claim_ids: list[str] | set[str] | tuple[str, ...]) -> tuple[int, int]:
    """Return the canonical pre-calibration candidate bounds for one source.

    A source with usable claims must nominate at least one candidate. Sparse sources,
    including the current-stage source, are valid with exactly one candidate.
    """
    return (1, MANDATORY_CANDIDATE_MAX) if claim_ids else (0, 0)


def claim_diversity_gaps(claims: list[dict[str, Any]]) -> list[str]:
    """Return unmet diversity axes without imposing an artificial claim count."""
    gaps: list[str] = []
    if len(claims) >= 4:
        if len({item.get("claim_family") for item in claims}) < 3:
            gaps.append("claim_family:3")
        if len({item.get("mechanism_family") for item in claims}) < 2:
            gaps.append("mechanism_family:2")
        if len({item.get("reality_dimension") for item in claims}) < 3:
            gaps.append("reality_dimension:3")
    elif len(claims) >= 2 and len({item.get("reality_dimension") for item in claims}) < 2:
        gaps.append("reality_dimension:2")
    return gaps


def required_coverage(domain: str | None) -> tuple[str, ...]:
    if domain in DIMENSIONS:
        return BASE_COVERAGE + SPECIAL_COVERAGE.get(domain, ())
    return BASE_COVERAGE


def delivery_mode(available_count: int, missing_coverage: list[str]) -> str:
    if available_count >= 6 and not missing_coverage:
        return "normal"
    if available_count >= 4:
        return "shortened"
    if available_count >= 2:
        return "minimal"
    return "evidence_gap"


def delivery_rule(mode: str) -> dict[str, Any]:
    if mode not in DELIVERY_RULES:
        raise ValueError(f"Unsupported delivery_mode: {mode}")
    return DELIVERY_RULES[mode]


def report_total_cjk_bounds(modes: list[str]) -> tuple[int, int]:
    """Return full-report bounds adjusted for evidence-driven section degradation."""
    normal_section_minimum = DELIVERY_RULES["normal"]["cjk"][0]
    reduction = 0
    for mode in modes:
        rule = delivery_rule(mode)
        reduction += max(0, normal_section_minimum - rule["cjk"][0])
    return max(1500, 4300 - reduction), 6500
