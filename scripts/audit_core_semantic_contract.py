#!/usr/bin/env python3
"""Audit the Core AI working contract against compiler and canonical Schema."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "internal/rensheng-youji-mingli-core/scripts"))

from core_semantic_contract import (  # noqa: E402
    COMPILER_OWNED_FIELDS,
    CORE_SCHEMA_PATH,
    build_ai_schema,
)
from core_synthesis_contract import SEMANTIC_SECTIONS  # noqa: E402
from validate_analysis_output import PREFERRED_CANDIDATE_LENSES  # noqa: E402


def audit(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    canonical = json.loads(CORE_SCHEMA_PATH.read_text(encoding="utf-8"))
    ai_schema = build_ai_schema(SEMANTIC_SECTIONS)
    if set(ai_schema.get("properties") or {}) != SEMANTIC_SECTIONS:
        errors.append("AI工作Schema与SEMANTIC_SECTIONS不一致")
    if set(ai_schema.get("required") or []) != SEMANTIC_SECTIONS:
        errors.append("AI工作Schema必填顶层区块与SEMANTIC_SECTIONS不一致")
    for definition_name, fields in COMPILER_OWNED_FIELDS.items():
        canonical_definition = canonical.get("$defs", {}).get(definition_name)
        ai_definition = ai_schema.get("$defs", {}).get(definition_name)
        if not canonical_definition or not ai_definition:
            errors.append(f"编译器责任定义不存在：{definition_name}")
            continue
        canonical_required = set(canonical_definition.get("required") or [])
        ai_required = set(ai_definition.get("required") or [])
        for field in fields:
            if field not in canonical_required:
                errors.append(f"{definition_name}.{field}不是正式Core必填字段")
            if field in ai_required:
                errors.append(f"{definition_name}.{field}仍被AI工作Schema要求填写")
            if field in (ai_definition.get("properties") or {}):
                errors.append(f"{definition_name}.{field}仍暴露在AI工作Schema中")
    schema_layers = set(
        canonical["$defs"]["realityCandidate"]["properties"]["source_layers"]
        ["items"]["enum"]
    )
    missing_lenses = sorted(PREFERRED_CANDIDATE_LENSES - schema_layers)
    if missing_lenses:
        errors.append(f"主校验器允许但Core Schema拒绝的候选来源层：{missing_lenses}")
    required_files = {
        "scripts/prepare_core_synthesis.py": ("build_ai_schema", "compiler_owned_fields"),
        "scripts/finalize_core_analysis.py": ("compile_bookkeeping", "ai_semantic_view", "require_calibration_feasibility"),
        "scripts/prepare_calibration_probes.py": ("source_sha256", "candidates"),
        "scripts/validate_calibration_probe_patch.py": ("source_sha256", "answerable_observation"),
        "scripts/prepare_semantic_repair.py": ("target_schema", "targets_from_errors"),
        "internal/rensheng-youji-mingli-core/references/core-production-bridge.md": ("target_schema", "确定性编译器"),
        "skills/rensheng-youji-growth-map/SKILL.md": ("compiler_owned_fields", "--errors"),
    }
    for relative, markers in required_files.items():
        path = root / relative
        if not path.is_file():
            errors.append(f"缺少Core契约文件：{relative}")
            continue
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                errors.append(f"{relative}缺少契约标记：{marker}")
    maintained_workflows = {
        "主报告Skill": root / "skills/rensheng-youji-growth-map/SKILL.md",
        "内部Core Skill": root / "internal/rensheng-youji-mingli-core/SKILL.md",
        "Core生产桥": root / "internal/rensheng-youji-mingli-core/references/core-production-bridge.md",
    }
    for label, path in maintained_workflows.items():
        text = path.read_text(encoding="utf-8")
        prepare_pos = text.find("scripts/prepare_calibration_probes.py")
        probe_validator_pos = text.find("scripts/validate_calibration_probe_patch.py", prepare_pos + 1)
        input_pos = text.find("--input", probe_validator_pos + 1)
        patch_pos = text.find("--patch", input_pos + 1)
        post_validator_pos = text.find("scripts/validate_core_synthesis.py", patch_pos + 1)
        probe_option_pos = text.find("--calibration-probe-patch", post_validator_pos + 1)
        finalizer_pos = text.find("scripts/finalize_core_analysis.py", probe_option_pos + 1)
        ordered = {
            "scripts/prepare_calibration_probes.py": prepare_pos,
            "scripts/validate_calibration_probe_patch.py": probe_validator_pos,
            "--input": input_pos,
            "--patch": patch_pos,
            "二次scripts/validate_core_synthesis.py": post_validator_pos,
            "--calibration-probe-patch": probe_option_pos,
            "scripts/finalize_core_analysis.py": finalizer_pos,
        }
        if any(position < 0 for position in ordered.values()):
            missing = [marker for marker, position in ordered.items() if position < 0]
            errors.append(f"{label}缺少正式Core阶段或参数：{missing}")
        finalizer = finalizer_pos
        finalizer_block = text[finalizer:finalizer + 500] if finalizer >= 0 else ""
        for option in ("--compiler-source", "--calibration-probe-patch", "--output"):
            if option not in finalizer_block:
                errors.append(f"{label}的正式Core组装命令缺少{option}")

    finalizer_text = (root / "scripts/finalize_core_analysis.py").read_text(encoding="utf-8")
    validator_text = (root / "scripts/validate_core_synthesis.py").read_text(encoding="utf-8")
    for option in ("--compiler-source", "--calibration-probe-patch"):
        declaration = f'parser.add_argument("{option}", type=Path, required=True)'
        if declaration not in finalizer_text:
            errors.append(f"正式Core组装器必须强制要求{option}")
    if 'parser.add_argument("--compiler-source", type=Path, required=True)' not in validator_text:
        errors.append("Core语义校验器必须强制要求--compiler-source")

    probe_schema = json.loads((root / "internal/rensheng-youji-mingli-core/schemas/calibration-probe-patch.schema.json").read_text(encoding="utf-8"))
    if probe_schema["properties"]["probes"].get("maxItems") != 10:
        errors.append("校准探针Schema必须与准备器共享最多10条的数量契约")

    pipeline = json.loads((root / "internal/pipeline-contract.json").read_text(encoding="utf-8"))
    stages = {item["id"]: item for item in pipeline.get("stages") or [] if isinstance(item, dict) and item.get("id")}
    required_initial_inputs = {
        "core_synthesis_input", "core_compiler_source", "core_semantic_analysis", "calibration_probe_patch",
    }
    if set(stages.get("initial_core", {}).get("inputs") or []) != required_initial_inputs:
        errors.append("initial_core没有严格消费综合输入、编译来源、语义答卷和校准探针补丁")
    if stages.get("baseline_freeze", {}).get("gate") != "CORE_GATE":
        errors.append("CORE_GATE必须在质量审计通过并冻结Baseline后执行")
    if stages.get("calibrated_core", {}).get("gate") != "CALIBRATION_GATE":
        errors.append("CALIBRATION_GATE必须在校准后Core生成后执行")

    gate_text = (root / "scripts/pipeline_gate.py").read_text(encoding="utf-8")
    for artifact in ("calibration-probe-input.json", "calibration-probe-patch.json"):
        if artifact not in gate_text:
            errors.append(f"CORE_GATE检查点没有绑定{artifact}")
    return errors


def main() -> int:
    errors = audit()
    if errors:
        print(json.dumps({"status": "error", "errors": errors}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({"status": "ok", "semantic_sections": len(SEMANTIC_SECTIONS), "compiler_owned_definitions": len(COMPILER_OWNED_FIELDS)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
