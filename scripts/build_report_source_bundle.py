#!/usr/bin/env python3
"""Build report_source_bundle deterministically from the validated claim ledger."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from report_source_contract import BASE_COVERAGE, DIMENSIONS, required_coverage


def _ordered_unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _priority(claim: dict[str, Any]) -> tuple[int, int, str]:
    role_rank = {"primary": 0, "supplemental": 1}.get(claim.get("report_role"), 2)
    confidence_rank = {"high": 0, "medium": 1, "to_verify": 2}.get(claim.get("confidence"), 3)
    return role_rank, confidence_rank, str(claim.get("claim_id", ""))


def _chain_ids(items: list[dict[str, Any]], field: str, domain: str | None) -> list[str]:
    result: list[str] = []
    for item in items:
        domains = set(item.get(field) or [])
        if domain is None or domain in domains:
            identifier = item.get("chain_id")
            if isinstance(identifier, str):
                result.append(identifier)
    return result


def _source(
    claims: list[dict[str, Any]],
    domain: str | None,
    formations: list[dict[str, Any]],
    linkages: list[dict[str, Any]],
    emphasis_limit: int = 1,
) -> dict[str, Any]:
    eligible = [
        item for item in claims
        if item.get("report_role") in {"primary", "supplemental"}
        and item.get("calibration_status") != "reject"
        and (domain is None or item.get("domain") == domain)
    ]
    eligible.sort(key=_priority)
    if domain is None:
        selected: list[dict[str, Any]] = []
        for name in DIMENSIONS:
            match = next((item for item in eligible if item.get("domain") == name), None)
            if match is not None:
                selected.append(match)
        for item in eligible:
            if len(selected) >= 6:
                break
            if item not in selected:
                selected.append(item)
        eligible = selected
    else:
        eligible = eligible[:6]

    claim_ids = [str(item["claim_id"]) for item in eligible]
    coverage_map: dict[str, list[str]] = {}
    for item in eligible:
        for tag in item.get("coverage_tags") or []:
            coverage_map.setdefault(str(tag), []).append(str(item["claim_id"]))
    coverage_map = {key: _ordered_unique(value) for key, value in coverage_map.items()}
    coverage = list(coverage_map)
    expected = set(required_coverage(domain)) if domain in DIMENSIONS else set(BASE_COVERAGE)
    missing = sorted(expected - set(coverage))
    mechanisms = _ordered_unique([str(item.get("mechanism_family", "")) for item in eligible])
    primary_ids = [str(item["claim_id"]) for item in eligible if item.get("report_role") == "primary"]
    mandatory_pool = primary_ids or claim_ids
    emphasis = [
        str(item["claim_id"]) for item in eligible
        if item.get("report_role") == "primary" and item.get("confidence") == "high"
    ][:emphasis_limit]
    concrete = _ordered_unique([
        str(example)
        for item in eligible
        for example in (item.get("allowed_examples") or [])
    ])
    return {
        "summary_materials": [str(item.get("plain_claim") or item.get("claim")) for item in eligible],
        "claim_ids": claim_ids,
        "claim_priority": claim_ids,
        "domain_specific_claim_ids": claim_ids,
        "mainline_claim_ids": [],
        "mandatory_candidate_ids": mandatory_pool[:2],
        "emphasis_candidate_ids": emphasis,
        "domain_mechanisms": mechanisms[: max(0, 2 if len(claim_ids) >= 4 else 1 if claim_ids else 0)],
        "survives_without_mainline": bool(claim_ids),
        "formation_chain_ids": _chain_ids(formations, "linked_domains", domain),
        "linkage_chain_ids": _chain_ids(linkages, "affected_domains", domain),
        "concrete_candidates": concrete,
        "coverage": coverage,
        "coverage_claim_map": coverage_map,
        "evidence_gaps": [f"缺少{tag}对应的独立方法判断，章节按证据降级。" for tag in missing],
    }


def build(analysis: dict[str, Any]) -> dict[str, Any]:
    claims = [item for item in analysis.get("report_claim_ledger") or [] if isinstance(item, dict)]
    formations = [item for item in analysis.get("formation_chains") or [] if isinstance(item, dict)]
    linkages = [item for item in analysis.get("domain_linkage_chains") or [] if isinstance(item, dict)]
    timing_claims = [item for item in claims if item.get("origin") == "timing_baseline"]
    return {
        "life_narrative_source": _source(claims, None, formations, linkages, 2),
        "dimensions": {
            domain: _source(claims, domain, formations, linkages)
            for domain in DIMENSIONS
        },
        "current_stage_source": _source(timing_claims or claims, None, formations, linkages, 1),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("analysis", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        analysis = json.loads(args.analysis.read_text(encoding="utf-8"))
        analysis["report_source_bundle"] = build(analysis)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "ok", "output": str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
