#!/usr/bin/env python3
"""Validate one isolated method packet before it can enter Core synthesis."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from _jsonschema_subset import validate_schema_instance


PRIMARY = {
    "pattern_structure", "momentum_configuration", "climate_adjustment",
    "ten_god_dynamics", "root_seed_flower_fruit", "blind_school", "timing_continuity",
}
PARTIAL = {"position_relationship", "stem_branch_dynamics"}
GROUPS = {
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
ALLOWED_ROOTS = {
    "request", "person", "chart", "solar_terms_and_boundaries", "five_elements",
    "luck_cycles", "annual_cycles", "chart_facts", "chart_audit",
}
TERMINAL_FAILURES = {"insufficient_evidence", "blocked_input", "generation_failed"}
HYPOTHESIS_DOMAINS = {
    "self_growth", "love_partner", "career", "finance_resources",
    "body_emotion", "family_growth", "learning", "mobility",
}
REALITY_CONFIRMATIONS = {"unverified", "supported", "confirmed", "contradicted"}
LOVE_PARTNER_ANCHORS = {
    "ten_god_dynamics", "position_relationship", "stem_branch_dynamics",
    "blind_school", "timing_continuity",
}
SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "analysis-output.schema.json"


def _formal_fragment(definition: str) -> dict[str, Any]:
    """Return one formal Core definition with the root refs kept resolvable."""
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    fragment = dict(schema["$defs"][definition])
    fragment["$defs"] = schema["$defs"]
    return fragment


def validate(packet: Any, expected_method: str | None = None) -> list[str]:
    errors: list[str] = []
    if not isinstance(packet, dict):
        return ["方法包必须是JSON对象"]
    if "__AI_FILL__" in json.dumps(packet, ensure_ascii=False):
        errors.append("方法包仍含草稿占位符__AI_FILL__")
    if set(packet) != {"method_analysis", "evidence_registry"}:
        errors.append("方法包只能包含method_analysis和evidence_registry")
    method = packet.get("method_analysis")
    evidence = packet.get("evidence_registry")
    if not isinstance(method, dict) or not isinstance(evidence, list):
        return errors + ["method_analysis必须是对象，evidence_registry必须是数组"]
    for formal_error in validate_schema_instance(
        method, _formal_fragment("independentMethodAnalysis")
    ):
        errors.append("method_analysis不符合正式Core Schema：" + formal_error)
    evidence_schema = _formal_fragment("registeredEvidence")
    for index, item in enumerate(evidence):
        for formal_error in validate_schema_instance(item, evidence_schema):
            errors.append(
                f"evidence_registry[{index}]不符合正式Core Schema：{formal_error}"
            )
    required = {
        "method_id", "tier", "independence_group", "status", "attempt_count",
        "failure_reasons", "degradation_effects", "input_scope", "method_input_sha256", "input_fact_refs",
        "source_method_ids_read", "technical_conclusions", "reality_hypotheses",
        "domain_assessments", "limitations",
    }
    missing = required - set(method)
    if missing:
        errors.append("method_analysis缺少字段：" + ", ".join(sorted(missing)))
    method_id = method.get("method_id")
    if method_id not in GROUPS:
        return errors + ["method_id不是规定方法家族"]
    if expected_method and method_id != expected_method:
        errors.append(f"方法包应为{expected_method}，实际为{method_id}")
    tier = "primary" if method_id in PRIMARY else "partial"
    if method.get("tier") != tier:
        errors.append(f"tier必须为{tier}")
    if method.get("independence_group") != GROUPS[method_id]:
        errors.append(f"independence_group必须为{GROUPS[method_id]}")
    if method.get("source_method_ids_read") != []:
        errors.append("source_method_ids_read必须为空")
    if method.get("input_scope") != "chart_only_topic_isolated":
        errors.append("input_scope必须为chart_only_topic_isolated")
    attempts = method.get("attempt_count")
    if not isinstance(attempts, int) or not 1 <= attempts <= 3:
        errors.append("attempt_count必须为1—3")
    status = method.get("status")
    if status not in {"complete", *TERMINAL_FAILURES}:
        errors.append("status无效")
    if status == "generation_failed" and attempts != 3:
        errors.append("generation_failed必须完成三轮局部修复")
    if status == "complete" and method.get("failure_reasons"):
        errors.append("complete方法不得保留failure_reasons")
    if status != "complete" and not method.get("failure_reasons"):
        errors.append("未完成方法必须说明failure_reasons")
    if status != "complete" and not method.get("degradation_effects"):
        errors.append("未完成方法必须说明degradation_effects")
    if not method.get("limitations"):
        errors.append("limitations至少说明一项方法边界")
    refs = method.get("input_fact_refs") or []
    if status != "blocked_input" and not refs:
        errors.append("除blocked_input外必须引用冻结排盘事实")
    if any(not isinstance(ref, str) or ref.split(".", 1)[0] not in ALLOWED_ROOTS for ref in refs):
        errors.append("input_fact_refs只能引用冻结排盘事实")
    conclusions = method.get("technical_conclusions") or []
    hypotheses = method.get("reality_hypotheses") or []
    assessments = method.get("domain_assessments") or []
    if status != "complete" and (conclusions or hypotheses or evidence or assessments):
        errors.append("未完成方法不得携带半成品结论、候选、领域检查或证据")
        return errors
    minimum = 2 if method_id in PRIMARY else 1
    if status == "complete" and (len(conclusions) < minimum or len(hypotheses) < minimum):
        errors.append(f"完成方法至少需要{minimum}条技术结论和{minimum}条现实候选")
    evidence_by_id: dict[str, dict[str, Any]] = {}
    evidence_required = {
        "evidence_id", "source_layer", "method", "method_id", "independence_group",
        "chart_refs", "observation", "interpretation", "limitations", "confidence",
    }
    for item in evidence:
        if not isinstance(item, dict):
            errors.append("evidence_registry只能包含对象")
            continue
        missing_evidence = evidence_required - set(item)
        if missing_evidence:
            errors.append("evidence_registry条目缺少字段：" + ", ".join(sorted(missing_evidence)))
        evidence_id = item.get("evidence_id")
        if not isinstance(evidence_id, str) or not evidence_id.startswith("evidence_") or evidence_id in evidence_by_id:
            errors.append("evidence_id缺失、格式无效或重复")
            continue
        evidence_by_id[evidence_id] = item
        if item.get("method_id") != method_id or item.get("independence_group") != GROUPS[method_id]:
            errors.append(f"{evidence_id}不属于当前方法")
        if not set(item.get("chart_refs") or []).issubset(set(refs)):
            errors.append(f"{evidence_id}.chart_refs未包含在input_fact_refs")
        if not item.get("limitations"):
            errors.append(f"{evidence_id}.limitations不得为空")
    if status == "complete" and not evidence_by_id:
        errors.append("完成方法必须提供实体证据")
    conclusion_ids: set[str] = set()
    conclusion_required = {
        "conclusion_id", "statement", "mechanism_chain", "chart_refs", "evidence_ids",
        "conditions", "counterconditions", "time_scope", "confidence",
    }
    for item in conclusions:
        if not isinstance(item, dict):
            errors.append("technical_conclusions只能包含对象")
            continue
        missing_conclusion = conclusion_required - set(item)
        if missing_conclusion:
            errors.append("technical_conclusions条目缺少字段：" + ", ".join(sorted(missing_conclusion)))
        conclusion_id = item.get("conclusion_id")
        if not isinstance(conclusion_id, str) or conclusion_id in conclusion_ids:
            errors.append("conclusion_id缺失或重复")
        conclusion_ids.add(str(conclusion_id))
        chart_refs = set(item.get("chart_refs") or [])
        if not chart_refs or not chart_refs.issubset(set(refs)):
            errors.append(f"{conclusion_id}.chart_refs未包含在input_fact_refs")
        evidence_ids = set(item.get("evidence_ids") or [])
        if not evidence_ids or evidence_ids - set(evidence_by_id):
            errors.append(f"{conclusion_id}.evidence_ids缺失或引用无效")
        for evidence_id in evidence_ids & set(evidence_by_id):
            entity = evidence_by_id[evidence_id]
            if entity.get("method_id") != method_id or entity.get("independence_group") != GROUPS[method_id]:
                errors.append(f"{conclusion_id}借用了其他方法证据")
        if len(item.get("mechanism_chain") or []) < 2:
            errors.append(f"{conclusion_id}.mechanism_chain至少两步")
    hypothesis_ids: set[str] = set()
    hypothesis_required = {
        "hypothesis_id", "derived_from_conclusion_ids", "domain", "normalized_direction",
        "statement", "observable_indicators", "conditions", "counterevidence",
        "unsupported_extensions", "added_information", "time_scope", "reality_confirmation",
    }
    for item in hypotheses:
        if not isinstance(item, dict):
            errors.append("reality_hypotheses只能包含对象")
            continue
        missing_hypothesis = hypothesis_required - set(item)
        if missing_hypothesis:
            errors.append("reality_hypotheses条目缺少字段：" + ", ".join(sorted(missing_hypothesis)))
        hypothesis_id = item.get("hypothesis_id")
        if not isinstance(hypothesis_id, str) or hypothesis_id in hypothesis_ids:
            errors.append("hypothesis_id缺失或重复")
        hypothesis_ids.add(str(hypothesis_id))
        if item.get("domain") not in HYPOTHESIS_DOMAINS:
            errors.append(
                f"{hypothesis_id}.domain无效：{item.get('domain')}；"
                f"只允许{sorted(HYPOTHESIS_DOMAINS)}"
            )
        direction = item.get("normalized_direction")
        if not isinstance(direction, str) or len(direction.strip()) < 4:
            errors.append(f"{hypothesis_id}.normalized_direction至少4个字符")
        if item.get("reality_confirmation") not in REALITY_CONFIRMATIONS:
            errors.append(f"{hypothesis_id}.reality_confirmation值无效")
        derived = set(item.get("derived_from_conclusion_ids") or [])
        if not derived or derived - conclusion_ids:
            errors.append(f"{hypothesis_id}只能引用本方法技术结论")
        if len(set(item.get("observable_indicators") or [])) < 2:
            errors.append(f"{hypothesis_id}至少需要两条可观察表现")
        for key in ("conditions", "counterevidence", "unsupported_extensions"):
            if not item.get(key):
                errors.append(f"{hypothesis_id}.{key}不得为空")

    if status == "complete":
        assessment_by_domain: dict[str, dict[str, Any]] = {}
        for item in assessments:
            if not isinstance(item, dict):
                errors.append("domain_assessments只能包含对象")
                continue
            domain = item.get("domain")
            if domain in assessment_by_domain:
                errors.append(f"domain_assessments领域重复：{domain}")
                continue
            assessment_by_domain[str(domain)] = item
        if set(assessment_by_domain) != HYPOTHESIS_DOMAINS:
            errors.append(
                "完成方法必须逐项检查八个现实领域；"
                f"缺少={sorted(HYPOTHESIS_DOMAINS - set(assessment_by_domain))}；"
                f"多余={sorted(set(assessment_by_domain) - HYPOTHESIS_DOMAINS)}"
            )
        hypothesis_ids_by_domain = {
            domain: {
                str(item.get("hypothesis_id")) for item in hypotheses
                if item.get("domain") == domain
            }
            for domain in HYPOTHESIS_DOMAINS
        }
        for domain, assessment in assessment_by_domain.items():
            if domain not in HYPOTHESIS_DOMAINS:
                continue
            assessment_ids = set(assessment.get("hypothesis_ids") or [])
            expected_ids = hypothesis_ids_by_domain[domain]
            assessment_status = assessment.get("status")
            if assessment_status == "supported":
                if not expected_ids or assessment_ids != expected_ids:
                    errors.append(f"domain_assessments.{domain}为supported时必须登记该领域全部候选")
            elif assessment_status in {"insufficient_evidence", "not_applicable"}:
                if expected_ids or assessment_ids:
                    errors.append(f"domain_assessments.{domain}无支持时不得保留候选编号")
            else:
                errors.append(f"domain_assessments.{domain}.status无效")
        love_assessment = assessment_by_domain.get("love_partner")
        if method_id in LOVE_PARTNER_ANCHORS and isinstance(love_assessment, dict):
            if love_assessment.get("status") == "not_applicable":
                errors.append(f"{method_id}是关系锚点方法，必须实际检查love_partner，不得标记not_applicable")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("packet", type=Path)
    parser.add_argument("--expected-method")
    args = parser.parse_args()
    try:
        packet = json.loads(args.packet.read_text(encoding="utf-8"))
        errors = validate(packet, args.expected_method)
    except (OSError, json.JSONDecodeError) as exc:
        errors = [str(exc)]
    print(json.dumps({"status": "ok" if not errors else "error", "errors": errors}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
