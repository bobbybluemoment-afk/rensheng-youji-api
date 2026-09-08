#!/usr/bin/env python3
"""Create a small, hash-bound repair request containing only named top-level sections."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "internal/rensheng-youji-mingli-core/scripts"))
from core_synthesis_contract import SEMANTIC_SECTIONS, canonical_digest  # noqa: E402


METHOD_TARGETS = {
    "technical_conclusions", "reality_hypotheses", "domain_limits", "limitations",
    "failure_reasons", "degradation_effects", "result",
}


def build(source: dict[str, Any], stage: str, targets: list[str], errors: list[str]) -> dict[str, Any]:
    allowed = METHOD_TARGETS if stage == "independent_method" else SEMANTIC_SECTIONS
    target_set = set(targets)
    if not targets or len(targets) != len(target_set):
        raise ValueError("返修目标不能为空或重复")
    invalid = sorted(target_set - allowed)
    missing = sorted(target_set - set(source))
    if invalid or missing:
        raise ValueError(f"返修目标无效；非法={invalid}；源文件缺少={missing}")
    request = {
        "schema_version": "1.0.0",
        "stage": stage,
        "source_sha256": canonical_digest(source),
        "allowed_targets": targets,
        "validation_errors": errors,
        "locked_rule": "只返回allowed_targets对应的replacements；不得重写其他已经通过的内容。",
        "fragments": {target: source[target] for target in targets},
    }
    request["repair_request_sha256"] = canonical_digest(request)
    return request


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--stage", choices=["independent_method", "core_synthesis"], required=True)
    parser.add_argument("--targets", required=True, help="逗号分隔的顶层字段")
    parser.add_argument("--errors", type=Path, help="校验器输出JSON；只读取errors数组")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        source = json.loads(args.source.read_text(encoding="utf-8"))
        errors: list[str] = []
        if args.errors:
            payload = json.loads(args.errors.read_text(encoding="utf-8"))
            errors = [str(item) for item in payload.get("errors") or []]
        result = build(source, args.stage, [item.strip() for item in args.targets.split(",") if item.strip()], errors)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False)); return 1
    print(json.dumps({"status": "ok", "output": str(args.output), "targets": result["allowed_targets"]}, ensure_ascii=False)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
