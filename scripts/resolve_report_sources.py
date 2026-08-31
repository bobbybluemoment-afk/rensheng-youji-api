#!/usr/bin/env python3
"""Compile a frozen Core candidate pool into post-calibration report sources."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from report_source_contract import BASE_COVERAGE, DIMENSIONS, delivery_mode, delivery_rule, required_coverage


def digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _ordered_unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _resolve_section(source: dict[str, Any], ledger: dict[str, dict[str, Any]], domain: str | None, emphasis_limit: int = 1) -> dict[str, Any]:
    priority = source.get("claim_priority") or source.get("claim_ids") or []
    pool = set(source.get("claim_ids") or [])
    rejected = [claim_id for claim_id in priority if ledger.get(claim_id, {}).get("calibration_status") == "reject"]
    available = [claim_id for claim_id in priority if claim_id in pool and claim_id in ledger and claim_id not in rejected]
    specific_pool = set(source.get("domain_specific_claim_ids") or [])
    mainline_pool = set(source.get("mainline_claim_ids") or [])
    coverage_map = source.get("coverage_claim_map") or {}
    required = list(required_coverage(domain))

    selected: list[str] = []

    def add(claim_id: str) -> bool:
        if claim_id not in available or claim_id in selected:
            return False
        selected.append(claim_id)
        return True

    # Cover each required person-description axis with a domain-specific fallback first.
    for tag in required:
        candidates = [item for item in coverage_map.get(tag, []) if item in specific_pool]
        candidates.extend(item for item in coverage_map.get(tag, []) if item not in candidates)
        for claim_id in candidates:
            if add(claim_id):
                break

    # Keep enough domain-specific claims and at least two mechanism families when possible.
    for claim_id in available:
        if len([item for item in selected if item in specific_pool]) >= 4:
            break
        if claim_id in specific_pool:
            add(claim_id)
    mechanism_families = {ledger[item].get("mechanism_family") for item in selected if item in ledger}
    for claim_id in available:
        family = ledger[claim_id].get("mechanism_family")
        if len(mechanism_families) >= 2:
            break
        if family not in mechanism_families and claim_id not in mainline_pool and add(claim_id):
            mechanism_families.add(family)

    # Fill to a normal target without allowing the shared life-mainline to dominate.
    for claim_id in available:
        if len(selected) >= 8:
            break
        if claim_id in mainline_pool:
            future_count = len(selected) + (claim_id not in selected)
            future_mainline = len([item for item in selected if item in mainline_pool]) + (claim_id not in selected)
            if future_mainline / max(future_count, 1) > 0.30:
                continue
        add(claim_id)

    achieved = [tag for tag in required if set(coverage_map.get(tag) or []) & set(selected)]
    missing = [tag for tag in required if tag not in achieved]
    mode = delivery_mode(len(available), missing)
    rule = delivery_rule(mode)
    target_minimum = rule["minimum_claims"]
    if len(selected) < target_minimum:
        for claim_id in available:
            if add(claim_id) and len(selected) >= target_minimum:
                break

    selected_specific = [item for item in selected if item in specific_pool]
    selected_mainline = [item for item in selected if item in mainline_pool]
    mandatory_candidates = source.get("mandatory_candidate_ids") or []
    mandatory_limit = 2 if mode == "normal" else 1
    mandatory = [item for item in mandatory_candidates if item in selected][:mandatory_limit]
    if not mandatory and selected:
        mandatory = (selected_specific or selected)[:1]
    emphasis = [item for item in source.get("emphasis_candidate_ids") or [] if item in selected][:emphasis_limit]
    mechanisms = _ordered_unique([
        str(ledger[item].get("mechanism_family"))
        for item in selected
        if ledger.get(item, {}).get("mechanism_family")
    ])
    baseline_preferred = [item for item in priority if item in pool][: len(selected)]
    replacements = [
        {"excluded_claim_id": old, "replacement_claim_id": new}
        for old, new in zip(baseline_preferred, selected)
        if old != new and old in rejected
    ]
    return {
        "claim_ids": selected,
        "domain_specific_claim_ids": selected_specific,
        "mainline_claim_ids": selected_mainline,
        "mandatory_claim_ids": mandatory,
        "emphasis_claim_ids": emphasis,
        "domain_mechanisms": mechanisms,
        "survives_without_mainline": len([item for item in selected if item not in mainline_pool]) >= rule["minimum_claims"],
        "formation_chain_ids": source.get("formation_chain_ids") or [],
        "linkage_chain_ids": source.get("linkage_chain_ids") or [],
        "coverage": achieved,
        "missing_coverage": missing,
        "delivery_mode": mode,
        "rejected_claim_ids": rejected,
        "replacement_log": replacements,
        "evidence_gaps": _ordered_unique((source.get("evidence_gaps") or []) + (["校准后可用判断不足，章节按证据缩短。"] if mode != "normal" else [])),
    }


def resolve(analysis: dict[str, Any]) -> dict[str, Any]:
    meta = analysis.get("analysis_meta") or {}
    if meta.get("core_version") != "0.9.0":
        raise ValueError("Post-calibration source resolution requires core_version=0.9.0")
    ledger = {item.get("claim_id"): item for item in analysis.get("report_claim_ledger") or [] if isinstance(item, dict)}
    source_bundle = analysis.get("report_source_bundle") or {}
    dimensions = source_bundle.get("dimensions") or {}
    result = {
        "schema_version": "1.0.0",
        "source": {
            "analysis_id": meta.get("analysis_id"),
            "core_version": meta.get("core_version"),
            "analysis_sha256": digest(analysis),
        },
        "life_overview": _resolve_section(source_bundle.get("life_narrative_source") or {}, ledger, None, 2),
        "dimensions": {domain: _resolve_section(dimensions.get(domain) or {}, ledger, domain) for domain in DIMENSIONS},
        "current_question": _resolve_section(source_bundle.get("current_stage_source") or {}, ledger, None, 1),
    }
    result["resolved_sha256"] = digest({key: value for key, value in result.items() if key != "resolved_sha256"})
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("analysis", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = resolve(json.loads(args.analysis.read_text(encoding="utf-8")))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "ok", "output": str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
