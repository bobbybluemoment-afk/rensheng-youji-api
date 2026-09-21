#!/usr/bin/env python3
"""Build a compact, hash-bound input for calibration wording only."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "internal/rensheng-youji-mingli-core/scripts"))
from core_synthesis_contract import canonical_digest  # noqa: E402


DOMAINS = (
    "self_growth", "love_partner", "career", "finance_resources",
    "body_emotion", "family_growth",
)
KIND_SCORE = {"timed_event": 40, "objective_state": 30, "current_stage": 20, "stable_pattern": 10}


def _years(value: Any) -> list[int]:
    return [int(item) for item in re.findall(r"(?<!\d)(20\d{2})(?!\d)", str(value or ""))]


def _eligible_for_wording(candidate: dict[str, Any], analysis_year: int) -> bool:
    text = " ".join(str(candidate.get(key, "")) for key in ("statement", "alternative_statement"))
    if any(year > analysis_year for year in _years(text)):
        return False
    if candidate.get("candidate_kind") == "timed_event":
        scope_years = _years(candidate.get("time_scope"))
        if scope_years and min(scope_years) > analysis_year:
            return False
    return True


def select_candidates(semantic: dict[str, Any], analysis_year: int, limit: int = 10) -> list[dict[str, Any]]:
    claims = {
        str(item.get("claim_id")): item
        for item in semantic.get("report_claim_ledger") or [] if isinstance(item, dict)
    }
    pool = []
    for candidate in semantic.get("reality_candidate_pool") or []:
        if not isinstance(candidate, dict) or candidate.get("domain") not in DOMAINS:
            continue
        if not _eligible_for_wording(candidate, analysis_year):
            continue
        linked = [claims[item] for item in candidate.get("related_claim_ids") or [] if item in claims]
        if linked and all(item.get("claim_class") == "weak_candidate" for item in linked):
            continue
        item = dict(candidate)
        item["_score"] = KIND_SCORE.get(str(item.get("candidate_kind")), 0)
        pool.append(item)
    pool.sort(key=lambda item: (-item["_score"], str(item.get("candidate_id", ""))))
    selected: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    # First preserve breadth: one candidate from every supported domain.
    for domain in DOMAINS:
        match = next((item for item in pool if item.get("domain") == domain), None)
        if match is not None:
            selected.append(match); counts[domain] += 1
    for item in pool:
        if len(selected) >= limit:
            break
        domain = str(item.get("domain"))
        if item in selected or counts[domain] >= 2:
            continue
        selected.append(item); counts[domain] += 1
    return selected[:limit]


def build(semantic: dict[str, Any], analysis_year: int) -> dict[str, Any]:
    selected = select_candidates(semantic, analysis_year)
    if len(selected) < 5:
        raise ValueError(f"可准备自然语言校准探针的Core候选不足5条：当前{len(selected)}条")
    return {
        "schema_version": "1.0.0",
        "source_sha256": canonical_digest(semantic),
        "analysis_year": analysis_year,
        "rules": [
            "只改写为过去或当前能够观察的一件事，不新增命理判断或现实经历。",
            "A与B各只表达一个现实问题轴；不用建议、解决办法或未来预测。",
            "统一使用你；删除‘你可能会发现’等提示套话。",
            "财富直接谈收入、工资、奖金、存钱、消费、预算或资产；身体情绪直接谈睡眠、疲劳、紧绷、烦躁、注意力、休息或身体感受。",
        ],
        "candidates": [{
            key: item.get(key)
            for key in (
                "candidate_id", "domain", "reality_dimension", "candidate_kind",
                "time_scope", "statement", "alternative_statement", "observable_examples",
            )
        } for item in selected],
        "output_contract": "internal/rensheng-youji-mingli-core/schemas/calibration-probe-patch.schema.json",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--semantic", type=Path, required=True)
    parser.add_argument("--analysis-year", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        semantic = json.loads(args.semantic.read_text(encoding="utf-8"))
        result = build(semantic, args.analysis_year)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False)); return 1
    print(json.dumps({"status": "ok", "output": str(args.output), "candidate_count": len(result["candidates"])}, ensure_ascii=False)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
