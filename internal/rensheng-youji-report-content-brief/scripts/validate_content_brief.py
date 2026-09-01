#!/usr/bin/env python3
"""校验报告事实提纲是否忠实引用校准后Core。"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from report_source_contract import BASE_COVERAGE, DIMENSIONS, delivery_rule, required_coverage  # noqa: E402


def digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate(data: Any, analysis: Any | None = None, resolved: Any | None = None) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["事实提纲必须是对象"]
    for key in ("schema_version", "brief_id", "source", "focus_scope", "life_overview", "dimensions", "current_question", "calibration_internal"):
        if key not in data:
            errors.append(f"缺少字段：{key}")
    is_v11 = data.get("schema_version") == "1.1.0"
    is_v12 = data.get("schema_version") == "1.2.0"
    is_v13 = data.get("schema_version") == "1.3.0"
    is_v14 = data.get("schema_version") == "1.4.0"
    is_v15 = data.get("schema_version") == "1.5.0"
    is_materialized = is_v11 or is_v12 or is_v13 or is_v14 or is_v15
    if data.get("schema_version") not in {"1.0.0", "1.1.0", "1.2.0", "1.3.0", "1.4.0", "1.5.0"}:
        errors.append("schema_version 必须为1.0.0—1.5.0中的受支持版本")
    source = data.get("source", {})
    expected_cores = {"0.9.0", "0.10.0", "0.11.0", "0.12.0", "0.13.0", "0.14.0"} if is_v15 else {"0.8.1"} if is_v14 else {"0.8.0"} if is_v13 else {"0.7.0"} if is_v12 else {"0.6.0"} if is_v11 else {"0.5.0"}
    if source.get("core_version") not in expected_cores:
        errors.append(f"事实提纲必须来自core_version={sorted(expected_cores)}")
    if data.get("focus_scope", {}).get("protected_sections") != ["life_overview", "dimensions"]:
        errors.append("完整人生主线和六个领域必须免受关注方向改写")
    sections = [data.get("life_overview"), data.get("current_question")]
    dimensions = data.get("dimensions")
    if not isinstance(dimensions, list) or [item.get("id") for item in dimensions if isinstance(item, dict)] != list(DIMENSIONS):
        errors.append("dimensions 必须按固定顺序完整包含六个领域")
    else:
        sections.extend(dimensions)
        for item in dimensions:
            if is_v15:
                mode = item.get("delivery_mode")
                try:
                    rule = delivery_rule(mode)
                except ValueError:
                    errors.append(f"{item.get('id')} 的delivery_mode无效")
                    continue
                expected_missing = set(required_coverage(item.get("id"))) - set(item.get("coverage") or [])
                if set(item.get("missing_coverage") or []) != expected_missing:
                    errors.append(f"{item.get('id')} 的缺失覆盖项与实际选材不一致")
                if mode == "normal" and expected_missing:
                    errors.append(f"{item.get('id')} 正常章节缺少人物描述覆盖项")
            elif not set(BASE_COVERAGE).issubset(set(item.get("coverage") or [])):
                errors.append(f"{item.get('id')} 缺少人物描述覆盖项")
        if is_v13 or is_v14 or is_v15:
            usage: dict[str, int] = {}
            for item in dimensions:
                claim_set = set(item.get("claim_ids") or [])
                specific = set(item.get("domain_specific_claim_ids") or [])
                mainline = set(item.get("mainline_claim_ids") or [])
                minimum_specific = delivery_rule(item.get("delivery_mode"))["minimum_specific"] if is_v15 and item.get("delivery_mode") in {"normal", "shortened", "minimal", "evidence_gap"} else 4
                if len(specific) < minimum_specific or not specific.issubset(claim_set):
                    errors.append(f"{item.get('id')} 至少需要{minimum_specific}个领域专属判断")
                if len(mainline) / max(len(claim_set), 1) > 0.30 or not mainline.issubset(claim_set):
                    errors.append(f"{item.get('id')} 人生主线判断不得超过30%")
                minimum_mechanisms = 2 if not is_v15 or item.get("delivery_mode") in {"normal", "shortened"} else 1 if item.get("delivery_mode") == "minimal" else 0
                if len(set(item.get("domain_mechanisms") or [])) < minimum_mechanisms or (item.get("delivery_mode") == "normal" and item.get("survives_without_mainline") is not True):
                    errors.append(f"{item.get('id')} 缺少领域机制，或去掉主线后不能独立成立")
                for claim_id in claim_set:
                    usage[claim_id] = usage.get(claim_id, 0) + 1
            overused = sorted(item for item, count in usage.items() if count > 2)
            if overused:
                errors.append(f"同一判断最多进入两个现实领域：{overused}")
    referenced: set[str] = set()
    for index, section in enumerate(sections):
        if not isinstance(section, dict):
            errors.append(f"第{index + 1}个内容区不是对象")
            continue
        claim_ids = section.get("claim_ids")
        minimum_claims = delivery_rule(section.get("delivery_mode"))["minimum_claims"] if is_v15 and section.get("delivery_mode") in {"normal", "shortened", "minimal", "evidence_gap"} else 4
        if not isinstance(claim_ids, list) or len(set(claim_ids)) < minimum_claims:
            errors.append(f"第{index + 1}个内容区至少引用{minimum_claims}个不同判断")
        else:
            referenced.update(claim_ids)
        if not isinstance(section.get("allowed_examples"), list) or not isinstance(section.get("prohibited_claims"), list):
            errors.append(f"第{index + 1}个内容区必须记录可用例子和禁止外推")
        if is_materialized:
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
        if is_v13 or is_v14 or is_v15:
            emphasis = section.get("emphasis_claim_ids")
            minimum, maximum = (0, 2) if index == 0 else (0, 1)
            if not isinstance(emphasis, list) or not minimum <= len(set(emphasis)) <= maximum or not set(emphasis or []).issubset(set(claim_ids or [])):
                errors.append(f"第{index + 1}个内容区重点判断最多{maximum}条，且必须来自本区判断")
            snapshots = section.get("emphasis_claims")
            if not isinstance(snapshots, list) or [item.get("claim_id") for item in snapshots if isinstance(item, dict)] != emphasis:
                errors.append(f"第{index + 1}个内容区必须携带Core重点判断实体")
        if is_v14 or is_v15:
            mandatory = section.get("mandatory_claim_ids")
            mandatory_snapshots = section.get("mandatory_claims")
            minimum_mandatory = 0 if is_v15 and section.get("delivery_mode") == "evidence_gap" else 1
            maximum_mandatory = 2 if not is_v15 or section.get("delivery_mode") == "normal" else 1
            if not isinstance(mandatory, list) or not minimum_mandatory <= len(mandatory) <= maximum_mandatory or not set(mandatory).issubset(set(claim_ids or [])):
                errors.append(f"第{index + 1}个内容区必须锁定{minimum_mandatory}—{maximum_mandatory}条必进报告判断")
            if not isinstance(mandatory_snapshots, list) or [item.get("claim_id") for item in mandatory_snapshots if isinstance(item, dict)] != mandatory:
                errors.append(f"第{index + 1}个内容区必须携带Core必进报告判断实体")
        if is_v12 or is_v13 or is_v14 or is_v15:
            required_entities = ("selected_evidence", "selected_formation_chains", "selected_linkage_chains", "selected_reality_candidates", "selected_candidate_relations", "selected_blind_images", "selected_domain_lifecycles", "portrait_context", "calibration_context")
            missing_entities = [key for key in required_entities if key not in section]
            if missing_entities:
                errors.append(f"第{index + 1}个内容区缺少完整Core实体：{'、'.join(missing_entities)}")
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
        if is_materialized and source.get("analysis_sha256") != digest(analysis):
            errors.append("事实提纲中的Core整体哈希与实际母稿不一致")
        if is_v13 or is_v14 or is_v15:
            source_bundle = analysis.get("report_source_bundle", {})
            data_dimensions = {item.get("id"): item for item in data.get("dimensions") or [] if isinstance(item, dict)}
            if is_v15:
                if not isinstance(resolved, dict):
                    errors.append("1.5.0事实提纲必须提供校准后确定性选材文件")
                    resolved = {}
                expected_resolved_hash = digest({key: value for key, value in resolved.items() if key != "resolved_sha256"})
                if resolved.get("resolved_sha256") != expected_resolved_hash:
                    errors.append("校准后确定性选材文件哈希无效")
                resolved_source = resolved.get("source") or {}
                if resolved_source.get("analysis_id") != meta.get("analysis_id") or resolved_source.get("analysis_sha256") != digest(analysis):
                    errors.append("校准后确定性选材文件与当前Core不一致")
                if source.get("resolved_source_sha256") != resolved.get("resolved_sha256"):
                    errors.append("事实提纲与校准后确定性选材来源不一致")
                source_pairs = [
                    (data.get("life_overview"), resolved.get("life_overview"), "life_overview"),
                    (data.get("current_question"), resolved.get("current_question"), "current_question"),
                    *[(data_dimensions.get(domain), (resolved.get("dimensions") or {}).get(domain), f"dimensions.{domain}") for domain in DIMENSIONS],
                ]
                locked = ("claim_ids", "formation_chain_ids", "linkage_chain_ids", "coverage", "missing_coverage", "domain_specific_claim_ids", "mainline_claim_ids", "mandatory_claim_ids", "emphasis_claim_ids", "domain_mechanisms", "survives_without_mainline", "delivery_mode", "rejected_claim_ids", "replacement_log", "evidence_gaps")
            else:
                source_pairs = [
                    (data.get("life_overview"), source_bundle.get("life_narrative_source"), "life_overview"),
                    (data.get("current_question"), source_bundle.get("current_stage_source"), "current_question"),
                    *[(data_dimensions.get(domain), (source_bundle.get("dimensions") or {}).get(domain), f"dimensions.{domain}") for domain in DIMENSIONS],
                ]
                locked = ("claim_ids", "formation_chain_ids", "linkage_chain_ids", "coverage", "domain_specific_claim_ids", "mainline_claim_ids", "mandatory_claim_ids", "emphasis_claim_ids", "domain_mechanisms", "survives_without_mainline")
            for section, core_source, where in source_pairs:
                if not isinstance(section, dict) or not isinstance(core_source, dict):
                    errors.append(f"{where} 缺少Core报告素材来源")
                    continue
                for key in locked:
                    if section.get(key) != core_source.get(key):
                        errors.append(f"{where}.{key} 已偏离Core报告素材")
        snapshot_keys = ("claim_id", "domain", "reality_dimension", "claim_family", "mechanism_family", "claim", "plain_claim", "new_information", "mechanism_chain", "evidence_ids", "supporting_methods", "allowed_examples", "counterevidence", "confidence", "unsupported_extensions", "calibration_status", "origin") if is_v14 or is_v15 else ("claim_id", "domain", "reality_dimension", "claim", "mechanism_chain", "evidence_ids", "supporting_methods", "allowed_examples", "counterevidence", "confidence", "unsupported_extensions", "calibration_status", "origin")
        if is_v15 and source.get("core_version") in {"0.10.0", "0.11.0", "0.12.0", "0.13.0", "0.14.0"}:
            snapshot_keys += ("synthesis_ids", "method_hypothesis_ids", "report_role", "coverage_tags", "applicable_conditions", "reality_confirmation")
        for section in sections if is_materialized else []:
            if not isinstance(section, dict):
                continue
            for selected in section.get("selected_claims") or []:
                claim = ledger.get(selected.get("claim_id")) if isinstance(selected, dict) else None
                if not claim:
                    continue
                body = {key: claim.get(key) for key in snapshot_keys}
                if any(selected.get(key) != body[key] for key in snapshot_keys) or selected.get("source_sha256") != digest(body):
                    errors.append(f"事实提纲中的判断实体已偏离Core：{selected.get('claim_id')}")
            if is_v13 or is_v14 or is_v15:
                for selected in section.get("emphasis_claims") or []:
                    claim = ledger.get(selected.get("claim_id")) if isinstance(selected, dict) else None
                    if not claim:
                        continue
                    body = {key: claim.get(key) for key in snapshot_keys}
                    if any(selected.get(key) != body[key] for key in snapshot_keys) or selected.get("source_sha256") != digest(body):
                        errors.append(f"事实提纲中的重点判断实体已偏离Core：{selected.get('claim_id')}")
            if is_v14 or is_v15:
                for selected in section.get("mandatory_claims") or []:
                    claim = ledger.get(selected.get("claim_id")) if isinstance(selected, dict) else None
                    if not claim:
                        continue
                    body = {key: claim.get(key) for key in snapshot_keys}
                    if any(selected.get(key) != body[key] for key in snapshot_keys) or selected.get("source_sha256") != digest(body):
                        errors.append(f"事实提纲中的必进报告判断实体已偏离Core：{selected.get('claim_id')}")
        if is_v12 or is_v13 or is_v14 or is_v15:
            evidence_index = {item.get("evidence_id"): item for item in analysis.get("evidence_registry", []) if isinstance(item, dict)}
            formation_index = {item.get("chain_id"): item for item in analysis.get("formation_chains", []) if isinstance(item, dict)}
            linkage_index = {item.get("chain_id"): item for item in analysis.get("domain_linkage_chains", []) if isinstance(item, dict)}
            candidate_index = {item.get("candidate_id"): item for item in analysis.get("reality_candidate_pool", []) if isinstance(item, dict)}
            relation_index = {item.get("relation_id"): item for item in analysis.get("candidate_relation_map", []) if isinstance(item, dict)}
            blind_index = {item.get("image_id"): item for item in analysis.get("blind_school_cross_analysis", {}).get("reality_image_candidates", []) if isinstance(item, dict)}
            lifecycle_index = {item.get("domain"): item for item in analysis.get("root_seed_flower_fruit_map", {}).get("domain_lifecycles", []) if isinstance(item, dict)}

            def check_exact(items: Any, index_map: dict[str, dict[str, Any]], id_key: str, where: str) -> None:
                if not isinstance(items, list):
                    errors.append(f"{where} 必须是实体快照数组")
                    return
                for wrapped in items:
                    if not isinstance(wrapped, dict) or set(wrapped) != {"value", "source_sha256"} or not isinstance(wrapped.get("value"), dict):
                        errors.append(f"{where} 含无效实体快照")
                        continue
                    value = wrapped["value"]
                    original = index_map.get(value.get(id_key))
                    if original != value or wrapped.get("source_sha256") != digest(value):
                        errors.append(f"{where} 中的实体已偏离Core：{value.get(id_key)}")

            for section_index, section in enumerate(sections):
                if not isinstance(section, dict):
                    continue
                where = f"第{section_index + 1}个内容区"
                check_exact(section.get("selected_evidence"), evidence_index, "evidence_id", where + ".selected_evidence")
                check_exact(section.get("selected_formation_chains"), formation_index, "chain_id", where + ".selected_formation_chains")
                check_exact(section.get("selected_linkage_chains"), linkage_index, "chain_id", where + ".selected_linkage_chains")
                check_exact(section.get("selected_reality_candidates"), candidate_index, "candidate_id", where + ".selected_reality_candidates")
                check_exact(section.get("selected_candidate_relations"), relation_index, "relation_id", where + ".selected_candidate_relations")
                check_exact(section.get("selected_blind_images"), blind_index, "image_id", where + ".selected_blind_images")
                check_exact(section.get("selected_domain_lifecycles"), lifecycle_index, "domain", where + ".selected_domain_lifecycles")
                portrait = section.get("portrait_context")
                if not isinstance(portrait, dict) or portrait.get("value") != analysis.get("portrait_thesis") or portrait.get("source_sha256") != digest(analysis.get("portrait_thesis")):
                    errors.append(where + ".portrait_context 已偏离Core人物总判断")
                selected_statuses = {wrapped["value"].get("status") for wrapped in section.get("selected_reality_candidates") or [] if isinstance(wrapped, dict) and isinstance(wrapped.get("value"), dict)}
                if "reject" in selected_statuses:
                    errors.append(where + " 使用了Core中已排除的现实候选")
    if re.search(r"组织化过劳型|先扎根后显声|表达窗口|花不显", json.dumps(data, ensure_ascii=False)):
        errors.append("事实提纲含有禁止进入报告链路的生造或技术短语")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("brief", type=Path)
    parser.add_argument("--analysis", type=Path)
    parser.add_argument("--resolved-sources", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.brief.read_text(encoding="utf-8"))
        analysis = json.loads(args.analysis.read_text(encoding="utf-8")) if args.analysis else None
        resolved = json.loads(args.resolved_sources.read_text(encoding="utf-8")) if args.resolved_sources else None
        errors = validate(data, analysis, resolved)
    except (OSError, json.JSONDecodeError) as exc:
        errors = [str(exc)]
    print(json.dumps({"status": "ok" if not errors else "error", "errors": errors}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
