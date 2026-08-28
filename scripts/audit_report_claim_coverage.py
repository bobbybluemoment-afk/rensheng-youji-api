#!/usr/bin/env python3
"""Verify that locked Core claims appear verbatim in draft and final report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def sections(value: dict[str, Any], kind: str) -> dict[str, dict[str, Any]]:
    if kind == "brief":
        result = {"life_overview": value.get("life_overview", {}), "current_question": value.get("current_question", {})}
    elif kind == "draft":
        result = {"life_overview": value.get("life_overview", {}), "current_question": value.get("current_question", {})}
    else:
        result = {
            "life_overview": value.get("executive_summary", {}).get("life_overview", {}),
            "current_question": value.get("current_question_narrative", {}),
        }
    for item in value.get("dimensions", []):
        if isinstance(item, dict):
            result[f"dimension:{item.get('id')}"] = item
    return result


def audit(analysis: dict[str, Any], brief: dict[str, Any], draft: dict[str, Any], report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    ledger = {item.get("claim_id"): item for item in analysis.get("report_claim_ledger", []) if isinstance(item, dict)}
    maps = {name: sections(value, name) for name, value in (("brief", brief), ("draft", draft), ("report", report))}
    if set(maps["brief"]) != set(maps["draft"]) or set(maps["brief"]) != set(maps["report"]):
        return ["Brief, draft, and report section sets differ"]
    usage: dict[str, int] = {}
    for section_id, brief_section in maps["brief"].items():
        mandatory = brief_section.get("mandatory_claim_ids") or []
        expected = {claim_id: ledger.get(claim_id, {}).get("plain_claim") for claim_id in mandatory}
        if any(not value for value in expected.values()):
            errors.append(f"{section_id} has invalid mandatory claims")
            continue
        for kind in ("draft", "report"):
            section = maps[kind][section_id]
            paragraphs = section.get("paragraphs") or []
            realizations = section.get("claim_realization_map")
            if not isinstance(realizations, list) or {item.get("claim_id") for item in realizations if isinstance(item, dict)} != set(mandatory):
                errors.append(f"{kind}.{section_id}.claim_realization_map must cover every mandatory claim exactly once")
                continue
            for item in realizations:
                if not isinstance(item, dict) or set(item) != {"claim_id", "paragraph_index", "exact_span"}:
                    errors.append(f"{kind}.{section_id} has an invalid realization record")
                    continue
                claim_id, paragraph_index, exact_span = item["claim_id"], item["paragraph_index"], item["exact_span"]
                if exact_span != expected.get(claim_id):
                    errors.append(f"{kind}.{section_id}.{claim_id} changed the locked Core wording")
                if not isinstance(paragraph_index, int) or not 0 <= paragraph_index < len(paragraphs) or exact_span not in paragraphs[paragraph_index]:
                    errors.append(f"{kind}.{section_id}.{claim_id} is not present in the declared paragraph")
                if kind == "report":
                    usage[claim_id] = usage.get(claim_id, 0) + 1
        if maps["draft"][section_id].get("claim_realization_map") != maps["report"][section_id].get("claim_realization_map"):
            errors.append(f"{section_id} editorial pass changed the locked realization map")
    overused = sorted(claim_id for claim_id, count in usage.items() if count > 2)
    if overused:
        errors.append("Mandatory claims appear in more than two sections: " + ", ".join(overused))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--analysis", type=Path, required=True)
    parser.add_argument("--brief", type=Path, required=True)
    parser.add_argument("--draft", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        values = [json.loads(path.read_text(encoding="utf-8")) for path in (args.analysis, args.brief, args.draft, args.report)]
        errors = audit(*values)
    except (OSError, json.JSONDecodeError) as exc:
        errors = [str(exc)]
    print(json.dumps({"status": "ok" if not errors else "error", "errors": errors}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
