#!/usr/bin/env python3
"""Compile prose-only AI output into the traceable production report draft."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

CORE_SCRIPTS = Path(__file__).resolve().parents[2] / "rensheng-youji-mingli-core/scripts"
sys.path.insert(0, str(CORE_SCRIPTS))
from _jsonschema_subset import validate_schema_instance  # noqa: E402

PATCH_SCHEMA = Path(__file__).resolve().parent.parent / "schemas/report-semantic-patch.schema.json"


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def compile_draft(brief: dict[str, Any], pack: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    if pack.get("brief_id") != brief.get("brief_id") or pack.get("brief_sha256") != digest(brief):
        raise ValueError("写作任务包没有绑定当前事实提纲")
    schema_errors = validate_schema_instance(patch, json.loads(PATCH_SCHEMA.read_text(encoding="utf-8")))
    if schema_errors:
        raise ValueError("正文语义补丁Schema无效：" + "；".join(schema_errors))
    if patch.get("schema_version") != "1.0.0" or patch.get("brief_id") != brief.get("brief_id"):
        raise ValueError("正文语义补丁没有绑定当前事实提纲")
    text_by_slot = {item.get("slot_id"): item.get("text") for item in patch.get("paragraphs") or [] if isinstance(item, dict)}
    expected_slots = [item["slot_id"] for item in pack["slots"]]
    if set(text_by_slot) != set(expected_slots) or len(text_by_slot) != len(expected_slots):
        raise ValueError("正文语义补丁必须逐一填写写作任务包中的段落槽位")
    slots_by_section: dict[str, list[dict[str, Any]]] = {}
    for slot in pack["slots"]:
        slots_by_section.setdefault(slot["section_id"], []).append(slot)

    def compile_section(source: dict[str, Any]) -> dict[str, Any]:
        slots = sorted(slots_by_section[source["id"]], key=lambda item: item["paragraph_index"])
        paragraphs = [text_by_slot[item["slot_id"]] for item in slots]
        realizations = []
        mandatory_index = {item["claim_id"]: item["plain_claim"] for item in source.get("mandatory_claims") or []}
        for claim_id, exact in mandatory_index.items():
            matches = [index for index, text in enumerate(paragraphs) if exact in text]
            if len(matches) != 1:
                raise ValueError(f"{source['id']}.{claim_id}必须在一个指定段落中完整出现一次")
            realizations.append({"claim_id": claim_id, "paragraph_index": matches[0], "exact_span": exact})
        emphasis = []
        claim_index = {item["claim_id"]: item for item in source.get("selected_claims") or []}
        for claim_id in source.get("emphasis_claim_ids") or []:
            exact = claim_index[claim_id]["plain_claim"]
            matches = [index for index, text in enumerate(paragraphs) if exact in text]
            if matches:
                emphasis.append({"paragraph_index": matches[0], "text": exact, "claim_ids": [claim_id]})
        result = {
            "id": source["id"], "title": source["title"], "paragraphs": paragraphs,
            "source_claim_ids": list(source.get("claim_ids") or []),
            "paragraph_claim_map": [item["claim_ids"] for item in slots],
            "claim_realization_map": realizations, "emphasis_spans": emphasis,
            "confidence": "高置信" if source.get("delivery_mode", "normal") == "normal" else "中等置信" if source.get("delivery_mode") in {"shortened", "minimal"} else "待验证",
        }
        for key in ("coverage", "domain_specific_claim_ids", "mainline_claim_ids", "mandatory_claim_ids", "domain_mechanisms", "survives_without_mainline", "delivery_mode", "missing_coverage"):
            if key in source:
                result[key] = source[key]
        return result

    life = compile_section(brief["life_overview"])
    dimensions = [compile_section(item) for item in brief["dimensions"]]
    current = compile_section(brief["current_question"])
    return {
        "schema_version": "1.6.0", "draft_id": "draft-" + digest(patch)[:16], "brief_id": brief["brief_id"],
        "life_overview": life, "dimensions": dimensions, "current_question": current,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--brief", type=Path, required=True)
    parser.add_argument("--writing-pack", type=Path, required=True)
    parser.add_argument("--semantic-patch", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        load = lambda path: json.loads(path.read_text(encoding="utf-8"))
        result = compile_draft(load(args.brief), load(args.writing_pack), load(args.semantic_patch))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "ok", "output": str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
