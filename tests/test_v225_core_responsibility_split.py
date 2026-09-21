from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "internal/rensheng-youji-mingli-core/scripts"))

from core_semantic_contract import COMPILER_OWNED_FIELDS, build_ai_schema, compile_bookkeeping  # noqa: E402
from core_synthesis_contract import SEMANTIC_SECTIONS  # noqa: E402


class CoreResponsibilitySplitTest(unittest.TestCase):
    def test_ai_schema_hides_all_compiler_owned_fields(self) -> None:
        schema = build_ai_schema(SEMANTIC_SECTIONS)
        for definition, fields in COMPILER_OWNED_FIELDS.items():
            properties = set(schema["$defs"][definition].get("properties") or {})
            self.assertFalse(properties & set(fields))

    def test_official_probe_mode_only_enables_selected_candidates(self) -> None:
        semantic = {
            "method_synthesis": {"clusters": []},
            "report_claim_ledger": [{
                "claim_id": "claim_1", "claim_class": "calibration_pending",
                "claim_family": "选择方式", "reality_dimension": "decision",
                "method_hypothesis_ids": [], "source_detail_atom_ids": [],
            }],
            "reality_candidate_pool": [{
                "candidate_id": "c1", "candidate_kind": "objective_state",
                "time_scope": "当前", "statement": "你会先比较几个标准再决定。",
                "alternative_statement": "你通常很快决定。", "related_claim_ids": ["claim_1"],
            }, {
                "candidate_id": "c2", "candidate_kind": "stable_pattern",
                "time_scope": "长期", "statement": "你喜欢独立处理。",
                "alternative_statement": "你更常主动求助。", "related_claim_ids": ["claim_1"],
            }],
            "candidate_relation_map": [],
        }
        probes = {"c1": {
            "answerable_time_scope": "当前",
            "answerable_observation": "你会先比较几个标准再决定。",
            "answerable_alternative": "你通常很快决定。",
        }}
        result = compile_bookkeeping(copy.deepcopy(semantic), [], [], [], 2026, probes)
        candidates = {item["candidate_id"]: item for item in result["reality_candidate_pool"]}
        self.assertTrue(candidates["c1"]["validation_question"])
        self.assertEqual(candidates["c2"]["validation_question"], "")

    def test_legacy_direct_mode_keeps_a_default_probe(self) -> None:
        semantic = {
            "method_synthesis": {"clusters": []}, "report_claim_ledger": [],
            "reality_candidate_pool": [{
                "candidate_id": "c1", "candidate_kind": "stable_pattern", "time_scope": "长期",
                "statement": "你会先比较再决定。", "alternative_statement": "你通常很快决定。",
                "related_claim_ids": [],
            }], "candidate_relation_map": [],
        }
        result = compile_bookkeeping(copy.deepcopy(semantic), [], [], [], 2026, None)
        self.assertTrue(result["reality_candidate_pool"][0]["validation_question"])


if __name__ == "__main__":
    unittest.main()
