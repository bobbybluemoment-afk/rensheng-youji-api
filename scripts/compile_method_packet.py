#!/usr/bin/env python3
"""Compile one compact method semantic answer into the canonical production packet."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
CORE_SCRIPTS = ROOT / "internal/rensheng-youji-mingli-core/scripts"
sys.path.insert(0, str(CORE_SCRIPTS))
sys.path.insert(0, str(ROOT / "scripts"))

from core_synthesis_contract import ALL_METHODS, PARTIAL_METHODS, canonical_digest  # noqa: E402
from validate_method_packet import GROUPS, validate as validate_packet  # noqa: E402
from validate_method_semantic_patch import DOMAINS, validate as validate_patch  # noqa: E402


METHOD_NAMES = {
    "pattern_structure": "格局法", "momentum_configuration": "气势与成象",
    "climate_adjustment": "调候法", "ten_god_dynamics": "十神动力",
    "root_seed_flower_fruit": "根苗花果", "blind_school": "盲派宾主体用与做功",
    "timing_continuity": "大运流年连续性", "position_relationship": "宫位六亲与位置关系",
    "stem_branch_dynamics": "干支动力",
}


def compile_packet(method_input: dict[str, Any], patch: dict[str, Any], method_id: str) -> dict[str, Any]:
    errors = validate_patch(patch, method_id)
    if errors:
        raise ValueError("；".join(errors))
    status = str(patch["result"])
    if status != "complete":
        packet = {
            "method_analysis": {
                "method_id": method_id,
                "tier": "partial" if method_id in PARTIAL_METHODS else "primary",
                "independence_group": GROUPS[method_id],
                "status": status,
                "attempt_count": 3 if status == "generation_failed" else 1,
                "failure_reasons": patch["failure_reasons"],
                "degradation_effects": patch["degradation_effects"],
                "input_scope": "chart_only_topic_isolated",
                "method_input_sha256": canonical_digest(method_input),
                "input_fact_refs": [] if status == "blocked_input" else ["chart_facts"],
                "source_method_ids_read": [],
                "technical_conclusions": [],
                "reality_hypotheses": [],
                "domain_assessments": [],
                "limitations": patch["limitations"],
            },
            "evidence_registry": [],
        }
    else:
        evidence_registry: list[dict[str, Any]] = []
        conclusions: list[dict[str, Any]] = []
        input_refs: set[str] = set()
        for conclusion_number, source in enumerate(patch["technical_conclusions"], 1):
            evidence_ids = []
            for source_evidence in source["evidence"]:
                evidence_number = len(evidence_registry) + 1
                evidence_id = f"evidence_{method_id}_{evidence_number:02d}"
                evidence_ids.append(evidence_id)
                input_refs.update(source_evidence["chart_refs"])
                evidence_registry.append({
                    "evidence_id": evidence_id,
                    "source_layer": source_evidence["source_layer"],
                    "method": METHOD_NAMES[method_id],
                    "method_id": method_id,
                    "independence_group": GROUPS[method_id],
                    "chart_refs": source_evidence["chart_refs"],
                    "observation": source_evidence["observation"],
                    "interpretation": source_evidence["interpretation"],
                    "limitations": source_evidence["limitations"],
                    "confidence": source_evidence["confidence"],
                })
            input_refs.update(source["chart_refs"])
            conclusions.append({
                "conclusion_id": f"mc_{method_id}_{conclusion_number:02d}",
                "statement": source["statement"],
                "mechanism_chain": source["mechanism_chain"],
                "chart_refs": source["chart_refs"],
                "evidence_ids": evidence_ids,
                "conditions": source["conditions"],
                "counterconditions": source["counterconditions"],
                "time_scope": source["time_scope"],
                "confidence": source["confidence"],
            })
        hypotheses = []
        for number, source in enumerate(patch["reality_hypotheses"], 1):
            hypotheses.append({
                "hypothesis_id": f"mh_{method_id}_{number:02d}",
                "derived_from_conclusion_ids": [
                    conclusions[index - 1]["conclusion_id"]
                    for index in source["derived_from_conclusion_numbers"]
                ],
                "domain": source["domain"],
                "normalized_direction": source["normalized_direction"],
                "statement": source["statement"],
                "observable_indicators": source["observable_indicators"],
                "conditions": source["conditions"],
                "counterevidence": source["counterevidence"],
                "unsupported_extensions": source["unsupported_extensions"],
                "time_scope": source["time_scope"],
                "reality_confirmation": "unverified",
            })
        limits = {item["domain"]: item for item in patch["domain_limits"]}
        assessments = []
        for domain in sorted(DOMAINS):
            domain_ids = [item["hypothesis_id"] for item in hypotheses if item["domain"] == domain]
            if domain_ids:
                assessments.append({
                    "domain": domain, "status": "supported", "hypothesis_ids": domain_ids,
                    "reasoning": f"本方法形成{len(domain_ids)}条该领域现实候选。",
                })
            else:
                limit = limits[domain]
                assessments.append({
                    "domain": domain, "status": limit["status"], "hypothesis_ids": [],
                    "reasoning": limit["reasoning"],
                })
        packet = {
            "method_analysis": {
                "method_id": method_id,
                "tier": "partial" if method_id in PARTIAL_METHODS else "primary",
                "independence_group": GROUPS[method_id],
                "status": "complete",
                "attempt_count": 1,
                "failure_reasons": [],
                "degradation_effects": [],
                "input_scope": "chart_only_topic_isolated",
                "method_input_sha256": canonical_digest(method_input),
                "input_fact_refs": sorted(input_refs),
                "source_method_ids_read": [],
                "technical_conclusions": conclusions,
                "reality_hypotheses": hypotheses,
                "domain_assessments": assessments,
                "limitations": patch["limitations"],
            },
            "evidence_registry": evidence_registry,
        }
    packet_errors = validate_packet(packet, method_id)
    if packet_errors:
        raise ValueError("编译后的正式方法包无效：" + "；".join(packet_errors))
    return packet


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--method-input", type=Path, required=True)
    parser.add_argument("--semantic-patch", type=Path, required=True)
    parser.add_argument("--method", required=True, choices=sorted(ALL_METHODS))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        method_input = json.loads(args.method_input.read_text(encoding="utf-8"))
        patch = json.loads(args.semantic_patch.read_text(encoding="utf-8"))
        packet = compile_packet(method_input, patch, args.method)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")
    except (OSError, KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "ok", "output": str(args.output), "method": args.method}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
