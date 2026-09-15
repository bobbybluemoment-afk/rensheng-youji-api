#!/usr/bin/env python3
"""Shared lifecycle rules for report-claim calibration states."""

from __future__ import annotations

from typing import Any


BASELINE_CLAIM_STATUSES = {"unverified", "uncertain"}
CALIBRATION_STATUS_VALUES = {
    "unverified",
    "match",
    "supported_unselected",
    "conditional",
    "weakened",
    "partial",
    "reject",
    "uncertain",
}


def pre_freeze_pending_claim_errors(claims: Any) -> list[str]:
    """Reject a baseline that already contains calibrated pending claims."""
    errors: list[str] = []
    for index, claim in enumerate(claims or []):
        if not isinstance(claim, dict) or claim.get("claim_class") != "calibration_pending":
            continue
        if claim.get("calibration_status") not in BASELINE_CLAIM_STATUSES:
            claim_id = claim.get("claim_id", f"report_claim_ledger[{index}]")
            errors.append(f"{claim_id} 待校准判断在冻结前必须保持unverified或uncertain")
    return errors


def calibrated_claim_update_errors(claims: Any, claim_updates: Any) -> list[str]:
    """Ensure every post-calibration claim status is backed by the delta ledger."""
    errors: list[str] = []
    claim_by_id = {
        item.get("claim_id"): item
        for item in (claims or [])
        if isinstance(item, dict) and isinstance(item.get("claim_id"), str)
    }
    update_by_id: dict[str, dict[str, Any]] = {}
    for index, update in enumerate(claim_updates or []):
        if not isinstance(update, dict):
            continue
        claim_id = update.get("claim_id")
        if not isinstance(claim_id, str) or claim_id not in claim_by_id:
            continue
        if claim_id in update_by_id:
            errors.append(f"calibration_delta.claim_updates[{index}].claim_id 不能重复")
            continue
        update_by_id[claim_id] = update
        claim = claim_by_id[claim_id]
        if update.get("after_status") != claim.get("calibration_status"):
            errors.append(f"{claim_id} 的calibration_status与校准增量after_status不一致")
        if update.get("rewritten_reality_claim") != claim.get("plain_claim"):
            errors.append(f"{claim_id} 的校准增量不得改写冻结判断正文")
        if update.get("preserves_chart_mechanism") is not True:
            errors.append(f"{claim_id} 的校准增量必须保留原命理机制")

    for claim_id, claim in claim_by_id.items():
        status = claim.get("calibration_status")
        if status not in CALIBRATION_STATUS_VALUES:
            continue
        if status not in BASELINE_CLAIM_STATUSES and claim_id not in update_by_id:
            errors.append(f"{claim_id} 的校准后状态{status}缺少calibration_delta.claim_updates记录")
    return errors
