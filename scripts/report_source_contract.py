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
    # Delivery mode follows usable explanation coverage, not a demand to collect
    # six near-synonymous claims. Four well-supported claims may jointly cover
    # several reality axes and therefore support a normal chapter.
    "normal": {"minimum_claims": 4, "minimum_specific": 3, "paragraphs": (2, 4), "cjk": (500, 700)},
    "shortened": {"minimum_claims": 2, "minimum_specific": 2, "paragraphs": (2, 3), "cjk": (320, 500)},
    "minimal": {"minimum_claims": 1, "minimum_specific": 1, "paragraphs": (1, 2), "cjk": (180, 320)},
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
    upstream: dict[str, list[tuple[str, str, str, set[str]]]] = {domain: [] for domain in DIMENSIONS}
    for method in data.get("independent_method_analyses") or []:
        if not isinstance(method, dict) or method.get("status") != "complete":
            continue
        method_id = str(method.get("method_id", ""))
        for item in method.get("reality_hypotheses") or []:
            if not isinstance(item, dict) or item.get("domain") not in upstream:
                continue
            detail_ids = {
                f"detail_{item.get('hypothesis_id')}_{index}"
                for index, _ in enumerate(item.get("observable_indicators") or [], 1)
            }
            upstream[item["domain"]].append((
                str(item.get("hypothesis_id", "")),
                method_id,
                str(item.get("normalized_direction", "")).strip(),
                detail_ids,
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
        available_details = set().union(*(item[3] for item in hypotheses)) if hypotheses else set()
        retained_details = {
            str(identifier)
            for claim in domain_claims
            for identifier in (claim.get("source_detail_atom_ids") or [])
            if str(identifier) in available_details
        }
        if len(domain_claims) < 2:
            gaps.append(
                f"{domain}: {len(hypotheses)}条上游候选来自{len(methods)}个方法，"
                f"Core仅保留{len(domain_claims)}条判断并覆盖"
                f"{len(retained_ids)}/{len(upstream_ids)}条候选、"
                f"{len(retained_methods)}/{len(methods)}个方法；请保留不同现实信息轴或明确完整归并"
            )
        elif available_details and not retained_details:
            gaps.append(f"{domain}: Core判断没有保留任何来自九方法的可观察现实细节")
    return gaps


def synthesis_disposition_gaps(data: dict[str, Any]) -> list[str]:
    """Require an explicit Core disposition for every distinct method hypothesis.

    This does not create a claim quota. Related hypotheses may share one synthesis
    cluster and one report claim, but none may silently disappear inside that
    cluster. Excluded clusters are the explicit internal disposition for evidence
    that should not enter the report ledger.
    """
    upstream_ids = {
        str(item.get("hypothesis_id"))
        for method in data.get("independent_method_analyses") or []
        if isinstance(method, dict) and method.get("status") == "complete"
        for item in method.get("reality_hypotheses") or []
        if isinstance(item, dict) and item.get("hypothesis_id")
    }
    clusters = [
        item for item in (data.get("method_synthesis") or {}).get("clusters") or []
        if isinstance(item, dict)
    ]
    cluster_ids = {str(item.get("synthesis_id")) for item in clusters if item.get("synthesis_id")}
    clustered_ids = {
        str(identifier)
        for cluster in clusters
        for identifier in cluster.get("member_hypothesis_ids") or []
    }
    gaps: list[str] = []
    missing = sorted(upstream_ids - clustered_ids)
    unknown = sorted(clustered_ids - upstream_ids)
    if missing:
        gaps.append(f"{len(missing)}条独立方法候选未进入任何综合簇：{missing}")
    if unknown:
        gaps.append(f"综合簇引用不存在的独立方法候选：{unknown}")

    claims = [item for item in data.get("report_claim_ledger") or [] if isinstance(item, dict)]
    unknown_synthesis = sorted({
        str(identifier)
        for claim in claims
        for identifier in claim.get("synthesis_ids") or []
        if str(identifier) not in cluster_ids
    })
    if unknown_synthesis:
        gaps.append(f"报告判断引用不存在的综合簇：{unknown_synthesis}")
    for cluster in clusters:
        synthesis_id = str(cluster.get("synthesis_id", ""))
        members = {str(value) for value in cluster.get("member_hypothesis_ids") or []}
        linked_claims = [claim for claim in claims if synthesis_id in set(claim.get("synthesis_ids") or [])]
        if cluster.get("report_role") == "excluded":
            if linked_claims:
                gaps.append(f"已排除综合簇{synthesis_id}不得进入报告判断台账")
            continue
        if not linked_claims:
            gaps.append(f"综合簇{synthesis_id}未登记进入报告判断台账的去向")
            continue
        retained = {
            str(identifier)
            for claim in linked_claims
            for identifier in claim.get("method_hypothesis_ids") or []
        }
        omitted = sorted(members - retained)
        if omitted:
            gaps.append(f"综合簇{synthesis_id}有上游候选被静默压缩：{omitted}")
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
    """Choose prose depth from usable evidence and explanation coverage.

    Claim count is only a sparse-evidence guardrail. It is not a writing quota:
    four diverse claims with complete coverage are enough for a full chapter,
    while any missing required axis keeps the section explicitly shortened.
    """
    if available_count >= 4 and not missing_coverage:
        return "normal"
    if available_count >= 2:
        return "shortened"
    if available_count >= 1:
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
