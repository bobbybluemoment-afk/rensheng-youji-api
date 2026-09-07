from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.audit_ai_stage_contracts import audit


ROOT = Path(__file__).resolve().parents[1]


class AiStageContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads((ROOT / "internal/pipeline-contract.json").read_text(encoding="utf-8"))

    def test_all_ai_stages_have_discoverable_output_contracts(self) -> None:
        self.assertEqual(audit(ROOT, copy.deepcopy(self.contract)), [])

    def test_missing_method_prompt_builder_is_detected(self) -> None:
        contract = copy.deepcopy(self.contract)
        stage = next(item for item in contract["stages"] if item["id"] == "method_prompt_packs")
        stage.pop("script")
        self.assertTrue(any("短提示生成器" in item for item in audit(ROOT, contract)))

    def test_missing_ai_output_contract_is_detected(self) -> None:
        contract = copy.deepcopy(self.contract)
        stage = next(item for item in contract["stages"] if item["id"] == "report_semantics")
        stage.pop("output_contract")
        self.assertTrue(any("output_contract" in item for item in audit(ROOT, contract)))


if __name__ == "__main__":
    unittest.main()
