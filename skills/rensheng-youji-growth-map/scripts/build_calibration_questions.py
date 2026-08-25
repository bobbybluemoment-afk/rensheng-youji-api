#!/usr/bin/env python3
"""把模型选择的命理校准计划确定性转换为五道用户可见问题。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from validate_calibration_questions import ABC_KEYS, expected_display, load_json, load_templates, validate


def build(plan: Any, analysis: Any) -> dict[str, Any]:
    if not isinstance(plan, dict) or plan.get("schema_version") != "1.0.0":
        raise ValueError("calibration-plan.schema_version 必须为1.0.0")
    items = plan.get("questions")
    if not isinstance(items, list) or len(items) != 5:
        raise ValueError("calibration-plan.questions 必须恰好包含五项")
    templates = load_templates()
    questions: list[dict[str, Any]] = []
    for index, item in enumerate(items, 1):
        if not isinstance(item, dict):
            raise ValueError(f"calibration-plan.questions[{index - 1}] 必须是对象")
        template_id = item.get("template_id")
        template = templates.get(template_id)
        if template is None:
            raise ValueError(f"未知固定题型：{template_id}")
        effects = item.get("candidate_effects")
        if not isinstance(effects, dict) or list(effects) != ABC_KEYS:
            raise ValueError(f"第{index}题 candidate_effects 必须依次包含A、B、C")
        candidate_ids: list[str] = []
        for key in ABC_KEYS:
            for effect in effects[key] if isinstance(effects[key], list) else []:
                candidate_id = effect.get("candidate_id") if isinstance(effect, dict) else None
                if isinstance(candidate_id, str) and candidate_id not in candidate_ids:
                    candidate_ids.append(candidate_id)
        questions.append({
            "display": expected_display(template, index),
            "audit": {
                "template_id": template_id,
                "comparison_axis": template["comparison_axis"],
                "time_window": template["time_window"],
                "selection_rule": template["selection_rule"],
                "answer_type": template["answer_type"],
                "evidence_mode": template["evidence_mode"],
                "choice_meanings": {choice["key"]: choice["value_code"] for choice in template["choices"]} | {"D": "uncertain"},
                "candidate_ids": candidate_ids,
                "candidate_effects": effects,
                "calibration_targets": template["calibration_targets"],
                "evidence_lenses": item.get("evidence_lenses"),
                "core_sections": item.get("core_sections"),
                "alternatives": item.get("alternatives"),
                "birth_time_dependency": item.get("birth_time_dependency"),
                "confidence": item.get("confidence"),
            },
        })
    output = {"schema_version": "2.1.0", "template_version": "1.0.0", "questions": questions}
    errors = validate(output, analysis)
    if errors:
        raise ValueError("；".join(errors))
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="根据固定题型生成五道现实校准题")
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--analysis", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        output = build(load_json(args.plan), load_json(args.analysis))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps({"status": "ok", "output": str(args.output), "questions": 5}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
