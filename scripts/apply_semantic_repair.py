#!/usr/bin/env python3
"""Apply a hash-bound semantic repair without permitting unrelated rewrites."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "internal/rensheng-youji-mingli-core/scripts"))
from _jsonschema_subset import validate_schema_instance  # noqa: E402
from core_synthesis_contract import canonical_digest  # noqa: E402
from prepare_semantic_repair import _target_parts  # noqa: E402

SCHEMA = ROOT / "internal/rensheng-youji-mingli-core/schemas/semantic-repair-patch.schema.json"


def _validate_replacement_values(request: dict[str, Any], replacements: list[dict[str, Any]]) -> None:
    target_contract = request.get("target_schema")
    if request.get("stage") != "core_synthesis":
        return
    if not isinstance(target_contract, dict):
        raise ValueError("Core返修请求缺少target_schema")
    target_schemas = target_contract.get("target_schemas") or {}
    definitions = target_contract.get("$defs") or {}
    errors: list[str] = []
    for item in replacements:
        target = item["target"]
        target_schema = target_schemas.get(target)
        if not isinstance(target_schema, dict):
            errors.append(f"{target}缺少目标Schema")
            continue
        schema = {
            "$schema": target_contract.get("$schema", "https://json-schema.org/draft/2020-12/schema"),
            **target_schema,
            "$defs": definitions,
        }
        for error in validate_schema_instance(item["value"], schema):
            errors.append(f"{target}: {error}")
    if errors:
        raise ValueError("返修补丁不符合目标Schema：" + "；".join(errors))


def apply(source: dict[str, Any], request: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    errors = validate_schema_instance(patch, json.loads(SCHEMA.read_text(encoding="utf-8")))
    if errors:
        raise ValueError("返修补丁Schema无效：" + "；".join(errors))
    expected_request = copy.deepcopy(request)
    receipt = expected_request.pop("repair_request_sha256", None)
    if receipt != canonical_digest(expected_request):
        raise ValueError("返修请求哈希无效")
    if patch["repair_request_sha256"] != receipt:
        raise ValueError("返修补丁不属于本次请求")
    if patch["source_sha256"] != request.get("source_sha256") or canonical_digest(source) != request.get("source_sha256"):
        raise ValueError("返修源文件已经变化")
    if patch["stage"] != request.get("stage"):
        raise ValueError("返修阶段不一致")
    replacements = patch["replacements"]
    targets = [item["target"] for item in replacements]
    if len(targets) != len(set(targets)) or set(targets) != set(request.get("allowed_targets") or []):
        raise ValueError("返修补丁必须且只能覆盖请求点名的全部字段")
    _validate_replacement_values(request, replacements)
    result = copy.deepcopy(source)
    for item in replacements:
        top, index = _target_parts(item["target"])
        if index is None:
            result[top] = item["value"]
        else:
            values = result.get(top)
            if not isinstance(values, list) or index >= len(values):
                raise ValueError(f"返修目标不存在：{item['target']}")
            values[index] = item["value"]
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--patch", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        source = json.loads(args.source.read_text(encoding="utf-8"))
        request = json.loads(args.request.read_text(encoding="utf-8"))
        patch = json.loads(args.patch.read_text(encoding="utf-8"))
        result = apply(source, request, patch)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False)); return 1
    print(json.dumps({"status": "ok", "output": str(args.output), "repaired_targets": request["allowed_targets"]}, ensure_ascii=False)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
