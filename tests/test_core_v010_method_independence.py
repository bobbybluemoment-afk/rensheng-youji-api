from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "internal/rensheng-youji-mingli-core/scripts"))

from validate_analysis_output import self_test_fixture, validate  # noqa: E402


class CoreV010MethodIndependenceTest(unittest.TestCase):
    def test_complete_independent_method_fixture_passes(self) -> None:
        self.assertEqual(validate(self_test_fixture()), [])

    def test_missing_required_method_family_fails(self) -> None:
        analysis = self_test_fixture()
        analysis["independent_method_analyses"] = [
            item for item in analysis["independent_method_analyses"]
            if item["method_id"] != "climate_adjustment"
        ]
        errors = validate(analysis)
        self.assertTrue(any("11个规定方法家族" in item or "缺少方法家族" in item for item in errors))

    def test_method_cannot_read_another_method_result(self) -> None:
        analysis = self_test_fixture()
        analysis["independent_method_analyses"][0]["source_method_ids_read"] = ["ten_god_dynamics"]
        errors = validate(analysis)
        self.assertTrue(any("独立方法不得读取其他方法结论" in item for item in errors))

    def test_independence_group_cannot_be_renamed_to_inflate_votes(self) -> None:
        analysis = self_test_fixture()
        analysis["independent_method_analyses"][0]["independence_group"] = "invented_extra_vote"
        errors = validate(analysis)
        self.assertTrue(any("independence_group 必须为pattern_organization" in item for item in errors))

    def test_method_input_cannot_point_to_report_or_calibration_results(self) -> None:
        analysis = self_test_fixture()
        method = analysis["independent_method_analyses"][0]
        method["input_fact_refs"] = ["report_claim_ledger.0"]
        method["technical_conclusions"][0]["chart_refs"] = ["report_claim_ledger.0"]
        errors = validate(analysis)
        self.assertTrue(any("只能引用冻结事实" in item for item in errors))

    def test_method_cannot_borrow_another_method_evidence(self) -> None:
        analysis = self_test_fixture()
        method = analysis["independent_method_analyses"][0]
        method["technical_conclusions"][0]["evidence_ids"] = ["evidence_3"]
        errors = validate(analysis)
        self.assertTrue(any("引用了其他方法的证据" in item for item in errors))

    def test_one_method_cannot_be_promoted_to_primary_consensus(self) -> None:
        analysis = self_test_fixture()
        cluster = analysis["method_synthesis"]["clusters"][0]
        cluster["member_hypothesis_ids"] = ["mh_pattern_structure_1"]
        cluster["supporting_method_ids"] = ["pattern_structure"]
        cluster["independence_groups"] = ["pattern_organization"]
        errors = validate(analysis)
        self.assertTrue(any("primary判断至少需要两个主要方法家族独立同向" in item for item in errors))

    def test_same_direction_cluster_requires_the_same_normalized_direction(self) -> None:
        analysis = self_test_fixture()
        hypothesis = analysis["independent_method_analyses"][0]["reality_hypotheses"][0]
        hypothesis["normalized_direction"] = "被人为改写的不同方向"
        errors = validate(analysis)
        self.assertTrue(any("same_direction成员必须使用相同标准化现实方向" in item for item in errors))

    def test_auxiliary_role_cannot_hide_primary_method_support(self) -> None:
        analysis = self_test_fixture()
        cluster = analysis["method_synthesis"]["clusters"][0]
        cluster["report_role"] = "auxiliary_only"
        analysis["method_synthesis"]["primary_synthesis_ids"].remove(cluster["synthesis_id"])
        analysis["method_synthesis"]["auxiliary_only_synthesis_ids"].append(cluster["synthesis_id"])
        errors = validate(analysis)
        self.assertTrue(any("auxiliary_only只能由神煞或纳音辅助方法支持" in item for item in errors))

    def test_single_primary_method_supplement_is_allowed(self) -> None:
        analysis = self_test_fixture()
        supplemental = next(
            item for item in analysis["method_synthesis"]["clusters"]
            if item["synthesis_id"] == "syn_supplemental"
        )
        self.assertEqual(supplemental["supporting_method_ids"], ["blind_school"])
        self.assertEqual(supplemental["report_role"], "supplemental")
        self.assertEqual(validate(analysis), [])

    def test_primary_report_claim_cannot_use_one_method(self) -> None:
        analysis = self_test_fixture()
        claim = copy.deepcopy(analysis["report_claim_ledger"][0])
        claim["method_hypothesis_ids"] = ["mh_blind_school_2"]
        claim["supporting_methods"] = ["blind_school"]
        claim["synthesis_ids"] = ["syn_supplemental"]
        claim["evidence_ids"] = ["evidence_11", "evidence_12"]
        analysis["report_claim_ledger"][0] = claim
        errors = validate(analysis)
        self.assertTrue(any("primary判断至少需要两个独立主要方法家族" in item for item in errors))


if __name__ == "__main__":
    unittest.main()
