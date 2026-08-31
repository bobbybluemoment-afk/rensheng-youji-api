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
from core_synthesis_contract import ALL_METHODS  # noqa: E402
from finalize_core_analysis import assemble  # noqa: E402
from prepare_core_synthesis import prepare  # noqa: E402
from rensheng_youji.local_engine import build_profile  # noqa: E402
from validate_analysis_output import self_test_fixture  # noqa: E402


DETERMINISTIC = {
    "analysis_meta", "chart_facts", "chart_audit", "independent_method_analyses",
    "method_execution_audit", "evidence_registry", "report_source_bundle",
    "calibration_state", "calibration_delta",
}


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
    fixture = self_test_fixture()
    evidence = {item["evidence_id"]: item for item in fixture["evidence_registry"]}
    packets = []
    for method in fixture["independent_method_analyses"]:
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

    def test_full_production_bridge_is_deterministic_and_valid(self) -> None:
        synthesis = prepare(copy.deepcopy(self.analysis_input), copy.deepcopy(self.packets))
        first, first_errors = assemble(synthesis, copy.deepcopy(self.semantic))
        second, second_errors = assemble(copy.deepcopy(synthesis), copy.deepcopy(self.semantic))
        self.assertEqual(first_errors, [])
        self.assertEqual(second_errors, [])
        self.assertEqual(first, second)
        self.assertIn("report_source_bundle", first)
        self.assertEqual(first["analysis_meta"]["core_version"], "0.12.0")

    def test_documented_cli_bridge_writes_a_complete_core(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rensheng-youji-core-bridge-") as temp_dir:
            work = Path(temp_dir)
            packet_dir = work / "method-packets"
            packet_dir.mkdir()
            analysis_input = work / "analysis-input.json"
            synthesis_input = work / "core-synthesis-input.json"
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
                [sys.executable, str(ROOT / "scripts/prepare_core_synthesis.py"), str(analysis_input), "--method-packet-dir", str(packet_dir), "--output", str(synthesis_input)],
                [sys.executable, str(ROOT / "scripts/validate_core_synthesis.py"), str(synthesis_input), str(semantic_output)],
                [sys.executable, str(ROOT / "scripts/finalize_core_analysis.py"), str(synthesis_input), str(semantic_output), "--output", str(final_output)],
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
