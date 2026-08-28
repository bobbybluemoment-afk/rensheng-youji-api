#!/usr/bin/env python3
"""Reject claim ledgers that satisfy counts with paraphrased repetition."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


DOMAINS = {"self_growth", "love_partner", "career", "finance_resources", "body_emotion", "family_growth"}
FIXTURE_PHRASES = {"遇到模糊任务时先整理信息再开始", "先整理再行动", "规则明确的平台"}


def normalize(value: str) -> str:
    return re.sub(r"[^\u3400-\u9fffA-Za-z0-9]", "", value)


def ngrams(value: str, size: int = 3) -> set[str]:
    text = normalize(value)
    if len(text) < size:
        return {text} if text else set()
    return {text[index:index + size] for index in range(len(text) - size + 1)}


def similarity(left: str, right: str) -> float:
    a, b = ngrams(left), ngrams(right)
    return len(a & b) / len(a | b) if a and b else 0.0


def audit(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    claims = [item for item in data.get("report_claim_ledger", []) if isinstance(item, dict)]
    claim_index = {item.get("claim_id"): item for item in claims}
    for claim in claims:
        claim_id = claim.get("claim_id")
        for key in ("claim_family", "mechanism_family", "new_information", "plain_claim"):
            if not isinstance(claim.get(key), str) or len(normalize(claim[key])) < 4:
                errors.append(f"{claim_id}.{key} must contain substantive text")
        plain = str(claim.get("plain_claim", ""))
        if not re.search(r"[。！？]$", plain.strip()):
            errors.append(f"{claim_id}.plain_claim must be a complete sentence")
        if any(phrase in plain or phrase in str(claim.get("claim", "")) for phrase in FIXTURE_PHRASES):
            errors.append(f"{claim_id} contains production-forbidden self-test wording")
    for domain in DOMAINS:
        items = [item for item in claims if item.get("domain") == domain]
        if len(items) < 4:
            errors.append(f"{domain} has fewer than four claims")
            continue
        if len({item.get("claim_family") for item in items}) < 3:
            errors.append(f"{domain} must contain at least three claim families")
        if len({item.get("mechanism_family") for item in items}) < 2:
            errors.append(f"{domain} must contain at least two mechanism families")
        if len({item.get("reality_dimension") for item in items}) < 3:
            errors.append(f"{domain} must cover at least three reality dimensions")
        information = [normalize(str(item.get("new_information", ""))) for item in items]
        if len(information) != len(set(information)):
            errors.append(f"{domain} repeats new_information labels")
    for index, left in enumerate(claims):
        for right in claims[index + 1:]:
            if left.get("claim_id") == right.get("claim_id"):
                continue
            score = similarity(str(left.get("plain_claim", "")), str(right.get("plain_claim", "")))
            if score >= 0.72:
                errors.append(f"Semantically repetitive plain claims: {left.get('claim_id')} / {right.get('claim_id')} ({score:.2f})")
    bundle = data.get("report_source_bundle", {})
    dimensions = bundle.get("dimensions", {}) if isinstance(bundle, dict) else {}
    sources = [bundle.get("life_narrative_source"), bundle.get("current_stage_source"), *dimensions.values()]
    for source in sources:
        if not isinstance(source, dict):
            continue
        mandatory = source.get("mandatory_claim_ids")
        if not isinstance(mandatory, list) or not 1 <= len(mandatory) <= 2:
            errors.append("Each report source must lock one or two mandatory claims")
            continue
        if not set(mandatory).issubset(set(source.get("claim_ids") or [])) or any(item not in claim_index for item in mandatory):
            errors.append("mandatory_claim_ids must be valid selected claims")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("analysis", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.analysis.read_text(encoding="utf-8"))
        errors = audit(data)
    except (OSError, json.JSONDecodeError) as exc:
        errors = [str(exc)]
    print(json.dumps({"status": "ok" if not errors else "error", "errors": errors}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
