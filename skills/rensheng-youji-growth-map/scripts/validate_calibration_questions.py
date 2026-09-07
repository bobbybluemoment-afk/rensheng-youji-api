#!/usr/bin/env python3
"""Validate deterministic personal calibration questions and render visible Markdown."""

from __future__ import annotations

import argparse
from collections import Counter
import json
import re
from pathlib import Path
from typing import Any

from build_calibration_questions import DOMAINS, digest, expected_display


VISIBLE_BANNED = {"日主", "身强", "身弱", "印旺", "比肩", "劫财", "食神", "伤官", "正印", "偏印", "正财", "偏财", "正官", "七杀", "格局", "喜用", "忌神", "天干", "地支", "藏干", "大运", "流年", "刑冲合害", "根苗花果", "候选编号", "置信度"}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(data: Any, analysis: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict) or data.get("schema_version") != "3.0.0" or data.get("template_version") != "2.0.0":
        return ["校准题必须使用schema_version=3.0.0和template_version=2.0.0"]
    expected_source = {
        "analysis_id": analysis.get("analysis_meta", {}).get("analysis_id"),
        "baseline_sha256": digest(analysis),
    }
    if data.get("source") != expected_source:
        errors.append("校准题没有绑定当前冻结Core及其哈希")
    questions = data.get("questions")
    if not isinstance(questions, list) or len(questions) != 5:
        return ["questions必须恰好包含五道题"]
    candidates = {item["candidate_id"]: item for item in analysis.get("reality_candidate_pool") or [] if isinstance(item, dict)}
    claims = {item["claim_id"]: item for item in analysis.get("report_claim_ledger") or [] if isinstance(item, dict)}
    domains: list[str] = []
    kinds: list[str] = []
    axes: list[tuple[str, str]] = []
    for index, question in enumerate(questions, 1):
        display, audit = question.get("display"), question.get("audit")
        ids = audit.get("candidate_ids") if isinstance(audit, dict) else None
        if not isinstance(ids, list) or len(ids) != 1 or ids[0] not in candidates:
            errors.append(f"第{index}题必须绑定一个冻结Core现实候选")
            continue
        candidate = candidates[ids[0]]
        if display != expected_display(candidate, index):
            errors.append(f"第{index}题没有由冻结Core候选确定性生成")
        visible = json.dumps(display, ensure_ascii=False)
        leaked = sorted(term for term in VISIBLE_BANNED if term in visible)
        if leaked or re.search(r"\b(?:c\d+|claim_[a-z0-9_]+)\b", visible, re.I):
            errors.append(f"第{index}题泄露内部信息：{'、'.join(leaked)}")
        domain, kind = candidate.get("domain"), candidate.get("candidate_kind")
        if domain not in DOMAINS:
            errors.append(f"第{index}题领域无效")
        else:
            domains.append(domain)
        kinds.append(str(kind))
        axes.append((str(domain), str(candidate.get("reality_dimension") or candidate.get("label"))))
        if audit.get("related_claim_ids") != candidate.get("related_claim_ids") or any(item not in claims for item in audit.get("related_claim_ids") or []):
            errors.append(f"第{index}题关联判断不是冻结Core中的真实判断")
        expected_effects = {
            "A": [{"candidate_id": ids[0], "status": "match"}],
            "B": [{"candidate_id": ids[0], "status": "reject"}],
            "C": [{"candidate_id": ids[0], "status": "partial"}], "D": [],
        }
        if audit.get("candidate_effects") != expected_effects:
            errors.append(f"第{index}题答案影响不是确定性映射")
        if audit.get("source_class") == "weak_candidate":
            errors.append(f"第{index}题不得使用证据较弱候选凑题")
    counts = Counter(domains)
    if len(counts) < 4:
        errors.append("五道题至少覆盖四个报告领域")
    if max(counts.values(), default=0) > 2:
        errors.append("同一报告领域最多两题")
    if "timed_event" not in kinds:
        errors.append("五道题至少包含一道时间事件题")
    if sum(item in {"objective_state", "timed_event"} for item in kinds) < 2:
        errors.append("五道题至少包含两道客观状态或时间事件题")
    if len(set(axes)) != 5:
        errors.append("五道题不得重复核对同一现实问题轴")
    return errors


def render_visible(data: dict[str, Any]) -> str:
    lines = ["为了让报告更贴近你的真实经历，请回答下面五道题。", "可以只回复字母；选择D时请写下自己的经历。", ""]
    for item in data["questions"]:
        display = item["display"]
        lines.extend([f"**校准{display['number']}｜{display['domain']}**", display["prompt"], f"时间范围：{display['time_scope']}"])
        lines.extend(f"{choice['key']}. {choice['text']}" for choice in display["choices"])
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--analysis", type=Path, required=True)
    parser.add_argument("--visible-out", type=Path)
    args = parser.parse_args()
    try:
        data, analysis = load_json(args.input), load_json(args.analysis)
        errors = validate(data, analysis)
        if not errors and args.visible_out:
            args.visible_out.parent.mkdir(parents=True, exist_ok=True)
            args.visible_out.write_text(render_visible(data), encoding="utf-8")
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        errors = [str(exc)]
    print(json.dumps({"status": "ok" if not errors else "error", "errors": errors}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
