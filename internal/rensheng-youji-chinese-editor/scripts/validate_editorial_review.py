#!/usr/bin/env python3
"""验证中文编辑不是自我勾选，并检查事实来源未改变。"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

BANNED = {"组织化过劳型", "先扎根后显声", "表达窗口", "能力输出", "可见度", "物质与经营底色", "资源伴随期待", "表达被规训", "花不显", "现实落点", "核对点"}


def digest(paragraphs: list[str]) -> str:
    return hashlib.sha256("\n".join(paragraphs).encode("utf-8")).hexdigest()


def report_sections(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    sections = {"life_overview": report.get("executive_summary", {}).get("life_overview", {})}
    for item in report.get("dimensions", []):
        if isinstance(item, dict):
            sections[f"dimension:{item.get('id')}"] = item
    sections["current_question"] = report.get("current_question_narrative", {})
    return sections


def draft_sections(draft: dict[str, Any]) -> dict[str, dict[str, Any]]:
    sections = {"life_overview": draft.get("life_overview", {})}
    for item in draft.get("dimensions", []):
        if isinstance(item, dict):
            sections[f"dimension:{item.get('id')}"] = item
    sections["current_question"] = draft.get("current_question", {})
    return sections


def validate(review: Any, draft: Any, report: Any) -> list[str]:
    errors: list[str] = []
    if not all(isinstance(item, dict) for item in (review, draft, report)):
        return ["编辑记录、初稿和终稿都必须是对象"]
    if review.get("version") != "2.0.0":
        errors.append("编辑记录版本必须为2.0.0")
    if review.get("draft_id") != draft.get("draft_id") or review.get("final_report_id") != report.get("report_id"):
        errors.append("编辑记录与初稿或终稿来源不一致")
    draft_map, final_map = draft_sections(draft), report_sections(report)
    records = review.get("sections")
    if not isinstance(records, list) or set(item.get("section_id") for item in records if isinstance(item, dict)) != set(draft_map):
        errors.append("编辑记录必须逐项覆盖完整人生主线、六个领域和当前问题")
        records = []
    changed = 0
    for record in records:
        section_id = record.get("section_id")
        before = draft_map.get(section_id, {})
        after = final_map.get(section_id, {})
        before_text = before.get("paragraphs") or []
        after_text = after.get("paragraphs") or []
        if record.get("draft_sha256") != digest(before_text) or record.get("final_sha256") != digest(after_text):
            errors.append(f"{section_id} 的编辑哈希与实际文本不一致")
        if set(before.get("source_claim_ids") or []) != set(after.get("source_claim_ids") or []):
            errors.append(f"{section_id} 编辑前后判断来源发生变化")
        if set(record.get("source_claim_ids") or []) != set(after.get("source_claim_ids") or []):
            errors.append(f"{section_id} 编辑记录中的判断来源与终稿不一致")
        if before_text != after_text:
            changed += 1
        if not isinstance(record.get("changes"), list):
            errors.append(f"{section_id} 缺少具体编辑记录")
    if changed < 3:
        errors.append("独立中文编辑必须对至少三个内容区产生实际修改")
    visible = json.dumps(final_map, ensure_ascii=False)
    found = sorted(term for term in BANNED if term in visible)
    if found:
        errors.append("终稿仍含生硬或生造表达：" + "、".join(found))
    if re.search(r"校准后的现实线索|校准确认|符合.+判断", visible):
        errors.append("终稿不得展示校准过程")
    checks = review.get("checks", {})
    required = {"facts_preserved", "no_new_claims", "natural_chinese", "no_template_repetition", "calibration_hidden"}
    if set(checks) != required or not all(checks.values()):
        errors.append("编辑记录必须完成五项检查，并由实际文本与来源校验支持")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("review", type=Path)
    parser.add_argument("--draft", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        review = json.loads(args.review.read_text(encoding="utf-8"))
        draft = json.loads(args.draft.read_text(encoding="utf-8"))
        report = json.loads(args.report.read_text(encoding="utf-8"))
        errors = validate(review, draft, report)
    except (OSError, json.JSONDecodeError) as exc:
        errors = [str(exc)]
    print(json.dumps({"status": "ok" if not errors else "error", "errors": errors}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
