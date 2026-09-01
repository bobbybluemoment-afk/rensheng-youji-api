#!/usr/bin/env python3
"""Audit report-source cardinalities and the pre-freeze quality gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from build_report_source_bundle import build
from report_source_contract import (
    MANDATORY_CANDIDATE_MAX,
    claim_diversity_gaps,
    mandatory_candidate_bounds,
    report_total_cjk_bounds,
)


STALE_RULES = (
    "2—4条 `mandatory_candidate_ids`",
    "two to four ranked mandatory candidates",
)


def audit(root: Path) -> list[str]:
    errors: list[str] = []
    schema_path = root / "internal/rensheng-youji-mingli-core/schemas/analysis-output.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    mandatory_schema = schema["$defs"]["domainSource"]["properties"]["mandatory_candidate_ids"]
    if mandatory_schema.get("maxItems") != MANDATORY_CANDIDATE_MAX:
        errors.append("Core Schema and report_source_contract disagree on mandatory candidate maximum")

    if mandatory_candidate_bounds([]) != (0, 0) or mandatory_candidate_bounds(["claim-1"]) != (1, 2):
        errors.append("Canonical mandatory candidate bounds are invalid")
    if claim_diversity_gaps([]) or claim_diversity_gaps([{"reality_dimension": "one"}]):
        errors.append("Sparse evidence must degrade instead of failing a fixed claim-count rule")
    if report_total_cjk_bounds(["normal"] * 8) != (4300, 6500):
        errors.append("Normal report total bounds changed unexpectedly")
    if report_total_cjk_bounds(["evidence_gap"] * 8)[0] >= 4300:
        errors.append("Degraded sections must lower the full-report minimum length")

    one_timing_claim: dict[str, Any] = {
        "report_claim_ledger": [{
            "claim_id": "stage-1",
            "domain": "career",
            "origin": "timing_baseline",
            "report_role": "primary",
            "calibration_status": "unverified",
            "confidence": "high",
            "coverage_tags": ["current_change"],
            "plain_claim": "当前阶段更需要把已经完成的成果正式记录下来。",
            "mechanism_family": "timing",
            "allowed_examples": [],
        }],
        "formation_chains": [],
        "domain_linkage_chains": [],
    }
    current = build(one_timing_claim)["current_stage_source"]
    if current.get("mandatory_candidate_ids") != ["stage-1"]:
        errors.append("A valid single current-stage claim is not preserved as one mandatory candidate")

    pipeline = json.loads((root / "internal/pipeline-contract.json").read_text(encoding="utf-8"))
    stages = pipeline.get("stages") or []
    stage_ids = [item.get("id") for item in stages if isinstance(item, dict)]
    try:
        audit_index = stage_ids.index("core_quality_audit")
        freeze_index = stage_ids.index("baseline_freeze")
    except ValueError:
        errors.append("Pipeline must declare core_quality_audit and baseline_freeze")
    else:
        if audit_index >= freeze_index:
            errors.append("Core quality audit must run before baseline freeze")
        freeze_stage = stages[freeze_index]
        if "core_quality_audit" not in (freeze_stage.get("inputs") or []):
            errors.append("Baseline freeze must consume the Core quality audit artifact")

    maintained_texts = (
        root / "scripts/audit_claim_diversity.py",
        root / "internal/rensheng-youji-mingli-core/references/post-calibration-report-selection.md",
        root / "internal/rensheng-youji-mingli-core/references/report-grade-reality-mapping.md",
    )
    for path in maintained_texts:
        text = path.read_text(encoding="utf-8")
        for stale in STALE_RULES:
            if stale in text:
                errors.append(f"Stale report-source rule remains in {path.relative_to(root)}: {stale}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    try:
        errors = audit(args.root.resolve())
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        errors = [str(exc)]
    print(json.dumps({"status": "ok" if not errors else "error", "errors": errors}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
