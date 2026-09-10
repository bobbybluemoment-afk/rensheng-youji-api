#!/usr/bin/env python3
"""Collect nine validated method packets into one immutable synthesis input."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
CORE_SCRIPTS = ROOT / "internal/rensheng-youji-mingli-core/scripts"
sys.path.insert(0, str(CORE_SCRIPTS))

from core_synthesis_contract import (  # noqa: E402
    ALL_METHODS,
    CORE_VERSION,
    SEMANTIC_SECTIONS,
    SYNTHESIS_INPUT_SCHEMA_VERSION,
    build_method_audit,
    build_source_coverage_audit,
    canonical_digest,
)
from _jsonschema_subset import validate_schema_instance  # noqa: E402
from validate_analysis_input import SCHEMA_PATH as INPUT_SCHEMA_PATH, validate as validate_analysis_input  # noqa: E402
from validate_method_packet import validate as validate_method_packet  # noqa: E402
from method_input_contract import build_core_synthesis_input, build_method_input  # noqa: E402


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def prepare(analysis_input: dict[str, Any], packets: list[dict[str, Any]]) -> dict[str, Any]:
    input_schema = _load(INPUT_SCHEMA_PATH)
    input_errors = validate_schema_instance(analysis_input, input_schema)
    input_errors.extend(validate_analysis_input(analysis_input))
    if input_errors:
        raise ValueError("analysis-input校验失败：" + "；".join(input_errors))
    methods: dict[str, dict[str, Any]] = {}
    evidence: dict[str, dict[str, Any]] = {}
    expected_method_input_sha256 = canonical_digest(build_method_input(analysis_input))
    synthesis_analysis_input = build_core_synthesis_input(analysis_input)
    for packet in packets:
        method = packet.get("method_analysis") if isinstance(packet, dict) else None
        method_id = method.get("method_id") if isinstance(method, dict) else None
        packet_errors = validate_method_packet(packet, method_id if isinstance(method_id, str) else None)
        if packet_errors:
            raise ValueError(f"方法包{method_id or '<unknown>'}校验失败：" + "；".join(packet_errors))
        if method.get("method_input_sha256") != expected_method_input_sha256:
            raise ValueError(
                f"方法包{method_id or '<unknown>'}.method_input_sha256与本次主题隔离输入不一致"
            )
        if method_id in methods:
            raise ValueError(f"方法包重复：{method_id}")
        methods[str(method_id)] = method
        for item in packet.get("evidence_registry") or []:
            evidence_id = str(item["evidence_id"])
            if evidence_id in evidence:
                raise ValueError(f"跨方法证据编号重复：{evidence_id}")
            evidence[evidence_id] = item
    if set(methods) != ALL_METHODS:
        missing = sorted(ALL_METHODS - set(methods))
        extra = sorted(set(methods) - ALL_METHODS)
        raise ValueError(f"必须提供9个规定方法包；缺少={missing}；多余={extra}")
    ordered_methods = [methods[method_id] for method_id in sorted(ALL_METHODS)]
    ordered_evidence = [evidence[evidence_id] for evidence_id in sorted(evidence)]
    conclusion_ids_seen: set[str] = set()
    hypothesis_ids_seen: set[str] = set()
    for method in ordered_methods:
        for conclusion in method.get("technical_conclusions") or []:
            conclusion_id = str(conclusion.get("conclusion_id"))
            if conclusion_id in conclusion_ids_seen:
                raise ValueError(f"跨方法技术结论编号重复：{conclusion_id}")
            conclusion_ids_seen.add(conclusion_id)
        for hypothesis in method.get("reality_hypotheses") or []:
            hypothesis_id = str(hypothesis.get("hypothesis_id"))
            if hypothesis_id in hypothesis_ids_seen:
                raise ValueError(f"跨方法现实候选编号重复：{hypothesis_id}")
            hypothesis_ids_seen.add(hypothesis_id)
    source_coverage = build_source_coverage_audit(ordered_methods)
    return {
        "schema_version": SYNTHESIS_INPUT_SCHEMA_VERSION,
        "core_version": CORE_VERSION,
        "analysis_input_sha256": canonical_digest(synthesis_analysis_input),
        "method_input_sha256": expected_method_input_sha256,
        "analysis_input": synthesis_analysis_input,
        "independent_method_analyses": ordered_methods,
        "evidence_registry": ordered_evidence,
        "method_packets_sha256": canonical_digest({
            "methods": ordered_methods,
            "evidence": ordered_evidence,
        }),
        "method_execution_audit": build_method_audit(ordered_methods),
        "source_coverage_audit": source_coverage,
        "semantic_output_contract": {
            "required_sections": sorted(SEMANTIC_SECTIONS),
            "forbidden_rule": "不得重写排盘事实、方法包、方法审计、实体证据、校准初始状态或报告来源映射。",
            "source_gap_rule": "uncovered_report_domains不得补造候选、报告判断或现实事实；必须保留为证据缺口并让对应章节降级。",
            "consensus_rule": "same_direction按同一领域中的实质语义归并，不要求成员normalized_direction字符串完全相同；必须保留成员候选、方法家族与归并理由。",
            "focus_isolation_rule": "完整人物Core形成前不得读取用户关注主题；analysis_input中的questions与current_concerns已确定性清空。",
            "repair_limit": 3,
        },
    }


def compact_view(source: dict[str, Any]) -> dict[str, Any]:
    """Return the only synthesis view that the AI is allowed to read."""
    technical_index = []
    judgment_matrix = {domain: [] for domain in sorted({
        "self_growth", "love_partner", "career", "finance_resources",
        "body_emotion", "family_growth",
    })}
    method_roles = []
    method_boundaries: dict[str, list[str]] = {}
    for method in source["independent_method_analyses"]:
        method_id = method["method_id"]
        conclusion_evidence = {
            conclusion["conclusion_id"]: conclusion["evidence_ids"]
            for conclusion in method.get("technical_conclusions") or []
        }
        method_roles.append({"method_id": method_id, "tier": method["tier"], "status": method["status"]})
        method_boundaries[method_id] = list(method.get("limitations") or [])
        for conclusion in method.get("technical_conclusions") or []:
            technical_index.append({
                "conclusion_id": conclusion["conclusion_id"],
                "statement": conclusion["statement"],
                "mechanism_chain": conclusion["mechanism_chain"],
                "evidence_ids": conclusion["evidence_ids"],
            })
        for hypothesis in method.get("reality_hypotheses") or []:
            evidence_ids = sorted({
                evidence_id
                for conclusion_id in hypothesis["derived_from_conclusion_ids"]
                for evidence_id in conclusion_evidence.get(conclusion_id, [])
            })
            judgment_matrix[hypothesis["domain"]].append({
                "hypothesis_id": hypothesis["hypothesis_id"],
                "method_id": method_id,
                "derived_from_conclusion_ids": hypothesis["derived_from_conclusion_ids"],
                "evidence_ids": evidence_ids,
                "normalized_direction": hypothesis["normalized_direction"],
                "statement": hypothesis["statement"],
                "observable_indicators": hypothesis["observable_indicators"],
                "conditions": hypothesis["conditions"],
                "counterevidence": hypothesis["counterevidence"],
                "unsupported_extensions": hypothesis["unsupported_extensions"],
                "time_scope": hypothesis["time_scope"],
            })
        unsupported = [
                {
                    "domain": item["domain"],
                    "status": item["status"],
                    "reasoning": item["reasoning"],
                }
                for item in method.get("domain_assessments") or []
                if item.get("status") != "supported"
        ]
        if unsupported:
            method_boundaries[method_id].extend(
                f"{item['domain']}：{item['reasoning']}" for item in unsupported
            )
    evidence_index = [{
        "evidence_id": item["evidence_id"],
        "method_id": item["method_id"],
        "independence_group": item["independence_group"],
        "source_layer": item["source_layer"],
        "confidence": item["confidence"],
    } for item in source["evidence_registry"]]
    return {
        "schema_version": "1.2.0",
        "core_version": source["core_version"],
        "analysis_input_sha256": source["analysis_input_sha256"],
        "method_input_sha256": source["method_input_sha256"],
        "method_packets_sha256": source["method_packets_sha256"],
        "analysis_context": source["analysis_input"],
        "method_roles": method_roles,
        "technical_index": technical_index,
        "judgment_matrix": judgment_matrix,
        "method_boundaries": method_boundaries,
        "evidence_index": evidence_index,
        "method_execution_audit": source["method_execution_audit"],
        "source_coverage_audit": source["source_coverage_audit"],
        "semantic_output_contract": source["semantic_output_contract"] | {
            "input_view_rule": "默认只按六领域判断矩阵综合；完整方法包留在core-compiler-source.json中供确定性编译和审计，不得要求AI重复搬运。",
            "claim_class_rule": "每条报告判断只标记六类claim_class之一；report_role由编译器填写。",
            "calibration_probe_rule": "现实候选的validation_question、正向表现、替代解释和时间范围必须足以让程序生成个性化校准题。",
            "evidence_retention_rule": "不按领域硬凑条数；但同一领域已有至少三个方法、四条以上且方向不同的候选时，一条判断不能代替多个现实信息轴，请至少拆开被证据支持的不同方向。",
            "user_address_rule": "plain_claim、现实候选陈述、可观察例子与validation_question统一使用第二人称‘你’，不得使用‘您’。",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("analysis_input", type=Path)
    parser.add_argument("--method-packet-dir", type=Path, required=True)
    parser.add_argument("--method-gate", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--compiler-source", type=Path, help="完整方法包与证据，仅供确定性Core编译器读取")
    args = parser.parse_args()
    try:
        packet_paths = [args.method_packet_dir / f"{method_id}.json" for method_id in sorted(ALL_METHODS)]
        missing_paths = [str(path) for path in packet_paths if not path.is_file()]
        if missing_paths:
            raise ValueError("缺少规定方法包文件：" + "，".join(missing_paths))
        packets = [_load(path) for path in packet_paths]
        if args.method_gate:
            gate = _load(args.method_gate)
            if gate.get("status") != "pass" or gate.get("packet_count") != 9:
                raise ValueError("METHOD GATE未通过或方法包数量无效")
            expected_hashes = gate.get("packet_sha256_by_method") or {}
            actual_hashes = {
                str(packet["method_analysis"]["method_id"]): canonical_digest(packet)
                for packet in packets
            }
            if expected_hashes != actual_hashes:
                raise ValueError("METHOD GATE与当前九个方法包哈希不一致")
        compiler_source = prepare(_load(args.analysis_input), packets)
        result = compact_view(compiler_source)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        compiler_path = args.compiler_source or args.output.with_name("core-compiler-source.json")
        compiler_path.write_text(json.dumps(compiler_source, ensure_ascii=False, indent=2), encoding="utf-8")
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "ok", "output": str(args.output), "compiler_source": str(compiler_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
