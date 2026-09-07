#!/usr/bin/env python3
"""Keep free-text calibration limited to fact extraction and existing candidates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CORE = ROOT / "internal/rensheng-youji-mingli-core"
sys.path.insert(0, str(CORE / "scripts"))
from _jsonschema_subset import validate_schema_instance  # noqa: E402

SCHEMA = CORE / "schemas/calibration-free-text-patch.schema.json"


def validate(patch: Any, baseline: dict[str, Any], questions: dict[str, Any]) -> list[str]:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    errors = validate_schema_instance(patch, schema)
    if not isinstance(patch, dict):
        return errors
    question_index = {item["display"]["number"]: item for item in questions.get("questions") or []}
    seen: set[int] = set()
    for item in patch.get("responses") or []:
        number = item.get("question_number")
        if number in seen:
            errors.append(f"第{number}题自由回答重复")
        seen.add(number)
        question = question_index.get(number)
        if question is None:
            errors.append(f"自由回答引用不存在的问题：{number}")
            continue
        allowed = set(question.get("audit", {}).get("candidate_ids") or [])
        updates = item.get("candidate_updates") or []
        if {update.get("candidate_id") for update in updates if isinstance(update, dict)} != allowed:
            errors.append(f"第{number}题自由回答必须且只能更新本题绑定候选")
        for update in updates:
            if update.get("candidate_id") not in allowed:
                errors.append(f"第{number}题自由回答试图修改未绑定候选")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("patch", type=Path)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--questions", type=Path, required=True)
    args = parser.parse_args()
    try:
        errors = validate(json.loads(args.patch.read_text(encoding="utf-8")), json.loads(args.baseline.read_text(encoding="utf-8")), json.loads(args.questions.read_text(encoding="utf-8")))
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        errors = [str(exc)]
    print(json.dumps({"status": "ok" if not errors else "error", "errors": errors}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
