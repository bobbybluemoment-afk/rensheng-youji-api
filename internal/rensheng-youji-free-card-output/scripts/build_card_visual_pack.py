#!/usr/bin/env python3
"""Build a compact baseline-only input for the card visual-signal AI task."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def build(baseline: dict[str, Any]) -> dict[str, Any]:
    meta = baseline["analysis_meta"]
    return {
        "schema_version": "1.0.0",
        "analysis_id": meta["analysis_id"],
        "baseline_sha256": digest(baseline),
        "center_year": int(meta["analysis_as_of"][:4]),
        "evidence_mode": "birth_only",
        "rules": {
            "output": "只输出visual-signals.schema.json规定的字段。",
            "source": "人生K线、事业、财富和关系机会只使用本包中的校准前Core材料。",
            "boundary": "不得使用用户校准事实，不得把候选职业、收入或关系当成已发生事实。",
        },
        "timing_context": {
            "chart_facts": baseline.get("chart_facts"),
            "life_stages": baseline.get("life_stages"),
            "luck_cycle_themes": baseline.get("luck_cycle_themes"),
            "annual_theme_activation": baseline.get("annual_theme_activation"),
            "turning_points": baseline.get("turning_points"),
            "domain_connections": baseline.get("domain_connections"),
            "relationship_system": baseline.get("relationship_system"),
            "resource_relationship": baseline.get("resource_relationship"),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
        result = build(baseline)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False)); return 1
    print(json.dumps({"status": "ok", "output": str(args.output)}, ensure_ascii=False)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
