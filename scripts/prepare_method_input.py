#!/usr/bin/env python3
"""Create the topic-isolated Core input that independent methods are allowed to read."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORE_SCRIPTS = ROOT / "internal" / "rensheng-youji-mingli-core" / "scripts"
sys.path.insert(0, str(CORE_SCRIPTS))

from _jsonschema_subset import validate_schema_instance  # noqa: E402
from validate_analysis_input import SCHEMA_PATH, validate  # noqa: E402
from method_input_contract import build_method_input, canonical_digest  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="生成九方法共用的主题隔离输入")
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        source = json.loads(args.input.read_text(encoding="utf-8"))
        result = build_method_input(source)
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        errors = validate_schema_instance(result, schema)
        errors.extend(validate(result))
        if errors:
            print(json.dumps({"status": "error", "errors": errors}, ensure_ascii=False, indent=2))
            return 2
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps({
        "status": "ok",
        "output": str(args.output),
        "method_input_sha256": canonical_digest(result),
        "topic_isolation": "user facts, questions and calibration removed",
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
