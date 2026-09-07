#!/usr/bin/env python3
"""Validate a complete analysis_bundle produced by the internal core."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from _jsonschema_subset import validate_schema_instance


ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = ROOT.parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from report_source_contract import (  # noqa: E402
    BASE_COVERAGE,
    DIMENSIONS,
    claim_diversity_gaps,
    mandatory_candidate_bounds,
    required_coverage,
)
from core_synthesis_contract import LOVE_PARTNER_ANCHORS, build_source_coverage_audit  # noqa: E402

SCHEMA_PATH = ROOT / "schemas" / "analysis-output.schema.json"
REQUIRED_SECTIONS = {
    "analysis_meta",
    "chart_facts",
    "chart_audit",
    "social_context_model",
    "five_elements",
    "day_master",
    "stems_branches_roots",
    "interaction_network",
    "independent_method_analyses",
    "method_execution_audit",
    "source_coverage_audit",
    "method_synthesis",
    "cross_method_analysis",
    "blind_school_cross_analysis",
    "evidence_registry",
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
    "report_source_bundle",
    "reality_candidate_pool",
    "candidate_relation_map",
    "calibration_state",
    "calibration_delta",
    "not_inferable_register",
    "portrait_balance_audit",
    "uncertainty_register",
    "safety_boundaries",
}
INFERENCE_KEYS = {
    "finding",
    "mechanism_chain",
    "evidence",
    "linked_domains",
    "time_scope",
    "confidence",
    "alternatives",
    "birth_time_dependency",
    "validation",
}
EVIDENCE_KEYS = {"natal", "luck_cycle", "annual", "user_facts", "social_priors"}
YEAR_KEYS = {
    "year",
    "age",
    "luck_cycle_index",
    "year_theme",
    "luck_theme_link",
    "activation_mechanisms",
    "natal_reactions",
    "change_intensity",
    "direction",
    "domain_impacts",
    "domain_connections",
    "human_actions",
    "social_feedback",
    "carry_in",
    "carry_out",
    "seed_for_next",
    "confidence",
    "alternatives",
    "validation",
}
SELF_PORTRAIT_KEYS = {
    "summary",
    "outward_presentation",
    "inner_motivation",
    "cognition_and_decision",
    "emotional_security",
    "action_and_execution",
    "values_and_boundaries",
    "stress_and_recovery",
    "contradictions",
    "environment_fit",
    "development_line",
    "findings",
}
FAMILY_SYSTEM_KEYS = {
    "summary",
    "early_resources",
    "expectations_and_costs",
    "role_position",
    "independence_and_boundaries",
    "partner_family_interface",
    "repetition_and_revision",
    "cross_domain_links",
    "findings",
}
RELATIONSHIP_SYSTEM_KEYS = {
    "summary",
    "intimacy_needs",
    "attraction_process",
    "expression_style",
    "conflict_pattern",
    "repair_pattern",
    "commitment_conditions",
    "autonomy_and_closeness",
    "career_family_money_effects",
    "findings",
}
PARTNER_PROFILE_KEYS = {
    "summary",
    "traits",
    "mechanism",
    "benefits",
    "costs",
    "evidence_strength",
    "alternatives",
    "validation",
    "findings",
}
MANDATORY_PORTRAIT_DOMAINS = {
    "self",
    "family",
    "resources",
    "social",
    "relationships",
    "partner",
    "interaction",
    "career",
    "wealth",
    "learning",
    "mobility",
    "health",
    "continuity",
}
PREFERRED_CANDIDATE_LENSES = {
    "cross_method",
    "luck",
    "annual",
    "root_seed_flower_fruit_map",
    "resource_relationship",
    "cross_method_analysis",
    "luck_cycle_themes",
    "annual_theme_activation",
    "domain_connections",
}
BLIND_LAYERS = {"blind_shared", "blind_duan", "blind_yang"}
NON_BLIND_LAYERS = {"natal", "root_seed_flower_fruit", "resource_relationship", "cross_method", "luck_cycle", "annual"}
REPORT_DOMAINS = {"self_growth", "love_partner", "career", "finance_resources", "body_emotion", "family_growth"}
SOURCE_GAP_PORTRAIT_MAP = {
    "self_growth": {"self"},
    "love_partner": {"relationships", "partner", "interaction"},
    "career": {"career"},
    "finance_resources": {"resources", "wealth"},
    "body_emotion": {"health"},
    "family_growth": {"family"},
}
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
METHOD_GROUPS = {
    "pattern_structure": "pattern_organization",
    "momentum_configuration": "momentum_intention",
    "climate_adjustment": "climate_environment",
    "ten_god_dynamics": "relationship_action",
    "root_seed_flower_fruit": "development_continuity",
    "blind_school": "blind_action_path",
    "timing_continuity": "timing_execution",
    "position_relationship": "position_interface",
    "stem_branch_dynamics": "stem_branch_structure",
}
ALLOWED_METHOD_INPUT_ROOTS = {
    "request",
    "person",
    "chart",
    "solar_terms_and_boundaries",
    "five_elements",
    "luck_cycles",
    "annual_cycles",
    "chart_facts",
    "chart_audit",
}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def require_keys(value: Any, keys: set[str], path: str, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{path} 必须是对象")
        return
    for key in sorted(keys - value.keys()):
        errors.append(f"{path}.{key} 缺失")


def walk(value: Any, path: str = "$") -> Iterator[tuple[str, Any]]:
    yield path, value
    if isinstance(value, dict):
        for key, child in value.items():
            yield from walk(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk(child, f"{path}[{index}]")


def validate_inference(value: dict[str, Any], path: str, errors: list[str]) -> None:
    require_keys(value, INFERENCE_KEYS, path, errors)
    if value.get("confidence") not in {"high", "medium", "to_verify"}:
        errors.append(f"{path}.confidence 必须是 high/medium/to_verify")
    if value.get("birth_time_dependency") not in {"none", "partial", "high"}:
        errors.append(f"{path}.birth_time_dependency 必须是 none/partial/high")
    require_keys(value.get("evidence"), EVIDENCE_KEYS, f"{path}.evidence", errors)
    chain = value.get("mechanism_chain")
    if not isinstance(chain, list) or not chain:
        errors.append(f"{path}.mechanism_chain 至少包含一步")


def method_delivery_decision(completed_methods: set[str]) -> tuple[str, bool, bool, bool]:
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


def validate(data: Any) -> list[str]:
    errors: list[str] = []
    require_keys(data, REQUIRED_SECTIONS, "$", errors)
    if not isinstance(data, dict):
        return errors
    unknown = set(data) - REQUIRED_SECTIONS
    if unknown:
        errors.append(f"$ 包含未定义顶层字段：{', '.join(sorted(unknown))}")

    meta = data.get("analysis_meta")
    require_keys(meta, {"analysis_id", "request_id", "core_version", "generated_at", "analysis_as_of", "target_range", "input_completeness", "status"}, "analysis_meta", errors)
    if isinstance(meta, dict):
        if meta.get("core_version") != "0.15.0":
            errors.append("analysis_meta.core_version 必须为 0.15.0")
        if meta.get("status") not in {"complete", "pass_with_flags"}:
            errors.append("analysis_meta.status 必须是 complete 或 pass_with_flags")
        try:
            datetime.fromisoformat(str(meta.get("generated_at", "")).replace("Z", "+00:00"))
        except ValueError:
            errors.append("analysis_meta.generated_at 不是有效 ISO 日期时间")
        target = meta.get("target_range")
        require_keys(target, {"start_year", "end_year"}, "analysis_meta.target_range", errors)

    chart = data.get("chart_facts")
    require_keys(chart, {"day_master", "pillars", "luck_cycles", "annual_cycles"}, "chart_facts", errors)
    if isinstance(chart, dict):
        pillars = chart.get("pillars")
        require_keys(pillars, {"year", "month", "day", "hour"}, "chart_facts.pillars", errors)
        if isinstance(pillars, dict):
            for name in ("year", "month", "day", "hour"):
                pillar = pillars.get(name)
                path = f"chart_facts.pillars.{name}"
                require_keys(pillar, {"stem", "branch", "stem_ten_god", "hidden_stems"}, path, errors)
                if isinstance(pillar, dict):
                    hidden = pillar.get("hidden_stems")
                    if not isinstance(hidden, list) or not 1 <= len(hidden) <= 3:
                        errors.append(f"{path}.hidden_stems 必须包含 1—3 个藏干")
                    elif hidden[0].get("qi_level") != "main":
                        errors.append(f"{path}.hidden_stems 第一项必须是主气 main")

    require_keys(data.get("chart_audit"), {"status", "checks", "boundary_dependencies", "versions"}, "chart_audit", errors)
    cross_method = data.get("cross_method_analysis")
    require_keys(cross_method, {"summary", "methods", "agreements", "conflicts", "findings"}, "cross_method_analysis", errors)
    if isinstance(cross_method, dict):
        methods = cross_method.get("methods")
        if not isinstance(methods, list):
            errors.append("cross_method_analysis.methods 必须是已完成主要方法的列表")
        if not isinstance(cross_method.get("agreements"), list) or not cross_method.get("agreements"):
            errors.append("cross_method_analysis.agreements 至少记录一项交叉支持")
        if not isinstance(cross_method.get("conflicts"), list):
            errors.append("cross_method_analysis.conflicts 必须是数组；无冲突时使用空数组")

    raw_completed_methods = {
        item.get("method_id")
        for item in (data.get("independent_method_analyses") or [])
        if isinstance(item, dict) and item.get("status") == "complete"
    }
    blind_complete = "blind_school" in raw_completed_methods
    blind = data.get("blind_school_cross_analysis")
    require_keys(blind, {"source_boundaries", "host_guest_map", "body_function_map", "work_paths", "image_hypotheses", "reality_image_candidates", "virtual_real_completeness", "timing_activation", "agreements", "conflicts", "prohibited_extensions"}, "blind_school_cross_analysis", errors)
    if isinstance(blind, dict) and blind_complete:
        if len(blind.get("source_boundaries") or []) < 2:
            errors.append("blind_school_cross_analysis.source_boundaries 必须分别说明两套参考口径")
        if not blind.get("work_paths"):
            errors.append("blind_school_cross_analysis.work_paths 至少包含一条完整做功路径")
        reality_images = blind.get("reality_image_candidates")
        if not isinstance(reality_images, list) or len(reality_images) < 4:
            errors.append("blind_school_cross_analysis.reality_image_candidates 至少包含四条现实取象")
        else:
            image_dimensions = {item.get("dimension") for item in reality_images if isinstance(item, dict)}
            if not {"industry", "function"}.issubset(image_dimensions):
                errors.append("盲派现实取象必须分别包含行业和岗位职能候选")
        if len(blind.get("prohibited_extensions") or []) < 4:
            errors.append("blind_school_cross_analysis.prohibited_extensions 至少包含四项禁止外推")
    elif isinstance(blind, dict):
        stale_blind_fields = [
            key
            for key in ("work_paths", "image_hypotheses", "reality_image_candidates", "timing_activation", "agreements")
            if blind.get(key)
        ]
        if stale_blind_fields:
            errors.append("blind_school方法未完成时不得保留盲派半成品：" + ", ".join(stale_blind_fields))

    registry = data.get("evidence_registry")
    evidence_by_id: dict[str, dict[str, Any]] = {}
    if not isinstance(registry, list) or not registry:
        errors.append("evidence_registry 至少包含一条由有效技术结论实际使用的实体证据")
    else:
        for index, evidence in enumerate(registry):
            path = f"evidence_registry[{index}]"
            require_keys(evidence, {"evidence_id", "source_layer", "method", "method_id", "independence_group", "chart_refs", "observation", "interpretation", "limitations", "confidence"}, path, errors)
            if not isinstance(evidence, dict):
                continue
            evidence_id = evidence.get("evidence_id")
            if not isinstance(evidence_id, str) or not evidence_id.startswith("evidence_"):
                errors.append(f"{path}.evidence_id 格式无效")
            elif evidence_id in evidence_by_id:
                errors.append(f"{path}.evidence_id 不能重复")
            else:
                evidence_by_id[evidence_id] = evidence
            if not evidence.get("limitations"):
                errors.append(f"{path}.limitations 至少说明一项限制")

    method_items = data.get("independent_method_analyses")
    method_by_id: dict[str, dict[str, Any]] = {}
    conclusion_to_method: dict[str, str] = {}
    hypothesis_to_method: dict[str, str] = {}
    hypothesis_by_id: dict[str, dict[str, Any]] = {}
    if not isinstance(method_items, list) or len(method_items) != len(ALL_METHODS):
        errors.append("independent_method_analyses 必须恰好包含9个规定方法家族")
    else:
        for index, method_item in enumerate(method_items):
            path = f"independent_method_analyses[{index}]"
            require_keys(method_item, {"method_id", "tier", "independence_group", "status", "attempt_count", "failure_reasons", "degradation_effects", "input_scope", "method_input_sha256", "input_fact_refs", "source_method_ids_read", "technical_conclusions", "reality_hypotheses", "domain_assessments", "limitations"}, path, errors)
            if not isinstance(method_item, dict):
                continue
            method_id = method_item.get("method_id")
            if method_id not in ALL_METHODS:
                errors.append(f"{path}.method_id 不是规定方法家族")
                continue
            if method_id in method_by_id:
                errors.append(f"{path}.method_id 不能重复")
            method_by_id[method_id] = method_item
            expected_tier = "primary" if method_id in PRIMARY_METHODS else "partial"
            if method_item.get("tier") != expected_tier:
                errors.append(f"{path}.tier 必须为{expected_tier}")
            if method_item.get("independence_group") != METHOD_GROUPS[method_id]:
                errors.append(f"{path}.independence_group 必须为{METHOD_GROUPS[method_id]}")
            if method_item.get("source_method_ids_read") != []:
                errors.append(f"{path}.source_method_ids_read 必须为空，独立方法不得读取其他方法结论")
            if method_item.get("input_scope") != "chart_only_topic_isolated":
                errors.append(f"{path}.input_scope 必须为chart_only_topic_isolated")
            status = method_item.get("status")
            attempt_count = method_item.get("attempt_count")
            if not isinstance(attempt_count, int) or not 1 <= attempt_count <= 3:
                errors.append(f"{path}.attempt_count 必须为1—3")
            if status == "generation_failed" and attempt_count != 3:
                errors.append(f"{path} generation_failed必须经过三轮局部修复")
            if status == "complete" and method_item.get("failure_reasons"):
                errors.append(f"{path} complete方法不得保留failure_reasons")
            if status != "complete" and not method_item.get("failure_reasons"):
                errors.append(f"{path} 未完成方法必须说明failure_reasons")
            if status != "complete" and not method_item.get("degradation_effects"):
                errors.append(f"{path} 未完成方法必须说明降级影响")
            if status != "blocked_input" and not method_item.get("input_fact_refs"):
                errors.append(f"{path}.input_fact_refs 至少引用一项冻结排盘事实")
            for fact_ref in method_item.get("input_fact_refs") or []:
                if not isinstance(fact_ref, str) or fact_ref.split(".", 1)[0] not in ALLOWED_METHOD_INPUT_ROOTS:
                    errors.append(f"{path}.input_fact_refs 只能引用冻结事实，不能读取方法结论、报告候选或校准结果")
            if not method_item.get("limitations"):
                errors.append(f"{path}.limitations 至少说明一项方法边界")
            conclusions = method_item.get("technical_conclusions") or []
            hypotheses = method_item.get("reality_hypotheses") or []
            if status != "complete":
                if conclusions or hypotheses or method_item.get("domain_assessments"):
                    errors.append(f"{path} 未完成方法不得用半成品结论或领域检查参与后续综合")
            elif method_id in PRIMARY_METHODS and (len(conclusions) < 2 or len(hypotheses) < 2):
                errors.append(f"{path} 完成的主要方法至少包含两条技术结论和两条现实候选")
            elif method_id in PARTIAL_METHODS and (len(conclusions) < 1 or len(hypotheses) < 1):
                errors.append(f"{path} 完成的部分独立方法至少包含一条技术结论和一条现实候选")
            local_conclusion_ids: set[str] = set()
            for conclusion_index, conclusion in enumerate(conclusions):
                conclusion_path = f"{path}.technical_conclusions[{conclusion_index}]"
                require_keys(conclusion, {"conclusion_id", "statement", "mechanism_chain", "chart_refs", "evidence_ids", "conditions", "counterconditions", "time_scope", "confidence"}, conclusion_path, errors)
                if not isinstance(conclusion, dict):
                    continue
                conclusion_id = conclusion.get("conclusion_id")
                if not isinstance(conclusion_id, str) or conclusion_id in conclusion_to_method:
                    errors.append(f"{conclusion_path}.conclusion_id 缺失或重复")
                else:
                    conclusion_to_method[conclusion_id] = method_id
                    local_conclusion_ids.add(conclusion_id)
                evidence_ids = set(conclusion.get("evidence_ids") or [])
                chart_refs = set(conclusion.get("chart_refs") or [])
                if not chart_refs or not chart_refs.issubset(set(method_item.get("input_fact_refs") or [])):
                    errors.append(f"{conclusion_path}.chart_refs 必须来自本方法声明的input_fact_refs")
                unknown = sorted(evidence_ids - set(evidence_by_id))
                if unknown:
                    errors.append(f"{conclusion_path}.evidence_ids 存在无效引用：{unknown}")
                for evidence_id in evidence_ids & set(evidence_by_id):
                    evidence = evidence_by_id[evidence_id]
                    if evidence.get("method_id") != method_id:
                        errors.append(f"{conclusion_path} 引用了其他方法的证据 {evidence_id}")
                    if evidence.get("independence_group") != method_item.get("independence_group"):
                        errors.append(f"{conclusion_path} 的证据独立家族与方法不一致")
            for hypothesis_index, hypothesis in enumerate(hypotheses):
                hypothesis_path = f"{path}.reality_hypotheses[{hypothesis_index}]"
                require_keys(hypothesis, {"hypothesis_id", "derived_from_conclusion_ids", "domain", "normalized_direction", "statement", "observable_indicators", "conditions", "counterevidence", "unsupported_extensions", "time_scope", "reality_confirmation"}, hypothesis_path, errors)
                if not isinstance(hypothesis, dict):
                    continue
                hypothesis_id = hypothesis.get("hypothesis_id")
                if not isinstance(hypothesis_id, str) or hypothesis_id in hypothesis_to_method:
                    errors.append(f"{hypothesis_path}.hypothesis_id 缺失或重复")
                else:
                    hypothesis_to_method[hypothesis_id] = method_id
                    hypothesis_by_id[hypothesis_id] = hypothesis
                derived = set(hypothesis.get("derived_from_conclusion_ids") or [])
                if not derived or derived - local_conclusion_ids:
                    errors.append(f"{hypothesis_path} 只能引用本方法的技术结论")
                if hypothesis.get("domain") not in REPORT_DOMAINS:
                    errors.append(f"{hypothesis_path}.domain 不是允许的现实领域")
                if len(set(hypothesis.get("observable_indicators") or [])) < 2:
                    errors.append(f"{hypothesis_path}.observable_indicators 至少包含两条可观察表现")
                for key in ("conditions", "counterevidence", "unsupported_extensions"):
                    if not hypothesis.get(key):
                        errors.append(f"{hypothesis_path}.{key} 至少包含一项")
            assessments = method_item.get("domain_assessments") or []
            assessment_by_domain = {
                item.get("domain"): item for item in assessments if isinstance(item, dict)
            }
            expected_domains = REPORT_DOMAINS
            if status == "complete" and set(assessment_by_domain) != expected_domains:
                errors.append(f"{path}.domain_assessments 必须逐项检查六个报告领域")
            if status == "complete":
                for domain, assessment in assessment_by_domain.items():
                    expected_ids = {
                        item.get("hypothesis_id") for item in hypotheses
                        if isinstance(item, dict) and item.get("domain") == domain
                    }
                    actual_ids = set(assessment.get("hypothesis_ids") or [])
                    if assessment.get("status") == "supported":
                        if not expected_ids or actual_ids != expected_ids:
                            errors.append(f"{path}.domain_assessments.{domain} supported映射无效")
                    elif assessment.get("status") in {"insufficient_evidence", "not_applicable"}:
                        if expected_ids or actual_ids:
                            errors.append(f"{path}.domain_assessments.{domain} 无支持时不得保留候选")
                love_assessment = assessment_by_domain.get("love_partner")
                if method_id in LOVE_PARTNER_ANCHORS and isinstance(love_assessment, dict):
                    if love_assessment.get("status") == "not_applicable":
                        errors.append(f"{path} 是关系锚点方法，必须实际检查love_partner")
        missing_methods = sorted(ALL_METHODS - set(method_by_id))
        if missing_methods:
            errors.append(f"independent_method_analyses 缺少方法家族：{missing_methods}")
        method_input_hashes = {
            item.get("method_input_sha256") for item in method_by_id.values()
            if isinstance(item.get("method_input_sha256"), str)
        }
        if len(method_input_hashes) != 1:
            errors.append("九个方法必须来自同一份主题隔离输入哈希")

    completed_methods = {method_id for method_id, item in method_by_id.items() if item.get("status") == "complete"}
    excluded_methods = set(method_by_id) - completed_methods
    failed_methods = {method_id for method_id, item in method_by_id.items() if item.get("status") in {"blocked_input", "generation_failed"}}
    completed_primary = completed_methods & PRIMARY_METHODS
    expected_delivery, structural_anchor, reality_anchor, timing_anchor = method_delivery_decision(completed_methods)
    stale_evidence = sorted(
        evidence_id
        for evidence_id, evidence in evidence_by_id.items()
        if evidence.get("method_id") in ALL_METHODS and evidence.get("method_id") not in completed_methods
    )
    if stale_evidence:
        errors.append(f"未完成方法不得在evidence_registry保留半成品证据：{stale_evidence}")
    method_audit = data.get("method_execution_audit")
    require_keys(method_audit, {"retry_limit", "completed_method_ids", "excluded_method_ids", "failed_method_ids", "primary_completed_count", "structural_anchor_complete", "reality_anchor_complete", "timing_anchor_complete", "delivery_decision", "degradation_reasons", "stage_validation_passed"}, "method_execution_audit", errors)
    if isinstance(method_audit, dict):
        exact_checks = {
            "completed_method_ids": completed_methods,
            "excluded_method_ids": excluded_methods,
            "failed_method_ids": failed_methods,
        }
        for key, expected in exact_checks.items():
            if set(method_audit.get(key) or []) != expected:
                errors.append(f"method_execution_audit.{key} 必须由各方法实际状态确定")
        if method_audit.get("retry_limit") != 3:
            errors.append("method_execution_audit.retry_limit 必须为3")
        if method_audit.get("primary_completed_count") != len(completed_primary):
            errors.append("method_execution_audit.primary_completed_count 与实际完成数不一致")
        for key, expected in (
            ("structural_anchor_complete", structural_anchor),
            ("reality_anchor_complete", reality_anchor),
            ("timing_anchor_complete", timing_anchor),
        ):
            if method_audit.get(key) is not expected:
                errors.append(f"method_execution_audit.{key} 与实际方法覆盖不一致")
        if method_audit.get("delivery_decision") != expected_delivery:
            errors.append(f"method_execution_audit.delivery_decision 应为{expected_delivery}")
        if excluded_methods and not method_audit.get("degradation_reasons"):
            errors.append("method_execution_audit 有方法未完成时必须说明degradation_reasons")
        if method_audit.get("stage_validation_passed") is not True:
            errors.append("method_execution_audit.stage_validation_passed 必须为true，表示每个方法已经单独校验或完成失败归类")

    source_coverage = data.get("source_coverage_audit")
    require_keys(source_coverage, {"report_domain_candidate_counts", "report_domain_primary_method_ids", "domain_review_counts", "love_partner_anchor_statuses", "love_partner_anchor_review_complete", "topic_isolation_required", "uncovered_report_domains", "single_primary_method_domains", "multi_primary_method_domains", "semantic_clustering_required", "status"}, "source_coverage_audit", errors)
    expected_source_coverage = build_source_coverage_audit(list(method_by_id.values()))
    if isinstance(source_coverage, dict) and source_coverage != expected_source_coverage:
        errors.append("source_coverage_audit 必须由实际完成的方法现实候选确定性生成")
    uncovered_source_domains = set(expected_source_coverage["uncovered_report_domains"])
    if isinstance(meta, dict):
        expected_meta_status = "complete" if expected_delivery == "full" else "pass_with_flags"
        if meta.get("status") != expected_meta_status:
            errors.append(f"analysis_meta.status 在{expected_delivery}模式下必须为{expected_meta_status}")
    if isinstance(cross_method, dict) and set(cross_method.get("methods") or []) != completed_primary:
        errors.append("cross_method_analysis.methods 必须只包含实际完成的主要方法家族")

    synthesis = data.get("method_synthesis")
    require_keys(synthesis, {"summary", "clusters", "conflicts", "primary_synthesis_ids", "supplemental_synthesis_ids", "to_verify_synthesis_ids"}, "method_synthesis", errors)
    synthesis_by_id: dict[str, dict[str, Any]] = {}
    if isinstance(synthesis, dict):
        clusters = synthesis.get("clusters")
        if not isinstance(clusters, list) or not clusters:
            errors.append("method_synthesis.clusters 至少包含一条由完成方法形成的综合判断")
        else:
            for index, cluster in enumerate(clusters):
                path = f"method_synthesis.clusters[{index}]"
                require_keys(cluster, {"synthesis_id", "domain", "normalized_direction", "member_hypothesis_ids", "supporting_method_ids", "independence_groups", "relationship_type", "structural_confidence", "reality_confirmation", "counterevidence", "report_role", "reasoning"}, path, errors)
                if not isinstance(cluster, dict):
                    continue
                synthesis_id = cluster.get("synthesis_id")
                if not isinstance(synthesis_id, str) or synthesis_id in synthesis_by_id:
                    errors.append(f"{path}.synthesis_id 缺失或重复")
                    continue
                synthesis_by_id[synthesis_id] = cluster
                member_ids = set(cluster.get("member_hypothesis_ids") or [])
                if not member_ids or member_ids - set(hypothesis_to_method):
                    errors.append(f"{path}.member_hypothesis_ids 存在无效引用")
                    continue
                actual_methods = {hypothesis_to_method[item] for item in member_ids}
                actual_groups = {method_by_id[item].get("independence_group") for item in actual_methods if item in method_by_id}
                if set(cluster.get("supporting_method_ids") or []) != actual_methods:
                    errors.append(f"{path}.supporting_method_ids 必须由成员现实候选确定")
                if set(cluster.get("independence_groups") or []) != actual_groups:
                    errors.append(f"{path}.independence_groups 必须由成员方法确定")
                primary_support = actual_methods & PRIMARY_METHODS
                role = cluster.get("report_role")
                if role not in {"primary", "supplemental", "to_verify", "excluded"}:
                    errors.append(f"{path}.report_role 值无效")
                if role == "primary" and (len(primary_support) < 2 or len(actual_groups) < 2):
                    errors.append(f"{path} primary判断至少需要两个主要方法家族独立同向")
                if role == "primary" and cluster.get("relationship_type") != "same_direction":
                    errors.append(f"{path} primary判断必须是不同主要方法独立得到的同向现实候选")
                if cluster.get("relationship_type") == "same_direction":
                    member_domains = {hypothesis_by_id[item].get("domain") for item in member_ids}
                    if member_domains != {cluster.get("domain")}:
                        errors.append(f"{path} same_direction成员必须属于同一现实领域")
                if role == "supplemental" and not primary_support:
                    errors.append(f"{path} supplemental判断至少需要一个主要方法支持")
                if cluster.get("structural_confidence") == "high" and (len(primary_support) < 2 or len(actual_groups) < 2):
                    errors.append(f"{path} high结构置信度至少需要两个不同主要方法家族")
                if cluster.get("reality_confirmation") == "contradicted" and role != "excluded":
                    errors.append(f"{path} 现实已反驳时必须标记excluded")
        role_lists = {
            "primary": set(synthesis.get("primary_synthesis_ids") or []),
            "supplemental": set(synthesis.get("supplemental_synthesis_ids") or []),
            "to_verify": set(synthesis.get("to_verify_synthesis_ids") or []),
        }
        for role, listed in role_lists.items():
            actual = {item_id for item_id, item in synthesis_by_id.items() if item.get("report_role") == role}
            if listed != actual:
                errors.append(f"method_synthesis.{role}_synthesis_ids 与clusters中的角色不一致")
        for index, conflict in enumerate(synthesis.get("conflicts") or []):
            path = f"method_synthesis.conflicts[{index}]"
            require_keys(conflict, {"conflict_id", "hypothesis_ids", "same_scope", "resolution", "requires_calibration"}, path, errors)
            if isinstance(conflict, dict) and set(conflict.get("hypothesis_ids") or []) - set(hypothesis_to_method):
                errors.append(f"{path}.hypothesis_ids 存在无效引用")

    if isinstance(blind, dict) and "blind_school" in completed_methods:
        for index, work_path in enumerate(blind.get("work_paths") or []):
            unknown = sorted(set(work_path.get("evidence_ids") or []) - set(evidence_by_id)) if isinstance(work_path, dict) else []
            if unknown:
                errors.append(f"blind_school_cross_analysis.work_paths[{index}].evidence_ids 存在无效引用：{unknown}")
        for index, image_item in enumerate(blind.get("reality_image_candidates") or []):
            unknown = sorted(set(image_item.get("evidence_ids") or []) - set(evidence_by_id)) if isinstance(image_item, dict) else []
            if unknown:
                errors.append(f"blind_school_cross_analysis.reality_image_candidates[{index}].evidence_ids 存在无效引用：{unknown}")
            if isinstance(image_item, dict) and not image_item.get("non_blind_support"):
                errors.append(f"blind_school_cross_analysis.reality_image_candidates[{index}] 缺少非盲派交叉支持")
    root_map = data.get("root_seed_flower_fruit_map")
    require_keys(root_map, {"summary", "root", "seedling", "flower", "fruit", "continuity", "domain_lifecycles", "findings"}, "root_seed_flower_fruit_map", errors)
    if isinstance(root_map, dict) and "root_seed_flower_fruit" in completed_methods:
        if not isinstance(root_map.get("continuity"), list) or len(root_map.get("continuity", [])) < 3:
            errors.append("root_seed_flower_fruit_map.continuity 至少包含时序、同时共存和传承三条关系")
        lifecycles = root_map.get("domain_lifecycles")
        if not isinstance(lifecycles, list) or len(lifecycles) < 3:
            errors.append("root_seed_flower_fruit_map.domain_lifecycles 至少包含三个领域")
        else:
            lifecycle_domains = {item.get("domain") for item in lifecycles if isinstance(item, dict)}
            if not {"career", "finance_resources"}.issubset(lifecycle_domains):
                errors.append("根苗花果领域生命周期必须包含事业和财富")
            for index, item in enumerate(lifecycles):
                unknown = sorted(set(item.get("evidence_ids") or []) - set(evidence_by_id)) if isinstance(item, dict) else []
                if unknown:
                    errors.append(f"root_seed_flower_fruit_map.domain_lifecycles[{index}].evidence_ids 存在无效引用：{unknown}")
    elif isinstance(root_map, dict):
        if root_map.get("continuity") or root_map.get("domain_lifecycles") or root_map.get("findings"):
            errors.append("root_seed_flower_fruit方法未完成时不得保留根苗花果半成品")
    require_keys(data.get("complete_self_portrait"), SELF_PORTRAIT_KEYS, "complete_self_portrait", errors)
    require_keys(data.get("family_system"), FAMILY_SYSTEM_KEYS, "family_system", errors)
    require_keys(data.get("relationship_system"), RELATIONSHIP_SYSTEM_KEYS, "relationship_system", errors)

    partner_profiles = data.get("partner_profiles")
    require_keys(partner_profiles, {"summary", "attraction", "sustainable", "high_attraction_high_friction", "evidence_limitations", "findings"}, "partner_profiles", errors)
    if isinstance(partner_profiles, dict):
        for name in ("attraction", "sustainable", "high_attraction_high_friction"):
            profile = partner_profiles.get(name)
            require_keys(profile, PARTNER_PROFILE_KEYS, f"partner_profiles.{name}", errors)
            if isinstance(profile, dict) and profile.get("evidence_strength") not in {"strong", "medium", "weak", "insufficient"}:
                errors.append(f"partner_profiles.{name}.evidence_strength 值无效")
        limitations = partner_profiles.get("evidence_limitations")
        if not isinstance(limitations, list) or not limitations:
            errors.append("partner_profiles.evidence_limitations 至少包含一项单人命盘限制")

    for path, value in walk(data):
        if isinstance(value, dict) and "finding" in value:
            validate_inference(value, path, errors)

    annuals = data.get("annual_theme_activation")
    if not isinstance(annuals, list) or not annuals:
        errors.append("annual_theme_activation 至少包含一年")
    else:
        years: list[int] = []
        for index, annual in enumerate(annuals):
            path = f"annual_theme_activation[{index}]"
            require_keys(annual, YEAR_KEYS, path, errors)
            if not isinstance(annual, dict):
                continue
            if isinstance(annual.get("year"), int):
                years.append(annual["year"])
            if annual.get("change_intensity") not in {"low", "medium", "high"}:
                errors.append(f"{path}.change_intensity 必须是 low/medium/high")
            if annual.get("direction") not in {"support", "mixed", "pressure", "consolidation"}:
                errors.append(f"{path}.direction 值无效")
            if annual.get("confidence") not in {"high", "medium", "to_verify"}:
                errors.append(f"{path}.confidence 值无效")
        if len(years) != len(set(years)):
            errors.append("annual_theme_activation.year 不能重复")
        if isinstance(meta, dict) and isinstance(meta.get("target_range"), dict):
            start = meta["target_range"].get("start_year")
            end = meta["target_range"].get("end_year")
            if isinstance(start, int) and isinstance(end, int):
                missing = sorted(set(range(start, end + 1)) - set(years))
                if missing:
                    errors.append(f"annual_theme_activation 缺少目标年份：{missing}")

    claims = data.get("report_claim_ledger")
    claim_ids: set[str] = set()
    claim_by_id: dict[str, dict[str, Any]] = {}
    if not isinstance(claims, list) or not claims:
        errors.append("report_claim_ledger 至少包含一条有真实方法来源的报告候选判断")
    else:
        for index, claim in enumerate(claims):
            path = f"report_claim_ledger[{index}]"
            require_keys(claim, {"claim_id", "domain", "reality_dimension", "claim_family", "mechanism_family", "claim", "plain_claim", "new_information", "mechanism_chain", "evidence_ids", "supporting_methods", "synthesis_ids", "method_hypothesis_ids", "claim_class", "report_role", "coverage_tags", "applicable_conditions", "reality_confirmation", "allowed_examples", "counterevidence", "confidence", "unsupported_extensions", "calibration_status", "origin"}, path, errors)
            if not isinstance(claim, dict):
                continue
            claim_id = claim.get("claim_id")
            if isinstance(claim_id, str):
                if claim_id in claim_ids:
                    errors.append(f"{path}.claim_id 不能重复")
                claim_ids.add(claim_id)
                claim_by_id[claim_id] = claim
            if not isinstance(claim.get("evidence_ids"), list) or not claim.get("evidence_ids"):
                errors.append(f"{path}.evidence_ids 至少包含一条实际使用的实体证据")
            if not isinstance(claim.get("supporting_methods"), list) or not claim.get("supporting_methods"):
                errors.append(f"{path}.supporting_methods 至少包含一种方法")
            for key in ("claim_family", "mechanism_family", "plain_claim", "new_information"):
                if not isinstance(claim.get(key), str) or len(claim.get(key, "").strip()) < 3:
                    errors.append(f"{path}.{key} 必须包含实质内容")
            if isinstance(claim.get("plain_claim"), str) and not claim["plain_claim"].rstrip().endswith(("。", "！", "？")):
                errors.append(f"{path}.plain_claim 必须是带句末标点的完整判断句")
            evidence_ids = set(claim.get("evidence_ids") or [])
            unknown_evidence = sorted(evidence_ids - set(evidence_by_id))
            if unknown_evidence:
                errors.append(f"{path}.evidence_ids 引用了不存在的实体证据：{unknown_evidence}")
            resolved = [evidence_by_id[item] for item in evidence_ids if item in evidence_by_id]
            substantive = [item for item in resolved if item.get("source_layer") not in {"user_fact", "social_prior"}]
            hypothesis_ids = set(claim.get("method_hypothesis_ids") or [])
            if not hypothesis_ids or hypothesis_ids - set(hypothesis_to_method):
                errors.append(f"{path}.method_hypothesis_ids 必须引用有效的独立方法现实候选")
            claim_method_ids = {hypothesis_to_method[item] for item in hypothesis_ids if item in hypothesis_to_method}
            if set(claim.get("supporting_methods") or []) != claim_method_ids:
                errors.append(f"{path}.supporting_methods 必须由method_hypothesis_ids确定")
            synthesis_ids = set(claim.get("synthesis_ids") or [])
            if not synthesis_ids or synthesis_ids - set(synthesis_by_id):
                errors.append(f"{path}.synthesis_ids 必须引用有效综合判断")
            synthesis_members = set()
            for synthesis_id in synthesis_ids & set(synthesis_by_id):
                synthesis_members.update(synthesis_by_id[synthesis_id].get("member_hypothesis_ids") or [])
            if hypothesis_ids and not hypothesis_ids.issubset(synthesis_members):
                errors.append(f"{path}.method_hypothesis_ids 必须属于所引用的综合判断")
            claim_groups = {method_by_id[item].get("independence_group") for item in claim_method_ids if item in method_by_id}
            primary_support = claim_method_ids & PRIMARY_METHODS
            report_role = claim.get("report_role")
            claim_class = claim.get("claim_class")
            expected_role = {
                "primary_judgment": "primary",
                "independent_supplement": "supplemental",
                "conditional_judgment": "supplemental",
                "stage_judgment": "supplemental",
                "calibration_pending": "to_verify",
                "weak_candidate": "to_verify",
            }.get(claim_class)
            if expected_role is None:
                errors.append(f"{path}.claim_class 不是六类Core判断之一")
            elif report_role != expected_role:
                errors.append(f"{path}.report_role 必须由claim_class确定为{expected_role}")
            if report_role == "primary":
                if len(primary_support) < 2 or len(claim_groups) < 2:
                    errors.append(f"{path} primary判断至少需要两个独立主要方法家族")
                if len(evidence_ids) < 2:
                    errors.append(f"{path} primary判断至少需要两条实体证据")
                if len({(item.get("independence_group"), item.get("method_id")) for item in substantive}) < 2:
                    errors.append(f"{path} primary判断至少需要两个不同的命理方法证据视角")
            elif report_role == "supplemental":
                if not primary_support:
                    errors.append(f"{path} supplemental判断至少需要一个主要方法支持")
                if not claim.get("applicable_conditions") or not claim.get("new_information"):
                    errors.append(f"{path} supplemental判断必须说明成立条件与新增信息")
            elif report_role == "to_verify" and not claim_method_ids:
                errors.append(f"{path} to_verify判断仍需保留方法来源")
            if claim_class == "independent_supplement" and len(claim_method_ids) != 1:
                errors.append(f"{path} 独立补充必须只来自一个有效方法")
            if claim_class == "calibration_pending" and claim.get("calibration_status") not in {"unverified", "uncertain"}:
                errors.append(f"{path} 待校准判断在冻结前必须保持unverified或uncertain")
            if claim_method_ids and not claim_method_ids.issubset({item.get("method_id") for item in substantive}):
                errors.append(f"{path}.evidence_ids 未覆盖声明的方法来源")
            incomplete_sources = sorted(claim_method_ids - completed_methods)
            if incomplete_sources:
                errors.append(f"{path} 引用了未完成或已排除的方法：{incomplete_sources}")
            allowed_coverage = set(BASE_COVERAGE) | set(required_coverage(claim.get("domain")))
            coverage_tags = set(claim.get("coverage_tags") or [])
            if not coverage_tags or coverage_tags - allowed_coverage:
                errors.append(f"{path}.coverage_tags 必须使用该领域允许的人物覆盖项")
            if claim.get("reality_confirmation") == "contradicted":
                errors.append(f"{path} 现实已反驳的判断不得进入报告判断台账")
            if claim.get("confidence") == "high" and any(item.get("source_layer") in BLIND_LAYERS for item in resolved) and not any(item.get("source_layer") in NON_BLIND_LAYERS for item in resolved):
                errors.append(f"{path} 高置信盲派判断必须有非盲派方法交叉支持")
            if claim.get("origin") == "user_fact_refinement" and not any(item.get("source_layer") == "user_fact" for item in resolved):
                errors.append(f"{path}.origin=user_fact_refinement 时必须引用用户事实证据")
            if not isinstance(claim.get("unsupported_extensions"), list) or not claim.get("unsupported_extensions"):
                errors.append(f"{path}.unsupported_extensions 至少说明一项禁止外推")
            if any(term in str(claim.get("claim", "")) for term in ("必然离婚", "一定离婚", "必然发财", "保证发财", "牢狱之灾", "必得重病", "短寿", "死亡年份")):
                errors.append(f"{path}.claim 含有禁止的确定性高风险断语")
        for domain in REPORT_DOMAINS:
            domain_claims = [item for item in claims if isinstance(item, dict) and item.get("domain") == domain]
            if domain in uncovered_source_domains and domain_claims:
                errors.append(f"report_claim_ledger.{domain} 没有方法现实候选来源，不得补造报告判断")
            diversity_gaps = claim_diversity_gaps(domain_claims)
            if "claim_family:3" in diversity_gaps:
                errors.append(f"report_claim_ledger.{domain} 至少包含三个不同判断家族")
            if "mechanism_family:2" in diversity_gaps:
                errors.append(f"report_claim_ledger.{domain} 至少包含两条不同命理机制路径")
            if "reality_dimension:3" in diversity_gaps:
                errors.append(f"report_claim_ledger.{domain} 至少覆盖三个现实问题轴")
            if "reality_dimension:2" in diversity_gaps:
                errors.append(f"report_claim_ledger.{domain} 在精简模式下仍需覆盖至少两个现实问题轴")
        normalized_claims = [str(claim.get("claim", "")).replace(" ", "") for claim in claims if isinstance(claim, dict)]
        if len(normalized_claims) != len(set(normalized_claims)):
            errors.append("report_claim_ledger 不得用重复判断填充数量")

    formation_ids: set[str] = set()
    formations = data.get("formation_chains")
    if not isinstance(formations, list) or not 3 <= len(formations) <= 6:
        errors.append("formation_chains 必须包含3—6条人物形成链")
    else:
        required = {"chain_id", "starting_condition", "adaptation_need", "learned_response", "ability_formed", "constraint", "adult_pattern", "linked_domains", "current_change", "claim_ids", "confidence"}
        for index, item in enumerate(formations):
            path = f"formation_chains[{index}]"
            require_keys(item, required, path, errors)
            if isinstance(item, dict):
                formation_ids.add(str(item.get("chain_id", "")))
                unknown = sorted(set(item.get("claim_ids") or []) - claim_ids)
                if unknown:
                    errors.append(f"{path}.claim_ids 引用了不存在的判断：{unknown}")

    thesis = data.get("portrait_thesis")
    require_keys(thesis, {"summary", "primary_traits", "complementary_traits", "internal_tensions", "observable_patterns", "formation_chain_ids", "current_shift", "evidence_ids", "boundaries"}, "portrait_thesis", errors)
    if isinstance(thesis, dict):
        if len(thesis.get("primary_traits") or []) < 2 or not thesis.get("complementary_traits") or not thesis.get("internal_tensions"):
            errors.append("portrait_thesis 必须同时包含主要特点、可共存的另一面和内在矛盾")
        if len(thesis.get("observable_patterns") or []) < 3:
            errors.append("portrait_thesis.observable_patterns 至少包含三项可观察行为")
        if set(thesis.get("formation_chain_ids") or []) - formation_ids:
            errors.append("portrait_thesis.formation_chain_ids 存在无效引用")
        thesis_evidence = set(thesis.get("evidence_ids") or [])
        if len(thesis_evidence) < 4 or thesis_evidence - set(evidence_by_id):
            errors.append("portrait_thesis.evidence_ids 必须包含至少四条有效实体证据")
        thesis_layers = {evidence_by_id[item].get("source_layer") for item in thesis_evidence if item in evidence_by_id}
        if not (thesis_layers & {"annual", "luck_cycle"}) or len(thesis_layers - {"user_fact", "social_prior"}) < 2:
            errors.append("portrait_thesis 必须同时包含原局/交叉方法与大运流年证据")

    linkage_ids: set[str] = set()
    linkages = data.get("domain_linkage_chains")
    if not isinstance(linkages, list) or not 3 <= len(linkages) <= 6:
        errors.append("domain_linkage_chains 必须包含3—6条跨领域联动链")
    else:
        required = {"chain_id", "trigger", "transmission", "affected_domains", "time_lag", "amplifiers", "buffers", "claim_ids", "confidence"}
        for index, item in enumerate(linkages):
            path = f"domain_linkage_chains[{index}]"
            require_keys(item, required, path, errors)
            if isinstance(item, dict):
                linkage_ids.add(str(item.get("chain_id", "")))
                unknown = sorted(set(item.get("claim_ids") or []) - claim_ids)
                if unknown:
                    errors.append(f"{path}.claim_ids 引用了不存在的判断：{unknown}")

    source_bundle = data.get("report_source_bundle")
    require_keys(source_bundle, {"life_narrative_source", "dimensions", "current_stage_source"}, "report_source_bundle", errors)
    if isinstance(source_bundle, dict):
        sources = {"life_narrative_source": source_bundle.get("life_narrative_source"), "current_stage_source": source_bundle.get("current_stage_source")}
        dimensions = source_bundle.get("dimensions")
        required_dimensions = {"self_growth", "career", "finance_resources", "love_partner", "family_growth", "body_emotion"}
        if not isinstance(dimensions, dict) or set(dimensions) != required_dimensions:
            errors.append("report_source_bundle.dimensions 必须完整包含六个现实领域")
        else:
            sources.update({f"dimensions.{key}": value for key, value in dimensions.items()})
        for name, source in sources.items():
            path = f"report_source_bundle.{name}"
            require_keys(source, {"summary_materials", "claim_ids", "claim_priority", "domain_specific_claim_ids", "mainline_claim_ids", "mandatory_candidate_ids", "emphasis_candidate_ids", "domain_mechanisms", "survives_without_mainline", "formation_chain_ids", "linkage_chain_ids", "concrete_candidates", "coverage", "coverage_claim_map", "evidence_gaps"}, path, errors)
            if not isinstance(source, dict):
                continue
            if len(source.get("summary_materials") or []) < len(source.get("claim_ids") or []):
                errors.append(f"{path}.summary_materials 不得少于实际候选判断数量")
            if set(source.get("claim_ids") or []) - claim_ids:
                errors.append(f"{path}.claim_ids 存在无效引用")
            source_ids = set(source.get("claim_ids") or [])
            reportable_classes = {"primary_judgment", "independent_supplement", "conditional_judgment", "stage_judgment"}
            ineligible_source_ids = sorted(item for item in source_ids if item in claim_by_id and claim_by_id[item].get("claim_class") not in reportable_classes)
            if ineligible_source_ids:
                errors.append(f"{path}.claim_ids 含不得进入报告素材的待验证或辅助判断：{ineligible_source_ids}")
            priority = source.get("claim_priority") or []
            specific_ids = set(source.get("domain_specific_claim_ids") or [])
            mainline_ids = set(source.get("mainline_claim_ids") or [])
            emphasis_ids = set(source.get("emphasis_candidate_ids") or [])
            mandatory_ids = set(source.get("mandatory_candidate_ids") or [])
            if len(priority) != len(source_ids) or set(priority) != source_ids:
                errors.append(f"{path}.claim_priority 必须无重复地排列全部候选判断")
            minimum_specific = min(2, len(source_ids)) if name.startswith("dimensions.") else min(1, len(source_ids))
            if len(specific_ids) < minimum_specific or not specific_ids.issubset(source_ids):
                errors.append(f"{path}.domain_specific_claim_ids 必须保留当前证据允许的本节判断且属于claim_ids")
            if len(mainline_ids) > 2 or not mainline_ids.issubset(source_ids) or len(mainline_ids) / max(len(source_ids), 1) > 0.30:
                errors.append(f"{path} 的共享人生主线判断不得超过本节判断的30%")
            expected_mandatory_range = mandatory_candidate_bounds(source_ids)
            if not expected_mandatory_range[0] <= len(mandatory_ids) <= expected_mandatory_range[1] or not mandatory_ids.issubset(source_ids):
                errors.append(f"{path}.mandatory_candidate_ids 必须随实际可用判断提供0—2条候选")
            emphasis_range = (0, 2) if name == "life_narrative_source" else (0, 1)
            if not emphasis_range[0] <= len(emphasis_ids) <= emphasis_range[1] or not emphasis_ids.issubset(source_ids):
                errors.append(f"{path}.emphasis_candidate_ids 最多包含{emphasis_range[1]}个可独立成立的重点候选；没有合适句子时允许为空")
            minimum_mechanisms = 2 if len(source_ids) >= 4 else 1 if source_ids else 0
            if len(set(source.get("domain_mechanisms") or [])) < minimum_mechanisms:
                errors.append(f"{path}.domain_mechanisms 与当前可用判断数量不匹配")
            if source_ids and source.get("survives_without_mainline") is not True:
                errors.append(f"{path} 有可用判断时去掉人生主线后必须仍能独立成立")
            if name.startswith("dimensions."):
                domain = name.split(".", 1)[1]
                wrong = [item for item in specific_ids if item in claim_by_id and claim_by_id[item].get("domain") != domain]
                if wrong:
                    errors.append(f"{path}.domain_specific_claim_ids 含其他领域判断：{sorted(wrong)}")
                required_tags = set(required_coverage(domain))
            else:
                required_tags = set(BASE_COVERAGE)
            coverage = set(source.get("coverage") or [])
            coverage_map = source.get("coverage_claim_map")
            if not isinstance(coverage_map, dict) or set(coverage_map) != coverage:
                errors.append(f"{path}.coverage_claim_map 必须只映射实际已经覆盖的项目")
            else:
                for tag in coverage:
                    mapped = coverage_map.get(tag)
                    if not isinstance(mapped, list) or len(set(mapped)) < 1 or set(mapped) - source_ids:
                        errors.append(f"{path}.coverage_claim_map.{tag} 必须绑定至少一个真实本节候选判断")
                    elif name.startswith("dimensions.") and not (set(mapped) & specific_ids):
                        errors.append(f"{path}.coverage_claim_map.{tag} 至少包含一个领域专属判断")
            missing_tags = required_tags - coverage
            if missing_tags and not source.get("evidence_gaps"):
                errors.append(f"{path} 缺少覆盖项时必须在evidence_gaps中说明降级原因")
            if set(source.get("formation_chain_ids") or []) - formation_ids:
                errors.append(f"{path}.formation_chain_ids 存在无效引用")
            if set(source.get("linkage_chain_ids") or []) - linkage_ids:
                errors.append(f"{path}.linkage_chain_ids 存在无效引用")
        if isinstance(dimensions, dict):
            usage: dict[str, int] = {}
            for source in dimensions.values():
                for item in set(source.get("claim_ids") or []):
                    usage[item] = usage.get(item, 0) + 1
            overused = sorted(item for item, count in usage.items() if count > 2)
            if overused:
                errors.append(f"同一判断最多进入两个现实领域：{overused}")
            # 家庭与身体专属覆盖不足时允许章节降级，但必须由上面的evidence_gaps显式记录。

    candidates = data.get("reality_candidate_pool")
    if not isinstance(candidates, list) or not 10 <= len(candidates) <= 24:
        errors.append("reality_candidate_pool 必须包含10—24条由方法现实候选派生的开放候选")
    else:
        ids: list[str] = []
        domains: set[str] = set()
        for index, candidate in enumerate(candidates):
            path = f"reality_candidate_pool[{index}]"
            require_keys(candidate, {"candidate_id", "domain", "reality_dimension", "parent_category", "label", "attributes", "candidate_kind", "time_scope", "calibration_targets", "statement", "observable_examples", "alternative_statement", "counterevidence", "unsupported_extensions", "source_layers", "evidence_ids", "related_claim_ids", "relation_ids", "confidence", "validation_question", "status"}, path, errors)
            if isinstance(candidate, dict) and isinstance(candidate.get("candidate_id"), str):
                ids.append(candidate["candidate_id"])
            if isinstance(candidate, dict) and isinstance(candidate.get("domain"), str):
                domains.add(candidate["domain"])
            if isinstance(candidate, dict):
                layers = candidate.get("source_layers")
                if not isinstance(layers, list) or len(set(layers)) < 1:
                    errors.append(f"{path}.source_layers 至少包含一个真实方法来源")
                elif not (set(layers) & PREFERRED_CANDIDATE_LENSES):
                    errors.append(f"{path}.source_layers 不能只依赖日主旺衰，必须包含根苗花果、资源、交叉方法或时运视角")
                examples = candidate.get("observable_examples")
                if not isinstance(examples, list) or not 2 <= len(examples) <= 3 or len(set(examples)) != len(examples):
                    errors.append(f"{path}.observable_examples 必须包含2—3条不同的可观察表现")
                statement = candidate.get("statement")
                alternative = candidate.get("alternative_statement")
                if isinstance(statement, str) and isinstance(alternative, str) and statement.strip() == alternative.strip():
                    errors.append(f"{path}.alternative_statement 不能重复主要候选")
                targets = candidate.get("calibration_targets")
                if not isinstance(targets, list) or not 1 <= len(targets) <= 4 or len(set(targets)) != len(targets):
                    errors.append(f"{path}.calibration_targets 必须包含1—4个不同的Core结论路径")
                if candidate.get("candidate_kind") == "timed_event" and not any(layer in set(layers or []) for layer in {"annual", "luck", "annual_theme_activation", "luck_cycle_themes"}):
                    errors.append(f"{path}.candidate_kind=timed_event 时必须包含时运证据")
                if not isinstance(candidate.get("attributes"), list) or not candidate.get("attributes"):
                    errors.append(f"{path}.attributes 至少包含一个现实属性")
                if not isinstance(candidate.get("unsupported_extensions"), list) or not candidate.get("unsupported_extensions"):
                    errors.append(f"{path}.unsupported_extensions 至少包含一项禁止外推")
                evidence_ids = set(candidate.get("evidence_ids") or [])
                if len(evidence_ids) < 1 or evidence_ids - set(evidence_by_id):
                    errors.append(f"{path}.evidence_ids 必须包含至少一条有效实体证据")
                candidate_groups = {
                    evidence_by_id[item].get("independence_group")
                    for item in evidence_ids
                    if item in evidence_by_id and evidence_by_id[item].get("method_id") in PRIMARY_METHODS
                }
                if candidate.get("confidence") == "high" and len(candidate_groups) < 2:
                    errors.append(f"{path} high候选至少需要两个独立主要方法家族")
                related_claim_ids = set(candidate.get("related_claim_ids") or [])
                if not related_claim_ids or related_claim_ids - claim_ids:
                    errors.append(f"{path}.related_claim_ids 必须引用有效报告判断")
                if not candidate.get("relation_ids"):
                    errors.append(f"{path}.relation_ids 至少引用一条候选关系")
        if len(ids) != len(set(ids)):
            errors.append("reality_candidate_pool.candidate_id 不能重复")
        missing_candidate_domains = sorted(REPORT_DOMAINS - domains)
        if set(missing_candidate_domains) != uncovered_source_domains:
            errors.append(
                "reality_candidate_pool 的领域缺口必须与source_coverage_audit一致："
                f"候选池缺少={missing_candidate_domains}；来源缺口={sorted(uncovered_source_domains)}"
            )

    candidate_ids = {item.get("candidate_id") for item in candidates or [] if isinstance(item, dict)}
    relations = data.get("candidate_relation_map")
    relation_ids: set[str] = set()
    if not isinstance(relations, list) or len(relations) < 6:
        errors.append("candidate_relation_map 至少包含六组候选关系")
    else:
        for index, relation in enumerate(relations):
            path = f"candidate_relation_map[{index}]"
            require_keys(relation, {"relation_id", "candidate_ids", "relation_type", "comparison_axis", "time_scope", "coexistence_rule", "exclusion_rule", "evidence_ids", "confidence"}, path, errors)
            if not isinstance(relation, dict):
                continue
            relation_id = relation.get("relation_id")
            if relation_id in relation_ids:
                errors.append(f"{path}.relation_id 不能重复")
            relation_ids.add(relation_id)
            if set(relation.get("candidate_ids") or []) - candidate_ids:
                errors.append(f"{path}.candidate_ids 存在无效引用")
            if len(set(relation.get("candidate_ids") or [])) < 2:
                errors.append(f"{path}.candidate_ids 至少包含两个不同候选")
            if set(relation.get("evidence_ids") or []) - set(evidence_by_id):
                errors.append(f"{path}.evidence_ids 存在无效引用")
            if relation.get("relation_type") != "mutually_exclusive" and not relation.get("coexistence_rule"):
                errors.append(f"{path} 非互斥候选必须说明共存方式")
        for index, candidate in enumerate(candidates or []):
            if isinstance(candidate, dict) and set(candidate.get("relation_ids") or []) - relation_ids:
                errors.append(f"reality_candidate_pool[{index}].relation_ids 存在无效引用")

    delta = data.get("calibration_delta")
    require_keys(delta, {"baseline_preserved", "confirmed", "supported_unselected", "conditional", "weakened", "rejected", "uncertain", "user_fact_evidence_ids", "claim_updates"}, "calibration_delta", errors)
    if isinstance(delta, dict):
        grouped = set().union(*(set(delta.get(key) or []) for key in ("confirmed", "supported_unselected", "conditional", "weakened", "rejected", "uncertain")))
        if grouped - candidate_ids:
            errors.append("calibration_delta 候选分组存在无效引用")
        user_fact_ids = set(delta.get("user_fact_evidence_ids") or [])
        if user_fact_ids - set(evidence_by_id) or any(evidence_by_id[item].get("source_layer") != "user_fact" for item in user_fact_ids if item in evidence_by_id):
            errors.append("calibration_delta.user_fact_evidence_ids 必须只引用用户事实证据")
        for index, update in enumerate(delta.get("claim_updates") or []):
            path = f"calibration_delta.claim_updates[{index}]"
            require_keys(update, {"claim_id", "before_status", "after_status", "reason", "user_fact_evidence_ids", "rewritten_reality_claim", "preserves_chart_mechanism"}, path, errors)
            if isinstance(update, dict):
                if update.get("claim_id") not in claim_ids:
                    errors.append(f"{path}.claim_id 存在无效引用")
                refs = set(update.get("user_fact_evidence_ids") or [])
                if refs - user_fact_ids:
                    errors.append(f"{path}.user_fact_evidence_ids 未登记在calibration_delta")
                if update.get("after_status") == "reject" and update.get("preserves_chart_mechanism") is not True:
                    errors.append(f"{path} 排除现实落点时仍须保留原命理机制记录")

    if data.get("monthly_theme_activation") is not None and not isinstance(data.get("monthly_theme_activation"), list):
        errors.append("monthly_theme_activation 必须是数组或 null")
    require_keys(data.get("calibration_state"), {"confirmed", "partial", "rejected", "uncertain", "updates"}, "calibration_state", errors)
    not_inferable = data.get("not_inferable_register")
    if not isinstance(not_inferable, list) or len(not_inferable) < 3:
        errors.append("not_inferable_register 至少包含 3 项")
    else:
        for index, item in enumerate(not_inferable):
            path = f"not_inferable_register[{index}]"
            require_keys(item, {"item", "reason", "evidence_level", "needed_input", "prohibited_claims"}, path, errors)
            if isinstance(item, dict) and item.get("evidence_level") not in {"weak", "insufficient"}:
                errors.append(f"{path}.evidence_level 必须是 weak/insufficient")

    audit = data.get("portrait_balance_audit")
    require_keys(audit, {"status", "covered_domains", "weak_domains", "unsupported_claims_removed", "cross_domain_paths", "warnings"}, "portrait_balance_audit", errors)
    if isinstance(audit, dict):
        covered = audit.get("covered_domains")
        if not isinstance(covered, list):
            errors.append("portrait_balance_audit.covered_domains 必须是数组")
        else:
            weak = set(audit.get("weak_domains") or [])
            missing_domains = sorted(MANDATORY_PORTRAIT_DOMAINS - set(covered) - weak)
            if missing_domains:
                errors.append(f"portrait_balance_audit 未覆盖或标弱的领域：{missing_domains}")
            required_weak = set().union(*(SOURCE_GAP_PORTRAIT_MAP[domain] for domain in uncovered_source_domains)) if uncovered_source_domains else set()
            if not required_weak.issubset(weak):
                errors.append(f"portrait_balance_audit.weak_domains 必须标记来源缺口：{sorted(required_weak)}")
            if required_weak & set(covered):
                errors.append("portrait_balance_audit 来源缺口领域不得同时标记为covered")
        paths = audit.get("cross_domain_paths")
        if not isinstance(paths, list) or len(paths) < 3:
            errors.append("portrait_balance_audit.cross_domain_paths 至少包含 3 条")
    require_keys(data.get("safety_boundaries"), {"disclaimer", "health", "finance", "legal", "relationships", "high_risk_flags"}, "safety_boundaries", errors)
    return errors


def empty_section() -> dict[str, Any]:
    return {"summary": "证据不足，保留结构。", "findings": []}


def self_test_fixture() -> dict[str, Any]:
    pillar = {"stem": "甲", "branch": "寅", "stem_ten_god": "比肩", "hidden_stems": [{"stem": "甲", "qi_level": "main", "ten_god": "比肩"}]}
    pillar_analysis = {"facts": [], "structural_role": "", "activation_keys": [], "possible_manifestations": [], "uncertainties": [], "findings": []}
    resource = {"acquire": [], "preserve": [], "exchange": [], "amplify": [], "loss_risks": [], "findings": []}
    annual = {"year": 2026, "age": 36, "luck_cycle_index": 0, "year_theme": "自检", "luck_theme_link": "自检", "activation_mechanisms": [], "natal_reactions": [], "change_intensity": "low", "direction": "consolidation", "domain_impacts": [], "domain_connections": [], "human_actions": [], "social_feedback": [], "carry_in": [], "carry_out": [], "seed_for_next": [], "confidence": "to_verify", "alternatives": [], "validation": []}
    candidate_domains = ["career", "finance_resources", "love_partner", "family_growth", "body_emotion", "self_growth", "career", "finance_resources", "love_partner", "family_growth", "body_emotion", "self_growth", "career", "finance_resources", "love_partner", "family_growth", "body_emotion", "self_growth"]
    candidate = lambda number: {"candidate_id": f"c{number}", "domain": candidate_domains[number - 1], "reality_dimension": f"candidate_axis_{number}", "parent_category": f"candidate_group_{number}", "label": f"候选侧面{number}", "attributes": [f"属性{number}"], "candidate_kind": "timed_event" if number == 6 else "objective_state" if number == 2 else "current_stage" if number == 12 else "stable_pattern", "time_scope": "过去五年" if number == 6 else "当前阶段" if number == 12 else "原局长期", "calibration_targets": ["reality_domains"], "statement": f"用于验证第{number}个现实侧面的自检陈述", "observable_examples": [f"第{number}个可观察例子甲", f"第{number}个可观察例子乙"], "alternative_statement": f"第{number}个候选也可能有另一种解释", "counterevidence": [], "unsupported_extensions": ["不能据此断定具体职业"], "source_layers": ["annual", "cross_method"] if number == 6 else ["chart", "cross_method"], "evidence_ids": [f"evidence_{number}", f"evidence_{1 if number == 24 else number + 1}"], "related_claim_ids": [f"claim_self_{number}"], "relation_ids": [f"relation_{(number - 1) // 3 + 1}"], "confidence": "to_verify", "validation_question": "哪个现实侧面更接近实际？", "status": "unverified"}
    partner_profile = {"summary": "自检", "traits": [], "mechanism": [], "benefits": [], "costs": [], "evidence_strength": "insufficient", "alternatives": [], "validation": [], "findings": []}
    complete_self_portrait = {
        "summary": "自检",
        "outward_presentation": empty_section(),
        "inner_motivation": empty_section(),
        "cognition_and_decision": empty_section(),
        "emotional_security": empty_section(),
        "action_and_execution": empty_section(),
        "values_and_boundaries": empty_section(),
        "stress_and_recovery": empty_section(),
        "contradictions": empty_section(),
        "environment_fit": empty_section(),
        "development_line": empty_section(),
        "findings": [],
    }
    family_system = {
        "summary": "自检",
        "early_resources": empty_section(),
        "expectations_and_costs": empty_section(),
        "role_position": empty_section(),
        "independence_and_boundaries": empty_section(),
        "partner_family_interface": empty_section(),
        "repetition_and_revision": empty_section(),
        "cross_domain_links": [],
        "findings": [],
    }
    relationship_system = {
        "summary": "自检",
        "intimacy_needs": empty_section(),
        "attraction_process": empty_section(),
        "expression_style": empty_section(),
        "conflict_pattern": empty_section(),
        "repair_pattern": empty_section(),
        "commitment_conditions": empty_section(),
        "autonomy_and_closeness": empty_section(),
        "career_family_money_effects": empty_section(),
        "findings": [],
    }
    interaction_dynamics = {
        "summary": "自检",
        "meeting_and_attention": empty_section(),
        "trust_building": empty_section(),
        "intimacy_development": empty_section(),
        "conflict_triggers": empty_section(),
        "conflict_response": empty_section(),
        "repair_conditions": empty_section(),
        "commitment_and_shared_life": empty_section(),
        "cross_domain_effects": empty_section(),
        "findings": [],
    }
    not_inferable = lambda number: {"item": f"不可推断项{number}", "reason": "自检", "evidence_level": "insufficient", "needed_input": [], "prohibited_claims": ["禁止编造"]}
    report_domains = ["self_growth", "love_partner", "career", "finance_resources", "body_emotion", "family_growth"]
    domain_labels = {"self_growth": "决策与成长", "love_partner": "关系互动", "career": "工作职能", "finance_resources": "收入与留存", "body_emotion": "压力与恢复", "family_growth": "家庭边界"}

    def domain_source(index: int, coverage: list[str]) -> dict[str, Any]:
        own = [f"claim_self_{index * 8 + offset}" for offset in range(1, 9)]
        neighbor = (index + 1) % len(report_domains)
        shared = [f"claim_self_{neighbor * 8 + 1}"]
        claim_ids_for_source = own + shared
        return {
            "summary_materials": [f"{domain_labels[report_domains[index]]}素材{offset}" for offset in range(1, len(claim_ids_for_source) + 1)],
            "claim_ids": claim_ids_for_source,
            "claim_priority": claim_ids_for_source,
            "domain_specific_claim_ids": own,
            "mainline_claim_ids": shared,
            "mandatory_candidate_ids": own[:2],
            "emphasis_candidate_ids": own[:1],
            "domain_mechanisms": [f"{domain_labels[report_domains[index]]}的形成机制", f"{domain_labels[report_domains[index]]}的阶段变化机制"],
            "survives_without_mainline": True,
            "formation_chain_ids": ["formation_1"],
            "linkage_chain_ids": ["linkage_1"],
            "concrete_candidates": [],
            "coverage": coverage,
            "coverage_claim_map": {tag: [own[offset % len(own)], own[(offset + 1) % len(own)]] for offset, tag in enumerate(coverage)},
            "evidence_gaps": [],
        }

    method_specs = [
        ("pattern_structure", "primary", "pattern_organization", 2),
        ("momentum_configuration", "primary", "momentum_intention", 2),
        ("climate_adjustment", "primary", "climate_environment", 2),
        ("ten_god_dynamics", "primary", "relationship_action", 2),
        ("root_seed_flower_fruit", "primary", "development_continuity", 2),
        ("blind_school", "primary", "blind_action_path", 2),
        ("timing_continuity", "primary", "timing_execution", 2),
        ("position_relationship", "partial", "position_interface", 1),
        ("stem_branch_dynamics", "partial", "stem_branch_structure", 1),
    ]
    method_evidence_ids: dict[str, list[str]] = {}
    evidence_cursor = 1
    for method_id, _, _, conclusion_count in method_specs:
        method_evidence_ids[method_id] = [f"evidence_{evidence_cursor + offset}" for offset in range(conclusion_count)]
        evidence_cursor += conclusion_count

    hypothesis_context = {
        ("pattern_structure", 1): ("self_growth", "综合现实方向1"),
        ("momentum_configuration", 1): ("self_growth", "综合现实方向1"),
        ("climate_adjustment", 1): ("love_partner", "综合现实方向2"),
        ("ten_god_dynamics", 1): ("love_partner", "综合现实方向2"),
        ("root_seed_flower_fruit", 1): ("career", "综合现实方向3"),
        ("blind_school", 1): ("career", "综合现实方向3"),
        ("timing_continuity", 1): ("finance_resources", "综合现实方向4"),
        ("pattern_structure", 2): ("finance_resources", "综合现实方向4"),
        ("momentum_configuration", 2): ("body_emotion", "综合现实方向5"),
        ("ten_god_dynamics", 2): ("body_emotion", "综合现实方向5"),
        ("climate_adjustment", 2): ("family_growth", "综合现实方向6"),
        ("root_seed_flower_fruit", 2): ("family_growth", "综合现实方向6"),
        ("blind_school", 2): ("self_growth", "单一主要方法补充侧面"),
    }

    independent_methods = []
    for method_index, (method_id, tier, group, conclusion_count) in enumerate(method_specs):
        conclusions = [
            {
                "conclusion_id": f"mc_{method_id}_{offset}",
                "statement": f"{method_id}第{offset}条独立技术结论用于结构自检",
                "mechanism_chain": ["读取本方法规定的排盘事实", "形成不依赖其他方法的技术判断"],
                "chart_refs": ["chart_facts.pillars"],
                "evidence_ids": [method_evidence_ids[method_id][offset - 1]],
                "conditions": ["本方法成立条件得到满足"],
                "counterconditions": ["出现削弱本方法解释的结构条件"],
                "time_scope": "原局长期",
                "confidence": "to_verify",
            }
            for offset in range(1, conclusion_count + 1)
        ]
        hypotheses = [
            {
                "hypothesis_id": f"mh_{method_id}_{offset}",
                "derived_from_conclusion_ids": [f"mc_{method_id}_{offset}"],
                "domain": hypothesis_context.get((method_id, offset), (report_domains[(method_index + offset - 1) % len(report_domains)], f"{method_id}现实方向{offset}"))[0],
                "normalized_direction": hypothesis_context.get((method_id, offset), (report_domains[(method_index + offset - 1) % len(report_domains)], f"{method_id}现实方向{offset}"))[1],
                "statement": f"由{method_id}独立推演得到的第{offset}条可观察现实候选。",
                "observable_indicators": [f"{method_id}表现{offset}A", f"{method_id}表现{offset}B"],
                "conditions": ["对应现实条件成立"],
                "counterevidence": ["持续出现相反现实表现"],
                "unsupported_extensions": ["不能据此断定唯一现实结果"],
                "time_scope": "原局长期",
                "reality_confirmation": "unverified",
            }
            for offset in range(1, conclusion_count + 1)
        ]
        independent_methods.append({
            "method_id": method_id,
            "tier": tier,
            "independence_group": group,
            "status": "complete",
            "attempt_count": 1,
            "failure_reasons": [],
            "degradation_effects": [],
            "input_scope": "chart_only_topic_isolated",
            "method_input_sha256": "a" * 64,
            "input_fact_refs": ["chart_facts.pillars"],
            "source_method_ids_read": [],
            "technical_conclusions": conclusions,
            "reality_hypotheses": hypotheses,
            "domain_assessments": [
                {
                    "domain": domain,
                    "status": (
                        "supported" if any(item["domain"] == domain for item in hypotheses)
                        else "insufficient_evidence" if domain == "love_partner" and method_id in {
                            "ten_god_dynamics", "position_relationship", "stem_branch_dynamics",
                            "blind_school", "timing_continuity",
                        }
                        else "not_applicable"
                    ),
                    "hypothesis_ids": [
                        item["hypothesis_id"] for item in hypotheses if item["domain"] == domain
                    ],
                    "reasoning": (
                        "本方法形成了该领域的现实候选"
                        if any(item["domain"] == domain for item in hypotheses)
                        else "本方法已检查该领域但未形成足够证据"
                    ),
                }
                for domain in sorted(REPORT_DOMAINS)
            ],
            "limitations": ["本方法不能单独保证具体事件"],
        })

    synthesis_pairs = [
        (("pattern_structure", 1), ("momentum_configuration", 1)),
        (("climate_adjustment", 1), ("ten_god_dynamics", 1)),
        (("root_seed_flower_fruit", 1), ("blind_school", 1)),
        (("timing_continuity", 1), ("pattern_structure", 2)),
        (("momentum_configuration", 2), ("ten_god_dynamics", 2)),
        (("climate_adjustment", 2), ("root_seed_flower_fruit", 2)),
    ]
    synthesis_clusters = []
    for index, ((left, left_offset), (right, right_offset)) in enumerate(synthesis_pairs, 1):
        member_ids = [f"mh_{left}_{left_offset}", f"mh_{right}_{right_offset}"]
        groups = [next(item[2] for item in method_specs if item[0] == left), next(item[2] for item in method_specs if item[0] == right)]
        synthesis_clusters.append({
            "synthesis_id": f"syn_{index}",
            "domain": report_domains[index - 1],
            "normalized_direction": f"综合现实方向{index}",
            "member_hypothesis_ids": member_ids,
            "supporting_method_ids": [left, right],
            "independence_groups": groups,
            "relationship_type": "same_direction",
            "structural_confidence": "high",
            "reality_confirmation": "unverified",
            "counterevidence": [],
            "report_role": "primary",
            "reasoning": "两个不同主要方法家族独立得到同向现实候选",
        })
    synthesis_clusters.append({
        "synthesis_id": "syn_supplemental",
        "domain": "self_growth",
        "normalized_direction": "单一主要方法补充侧面",
        "member_hypothesis_ids": ["mh_blind_school_2"],
        "supporting_method_ids": ["blind_school"],
        "independence_groups": ["blind_action_path"],
        "relationship_type": "complementary",
        "structural_confidence": "to_verify",
        "reality_confirmation": "unverified",
        "counterevidence": [],
        "report_role": "supplemental",
        "reasoning": "单一主要方法提供不矛盾且新增信息的补充侧面",
    })

    evidence_method_sequence = [
        "pattern_structure", "pattern_structure", "momentum_configuration", "momentum_configuration",
        "climate_adjustment", "climate_adjustment", "ten_god_dynamics", "ten_god_dynamics",
        "root_seed_flower_fruit", "root_seed_flower_fruit", "blind_school", "blind_school",
        "timing_continuity", "timing_continuity", "position_relationship", "stem_branch_dynamics",
        "pattern_structure", "momentum_configuration", "climate_adjustment", "ten_god_dynamics",
        "root_seed_flower_fruit", "blind_school", "timing_continuity", "pattern_structure",
    ]
    method_groups = {item[0]: item[2] for item in method_specs}
    source_layers = {
        "root_seed_flower_fruit": "root_seed_flower_fruit",
        "blind_school": "blind_shared",
        "timing_continuity": "luck_cycle",
    }

    def report_claim(number: int) -> dict[str, Any]:
        domain_index = (number - 1) // 8
        domain = report_domains[domain_index]
        local_index = (number - 1) % 8 + 1
        if number == 8:
            synthesis_id = "syn_supplemental"
            method_ids = ["blind_school"]
            hypothesis_ids = ["mh_blind_school_2"]
            evidence_ids = ["evidence_11", "evidence_12"]
            report_role = "supplemental"
            confidence = "to_verify"
        else:
            synthesis_index = domain_index + 1
            synthesis_id = f"syn_{synthesis_index}"
            pair = synthesis_pairs[synthesis_index - 1]
            method_ids = [item[0] for item in pair]
            hypothesis_ids = [f"mh_{method_id}_{offset}" for method_id, offset in pair]
            evidence_ids = [method_evidence_ids[method_id][0] for method_id in method_ids]
            report_role = "primary"
            confidence = "high"
        return {
            "claim_id": f"claim_self_{number}",
            "domain": domain,
            "reality_dimension": f"axis_{local_index}",
            "claim_family": f"family_{(number - 1) % 4 + 1}",
            "mechanism_family": f"mechanism_{(number - 1) % 3 + 1}",
            "claim": f"{domain_labels[domain]}的第{local_index}项内部自检判断",
            "plain_claim": f"你在{domain_labels[domain]}方面可能呈现第{local_index}种可核对的独立表现。",
            "new_information": f"{domain_labels[domain]}新增信息{local_index}",
            "mechanism_chain": ["读取独立方法现实候选", "经综合层形成报告判断"],
            "evidence_ids": evidence_ids,
            "supporting_methods": method_ids,
            "synthesis_ids": [synthesis_id],
            "method_hypothesis_ids": hypothesis_ids,
            "claim_class": "independent_supplement" if number == 8 else "primary_judgment",
            "report_role": report_role,
            "coverage_tags": [BASE_COVERAGE[(local_index - 1) % len(BASE_COVERAGE)]],
            "applicable_conditions": ["对应现实条件成立"],
            "reality_confirmation": "unverified",
            "allowed_examples": ["可观察行为"],
            "counterevidence": [],
            "confidence": confidence,
            "unsupported_extensions": ["不能据此断定唯一现实结果"],
            "calibration_status": "unverified",
            "origin": "chart_baseline",
        }

    data = {
        "analysis_meta": {"analysis_id": "self-test", "request_id": "self-test", "core_version": "0.15.0", "generated_at": "2026-08-18T00:00:00+08:00", "analysis_as_of": "2026-08-18", "target_range": {"start_year": 2026, "end_year": 2026}, "input_completeness": "complete", "status": "complete"},
        "chart_facts": {"day_master": "甲", "pillars": {"year": pillar, "month": pillar, "day": {**pillar, "stem_ten_god": "日主"}, "hour": pillar}, "luck_cycles": [{}], "annual_cycles": [{}]},
        "chart_audit": {"status": "pass", "checks": [], "boundary_dependencies": [], "versions": []},
        "social_context_model": empty_section(),
        "five_elements": None,
        "day_master": empty_section(),
        "stems_branches_roots": {"summary": "", "pillars": {"year": pillar_analysis, "month": pillar_analysis, "day": pillar_analysis, "hour": pillar_analysis}, "findings": []},
        "interaction_network": empty_section(),
        "independent_method_analyses": independent_methods,
        "method_execution_audit": {
            "retry_limit": 3,
            "completed_method_ids": [item[0] for item in method_specs if item[3]],
            "excluded_method_ids": [],
            "failed_method_ids": [],
            "primary_completed_count": 7,
            "structural_anchor_complete": True,
            "reality_anchor_complete": True,
            "timing_anchor_complete": True,
            "delivery_decision": "full",
            "degradation_reasons": [],
            "stage_validation_passed": True,
        },
        "source_coverage_audit": build_source_coverage_audit(independent_methods),
        "method_synthesis": {
            "summary": "各方法独立推演后按现实方向归并",
            "clusters": synthesis_clusters,
            "conflicts": [],
            "primary_synthesis_ids": [f"syn_{i}" for i in range(1, 7)],
            "supplemental_synthesis_ids": ["syn_supplemental"],
            "to_verify_synthesis_ids": [],
        },
        "cross_method_analysis": {"summary": "自检", "methods": sorted(PRIMARY_METHODS), "agreements": ["自检交叉支持"], "conflicts": [], "findings": []},
        "blind_school_cross_analysis": {
            "source_boundaries": ["段氏宾主体用与做功仅作交叉", "杨氏明暗虚实与岁运动静仅作交叉"],
            "host_guest_map": [], "body_function_map": [],
            "work_paths": [{"path_id": "work_1", "actor": "命主", "tool": "专业能力", "target": "外部任务", "mechanism": ["整理后执行"], "direction": "由外向内取得结果", "result_type": "项目成果", "retained_by_subject": True, "costs": ["准备时间"], "failure_conditions": ["职责边界不清"], "evidence_ids": ["evidence_11"], "method_sources": ["blind_shared"], "confidence": "to_verify"}],
            "image_hypotheses": [],
            "reality_image_candidates": [
                {"image_id": "image_org", "dimension": "organization", "candidate_labels": ["仅用于结构校验的组织候选"], "derivation_chain": ["宾主区分", "体用落实"], "evidence_ids": ["evidence_11", "evidence_12"], "non_blind_support": ["格局调候"], "counterevidence": ["自主性仍待验证"], "limitations": ["不能指定单位"], "confidence": "to_verify"},
                {"image_id": "image_industry", "dimension": "industry", "candidate_labels": ["专业服务"], "derivation_chain": ["处理对象", "结果形式"], "evidence_ids": ["evidence_11", "evidence_12"], "non_blind_support": ["根苗花果"], "counterevidence": ["行业事实未知"], "limitations": ["不能指定行业"], "confidence": "to_verify"},
                {"image_id": "image_function", "dimension": "function", "candidate_labels": ["研究分析"], "derivation_chain": ["工具能力", "工作动作"], "evidence_ids": ["evidence_11", "evidence_12"], "non_blind_support": ["十神网络"], "counterevidence": ["岗位事实未知"], "limitations": ["不能指定岗位"], "confidence": "to_verify"},
                {"image_id": "image_result", "dimension": "result_form", "candidate_labels": ["项目成果"], "derivation_chain": ["做功路径", "结果归属"], "evidence_ids": ["evidence_11", "evidence_12"], "non_blind_support": ["岁运连续"], "counterevidence": ["成果事实未知"], "limitations": ["不能保证结果"], "confidence": "to_verify"}
            ],
            "virtual_real_completeness": [], "timing_activation": [],
            "agreements": ["与根苗花果的积累路径方向一致"], "conflicts": ["旺衰权重在两套参考中不同"],
            "prohibited_extensions": ["不推具体职业", "不推收入金额", "不推疾病寿夭", "不推婚姻结果"]
        },
        "evidence_registry": [
            {"evidence_id": f"evidence_{i}", "source_layer": source_layers.get(evidence_method_sequence[i - 1], "cross_method"), "method": evidence_method_sequence[i - 1], "method_id": evidence_method_sequence[i - 1], "independence_group": method_groups[evidence_method_sequence[i - 1]], "chart_refs": ["chart_facts.pillars"], "observation": f"自检结构观察{i}", "interpretation": "仅用于校验实体证据引用关系", "limitations": ["不能外推具体职业"], "confidence": "to_verify"}
            for i in range(1, 25)
        ],
        "root_seed_flower_fruit_map": {"summary": "自检", "root": empty_section(), "seedling": empty_section(), "flower": empty_section(), "fruit": empty_section(), "continuity": ["根与苗跨阶段连续", "花与果在当前同时作用", "成果进入下一轮传承"], "domain_lifecycles": [
            {"domain": "career", "root": "专业基础", "seedling": "技能训练", "flower": "方案呈现", "fruit": "项目成果", "continuity": "专业基础经训练转化为方案和成果", "evidence_ids": ["evidence_9", "evidence_10"], "confidence": "to_verify"},
            {"domain": "finance_resources", "root": "资源来源", "seedling": "获取能力", "flower": "收入表现", "fruit": "资产留存", "continuity": "资源来源经能力转化为收入和留存", "evidence_ids": ["evidence_9", "evidence_10"], "confidence": "to_verify"},
            {"domain": "love_partner", "root": "关系经验", "seedling": "信任能力", "flower": "吸引互动", "fruit": "长期关系", "continuity": "关系经验经信任建立进入互动和承诺", "evidence_ids": ["evidence_9", "evidence_10"], "confidence": "to_verify"}
        ], "findings": []},
        "natal_portrait": empty_section(),
        "complete_self_portrait": complete_self_portrait,
        "family_system": family_system,
        "resource_relationship": {"summary": "", "material": resource, "institutional": resource, "relational": resource, "capability": resource, "time_energy": resource, "psychological": resource, "findings": []},
        "social_relationship_style": empty_section(),
        "relationship_system": relationship_system,
        "partner_profiles": {"summary": "自检", "attraction": partner_profile, "sustainable": partner_profile, "high_attraction_high_friction": partner_profile, "evidence_limitations": ["单人命盘限制"], "findings": []},
        "interaction_dynamics": interaction_dynamics,
        "environment_and_mobility": empty_section(),
        "reality_domains": {key: empty_section() for key in ("career", "wealth", "learning", "relationships", "family", "mobility", "health", "growth")},
        "domain_connections": [],
        "luck_cycle_themes": [{"cycle_index": 0, "start_year": 2020, "end_year": 2029, "theme_statement": "自检", "structural_mechanism": ["自检"], "opportunities": [], "costs": [], "required_capabilities": [], "activated_domains": [], "activation_keys": [], "entry_phase": "", "middle_phase": "", "exit_phase": "", "continuity_from_previous": "", "seed_for_next": "", "confidence": "to_verify", "alternatives": [], "birth_time_dependency": "none"}],
        "annual_theme_activation": [annual],
        "monthly_theme_activation": None,
        "life_stages": [],
        "turning_points": [],
        "report_claim_ledger": [report_claim(i) for i in range(1, 49)],
        "formation_chains": [
            {"chain_id": f"formation_{i}", "starting_condition": "早期规则较明确", "adaptation_need": "需要减少出错", "learned_response": "先观察再行动", "ability_formed": "能够整理复杂信息", "constraint": "进入新环境较慢", "adult_pattern": "先确认要求再执行", "linked_domains": ["self_growth", "career"], "current_change": "开始增加主动表达", "claim_ids": ["claim_self_1", "claim_self_2"], "confidence": "to_verify"}
            for i in range(1, 4)
        ],
        "portrait_thesis": {"summary": "这是用于检验完整人物主轴、另一面、矛盾和当前变化是否同时存在的自检内容。", "primary_traits": ["先确认条件再行动", "重视专业积累"], "complementary_traits": ["条件明确时也能快速推进"], "internal_tensions": ["稳定准备与主动尝试并存"], "observable_patterns": ["先列步骤", "交付前核对", "在熟悉领域主动表达"], "formation_chain_ids": ["formation_1", "formation_2"], "current_shift": "当前阶段开始增加主动表达和尝试", "evidence_ids": ["evidence_1", "evidence_3", "evidence_9", "evidence_13"], "boundaries": ["不能指定具体职业"]},
        "domain_linkage_chains": [
            {"chain_id": f"linkage_{i}", "trigger": "责任增加", "transmission": ["提高稳定需求", "减少快速变化"], "affected_domains": ["career", "finance_resources"], "time_lag": "逐步出现", "amplifiers": [], "buffers": [], "claim_ids": ["claim_self_1", "claim_self_2"], "confidence": "to_verify"}
            for i in range(1, 4)
        ],
        "report_source_bundle": {
            "life_narrative_source": domain_source(0, list(BASE_COVERAGE)),
            "dimensions": {
                "self_growth": domain_source(0, ["feature", "behavior", "formation", "challenge", "current_change", "response"]),
                "career": domain_source(2, ["feature", "behavior", "formation", "challenge", "current_change", "response"]),
                "finance_resources": domain_source(3, ["feature", "behavior", "formation", "challenge", "current_change", "response"]),
                "love_partner": domain_source(1, ["feature", "behavior", "formation", "challenge", "current_change", "response"]),
                "family_growth": domain_source(5, ["feature", "behavior", "formation", "challenge", "current_change", "response", "parent_kin_interaction", "support_and_constraint", "independence_and_reciprocity"]),
                "body_emotion": domain_source(4, ["feature", "behavior", "formation", "challenge", "current_change", "response", "baseline_signals", "stress_sequence", "recovery_pattern"])
            },
            "current_stage_source": {**domain_source(5, list(BASE_COVERAGE)), "formation_chain_ids": []}
        },
        "reality_candidate_pool": [candidate(i) for i in range(1, 19)],
        "candidate_relation_map": [
            {"relation_id": f"relation_{i}", "candidate_ids": [f"c{(i - 1) * 3 + 1}", f"c{(i - 1) * 3 + 2}", f"c{(i - 1) * 3 + 3}"], "relation_type": "compatible", "comparison_axis": "现实表现方式", "time_scope": "原局长期", "coexistence_rule": "三项可在不同任务中同时存在", "exclusion_rule": "只有同一时段客观事实冲突才排除", "evidence_ids": [f"evidence_{i}", f"evidence_{i + 1}"], "confidence": "to_verify"}
            for i in range(1, 7)
        ],
        "calibration_state": {"confirmed": [], "partial": [], "rejected": [], "uncertain": [], "updates": []},
        "calibration_delta": {"baseline_preserved": True, "confirmed": [], "supported_unselected": [], "conditional": [], "weakened": [], "rejected": [], "uncertain": [f"c{i}" for i in range(1, 19)], "user_fact_evidence_ids": [], "claim_updates": []},
        "not_inferable_register": [not_inferable(i) for i in range(1, 4)],
        "portrait_balance_audit": {"status": "pass_with_flags", "covered_domains": sorted(MANDATORY_PORTRAIT_DOMAINS), "weak_domains": [], "unsupported_claims_removed": [], "cross_domain_paths": ["自检1", "自检2", "自检3"], "warnings": []},
        "uncertainty_register": [],
        "safety_boundaries": {"disclaimer": "仅供传统文化体验与自我观察。", "health": "", "finance": "", "legal": "", "relationships": "", "high_risk_flags": []}
    }
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="校验人生有迹 analysis_bundle JSON")
    parser.add_argument("json_file", nargs="?", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    try:
        schema = load_json(SCHEMA_PATH)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Schema 无法读取：{exc}", file=sys.stderr)
        return 2
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        print("Schema 版本不是 JSON Schema 2020-12", file=sys.stderr)
        return 2

    if args.self_test:
        data = self_test_fixture()
        errors = validate_schema_instance(data, schema)
        errors.extend(validate(data))
    elif args.json_file:
        try:
            data = load_json(args.json_file)
            errors = validate_schema_instance(data, schema)
            errors.extend(validate(data))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"输出 JSON 无法读取：{exc}", file=sys.stderr)
            return 2
    else:
        parser.error("请提供 json_file 或 --self-test")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("OK: analysis output validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
