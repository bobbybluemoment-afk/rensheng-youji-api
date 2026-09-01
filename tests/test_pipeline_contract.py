from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_pipeline_contract import audit  # noqa: E402


class PipelineContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads((ROOT / "internal/pipeline-contract.json").read_text(encoding="utf-8"))

    def test_complete_pipeline_has_no_unproduced_internal_inputs(self) -> None:
        self.assertEqual(audit(ROOT, copy.deepcopy(self.contract)), [])

    def test_missing_bridge_output_is_detected(self) -> None:
        contract = copy.deepcopy(self.contract)
        stage = next(item for item in contract["stages"] if item["id"] == "synthesis_input")
        stage["outputs"] = []
        errors = audit(ROOT, contract)
        self.assertTrue(any("没有声明输出" in item or "没有上游生产者" in item for item in errors))

    def test_ai_stage_without_contract_is_detected(self) -> None:
        contract = copy.deepcopy(self.contract)
        stage = next(item for item in contract["stages"] if item["id"] == "semantic_synthesis")
        stage.pop("contract")
        self.assertTrue(any("没有Skill或参考契约" in item for item in audit(ROOT, contract)))

    def test_free_card_has_a_deterministic_assembler(self) -> None:
        stages = {item["id"]: item for item in self.contract["stages"]}
        self.assertEqual(stages["free_card_visual_series"]["producer"], "deterministic")
        self.assertEqual(
            stages["free_card_output"]["script"],
            "scripts/assemble_free_card.py",
        )
        self.assertIn("visual_series", stages["free_card_output"]["inputs"])

    def test_runtime_launcher_is_required(self) -> None:
        contract = copy.deepcopy(self.contract)
        contract.pop("runtime")
        self.assertTrue(any("runtime" in item for item in audit(ROOT, contract)))

    def test_method_packet_schema_and_scaffold_are_declared(self) -> None:
        stage = next(item for item in self.contract["stages"] if item["id"] == "independent_methods")
        self.assertEqual(
            stage["output_contract"],
            "internal/rensheng-youji-mingli-core/schemas/method-packet.schema.json",
        )
        self.assertEqual(stage["scaffold"], "scripts/initialize_method_packets.py")


if __name__ == "__main__":
    unittest.main()
