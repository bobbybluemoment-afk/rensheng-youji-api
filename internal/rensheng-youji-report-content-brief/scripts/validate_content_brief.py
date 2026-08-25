#!/usr/bin/env python3
"""校验报告事实提纲是否忠实引用校准后Core。"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

DIMENSIONS = ["self_growth", "love_partner", "career", "finance_resources", "body_emotion", "family_growth"]
REQUIRED_COVERAGE = {"feature", "behavior", "formation", "challenge", "current_change", "response"}


def validate(data: Any, analysis: Any | None = None) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["事实提纲必须是对象"]
    for key in ("schema_version", "brief_id", "source", "focus_scope", "life_overview", "dimensions", "current_question", "calibration_internal"):
        if key not in data:
            errors.append(f"缺少字段：{key}")
    if data.get("schema_version") != "1.0.0":
        errors.append("schema_version 必须为1.0.0")
    source = data.get("source", {})
    if source.get("core_version") != "0.5.0":
        errors.append("事实提纲必须来自core_version=0.5.0")
    if data.get("focus_scope", {}).get("protected_sections") != ["life_overview", "dimensions"]:
        errors.append("完整人生主线和六个领域必须免受关注方向改写")
    sections = [data.get("life_overview"), data.get("current_question")]
    dimensions = data.get("dimensions")
    if not isinstance(dimensions, list) or [item.get("id") for item in dimensions if isinstance(item, dict)] != DIMENSIONS:
        errors.append("dimensions 必须按固定顺序完整包含六个领域")
    else:
        sections.extend(dimensions)
        for item in dimensions:
            if not REQUIRED_COVERAGE.issubset(set(item.get("coverage") or [])):
                errors.append(f"{item.get('id')} 缺少人物描述覆盖项")
    referenced: set[str] = set()
    for index, section in enumerate(sections):
        if not isinstance(section, dict):
            errors.append(f"第{index + 1}个内容区不是对象")
            continue
        claim_ids = section.get("claim_ids")
        if not isinstance(claim_ids, list) or len(set(claim_ids)) < 4:
            errors.append(f"第{index + 1}个内容区至少引用4个不同判断")
        else:
            referenced.update(claim_ids)
        if not isinstance(section.get("allowed_examples"), list) or not isinstance(section.get("prohibited_claims"), list):
            errors.append(f"第{index + 1}个内容区必须记录可用例子和禁止外推")
    calibration = data.get("calibration_internal", {})
    rejected = set(calibration.get("rejected_claim_ids") or [])
    if rejected & referenced:
        errors.append("事实提纲使用了已被校准排除的判断")
    if analysis is not None and isinstance(analysis, dict):
        meta = analysis.get("analysis_meta", {})
        if source.get("analysis_id") != meta.get("analysis_id") or source.get("core_version") != meta.get("core_version"):
            errors.append("事实提纲与Core来源不一致")
        ledger = {item.get("claim_id"): item for item in analysis.get("report_claim_ledger", []) if isinstance(item, dict)}
        missing = sorted(referenced - set(ledger))
        if missing:
            errors.append("事实提纲引用了不存在的判断：" + "、".join(missing))
        rejected_from_core = {key for key, value in ledger.items() if value.get("calibration_status") == "reject"}
        if rejected_from_core & referenced:
            errors.append("事实提纲使用了Core中已排除的判断")
    if re.search(r"组织化过劳型|先扎根后显声|表达窗口|花不显", json.dumps(data, ensure_ascii=False)):
        errors.append("事实提纲含有禁止进入报告链路的生造或技术短语")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("brief", type=Path)
    parser.add_argument("--analysis", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.brief.read_text(encoding="utf-8"))
        analysis = json.loads(args.analysis.read_text(encoding="utf-8")) if args.analysis else None
        errors = validate(data, analysis)
    except (OSError, json.JSONDecodeError) as exc:
        errors = [str(exc)]
    print(json.dumps({"status": "ok" if not errors else "error", "errors": errors}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
