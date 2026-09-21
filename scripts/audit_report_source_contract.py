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
    delivery_mode,
    focus_domain,
    mandatory_candidate_bounds,
    report_total_cjk_bounds,
    synthesis_disposition_gaps,
)
from report_pipeline import STAGES as STATUS_STAGES
from calibration_state_contract import CALIBRATION_STATUS_VALUES


STALE_RULES = (
    "2—4条 `mandatory_candidate_ids`",
    "two to four ranked mandatory candidates",
    "六个领域各至少包含三个判断家族",
    "每个领域至少覆盖三个不同判断家族",
    "完整人生主线写3—4个自然段、500—700个汉字；每个领域写3—4个自然段、500—700个汉字",
    "完整人生主线与六领域各500—700字",
    "每个自然段至少映射两个实体化Core判断",
    "minimum_mapped = 2 if",
    "at least two distinct claims per",
    "`domain_mechanisms`：至少两个领域自身机制",
    "证据缺口模式0条",
    "写作前先为每段选择至少两个 `selected_claims`",
    "六个领域保持相同篇幅范围",
    "`editorial_review` 只保存 `review_id` 和 `version=2.4.0`",
    "至少三个内容区发生实际编辑",
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
    "internal/rensheng-youji-mingli-core/references/interpretive-spine-and-detail-retention.md",
    "internal/rensheng-youji-report-content-brief/SKILL.md",
    "internal/rensheng-youji-report-content-brief/references/content-brief.md",
    "internal/rensheng-youji-report-writer/SKILL.md",
    "internal/rensheng-youji-report-writer/references/portrait-writing.md",
    "internal/rensheng-youji-chinese-editor/references/natural-chinese.md",
)


