#!/usr/bin/env python3
"""校验五条现实校准题，并隔离用户可见文字与内部命理审计。"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


VISIBLE_BANNED = {
    "日主", "身强", "身弱", "印旺", "比肩", "劫财", "食神", "伤官",
    "正印", "偏印", "正财", "偏财", "正官", "七杀", "格局", "喜用",
    "忌神", "天干", "地支", "藏干", "大运", "流年", "刑冲合害",
    "根苗花果", "盘面", "证据", "置信", "候选编号", "替代解释",
}
OPTIONS = ["很符合", "部分符合", "不符合", "不确定／不了解"]
DOMAINS = {"家庭与教育", "事业与组织", "关系", "财务", "迁移", "身心"}
PREFERRED_LENSES = {
    "root_seed_flower_fruit_map",
    "resource_relationship",
    "cross_method_analysis",
    "luck_cycle_themes",
    "annual_theme_activation",
    "domain_connections",
}


def cjk_count(value: str) -> int:
    return len(re.findall(r"[\u3400-\u9fff]", value))


def validate(data: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["根节点必须是对象"]
    if data.get("schema_version") != "1.0.0":
        errors.append("schema_version 必须为 1.0.0")
    questions = data.get("questions")
    if not isinstance(questions, list) or len(questions) != 5:
        return errors + ["questions 必须恰好包含五条"]

    domains: set[str] = set()
    numbers: list[int] = []
    for index, question in enumerate(questions):
        path = f"questions[{index}]"
        if not isinstance(question, dict):
            errors.append(f"{path} 必须是对象")
            continue
        display = question.get("display")
        audit = question.get("audit")
        if not isinstance(display, dict):
            errors.append(f"{path}.display 必须是对象")
            continue
        if not isinstance(audit, dict):
            errors.append(f"{path}.audit 必须是对象")
            continue

        number = display.get("number")
        domain = display.get("domain")
        statement = display.get("statement")
        options = display.get("options")
        if not isinstance(number, int):
            errors.append(f"{path}.display.number 必须是整数")
        else:
            numbers.append(number)
        if domain not in DOMAINS:
            errors.append(f"{path}.display.domain 不在允许范围")
        else:
            domains.add(domain)
        if not isinstance(statement, str):
            errors.append(f"{path}.display.statement 必须是文字")
        else:
            count = cjk_count(statement)
            if not 35 <= count <= 100:
                errors.append(f"{path}.display.statement 应为35—100个汉字，当前{count}")
            found = sorted(term for term in VISIBLE_BANNED if term in statement)
            if found:
                errors.append(f"{path}.display.statement 泄露内部术语：{'、'.join(found)}")
            if re.search(r"\b(?:c\d+|candidate[_-]?\w*)\b", statement, re.IGNORECASE):
                errors.append(f"{path}.display.statement 泄露内部候选编号")
        if options != OPTIONS:
            errors.append(f"{path}.display.options 必须使用固定四选项")

        required_audit = {
            "candidate_id", "evidence_lenses", "core_sections", "alternatives",
            "birth_time_dependency", "confidence",
        }
        missing = sorted(required_audit - set(audit))
        if missing:
            errors.append(f"{path}.audit 缺少：{','.join(missing)}")
            continue
        candidate_id = audit.get("candidate_id")
        if not isinstance(candidate_id, str) or not re.fullmatch(r"c\d+", candidate_id):
            errors.append(f"{path}.audit.candidate_id 必须形如 c01")
        lenses = audit.get("evidence_lenses")
        if not isinstance(lenses, list) or len(set(lenses)) < 2:
            errors.append(f"{path}.audit.evidence_lenses 至少包含两个独立视角")
        elif not (set(lenses) & PREFERRED_LENSES):
            errors.append(f"{path}.audit.evidence_lenses 必须包含根苗花果、资源、交叉方法或时运视角")
        if audit.get("birth_time_dependency") not in {"none", "partial", "high"}:
            errors.append(f"{path}.audit.birth_time_dependency 值无效")
        if audit.get("confidence") not in {"high", "medium", "to_verify"}:
            errors.append(f"{path}.audit.confidence 值无效")

    if numbers != [1, 2, 3, 4, 5]:
        errors.append("五条题目的 number 必须依次为1—5")
    if len(domains) < 3:
        errors.append("五条题目至少覆盖三个生活领域")
    return errors


def render_visible(data: dict[str, Any]) -> str:
    """只输出 display；audit 永远不进入用户可见文本。"""
    lines = [
        "为了让报告更贴近你的真实经历，请按直觉回答下面五条。",
        "只需回复题号和选项，也可以补充一两句事实或年份。",
        "",
    ]
    for item in data["questions"]:
        display = item["display"]
        lines.extend([
            f"**判断{display['number']}｜{display['domain']}**",
            display["statement"],
            "A. 很符合　B. 部分符合　C. 不符合　D. 不确定／不了解",
            "",
        ])
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="校验并生成用户可见的五条现实校准题")
    parser.add_argument("input", type=Path)
    parser.add_argument("--visible-out", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
        errors = validate(data)
        if errors:
            print(json.dumps({"status": "validation_error", "errors": errors}, ensure_ascii=False, indent=2))
            return 3
        if args.visible_out:
            args.visible_out.parent.mkdir(parents=True, exist_ok=True)
            args.visible_out.write_text(render_visible(data), encoding="utf-8")
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps({"status": "ok", "questions": 5, "visible_output": str(args.visible_out) if args.visible_out else None}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
