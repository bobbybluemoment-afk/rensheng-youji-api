from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "internal/rensheng-youji-mingli-core/scripts"))

from adapter_from_api_profile import adapt_profile  # noqa: E402
from core_synthesis_contract import ALL_METHODS, LOVE_PARTNER_ANCHORS  # noqa: E402
from method_input_contract import build_method_input, canonical_digest  # noqa: E402
from finalize_core_analysis import assemble  # noqa: E402
from prepare_core_synthesis import prepare  # noqa: E402
from rensheng_youji.local_engine import build_profile  # noqa: E402
from validate_analysis_output import self_test_fixture  # noqa: E402


DETERMINISTIC = {
    "analysis_meta", "chart_facts", "chart_audit", "independent_method_analyses",
    "method_execution_audit", "source_coverage_audit", "evidence_registry", "report_source_bundle",
    "calibration_state", "calibration_delta",
}


def sync_domain_assessments(method: dict) -> None:
    for assessment in method["domain_assessments"]:
        domain = assessment["domain"]
        ids = [
            item["hypothesis_id"] for item in method["reality_hypotheses"]
            if item["domain"] == domain
        ]
        assessment["hypothesis_ids"] = ids
        assessment["status"] = (
            "supported" if ids
            else "insufficient_evidence"
            if domain == "love_partner" and method["method_id"] in LOVE_PARTNER_ANCHORS
            else "not_applicable"
        )


def production_fixture() -> tuple[dict, list[dict], dict]:
    profile = build_profile(
        name="",
        birth="1999-01-22 17:45",
        gender="male",
        city="福建泉州",
        time_basis="local_civil",
        center_year=2026,
    )
    analysis_input = adapt_profile(profile, analysis_as_of="2026-08-31")
    analysis_input["request"]["target_range"] = {"start_year": 2026, "end_year": 2026}
    analysis_input["annual_cycles"] = [item for item in analysis_input["annual_cycles"] if item["year"] == 2026]
    method_input_sha256 = canonical_digest(build_method_input(analysis_input))
    fixture = self_test_fixture()
    evidence = {item["evidence_id"]: item for item in fixture["evidence_registry"]}
    packets = []
    for method in fixture["independent_method_analyses"]:
        method["method_input_sha256"] = method_input_sha256
        evidence_ids = {
            evidence_id
            for conclusion in method["technical_conclusions"]
            for evidence_id in conclusion["evidence_ids"]
        }
        packets.append({
            "method_analysis": copy.deepcopy(method),
            "evidence_registry": [copy.deepcopy(evidence[evidence_id]) for evidence_id in sorted(evidence_ids)],
        })
    semantic = copy.deepcopy({key: value for key, value in fixture.items() if key not in DETERMINISTIC})
    for index, candidate in enumerate(semantic["reality_candidate_pool"]):
        candidate["evidence_ids"] = [f"evidence_{index % 16 + 1}"]
    return analysis_input, packets, semantic


