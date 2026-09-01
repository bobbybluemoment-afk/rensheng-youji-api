#!/usr/bin/env python3
"""Shared contract for the method-packet to complete-Core production bridge."""

from __future__ import annotations

import hashlib
import json
from typing import Any


CORE_VERSION = "0.14.0"
SYNTHESIS_INPUT_SCHEMA_VERSION = "1.0.0"
PRIMARY_METHODS = {
    "pattern_structure",
    "momentum_configuration",
    "climate_adjustment",
    "ten_god_dynamics",
    "root_seed_flower_fruit",
    "blind_school",
    "timing_continuity",
}
PARTIAL_METHODS = {"position_relationship", "stem_branch_dynamics"}
ALL_METHODS = PRIMARY_METHODS | PARTIAL_METHODS
REPORT_DOMAINS = {
    "self_growth",
    "love_partner",
    "career",
    "finance_resources",
    "body_emotion",
    "family_growth",
}
ALL_REALITY_DOMAINS = REPORT_DOMAINS | {"learning", "mobility"}
LOVE_PARTNER_ANCHORS = {
    "ten_god_dynamics", "position_relationship", "stem_branch_dynamics",
    "blind_school", "timing_continuity",
}

DETERMINISTIC_CORE_SECTIONS = {
    "analysis_meta",
    "chart_facts",
    "chart_audit",
    "independent_method_analyses",
    "method_execution_audit",
    "source_coverage_audit",
    "evidence_registry",
    "report_source_bundle",
    "calibration_state",
    "calibration_delta",
}

SEMANTIC_SECTIONS = {
    "social_context_model",
    "five_elements",
    "day_master",
    "stems_branches_roots",
    "interaction_network",
    "method_synthesis",
    "cross_method_analysis",
    "blind_school_cross_analysis",
    "root_seed_flower_fruit_map",
    "natal_portrait",
    "portrait_thesis",
    "complete_self_portrait",
    "family_system",
    "resource_relationship",
    "social_relationship_style",
    "relationship_system",
    "partner_profiles",
    "interaction_dynamics",
    "environment_and_mobility",
    "reality_domains",
    "domain_connections",
    "luck_cycle_themes",
    "annual_theme_activation",
    "monthly_theme_activation",
    "life_stages",
    "turning_points",
    "report_claim_ledger",
    "formation_chains",
    "domain_linkage_chains",
    "reality_candidate_pool",
    "candidate_relation_map",
    "not_inferable_register",
    "portrait_balance_audit",
    "uncertainty_register",
    "safety_boundaries",
}


def canonical_digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def delivery_decision(completed_methods: set[str]) -> tuple[str, bool, bool, bool]:
    completed_primary = completed_methods & PRIMARY_METHODS
    structural_anchor = bool(completed_primary & {"pattern_structure", "momentum_configuration"})
    reality_anchor = len(completed_primary & {"ten_god_dynamics", "root_seed_flower_fruit", "blind_school"}) >= 2
    timing_anchor = "timing_continuity" in completed_primary
    if completed_primary == PRIMARY_METHODS:
        decision = "full"
    elif len(completed_primary) >= 5 and structural_anchor and reality_anchor and timing_anchor:
        decision = "degraded"
    else:
        decision = "preliminary_only"
    return decision, structural_anchor, reality_anchor, timing_anchor


def build_method_audit(methods: list[dict[str, Any]]) -> dict[str, Any]:
    by_id = {str(item.get("method_id")): item for item in methods}
    completed = {method_id for method_id, item in by_id.items() if item.get("status") == "complete"}
    excluded = set(by_id) - completed
    failed = {
        method_id
        for method_id, item in by_id.items()
        if item.get("status") in {"blocked_input", "generation_failed"}
    }
    decision, structural, reality, timing = delivery_decision(completed)
    reasons = []
    for method_id in sorted(excluded):
        item = by_id[method_id]
        details = item.get("degradation_effects") or item.get("failure_reasons") or ["方法未完成"]
        reasons.append(f"{method_id}：{'；'.join(str(value) for value in details)}")
    return {
        "retry_limit": 3,
        "completed_method_ids": sorted(completed),
        "excluded_method_ids": sorted(excluded),
        "failed_method_ids": sorted(failed),
        "primary_completed_count": len(completed & PRIMARY_METHODS),
        "structural_anchor_complete": structural,
        "reality_anchor_complete": reality,
        "timing_anchor_complete": timing,
        "delivery_decision": decision,
        "degradation_reasons": reasons,
        "stage_validation_passed": True,
    }


def build_source_coverage_audit(methods: list[dict[str, Any]]) -> dict[str, Any]:
    """Describe what the frozen method packets can support without inventing content."""
    candidates: dict[str, list[dict[str, Any]]] = {domain: [] for domain in REPORT_DOMAINS}
    for method in methods:
        if method.get("status") != "complete":
            continue
        method_id = str(method.get("method_id"))
        for hypothesis in method.get("reality_hypotheses") or []:
            domain = hypothesis.get("domain")
            if domain in candidates:
                candidates[str(domain)].append({
                    "hypothesis_id": str(hypothesis.get("hypothesis_id")),
                    "method_id": method_id,
                    "normalized_direction": str(hypothesis.get("normalized_direction")),
                })

    counts = {domain: len(candidates[domain]) for domain in sorted(REPORT_DOMAINS)}
    primary_methods = {
        domain: sorted({
            item["method_id"] for item in candidates[domain]
            if item["method_id"] in PRIMARY_METHODS
        })
        for domain in sorted(REPORT_DOMAINS)
    }
    reviews = {
        domain: sum(
            1 for method in methods
            if method.get("status") == "complete"
            and any(item.get("domain") == domain for item in method.get("domain_assessments") or [])
        )
        for domain in sorted(ALL_REALITY_DOMAINS)
    }
    method_by_id = {str(method.get("method_id")): method for method in methods}
    love_anchor_statuses: dict[str, str] = {}
    for method_id in sorted(LOVE_PARTNER_ANCHORS):
        method = method_by_id.get(method_id)
        if not method or method.get("status") != "complete":
            love_anchor_statuses[method_id] = "method_unavailable"
            continue
        assessment = next(
            (item for item in method.get("domain_assessments") or [] if item.get("domain") == "love_partner"),
            None,
        )
        love_anchor_statuses[method_id] = str(assessment.get("status")) if assessment else "method_unavailable"
    uncovered = sorted(domain for domain, count in counts.items() if count == 0)
    single = sorted(domain for domain, methods_for_domain in primary_methods.items() if len(methods_for_domain) == 1)
    multiple = sorted(domain for domain, methods_for_domain in primary_methods.items() if len(methods_for_domain) >= 2)
    love_anchor_complete = all(
        status in {"supported", "insufficient_evidence"}
        for status in love_anchor_statuses.values()
    )
    return {
        "report_domain_candidate_counts": counts,
        "report_domain_primary_method_ids": primary_methods,
        "domain_review_counts": reviews,
        "love_partner_anchor_statuses": love_anchor_statuses,
        "love_partner_anchor_review_complete": love_anchor_complete,
        "topic_isolation_required": True,
        "uncovered_report_domains": uncovered,
        "single_primary_method_domains": single,
        "multi_primary_method_domains": multiple,
        "semantic_clustering_required": True,
        "status": "ready_with_gaps" if uncovered or not love_anchor_complete else "ready",
    }
