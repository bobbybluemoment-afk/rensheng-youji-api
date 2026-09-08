from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.compile_method_packet import compile_packet
from scripts.core_synthesis_contract import ALL_METHODS, PARTIAL_METHODS
from scripts.audit_method_prompt_contract import audit as audit_prompts
from scripts.build_method_prompt_packs import MANIFEST, build as build_prompt
from scripts.method_input_contract import build_method_input_view


ROOT = Path(__file__).resolve().parents[1]
DOMAINS = {
    "self_growth", "love_partner", "career", "finance_resources",
    "body_emotion", "family_growth",
}


def semantic_patch(method_id: str) -> dict:
    count = 1 if method_id in PARTIAL_METHODS else 2
    conclusions = []
    hypotheses = []
    supported = ["career"] if count == 1 else ["career", "self_growth"]
    for index in range(count):
        conclusions.append({
            "statement": f"第{index + 1}条方法技术结论具有清楚的结构条件。",
            "mechanism_chain": ["冻结事实形成结构", "结构在条件满足时形成现实动力"],
            "chart_refs": ["chart_facts"],
            "evidence": [{
                "source_layer": "natal",
                "chart_refs": ["chart_facts"],
                "observation": "四柱与藏干形成可以核对的结构关系。",
                "interpretation": "本方法据此判断结构的主要作用方向。",
                "limitations": ["不能单独推出具体职业或事件。"],
                "confidence": "medium",
            }],
            "conditions": ["相关结构没有被相反条件完全破坏。"],
            "counterconditions": ["若关键连接不成立则降低判断。"],
            "time_scope": "原局长期",
            "confidence": "medium",
        })
        domain = supported[index]
        hypotheses.append({
            "derived_from_conclusion_numbers": [index + 1],
            "domain": domain,
            "normalized_direction": f"{domain}现实方向",
            "statement": "现实中可能更重视清楚条件，并通过持续完成事情形成结果。",
            "observable_indicators": ["重要决定前会核对条件。", "倾向把任务推进到完整结果。"],
            "conditions": ["现实环境允许持续投入。"],
            "counterevidence": ["长期表现完全相反时应降低判断。"],
            "unsupported_extensions": ["不能据此指定单位、岗位或收入。"],
            "time_scope": "原局长期",
        })
    limits = [
        {"domain": domain, "status": "insufficient_evidence", "reasoning": "已经检查，但本方法没有足够独立证据形成现实候选。"}
        for domain in sorted(DOMAINS - set(supported))
    ]
    return {
        "schema_version": "1.0.0",
        "result": "complete",
        "technical_conclusions": conclusions,
        "reality_hypotheses": hypotheses,
        "domain_limits": limits,
        "limitations": ["本方法只提供独立视角，最终结论仍需综合。"],
        "failure_reasons": [],
        "degradation_effects": [],
    }


