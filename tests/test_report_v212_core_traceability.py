from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from apply_calibration_delta import apply_patch
from audit_claim_diversity import audit as audit_diversity
from audit_report_claim_coverage import audit as audit_coverage
from audit_skill_references import audit as audit_skill_references
from core_baseline import digest, protected_projection


class ReportV212CoreTraceabilityTest(unittest.TestCase):
    def test_every_declared_skill_reference_exists(self) -> None:
        self.assertEqual(audit_skill_references(ROOT), [])

    def test_calibration_patch_cannot_rewrite_core_claim(self) -> None:
        baseline = {
            "analysis_meta": {"analysis_id": "a-1", "core_version": "0.8.1"},
            "reality_candidate_pool": [{"candidate_id": "cand-1", "status": "unverified", "text": "候选"}],
            "report_claim_ledger": [{"claim_id": "claim-1", "plain_claim": "你会先核对职责，再决定是否继续投入。", "calibration_status": "unverified"}],
            "evidence_registry": [{"evidence_id": "ev-1", "source_layer": "chart"}],
            "report_source_bundle": {"life_narrative_source": {"mandatory_claim_ids": ["claim-1"]}},
        }
        lock = {
            "analysis_id": "a-1",
            "core_version": "0.8.1",
            "baseline_sha256": digest(baseline),
            "protected_sha256": digest(protected_projection(baseline)),
        }
        delta = {
            "schema_version": "1.0.0",
            "analysis_id": "a-1",
            "baseline_sha256": lock["baseline_sha256"],
            "candidate_updates": [{"candidate_id": "cand-1", "status": "match"}],
            "claim_updates": [],
            "user_fact_evidence": [],
            "responses": [{"question_id": "q1", "selected_value": "A"}],
        }
        calibrated = apply_patch(baseline, lock, delta)
        self.assertEqual(calibrated["report_claim_ledger"][0]["plain_claim"], baseline["report_claim_ledger"][0]["plain_claim"])
        self.assertEqual(calibrated["reality_candidate_pool"][0]["status"], "match")
        tampered = copy.deepcopy(calibrated)
        tampered["report_claim_ledger"][0]["plain_claim"] = "用户选了A，所以整份报告只围绕这一点。"
        self.assertNotEqual(digest(protected_projection(tampered)), lock["protected_sha256"])

    def test_mandatory_claim_must_exist_verbatim_in_draft_and_report(self) -> None:
        sentence = "你可以接受家庭帮助，但会同时衡量这份帮助是否影响自己的决定权。"
        analysis = {"report_claim_ledger": [{"claim_id": "family-1", "plain_claim": sentence}]}
        brief_section = {"mandatory_claim_ids": ["family-1"]}
        realized = {"paragraphs": [sentence + "这会影响你与父母讨论城市和工作时的方式。"], "claim_realization_map": [{"claim_id": "family-1", "paragraph_index": 0, "exact_span": sentence}]}
        brief = {"life_overview": brief_section, "current_question": brief_section, "dimensions": []}
        draft = {"life_overview": realized, "current_question": realized, "dimensions": []}
        report = {"executive_summary": {"life_overview": realized}, "current_question_narrative": realized, "dimensions": []}
        self.assertEqual(audit_coverage(analysis, brief, draft, report), [])
        broken = copy.deepcopy(report)
        broken["current_question_narrative"]["paragraphs"] = ["你会考虑家庭意见，但仍想自己决定。"]
        self.assertTrue(any("未真实进入" in item or "not present" in item for item in audit_coverage(analysis, brief, draft, broken)))

    def test_diversity_audit_rejects_paraphrased_claim_counts(self) -> None:
        domains = {"self_growth", "love_partner", "career", "finance_resources", "body_emotion", "family_growth"}
        claims = []
        for domain in domains:
            for index in range(4):
                claims.append({
                    "claim_id": f"{domain}-{index}",
                    "domain": domain,
                    "claim_family": f"family-{index % 3}",
                    "mechanism_family": f"mechanism-{index % 2}",
                    "reality_dimension": f"axis-{index % 3}",
                    "new_information": f"新增信息-{domain}-{index}",
                    "plain_claim": "你遇到事情时会先整理信息，然后再开始行动。",
                    "claim": "你遇到事情时会先整理信息，然后再开始行动。",
                })
        source = {"claim_ids": [claims[0]["claim_id"]], "mandatory_claim_ids": [claims[0]["claim_id"]]}
        data = {
            "report_claim_ledger": claims,
            "report_source_bundle": {
                "life_narrative_source": source,
                "current_stage_source": source,
                "dimensions": {domain: source for domain in domains},
            },
        }
        errors = audit_diversity(data)
        self.assertTrue(any("repetitive" in item for item in errors))


if __name__ == "__main__":
    unittest.main()
