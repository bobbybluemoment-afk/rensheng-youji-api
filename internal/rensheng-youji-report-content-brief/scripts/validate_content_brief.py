#!/usr/bin/env python3
"""校验报告事实提纲是否忠实引用校准后Core。"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

DIMENSIONS = ["self_growth", "love_partner", "career", "finance_resources", "body_emotion", "family_growth"]
REQUIRED_COVERAGE = {"feature", "behavior", "formation", "challenge", "current_change", "response"}


def digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate(data: Any, analysis: Any | None = None) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["事实提纲必须是对象"]
    for key in ("schema_version", "brief_id", "source", "focus_scope", "life_overview", "dimensions", "current_question", "calibration_internal"):
        if key not in data:
            errors.append(f"缺少字段：{key}")
    is_v11 = data.get("schema_version") == "1.1.0"
    if data.get("schema_version") not in {"1.0.0", "1.1.0"}:
        errors.append("schema_version 必须为1.0.0或1.1.0")
    source = data.get("source", {})
    expected_core = "0.6.0" if is_v11 else "0.5.0"
    if source.get("core_version") != expected_core:
        errors.append(f"事实提纲必须来自core_version={expected_core}")
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
        if is_v11:
            selected = section.get("selected_claims")
            if not isinstance(selected, list) or [item.get("claim_id") for item in selected if isinstance(item, dict)] != claim_ids:
                errors.append(f"第{index + 1}个内容区必须按claim_ids顺序携带Core判断实体")
            balance = section.get("source_balance")
            if not isinstance(balance, dict):
                errors.append(f"第{index + 1}个内容区缺少来源比例审计")
            else:
                baseline = sum(item.get("origin") in {"chart_baseline", "timing_baseline"} for item in selected or [] if isinstance(item, dict))
                calibrated = sum(item.get("origin") == "user_fact_refinement" for item in selected or [] if isinstance(item, dict))
                expected_ratio = round(baseline / len(selected), 4) if selected else 0
                methods = sorted({method for item in selected or [] if isinstance(item, dict) for method in item.get("supporting_methods") or []})
                expected = {"baseline_count": baseline, "calibrated_refinement_count": calibrated, "baseline_ratio": expected_ratio, "method_layers": methods}
                if balance != expected:
                    errors.append(f"第{index + 1}个内容区的来源比例审计与实体判断不一致")
                if index != 1 and (expected_ratio < 0.8 or calibrated > 1):
                    errors.append(f"第{index + 1}个内容区必须至少八成来自命盘/时运基线，且校准修正最多一条")
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
        if is_v11 and source.get("analysis_sha256") != digest(analysis):
            errors.append("事实提纲中的Core整体哈希与实际母稿不一致")
        snapshot_keys = ("claim_id", "domain", "reality_dimension", "claim", "mechanism_chain", "evidence_ids", "supporting_methods", "allowed_examples", "counterevidence", "confidence", "unsupported_extensions", "calibration_status", "origin")
        for section in sections if is_v11 else []:
            if not isinstance(section, dict):
                continue
            for selected in section.get("selected_claims") or []:
                claim = ledger.get(selected.get("claim_id")) if isinstance(selected, dict) else None
                if not claim:
                    continue
                body = {key: claim.get(key) for key in snapshot_keys}
                if any(selected.get(key) != body[key] for key in snapshot_keys) or selected.get("source_sha256") != digest(body):
                    errors.append(f"事实提纲中的判断实体已偏离Core：{selected.get('claim_id')}")
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
