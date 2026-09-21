#!/usr/bin/env python3
"""Validate the small AI-authored calibration wording patch."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "internal/rensheng-youji-mingli-core/scripts"))
from _jsonschema_subset import validate_schema_instance  # noqa: E402
from core_synthesis_contract import canonical_digest  # noqa: E402
from calibration_question_contract import quality_errors  # noqa: E402


SCHEMA = ROOT / "internal/rensheng-youji-mingli-core/schemas/calibration-probe-patch.schema.json"


def validate(probe_input: dict[str, Any], patch: dict[str, Any]) -> list[str]:
    errors = validate_schema_instance(patch, json.loads(SCHEMA.read_text(encoding="utf-8")))
    if errors:
        return errors
    if patch.get("source_sha256") != probe_input.get("source_sha256"):
        errors.append("校准探针补丁不属于当前Core语义文件")
    source_by_id = {
        str(item.get("candidate_id")): item
        for item in probe_input.get("candidates") or [] if isinstance(item, dict)
    }
    probe_ids = [str(item.get("candidate_id")) for item in patch.get("probes") or []]
    if len(probe_ids) != len(set(probe_ids)):
        errors.append("calibration probes candidate_id不能重复")
    if set(probe_ids) != set(source_by_id):
        errors.append("校准探针必须且只能覆盖准备包中的全部候选")
    analysis_year = int(probe_input.get("analysis_year", 0))
    for index, item in enumerate(patch.get("probes") or []):
        candidate_id = str(item.get("candidate_id"))
        source = source_by_id.get(candidate_id)
        if not source:
            continue
        merged = dict(source)
        merged.update(item)
        for reason in quality_errors(merged, analysis_year):
            errors.append(f"probes[{index}] {candidate_id}：{reason}")
        if "您" in " ".join(str(item.get(key, "")) for key in ("answerable_observation", "answerable_alternative")):
            errors.append(f"probes[{index}] {candidate_id}必须统一使用‘你’")
        if any("你可能会发现" in str(item.get(key, "")) for key in ("answerable_observation", "answerable_alternative")):
            errors.append(f"probes[{index}] {candidate_id}不得保留提示套话‘你可能会发现’")
    return errors


def load_validated(probe_input: dict[str, Any], patch: dict[str, Any]) -> dict[str, dict[str, str]]:
    errors = validate(probe_input, patch)
    if errors:
        raise ValueError("校准探针补丁无效：" + "；".join(errors))
    return {
        str(item["candidate_id"]): {
            "answerable_time_scope": str(item["answerable_time_scope"]),
            "answerable_observation": str(item["answerable_observation"]),
            "answerable_alternative": str(item["answerable_alternative"]),
        }
        for item in patch["probes"]
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--patch", type=Path, required=True)
    args = parser.parse_args()
    try:
        probe_input = json.loads(args.input.read_text(encoding="utf-8"))
        patch = json.loads(args.patch.read_text(encoding="utf-8"))
        errors = validate(probe_input, patch)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        errors = [str(exc)]
    print(json.dumps({"status": "ok" if not errors else "error", "errors": errors}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
