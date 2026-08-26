#!/usr/bin/env python3
"""把Core中的完整判断实体写入报告事实提纲，避免写作模型只看到编号。"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def canonical_digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def snapshot(claim: dict[str, Any]) -> dict[str, Any]:
    keys = ("claim_id", "domain", "reality_dimension", "claim", "mechanism_chain", "evidence_ids", "supporting_methods", "allowed_examples", "counterevidence", "confidence", "unsupported_extensions", "calibration_status", "origin")
    body = {key: claim[key] for key in keys}
    return {**body, "source_sha256": canonical_digest(body)}


def enrich_section(section: dict[str, Any], ledger: dict[str, dict[str, Any]]) -> None:
    ids = section.get("claim_ids") or []
    missing = [claim_id for claim_id in ids if claim_id not in ledger]
    if missing:
        raise ValueError("提纲引用了不存在的判断：" + "、".join(missing))
    selected = [snapshot(ledger[claim_id]) for claim_id in ids]
    section["selected_claims"] = selected
    baseline = sum(item["origin"] in {"chart_baseline", "timing_baseline"} for item in selected)
    calibrated = sum(item["origin"] == "user_fact_refinement" for item in selected)
    section["source_balance"] = {
        "baseline_count": baseline,
        "calibrated_refinement_count": calibrated,
        "baseline_ratio": round(baseline / len(selected), 4) if selected else 0,
        "method_layers": sorted({method for item in selected for method in item["supporting_methods"]}),
    }


def materialize(selection: dict[str, Any], analysis: dict[str, Any]) -> dict[str, Any]:
    result = json.loads(json.dumps(selection, ensure_ascii=False))
    result["schema_version"] = "1.1.0"
    meta = analysis["analysis_meta"]
    result.setdefault("source", {}).update({"analysis_id": meta["analysis_id"], "core_version": meta["core_version"], "analysis_sha256": canonical_digest(analysis)})
    ledger = {item["claim_id"]: item for item in analysis["report_claim_ledger"]}
    for section in [result["life_overview"], *result["dimensions"], result["current_question"]]:
        enrich_section(section, ledger)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("selection", type=Path)
    parser.add_argument("--analysis", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = materialize(json.loads(args.selection.read_text(encoding="utf-8")), json.loads(args.analysis.read_text(encoding="utf-8")))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "ok", "output": str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
