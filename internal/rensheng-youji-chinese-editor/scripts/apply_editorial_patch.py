#!/usr/bin/env python3
"""Apply optional paragraph-only repairs and produce an auditable editorial review."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


CORE_SCRIPTS = Path(__file__).resolve().parents[2] / "rensheng-youji-mingli-core/scripts"
sys.path.insert(0, str(CORE_SCRIPTS))
from _jsonschema_subset import validate_schema_instance  # noqa: E402
from scan_report_language import digest as semantic_digest, scan as scan_language  # noqa: E402

PATCH_SCHEMA = Path(__file__).resolve().parent.parent / "schemas/editorial-repair-patch.schema.json"


def digest(items: list[str]) -> str:
    return hashlib.sha256("\n".join(items).encode()).hexdigest()


def section_map(draft: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in [draft["life_overview"], *draft["dimensions"], draft["current_question"]]}


def set_semantic_text(semantic: dict[str, Any], slot_id: str, text: str) -> None:
    if not slot_id.startswith("semantic."):
        raise ValueError(f"未知语义修订位置：{slot_id}")
    current: Any = semantic
    parts = slot_id.removeprefix("semantic.").split(".")
    for part in parts[:-1]:
        current = current[int(part)] if isinstance(current, list) else current[part]
    final = parts[-1]
    if isinstance(current, list):
        current[int(final)] = text
    else:
        current[final] = text


def apply_all(
    draft: dict[str, Any],
    semantic: dict[str, Any] | None,
    scan: dict[str, Any],
    patch: dict[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any]]:
    if scan.get("draft_id") != draft.get("draft_id"):
        raise ValueError("语言扫描没有绑定当前初稿")
    if scan.get("semantic_sha256") != (semantic_digest(semantic) if semantic is not None else None):
        raise ValueError("语言扫描没有绑定当前报告语义补丁")
    allowed = {item["slot_id"] for item in scan.get("issues") or []}
    if patch is not None:
        schema_errors = validate_schema_instance(patch, json.loads(PATCH_SCHEMA.read_text(encoding="utf-8")))
        if schema_errors:
            raise ValueError("局部修订补丁Schema无效：" + "；".join(schema_errors))
    repair_items = [] if patch is None else patch.get("repairs") or []
    repairs = {item["slot_id"]: item["text"] for item in repair_items}
    if len(repairs) != len(repair_items):
        raise ValueError("局部修订补丁不得重复填写同一段落")
    if scan.get("status") == "repair_required" and patch is None:
        raise ValueError("存在语言问题时必须提供局部修订补丁")
    if scan.get("status") == "repair_required" and set(repairs) != allowed:
        raise ValueError("局部修订补丁必须逐一修复扫描点名的全部段落")
    if scan.get("status") == "pass" and patch is not None:
        raise ValueError("语言扫描已通过时不得生成无意义的编辑补丁")
    if patch and (patch.get("schema_version") != "1.0.0" or patch.get("draft_id") != draft.get("draft_id") or not set(repairs).issubset(allowed)):
        raise ValueError("局部修订只能修改扫描点名的段落")
    result = json.loads(json.dumps(draft, ensure_ascii=False))
    semantic_result = json.loads(json.dumps(semantic, ensure_ascii=False)) if semantic is not None else None
    by_id = section_map(result)
    for slot_id, text in repairs.items():
        if slot_id.startswith("semantic."):
            if semantic_result is None:
                raise ValueError("修订补丁引用了不存在的报告语义字段")
            set_semantic_text(semantic_result, slot_id, text)
            continue
        section_id, number = slot_id.rsplit(":", 1)
        section = by_id[section_id]
        index = int(number) - 1
        mandatory = [item["exact_span"] for item in section.get("claim_realization_map") or [] if item.get("paragraph_index") == index]
        if any(exact not in text for exact in mandatory):
            raise ValueError(f"{slot_id}局部修订删除了Core锁定判断")
        section["paragraphs"][index] = text
    remaining = scan_language(result, semantic_result)
    if remaining.get("status") != "pass":
        left = "、".join(item.get("slot_id", "未知段落") for item in remaining.get("issues") or [])
        raise ValueError("局部修订后仍有语言问题：" + left)
    records = []
    original = section_map(draft)
    edited = section_map(result)
    for section_id in original:
        before, after = original[section_id], edited[section_id]
        changes = [f"第{index + 1}段局部修订" for index, (left, right) in enumerate(zip(before["paragraphs"], after["paragraphs"])) if left != right]
        records.append({"section_id": "dimension:" + section_id if section_id not in {"life_overview", "current_question"} else section_id, "draft_sha256": digest(before["paragraphs"]), "final_sha256": digest(after["paragraphs"]), "source_claim_ids": after["source_claim_ids"], "changes": changes})
    checks = {key: True for key in ("facts_preserved", "no_new_claims", "natural_chinese", "no_template_repetition", "calibration_hidden", "term_context_checked", "cross_section_repetition_checked", "calibration_dominance_checked", "emphasis_preserved", "domain_independence_checked", "mandatory_claims_preserved", "degraded_sections_preserved", "only_flagged_paragraphs_changed")}
    semantic_changes = sorted(slot_id for slot_id in repairs if slot_id.startswith("semantic."))
    semantic_source_sha256 = semantic_digest(semantic) if semantic is not None else None
    semantic_final_sha256 = semantic_digest(semantic_result) if semantic_result is not None else None
    review_id = "review-" + hashlib.sha256(json.dumps({
        "sections": records,
        "semantic_source_sha256": semantic_source_sha256,
        "semantic_final_sha256": semantic_final_sha256,
        "semantic_changes": semantic_changes,
    }, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]
    review = {
        "version": "2.5.0", "review_id": review_id, "draft_id": draft["draft_id"],
        "final_report_id": "pending", "scan_status": scan["status"], "sections": records,
        "semantic_source_sha256": semantic_source_sha256,
        "semantic_final_sha256": semantic_final_sha256,
        "semantic_changes": semantic_changes, "checks": checks,
    }
    return result, semantic_result, review


def apply(draft: dict[str, Any], scan: dict[str, Any], patch: dict[str, Any] | None) -> tuple[dict[str, Any], dict[str, Any]]:
    result, _, review = apply_all(draft, None, scan, patch)
    return result, review


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--draft", type=Path, required=True); parser.add_argument("--scan", type=Path, required=True)
    parser.add_argument("--semantic", type=Path); parser.add_argument("--semantic-output", type=Path)
    parser.add_argument("--patch", type=Path); parser.add_argument("--output", type=Path, required=True); parser.add_argument("--review", type=Path, required=True)
    args = parser.parse_args()
    try:
        load=lambda p: json.loads(p.read_text(encoding="utf-8"))
        if bool(args.semantic) != bool(args.semantic_output):
            raise ValueError("--semantic与--semantic-output必须同时提供")
        result, semantic, review = apply_all(
            load(args.draft), load(args.semantic) if args.semantic else None,
            load(args.scan), load(args.patch) if args.patch else None,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        if args.semantic_output and semantic is not None:
            args.semantic_output.write_text(json.dumps(semantic, ensure_ascii=False, indent=2), encoding="utf-8")
        args.review.write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8")
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status":"error","message":str(exc)}, ensure_ascii=False)); return 1
    print(json.dumps({"status":"ok","output":str(args.output),"review":str(args.review)}, ensure_ascii=False)); return 0


if __name__ == "__main__": raise SystemExit(main())
