#!/usr/bin/env python3
"""Compile fixed choices and optional free-text facts into the narrow calibration delta."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from core_baseline import digest  # noqa: E402
from validate_calibration_free_text import validate as validate_free_text  # noqa: E402


CLAIM_STATUS = {"match": "match", "partial": "conditional", "reject": "weakened", "uncertain": "uncertain"}


def compile_delta(baseline: dict[str, Any], lock: dict[str, Any], questions: dict[str, Any], answers: dict[str, Any], free_text: dict[str, Any] | None = None) -> dict[str, Any]:
    if digest(baseline) != lock.get("baseline_sha256"):
        raise ValueError("Baseline与锁文件不一致")
    if questions.get("source") != {"analysis_id": lock.get("analysis_id"), "baseline_sha256": lock.get("baseline_sha256")}:
        raise ValueError("校准题没有绑定当前Baseline与锁文件")
    question_index = {item["display"]["number"]: item for item in questions.get("questions") or []}
    if sorted(question_index) != [1, 2, 3, 4, 5]:
        raise ValueError("校准题必须恰好包含编号1—5")
    answer_items = answers.get("responses")
    if not isinstance(answer_items, list) or len(answer_items) != 5:
        raise ValueError("必须提供五道校准题回答")
    answer_numbers = [item.get("question_number") for item in answer_items if isinstance(item, dict)]
    if sorted(answer_numbers) != [1, 2, 3, 4, 5]:
        raise ValueError("五道校准回答不得缺失或重复")
    free_by_number: dict[int, dict[str, Any]] = {}
    if free_text:
        errors = validate_free_text(free_text, baseline, questions)
        if errors:
            raise ValueError("自由回答补丁无效：" + "；".join(errors))
        free_by_number = {item["question_number"]: item for item in free_text.get("responses") or []}
    d_numbers = {item.get("question_number") for item in answer_items if isinstance(item, dict) and item.get("choice") == "D"}
    if set(free_by_number) != d_numbers:
        raise ValueError("自由回答语义补丁必须且只能覆盖选择D的问题")
    candidates = {item["candidate_id"]: item for item in baseline.get("reality_candidate_pool") or []}
    claims = {item["claim_id"]: item for item in baseline.get("report_claim_ledger") or []}
    candidate_status: dict[str, str] = {}
    reasons: dict[str, list[str]] = {}
    responses = []
    facts: list[dict[str, Any]] = []
    fact_ids_by_candidate: dict[str, list[str]] = {}
    for answer in answer_items:
        number, choice = answer.get("question_number"), answer.get("choice")
        question = question_index.get(number)
        if question is None or choice not in {"A", "B", "C", "D"}:
            raise ValueError(f"第{number}题回答无效")
        free_item = free_by_number.get(number)
        if choice == "D":
            if free_item is None:
                raise ValueError(f"第{number}题选择D时必须提供自由描述语义补丁")
            if str(answer.get("free_text", "")).strip() != str(free_item.get("user_text", "")).strip():
                raise ValueError(f"第{number}题自由描述补丁与用户原文不一致")
            effects = [{"candidate_id": item["candidate_id"], "status": item["status"]} for item in free_item["candidate_updates"]]
            for item in free_item["candidate_updates"]:
                reasons.setdefault(item["candidate_id"], []).append(item["reason"])
            for fact_number, statement in enumerate(free_item["facts"], 1):
                evidence_id = f"evidence_user_q{number}_{fact_number}"
                facts.append({
                    "evidence_id": evidence_id, "source_layer": "user_fact",
                    "method": "用户校准事实", "method_id": "user_fact", "independence_group": "reality_confirmation",
                    "chart_refs": [], "observation": statement, "interpretation": "该事实只用于确认现实落点，不改变命盘技术结论。",
                    "limitations": ["用户自述仅影响相关候选状态。"], "confidence": "medium",
                })
                for item in free_item["candidate_updates"]:
                    fact_ids_by_candidate.setdefault(item["candidate_id"], []).append(evidence_id)
        else:
            effects = question["audit"]["candidate_effects"][choice]
        for effect in effects:
            candidate_status[effect["candidate_id"]] = effect["status"]
        selected = next(item["text"] for item in question["display"]["choices"] if item["key"] == choice)
        responses.append({
            "question_number": number, "template_id": question["audit"]["template_id"], "domain": question["display"]["domain"],
            "choice": choice, "selected_text": selected, "selected_value": choice.lower(),
            "candidate_updates": effects, "user_note": answer.get("free_text", ""),
        })
    candidate_updates = [{"candidate_id": key, "status": value} for key, value in sorted(candidate_status.items())]
    claim_updates = []
    for candidate_id, status in sorted(candidate_status.items()):
        for claim_id in candidates[candidate_id].get("related_claim_ids") or []:
            if claim_id not in claims or any(item["claim_id"] == claim_id for item in claim_updates):
                continue
            claim_updates.append({
                "claim_id": claim_id, "after_status": CLAIM_STATUS[status],
                "reason": "；".join(reasons.get(candidate_id) or [f"第{next(number for number, q in question_index.items() if candidate_id in q['audit']['candidate_ids'])}题确定性选择更新相关现实候选。"]),
                "user_fact_evidence_ids": fact_ids_by_candidate.get(candidate_id, []),
            })
    return {
        "schema_version": "1.0.0", "analysis_id": lock["analysis_id"], "baseline_sha256": lock["baseline_sha256"],
        "candidate_updates": candidate_updates, "claim_updates": claim_updates,
        "user_fact_evidence": facts, "responses": sorted(responses, key=lambda item: item["question_number"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--answers", type=Path, required=True)
    parser.add_argument("--free-text-patch", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        load = lambda path: json.loads(path.read_text(encoding="utf-8"))
        result = compile_delta(load(args.baseline), load(args.lock), load(args.questions), load(args.answers), load(args.free_text_patch) if args.free_text_patch else None)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    except (OSError, KeyError, StopIteration, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "ok", "output": str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
