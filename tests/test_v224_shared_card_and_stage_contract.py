#!/usr/bin/env python3
"""Regression tests for the 2.24 shared card and report-depth contracts."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "internal/rensheng-youji-mingli-core/scripts"))
sys.path.insert(0, str(ROOT / "internal/rensheng-youji-report-writer/scripts"))
sys.path.insert(0, str(ROOT / "skills/rensheng-youji-growth-map/scripts"))
from report_source_contract import delivery_mode  # noqa: E402
from build_report_writing_pack import yearly_writing_plan  # noqa: E402
from validate_analysis_output import self_test_fixture, validate  # noqa: E402
from render_report import _validate_narrative  # noqa: E402


def twenty_year_fixture() -> dict:
    data = self_test_fixture()
    seed = data["annual_theme_activation"][0]
    annuals = []
    directions = ("consolidation", "support", "mixed", "consolidation", "pressure")
    for index, year in enumerate(range(2021, 2041)):
        item = copy.deepcopy(seed)
        direction = directions[index % len(directions)]
        item.update({
            "year": year, "age": 22 + index,
            "luck_cycle_index": 2 if year < 2033 else 3,
            "luck_theme_link": "积累经验" if year < 2033 else "扩大责任",
            "year_theme": f"{year}年的现实安排",
            "direction": direction,
            "change_intensity": "high" if index % 4 == 2 else "medium",
            "activation_mechanisms": [f"年度机制{index % 4}"],
            "human_actions": [f"行动{index}"], "social_feedback": [f"反馈{index}"],
            "carry_in": [f"带入{index}"], "carry_out": [f"留下{index}"], "seed_for_next": [f"准备{index + 1}"],
            "domain_impacts": [
                {"domain": "career", "direction": direction, "intensity": item["change_intensity"], "mechanism": f"事业机制{index % 4}"},
                {"domain": "finance_resources", "direction": directions[(index + 1) % len(directions)], "intensity": item["change_intensity"], "mechanism": f"财富机制{index % 3}"},
            ],
        })
        annuals.append(item)
    data["annual_theme_activation"] = annuals
    data["analysis_meta"]["analysis_as_of"] = "2026-09-17"
    data["analysis_meta"]["target_range"] = {"start_year": 2021, "end_year": 2040}
    data["turning_points"] = [{"year_or_range": "2023", "phase": "阶段变化", "theme": "工作变化", "linked_domains": ["career"], "confidence": "medium"}]
    return data


class V224SharedCardAndStageContractTest(unittest.TestCase):
    def test_four_complete_claims_support_normal_delivery(self) -> None:
        self.assertEqual(delivery_mode(4, []), "normal")
        self.assertEqual(delivery_mode(4, ["formation"]), "shortened")
        self.assertEqual(delivery_mode(2, []), "shortened")
        self.assertEqual(delivery_mode(1, []), "minimal")

    def test_four_claims_can_cover_three_normal_paragraphs(self) -> None:
        sentence = "你会先把现实情况看清，再决定下一步怎样推进。"
        section = {
            "delivery_mode": "normal",
            "paragraphs": [sentence * 11, sentence * 11, sentence * 11],
            "source_claim_ids": ["c1", "c2", "c3", "c4"],
            "paragraph_claim_map": [["c1"], ["c2"], ["c3", "c4"]],
        }
        errors: list[str] = []
        _validate_narrative(section, 0, 0, "dimensions.career", errors, require_map=True, use_delivery_mode=True)
        self.assertEqual(errors, [])

    def test_skill_does_not_restore_two_claims_per_paragraph(self) -> None:
        skill_text = (ROOT / "skills/rensheng-youji-growth-map/SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("每个自然段至少映射两个实体化Core判断", skill_text)
        self.assertIn("每个自然段至少映射一条实体化Core判断", skill_text)
        self.assertIn("章节整体必须覆盖全部必进判断", skill_text)

    def test_report_ai_writes_stages_not_twenty_rows(self) -> None:
        baseline = twenty_year_fixture()
        plan = yearly_writing_plan(baseline)
        self.assertTrue(3 <= len(plan["stages"]) <= 6)
        self.assertTrue(3 <= len(plan["key_years"]) <= 8)
        self.assertEqual(plan["stages"][0]["start_year"], baseline["annual_theme_activation"][0]["year"])
        self.assertEqual(plan["stages"][-1]["end_year"], baseline["annual_theme_activation"][-1]["year"])
        schema = json.loads((ROOT / "internal/rensheng-youji-report-writer/schemas/report-semantic-patch.schema.json").read_text(encoding="utf-8"))
        yearly = schema["properties"]["yearly_outlook"]
        self.assertEqual(set(yearly["required"]), {"start_year", "end_year", "summary", "stages", "key_years"})
        self.assertNotIn("years", yearly["properties"])

    def test_core_rejects_twenty_year_domain_template_collapse(self) -> None:
        data = twenty_year_fixture()
        copied = {"domain": "finance_resources", "direction": "mixed", "intensity": "medium", "mechanism": "每年复制同一模板"}
        for item in data["annual_theme_activation"]:
            item["domain_impacts"] = [copy.deepcopy(copied)]
        errors = validate(data)
        self.assertTrue(any("跨多年完全复制" in item for item in errors), errors)

    def test_shared_card_algorithm_preserves_structured_variation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            baseline = temp / "baseline.json"
            baseline.write_text(json.dumps(twenty_year_fixture(), ensure_ascii=False), encoding="utf-8")
            pack, signals, series = temp / "pack.json", temp / "signals.json", temp / "series.json"
            commands = (
                ["internal/rensheng-youji-free-card-output/scripts/build_card_visual_pack.py", "--baseline", str(baseline), "--output", str(pack)],
                ["internal/rensheng-youji-free-card-output/scripts/build_visual_signals_from_core.py", "--pack", str(pack), "--output", str(signals)],
                ["internal/rensheng-youji-free-card-output/scripts/build_visual_series.py", str(signals), "--output", str(series)],
            )
            for command in commands:
                result = subprocess.run([sys.executable, *command], cwd=ROOT, text=True, capture_output=True, check=False)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result = json.loads(series.read_text(encoding="utf-8"))
            self.assertEqual(result["algorithm_version"], "2.0.0")
            self.assertGreater(len({item["life_kline"]["close"] for item in result["years"]}), 1)
            self.assertGreater(len({item["career"]["level"] for item in result["years"]}), 1)
            self.assertGreater(len({item["wealth"]["level"] for item in result["years"]}), 1)


if __name__ == "__main__":
    unittest.main()
