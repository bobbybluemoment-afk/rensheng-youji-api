#!/usr/bin/env python3
"""Single source of truth for the Core AI working contract and compiler-owned fields."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
CORE_SCHEMA_PATH = ROOT / "internal/rensheng-youji-mingli-core/schemas/analysis-output.schema.json"


# These fields are accepted for backward compatibility, but the production
# compiler always recalculates them.  Prompts must tell the AI to omit them.
COMPILER_OWNED_FIELDS: dict[str, tuple[str, ...]] = {
    "methodSynthesisCluster": ("supporting_method_ids", "independence_groups"),
    "reportClaim": (
        "evidence_ids", "supporting_methods", "report_role",
        "observable_scenes", "allowed_examples",
    ),
    "realityCandidate": ("source_layers", "evidence_ids", "relation_ids", "status"),
    "candidateRelation": ("evidence_ids",),
}


def _scan_refs(value: Any, refs: set[str]) -> None:
    if isinstance(value, dict):
        ref = value.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/$defs/"):
            refs.add(ref.rsplit("/", 1)[-1])
        for child in value.values():
            _scan_refs(child, refs)
    elif isinstance(value, list):
        for child in value:
            _scan_refs(child, refs)


def build_ai_schema(required_sections: set[str], targets: set[str] | None = None) -> dict[str, Any]:
    """Project the canonical Core Schema into the exact AI-visible working schema."""
    canonical = json.loads(CORE_SCHEMA_PATH.read_text(encoding="utf-8"))
    selected = required_sections if targets is None else required_sections & targets
    properties = {
        key: copy.deepcopy(canonical["properties"][key])
        for key in sorted(selected)
    }
    refs: set[str] = set()
    _scan_refs(properties, refs)
    while True:
        before = set(refs)
        for name in list(refs):
            _scan_refs(canonical["$defs"][name], refs)
        if refs == before:
            break
    definitions = {name: copy.deepcopy(canonical["$defs"][name]) for name in sorted(refs)}
    for definition_name, fields in COMPILER_OWNED_FIELDS.items():
        definition = definitions.get(definition_name)
        if not definition:
            continue
        definition["required"] = [
            item for item in definition.get("required", []) if item not in fields
        ]
        for field in fields:
            prop = definition.get("properties", {}).get(field)
            if isinstance(prop, dict):
                prop["description"] = "由确定性编译器计算；AI应省略，已有值也会被覆盖。"
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": sorted(selected),
        "properties": properties,
        "$defs": definitions,
    }


def compiler_owned_contract() -> dict[str, list[str]]:
    return {key: list(value) for key, value in sorted(COMPILER_OWNED_FIELDS.items())}


def compile_bookkeeping(
    semantic: dict[str, Any],
    method_analyses: list[dict[str, Any]],
    evidence_registry: list[dict[str, Any]],
    detail_registry: list[dict[str, Any]],
) -> dict[str, Any]:
    """Fill provenance bookkeeping deterministically without changing AI judgments."""
    result = copy.deepcopy(semantic)
    method_by_id = {str(item.get("method_id")): item for item in method_analyses}
    hypothesis_meta: dict[str, dict[str, Any]] = {}
    for method_id, method in method_by_id.items():
        evidence_by_conclusion = {
            str(item.get("conclusion_id")): list(item.get("evidence_ids") or [])
            for item in method.get("technical_conclusions") or []
        }
        for hypothesis in method.get("reality_hypotheses") or []:
            evidence_ids = sorted({
                evidence_id
                for conclusion_id in hypothesis.get("derived_from_conclusion_ids") or []
                for evidence_id in evidence_by_conclusion.get(str(conclusion_id), [])
            })
            hypothesis_meta[str(hypothesis.get("hypothesis_id"))] = {
                "method_id": method_id,
                "independence_group": str(method.get("independence_group", "")),
                "evidence_ids": evidence_ids,
            }

    evidence_by_id = {str(item.get("evidence_id")): item for item in evidence_registry}
    detail_by_id = {str(item.get("detail_atom_id")): item for item in detail_registry}
    role_by_class = {
        "primary_judgment": "primary",
        "independent_supplement": "supplemental",
        "conditional_judgment": "supplemental",
        "stage_judgment": "supplemental",
        "calibration_pending": "to_verify",
        "weak_candidate": "to_verify",
    }

    for cluster in (result.get("method_synthesis") or {}).get("clusters") or []:
        member_ids = [str(item) for item in cluster.get("member_hypothesis_ids") or []]
        methods = sorted({
            hypothesis_meta[item]["method_id"] for item in member_ids if item in hypothesis_meta
        })
        cluster["supporting_method_ids"] = methods
        cluster["independence_groups"] = sorted({
            hypothesis_meta[item]["independence_group"]
            for item in member_ids
            if item in hypothesis_meta and hypothesis_meta[item]["independence_group"]
        })

    claims = result.get("report_claim_ledger") or []
    claim_by_id: dict[str, dict[str, Any]] = {}
    for claim in claims:
        hypothesis_ids = [str(item) for item in claim.get("method_hypothesis_ids") or []]
        claim["supporting_methods"] = sorted({
            hypothesis_meta[item]["method_id"] for item in hypothesis_ids if item in hypothesis_meta
        })
        claim["evidence_ids"] = sorted({
            evidence_id
            for item in hypothesis_ids if item in hypothesis_meta
            for evidence_id in hypothesis_meta[item]["evidence_ids"]
        })
        if claim.get("claim_class") in role_by_class:
            claim["report_role"] = role_by_class[claim["claim_class"]]
        detail_ids = [str(item) for item in claim.get("source_detail_atom_ids") or []]
        scenes = list(dict.fromkeys(
            str(detail_by_id[item]["text"]) for item in detail_ids if item in detail_by_id
        ))
        claim["observable_scenes"] = scenes
        claim["allowed_examples"] = scenes
        claim_by_id[str(claim.get("claim_id"))] = claim

    candidates = result.get("reality_candidate_pool") or []
    candidate_by_id: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        linked_claims = [
            claim_by_id[item]
            for item in candidate.get("related_claim_ids") or []
            if item in claim_by_id
        ]
        candidate["evidence_ids"] = sorted({
            evidence_id for claim in linked_claims for evidence_id in claim.get("evidence_ids") or []
        })
        supporting_methods = {
            method_id for claim in linked_claims for method_id in claim.get("supporting_methods") or []
        }
        layers: set[str] = set()
        if len(supporting_methods) >= 2:
            layers.add("cross_method")
        if "root_seed_flower_fruit" in supporting_methods:
            layers.add("root_seed_flower_fruit_map")
        if "ten_god_dynamics" in supporting_methods:
            layers.add("resource_relationship")
        if "blind_school" in supporting_methods:
            layers.add("cross_method_analysis")
        if "timing_continuity" in supporting_methods:
            layers.update({"luck_cycle_themes", "annual_theme_activation"})
        if candidate.get("candidate_kind") == "timed_event":
            layers.add("annual")
        elif candidate.get("candidate_kind") == "current_stage":
            layers.add("luck")
        if not layers:
            layers.add("chart")
        candidate["source_layers"] = sorted(layers)
        candidate["status"] = "unverified"
        candidate["relation_ids"] = []
        candidate_by_id[str(candidate.get("candidate_id"))] = candidate

    for relation in result.get("candidate_relation_map") or []:
        relation_id = str(relation.get("relation_id"))
        linked_candidates = [
            candidate_by_id[item]
            for item in relation.get("candidate_ids") or []
            if item in candidate_by_id
        ]
        relation["evidence_ids"] = sorted({
            evidence_id
            for candidate in linked_candidates
            for evidence_id in candidate.get("evidence_ids") or []
        })
        for candidate in linked_candidates:
            candidate["relation_ids"].append(relation_id)
    for candidate in candidates:
        candidate["relation_ids"] = sorted(set(candidate.get("relation_ids") or []))
    return result
