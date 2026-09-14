#!/usr/bin/env python3
"""Deterministically locate only the paragraphs that need Chinese editing."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

BANNED = {
    "换轨", "能量场", "底层逻辑", "现实落点", "核对点", "组织化过劳型", "先扎根后显声",
    "赋能", "抓手", "价值闭环", "价值沉淀", "成果悬置", "评价结算", "重新归档",
    "长期承接", "价值留存",
}
MINGLI = {"日主", "身强", "身弱", "格局", "调候", "喜用", "忌神", "大运", "流年", "天干", "地支", "藏干", "根苗花果"}
ABSTRACT_WATCH = {"成果", "责任", "边界", "归属", "流程", "标准", "评价", "路径", "稳定", "长期", "资源", "承接", "沉淀", "定型", "映射"}
DEFENSIVE_PATTERNS = (
    r"你不是", r"并不是说你", r"这并不意味着", r"不能因此断定",
    r"不是没有[^。！？]{0,24}而是", r"真正[^。！？]{0,20}不是[^。！？]{0,30}而是",
    r"不只是[^。！？]{0,30}(?:而是|更是|还在于)", r"解决办法不是[^。！？]{0,30}而是",
    r"优势不只在于", r"与其[^。！？]{0,30}(?:不如|更应该)",
)
DANGLING_ENDINGS = ("与此同时", "因为", "但", "但是", "而", "并且", "以及", "另一面是", "例如", "比如")


def sections(draft: dict[str, Any]) -> list[dict[str, Any]]:
    return [draft["life_overview"], *draft["dimensions"], draft["current_question"]]


def digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def reasons_for(text: str) -> list[str]:
    reasons = []
    if any(term in text for term in BANNED): reasons.append("AI黑话或生造表达")
    if any(term in text for term in MINGLI): reasons.append("用户不可见命理术语")
    if any(re.search(pattern, text) for pattern in DEFENSIVE_PATTERNS): reasons.append("高频防御性或先否定后解释句式")
    if "命主" in text or "这个人" in text: reasons.append("未使用第二人称")
    if "您" in text: reasons.append("称呼必须统一为‘你’")
    if re.search(r"[。！？]\s*[。！？]", text): reasons.append("重复标点或空句")
    if any(len(re.findall(r"[\u3400-\u9fff]", sentence)) > 70 for sentence in re.split(r"[。！？]", text)): reasons.append("句子过长")
    for sentence in [item.strip() for item in re.split(r"[。！？]", text) if item.strip()]:
        cjk = len(re.findall(r"[\u3400-\u9fff]", sentence))
        abstract_hits = sum(sentence.count(term) for term in ABSTRACT_WATCH)
        action_hits = len(re.findall(r"理解|整理|形成|推动|建立|确认|承担|转化|实现|获得|处理|安排|判断|说明|提高|减少", sentence))
        if cjk > 45 and (abstract_hits >= 3 or action_hits >= 3):
            reasons.append("一句话塞入过多动作或抽象概念")
            break
    abstract_total = sum(text.count(term) for term in ABSTRACT_WATCH)
    abstract_kinds = sum(term in text for term in ABSTRACT_WATCH)
    if abstract_total >= 7 and abstract_kinds >= 4:
        reasons.append("抽象名词密度过高，需要翻译成现实动作或感受")
    if text.rstrip("。！？；， ").endswith(DANGLING_ENDINGS):
        reasons.append("句子以连接语结束，意思没有说完整")
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
    domain_terms = {
        "love_partner": ("喜欢", "靠近", "回应", "承诺", "失望", "依赖", "争执", "陪伴", "安心", "关系"),
        "finance_resources": ("工资", "奖金", "存钱", "消费", "价格", "预算", "风险", "收入", "钱", "积蓄"),
        "body_emotion": ("累", "紧绷", "睡眠", "睡不着", "烦躁", "注意力", "休息", "身体", "情绪", "脑子"),
        "family_growth": ("父母", "家人", "家庭", "期待", "支持", "求助", "独立", "照顾", "亲友"),
    }
    existing_slots = {item["slot_id"] for item in issues}
    for section in sections(draft):
        section_id = str(section.get("id", ""))
        # Legacy/unit fixtures may contain placeholder sections without bound
        # claims. Domain-language QA is meaningful only for production prose.
        if section_id not in domain_terms or not section.get("source_claim_ids"):
            continue
        text_value = "".join(section.get("paragraphs") or [])
        if not any(term in text_value for term in domain_terms[section_id]):
            slot_id = f"{section_id}:1"
            if slot_id not in existing_slots:
                issues.append({"slot_id": slot_id, "section_id": section_id, "paragraph_index": 0, "reasons": ["本领域没有使用能够让用户认出生活场景的语言"], "text": (section.get("paragraphs") or [""])[0]})
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
