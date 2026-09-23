#!/usr/bin/env python3
"""Create a small, hash-bound repair request containing only named top-level sections."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "internal/rensheng-youji-mingli-core/scripts"))
from core_synthesis_contract import SEMANTIC_SECTIONS, canonical_digest  # noqa: E402
from core_semantic_contract import build_ai_schema  # noqa: E402


METHOD_TARGETS = {
    "technical_conclusions", "reality_hypotheses", "domain_limits", "limitations",
    "failure_reasons", "degradation_effects", "result",
}


TARGET_RE = re.compile(r"^\$?\.?([A-Za-z0-9_]+)(?:\[([0-9]+)\])?")

# Some cross-section semantic audits describe the problem in natural Chinese
# instead of beginning with a JSON path.  Keep their repair ownership
# deterministic so an AI never has to guess or manually widen targets.
CORE_SEMANTIC_ERROR_TARGET_HINTS = (
    ("盲派现实取象", ("blind_school_cross_analysis",)),
    ("候选关系", ("candidate_relation_map",)),
    ("九方法到Core证据保留不足", ("report_claim_ledger",)),
    ("画像审计", ("portrait_balance_audit",)),
)


def _target_parts(target: str) -> tuple[str, int | None]:
    match = TARGET_RE.fullmatch(target)
    if not match:
        raise ValueError(f"返修目标路径无效：{target}")
    return match.group(1), int(match.group(2)) if match.group(2) is not None else None


def _fragment(source: dict[str, Any], target: str) -> Any:
    top, index = _target_parts(target)
    value = source[top]
    if index is None:
        return value
    if not isinstance(value, list) or index >= len(value):
        raise ValueError(f"返修目标不存在：{target}")
    return value[index]


def targets_from_errors(errors: list[str], allowed: set[str]) -> list[str]:
    """Extract the smallest addressable AI-owned sections named by errors."""
    targets: set[str] = set()
    for error in errors:
        for phrase, hinted_targets in CORE_SEMANTIC_ERROR_TARGET_HINTS:
            if phrase in error:
                targets.update(target for target in hinted_targets if target in allowed)
        match = TARGET_RE.match(error)
        if not match:
            continue
        top = match.group(1)
        if top in allowed:
            index = match.group(2)
            targets.add(f"{top}[{index}]" if index is not None else top)
    return sorted(targets)


def build(source: dict[str, Any], stage: str, targets: list[str], errors: list[str]) -> dict[str, Any]:
    allowed = METHOD_TARGETS if stage == "independent_method" else SEMANTIC_SECTIONS
    target_set = set(targets)
    if not targets or len(targets) != len(target_set):
        raise ValueError("返修目标不能为空或重复")
    top_targets = {_target_parts(target)[0] for target in targets}
    invalid = sorted(top_targets - allowed)
    missing = sorted(top_targets - set(source))
    if invalid or missing:
        raise ValueError(f"返修目标无效；非法={invalid}；源文件缺少={missing}")
    request = {
        "schema_version": "1.0.0",
        "stage": stage,
        "source_sha256": canonical_digest(source),
        "allowed_targets": targets,
        "validation_errors": errors,
        "locked_rule": "只返回allowed_targets对应的replacements；不得重写其他已经通过的内容。",
        "fragments": {target: _fragment(source, target) for target in targets},
    }
    if stage == "core_synthesis":
        projected = build_ai_schema(SEMANTIC_SECTIONS, top_targets)
        schemas: dict[str, Any] = {}
        for target in targets:
            top, index = _target_parts(target)
            field_schema = projected["properties"][top]
            schemas[target] = field_schema.get("items", {}) if index is not None else field_schema
        request["target_schema"] = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "target_schemas": schemas,
            "$defs": projected.get("$defs", {}),
        }
        request["schema_rule"] = "每个replacement.value必须符合target_schema.target_schemas中同名目标；数组下标目标只返回该单项，不得返回或重写整个数组。"
    request["repair_request_sha256"] = canonical_digest(request)
    return request


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--stage", choices=["independent_method", "core_synthesis"], required=True)
    parser.add_argument("--targets", help="逗号分隔的顶层字段；core_synthesis建议省略并从--errors自动提取")
    parser.add_argument("--errors", type=Path, help="校验器输出JSON；只读取errors数组")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        source = json.loads(args.source.read_text(encoding="utf-8"))
        errors: list[str] = []
        if args.errors:
            payload = json.loads(args.errors.read_text(encoding="utf-8"))
            errors = [str(item) for item in payload.get("errors") or []]
        if args.targets:
            targets = [item.strip() for item in args.targets.split(",") if item.strip()]
        elif args.errors:
            allowed = METHOD_TARGETS if args.stage == "independent_method" else SEMANTIC_SECTIONS
            targets = targets_from_errors(errors, allowed)
        else:
            raise ValueError("必须提供--targets或可解析的--errors")
        result = build(source, args.stage, targets, errors)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False)); return 1
    print(json.dumps({"status": "ok", "output": str(args.output), "targets": result["allowed_targets"]}, ensure_ascii=False)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
