#!/usr/bin/env python3
"""把Core中的完整判断实体写入报告事实提纲，避免写作模型只看到编号。"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def canonical_digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def snapshot(claim: dict[str, Any]) -> dict[str, Any]:
    keys = ("claim_id", "domain", "reality_dimension", "claim", "mechanism_chain", "evidence_ids", "supporting_methods", "allowed_examples", "counterevidence", "confidence", "unsupported_extensions", "calibration_status", "origin")
    body = {key: claim[key] for key in keys}
    return {**body, "source_sha256": canonical_digest(body)}


def exact_snapshot(value: dict[str, Any]) -> dict[str, Any]:
    body = json.loads(json.dumps(value, ensure_ascii=False))
    return {"value": body, "source_sha256": canonical_digest(body)}


def enrich_section(section: dict[str, Any], analysis: dict[str, Any], ledger: dict[str, dict[str, Any]]) -> None:
    ids = section.get("claim_ids") or []
    missing = [claim_id for claim_id in ids if claim_id not in ledger]
    if missing:
        raise ValueError("提纲引用了不存在的判断：" + "、".join(missing))
    selected = [snapshot(ledger[claim_id]) for claim_id in ids]
    section["selected_claims"] = selected
    emphasis_ids = section.get("emphasis_claim_ids") or []
    section["emphasis_claims"] = [snapshot(ledger[claim_id]) for claim_id in emphasis_ids]
    evidence_ids = list(dict.fromkeys(evidence_id for item in selected for evidence_id in item["evidence_ids"]))
    evidence_index = {item["evidence_id"]: item for item in analysis["evidence_registry"]}
    missing_evidence = [evidence_id for evidence_id in evidence_ids if evidence_id not in evidence_index]
    if missing_evidence:
        raise ValueError("判断引用了不存在的实体证据：" + "、".join(missing_evidence))
    section["selected_evidence"] = [exact_snapshot(evidence_index[evidence_id]) for evidence_id in evidence_ids]

    formation_index = {item["chain_id"]: item for item in analysis["formation_chains"]}
    linkage_index = {item["chain_id"]: item for item in analysis["domain_linkage_chains"]}
    formation_ids = section.get("formation_chain_ids") or []
    linkage_ids = section.get("linkage_chain_ids") or []
    section["selected_formation_chains"] = [exact_snapshot(formation_index[item]) for item in formation_ids if item in formation_index]
    section["selected_linkage_chains"] = [exact_snapshot(linkage_index[item]) for item in linkage_ids if item in linkage_index]

    related_candidates = [
        item for item in analysis["reality_candidate_pool"]
        if set(item.get("related_claim_ids") or []) & set(ids) and item.get("status") != "reject"
    ]
    section["selected_reality_candidates"] = [exact_snapshot(item) for item in related_candidates]
    related_candidate_ids = {item["candidate_id"] for item in related_candidates}
    relations = [item for item in analysis["candidate_relation_map"] if set(item.get("candidate_ids") or []) & related_candidate_ids]
    section["selected_candidate_relations"] = [exact_snapshot(item) for item in relations]

    blind_images = [
        item for item in analysis["blind_school_cross_analysis"]["reality_image_candidates"]
        if set(item.get("evidence_ids") or []) & set(evidence_ids)
    ]
    section["selected_blind_images"] = [exact_snapshot(item) for item in blind_images]
    lifecycles = [
        item for item in analysis["root_seed_flower_fruit_map"]["domain_lifecycles"]
        if set(item.get("evidence_ids") or []) & set(evidence_ids)
    ]
    section["selected_domain_lifecycles"] = [exact_snapshot(item) for item in lifecycles]
    section["portrait_context"] = exact_snapshot(analysis["portrait_thesis"])

    relevant_updates = [item for item in analysis["calibration_delta"]["claim_updates"] if item.get("claim_id") in set(ids)]
    section["calibration_context"] = {
        "candidate_statuses": {item["candidate_id"]: item["status"] for item in related_candidates},
        "claim_updates": [exact_snapshot(item) for item in relevant_updates],
        "rejected_candidate_ids": sorted(set(analysis["calibration_delta"]["rejected"]) & related_candidate_ids),
    }
    baseline = sum(item["origin"] in {"chart_baseline", "timing_baseline"} for item in selected)
    calibrated = sum(item["origin"] == "user_fact_refinement" for item in selected)
    section["source_balance"] = {
        "baseline_count": baseline,
        "calibrated_refinement_count": calibrated,
        "baseline_ratio": round(baseline / len(selected), 4) if selected else 0,
        "method_layers": sorted({method for item in selected for method in item["supporting_methods"]}),
    }


def materialize(selection: dict[str, Any], analysis: dict[str, Any]) -> dict[str, Any]:
    result = json.loads(json.dumps(selection, ensure_ascii=False))
    meta = analysis["analysis_meta"]
    is_v08 = meta.get("core_version") == "0.8.0"
    result["schema_version"] = "1.3.0" if is_v08 else "1.2.0"
    result.setdefault("source", {}).update({"analysis_id": meta["analysis_id"], "core_version": meta["core_version"], "analysis_sha256": canonical_digest(analysis)})
    ledger = {item["claim_id"]: item for item in analysis["report_claim_ledger"]}
    sections = [result["life_overview"], *result["dimensions"], result["current_question"]]
    if is_v08:
        source_bundle = analysis["report_source_bundle"]
        source_pairs = [
            (result["life_overview"], source_bundle["life_narrative_source"]),
            *[(section, source_bundle["dimensions"][section["id"]]) for section in result["dimensions"]],
            (result["current_question"], source_bundle["current_stage_source"]),
        ]
        locked = ("claim_ids", "formation_chain_ids", "linkage_chain_ids", "coverage", "domain_specific_claim_ids", "mainline_claim_ids", "emphasis_claim_ids", "domain_mechanisms", "survives_without_mainline")
        for section, source_section in source_pairs:
            for key in locked:
                section[key] = json.loads(json.dumps(source_section[key], ensure_ascii=False))
    for section in sections:
        enrich_section(section, analysis, ledger)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("selection", type=Path)
    parser.add_argument("--analysis", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = materialize(json.loads(args.selection.read_text(encoding="utf-8")), json.loads(args.analysis.read_text(encoding="utf-8")))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "ok", "output": str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
