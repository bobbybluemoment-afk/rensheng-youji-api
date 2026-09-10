from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "internal/rensheng-youji-mingli-core/scripts"))
sys.path.insert(0, str(ROOT / "internal/rensheng-youji-report-writer/scripts"))
sys.path.insert(0, str(ROOT / "internal/rensheng-youji-chinese-editor/scripts"))
sys.path.insert(0, str(ROOT / "skills/rensheng-youji-growth-map/scripts"))

from build_report_writing_pack import section_slots  # noqa: E402
from report_source_contract import evidence_retention_gaps, focus_domain  # noqa: E402
from resolve_report_sources import resolve  # noqa: E402
from run_checkpoint import record  # noqa: E402
from scan_report_language import scan  # noqa: E402
from validate_analysis_output import self_test_fixture  # noqa: E402
from render_report_pdf import year_story  # noqa: E402


class V2211QualityContractsTest(unittest.TestCase):
    def test_focus_domain_and_current_question_are_career_only(self) -> None:
        analysis = self_test_fixture()
        resolved = resolve(analysis, "我最关心事业发展和工作选择")
        ledger = {item["claim_id"]: item for item in analysis["report_claim_ledger"]}
        self.assertEqual(focus_domain("事业发展"), "career")
        self.assertEqual(resolved["focus_scope"]["selected_domain"], "career")
        self.assertTrue(resolved["current_question"]["claim_ids"])
        self.assertEqual(
            {ledger[item]["domain"] for item in resolved["current_question"]["claim_ids"]},
            {"career"},
        )

    def test_rich_method_evidence_cannot_be_silently_collapsed(self) -> None:
        methods = []
        for method_id, count in (("pattern_structure", 2), ("ten_god_dynamics", 1), ("timing_continuity", 1)):
            methods.append({
                "method_id": method_id,
                "status": "complete",
                "reality_hypotheses": [{
                    "hypothesis_id": f"{method_id}-{index}",
                    "domain": "finance_resources",
                    "normalized_direction": f"财务方向{method_id}{index}",
                } for index in range(count)],
            })
        data = {
            "independent_method_analyses": methods,
            "report_claim_ledger": [{
                "claim_id": "finance-1",
                "domain": "finance_resources",
                "method_hypothesis_ids": ["pattern_structure-0"],
            }],
        }
        self.assertTrue(evidence_retention_gaps(data))
        data["report_claim_ledger"] = [
            {"claim_id": "finance-1", "domain": "finance_resources", "method_hypothesis_ids": ["pattern_structure-0", "pattern_structure-1"]},
            {"claim_id": "finance-2", "domain": "finance_resources", "method_hypothesis_ids": ["ten_god_dynamics-0", "timing_continuity-0"]},
        ]
        self.assertEqual(evidence_retention_gaps(data), [])

    def test_writing_slots_follow_narrative_roles_and_drop_technical_payload(self) -> None:
        claims = [
            {"claim_id": "feature", "plain_claim": "你做事先确认要求。", "coverage_tags": ["feature"], "evidence_ids": ["e1"], "mechanism_chain": ["technical"]},
            {"claim_id": "formation", "plain_claim": "这种习惯形成得较早。", "coverage_tags": ["formation"], "evidence_ids": ["e2"], "mechanism_chain": ["technical"]},
            {"claim_id": "change", "plain_claim": "当前需要更主动表达成果。", "coverage_tags": ["current_change", "response"], "evidence_ids": ["e3"], "mechanism_chain": ["technical"]},
        ]
        section = {
            "id": "career", "delivery_mode": "normal",
            "claim_ids": [item["claim_id"] for item in claims],
            "mandatory_claim_ids": ["feature"], "selected_claims": claims,
        }
        slots = section_slots(section)
        self.assertEqual([item["narrative_role"] for item in slots], [
            "主要表现与行为", "形成经历与现实条件", "重复挑战、阶段变化与应对",
        ])
        self.assertEqual([item["claim_ids"] for item in slots], [["feature"], ["formation"], ["change"]])
        self.assertNotIn("evidence_ids", slots[0]["claims"][0])
        self.assertNotIn("mechanism_chain", slots[0]["claims"][0])

    def test_language_scan_flags_honorific_and_repeated_year_templates(self) -> None:
        draft = {
            "draft_id": "draft-test",
            "life_overview": {"id": "life_overview", "paragraphs": ["您会先确认条件。"]},
            "dimensions": [],
            "current_question": {"id": "current_question", "paragraphs": ["你可以先行动。"]},
        }
        years = [{
            "carry_in": "上一年留下的影响会继续进入这一年。",
            "real_world_signal": "这一年的表现各不相同。",
            "seed_for_next": "之后会留下新的准备。",
        } for _ in range(4)]
        result = scan(draft, {"yearly_outlook": {"years": years}})
        self.assertEqual(result["status"], "repair_required")
        self.assertTrue(any("称呼" in reason for item in result["issues"] for reason in item["reasons"]))
        self.assertTrue(any("模板" in reason for item in result["issues"] for reason in item["reasons"]))

    def test_year_story_removes_fixed_labels_and_duplicate_punctuation(self) -> None:
        item = {
            "carry_in": "已有经验。",
            "real_world_signal": "工作责任增加。。",
            "seed_for_next": "留下新的合作基础。",
        }
        stories = [year_story(item, index) for index in range(4)]
        self.assertEqual(len(set(stories)), 4)
        self.assertTrue(all("上一年留下的影响" not in text for text in stories))
        self.assertTrue(all("。。" not in text for text in stories))

    def test_report_checkpoint_cannot_precede_calibration(self) -> None:
        run_root = ROOT / "work/runs"
        run_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=run_root) as temp_dir:
            run_dir = Path(temp_dir)
            (run_dir / "run-state.json").write_text(json.dumps({"run_id": "quality-order"}), encoding="utf-8")
            artifact = run_dir / "artifact.json"
            artifact.write_text("{}", encoding="utf-8")
            record(run_dir, "METHOD_GATE", [artifact], [artifact])
            record(run_dir, "CORE_GATE", [artifact], [artifact])
            with self.assertRaisesRegex(ValueError, "CALIBRATION_GATE"):
                record(run_dir, "REPORT_GATE", [artifact], [artifact])


if __name__ == "__main__":
    unittest.main()
