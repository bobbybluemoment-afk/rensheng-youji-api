#!/usr/bin/env python3
"""校验模板化现实校准题，并隔离用户可见文字与内部命理审计。"""

from __future__ import annotations

import argparse
from collections import Counter
import json
import re
from pathlib import Path
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = SKILL_ROOT / "references" / "calibration-question-templates.json"
VISIBLE_BANNED = {
    "日主", "身强", "身弱", "印旺", "比肩", "劫财", "食神", "伤官",
    "正印", "偏印", "正财", "偏财", "正官", "七杀", "格局", "喜用",
    "忌神", "天干", "地支", "藏干", "大运", "流年", "刑冲合害",
    "根苗花果", "盘面", "证据", "置信", "候选编号", "替代解释",
}
CHOICE_KEYS = ["A", "B", "C", "D"]
ABC_KEYS = CHOICE_KEYS[:3]
UNCERTAIN_CHOICE = "都不符合／不确定（可补充）"
DOMAINS = {"家庭与教育", "事业与组织", "关系", "财务", "迁移", "身心"}
PREFERRED_LENSES = {
    "root_seed_flower_fruit_map", "resource_relationship", "cross_method_analysis",
    "luck_cycle_themes", "annual_theme_activation", "domain_connections",
}
EFFECT_STATUS = {"match", "partial", "reject"}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_templates() -> dict[str, dict[str, Any]]:
    data = load_json(TEMPLATE_PATH)
    if data.get("schema_version") != "1.0.0" or not isinstance(data.get("templates"), list):
        raise ValueError("校准题模板文件版本或结构无效")
    templates = {item["id"]: item for item in data["templates"]}
    if len(templates) != len(data["templates"]):
        raise ValueError("校准题模板ID不能重复")
    return templates


