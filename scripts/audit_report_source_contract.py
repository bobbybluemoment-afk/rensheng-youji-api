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
    evidence_retention_gaps,
    focus_domain,
    mandatory_candidate_bounds,
    report_total_cjk_bounds,
)
from report_pipeline import STAGES as STATUS_STAGES


STALE_RULES = (
    "2—4条 `mandatory_candidate_ids`",
    "two to four ranked mandatory candidates",
    "六个领域各至少包含三个判断家族",
    "每个领域至少覆盖三个不同判断家族",
    "完整人生主线写3—4个自然段、500—700个汉字；每个领域写3—4个自然段、500—700个汉字",
    "完整人生主线与六领域各500—700字",
    "每个自然段至少映射两个实体化Core判断，完整人生主线和六领域",
    "`domain_mechanisms`：至少两个领域自身机制",
    "证据缺口模式0条",
    "写作前先为每段选择至少两个 `selected_claims`",
    "六个领域保持相同篇幅范围",
)

MAINTAINED_TEXTS = (
    "scripts/audit_claim_diversity.py",
    "skills/rensheng-youji-growth-map/SKILL.md",
    "skills/rensheng-youji-growth-map/references/full-report.md",
    "skills/rensheng-youji-growth-map/references/report-schema.md",
    "internal/rensheng-youji-mingli-core/SKILL.md",
    "internal/rensheng-youji-mingli-core/references/analysis-workflow.md",
    "internal/rensheng-youji-mingli-core/references/domain-independent-analysis.md",
    "internal/rensheng-youji-mingli-core/references/method-failure-and-recovery.md",
    "internal/rensheng-youji-mingli-core/references/post-calibration-report-selection.md",
    "internal/rensheng-youji-mingli-core/references/report-grade-reality-mapping.md",
    "internal/rensheng-youji-report-content-brief/SKILL.md",
    "internal/rensheng-youji-report-content-brief/references/content-brief.md",
    "internal/rensheng-youji-report-writer/SKILL.md",
    "internal/rensheng-youji-report-writer/references/portrait-writing.md",
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
    if focus_domain("事业发展") != "career" or focus_domain("财务与收入") != "finance_resources":
        errors.append("User focus phrases are not mapped to report domains deterministically")
    rich_but_lost = {
        "independent_method_analyses": [{
            "method_id": f"m{index}", "status": "complete",
            "reality_hypotheses": [{"hypothesis_id": f"h{index}", "domain": "finance_resources", "normalized_direction": f"方向{index}"}],
        } for index in range(4)],
        "report_claim_ledger": [{"domain": "finance_resources", "method_hypothesis_ids": ["h0"]}],
    }
    if not evidence_retention_gaps(rich_but_lost):
        errors.append("Rich multi-method evidence can still be silently collapsed in Core")

    one_timing_claim: dict[str, Any] = {
        "report_claim_ledger": [{
            "claim_id": "stage-1",
            "domain": "career",
            "origin": "timing_baseline",
            "claim_class": "stage_judgment",
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

    status_stage_ids = [stage_id for stage_id, *_ in STATUS_STAGES]
    if status_stage_ids != stage_ids:
        errors.append("pipeline-contract.json and report_pipeline.py disagree on production stage order")

    for relative in MAINTAINED_TEXTS:
        path = root / relative
        text = path.read_text(encoding="utf-8")
        for stale in STALE_RULES:
            if stale in text:
                errors.append(f"Stale report-source rule remains in {path.relative_to(root)}: {stale}")

    delivery_text = (root / "skills/rensheng-youji-growth-map/scripts/generate_full_report.py").read_text(encoding="utf-8")
    renderer_text = (root / "skills/rensheng-youji-growth-map/scripts/render_report.py").read_text(encoding="utf-8")
    if 'CURRENT_CALIBRATION_SCHEMA = "3.0.0"' not in delivery_text or 'CURRENT_CALIBRATION_SCHEMA = "3.0.0"' not in renderer_text:
        errors.append("Current delivery and report validation must share calibration schema 3.0.0")
    resolver_text = (root / "scripts/resolve_report_sources.py").read_text(encoding="utf-8")
    brief_skill_text = (root / "internal/rensheng-youji-report-content-brief/SKILL.md").read_text(encoding="utf-8")
    if 'parser.add_argument("--focus"' not in resolver_text or '--focus "事业发展"' not in brief_skill_text:
        errors.append("Current-question source resolution must receive the user focus explicitly")
    diversity_text = (root / "scripts/audit_claim_diversity.py").read_text(encoding="utf-8")
    core_validator_text = (root / "internal/rensheng-youji-mingli-core/scripts/validate_analysis_output.py").read_text(encoding="utf-8")
    if "evidence_retention_gaps" not in diversity_text or "evidence_retention_gaps" not in core_validator_text:
        errors.append("Core validator and quality audit must share the evidence-retention contract")
    writing_pack_text = (root / "internal/rensheng-youji-report-writer/scripts/build_report_writing_pack.py").read_text(encoding="utf-8")
    if "narrative_role" not in writing_pack_text or "index % count" in writing_pack_text:
        errors.append("Writing pack must use narrative roles instead of round-robin claim distribution")

    growth_skill_text = (root / "skills/rensheng-youji-growth-map/SKILL.md").read_text(encoding="utf-8")
    card_skill_text = (root / "internal/rensheng-youji-free-card-output/SKILL.md").read_text(encoding="utf-8")
    if "卡片没有独立校准流程" not in growth_skill_text or "命理结构、人生K线语义和原始判断仍来自校准前冻结的同一Core" not in growth_skill_text:
        errors.append("Growth-map Skill must preserve the embedded-card calibration boundary")
    if "卡片没有独立的五题校准流程" not in card_skill_text or "不得改写校准前冻结的命理结构、人生K线语义和原始判断" not in card_skill_text:
        errors.append("Free-card output Skill must preserve the standalone and embedded-card calibration boundary")
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
