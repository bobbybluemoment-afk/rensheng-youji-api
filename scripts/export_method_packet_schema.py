#!/usr/bin/env python3
"""Export the canonical standalone method-packet schema from the Core schema."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
CORE_SCHEMA = ROOT / "internal/rensheng-youji-mingli-core/schemas/analysis-output.schema.json"
DEFAULT_OUTPUT = ROOT / "internal/rensheng-youji-mingli-core/schemas/method-packet.schema.json"
DEFINITIONS = {
    "confidence",
    "methodTechnicalConclusion",
    "methodRealityHypothesis",
    "methodDomainAssessment",
    "independentMethodAnalysis",
    "registeredEvidence",
}


def build_schema(core_schema: dict[str, Any]) -> dict[str, Any]:
    definitions = core_schema.get("$defs") or {}
    missing = DEFINITIONS - set(definitions)
    if missing:
        raise ValueError("完整Core Schema缺少方法包定义：" + "、".join(sorted(missing)))
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://rensheng-youji.local/schemas/method-packet.schema.json",
        "title": "人生有迹独立方法包",
        "type": "object",
        "additionalProperties": False,
        "required": ["method_analysis", "evidence_registry"],
        "properties": {
            "method_analysis": {"$ref": "#/$defs/independentMethodAnalysis"},
            "evidence_registry": {
                "type": "array",
                "items": {"$ref": "#/$defs/registeredEvidence"},
            },
        },
        "$defs": {name: definitions[name] for name in sorted(DEFINITIONS)},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        expected = build_schema(json.loads(CORE_SCHEMA.read_text(encoding="utf-8")))
        if args.check:
            actual = json.loads(args.output.read_text(encoding="utf-8"))
            if actual != expected:
                raise ValueError("method-packet.schema.json与完整Core Schema定义不同步")
        else:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(expected, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "ok", "output": str(args.output), "check": args.check}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
