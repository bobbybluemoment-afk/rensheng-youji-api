#!/usr/bin/env python3
"""Deterministically select five personal calibration questions from a frozen Core."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
from itertools import combinations
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from calibration_question_contract import quality_errors, years_in  # noqa: E402

DOMAINS = {"self_growth", "love_partner", "career", "finance_resources", "body_emotion", "family_growth"}
DOMAIN_LABELS = {
    "self_growth": "性格与成长", "love_partner": "恋爱与伴侣", "career": "事业发展",
    "finance_resources": "财富与资源", "body_emotion": "身体与情绪", "family_growth": "家庭与成长",
}
TEMPLATE_BY_KIND = {
    "stable_pattern": "pattern_choice", "objective_state": "objective_state",
    "timed_event": "timed_change", "current_stage": "current_stage",
}
CLASS_SCORE = {
    "calibration_pending": 600, "conditional_judgment": 500,
    "independent_supplement": 400, "stage_judgment": 300,
    "primary_judgment": 200,
}
FOCUS_HINTS = {
    "career": ("事业", "工作", "职业", "升职", "求职"),
    "finance_resources": ("财富", "财务", "收入", "钱"),
    "love_partner": ("恋爱", "感情", "伴侣", "婚姻"),
    "family_growth": ("家庭", "父母", "亲友"),
    "body_emotion": ("身体", "健康", "情绪", "压力"),
    "self_growth": ("性格", "成长", "自己"),
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def focus_domain(focus: str) -> str | None:
    return next((domain for domain, hints in FOCUS_HINTS.items() if any(hint in focus for hint in hints)), None)


def claim_class_for(candidate: dict[str, Any], claims: dict[str, dict[str, Any]]) -> str | None:
    classes = [claims[item].get("claim_class") for item in candidate.get("related_claim_ids") or [] if item in claims]
    classes = [item for item in classes if item in CLASS_SCORE]
    return max(classes, key=lambda item: CLASS_SCORE[item]) if classes else None


def candidate_score(candidate: dict[str, Any], source_class: str, wanted_domain: str | None) -> int:
    score = CLASS_SCORE[source_class]
    score += {"high": 30, "medium": 20, "to_verify": 10}.get(candidate.get("confidence"), 0)
    score += {"timed_event": 25, "objective_state": 20, "current_stage": 12, "stable_pattern": 8}.get(candidate.get("candidate_kind"), 0)
    if candidate.get("domain") == wanted_domain:
        score += 40
    return score


def answerable(candidate: dict[str, Any], analysis_year: int) -> bool:
    """Calibration can only ask about evidence already observable today."""
    if quality_errors(candidate, analysis_year):
        return False
    if candidate.get("candidate_kind") == "timed_event":
        scope = candidate.get("answerable_time_scope", candidate.get("time_scope"))
        window = years_in(scope)
        return (bool(window) and min(window) <= analysis_year) or (not window and any(term in str(scope) for term in ("过去", "当前", "至今")))
    return True


def _valid_set(items: tuple[dict[str, Any], ...]) -> bool:
    counts = Counter(item["domain"] for item in items)
    kinds = [item["candidate_kind"] for item in items]
    axes = [(item.get("domain"), item.get("reality_dimension") or item.get("label")) for item in items]
    return len(counts) >= 4 and max(counts.values(), default=0) <= 2 and "timed_event" in kinds and sum(kind in {"objective_state", "timed_event"} for kind in kinds) >= 2 and len(set(axes)) == 5


def select_candidates(analysis: dict[str, Any], focus: str = "") -> list[dict[str, Any]]:
    claims = {item["claim_id"]: item for item in analysis.get("report_claim_ledger") or [] if isinstance(item, dict)}
    wanted_domain = focus_domain(focus)
    analysis_year = int(str(analysis.get("analysis_meta", {}).get("analysis_as_of", "0000"))[:4])
    strict_semantics = analysis.get("analysis_meta", {}).get("core_version") == "0.16.0"
    eligible = []
    for candidate in analysis.get("reality_candidate_pool") or []:
        if not isinstance(candidate, dict) or candidate.get("domain") not in DOMAINS:
            continue
        source_class = claim_class_for(candidate, claims)
        if source_class is None or source_class == "weak_candidate":
            continue
        if not candidate.get("validation_question") or len(candidate.get("observable_examples") or []) < 2:
            continue
        if strict_semantics:
            candidate_is_answerable = answerable(candidate, analysis_year)
        else:
            candidate_is_answerable = not quality_errors(candidate, analysis_year, strict_semantics=False)
            if candidate.get("candidate_kind") == "timed_event":
                scope = candidate.get("answerable_time_scope", candidate.get("time_scope"))
                window = years_in(scope)
                candidate_is_answerable = candidate_is_answerable and ((bool(window) and min(window) <= analysis_year) or (not window and any(term in str(scope) for term in ("过去", "当前", "至今"))))
        if not candidate_is_answerable:
            continue
        item = dict(candidate)
        item["source_class"] = source_class
        item["selection_score"] = candidate_score(item, source_class, wanted_domain)
        eligible.append(item)
    if len(eligible) < 5:
        raise ValueError("冻结Core中可校准且非弱证据的现实候选不足5条")
    eligible.sort(key=lambda item: (-item["selection_score"], str(item["candidate_id"])))
    # The Core contract caps this pool at 24 items. Enumerating all 5-item
    # combinations is still small, and avoids losing a needed fourth domain or
    # timed event merely because it ranked 19th on individual score.
    valid = [items for items in combinations(eligible, 5) if _valid_set(items)]
    if not valid:
        raise ValueError("无法在不凑题的前提下满足5题、4领域、客观题和时间题覆盖")
    return list(max(valid, key=lambda items: (sum(item["selection_score"] for item in items), tuple(item["candidate_id"] for item in items))))


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
