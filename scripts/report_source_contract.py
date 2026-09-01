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
