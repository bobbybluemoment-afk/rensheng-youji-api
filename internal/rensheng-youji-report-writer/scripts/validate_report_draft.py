#!/usr/bin/env python3
"""校验人物初稿的来源、篇幅和结构。"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

DIMENSIONS = ["self_growth", "love_partner", "career", "finance_resources", "body_emotion", "family_growth"]
REQUIRED_COVERAGE = {"feature", "behavior", "formation", "challenge", "current_change", "response"}
BANNED = {"组织化过劳型", "先扎根后显声", "表达窗口", "能力输出", "可见度", "物质与经营底色", "资源伴随期待", "表达被规训"}


def cjk(value: Any) -> int:
    return len(re.findall(r"[\u3400-\u9fff]", str(value)))


def check_section(section: Any, minimum: int, maximum: int, where: str, errors: list[str]) -> set[str]:
    if not isinstance(section, dict):
        errors.append(f"{where} 必须是对象")
        return set()
    paragraphs = section.get("paragraphs")
    if not isinstance(paragraphs, list) or not 2 <= len(paragraphs) <= 4 or any(not isinstance(item, str) for item in paragraphs):
        errors.append(f"{where}.paragraphs 必须包含2—4个自然段")
    else:
        count = cjk("".join(paragraphs))
        if not minimum <= count <= maximum:
            errors.append(f"{where} 应为{minimum}—{maximum}个汉字，当前{count}")
        for index, paragraph in enumerate(paragraphs):
            sentences = [item for item in re.split(r"[。！？]", paragraph) if cjk(item)]
            if any(cjk(sentence) > 70 for sentence in sentences):
                errors.append(f"{where}.paragraphs[{index}] 存在超过70个汉字的长句")
    claim_ids = section.get("source_claim_ids")
    if not isinstance(claim_ids, list) or len(set(claim_ids)) < 4:
        errors.append(f"{where} 至少引用4个不同判断")
        return set()
    return set(claim_ids)


def validate(data: Any, brief: Any | None = None) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["报告初稿必须是对象"]
    for key in ("schema_version", "draft_id", "brief_id", "life_overview", "dimensions", "current_question"):
        if key not in data:
            errors.append(f"缺少字段：{key}")
    if data.get("schema_version") != "1.0.0":
        errors.append("schema_version 必须为1.0.0")
    used = check_section(data.get("life_overview"), 350, 550, "life_overview", errors)
    dimensions = data.get("dimensions")
    if not isinstance(dimensions, list) or [item.get("id") for item in dimensions if isinstance(item, dict)] != DIMENSIONS:
        errors.append("dimensions 必须按固定顺序完整包含六个领域")
    else:
        for item in dimensions:
            used |= check_section(item, 380, 650, f"dimensions.{item.get('id')}", errors)
            if not REQUIRED_COVERAGE.issubset(set(item.get("coverage") or [])):
                errors.append(f"dimensions.{item.get('id')} 缺少人物描述覆盖项")
    current = data.get("current_question")
    if isinstance(current, dict):
        used |= check_section(current, 280, 600, "current_question", errors)
    else:
        errors.append("current_question 必须是对象")
    visible = json.dumps(data, ensure_ascii=False)
    found = sorted(term for term in BANNED if term in visible)
    if found:
        errors.append("初稿含有生硬或生造表达：" + "、".join(found))
    if "校准后的现实线索" in visible or "校准确认" in visible:
        errors.append("初稿不得展示校准过程")
    if brief is not None and isinstance(brief, dict):
        if data.get("brief_id") != brief.get("brief_id"):
            errors.append("初稿与事实提纲来源不一致")
        allowed: set[str] = set()
        for section in [brief.get("life_overview"), brief.get("current_question"), *(brief.get("dimensions") or [])]:
            if isinstance(section, dict):
                allowed.update(section.get("claim_ids") or [])
        if used - allowed:
            errors.append("初稿使用了事实提纲没有授权的判断")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("draft", type=Path)
    parser.add_argument("--brief", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.draft.read_text(encoding="utf-8"))
        brief = json.loads(args.brief.read_text(encoding="utf-8")) if args.brief else None
        errors = validate(data, brief)
    except (OSError, json.JSONDecodeError) as exc:
        errors = [str(exc)]
    print(json.dumps({"status": "ok" if not errors else "error", "errors": errors}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
