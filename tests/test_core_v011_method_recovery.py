from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "internal/rensheng-youji-mingli-core/scripts"))
sys.path.insert(0, str(ROOT / "scripts"))

from build_report_source_bundle import build  # noqa: E402
from validate_analysis_output import (  # noqa: E402
    PRIMARY_METHODS,
    method_delivery_decision,
    self_test_fixture,
    validate as validate_core,
)
from validate_method_packet import validate as validate_packet  # noqa: E402
from resolve_report_sources import resolve  # noqa: E402


def method_packet(method_id: str) -> dict:
    analysis = self_test_fixture()
    method = next(item for item in analysis["independent_method_analyses"] if item["method_id"] == method_id)
    evidence_ids = {
        evidence_id
        for conclusion in method["technical_conclusions"]
        for evidence_id in conclusion["evidence_ids"]
    }
    evidence = [item for item in analysis["evidence_registry"] if item["evidence_id"] in evidence_ids]
    return {"method_analysis": copy.deepcopy(method), "evidence_registry": copy.deepcopy(evidence)}


class CoreV011MethodRecoveryTest(unittest.TestCase):
    def test_complete_primary_method_packet_passes(self) -> None:
        self.assertEqual(validate_packet(method_packet("pattern_structure"), "pattern_structure"), [])

    def test_illegal_reality_domain_fails_inside_method_packet(self) -> None:
        packet = method_packet("blind_school")
        packet["method_analysis"]["reality_hypotheses"][0]["domain"] = "social_relationship"
        errors = validate_packet(packet, "blind_school")
        self.assertTrue(any("domain无效：social_relationship" in item for item in errors))

    def test_method_packet_uses_formal_core_schema_constraints(self) -> None:
        packet = method_packet("blind_school")
        packet["method_analysis"]["technical_conclusions"][0]["conclusion_id"] = "bad-id"
        errors = validate_packet(packet, "blind_school")
        self.assertTrue(any("不符合正式Core Schema" in item and "pattern" in item for item in errors))

    def test_complete_method_must_review_all_eight_domains(self) -> None:
        packet = method_packet("pattern_structure")
        packet["method_analysis"]["domain_assessments"] = packet["method_analysis"]["domain_assessments"][:-1]
        errors = validate_packet(packet, "pattern_structure")
        self.assertTrue(any("逐项检查八个现实领域" in item for item in errors))

    def test_relationship_anchor_cannot_skip_love_partner_review(self) -> None:
        packet = method_packet("blind_school")
        assessment = next(
            item for item in packet["method_analysis"]["domain_assessments"]
            if item["domain"] == "love_partner"
        )
        assessment["status"] = "not_applicable"
        assessment["hypothesis_ids"] = []
        packet["method_analysis"]["reality_hypotheses"] = [
            item for item in packet["method_analysis"]["reality_hypotheses"]
            if item["domain"] != "love_partner"
        ]
        errors = validate_packet(packet, "blind_school")
        self.assertTrue(any("关系锚点方法" in item for item in errors))

    def test_generation_failure_requires_three_attempts(self) -> None:
        packet = method_packet("pattern_structure")
        method = packet["method_analysis"]
        method.update({
            "status": "generation_failed",
            "attempt_count": 2,
            "failure_reasons": ["两轮局部修复后仍未形成有效机制链"],
            "degradation_effects": ["格局法不参与综合计票"],
            "technical_conclusions": [],
            "reality_hypotheses": [],
            "domain_assessments": [],
        })
        packet["evidence_registry"] = []
        errors = validate_packet(packet, "pattern_structure")
        self.assertTrue(any("三轮局部修复" in item for item in errors))
        method["attempt_count"] = 3
        self.assertEqual(validate_packet(packet, "pattern_structure"), [])

    def test_delivery_decision_uses_anchor_coverage(self) -> None:
        self.assertEqual(method_delivery_decision(set(PRIMARY_METHODS))[0], "full")
        self.assertEqual(method_delivery_decision(set(PRIMARY_METHODS) - {"climate_adjustment"})[0], "degraded")
        self.assertEqual(method_delivery_decision(set(PRIMARY_METHODS) - {"climate_adjustment", "pattern_structure"})[0], "degraded")
        self.assertEqual(method_delivery_decision(set(PRIMARY_METHODS) - {"timing_continuity"})[0], "preliminary_only")

    def test_report_source_bundle_is_built_deterministically(self) -> None:
        analysis = self_test_fixture()
        first = build(analysis)
        second = build(copy.deepcopy(analysis))
        self.assertEqual(first, second)
        analysis["report_source_bundle"] = first
        self.assertEqual(validate_core(analysis), [])

    def test_single_method_supplement_can_use_one_evidence(self) -> None:
        analysis = self_test_fixture()
        claim = next(item for item in analysis["report_claim_ledger"] if item["claim_id"] == "claim_self_8")
        claim["evidence_ids"] = ["evidence_11"]
        self.assertEqual(validate_core(analysis), [])

    def test_preliminary_core_cannot_enter_formal_report_selection(self) -> None:
        analysis = self_test_fixture()
        analysis["method_execution_audit"]["delivery_decision"] = "preliminary_only"
        with self.assertRaisesRegex(ValueError, "preliminary_only"):
            resolve(analysis)

    def test_failed_blind_method_does_not_require_blind_outputs(self) -> None:
        analysis = self_test_fixture()
        method = next(item for item in analysis["independent_method_analyses"] if item["method_id"] == "blind_school")
        method.update({
            "status": "generation_failed",
            "attempt_count": 3,
            "failure_reasons": ["三轮局部修复后仍未形成完整做功链"],
            "degradation_effects": ["盲派不参与综合计票"],
            "technical_conclusions": [],
            "reality_hypotheses": [],
            "domain_assessments": [],
        })
        blind = analysis["blind_school_cross_analysis"]
        for key in ("source_boundaries", "host_guest_map", "body_function_map", "work_paths", "image_hypotheses", "reality_image_candidates", "virtual_real_completeness", "timing_activation", "agreements", "conflicts", "prohibited_extensions"):
            blind[key] = []
        errors = validate_core(analysis)
        self.assertFalse(any("至少包含四条现实取象" in item or "至少包含一条完整做功路径" in item for item in errors))

    def test_failed_root_method_does_not_require_root_outputs(self) -> None:
        analysis = self_test_fixture()
        method = next(item for item in analysis["independent_method_analyses"] if item["method_id"] == "root_seed_flower_fruit")
        method.update({
            "status": "generation_failed",
            "attempt_count": 3,
            "failure_reasons": ["三轮局部修复后仍未形成完整根苗花果链"],
            "degradation_effects": ["根苗花果不参与综合计票"],
            "technical_conclusions": [],
            "reality_hypotheses": [],
            "domain_assessments": [],
        })
        root_map = analysis["root_seed_flower_fruit_map"]
        root_map["continuity"] = []
        root_map["domain_lifecycles"] = []
        root_map["findings"] = []
        errors = validate_core(analysis)
        self.assertFalse(any("continuity 至少" in item or "domain_lifecycles 至少" in item for item in errors))


if __name__ == "__main__":
    unittest.main()
