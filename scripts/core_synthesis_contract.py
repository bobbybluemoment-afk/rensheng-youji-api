#!/usr/bin/env python3
"""Shared contract for the method-packet to complete-Core production bridge."""

from __future__ import annotations

import hashlib
import json
from typing import Any


CORE_VERSION = "0.12.0"
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

DETERMINISTIC_CORE_SECTIONS = {
    "analysis_meta",
    "chart_facts",
    "chart_audit",
    "independent_method_analyses",
    "method_execution_audit",
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
