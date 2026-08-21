#!/usr/bin/env python3
"""校验五条现实校准题，并隔离用户可见文字与内部命理审计。"""

from __future__ import annotations

import argparse
from difflib import SequenceMatcher
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
CHOICE_KEYS = ["A", "B", "C", "D"]
UNCERTAIN_CHOICE = "都不符合／不确定（可补充）"
DOMAINS = {"家庭与教育", "事业与组织", "关系", "财务", "迁移", "身心"}
PREFERRED_LENSES = {
    "root_seed_flower_fruit_map",
    "resource_relationship",
    "cross_method_analysis",
    "luck_cycle_themes",
    "annual_theme_activation",
    "domain_connections",
}
OBSERVABLE_MARKERS = {"先", "再", "会", "做", "查", "问", "说", "选", "拒绝", "记录", "讨论", "比较", "核对", "离开", "搬", "换", "借", "存", "付", "等", "联系", "回避", "争论", "负责", "提出"}


def cjk_count(value: str) -> int:
    return len(re.findall(r"[\u3400-\u9fff]", value))


def validate(data: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["根节点必须是对象"]
    if data.get("schema_version") != "2.0.0":
        errors.append("schema_version 必须为 2.0.0")
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
        prompt = display.get("prompt")
        choices = display.get("choices")
        if not isinstance(number, int):
            errors.append(f"{path}.display.number 必须是整数")
        else:
            numbers.append(number)
        if domain not in DOMAINS:
            errors.append(f"{path}.display.domain 不在允许范围")
        else:
            domains.add(domain)
        visible_parts: list[str] = []
        if not isinstance(prompt, str):
            errors.append(f"{path}.display.prompt 必须是文字")
        else:
            count = cjk_count(prompt)
            if not 8 <= count <= 45:
                errors.append(f"{path}.display.prompt 应为8—45个汉字，当前{count}")
            visible_parts.append(prompt)
        if not isinstance(choices, list) or len(choices) != 4:
            errors.append(f"{path}.display.choices 必须恰好包含A—D四项")
        else:
            keys = [choice.get("key") for choice in choices if isinstance(choice, dict)]
            if keys != CHOICE_KEYS:
                errors.append(f"{path}.display.choices 必须依次使用A、B、C、D")
            abc_texts: list[str] = []
            for choice_index, choice in enumerate(choices):
                choice_path = f"{path}.display.choices[{choice_index}]"
                if not isinstance(choice, dict) or set(choice) != {"key", "text"}:
                    errors.append(f"{choice_path} 必须只包含key和text")
                    continue
                choice_text = choice.get("text")
                if not isinstance(choice_text, str):
                    errors.append(f"{choice_path}.text 必须是文字")
                    continue
                visible_parts.append(choice_text)
                if choice_index < 3:
                    count = cjk_count(choice_text)
                    if not 8 <= count <= 38:
                        errors.append(f"{choice_path}.text 应为8—38个汉字，当前{count}")
                    abc_texts.append(re.sub(r"[，。；、\s]", "", choice_text))
                elif choice_text != UNCERTAIN_CHOICE:
                    errors.append(f"{choice_path}.text 必须为{UNCERTAIN_CHOICE}")
            if len(set(abc_texts)) != len(abc_texts):
                errors.append(f"{path}.display A、B、C不能使用重复选项")
            for choice_index, choice_text in enumerate(abc_texts):
                if not any(marker in choice_text for marker in OBSERVABLE_MARKERS):
                    errors.append(f"{path}.display.choices[{choice_index}] 必须包含可观察动作，不能只写性格标签")
            for left in range(len(abc_texts)):
                for right in range(left + 1, len(abc_texts)):
                    if SequenceMatcher(None, abc_texts[left], abc_texts[right]).ratio() > 0.72:
                        errors.append(f"{path}.display A、B、C区分度不足")
        for visible_text in visible_parts:
            found = sorted(term for term in VISIBLE_BANNED if term in visible_text)
            if found:
                errors.append(f"{path}.display 泄露内部术语：{'、'.join(found)}")
            if re.search(r"\b(?:c\d+|candidate[_-]?\w*)\b", visible_text, re.IGNORECASE):
                errors.append(f"{path}.display 泄露内部候选编号")

        required_audit = {
            "candidate_ids", "choice_meanings", "evidence_lenses", "core_sections", "alternatives",
            "birth_time_dependency", "confidence",
        }
        missing = sorted(required_audit - set(audit))
        if missing:
            errors.append(f"{path}.audit 缺少：{','.join(missing)}")
            continue
        candidate_ids = audit.get("candidate_ids")
        if not isinstance(candidate_ids, list) or len(candidate_ids) != 3 or not all(isinstance(item, str) and re.fullmatch(r"c\d+", item) for item in candidate_ids):
            errors.append(f"{path}.audit.candidate_ids 必须包含三个形如c01的候选编号")
        choice_meanings = audit.get("choice_meanings")
        if not isinstance(choice_meanings, dict) or list(choice_meanings) != CHOICE_KEYS:
            errors.append(f"{path}.audit.choice_meanings 必须依次映射A、B、C、D")
        elif isinstance(candidate_ids, list) and ([choice_meanings.get(key) for key in CHOICE_KEYS[:3]] != candidate_ids or choice_meanings.get("D") != "uncertain"):
            errors.append(f"{path}.audit.choice_meanings 必须把A—C对应candidate_ids，D对应uncertain")
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
        "为了让报告更贴近你的真实经历，请选择每个场景中更接近你的一项。",
        "只需回复题号和字母；最关心的一两题也可以补充一个具体例子或年份。",
        "",
    ]
    for item in data["questions"]:
        display = item["display"]
        lines.extend([
            f"**校准{display['number']}｜{display['domain']}**",
            display["prompt"],
            *[f"{choice['key']}. {choice['text']}" for choice in display["choices"]],
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
