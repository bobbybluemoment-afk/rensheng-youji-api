#!/usr/bin/env python3
"""Deterministically locate only the paragraphs that need Chinese editing."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

BANNED = {"换轨", "能量场", "底层逻辑", "现实落点", "核对点", "组织化过劳型", "先扎根后显声"}
MINGLI = {"日主", "身强", "身弱", "格局", "调候", "喜用", "忌神", "大运", "流年", "天干", "地支", "藏干", "根苗花果"}
DEFENSIVE = ("你不是", "并不是说你", "这并不意味着", "不能因此断定")


def sections(draft: dict[str, Any]) -> list[dict[str, Any]]:
    return [draft["life_overview"], *draft["dimensions"], draft["current_question"]]


def digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def reasons_for(text: str) -> list[str]:
    reasons = []
    if any(term in text for term in BANNED): reasons.append("AI黑话或生造表达")
    if any(term in text for term in MINGLI): reasons.append("用户不可见命理术语")
    if any(term in text for term in DEFENSIVE): reasons.append("防御性或否定式开头")
    if "命主" in text or "这个人" in text: reasons.append("未使用第二人称")
    if "您" in text: reasons.append("称呼必须统一为‘你’")
    if re.search(r"[。！？]\s*[。！？]", text): reasons.append("重复标点或空句")
    if any(len(re.findall(r"[\u3400-\u9fff]", sentence)) > 70 for sentence in re.split(r"[。！？]", text)): reasons.append("句子过长")
    return reasons


def semantic_slots(semantic: dict[str, Any]) -> list[tuple[str, str]]:
    slots: list[tuple[str, str]] = []

    def add(path: str, value: Any) -> None:
        if isinstance(value, str):
            slots.append(("semantic." + path, value))

    for index, value in enumerate(semantic.get("summary", {}).get("capabilities_resources") or []):
        add(f"summary.capabilities_resources.{index}", value)
    for key, value in (semantic.get("stage_story") or {}).items():
        add(f"stage_story.{key}", value)
    outlook = semantic.get("yearly_outlook") or {}
    add("yearly_outlook.summary", outlook.get("summary"))
    for index, year in enumerate(outlook.get("years") or []):
        for key in ("theme", "carry_in", "real_world_signal", "seed_for_next"):
            add(f"yearly_outlook.years.{index}.{key}", year.get(key))
    guide = semantic.get("action_guide") or {}
    for index, value in enumerate(guide.get("priority_actions") or []):
        add(f"action_guide.priority_actions.{index}", value)
    add("action_guide.reduce", guide.get("reduce"))
    for index, item in enumerate(guide.get("traditional_preferences") or []):
        add(f"action_guide.traditional_preferences.{index}.advice", item.get("advice"))
    for index, value in enumerate(semantic.get("open_questions") or []):
        add(f"open_questions.{index}", value)
    return slots


def scan(draft: dict[str, Any], semantic: dict[str, Any] | None = None) -> dict[str, Any]:
    issues = []
    for section in sections(draft):
        for index, text in enumerate(section.get("paragraphs") or []):
            reasons = reasons_for(text)
            if reasons:
                issues.append({"slot_id": f"{section['id']}:{index + 1}", "section_id": section["id"], "paragraph_index": index, "reasons": reasons, "text": text})
    for slot_id, text in semantic_slots(semantic or {}):
        reasons = reasons_for(text)
        if reasons:
            issues.append({"slot_id": slot_id, "reasons": reasons, "text": text})
    yearly = (semantic or {}).get("yearly_outlook", {}).get("years") or []
    opening_slots: dict[str, list[tuple[str, str]]] = {}
    for index, year in enumerate(yearly):
        if not isinstance(year, dict):
            continue
        for key in ("carry_in", "real_world_signal", "seed_for_next"):
            value = year.get(key)
            if not isinstance(value, str):
                continue
            opening = "".join(re.findall(r"[\u3400-\u9fff]", value))[:10]
            if len(opening) >= 6:
                opening_slots.setdefault(opening, []).append((f"semantic.yearly_outlook.years.{index}.{key}", value))
    issue_ids = {item["slot_id"] for item in issues}
    for repeated in opening_slots.values():
        if len(repeated) < 4:
            continue
        for slot_id, value in repeated:
            if slot_id not in issue_ids:
                issues.append({"slot_id": slot_id, "reasons": ["逐年文字重复使用同一模板开头"], "text": value})
                issue_ids.add(slot_id)
    return {
        "schema_version": "1.1.0",
        "draft_id": draft["draft_id"],
        "semantic_sha256": digest(semantic) if semantic is not None else None,
        "status": "repair_required" if issues else "pass",
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--draft", type=Path, required=True)
    parser.add_argument("--semantic", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = scan(
            json.loads(args.draft.read_text(encoding="utf-8")),
            json.loads(args.semantic.read_text(encoding="utf-8")) if args.semantic else None,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False)); return 1
    print(json.dumps({"status": result["status"], "issues": len(result["issues"]), "output": str(args.output)}, ensure_ascii=False)); return 0


if __name__ == "__main__": raise SystemExit(main())