class CoreV012ProductionBridgeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.analysis_input, cls.packets, cls.semantic = production_fixture()

    def test_contract_contains_exactly_nine_methods_without_auxiliaries(self) -> None:
        self.assertEqual(len(ALL_METHODS), 9)
        self.assertNotIn("nayin", self.analysis_input["chart"])
        self.assertNotIn("shen_sha", self.analysis_input["chart"])

    def test_pre_adjusted_true_solar_input_keeps_location_metadata(self) -> None:
        profile = build_profile(
            name="",
            birth="1999-01-22 17:28",
            gender="male",
            city="福建泉州",
            time_basis="true_solar_adjusted",
            center_year=2026,
        )
        adapted = adapt_profile(profile, analysis_as_of="2026-08-31")
        self.assertTrue(adapted["solar_terms_and_boundaries"]["true_solar_time_applied"])
        self.assertIsInstance(profile["time"]["longitude"], float)
        self.assertTrue(profile["time"]["timezone"])
        self.assertNotIn("nayin", adapted["chart"])
        self.assertNotIn("shen_sha", adapted["chart"])

    def test_prepare_builds_a_full_immutable_synthesis_input(self) -> None:
        synthesis = prepare(copy.deepcopy(self.analysis_input), copy.deepcopy(self.packets))
        self.assertEqual(len(synthesis["independent_method_analyses"]), 9)
        self.assertEqual(synthesis["method_execution_audit"]["delivery_decision"], "full")
        self.assertEqual(synthesis["method_execution_audit"]["excluded_method_ids"], [])
        self.assertEqual(synthesis["source_coverage_audit"]["status"], "ready")
        self.assertTrue(synthesis["source_coverage_audit"]["love_partner_anchor_review_complete"])
        self.assertTrue(synthesis["source_coverage_audit"]["topic_isolation_required"])

    def test_method_input_removes_reality_and_calibration_but_keeps_chart(self) -> None:
        source = copy.deepcopy(self.analysis_input)
        source["reality_context"] = {
            "facts": [{"fact_id": "fact_1", "domain": "career", "statement": "当前关注事业", "time_scope": "current", "source": "user", "confidence": "confirmed"}],
            "questions": ["事业发展"],
            "current_concerns": ["事业发展"],
        }
        source["calibration"]["rejected_claims"] = ["旧判断"]
        isolated = build_method_input(source)
        self.assertEqual(isolated["reality_context"], {"facts": [], "questions": []})
        self.assertEqual(isolated["calibration"]["rejected_claims"], [])
        self.assertEqual(isolated["chart"], source["chart"])

    def test_core_synthesis_removes_focus_but_keeps_factual_context(self) -> None:
        source = copy.deepcopy(self.analysis_input)
        source["reality_context"]["occupation"] = "项目经理"
        source["reality_context"]["questions"] = ["事业发展"]
        source["reality_context"]["current_concerns"] = ["事业发展"]
        synthesis = prepare(source, copy.deepcopy(self.packets))
        self.assertEqual(synthesis["analysis_input"]["reality_context"]["questions"], [])
        self.assertEqual(synthesis["analysis_input"]["reality_context"]["current_concerns"], [])
        self.assertEqual(synthesis["analysis_input"]["reality_context"]["occupation"], "项目经理")

    def test_prepare_rejects_packet_from_another_method_input(self) -> None:
        packets = copy.deepcopy(self.packets)
        packets[0]["method_analysis"]["method_input_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "method_input_sha256"):
            prepare(copy.deepcopy(self.analysis_input), packets)

    def test_uncovered_report_domain_becomes_a_source_gap_not_a_pipeline_stop(self) -> None:
        packets = copy.deepcopy(self.packets)
        for packet in packets:
            for hypothesis in packet["method_analysis"]["reality_hypotheses"]:
                if hypothesis["domain"] == "love_partner":
                    hypothesis["domain"] = "self_growth"
            sync_domain_assessments(packet["method_analysis"])
        synthesis = prepare(copy.deepcopy(self.analysis_input), packets)
        self.assertEqual(synthesis["source_coverage_audit"]["status"], "ready_with_gaps")
        self.assertIn("love_partner", synthesis["source_coverage_audit"]["uncovered_report_domains"])

    def test_source_gap_can_finish_core_without_inventing_domain_material(self) -> None:
        packets = copy.deepcopy(self.packets)
        semantic = copy.deepcopy(self.semantic)
        for packet in packets:
            for hypothesis in packet["method_analysis"]["reality_hypotheses"]:
                if hypothesis["domain"] == "love_partner":
                    hypothesis["domain"] = "self_growth"
            sync_domain_assessments(packet["method_analysis"])
        synthesis = prepare(copy.deepcopy(self.analysis_input), packets)

        removed_synthesis_ids = {
            item["synthesis_id"] for item in semantic["method_synthesis"]["clusters"]
            if item["domain"] == "love_partner"
        }
        semantic["method_synthesis"]["clusters"] = [
            item for item in semantic["method_synthesis"]["clusters"]
            if item["synthesis_id"] not in removed_synthesis_ids
        ]
        for key in ("primary_synthesis_ids", "supplemental_synthesis_ids", "to_verify_synthesis_ids"):
            semantic["method_synthesis"][key] = [
                item for item in semantic["method_synthesis"][key]
                if item not in removed_synthesis_ids
            ]
        semantic["report_claim_ledger"] = [
            item for item in semantic["report_claim_ledger"]
            if item["domain"] != "love_partner"
        ]
        valid_claim_ids = {item["claim_id"] for item in semantic["report_claim_ledger"]}
        fallback_claim_id = sorted(valid_claim_ids)[0]
        removed_candidate_ids = {
            item["candidate_id"] for item in semantic["reality_candidate_pool"]
            if item["domain"] == "love_partner"
        }
        semantic["reality_candidate_pool"] = [
            item for item in semantic["reality_candidate_pool"]
            if item["candidate_id"] not in removed_candidate_ids
        ]
        for candidate in semantic["reality_candidate_pool"]:
            candidate["related_claim_ids"] = [
                item for item in candidate["related_claim_ids"] if item in valid_claim_ids
            ] or [fallback_claim_id]
        for relation in semantic["candidate_relation_map"]:
            relation["candidate_ids"] = [
                item for item in relation["candidate_ids"] if item not in removed_candidate_ids
            ]
        for domain in ("relationships", "partner", "interaction"):
            semantic["portrait_balance_audit"]["covered_domains"].remove(domain)
            semantic["portrait_balance_audit"]["weak_domains"].append(domain)

        final, errors = assemble(synthesis, semantic)
        self.assertEqual(errors, [])
        self.assertEqual(final["source_coverage_audit"]["status"], "ready_with_gaps")
        self.assertEqual(final["report_source_bundle"]["dimensions"]["love_partner"]["claim_ids"], [])
        self.assertTrue(final["report_source_bundle"]["dimensions"]["love_partner"]["evidence_gaps"])

    def test_prepare_rejects_a_missing_method_packet(self) -> None:
        with self.assertRaisesRegex(ValueError, "必须提供9个规定方法包"):
            prepare(copy.deepcopy(self.analysis_input), copy.deepcopy(self.packets[:-1]))

    def test_semantic_output_cannot_overwrite_deterministic_sections(self) -> None:
        synthesis = prepare(copy.deepcopy(self.analysis_input), copy.deepcopy(self.packets))
        semantic = copy.deepcopy(self.semantic)
        semantic["chart_facts"] = {"pillars": "tampered"}
        _, errors = assemble(synthesis, semantic)
        self.assertTrue(any("禁止或未知区块" in item for item in errors))

    def test_tampered_synthesis_input_is_rejected(self) -> None:
        synthesis = prepare(copy.deepcopy(self.analysis_input), copy.deepcopy(self.packets))
        synthesis["analysis_input"]["request"]["request_id"] = "tampered"
        _, errors = assemble(synthesis, copy.deepcopy(self.semantic))
        self.assertTrue(any("analysis_input_sha256" in item for item in errors))

    def test_tampered_method_packets_are_rejected(self) -> None:
        synthesis = prepare(copy.deepcopy(self.analysis_input), copy.deepcopy(self.packets))
        synthesis["independent_method_analyses"][0]["limitations"].append("tampered")
        _, errors = assemble(synthesis, copy.deepcopy(self.semantic))
        self.assertTrue(any("method_packets_sha256" in item for item in errors))

    def test_full_production_bridge_is_deterministic_and_valid(self) -> None:
        synthesis = prepare(copy.deepcopy(self.analysis_input), copy.deepcopy(self.packets))
        first, first_errors = assemble(synthesis, copy.deepcopy(self.semantic))
        second, second_errors = assemble(copy.deepcopy(synthesis), copy.deepcopy(self.semantic))
        self.assertEqual(first_errors, [])
        self.assertEqual(second_errors, [])
        self.assertEqual(first, second)
        self.assertIn("report_source_bundle", first)
        self.assertEqual(first["analysis_meta"]["core_version"], "0.15.0")

    def test_documented_cli_bridge_writes_a_complete_core(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rensheng-youji-core-bridge-") as temp_dir:
            work = Path(temp_dir)
            packet_dir = work / "method-packets"
            packet_dir.mkdir()
            analysis_input = work / "analysis-input.json"
            synthesis_input = work / "core-synthesis-input.json"
            compiler_source = work / "core-compiler-source.json"
            semantic_output = work / "core-semantic-analysis.json"
            final_output = work / "analysis-output-initial.json"
            analysis_input.write_text(json.dumps(self.analysis_input, ensure_ascii=False), encoding="utf-8")
            semantic_output.write_text(json.dumps(self.semantic, ensure_ascii=False), encoding="utf-8")
            for packet in self.packets:
                method_id = packet["method_analysis"]["method_id"]
                (packet_dir / f"{method_id}.json").write_text(
                    json.dumps(packet, ensure_ascii=False), encoding="utf-8"
                )
            commands = [
                [sys.executable, str(ROOT / "scripts/prepare_core_synthesis.py"), str(analysis_input), "--method-packet-dir", str(packet_dir), "--output", str(synthesis_input), "--compiler-source", str(compiler_source)],
                [sys.executable, str(ROOT / "scripts/validate_core_synthesis.py"), str(synthesis_input), str(semantic_output), "--compiler-source", str(compiler_source)],
                [sys.executable, str(ROOT / "scripts/finalize_core_analysis.py"), str(synthesis_input), str(semantic_output), "--compiler-source", str(compiler_source), "--output", str(final_output)],
            ]
            for command in commands:
                result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
                self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            final = json.loads(final_output.read_text(encoding="utf-8"))
            self.assertEqual(final["analysis_meta"]["status"], "complete")
            self.assertEqual(len(final["independent_method_analyses"]), 9)
            self.assertIn("report_source_bundle", final)


if __name__ == "__main__":
    unittest.main()
