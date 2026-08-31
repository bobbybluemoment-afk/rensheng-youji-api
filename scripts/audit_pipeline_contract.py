#!/usr/bin/env python3
"""Audit that every production-stage input has an earlier producer and a real contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def audit(root: Path, contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if contract.get("schema_version") != "1.0.0":
        errors.append("pipeline contract schema_version 必须为1.0.0")
    available = set(contract.get("external_artifacts") or [])
    produced_by: dict[str, str] = {}
    stage_ids: set[str] = set()
    stages = contract.get("stages")
    if not isinstance(stages, list) or not stages:
        return errors + ["pipeline contract 必须包含stages"]
    for index, stage in enumerate(stages):
        path = f"stages[{index}]"
        if not isinstance(stage, dict):
            errors.append(f"{path} 必须是对象")
            continue
        stage_id = stage.get("id")
        if not isinstance(stage_id, str) or not stage_id or stage_id in stage_ids:
            errors.append(f"{path}.id 缺失或重复")
            continue
        stage_ids.add(stage_id)
        producer = stage.get("producer")
        if producer not in {"deterministic", "ai_constrained"}:
            errors.append(f"{path}.producer 值无效")
        missing_inputs = sorted(set(stage.get("inputs") or []) - available)
        if missing_inputs:
            errors.append(f"{stage_id}存在没有上游生产者的输入：{missing_inputs}")
        outputs = stage.get("outputs") or []
        if not outputs:
            errors.append(f"{stage_id}没有声明输出")
        for output in outputs:
            if output in available:
                errors.append(f"产物{output}被重复生产：{produced_by.get(output, 'external')}与{stage_id}")
            available.add(output)
            produced_by[output] = stage_id
        if producer == "deterministic" and not stage.get("script"):
            errors.append(f"{stage_id}是确定性阶段但没有生产脚本")
        if producer == "ai_constrained" and not stage.get("contract"):
            errors.append(f"{stage_id}是AI阶段但没有Skill或参考契约")
        for key in ("script", "contract", "validator"):
            value = stage.get(key)
            if value and not (root / value).is_file():
                errors.append(f"{stage_id}.{key}引用文件不存在：{value}")
    required_delivery = {"delivery_manifest", "card_png", "report_markdown", "report_pdf"}
    if not required_delivery.issubset(available):
        errors.append("生产链没有形成完整最终交付产物")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--contract", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    contract_path = args.contract or root / "internal/pipeline-contract.json"
    try:
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        errors = audit(root, contract)
    except (OSError, json.JSONDecodeError) as exc:
        errors = [str(exc)]
    print(json.dumps({"status": "ok" if not errors else "error", "errors": errors}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
