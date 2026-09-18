from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "internal/rensheng-youji-mingli-core/scripts"))

from audit_core_semantic_contract import audit  # noqa: E402
from core_semantic_contract import (  # noqa: E402
    COMPILER_OWNED_FIELDS,
    build_ai_schema,
    compile_bookkeeping,
)
from core_synthesis_contract import SEMANTIC_SECTIONS  # noqa: E402
from prepare_semantic_repair import build, targets_from_errors  # noqa: E402


class CoreSemanticContractTest(unittest.TestCase):
    def test_contract_audit_passes(self) -> None:
        self.assertEqual(audit(ROOT), [])

    def test_ai_schema_comes_from_all_semantic_sections(self) -> None:
        schema = build_ai_schema(SEMANTIC_SECTIONS)
        self.assertEqual(set(schema["properties"]), SEMANTIC_SECTIONS)
        self.assertEqual(set(schema["required"]), SEMANTIC_SECTIONS)
        for definition, fields in COMPILER_OWNED_FIELDS.items():
            required = set(schema["$defs"][definition].get("required") or [])
            self.assertFalse(required & set(fields))

    def test_repair_targets_are_extracted_from_real_error_paths(self) -> None:
        errors = [
            "$.report_claim_ledger[0].plain_claim 长度不能小于 4",
            "reality_candidate_pool[2].status 值无效",
            "不属于任何区块的总体错误",
        ]
        self.assertEqual(
            targets_from_errors(errors, SEMANTIC_SECTIONS),
            ["reality_candidate_pool", "report_claim_ledger"],
        )
        source = {key: [] for key in SEMANTIC_SECTIONS}
        source["method_synthesis"] = {}
        request = build(source, "core_synthesis", ["report_claim_ledger"], errors)
        self.assertEqual(set(request["target_schema"]["properties"]), {"report_claim_ledger"})

    def test_compiler_overwrites_bookkeeping_from_frozen_sources(self) -> None:
        semantic = {
            "method_synthesis": {"clusters": [{
                "member_hypothesis_ids": ["mh_a"],
                "supporting_method_ids": ["wrong"],
                "independence_groups": ["wrong"],
            }]},
            "report_claim_ledger": [{
                "claim_id": "claim_1", "claim_class": "primary_judgment",
                "method_hypothesis_ids": ["mh_a"],
                "source_detail_atom_ids": ["detail_mh_a_1"],
            }],
            "reality_candidate_pool": [{
                "candidate_id": "candidate_1", "related_claim_ids": ["claim_1"],
            }],
            "candidate_relation_map": [],
        }
        methods = [{
            "method_id": "pattern_structure", "independence_group": "structure",
            "technical_conclusions": [{"conclusion_id": "mc_a", "evidence_ids": ["evidence_a"]}],
            "reality_hypotheses": [{"hypothesis_id": "mh_a", "derived_from_conclusion_ids": ["mc_a"]}],
        }]
        evidence = [{"evidence_id": "evidence_a", "source_layer": "natal"}]
        details = [{"detail_atom_id": "detail_mh_a_1", "text": "现实表现", "hypothesis_id": "mh_a"}]
        result = compile_bookkeeping(copy.deepcopy(semantic), methods, evidence, details)
        cluster = result["method_synthesis"]["clusters"][0]
        claim = result["report_claim_ledger"][0]
        candidate = result["reality_candidate_pool"][0]
        self.assertEqual(cluster["supporting_method_ids"], ["pattern_structure"])
        self.assertEqual(cluster["independence_groups"], ["structure"])
        self.assertEqual(claim["evidence_ids"], ["evidence_a"])
        self.assertEqual(claim["observable_scenes"], ["现实表现"])
        self.assertEqual(candidate["source_layers"], ["chart"])
        self.assertEqual(candidate["status"], "unverified")


if __name__ == "__main__":
    unittest.main()
