from __future__ import annotations

import json
import copy
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "internal/rensheng-youji-mingli-core/scripts"))

from apply_semantic_repair import apply as apply_repair  # noqa: E402
from core_synthesis_contract import canonical_digest  # noqa: E402
from prepare_core_synthesis import compact_view  # noqa: E402
from prepare_semantic_repair import build as build_repair  # noqa: E402
from record_ai_usage import cost  # noqa: E402
from run_checkpoint import record, verify  # noqa: E402


class V221EfficiencyContractsTest(unittest.TestCase):
    def test_core_ai_view_uses_domain_matrix_and_keeps_full_source_out(self) -> None:
        source = {
            "core_version": "0.15.0", "analysis_input_sha256": "a" * 64,
            "method_input_sha256": "b" * 64, "method_packets_sha256": "c" * 64,
            "analysis_input": {"request": {"questions": [], "current_concerns": []}},
            "independent_method_analyses": [{
                "method_id": "pattern_structure", "tier": "primary", "status": "complete",
                "technical_conclusions": [{
                    "conclusion_id": "mc_pattern_structure_01", "statement": "技术判断示例",
                    "mechanism_chain": ["甲", "乙"], "conditions": ["条件"],
                    "counterconditions": ["反证"], "time_scope": "长期", "confidence": "medium",
                    "evidence_ids": ["evidence_pattern_structure_01"], "chart_refs": ["chart.pillars"],
                }],
                "reality_hypotheses": [{
                    "hypothesis_id": "mh_pattern_structure_01", "derived_from_conclusion_ids": ["mc_pattern_structure_01"],
                    "domain": "career", "normalized_direction": "规则环境", "statement": "更容易在规则清楚的工作环境里稳定推进",
                    "observable_indicators": ["先确认要求", "重视交付"], "conditions": ["目标清楚"],
                    "counterevidence": ["长期拒绝规则"], "unsupported_extensions": ["不能断定单位"], "time_scope": "长期",
                }],
                "domain_assessments": [{"domain": "career", "status": "supported", "hypothesis_ids": ["mh_pattern_structure_01"], "reasoning": "形成候选"}],
                "limitations": ["仅供综合"],
            }],
            "evidence_registry": [{
                "evidence_id": "evidence_pattern_structure_01", "method_id": "pattern_structure",
                "independence_group": "structure", "source_layer": "natal", "observation": "观察",
                "interpretation": "完整解释不应重复进入AI视图", "confidence": "medium",
            }],
            "method_execution_audit": {}, "source_coverage_audit": {},
            "semantic_output_contract": {},
        }
        before = copy.deepcopy(source)
        view = compact_view(source)
        self.assertEqual(source, before)
        self.assertEqual(view["schema_version"], "1.2.0")
        self.assertIn("judgment_matrix", view)
        self.assertNotIn("method_summaries", view)
        self.assertNotIn("interpretation", view["evidence_index"][0])
        self.assertEqual(view["judgment_matrix"]["career"][0]["hypothesis_id"], "mh_pattern_structure_01")

    def test_repair_patch_cannot_change_unrequested_sections(self) -> None:
        source = {"schema_version": "1.0.0", "technical_conclusions": [1], "reality_hypotheses": [2], "domain_limits": [], "limitations": ["x"], "failure_reasons": [], "degradation_effects": [], "result": "complete"}
        request = build_repair(source, "independent_method", ["technical_conclusions"], ["字段错误"])
        patch = {
            "schema_version": "1.0.0", "stage": "independent_method",
            "source_sha256": canonical_digest(source),
            "repair_request_sha256": request["repair_request_sha256"],
            "replacements": [{"target": "technical_conclusions", "value": [3]}],
        }
        result = apply_repair(source, request, patch)
        self.assertEqual(result["technical_conclusions"], [3])
        self.assertEqual(result["reality_hypotheses"], [2])
        bad = dict(patch)
        bad["replacements"] = [{"target": "reality_hypotheses", "value": []}]
        with self.assertRaisesRegex(ValueError, "只能覆盖"):
            apply_repair(source, request, bad)

    def test_checkpoint_detects_changed_output(self) -> None:
        run_root = ROOT / "work/runs"
        run_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=run_root) as temp_dir:
            run_dir = Path(temp_dir)
            (run_dir / "run-state.json").write_text(json.dumps({"run_id": "test", "work_dir": str(run_dir)}), encoding="utf-8")
            source, output = run_dir / "source.json", run_dir / "output.json"
            source.write_text("{}", encoding="utf-8")
            output.write_text("{\"ok\":true}", encoding="utf-8")
            record(run_dir, "TEST_GATE", [source], [output])
            self.assertEqual(verify(run_dir), [])
            output.write_text("{\"ok\":false}", encoding="utf-8")
            self.assertTrue(any("哈希变化" in item for item in verify(run_dir)))

    def test_current_sol_cost_formula_counts_reasoning_inside_output(self) -> None:
        self.assertAlmostEqual(cost(100_000, 0, 50_000), 1.4)
        self.assertAlmostEqual(cost(100_000, 50_000, 50_000), 1.22)


if __name__ == "__main__":
    unittest.main()
