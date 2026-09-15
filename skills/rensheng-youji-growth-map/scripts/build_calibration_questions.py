#!/usr/bin/env python3
"""Deterministically select five personal calibration questions from a frozen Core."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from calibration_question_contract import years_in  # noqa: E402
from calibration_selection_contract import DOMAINS, select_candidates  # noqa: E402

DOMAIN_LABELS = {
    "self_growth": "性格与成长", "love_partner": "恋爱与伴侣", "career": "事业发展",
    "finance_resources": "财富与资源", "body_emotion": "身体与情绪", "family_growth": "家庭与成长",
}
TEMPLATE_BY_KIND = {
    "stable_pattern": "pattern_choice", "objective_state": "objective_state",
    "timed_event": "timed_change", "current_stage": "current_stage",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def expected_display(candidate: dict[str, Any], number: int, analysis_year: int) -> dict[str, Any]:
    kind = candidate["candidate_kind"]
    if kind == "timed_event":
        source_scope = candidate.get("answerable_time_scope", candidate.get("time_scope"))
        source_years = years_in(source_scope)
        if source_years:
            start_year = min(source_years)
            prompt = f"从{start_year}年到现在，下面哪种情况更接近你的实际经历？"
            time_scope = f"{start_year}年至{analysis_year}年"
        else:
            prompt, time_scope = "回看已经发生的这段时间，下面哪种变化更接近你的实际经历？", str(source_scope)
    elif kind == "current_stage":
        prompt, time_scope = "就你现在的情况来说，下面哪种描述更接近你？", "当前"
    elif kind == "objective_state":
        prompt, time_scope = "回看过去几年的实际经历，下面哪种情况更接近你？", "过去几年"
    else:
        prompt, time_scope = "遇到类似情况时，你通常更接近下面哪一种？", "长期表现"
    return {
        "number": number, "domain": DOMAIN_LABELS[candidate["domain"]],
        "prompt": prompt, "time_scope": time_scope,
        "choices": [
            {"key": "A", "text": candidate.get("answerable_observation", candidate["statement"])},
            {"key": "B", "text": candidate.get("answerable_alternative", candidate["alternative_statement"])},
            {"key": "C", "text": "两种情况都出现过，通常会随着环境或阶段改变。"},
            {"key": "D", "text": "自己描述（可以补充具体经历或年份）。"},
        ],
    }


def build(analysis: dict[str, Any], focus: str = "") -> dict[str, Any]:
    analysis_id = analysis.get("analysis_meta", {}).get("analysis_id")
    if not analysis_id:
        raise ValueError("冻结Core缺少analysis_id，不能生成可追溯校准题")
    questions = []
    analysis_year = int(str(analysis.get("analysis_meta", {}).get("analysis_as_of", "0000"))[:4])
    for number, candidate in enumerate(select_candidates(analysis, focus), 1):
        candidate_id = candidate["candidate_id"]
        questions.append({
            "display": expected_display(candidate, number, analysis_year),
            "audit": {
                "template_id": TEMPLATE_BY_KIND[candidate["candidate_kind"]], "candidate_kind": candidate["candidate_kind"],
                "candidate_ids": [candidate_id], "related_claim_ids": candidate["related_claim_ids"],
                "source_class": candidate["source_class"], "selection_score": candidate["selection_score"],
                "candidate_effects": {
                    "A": [{"candidate_id": candidate_id, "status": "match"}],
                    "B": [{"candidate_id": candidate_id, "status": "reject"}],
                    "C": [{"candidate_id": candidate_id, "status": "partial"}], "D": [],
                },
            },
        })
    return {
        "schema_version": "3.0.0",
        "template_version": "2.0.0",
        "source": {"analysis_id": analysis_id, "baseline_sha256": digest(analysis)},
        "questions": questions,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="从冻结Core确定性选择并生成五道个性化现实校准题")
    parser.add_argument("--analysis", type=Path, required=True)
    parser.add_argument("--focus", default="")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        output = build(load_json(args.analysis), args.focus)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps({"status": "ok", "output": str(args.output), "questions": 5, "ai_calls": 0}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
