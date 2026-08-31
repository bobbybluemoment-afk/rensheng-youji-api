from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "internal/rensheng-youji-mingli-core/scripts"))
from validate_analysis_output import self_test_fixture, validate as validate_analysis  # noqa: E402

sys.path.insert(0, str(ROOT / "skills/rensheng-youji-growth-map/scripts"))
from render_report import emphasized_paragraph  # noqa: E402
from render_report_pdf import Page, dimensions_page  # noqa: E402


class ReportV210DomainIndependenceTest(unittest.TestCase):
    def test_core_fixture_has_independent_domain_sources(self) -> None:
        self.assertEqual(validate_analysis(self_test_fixture()), [])

    def test_wrong_domain_claim_is_rejected(self) -> None:
        analysis = self_test_fixture()
        source = analysis["report_source_bundle"]["dimensions"]["family_growth"]
        source["domain_specific_claim_ids"][0] = "claim_self_1"
        self.assertTrue(any("含其他领域判断" in item for item in validate_analysis(analysis)))

    def test_shared_mainline_cannot_dominate(self) -> None:
        analysis = self_test_fixture()
        source = analysis["report_source_bundle"]["dimensions"]["career"]
        source["mainline_claim_ids"] = source["claim_ids"][:3]
        self.assertTrue(any("不得超过本节判断的30%" in item for item in validate_analysis(analysis)))

    def test_same_claim_cannot_fill_six_domains(self) -> None:
        analysis = self_test_fixture()
        for source in analysis["report_source_bundle"]["dimensions"].values():
            source["claim_ids"][-1] = "claim_self_1"
            source["mainline_claim_ids"] = ["claim_self_1"]
        self.assertTrue(any("最多进入两个现实领域" in item for item in validate_analysis(analysis)))

    def test_markdown_only_bolds_configured_sentence(self) -> None:
        section = {
            "paragraphs": ["前一句说明条件。你适合在职责清楚的组织里逐步扩大权限。后一句说明边界。"],
            "emphasis_spans": [{"paragraph_index": 0, "text": "你适合在职责清楚的组织里逐步扩大权限。", "claim_ids": ["claim_career_1"]}],
        }
        rendered = emphasized_paragraph(section, 0)
        self.assertEqual(rendered.count("**"), 2)
        self.assertIn("**你适合在职责清楚的组织里逐步扩大权限。**", rendered)

    def test_pdf_emphasis_keeps_fixed_layout_method(self) -> None:
        page = Page(5, "六个现实领域", compact=True)
        text = "你遇事会先核对条件。你适合在职责清楚的组织里逐步扩大权限。之后再观察结果。"
        page.paragraph_emphasis(text, "你适合在职责清楚的组织里逐步扩大权限。", size=23)
        self.assertGreater(page.y, 158)

    def test_domain_pages_fit_700_characters_at_larger_size(self) -> None:
        base = "这个领域有一条清楚的人物判断和现实条件。这个判断需要结合具体环境观察，只有相关条件同时出现时，才适合用来理解实际选择和行为变化。"
        paragraph = (base * 4)[:175]
        dimensions = []
        for domain in ("self_growth", "love_partner", "career", "finance_resources", "body_emotion", "family_growth"):
            dimensions.append({
                "id": domain,
                "title": domain,
                "paragraphs": [paragraph] * 4,
                "emphasis_spans": [{"paragraph_index": 0, "text": "这个领域有一条清楚的人物判断和现实条件。"}],
            })
        report = {"schema_version": "2.10.0", "dimensions": dimensions}
        for number, indexes in ((5, (0, 1)), (6, (2, 3)), (7, (4, 5))):
            self.assertEqual(dimensions_page(report, number, indexes).size, (1240, 1754))


if __name__ == "__main__":
    unittest.main()
