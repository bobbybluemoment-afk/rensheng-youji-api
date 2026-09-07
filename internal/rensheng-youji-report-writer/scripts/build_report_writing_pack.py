#!/usr/bin/env python3
"""Build paragraph slots so the writer AI only writes prose, not traceability metadata."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


PARAGRAPHS = {"normal": 3, "shortened": 2, "minimal": 1, "evidence_gap": 1}


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def section_slots(section: dict[str, Any]) -> list[dict[str, Any]]:
    mode = section.get("delivery_mode", "normal")
    count = PARAGRAPHS[mode]
    ids = list(section.get("claim_ids") or [])
    mandatory = list(section.get("mandatory_claim_ids") or [])
    ordered = mandatory + [item for item in ids if item not in mandatory]
    buckets = [[] for _ in range(count)]
    for index, claim_id in enumerate(ordered):
        buckets[index % count].append(claim_id)
    claim_index = {item["claim_id"]: item for item in section.get("selected_claims") or []}
    return [{
        "slot_id": f"{section['id']}:{index + 1}", "section_id": section["id"], "paragraph_index": index,
        "delivery_mode": mode, "claim_ids": bucket,
        "claims": [claim_index[item] for item in bucket if item in claim_index],
        "must_include_exact": [claim_index[item]["plain_claim"] for item in mandatory if item in bucket and item in claim_index],
    } for index, bucket in enumerate(buckets)]


def build(brief: dict[str, Any], analysis: dict[str, Any] | None = None) -> dict[str, Any]:
    sections = [brief["life_overview"], *brief["dimensions"], brief["current_question"]]
    slots = [slot for section in sections for slot in section_slots(section)]
    return {
        "schema_version": "1.0.0", "brief_id": brief["brief_id"], "brief_sha256": digest(brief),
        "rules": {
            "task": "只为每个slot_id写一个自然中文段落，不输出来源映射。",
            "voice": "统一使用第二人称你，先肯定表达，再写条件和例子。",
            "boundaries": "不得添加未给出的经历、命理术语、内部编号或绝对事件保证。",
        },
        "slots": slots,
        "supplemental_tasks": {
            "summary": ["capabilities_resources"],
            "stage_story": ["previous_foundation", "recent_development", "present_task", "next_direction", "long_range"],
            "yearly_outlook": "根据冻结Core的20年连续年度材料逐年写现实信号，不写绝对吉凶。",
            "action_guide": "写三条优先行动、一个减少项和两条传统偏好建议。",
            "open_questions": "只保留仍值得用户继续观察的问题。",
        },
        "core_context": {
            "portrait_thesis": (analysis or {}).get("portrait_thesis"),
            "life_stages": (analysis or {}).get("life_stages"),
            "turning_points": (analysis or {}).get("turning_points"),
            "annual_theme_activation": (analysis or {}).get("annual_theme_activation"),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--brief", type=Path, required=True)
    parser.add_argument("--analysis", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = build(json.loads(args.brief.read_text(encoding="utf-8")), json.loads(args.analysis.read_text(encoding="utf-8")) if args.analysis else None)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "ok", "output": str(args.output), "slots": len(result["slots"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
