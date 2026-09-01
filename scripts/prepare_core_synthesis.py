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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("analysis_input", type=Path)
    parser.add_argument("--method-packet-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        packet_paths = [args.method_packet_dir / f"{method_id}.json" for method_id in sorted(ALL_METHODS)]
        missing_paths = [str(path) for path in packet_paths if not path.is_file()]
        if missing_paths:
            raise ValueError("缺少规定方法包文件：" + "，".join(missing_paths))
        result = prepare(_load(args.analysis_input), [_load(path) for path in packet_paths])
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "ok", "output": str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
