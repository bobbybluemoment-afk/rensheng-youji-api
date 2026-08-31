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
from report_source_contract import BASE_COVERAGE, DIMENSIONS, required_coverage  # noqa: E402

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
        if meta.get("core_version") != "0.9.0":
            errors.append("analysis_meta.core_version 必须为 0.9.0")
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
        if not isinstance(methods, list) or len(set(methods)) < 3:
            errors.append("cross_method_analysis.methods 至少包含三个独立方法")
        if not isinstance(cross_method.get("agreements"), list) or not cross_method.get("agreements"):
            errors.append("cross_method_analysis.agreements 至少记录一项交叉支持")
        if not isinstance(cross_method.get("conflicts"), list):
            errors.append("cross_method_analysis.conflicts 必须是数组；无冲突时使用空数组")

    blind = data.get("blind_school_cross_analysis")
    require_keys(blind, {"source_boundaries", "host_guest_map", "body_function_map", "work_paths", "image_hypotheses", "reality_image_candidates", "virtual_real_completeness", "timing_activation", "agreements", "conflicts", "prohibited_extensions"}, "blind_school_cross_analysis", errors)
    if isinstance(blind, dict):
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

    registry = data.get("evidence_registry")
    evidence_by_id: dict[str, dict[str, Any]] = {}
    if not isinstance(registry, list) or len(registry) < 24:
        errors.append("evidence_registry 至少包含24条实体证据")
    else:
        for index, evidence in enumerate(registry):
            path = f"evidence_registry[{index}]"
            require_keys(evidence, {"evidence_id", "source_layer", "method", "chart_refs", "observation", "interpretation", "limitations", "confidence"}, path, errors)
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
    if isinstance(blind, dict):
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
    if isinstance(root_map, dict):
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
    if not isinstance(claims, list) or len(claims) < 48:
        errors.append("report_claim_ledger 至少包含48条报告级候选判断")
    else:
        for index, claim in enumerate(claims):
            path = f"report_claim_ledger[{index}]"
            require_keys(claim, {"claim_id", "domain", "reality_dimension", "claim_family", "mechanism_family", "claim", "plain_claim", "new_information", "mechanism_chain", "evidence_ids", "supporting_methods", "allowed_examples", "counterevidence", "confidence", "unsupported_extensions", "calibration_status", "origin"}, path, errors)
            if not isinstance(claim, dict):
                continue
            claim_id = claim.get("claim_id")
            if isinstance(claim_id, str):
                if claim_id in claim_ids:
                    errors.append(f"{path}.claim_id 不能重复")
                claim_ids.add(claim_id)
                claim_by_id[claim_id] = claim
            if not isinstance(claim.get("evidence_ids"), list) or len(set(claim.get("evidence_ids") or [])) < 2:
                errors.append(f"{path}.evidence_ids 至少包含两个独立证据")
            if not isinstance(claim.get("supporting_methods"), list) or len(set(claim.get("supporting_methods") or [])) < 2:
                errors.append(f"{path}.supporting_methods 至少包含两种交叉方法")
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
            if len({(item.get("source_layer"), item.get("method")) for item in substantive}) < 2:
                errors.append(f"{path} 至少需要两个不同的命盘或时运证据视角")
            if claim.get("confidence") == "high" and any(item.get("source_layer") in BLIND_LAYERS for item in resolved) and not any(item.get("source_layer") in NON_BLIND_LAYERS for item in resolved):
                errors.append(f"{path} 高置信盲派判断必须有非盲派方法交叉支持")
            if claim.get("origin") == "user_fact_refinement" and not any(item.get("source_layer") == "user_fact" for item in resolved):
                errors.append(f"{path}.origin=user_fact_refinement 时必须引用用户事实证据")
            if not isinstance(claim.get("unsupported_extensions"), list) or not claim.get("unsupported_extensions"):
                errors.append(f"{path}.unsupported_extensions 至少说明一项禁止外推")
            if any(term in str(claim.get("claim", "")) for term in ("必然离婚", "一定离婚", "必然发财", "保证发财", "牢狱之灾", "必得重病", "短寿", "死亡年份")):
                errors.append(f"{path}.claim 含有禁止的确定性高风险断语")
        domain_counts = {domain: sum(1 for claim in claims if isinstance(claim, dict) and claim.get("domain") == domain) for domain in REPORT_DOMAINS}
        thin = sorted(domain for domain, count in domain_counts.items() if count < 8)
        if thin:
            errors.append(f"report_claim_ledger 六个报告领域各至少8条候选判断，当前不足：{thin}")
        for domain in REPORT_DOMAINS:
            domain_claims = [item for item in claims if isinstance(item, dict) and item.get("domain") == domain]
            if len({item.get("claim_family") for item in domain_claims}) < 3:
                errors.append(f"report_claim_ledger.{domain} 至少包含三个不同判断家族")
            if len({item.get("mechanism_family") for item in domain_claims}) < 2:
                errors.append(f"report_claim_ledger.{domain} 至少包含两条不同命理机制路径")
            if len({item.get("reality_dimension") for item in domain_claims}) < 3:
                errors.append(f"report_claim_ledger.{domain} 至少覆盖三个现实问题轴")
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
            if len(source.get("summary_materials") or []) < 8 or len(source.get("claim_ids") or []) < 8:
                errors.append(f"{path} 至少包含8条素材和8个候选判断，以便校准后确定性替换")
            if set(source.get("claim_ids") or []) - claim_ids:
                errors.append(f"{path}.claim_ids 存在无效引用")
            source_ids = set(source.get("claim_ids") or [])
            priority = source.get("claim_priority") or []
            specific_ids = set(source.get("domain_specific_claim_ids") or [])
            mainline_ids = set(source.get("mainline_claim_ids") or [])
            emphasis_ids = set(source.get("emphasis_candidate_ids") or [])
            mandatory_ids = set(source.get("mandatory_candidate_ids") or [])
            if len(priority) != len(source_ids) or set(priority) != source_ids:
                errors.append(f"{path}.claim_priority 必须无重复地排列全部候选判断")
            minimum_specific = 6 if name.startswith("dimensions.") else 4
            if len(specific_ids) < minimum_specific or not specific_ids.issubset(source_ids):
                errors.append(f"{path}.domain_specific_claim_ids 至少包含{minimum_specific}个本节判断且必须属于claim_ids")
            if len(mainline_ids) > 2 or not mainline_ids.issubset(source_ids) or len(mainline_ids) / max(len(source_ids), 1) > 0.30:
                errors.append(f"{path} 的共享人生主线判断不得超过本节判断的30%")
            if not 2 <= len(mandatory_ids) <= 4 or not mandatory_ids.issubset(source_ids):
                errors.append(f"{path}.mandatory_candidate_ids 必须提供2—4条按优先级排列的必进候选")
            emphasis_range = (0, 4) if name == "life_narrative_source" else (0, 3)
            if not emphasis_range[0] <= len(emphasis_ids) <= emphasis_range[1] or not emphasis_ids.issubset(source_ids):
                errors.append(f"{path}.emphasis_candidate_ids 最多包含{emphasis_range[1]}个可独立成立的重点候选；没有合适句子时允许为空")
            if len(set(source.get("domain_mechanisms") or [])) < 2:
                errors.append(f"{path}.domain_mechanisms 至少包含两个领域自身机制")
            if source.get("survives_without_mainline") is not True:
                errors.append(f"{path} 去掉人生主线后必须仍能独立成立")
            if name.startswith("dimensions."):
                domain = name.split(".", 1)[1]
                wrong = [item for item in specific_ids if item in claim_by_id and claim_by_id[item].get("domain") != domain]
                if wrong:
                    errors.append(f"{path}.domain_specific_claim_ids 含其他领域判断：{sorted(wrong)}")
                required_tags = set(required_coverage(domain))
            else:
                required_tags = set(BASE_COVERAGE)
            coverage = set(source.get("coverage") or [])
            if not required_tags.issubset(coverage):
                errors.append(f"{path}.coverage 缺少统一人物覆盖项：{sorted(required_tags - coverage)}")
            coverage_map = source.get("coverage_claim_map")
            if not isinstance(coverage_map, dict) or not required_tags.issubset(set(coverage_map)):
                errors.append(f"{path}.coverage_claim_map 必须为每个规定覆盖项提供备用判断")
            else:
                for tag in required_tags:
                    mapped = coverage_map.get(tag)
                    if not isinstance(mapped, list) or len(set(mapped)) < 2 or set(mapped) - source_ids:
                        errors.append(f"{path}.coverage_claim_map.{tag} 必须绑定至少两个不同的本节候选判断")
                    elif name.startswith("dimensions.") and not (set(mapped) & specific_ids):
                        errors.append(f"{path}.coverage_claim_map.{tag} 至少包含一个领域专属判断")
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
            family_coverage = set((dimensions.get("family_growth") or {}).get("coverage") or [])
            if not {"parent_kin_interaction", "support_and_constraint", "independence_and_reciprocity"}.issubset(family_coverage):
                errors.append("家庭领域必须覆盖父母亲友互动、可借力与受限、独立与回馈")
            body_coverage = set((dimensions.get("body_emotion") or {}).get("coverage") or [])
            if not {"baseline_signals", "stress_sequence", "recovery_pattern"}.issubset(body_coverage):
                errors.append("身体与情绪领域必须覆盖基础反应、压力顺序和恢复方式")

    candidates = data.get("reality_candidate_pool")
    if not isinstance(candidates, list) or not 18 <= len(candidates) <= 30:
        errors.append("reality_candidate_pool 必须包含 18—30 条开放现实候选")
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
                if not isinstance(layers, list) or len(set(layers)) < 2:
                    errors.append(f"{path}.source_layers 至少包含两个独立证据视角")
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
                if len(evidence_ids) < 2 or evidence_ids - set(evidence_by_id):
                    errors.append(f"{path}.evidence_ids 必须包含至少两条有效实体证据")
                related_claim_ids = set(candidate.get("related_claim_ids") or [])
                if not related_claim_ids or related_claim_ids - claim_ids:
                    errors.append(f"{path}.related_claim_ids 必须引用有效报告判断")
                if not candidate.get("relation_ids"):
                    errors.append(f"{path}.relation_ids 至少引用一条候选关系")
        if len(ids) != len(set(ids)):
            errors.append("reality_candidate_pool.candidate_id 不能重复")
        missing_candidate_domains = sorted(REPORT_DOMAINS - domains)
        if missing_candidate_domains:
            errors.append(f"reality_candidate_pool 必须覆盖六个报告领域，当前缺少：{missing_candidate_domains}")

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
            missing_domains = sorted(MANDATORY_PORTRAIT_DOMAINS - set(covered))
            if missing_domains:
                errors.append(f"portrait_balance_audit 缺少领域：{missing_domains}")
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
    candidate_domains = ["career", "finance_resources", "love_partner", "family_growth", "body_emotion", "self_growth", "learning", "mobility", "career", "finance_resources", "love_partner", "family_growth", "body_emotion", "self_growth", "career", "finance_resources", "love_partner", "family_growth"]
    candidate = lambda number: {"candidate_id": f"c{number}", "domain": candidate_domains[number - 1], "reality_dimension": f"candidate_axis_{number}", "parent_category": f"candidate_group_{number}", "label": f"候选侧面{number}", "attributes": [f"属性{number}"], "candidate_kind": "timed_event" if number == 6 else "stable_pattern", "time_scope": "过去五年" if number == 6 else "原局长期", "calibration_targets": ["reality_domains"], "statement": f"用于验证第{number}个现实侧面的自检陈述", "observable_examples": [f"第{number}个可观察例子甲", f"第{number}个可观察例子乙"], "alternative_statement": f"第{number}个候选也可能有另一种解释", "counterevidence": [], "unsupported_extensions": ["不能据此断定具体职业"], "source_layers": ["annual", "cross_method"] if number == 6 else ["chart", "cross_method"], "evidence_ids": [f"evidence_{number}", f"evidence_{1 if number == 24 else number + 1}"], "related_claim_ids": [f"claim_self_{number}"], "relation_ids": [f"relation_{(number - 1) // 3 + 1}"], "confidence": "to_verify", "validation_question": "哪个现实侧面更接近实际？", "status": "unverified"}
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
            "summary_materials": [f"{domain_labels[report_domains[index]]}素材{offset}" for offset in range(1, 9)],
            "claim_ids": claim_ids_for_source,
            "claim_priority": claim_ids_for_source,
            "domain_specific_claim_ids": own,
            "mainline_claim_ids": shared,
            "mandatory_candidate_ids": own[:4],
            "emphasis_candidate_ids": own[:3],
            "domain_mechanisms": [f"{domain_labels[report_domains[index]]}的形成机制", f"{domain_labels[report_domains[index]]}的阶段变化机制"],
            "survives_without_mainline": True,
            "formation_chain_ids": ["formation_1"],
            "linkage_chain_ids": ["linkage_1"],
            "concrete_candidates": [],
            "coverage": coverage,
            "coverage_claim_map": {tag: [own[offset % len(own)], own[(offset + 1) % len(own)]] for offset, tag in enumerate(coverage)},
            "evidence_gaps": [],
        }

    data = {
        "analysis_meta": {"analysis_id": "self-test", "request_id": "self-test", "core_version": "0.9.0", "generated_at": "2026-08-18T00:00:00+08:00", "analysis_as_of": "2026-08-18", "target_range": {"start_year": 2026, "end_year": 2026}, "input_completeness": "complete", "status": "complete"},
        "chart_facts": {"day_master": "甲", "pillars": {"year": pillar, "month": pillar, "day": {**pillar, "stem_ten_god": "日主"}, "hour": pillar}, "luck_cycles": [{}], "annual_cycles": [{}]},
        "chart_audit": {"status": "pass", "checks": [], "boundary_dependencies": [], "versions": []},
        "social_context_model": empty_section(),
        "five_elements": None,
        "day_master": empty_section(),
        "stems_branches_roots": {"summary": "", "pillars": {"year": pillar_analysis, "month": pillar_analysis, "day": pillar_analysis, "hour": pillar_analysis}, "findings": []},
        "interaction_network": empty_section(),
        "cross_method_analysis": {"summary": "自检", "methods": ["格局", "调候", "根苗花果"], "agreements": ["自检交叉支持"], "conflicts": [], "findings": []},
        "blind_school_cross_analysis": {
            "source_boundaries": ["段氏宾主体用与做功仅作交叉", "杨氏明暗虚实与岁运动静仅作交叉"],
            "host_guest_map": [], "body_function_map": [],
            "work_paths": [{"path_id": "work_1", "actor": "命主", "tool": "专业能力", "target": "外部任务", "mechanism": ["整理后执行"], "direction": "由外向内取得结果", "result_type": "项目成果", "retained_by_subject": True, "costs": ["准备时间"], "failure_conditions": ["职责边界不清"], "evidence_ids": ["evidence_1"], "method_sources": ["blind_shared"], "confidence": "to_verify"}],
            "image_hypotheses": [],
            "reality_image_candidates": [
                {"image_id": "image_org", "dimension": "organization", "candidate_labels": ["仅用于结构校验的组织候选"], "derivation_chain": ["宾主区分", "体用落实"], "evidence_ids": ["evidence_1", "evidence_2"], "non_blind_support": ["格局调候"], "counterevidence": ["自主性仍待验证"], "limitations": ["不能指定单位"], "confidence": "to_verify"},
                {"image_id": "image_industry", "dimension": "industry", "candidate_labels": ["专业服务"], "derivation_chain": ["处理对象", "结果形式"], "evidence_ids": ["evidence_3", "evidence_4"], "non_blind_support": ["根苗花果"], "counterevidence": ["行业事实未知"], "limitations": ["不能指定行业"], "confidence": "to_verify"},
                {"image_id": "image_function", "dimension": "function", "candidate_labels": ["研究分析"], "derivation_chain": ["工具能力", "工作动作"], "evidence_ids": ["evidence_5", "evidence_6"], "non_blind_support": ["十神网络"], "counterevidence": ["岗位事实未知"], "limitations": ["不能指定岗位"], "confidence": "to_verify"},
                {"image_id": "image_result", "dimension": "result_form", "candidate_labels": ["项目成果"], "derivation_chain": ["做功路径", "结果归属"], "evidence_ids": ["evidence_7", "evidence_8"], "non_blind_support": ["岁运连续"], "counterevidence": ["成果事实未知"], "limitations": ["不能保证结果"], "confidence": "to_verify"}
            ],
            "virtual_real_completeness": [], "timing_activation": [],
            "agreements": ["与根苗花果的积累路径方向一致"], "conflicts": ["旺衰权重在两套参考中不同"],
            "prohibited_extensions": ["不推具体职业", "不推收入金额", "不推疾病寿夭", "不推婚姻结果"]
        },
        "evidence_registry": [
            {"evidence_id": f"evidence_{i}", "source_layer": "annual" if i == 3 else "luck_cycle" if i == 4 else "natal" if i % 2 else "root_seed_flower_fruit", "method": "流年执行" if i == 3 else "大运主题" if i == 4 else "格局调候" if i % 2 else "根苗花果", "chart_refs": ["chart_facts.pillars"], "observation": f"自检结构观察{i}", "interpretation": "仅用于校验实体证据引用关系", "limitations": ["不能外推具体职业"], "confidence": "to_verify"}
            for i in range(1, 25)
        ],
        "root_seed_flower_fruit_map": {"summary": "自检", "root": empty_section(), "seedling": empty_section(), "flower": empty_section(), "fruit": empty_section(), "continuity": ["根与苗跨阶段连续", "花与果在当前同时作用", "成果进入下一轮传承"], "domain_lifecycles": [
            {"domain": "career", "root": "专业基础", "seedling": "技能训练", "flower": "方案呈现", "fruit": "项目成果", "continuity": "专业基础经训练转化为方案和成果", "evidence_ids": ["evidence_1", "evidence_2"], "confidence": "to_verify"},
            {"domain": "finance_resources", "root": "资源来源", "seedling": "获取能力", "flower": "收入表现", "fruit": "资产留存", "continuity": "资源来源经能力转化为收入和留存", "evidence_ids": ["evidence_3", "evidence_4"], "confidence": "to_verify"},
            {"domain": "love_partner", "root": "关系经验", "seedling": "信任能力", "flower": "吸引互动", "fruit": "长期关系", "continuity": "关系经验经信任建立进入互动和承诺", "evidence_ids": ["evidence_5", "evidence_6"], "confidence": "to_verify"}
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
        "report_claim_ledger": [
            {"claim_id": f"claim_self_{i}", "domain": report_domains[(i - 1) // 8], "reality_dimension": f"axis_{(i - 1) % 8 + 1}", "claim_family": f"family_{(i - 1) % 4 + 1}", "mechanism_family": f"mechanism_{(i - 1) % 3 + 1}", "claim": f"{domain_labels[report_domains[(i - 1) // 8]]}的第{(i - 1) % 8 + 1}项内部自检判断", "plain_claim": f"你在{domain_labels[report_domains[(i - 1) // 8]]}方面可能呈现第{(i - 1) % 8 + 1}种可核对的独立表现。", "new_information": f"{domain_labels[report_domains[(i - 1) // 8]]}新增信息{(i - 1) % 8 + 1}", "mechanism_chain": ["识别本领域的结构条件", "形成与该领域对应的现实表现"], "evidence_ids": [f"evidence_{(i - 1) % 24 + 1}", f"evidence_{i % 24 + 1}"], "supporting_methods": ["格局调候", "根苗花果"], "allowed_examples": ["可观察行为"], "counterevidence": [], "confidence": "to_verify", "unsupported_extensions": ["不能据此断定唯一现实结果"], "calibration_status": "unverified", "origin": "chart_baseline"}
            for i in range(1, 49)
        ],
        "formation_chains": [
            {"chain_id": f"formation_{i}", "starting_condition": "早期规则较明确", "adaptation_need": "需要减少出错", "learned_response": "先观察再行动", "ability_formed": "能够整理复杂信息", "constraint": "进入新环境较慢", "adult_pattern": "先确认要求再执行", "linked_domains": ["self_growth", "career"], "current_change": "开始增加主动表达", "claim_ids": ["claim_self_1", "claim_self_2"], "confidence": "to_verify"}
            for i in range(1, 4)
        ],
        "portrait_thesis": {"summary": "这是用于检验完整人物主轴、另一面、矛盾和当前变化是否同时存在的自检内容。", "primary_traits": ["先确认条件再行动", "重视专业积累"], "complementary_traits": ["条件明确时也能快速推进"], "internal_tensions": ["稳定准备与主动尝试并存"], "observable_patterns": ["先列步骤", "交付前核对", "在熟悉领域主动表达"], "formation_chain_ids": ["formation_1", "formation_2"], "current_shift": "当前阶段开始增加主动表达和尝试", "evidence_ids": ["evidence_1", "evidence_2", "evidence_3", "evidence_4"], "boundaries": ["不能指定具体职业"]},
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
