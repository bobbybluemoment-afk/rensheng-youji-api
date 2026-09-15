#!/usr/bin/env python3
"""Validate the compact AI-authored semantic answer for one method."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from _jsonschema_subset import validate_schema_instance


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from method_structure_contract import expected_check_ids  # noqa: E402


PRIMARY = {
    "pattern_structure", "momentum_configuration", "climate_adjustment",
    "ten_god_dynamics", "root_seed_flower_fruit", "blind_school", "timing_continuity",
}
METHODS = PRIMARY | {"position_relationship", "stem_branch_dynamics"}
DOMAINS = {
    "self_growth", "love_partner", "career", "finance_resources",
    "body_emotion", "family_growth",
}
LOVE_ANCHORS = {
    "ten_god_dynamics", "position_relationship", "stem_branch_dynamics",
    "blind_school", "timing_continuity",
}
ALLOWED_ROOTS = {
    "request", "person", "chart", "solar_terms_and_boundaries", "five_elements",
    "luck_cycles", "annual_cycles", "chart_facts", "chart_audit",
}
SCHEMA = Path(__file__).resolve().parents[1] / "schemas/method-semantic-patch.schema.json"


def validate(patch: Any, method_id: str) -> list[str]:
    if method_id not in METHODS:
        return ["expected_method不是规定方法家族"]
    if not isinstance(patch, dict):
        return ["语义答卷必须是JSON对象"]
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    errors = ["语义答卷Schema：" + item for item in validate_schema_instance(patch, schema)]
    result = patch.get("result")
    structure_checks = patch.get("structure_checks") or []
    conclusions = patch.get("technical_conclusions") or []
    hypotheses = patch.get("reality_hypotheses") or []
    domain_limits = patch.get("domain_limits") or []
    failure_reasons = patch.get("failure_reasons") or []
    degradation_effects = patch.get("degradation_effects") or []

    if result != "complete":
        if structure_checks or conclusions or hypotheses or domain_limits:
            errors.append("未完成答卷不得携带半成品结构检查、结论、候选或领域检查")
        if not failure_reasons or not degradation_effects:
            errors.append("未完成答卷必须说明失败原因和降级影响")
        return errors
    if failure_reasons or degradation_effects:
        errors.append("complete答卷不得携带失败原因或降级影响")
    minimum = 2 if method_id in PRIMARY else 1
    if len(conclusions) < minimum or len(hypotheses) < minimum:
        errors.append(f"{method_id}至少需要{minimum}条技术结论和{minimum}条现实候选")
    if len(conclusions) > 12:
        errors.append(f"{method_id}技术结论最多12条，当前{len(conclusions)}条")
    if len(hypotheses) > 18:
        errors.append(f"{method_id}现实候选总数最多18条，当前{len(hypotheses)}条")

    check_by_id: dict[str, dict[str, Any]] = {}
    for item in structure_checks:
        if not isinstance(item, dict):
            continue
        check_id = str(item.get("check_id", ""))
        if check_id in check_by_id:
            errors.append(f"structure_checks检查项重复：{check_id}")
        check_by_id[check_id] = item
    expected_checks = expected_check_ids(method_id)
    if set(check_by_id) != expected_checks:
        errors.append(
            "本方法结构检查表不完整："
            f"缺少={sorted(expected_checks - set(check_by_id))}；"
            f"多余={sorted(set(check_by_id) - expected_checks)}"
        )

    for index, conclusion in enumerate(conclusions, 1):
        refs = list(conclusion.get("chart_refs") or []) if isinstance(conclusion, dict) else []
        for evidence in conclusion.get("evidence") or [] if isinstance(conclusion, dict) else []:
            refs.extend(evidence.get("chart_refs") or [] if isinstance(evidence, dict) else [])
        if any(not isinstance(ref, str) or ref.split(".", 1)[0] not in ALLOWED_ROOTS for ref in refs):
            errors.append(f"第{index}条技术结论只能引用冻结排盘事实")

    supported_domains: set[str] = set()
    domain_counts: dict[str, int] = {domain: 0 for domain in DOMAINS}
    for index, hypothesis in enumerate(hypotheses, 1):
        if not isinstance(hypothesis, dict):
            continue
        supported_domains.add(str(hypothesis.get("domain")))
        domain = str(hypothesis.get("domain"))
        if domain in domain_counts:
            domain_counts[domain] += 1
        numbers = hypothesis.get("derived_from_conclusion_numbers") or []
        if any(not isinstance(number, int) or not 1 <= number <= len(conclusions) for number in numbers):
            errors.append(f"第{index}条现实候选引用了不存在的技术结论序号")

    referenced_conclusions: set[int] = set()
    hypothesis_covered_by_check: set[int] = set()
    for check_id, item in check_by_id.items():
        importance = item.get("importance")
        numbers = set(item.get("conclusion_numbers") or [])
        domains = set(item.get("projection_domains") or [])
        if any(not isinstance(number, int) or not 1 <= number <= len(conclusions) for number in numbers):
            errors.append(f"structure_checks.{check_id}引用了不存在的技术结论序号")
            continue
        if importance in {"material", "conditional"}:
            if not numbers or not domains:
                errors.append(f"structure_checks.{check_id}为重要或条件结构时必须连接技术结论和现实领域")
                continue
            referenced_conclusions.update(numbers)
            for domain in domains:
                matches = {
                    index
                    for index, hypothesis in enumerate(hypotheses, 1)
                    if hypothesis.get("domain") == domain
                    and numbers & set(hypothesis.get("derived_from_conclusion_numbers") or [])
                }
                if not matches:
                    errors.append(f"structure_checks.{check_id}声明投影到{domain}，但没有对应现实候选")
                hypothesis_covered_by_check.update(matches)
        elif importance == "background" and (numbers or domains):
            errors.append(f"structure_checks.{check_id}为背景结构时不得伪装成已形成结论或现实投影")

    missing_conclusion_checks = sorted(set(range(1, len(conclusions) + 1)) - referenced_conclusions)
    if missing_conclusion_checks:
        errors.append(f"技术结论没有重要结构来源：{missing_conclusion_checks}")
    missing_hypothesis_checks = sorted(set(range(1, len(hypotheses) + 1)) - hypothesis_covered_by_check)
    if missing_hypothesis_checks:
        errors.append(f"现实候选没有结构检查来源：{missing_hypothesis_checks}")

    limit_by_domain: dict[str, dict[str, Any]] = {}
    for item in domain_limits:
        if not isinstance(item, dict):
            continue
        domain = str(item.get("domain"))
        if domain in limit_by_domain:
            errors.append(f"domain_limits领域重复：{domain}")
        limit_by_domain[domain] = item
    if supported_domains & set(limit_by_domain):
        errors.append("已经形成现实候选的领域不得同时进入domain_limits")
    reviewed = supported_domains | set(limit_by_domain)
    if reviewed != DOMAINS:
        errors.append(f"六领域检查不完整：缺少={sorted(DOMAINS - reviewed)}；多余={sorted(reviewed - DOMAINS)}")
    for domain, count in domain_counts.items():
        if count > 5:
            errors.append(f"{domain}现实候选最多5条，当前{count}条")
    love_limit = limit_by_domain.get("love_partner")
    if method_id in LOVE_ANCHORS and love_limit and love_limit.get("status") == "not_applicable":
        errors.append(f"{method_id}必须实际检查love_partner，不得标记not_applicable")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("patch", type=Path)
    parser.add_argument("--expected-method", required=True)
    args = parser.parse_args()
    try:
        patch = json.loads(args.patch.read_text(encoding="utf-8"))
        errors = validate(patch, args.expected_method)
    except (OSError, json.JSONDecodeError) as exc:
        errors = [str(exc)]
    print(json.dumps({"status": "ok" if not errors else "error", "errors": errors}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
