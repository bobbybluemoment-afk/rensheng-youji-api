from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "internal/rensheng-youji-mingli-core/scripts"))
sys.path.insert(0, str(ROOT / "internal/rensheng-youji-report-content-brief/scripts"))
sys.path.insert(0, str(ROOT / "internal/rensheng-youji-report-writer/scripts"))

from apply_calibration_delta import apply_patch  # noqa: E402
from core_baseline import digest, protected_projection  # noqa: E402
from materialize_content_brief import materialize  # noqa: E402
from resolve_report_sources import resolve  # noqa: E402
from validate_analysis_output import self_test_fixture, validate as validate_analysis  # noqa: E402
from validate_content_brief import validate as validate_brief  # noqa: E402
from validate_report_draft import check_section  # noqa: E402


DIMENSIONS = ["self_growth", "love_partner", "career", "finance_resources", "body_emotion", "family_growth"]


def locked_fixture() -> tuple[dict, dict]:
    baseline = self_test_fixture()
    lock = {
        "analysis_id": baseline["analysis_meta"]["analysis_id"],
        "core_version": baseline["analysis_meta"]["core_version"],
        "baseline_sha256": digest(baseline),
        "protected_sha256": digest(protected_projection(baseline)),
    }
    return baseline, lock


def selection_fixture() -> dict:
    section = lambda: {"claim_ids": [], "allowed_examples": [], "prohibited_claims": []}
    return {
        "schema_version": "selection-1.0",
        "brief_id": "brief-v213-test",
        "source": {},
        "focus_scope": {"protected_sections": ["life_overview", "dimensions"]},
        "life_overview": section(),
        "dimensions": [{"id": domain, **section()} for domain in DIMENSIONS],
        "current_question": section(),
        "calibration_internal": {"rejected_claim_ids": []},
    }


class ReportV213PostCalibrationSelectionTest(unittest.TestCase):
    def test_core_requires_an_explicit_gap_when_shared_coverage_is_missing(self) -> None:
        analysis = self_test_fixture()
        source = analysis["report_source_bundle"]["dimensions"]["career"]
        source["coverage"].remove("response")
        source["coverage_claim_map"].pop("response")
        errors = validate_analysis(analysis)
        self.assertTrue(any("evidence_gaps" in item for item in errors))

    def test_rejected_mandatory_candidate_is_replaced_without_mutating_baseline(self) -> None:
        baseline, lock = locked_fixture()
        delta = {
            "schema_version": "1.0.0",
            "analysis_id": lock["analysis_id"],
            "baseline_sha256": lock["baseline_sha256"],
            "candidate_updates": [],
            "claim_updates": [{
                "claim_id": "claim_self_33",
                "after_status": "reject",
                "reason": "用户明确否定这条身体反应候选",
                "user_fact_evidence_ids": [],
            }],
            "user_fact_evidence": [],
            "responses": [],
        }
        calibrated = apply_patch(baseline, lock, delta)
        self.assertEqual(digest(protected_projection(calibrated)), lock["protected_sha256"])
        resolved = resolve(calibrated)
        body = resolved["dimensions"]["body_emotion"]
        self.assertEqual(body["delivery_mode"], "normal")
        self.assertNotIn("claim_self_33", body["claim_ids"])
        self.assertNotIn("claim_self_33", body["mandatory_claim_ids"])
        self.assertFalse(body["missing_coverage"])

    def test_multiple_rejections_degrade_only_the_affected_section(self) -> None:
        analysis = self_test_fixture()
        for claim in analysis["report_claim_ledger"]:
            if claim["claim_id"] in {"claim_self_33", "claim_self_34"}:
                claim["calibration_status"] = "reject"
        resolved = resolve(analysis)
        self.assertEqual(resolved["dimensions"]["body_emotion"]["delivery_mode"], "shortened")
        self.assertTrue(resolved["dimensions"]["body_emotion"]["missing_coverage"])
        self.assertEqual(resolved["dimensions"]["career"]["delivery_mode"], "normal")

    def test_materialized_brief_uses_resolved_sources_and_excludes_rejected_claim(self) -> None:
        analysis = self_test_fixture()
        for claim in analysis["report_claim_ledger"]:
            if claim["claim_id"] == "claim_self_33":
                claim["calibration_status"] = "reject"
        resolved = resolve(analysis)
        brief = materialize(selection_fixture(), analysis, resolved)
        body = next(item for item in brief["dimensions"] if item["id"] == "body_emotion")
        self.assertNotIn("claim_self_33", body["claim_ids"])
        self.assertEqual(body["delivery_mode"], "normal")
        self.assertEqual(validate_brief(brief, analysis, resolved), [])

    def test_tampered_resolved_sources_are_rejected(self) -> None:
        analysis = self_test_fixture()
        resolved = resolve(analysis)
        brief = materialize(selection_fixture(), analysis, resolved)
        tampered = copy.deepcopy(resolved)
        tampered["dimensions"]["career"]["claim_ids"].pop()
        errors = validate_brief(brief, analysis, tampered)
        self.assertTrue(any("哈希无效" in item or "来源不一致" in item for item in errors))

    def test_writer_accepts_section_level_degradation_without_padding(self) -> None:
        minimal_text = "你目前只能确认少数稳定表现，因此这一部分只保留有来源的判断，不再用相似说法补足篇幅。" * 6
        minimal = {
            "delivery_mode": "minimal",
            "paragraphs": [minimal_text],
            "source_claim_ids": ["claim-1", "claim-2"],
            "paragraph_claim_map": [["claim-1", "claim-2"]],
        }
        errors: list[str] = []
        check_section(minimal, 0, 0, "minimal", errors, True, True)
        self.assertEqual(errors, [])

        gap_text = "现有信息不足以支持这一领域的完整判断。本节暂不补写常见描述，后续可结合真实经历继续核对。" * 2
        evidence_gap = {
            "delivery_mode": "evidence_gap",
            "paragraphs": [gap_text],
            "source_claim_ids": [],
            "paragraph_claim_map": [[]],
        }
        errors = []
        check_section(evidence_gap, 0, 0, "evidence_gap", errors, True, True)
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