class MethodSemanticCompilerTest(unittest.TestCase):
    def test_all_compact_prompt_guides_pass_contract_audit(self) -> None:
        self.assertEqual(audit_prompts(ROOT), [])

    def test_nine_semantic_answers_compile_to_canonical_packets(self) -> None:
        method_input = {"chart_facts": {"pillars": ["戊寅", "乙丑", "甲戌", "癸酉"]}}
        for method_id in sorted(ALL_METHODS):
            packet = compile_packet(method_input, semantic_patch(method_id), method_id)
            method = packet["method_analysis"]
            self.assertEqual(method["method_id"], method_id)
            self.assertEqual(method["source_method_ids_read"], [])
            self.assertEqual(len(method["domain_assessments"]), 6)
            self.assertTrue(all(item["reality_confirmation"] == "unverified" for item in method["reality_hypotheses"]))

    def test_compiler_rejects_incomplete_domain_review(self) -> None:
        patch = semantic_patch("pattern_structure")
        patch["domain_limits"].pop()
        with self.assertRaisesRegex(ValueError, "六领域检查不完整"):
            compile_packet({"chart_facts": {}}, patch, "pattern_structure")

    def test_compiler_rejects_cross_method_identity_from_ai(self) -> None:
        patch = semantic_patch("pattern_structure")
        patch["method_id"] = "climate_adjustment"
        with self.assertRaisesRegex(ValueError, "Schema"):
            compile_packet({"chart_facts": {}}, patch, "pattern_structure")

    def test_method_views_only_include_method_relevant_time_data(self) -> None:
        method_input = {
            "request": {"request_id": "x", "analysis_as_of": "2026-09-07", "calendar_basis": "local_civil", "target_range": {"start_year": 2021, "end_year": 2040}},
            "person": {"name": None, "gender": "male", "birth": {"local_datetime": "1999-01-22T17:45:00+08:00", "place_name": "福建省·泉州市", "timezone": "Asia/Shanghai", "raw_input": "secret-free"}},
            "chart": {"day_master": "甲", "pillars": {"day": {"stem": "甲", "branch": "戌"}}, "calculation_engine": "engine"},
            "solar_terms_and_boundaries": {"boundary_flags": [], "nearest_solar_terms": [{"name": "小寒"}], "notes": ["long note"]},
            "luck_cycles": {"direction": "forward", "cycles": [{"index": 1, "stem": "丙", "branch": "寅", "hidden_stems": [{"stem": "甲"}]}]},
            "annual_cycles": [{"year": 2026, "stem": "丙", "branch": "午", "stem_ten_god": "食神", "luck_cycle_index": 3, "hidden_stems": [{"stem": "丁"}], "age": 27}],
            "monthly_cycles": None,
            "reality_context": {"facts": [], "questions": []},
            "calibration": {"candidate_feedback": []},
        }
        root_view = build_method_input_view(method_input, "root_seed_flower_fruit")
        pattern_view = build_method_input_view(method_input, "pattern_structure")
        stem_view = build_method_input_view(method_input, "stem_branch_dynamics")
        timing_view = build_method_input_view(method_input, "timing_continuity")
        self.assertNotIn("luck_cycles", root_view)
        self.assertNotIn("annual_cycles", root_view)
        self.assertIn("luck_cycles", pattern_view)
        self.assertNotIn("annual_cycles", pattern_view)
        self.assertIn("hidden_stems", stem_view["annual_cycles"][0])
        self.assertNotIn("age", stem_view["annual_cycles"][0])
        self.assertIn("hidden_stems", timing_view["annual_cycles"][0])
        for view in (root_view, pattern_view, stem_view, timing_view):
            self.assertNotIn("reality_context", view)
            self.assertNotIn("calibration", view)
            self.assertNotIn("calculation_engine", view["chart"])

    def test_prompt_views_are_materially_smaller_than_repeating_full_input(self) -> None:
        annual = [
            {"year": year, "stem": "丙", "branch": "午", "stem_ten_god": "食神", "luck_cycle_index": 3, "hidden_stems": [{"stem": "丁", "ten_god": "伤官"}], "age": year - 1999}
            for year in range(2021, 2041)
        ]
        method_input = {
            "request": {"analysis_as_of": "2026-09-07", "calendar_basis": "local_civil", "target_range": {"start_year": 2021, "end_year": 2040}},
            "person": {"gender": "male", "birth": {"local_datetime": "1999-01-22T17:45:00+08:00", "place_name": "福建省·泉州市", "timezone": "Asia/Shanghai"}},
            "chart": {"day_master": "甲", "pillars": {"day": {"stem": "甲", "branch": "戌"}}},
            "solar_terms_and_boundaries": {"boundary_flags": [], "nearest_solar_terms": [{"name": "小寒"}]},
            "luck_cycles": {"direction": "forward", "cycles": [{"index": index, "stem": "丙", "branch": "寅", "hidden_stems": [{"stem": "甲"}]} for index in range(1, 9)]},
            "annual_cycles": annual,
            "monthly_cycles": None,
            "reality_context": {"facts": [], "questions": []},
            "calibration": {"candidate_feedback": []},
        }
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        receipts = [build_prompt(method_input, method_id, manifest)[1] for method_id in sorted(ALL_METHODS)]
        projected = sum(item["input_view_bytes"] for item in receipts)
        repeated = len(json.dumps(method_input, ensure_ascii=False, separators=(",", ":")).encode("utf-8")) * 9
        self.assertLess(projected, repeated * 0.65)

    def test_compiler_rejects_more_than_eighteen_hypotheses(self) -> None:
        patch = semantic_patch("pattern_structure")
        template = patch["reality_hypotheses"][0]
        patch["reality_hypotheses"] = [dict(template, normalized_direction=f"方向{index}") for index in range(19)]
        with self.assertRaisesRegex(ValueError, "最多"):
            compile_packet({"chart_facts": {}}, patch, "pattern_structure")


if __name__ == "__main__":
    unittest.main()
