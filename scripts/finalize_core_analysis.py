#!/usr/bin/env python3
"""Deterministically merge a synthesis input and AI semantic output into a full Core."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
CORE_SCRIPTS = ROOT / "internal/rensheng-youji-mingli-core/scripts"
sys.path.insert(0, str(CORE_SCRIPTS))
sys.path.insert(0, str(ROOT / "scripts"))

from _jsonschema_subset import validate_schema_instance  # noqa: E402
from build_report_source_bundle import build as build_report_sources  # noqa: E402
from core_synthesis_contract import (  # noqa: E402
    CORE_VERSION,
    SEMANTIC_SECTIONS,
    SYNTHESIS_INPUT_SCHEMA_VERSION,
    canonical_digest,
)
from validate_analysis_output import SCHEMA_PATH, load_json, validate as validate_core  # noqa: E402


def _chart_facts(source: dict[str, Any]) -> dict[str, Any]:
    chart = source["chart"]
    return {
        "day_master": chart["day_master"],
        "pillars": chart["pillars"],
        "luck_cycles": source["luck_cycles"]["cycles"],
        "annual_cycles": source["annual_cycles"],
    }


def _chart_audit(source: dict[str, Any]) -> dict[str, Any]:
    boundary = source["solar_terms_and_boundaries"]
    flags = [item for item in boundary.get("boundary_flags") or [] if item != "none"]
    chart = source["chart"]
    engine = str(chart.get("calculation_engine", "unknown"))
    version = str(chart.get("calculation_version") or "unspecified")
    return {
        "status": "pass_with_flags" if flags else "pass",
        "checks": [{
            "item": "deterministic_chart_input",
            "status": "flag" if flags else "pass",
            "detail": "确定性四柱、大运、流年和时间边界已由上游提供。",
        }],
        "boundary_dependencies": flags,
        "versions": [{"version_id": version, "description": engine}],
    }


def assemble(synthesis_input: dict[str, Any], semantic: dict[str, Any], compiler_source: dict[str, Any] | None = None) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    source_bundle = compiler_source or synthesis_input
    if synthesis_input.get("schema_version") not in {SYNTHESIS_INPUT_SCHEMA_VERSION, "1.1.0", "1.2.0"}:
        errors.append("synthesis_input.schema_version 必须为1.0.0、1.1.0或1.2.0")
    if synthesis_input.get("core_version") != CORE_VERSION:
        errors.append(f"synthesis_input.core_version 必须为{CORE_VERSION}")
    source = source_bundle.get("analysis_input")
    visible_context = synthesis_input.get("analysis_context", source)
    if not isinstance(source, dict) or synthesis_input.get("analysis_input_sha256") != canonical_digest(source):
        errors.append("analysis_input_sha256 无效，确定性输入可能被改写")
    if visible_context != source:
        errors.append("紧凑综合输入的analysis_context与编译器锁定来源不一致")
    method_packet_digest = canonical_digest({
        "methods": source_bundle.get("independent_method_analyses"),
        "evidence": source_bundle.get("evidence_registry"),
    })
    if synthesis_input.get("method_packets_sha256") != method_packet_digest:
        errors.append("method_packets_sha256 无效，已校验方法包或证据可能被改写")
    if not isinstance(semantic, dict):
        return {}, errors + ["Core语义综合输出必须是JSON对象"]
    missing = sorted(SEMANTIC_SECTIONS - set(semantic))
    extra = sorted(set(semantic) - SEMANTIC_SECTIONS)
    if missing:
        errors.append(f"Core语义综合缺少规定区块：{missing}")
    if extra:
        errors.append(f"Core语义综合包含禁止或未知区块：{extra}")
    if errors:
        return {}, errors
    audit = source_bundle["method_execution_audit"]
    request = source["request"]
    candidates = semantic.get("reality_candidate_pool") or []
    role_by_class = {
        "primary_judgment": "primary",
        "independent_supplement": "supplemental",
        "conditional_judgment": "supplemental",
        "stage_judgment": "supplemental",
        "calibration_pending": "to_verify",
        "weak_candidate": "to_verify",
    }
    for claim in semantic.get("report_claim_ledger") or []:
        if isinstance(claim, dict) and claim.get("claim_class") in role_by_class:
            claim["report_role"] = role_by_class[claim["claim_class"]]
    candidate_ids = [str(item.get("candidate_id")) for item in candidates if isinstance(item, dict)]
    result: dict[str, Any] = {
        "analysis_meta": {
            "analysis_id": "analysis-" + canonical_digest({"input": synthesis_input["analysis_input_sha256"], "methods": source_bundle["independent_method_analyses"]})[:16],
            "request_id": request["request_id"],
            "core_version": CORE_VERSION,
            "generated_at": request["analysis_as_of"] + "T00:00:00+00:00",
            "analysis_as_of": request["analysis_as_of"],
            "target_range": request["target_range"],
            "input_completeness": "complete",
            "status": "complete" if audit["delivery_decision"] == "full" else "pass_with_flags",
        },
        "chart_facts": _chart_facts(source),
        "chart_audit": _chart_audit(source),
        "independent_method_analyses": source_bundle["independent_method_analyses"],
        "method_execution_audit": audit,
        "source_coverage_audit": source_bundle["source_coverage_audit"],
        "evidence_registry": source_bundle["evidence_registry"],
        **semantic,
        "calibration_state": {"confirmed": [], "partial": [], "rejected": [], "uncertain": [], "updates": []},
        "calibration_delta": {
            "baseline_preserved": True,
            "confirmed": [],
            "supported_unselected": [],
            "conditional": [],
            "weakened": [],
            "rejected": [],
            "uncertain": candidate_ids,
            "user_fact_evidence_ids": [],
            "claim_updates": [],
        },
    }
    result["report_source_bundle"] = build_report_sources(result)
    schema = load_json(SCHEMA_PATH)
    errors.extend(validate_schema_instance(result, schema))
    errors.extend(validate_core(result))
    return result, errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("synthesis_input", type=Path)
    parser.add_argument("semantic_output", type=Path)
    parser.add_argument("--compiler-source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        synthesis_input = json.loads(args.synthesis_input.read_text(encoding="utf-8"))
        semantic = json.loads(args.semantic_output.read_text(encoding="utf-8"))
        compiler_source = load_json(args.compiler_source) if args.compiler_source else None
        result, errors = assemble(synthesis_input, semantic, compiler_source)
        if errors:
            print(json.dumps({"status": "validation_error", "errors": errors}, ensure_ascii=False, indent=2))
            return 2
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "ok", "output": str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