def audit(root: Path) -> list[str]:
    errors: list[str] = []
    schema_path = root / "internal/rensheng-youji-mingli-core/schemas/analysis-output.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    mandatory_schema = schema["$defs"]["domainSource"]["properties"]["mandatory_candidate_ids"]
    if mandatory_schema.get("maxItems") != MANDATORY_CANDIDATE_MAX:
        errors.append("Core Schema and report_source_contract disagree on mandatory candidate maximum")
    top_required = set(schema.get("required") or [])
    claim_required = set(schema["$defs"]["reportClaim"].get("required") or [])
    if not {"reality_detail_registry", "interpretive_spine"}.issubset(top_required):
        errors.append("Core Schema must require both reality-detail retention and the interpretive spine")
    if not {"human_explanation", "source_detail_atom_ids", "observable_scenes", "helpful_effects", "possible_costs"}.issubset(claim_required):
        errors.append("Report claims can still lose explanation, reality scenes or two-sided effects")
    candidate_required = set(schema["$defs"]["realityCandidate"].get("required") or [])
    if not {"answerable_time_scope", "answerable_observation", "answerable_alternative"}.issubset(candidate_required):
        errors.append("Calibration candidates must provide past/current answerable text")
    status_enum = set(schema["$defs"]["reportClaim"]["properties"]["calibration_status"].get("enum") or [])
    if status_enum != CALIBRATION_STATUS_VALUES:
        errors.append("Core Schema and calibration-state contract disagree on claim statuses")

    if mandatory_candidate_bounds([]) != (0, 0) or mandatory_candidate_bounds(["claim-1"]) != (1, 2):
        errors.append("Canonical mandatory candidate bounds are invalid")
    if claim_diversity_gaps([]) or claim_diversity_gaps([{"reality_dimension": "one"}]):
        errors.append("Sparse evidence must degrade instead of failing a fixed claim-count rule")
    if report_total_cjk_bounds(["normal"] * 8) != (4300, 6500):
        errors.append("Normal report total bounds changed unexpectedly")
    if delivery_mode(4, []) != "normal" or delivery_mode(4, ["formation"]) != "shortened":
        errors.append("Delivery mode must let four complete diverse claims support a normal chapter")
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
    disposition_sample = {
        "independent_method_analyses": [{
            "method_id": "pattern_structure", "status": "complete",
            "reality_hypotheses": [{"hypothesis_id": "h1"}, {"hypothesis_id": "h2"}],
        }],
        "method_synthesis": {"clusters": [{
            "synthesis_id": "s1", "member_hypothesis_ids": ["h1", "h2"],
            "report_role": "supplemental",
        }]},
        "report_claim_ledger": [{"synthesis_ids": ["s1"], "method_hypothesis_ids": ["h1"]}],
    }
    if not synthesis_disposition_gaps(disposition_sample):
        errors.append("A method hypothesis can still disappear silently inside a Core synthesis cluster")

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
    baseline_text = (root / "scripts/core_baseline.py").read_text(encoding="utf-8")
    if "calibration_state_contract" not in core_validator_text or "calibration_state_contract" not in baseline_text:
        errors.append("Baseline freeze and calibrated Core validation must share one calibration-state contract")
    if "evidence_retention_gaps" not in diversity_text or "evidence_retention_gaps" not in core_validator_text:
        errors.append("Core validator and quality audit must share the evidence-retention contract")
    if "synthesis_disposition_gaps" not in diversity_text or "synthesis_disposition_gaps" not in core_validator_text:
        errors.append("Core validator and quality audit must share the complete information-disposition contract")
    selection_contract_text = (root / "scripts/calibration_selection_contract.py").read_text(encoding="utf-8")
    calibration_builder_text = (root / "skills/rensheng-youji-growth-map/scripts/build_calibration_questions.py").read_text(encoding="utf-8")
    if not all("calibration_selection_contract" in text for text in (diversity_text, core_validator_text, calibration_builder_text)):
        errors.append("Core pre-freeze audit and calibration builder must share one five-question selection contract")
    method_compiler_text = (root / "scripts/compile_method_packets.py").read_text(encoding="utf-8")
    method_gate_text = (root / "scripts/pipeline_gate.py").read_text(encoding="utf-8")
    method_validator_text = (root / "internal/rensheng-youji-mingli-core/scripts/validate_method_semantic_patch.py").read_text(encoding="utf-8")
    if not all("method_structure_contract" in text for text in (method_compiler_text, method_gate_text, method_validator_text)):
        errors.append("Method compiler, METHOD GATE and semantic validator must share one important-structure contract")
    if "feasible_sets" not in selection_contract_text or "valid_question_set" not in selection_contract_text:
        errors.append("The shared calibration selector does not expose one deterministic feasibility rule")
    calibration_validator_text = (root / "skills/rensheng-youji-growth-map/scripts/validate_calibration_questions.py").read_text(encoding="utf-8")
    calibration_reference_text = (root / "skills/rensheng-youji-growth-map/references/calibration.md").read_text(encoding="utf-8")
    if not all("visible_question_signature" in text for text in (selection_contract_text, calibration_validator_text)):
        errors.append("Calibration selection and final validation do not share the visible A/B deduplication contract")
    if "用户可见A/B题意必须各不相同" not in calibration_reference_text:
        errors.append("Calibration reference does not document visible A/B deduplication")
    writing_pack_text = (root / "internal/rensheng-youji-report-writer/scripts/build_report_writing_pack.py").read_text(encoding="utf-8")
    draft_validator_text = (root / "internal/rensheng-youji-report-writer/scripts/validate_report_draft.py").read_text(encoding="utf-8")
    if "narrative_role" not in writing_pack_text or "index % count" in writing_pack_text:
        errors.append("Writing pack must use narrative roles instead of round-robin claim distribution")
    if not all(field in writing_pack_text for field in ("interpretive_spine", "human_explanation", "observable_scenes", "helpful_effects", "possible_costs")):
        errors.append("Writing pack does not carry the complete Core explanation contract downstream")
    if 'minimum_mapped = 1 if not rule or mode != "evidence_gap" else 0' not in draft_validator_text:
        errors.append("Draft validator must accept one real Core claim per non-gap paragraph")
    brief_materializer_text = (root / "internal/rensheng-youji-report-content-brief/scripts/materialize_content_brief.py").read_text(encoding="utf-8")
    brief_validator_text = (root / "internal/rensheng-youji-report-content-brief/scripts/validate_content_brief.py").read_text(encoding="utf-8")
    explanation_fields = ("human_explanation", "source_detail_atom_ids", "observable_scenes", "helpful_effects", "possible_costs")
    if not all(field in brief_materializer_text and field in brief_validator_text for field in explanation_fields):
        errors.append("Content brief can still drop Core explanation or reality-detail fields")

    calibration_text = (root / "skills/rensheng-youji-growth-map/scripts/build_calibration_questions.py").read_text(encoding="utf-8")
    calibration_contract_text = (root / "scripts/calibration_question_contract.py").read_text(encoding="utf-8")
    if not all(field in calibration_text for field in ("answerable_time_scope", "answerable_observation", "answerable_alternative")) or "year > analysis_year" not in calibration_contract_text:
        errors.append("Calibration generator can still ask users to verify future events")
    if "calibration_question_contract" not in calibration_text or "calibration_question_contract" not in calibration_validator_text or "calibration_question_contract" not in core_validator_text:
        errors.append("Core, calibration selection and calibration validation must share one answerability contract")
    final_compiler_text = (root / "skills/rensheng-youji-growth-map/scripts/compile_final_report.py").read_text(encoding="utf-8")
    language_scanner_text = (root / "internal/rensheng-youji-chinese-editor/scripts/scan_report_language.py").read_text(encoding="utf-8")
    if "BODY_EMOTION_SAFETY_NOTE" not in final_compiler_text or "BODY_EMOTION_SAFETY_MARKERS" not in renderer_text:
        errors.append("The deterministic final compiler must produce the body-emotion safety note checked by the renderer")
    if "user_language_contract" not in core_validator_text or "user_language_contract" not in language_scanner_text or "user_language_contract" not in renderer_text:
        errors.append("Core, editor and final report must share the user-language phrase contract")
    if 'AI_JARGON = {"卡点", "卡住", "换轨", "兑现"' in renderer_text:
        errors.append("The renderer must not ban the natural phrase 兑现承诺 through a bare-word rule")
    natural_text = (root / "internal/rensheng-youji-chinese-editor/references/natural-chinese.md").read_text(encoding="utf-8")
    scanner_text = (root / "internal/rensheng-youji-chinese-editor/scripts/scan_report_language.py").read_text(encoding="utf-8")
    if "不要总结用户，要解释用户" not in natural_text or "AI黑话或生造表达" not in scanner_text or "本领域没有使用" not in scanner_text:
        errors.append("Natural-Chinese generation rules and deterministic language QA are incomplete")

    growth_skill_text = (root / "skills/rensheng-youji-growth-map/SKILL.md").read_text(encoding="utf-8")
    card_skill_text = (root / "internal/rensheng-youji-free-card-output/SKILL.md").read_text(encoding="utf-8")
    if "卡片没有独立校准流程" not in growth_skill_text or "命理结构、人生K线语义和原始判断仍来自校准前冻结的同一Core" not in growth_skill_text:
        errors.append("Growth-map Skill must preserve the embedded-card calibration boundary")
    if "每个自然段至少映射一条实体化Core判断" not in growth_skill_text or "章节整体必须覆盖全部必进判断" not in growth_skill_text:
        errors.append("Growth-map Skill must match the one-claim paragraph mapping used by the report validator")
    if "卡片没有独立的五题校准流程" not in card_skill_text or "不得改写校准前冻结的命理结构、人生K线语义和原始判断" not in card_skill_text:
        errors.append("Free-card output Skill must preserve the standalone and embedded-card calibration boundary")
    card_contract_text = (root / "internal/rensheng-youji-free-card-output/scripts/card_visual_contract.py").read_text(encoding="utf-8")
    card_assembler_text = (root / "scripts/assemble_free_card.py").read_text(encoding="utf-8")
    delivery_text = (root / "skills/rensheng-youji-growth-map/scripts/generate_full_report.py").read_text(encoding="utf-8")
    if 'CARD_ALGORITHM_VERSION = "2.0.0"' not in card_contract_text:
        errors.append("Shared free/report card algorithm version is missing")
    if not all("card_algorithm_version" in text and "visual_series_sha256" in text for text in (card_assembler_text, delivery_text)):
        errors.append("Card assembler and final delivery do not verify the same algorithm and visual-series hash")
    semantic_schema = json.loads((root / "internal/rensheng-youji-report-writer/schemas/report-semantic-patch.schema.json").read_text(encoding="utf-8"))
    yearly_required = set(semantic_schema["properties"]["yearly_outlook"].get("required") or [])
    if yearly_required != {"start_year", "end_year", "summary", "stages", "key_years"}:
        errors.append("Report writer must output deterministic stages and key years instead of 20 AI-written rows")
    if "annual_differentiation_rule" not in (root / "scripts/prepare_core_synthesis.py").read_text(encoding="utf-8"):
        errors.append("Core synthesis does not require evidence-based annual differentiation")
    if "跨多年完全复制同一方向、强度和机制" not in core_validator_text:
        errors.append("Core validator cannot detect annual template collapse")
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
