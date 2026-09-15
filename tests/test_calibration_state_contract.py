from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "internal/rensheng-youji-mingli-core/scripts"))

from calibration_state_contract import pre_freeze_pending_claim_errors  # noqa: E402
from core_baseline import freeze  # noqa: E402
from validate_analysis_output import self_test_fixture, validate  # noqa: E402


def analysis_with_pending_claim() -> dict:
    analysis = self_test_fixture()
    claim = analysis["report_claim_ledger"][0]
    claim.update({
        "claim_class": "calibration_pending",
        "report_role": "to_verify",
        "confidence": "to_verify",
        "calibration_status": "unverified",
    })
    return analysis


def claim_update(claim: dict, status: str) -> dict:
    return {
        "claim_id": claim["claim_id"],
        "before_status": "unverified",
        "after_status": status,
        "reason": "用户的校准答案更新了这条现实判断",
        "user_fact_evidence_ids": [],
        "rewritten_reality_claim": claim["plain_claim"],
        "preserves_chart_mechanism": True,
    }


class CalibrationStateContractTest(unittest.TestCase):
    def test_calibrated_pending_claim_is_valid_when_delta_matches(self) -> None:
        analysis = analysis_with_pending_claim()
        claim = analysis["report_claim_ledger"][0]
        claim["calibration_status"] = "match"
        analysis["calibration_delta"]["claim_updates"] = [claim_update(claim, "match")]

        errors = validate(analysis)

        self.assertFalse(any("待校准判断在冻结前" in item for item in errors))
        self.assertFalse(any("校准后状态" in item or "校准增量" in item for item in errors))

    def test_changed_claim_status_requires_a_matching_delta_record(self) -> None:
        analysis = analysis_with_pending_claim()
        analysis["report_claim_ledger"][0]["calibration_status"] = "weakened"

        errors = validate(analysis)

        self.assertTrue(any("缺少calibration_delta.claim_updates记录" in item for item in errors))

    def test_delta_after_status_must_match_claim_ledger(self) -> None:
        analysis = analysis_with_pending_claim()
        claim = analysis["report_claim_ledger"][0]
        claim["calibration_status"] = "match"
        analysis["calibration_delta"]["claim_updates"] = [claim_update(claim, "weakened")]

        errors = validate(analysis)

        self.assertTrue(any("calibration_status与校准增量after_status不一致" in item for item in errors))

    def test_freeze_contract_rejects_a_prematurely_calibrated_pending_claim(self) -> None:
        analysis = analysis_with_pending_claim()
        premature = copy.deepcopy(analysis)
        premature["report_claim_ledger"][0]["calibration_status"] = "match"

        self.assertFalse(pre_freeze_pending_claim_errors(analysis["report_claim_ledger"]))
        self.assertTrue(pre_freeze_pending_claim_errors(premature["report_claim_ledger"]))

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "analysis-output-initial.json"
            source.write_text(json.dumps(premature, ensure_ascii=False), encoding="utf-8")
            with patch("core_baseline.validate_core"), patch(
                "core_baseline.validate_quality_audit",
                return_value={"schema_version": "1.0.0", "status": "ok", "errors": []},
            ):
                with self.assertRaisesRegex(ValueError, "待校准判断在冻结前"):
                    freeze(
                        source,
                        root / "analysis-baseline.json",
                        root / "analysis-baseline-lock.json",
                        root / "core-quality-audit.json",
                    )


if __name__ == "__main__":
    unittest.main()
