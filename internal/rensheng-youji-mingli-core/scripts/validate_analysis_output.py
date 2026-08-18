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
    "root_seed_flower_fruit_map",
    "natal_portrait",
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
    "reality_candidate_pool",
    "calibration_state",
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

    candidates = data.get("reality_candidate_pool")
    if not isinstance(candidates, list) or not 8 <= len(candidates) <= 15:
        errors.append("reality_candidate_pool 必须包含 8—15 条候选")
    else:
        ids: list[str] = []
        for index, candidate in enumerate(candidates):
            path = f"reality_candidate_pool[{index}]"
            require_keys(candidate, {"candidate_id", "domain", "statement", "source_layers", "confidence", "validation_question", "status"}, path, errors)
            if isinstance(candidate, dict) and isinstance(candidate.get("candidate_id"), str):
                ids.append(candidate["candidate_id"])
        if len(ids) != len(set(ids)):
            errors.append("reality_candidate_pool.candidate_id 不能重复")

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
    candidate = lambda number: {"candidate_id": f"c{number}", "domain": "self-test", "statement": "待验证候选", "source_layers": ["chart"], "confidence": "to_verify", "validation_question": "是否符合？", "status": "unverified"}
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
    data = {
        "analysis_meta": {"analysis_id": "self-test", "request_id": "self-test", "core_version": "0.1.0", "generated_at": "2026-08-18T00:00:00+08:00", "analysis_as_of": "2026-08-18", "target_range": {"start_year": 2026, "end_year": 2026}, "input_completeness": "complete", "status": "complete"},
        "chart_facts": {"day_master": "甲", "pillars": {"year": pillar, "month": pillar, "day": {**pillar, "stem_ten_god": "日主"}, "hour": pillar}, "luck_cycles": [{}], "annual_cycles": [{}]},
        "chart_audit": {"status": "pass", "checks": [], "boundary_dependencies": [], "versions": []},
        "social_context_model": empty_section(),
        "five_elements": None,
        "day_master": empty_section(),
        "stems_branches_roots": {"summary": "", "pillars": {"year": pillar_analysis, "month": pillar_analysis, "day": pillar_analysis, "hour": pillar_analysis}, "findings": []},
        "interaction_network": empty_section(),
        "cross_method_analysis": {"summary": "", "methods": [], "agreements": [], "conflicts": [], "findings": []},
        "root_seed_flower_fruit_map": {"summary": "", "root": empty_section(), "seedling": empty_section(), "flower": empty_section(), "fruit": empty_section(), "continuity": [], "findings": []},
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
        "reality_candidate_pool": [candidate(i) for i in range(1, 9)],
        "calibration_state": {"confirmed": [], "partial": [], "rejected": [], "uncertain": [], "updates": []},
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