def candidate_index(analysis: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(analysis, dict) or not isinstance(analysis.get("reality_candidate_pool"), list):
        raise ValueError("analysis 必须包含 reality_candidate_pool")
    result: dict[str, dict[str, Any]] = {}
    for item in analysis["reality_candidate_pool"]:
        if isinstance(item, dict) and isinstance(item.get("candidate_id"), str):
            result[item["candidate_id"]] = item
    return result


def expected_display(template: dict[str, Any], number: int) -> dict[str, Any]:
    return {
        "number": number,
        "domain": template["domain"],
        "prompt": template["prompt"],
        "choices": [
            *[{"key": item["key"], "text": item["text"]} for item in template["choices"]],
            {"key": "D", "text": UNCERTAIN_CHOICE},
        ],
    }


def validate(data: Any, analysis: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["根节点必须是对象"]
    if data.get("schema_version") != "2.1.0":
        errors.append("schema_version 必须为 2.1.0")
    try:
        templates = load_templates()
        candidates = candidate_index(analysis)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return errors + [str(exc)]
    questions = data.get("questions")
    if not isinstance(questions, list) or len(questions) != 5:
        return errors + ["questions 必须恰好包含五条"]

    domains: set[str] = set()
    domain_counts: Counter[str] = Counter()
    numbers: list[int] = []
    template_ids: list[str] = []
    evidence_modes: list[str] = []
    for index, question in enumerate(questions):
        path = f"questions[{index}]"
        if not isinstance(question, dict):
            errors.append(f"{path} 必须是对象")
            continue
        display, audit = question.get("display"), question.get("audit")
        if not isinstance(display, dict) or not isinstance(audit, dict):
            errors.append(f"{path}.display 和 audit 必须是对象")
            continue
        template_id = audit.get("template_id")
        template = templates.get(template_id)
        if template is None:
            errors.append(f"{path}.audit.template_id 不在固定题型库中")
            continue
        template_ids.append(template_id)
        evidence_modes.append(template["evidence_mode"])

        number = display.get("number")
        if isinstance(number, int):
            numbers.append(number)
        else:
            errors.append(f"{path}.display.number 必须是整数")
            continue
        if display != expected_display(template, number):
            errors.append(f"{path}.display 必须由固定题型 {template_id} 原样生成，禁止模型自行改写题干或选项")
        domain = display.get("domain")
        if domain not in DOMAINS:
            errors.append(f"{path}.display.domain 不在允许范围")
        else:
            domains.add(domain)
            domain_counts[domain] += 1
        visible = json.dumps(display, ensure_ascii=False)
        found = sorted(term for term in VISIBLE_BANNED if term in visible)
        if found:
            errors.append(f"{path}.display 泄露内部术语：{'、'.join(found)}")
        if re.search(r"\b(?:c\d+|candidate[_-]?\w*)\b", visible, re.IGNORECASE):
            errors.append(f"{path}.display 泄露内部候选编号")

        fixed_fields = {
            "comparison_axis": template["comparison_axis"],
            "time_window": template["time_window"],
            "selection_rule": template["selection_rule"],
            "answer_type": template["answer_type"],
            "evidence_mode": template["evidence_mode"],
            "calibration_targets": template["calibration_targets"],
        }
        for key, expected_value in fixed_fields.items():
            if audit.get(key) != expected_value:
                errors.append(f"{path}.audit.{key} 必须与固定题型一致")
        expected_meanings = {item["key"]: item["value_code"] for item in template["choices"]} | {"D": "uncertain"}
        if audit.get("choice_meanings") != expected_meanings:
            errors.append(f"{path}.audit.choice_meanings 必须使用固定题型的互斥值编码")

        effects = audit.get("candidate_effects")
        used_ids: list[str] = []
        signatures: list[tuple[tuple[str, str], ...]] = []
        if not isinstance(effects, dict) or list(effects) != ABC_KEYS:
            errors.append(f"{path}.audit.candidate_effects 必须依次包含A、B、C")
        else:
            for key in ABC_KEYS:
                items = effects[key]
                signature: list[tuple[str, str]] = []
                if not isinstance(items, list) or not 1 <= len(items) <= 3:
                    errors.append(f"{path}.audit.candidate_effects.{key} 必须包含1—3条候选影响")
                    continue
                for effect_index, effect in enumerate(items):
                    effect_path = f"{path}.audit.candidate_effects.{key}[{effect_index}]"
                    if not isinstance(effect, dict) or set(effect) != {"candidate_id", "status"}:
                        errors.append(f"{effect_path} 必须只包含candidate_id和status")
                        continue
                    candidate_id, status = effect["candidate_id"], effect["status"]
                    if status not in EFFECT_STATUS:
                        errors.append(f"{effect_path}.status 必须为match/partial/reject")
                    candidate = candidates.get(candidate_id)
                    if candidate is None:
                        errors.append(f"{effect_path}.candidate_id 不存在于Core候选池")
                    elif candidate.get("domain") not in set(template["candidate_domains"]):
                        errors.append(f"{effect_path} 候选领域与题型 {template_id} 不一致")
                    used_ids.append(candidate_id)
                    signature.append((candidate_id, status))
                signatures.append(tuple(sorted(signature)))
            if len(signatures) == 3 and len(set(signatures)) != 3:
                errors.append(f"{path}.audit A、B、C对命理候选产生的校准结果必须不同")
        expected_ids = list(dict.fromkeys(used_ids))
        if audit.get("candidate_ids") != expected_ids:
            errors.append(f"{path}.audit.candidate_ids 必须按首次出现顺序汇总candidate_effects")
        if template["evidence_mode"] == "timed_event":
            linked = [candidates.get(item) for item in expected_ids]
            if not any(item and item.get("candidate_kind") == "timed_event" for item in linked):
                errors.append(f"{path} 带时间窗口的题型必须绑定至少一个 timed_event Core候选")

        lenses = audit.get("evidence_lenses")
        if not isinstance(lenses, list) or len(set(lenses)) < 2:
            errors.append(f"{path}.audit.evidence_lenses 至少包含两个独立视角")
        elif not (set(lenses) & PREFERRED_LENSES):
            errors.append(f"{path}.audit.evidence_lenses 必须包含根苗花果、资源、交叉方法或时运视角")
        core_sections = audit.get("core_sections")
        if not isinstance(core_sections, list) or len(set(core_sections)) < 2:
            errors.append(f"{path}.audit.core_sections 至少包含两个Core来源")
        if not isinstance(audit.get("alternatives"), list) or not audit["alternatives"]:
            errors.append(f"{path}.audit.alternatives 至少保留一个替代解释")
        if audit.get("birth_time_dependency") not in {"none", "partial", "high"}:
            errors.append(f"{path}.audit.birth_time_dependency 值无效")
        if audit.get("confidence") not in {"high", "medium", "to_verify"}:
            errors.append(f"{path}.audit.confidence 值无效")

    if numbers != [1, 2, 3, 4, 5]:
        errors.append("五条题目的 number 必须依次为1—5")
    if len(template_ids) != len(set(template_ids)):
        errors.append("五道校准题不得重复使用同一个固定题型")
    if len(domains) < 4:
        errors.append("五条题目至少覆盖四个生活领域")
    for domain, count in domain_counts.items():
        if count > 2:
            errors.append(f"同一生活领域最多两题：{domain} 当前{count}题")
    if "timed_event" not in evidence_modes:
        errors.append("五道题至少包含一道已发生事件的时间窗口题，用于校准大运流年的现实执行")
    if sum(mode in {"objective_state", "timed_event"} for mode in evidence_modes) < 2:
        errors.append("五道题至少包含两道客观状态或已发生事件题，不能全部询问性格偏好")
    return errors


def render_visible(data: dict[str, Any]) -> str:
    lines = [
        "为了让报告更贴近你的真实经历，请按题目限定的时间和场景选择最接近的一项。",
        "A、B、C只比较同一件事；如果两项都发生过，请按题目中的“最先、最多或主要”规则选择。",
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
    parser = argparse.ArgumentParser(description="校验并生成模板化的五条现实校准题")
    parser.add_argument("input", type=Path)
    parser.add_argument("--analysis", type=Path, required=True, help="已校验的Core analysis-output-initial.json")
    parser.add_argument("--visible-out", type=Path)
    args = parser.parse_args()
    try:
        data, analysis = load_json(args.input), load_json(args.analysis)
        errors = validate(data, analysis)
        if errors:
            print(json.dumps({"status": "validation_error", "errors": errors}, ensure_ascii=False, indent=2))
            return 3
        if args.visible_out:
            args.visible_out.parent.mkdir(parents=True, exist_ok=True)
            args.visible_out.write_text(render_visible(data), encoding="utf-8")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps({"status": "ok", "questions": 5, "visible_output": str(args.visible_out) if args.visible_out else None}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
