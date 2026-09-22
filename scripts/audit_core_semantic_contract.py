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
    growth_skill = (root / "skills/rensheng-youji-growth-map/SKILL.md").read_text(encoding="utf-8")
    probe_command = (
        "scripts/validate_calibration_probe_patch.py \\\n"
        "  --input work/calibration-probe-input.json \\\n"
        "  --patch work/calibration-probe-patch.json"
    )
    if probe_command not in growth_skill:
        errors.append("校准探针校验命令必须使用脚本声明的--input与--patch参数")
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
