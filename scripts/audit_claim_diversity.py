#!/usr/bin/env python3
"""Reject claim ledgers that satisfy counts with paraphrased repetition."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from report_source_contract import claim_diversity_gaps, evidence_retention_gaps, mandatory_candidate_bounds  # noqa: E402


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
        if "您" in plain:
            errors.append(f"{claim_id}.plain_claim必须统一使用第二人称‘你’，不得使用‘您’")
        if not re.search(r"[。！？]$", plain.strip()):
            errors.append(f"{claim_id}.plain_claim must be a complete sentence")
        if any(phrase in plain or phrase in str(claim.get("claim", "")) for phrase in FIXTURE_PHRASES):
            errors.append(f"{claim_id} contains production-forbidden self-test wording")
    for domain in DOMAINS:
        items = [item for item in claims if item.get("domain") == domain]
        gaps = claim_diversity_gaps(items)
        if "claim_family:3" in gaps:
            errors.append(f"{domain} with four or more claims must contain at least three claim families")
        if "mechanism_family:2" in gaps:
            errors.append(f"{domain} with four or more claims must contain at least two mechanism families")
        if "reality_dimension:3" in gaps:
            errors.append(f"{domain} with four or more claims must cover at least three reality dimensions")
        if "reality_dimension:2" in gaps:
            errors.append(f"{domain} with two or three claims must cover at least two reality dimensions")
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
    sources = {
        "life_narrative_source": bundle.get("life_narrative_source"),
        "current_stage_source": bundle.get("current_stage_source"),
        **{f"dimensions.{name}": value for name, value in dimensions.items()},
    }
    for source_name, source in sources.items():
        if not isinstance(source, dict):
            continue
        mandatory = source.get("mandatory_candidate_ids")
        claim_ids = source.get("claim_ids") or []
        minimum, maximum = mandatory_candidate_bounds(claim_ids)
        if not isinstance(mandatory, list) or not minimum <= len(mandatory) <= maximum:
            errors.append(
                f"{source_name}.mandatory_candidate_ids must contain {minimum}—{maximum} ranked candidates"
            )
            continue
        if not set(mandatory).issubset(set(source.get("claim_ids") or [])) or any(item not in claim_index for item in mandatory):
            errors.append("mandatory_candidate_ids must be valid source candidates")
    errors.extend("九方法到Core证据保留不足：" + item for item in evidence_retention_gaps(data))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("analysis", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        raw = args.analysis.read_bytes()
        data = json.loads(raw.decode("utf-8"))
        errors = audit(data)
    except (OSError, json.JSONDecodeError) as exc:
        errors = [str(exc)]
        raw = b""
    result = {
        "schema_version": "1.0.0",
        "status": "ok" if not errors else "error",
        "analysis_sha256": hashlib.sha256(raw).hexdigest() if raw else None,
        "errors": errors,
    }
    if args.output and not errors:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
