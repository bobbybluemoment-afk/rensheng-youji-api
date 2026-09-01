#!/usr/bin/env python3
"""Create nine method-specific draft packets with immutable fields prefilled."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core_synthesis_contract import ALL_METHODS, PARTIAL_METHODS
from method_input_contract import canonical_digest


ROOT = Path(__file__).resolve().parent.parent
DOMAINS = [
    "self_growth", "love_partner", "career", "finance_resources",
    "body_emotion", "family_growth", "learning", "mobility",
]
GROUPS = {
    "pattern_structure": "pattern_organization",
    "momentum_configuration": "momentum_intention",
    "climate_adjustment": "climate_environment",
    "ten_god_dynamics": "relationship_action",
    "root_seed_flower_fruit": "development_continuity",
    "blind_school": "blind_action_path",
    "timing_continuity": "timing_execution",
    "position_relationship": "position_interface",
    "stem_branch_dynamics": "stem_branch_structure",
}


def draft(method_id: str, method_input_sha256: str) -> dict[str, object]:
    return {
        "_draft_notice": (
            "这是结构草稿，不是已完成方法包。AI只读取method-input.json独立分析，"
            "替换所有__AI_FILL__并删除本字段后，另存到method-packets/<method_id>.json。"
        ),
        "method_analysis": {
            "method_id": method_id,
            "tier": "partial" if method_id in PARTIAL_METHODS else "primary",
            "independence_group": GROUPS[method_id],
            "status": "complete",
            "attempt_count": 1,
            "failure_reasons": [],
            "degradation_effects": [],
            "input_scope": "chart_only_topic_isolated",
            "method_input_sha256": method_input_sha256,
            "input_fact_refs": ["__AI_FILL__"],
            "source_method_ids_read": [],
            "technical_conclusions": [],
            "reality_hypotheses": [],
            "domain_assessments": [
                {
                    "domain": domain,
                    "status": "insufficient_evidence",
                    "hypothesis_ids": [],
                    "reasoning": "__AI_FILL__",
                }
                for domain in DOMAINS
            ],
            "limitations": ["__AI_FILL__"],
        },
        "evidence_registry": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("method_input", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        data = json.loads(args.method_input.read_text(encoding="utf-8"))
        output_dir = args.output_dir.resolve()
        expected_parent = (ROOT / "work/runs").resolve()
        if expected_parent not in output_dir.parents:
            raise ValueError("方法包草稿必须写入仓库work/runs下的本次运行目录")
        output_dir.mkdir(parents=True, exist_ok=True)
        if any(output_dir.iterdir()):
            raise ValueError("方法包草稿目录必须为空，避免复用旧方法包")
        method_hash = canonical_digest(data)
        for method_id in sorted(ALL_METHODS):
            path = output_dir / f"{method_id}.draft.json"
            path.write_text(json.dumps(draft(method_id, method_hash), ensure_ascii=False, indent=2), encoding="utf-8")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({
        "status": "ok",
        "output_dir": str(output_dir),
        "draft_count": len(ALL_METHODS),
        "method_input_sha256": method_hash,
        "schema": "internal/rensheng-youji-mingli-core/schemas/method-packet.schema.json",
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
