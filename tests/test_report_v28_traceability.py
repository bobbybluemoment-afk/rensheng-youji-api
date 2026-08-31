#!/usr/bin/env python3
"""v2.8实体证据、事实提纲与人物初稿的来源约束。"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "internal/rensheng-youji-mingli-core/scripts"))
from validate_analysis_output import self_test_fixture, validate as validate_analysis  # noqa: E402

MATERIALIZE = ROOT / "internal/rensheng-youji-report-content-brief/scripts/materialize_content_brief.py"
VALIDATE_BRIEF = ROOT / "internal/rensheng-youji-report-content-brief/scripts/validate_content_brief.py"
VALIDATE_DRAFT = ROOT / "internal/rensheng-youji-report-writer/scripts/validate_report_draft.py"
RESOLVE = ROOT / "scripts/resolve_report_sources.py"
sys.path.insert(0, str(ROOT / "skills/rensheng-youji-growth-map/scripts"))
from render_report_pdf import dimensions_page  # noqa: E402
DIMENSIONS = ["self_growth", "love_partner", "career", "finance_resources", "body_emotion", "family_growth"]
COVERAGE = ["feature", "behavior", "formation", "challenge", "current_change", "response"]


def long_paragraph(seed: str) -> str:
    sentence = f"{seed}。这个判断需要结合具体环境观察，只有相关条件同时出现时，才适合用来理解实际选择和行为变化。"
    return sentence * 3


class ReportV28TraceabilityTest(unittest.TestCase):
    def test_fake_evidence_id_is_rejected(self) -> None:
        analysis = self_test_fixture()
        analysis["report_claim_ledger"][0]["evidence_ids"][0] = "evidence_missing"
        self.assertTrue(any("不存在的实体证据" in item for item in validate_analysis(analysis)))

    def test_materialized_brief_and_draft(self) -> None:
        analysis = self_test_fixture()
        claim_ids = [f"claim_self_{index}" for index in range(1, 7)]

        def section() -> dict:
            return {"claim_ids": claim_ids, "formation_chain_ids": ["formation_1"], "linkage_chain_ids": ["linkage_1"], "allowed_examples": [], "prohibited_claims": ["不能断定唯一职业"], "coverage": COVERAGE}

        selection = {
            "schema_version": "selection-1.0.0", "brief_id": "brief-v28",
            "source": {}, "focus_scope": {"protected_sections": ["life_overview", "dimensions"]},
            "life_overview": section(),
            "dimensions": [{"id": item, **section()} for item in DIMENSIONS],
            "current_question": section(),
            "calibration_internal": {"confirmed_claim_ids": [], "partial_claim_ids": [], "rejected_claim_ids": [], "uncertain_claim_ids": []},
        }
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            analysis_path, selection_path, brief_path, resolved_path = work / "analysis.json", work / "selection.json", work / "brief.json", work / "resolved.json"
            analysis_path.write_text(json.dumps(analysis, ensure_ascii=False), encoding="utf-8")
            selection_path.write_text(json.dumps(selection, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run([sys.executable, str(RESOLVE), str(analysis_path), "--output", str(resolved_path)], cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result = subprocess.run([sys.executable, str(MATERIALIZE), str(selection_path), "--analysis", str(analysis_path), "--resolved-sources", str(resolved_path), "--output", str(brief_path)], cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result = subprocess.run([sys.executable, str(VALIDATE_BRIEF), str(brief_path), "--analysis", str(analysis_path), "--resolved-sources", str(resolved_path)], cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            paragraphs = [long_paragraph("面对现实问题时会先确认条件再行动"), long_paragraph("过去形成的准备习惯会影响现在的判断"), long_paragraph("当前阶段需要把已有能力用在清楚目标上")]
            draft_section = {"paragraphs": paragraphs, "source_claim_ids": claim_ids, "paragraph_claim_map": [claim_ids[:2], claim_ids[2:4], claim_ids[4:6]]}
            draft = {
                "schema_version": "1.1.0", "draft_id": "draft-v28", "brief_id": "brief-v28",
                "life_overview": draft_section,
                "dimensions": [{"id": item, **draft_section, "coverage": COVERAGE} for item in DIMENSIONS],
                "current_question": draft_section,
            }
            draft_path = work / "draft.json"
            draft_path.write_text(json.dumps(draft, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run([sys.executable, str(VALIDATE_DRAFT), str(draft_path), "--brief", str(brief_path)], cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_six_domain_pages_fit_larger_text(self) -> None:
        paragraphs = [long_paragraph("这个领域有一条清楚的人物判断和现实条件") for _ in range(4)]
        report = {"schema_version": "2.8.0", "dimensions": [{"id": item, "title": item, "paragraphs": paragraphs} for item in DIMENSIONS]}
        for number, indexes in ((5, (0, 1)), (6, (2, 3)), (7, (4, 5))):
            page = dimensions_page(report, number, indexes)
            self.assertEqual(page.size, (1240, 1754))


if __name__ == "__main__":
    unittest.main()
