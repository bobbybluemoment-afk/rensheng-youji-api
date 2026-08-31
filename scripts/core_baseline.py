#!/usr/bin/env python3
"""Freeze and verify the immutable pre-calibration Core baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
CORE_VALIDATOR = REPO_ROOT / "internal/rensheng-youji-mingli-core/scripts/validate_analysis_output.py"


def digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def protected_projection(data: dict[str, Any]) -> dict[str, Any]:
    """Return everything calibration is forbidden to rewrite."""
    projection = {
        key: value
        for key, value in data.items()
        if key not in {
            "calibration_state",
            "calibration_delta",
            "reality_candidate_pool",
            "report_claim_ledger",
            "evidence_registry",
        }
    }
    projection["reality_candidate_pool"] = [
        {key: value for key, value in item.items() if key != "status"}
        for item in data.get("reality_candidate_pool", [])
    ]
    projection["report_claim_ledger"] = [
        {key: value for key, value in item.items() if key != "calibration_status"}
        for item in data.get("report_claim_ledger", [])
    ]
    projection["evidence_registry"] = [
        item for item in data.get("evidence_registry", []) if item.get("source_layer") != "user_fact"
    ]
    return projection


def validate_core(path: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(CORE_VALIDATOR), str(path)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise ValueError(result.stdout.strip() or result.stderr.strip() or "Core validation failed")


def freeze(source: Path, baseline: Path, lock_path: Path) -> dict[str, Any]:
    validate_core(source)
    data = json.loads(source.read_text(encoding="utf-8"))
    meta = data.get("analysis_meta", {})
    if meta.get("core_version") != "0.12.0":
        raise ValueError("Only core_version=0.12.0 can be frozen by this workflow")
    if data.get("method_execution_audit", {}).get("delivery_decision") == "preliminary_only":
        raise ValueError("preliminary_only Core cannot be frozen for the full calibrated report workflow")
    if any(item.get("source_layer") == "user_fact" for item in data.get("evidence_registry", [])):
        raise ValueError("Baseline Core must be frozen before calibration user facts are added")
    if any(item.get("status") != "unverified" for item in data.get("reality_candidate_pool", [])):
        raise ValueError("Baseline candidates must all be unverified before calibration")
    baseline.parent.mkdir(parents=True, exist_ok=True)
    baseline.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    lock = {
        "schema_version": "1.0.0",
        "analysis_id": meta.get("analysis_id"),
        "core_version": meta.get("core_version"),
        "baseline_sha256": digest(data),
        "protected_sha256": digest(protected_projection(data)),
    }
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(json.dumps(lock, ensure_ascii=False, indent=2), encoding="utf-8")
    return lock


def verify(baseline_path: Path, lock_path: Path, calibrated_path: Path) -> dict[str, Any]:
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    calibrated = json.loads(calibrated_path.read_text(encoding="utf-8"))
    meta = calibrated.get("analysis_meta", {})
    errors: list[str] = []
    if digest(baseline) != lock.get("baseline_sha256"):
        errors.append("Baseline Core bytes no longer match the lock")
    if digest(protected_projection(baseline)) != lock.get("protected_sha256"):
        errors.append("Baseline protected projection no longer matches the lock")
    if digest(protected_projection(calibrated)) != lock.get("protected_sha256"):
        errors.append("Calibration rewrote chart facts, technical evidence, claim wording, or report sources")
    if meta.get("analysis_id") != lock.get("analysis_id") or meta.get("core_version") != lock.get("core_version"):
        errors.append("Calibrated Core identity differs from baseline")
    if calibrated.get("calibration_delta", {}).get("baseline_preserved") is not True:
        errors.append("calibration_delta.baseline_preserved must be true")
    if errors:
        raise ValueError("; ".join(errors))
    validate_core(calibrated_path)
    return {
        "status": "ok",
        "analysis_id": lock.get("analysis_id"),
        "baseline_sha256": lock.get("baseline_sha256"),
        "protected_sha256": lock.get("protected_sha256"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    freeze_parser = sub.add_parser("freeze")
    freeze_parser.add_argument("source", type=Path)
    freeze_parser.add_argument("--baseline", type=Path, required=True)
    freeze_parser.add_argument("--lock", type=Path, required=True)
    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument("--baseline", type=Path, required=True)
    verify_parser.add_argument("--lock", type=Path, required=True)
    verify_parser.add_argument("--calibrated", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = (
            freeze(args.source, args.baseline, args.lock)
            if args.command == "freeze"
            else verify(args.baseline, args.lock, args.calibrated)
        )
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "ok", **result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
