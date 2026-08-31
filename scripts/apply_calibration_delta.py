#!/usr/bin/env python3
"""Apply calibration as a narrow patch without regenerating the Core."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from core_baseline import digest, protected_projection


ALLOWED_STATUS = {"match", "supported_unselected", "conditional", "weakened", "partial", "reject", "uncertain"}
GROUP_FOR_STATUS = {
    "match": "confirmed",
    "supported_unselected": "supported_unselected",
    "conditional": "conditional",
    "weakened": "weakened",
    "partial": "conditional",
    "reject": "rejected",
    "uncertain": "uncertain",
}


def apply_patch(baseline: dict[str, Any], lock: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    if patch.get("schema_version") != "1.0.0":
        raise ValueError("Calibration patch schema_version must be 1.0.0")
    if patch.get("analysis_id") != lock.get("analysis_id"):
        raise ValueError("Calibration patch analysis_id differs from baseline")
    if patch.get("baseline_sha256") != lock.get("baseline_sha256") or digest(baseline) != lock.get("baseline_sha256"):
        raise ValueError("Calibration patch is not bound to the locked baseline")
    result = json.loads(json.dumps(baseline, ensure_ascii=False))
    candidates = {item["candidate_id"]: item for item in result.get("reality_candidate_pool", [])}
    claims = {item["claim_id"]: item for item in result.get("report_claim_ledger", [])}
    seen_candidates: set[str] = set()
    for update in patch.get("candidate_updates", []):
        if set(update) != {"candidate_id", "status"}:
            raise ValueError("Each candidate update must contain only candidate_id and status")
        candidate_id, status = update["candidate_id"], update["status"]
        if candidate_id not in candidates or status not in ALLOWED_STATUS or candidate_id in seen_candidates:
            raise ValueError(f"Invalid or duplicate candidate update: {candidate_id}")
        seen_candidates.add(candidate_id)
        candidates[candidate_id]["status"] = status

    claim_updates: list[dict[str, Any]] = []
    seen_claims: set[str] = set()
    for update in patch.get("claim_updates", []):
        required = {"claim_id", "after_status", "reason", "user_fact_evidence_ids"}
        if set(update) != required:
            raise ValueError("Each claim update has invalid fields")
        claim_id, status = update["claim_id"], update["after_status"]
        if claim_id not in claims or status not in ALLOWED_STATUS or claim_id in seen_claims:
            raise ValueError(f"Invalid or duplicate claim update: {claim_id}")
        if len(str(update["reason"])) < 6:
            raise ValueError(f"Claim update reason is too short: {claim_id}")
        seen_claims.add(claim_id)
        before = claims[claim_id]["calibration_status"]
        claims[claim_id]["calibration_status"] = status
        claim_updates.append({
            "claim_id": claim_id,
            "before_status": before,
            "after_status": status,
            "reason": update["reason"],
            "user_fact_evidence_ids": update["user_fact_evidence_ids"],
            "rewritten_reality_claim": claims[claim_id]["plain_claim"],
            "preserves_chart_mechanism": True,
        })

    existing_evidence = {item["evidence_id"] for item in result.get("evidence_registry", [])}
    user_fact_ids: list[str] = []
    for evidence in patch.get("user_fact_evidence", []):
        if evidence.get("source_layer") != "user_fact" or evidence.get("evidence_id") in existing_evidence:
            raise ValueError("Calibration may append only new user_fact evidence")
        normalized_evidence = dict(evidence)
        normalized_evidence.setdefault("method_id", "user_fact")
        normalized_evidence.setdefault("independence_group", "reality_confirmation")
        result["evidence_registry"].append(normalized_evidence)
        existing_evidence.add(normalized_evidence["evidence_id"])
        user_fact_ids.append(normalized_evidence["evidence_id"])
    for update in claim_updates:
        if set(update["user_fact_evidence_ids"]) - set(user_fact_ids):
            raise ValueError(f"{update['claim_id']} references unregistered user fact evidence")

    groups = {name: [] for name in ("confirmed", "supported_unselected", "conditional", "weakened", "rejected", "uncertain")}
    for candidate in candidates.values():
        status = candidate.get("status", "unverified")
        if status == "unverified":
            status = "uncertain"
            candidate["status"] = status
        groups[GROUP_FOR_STATUS[status]].append(candidate["candidate_id"])
    result["calibration_state"] = {
        "confirmed": groups["confirmed"],
        "partial": groups["conditional"] + groups["weakened"],
        "rejected": groups["rejected"],
        "uncertain": groups["uncertain"],
        "updates": patch.get("responses", []),
    }
    result["calibration_delta"] = {
        "baseline_preserved": True,
        **groups,
        "user_fact_evidence_ids": user_fact_ids,
        "claim_updates": claim_updates,
    }
    if digest(protected_projection(result)) != lock.get("protected_sha256"):
        raise ValueError("Calibration patch changed a protected Core field")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--delta", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
        lock = json.loads(args.lock.read_text(encoding="utf-8"))
        patch = json.loads(args.delta.read_text(encoding="utf-8"))
        result = apply_patch(baseline, lock, patch)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "ok", "output": str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
