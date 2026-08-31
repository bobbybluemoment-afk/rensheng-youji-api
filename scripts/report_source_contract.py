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

