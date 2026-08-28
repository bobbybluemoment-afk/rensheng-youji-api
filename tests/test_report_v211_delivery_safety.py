from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/rensheng-youji-growth-map/scripts"
sys.path.insert(0, str(SCRIPTS))

from render_report import MINGLI_TERMS, _validate_emphasis, length  # noqa: E402
import render_report_pdf as pdf_renderer  # noqa: E402


class ReportV211DeliverySafetyTest(unittest.TestCase):
    def test_year_text_must_not_be_python_list(self) -> None:
        with self.assertRaisesRegex(ValueError, "必须是字符串"):
            length(["为2022积累"], 2, 50, "carry_in")  # type: ignore[arg-type]

    def test_visible_term_set_catches_regression_words(self) -> None:
        for term in ("命盘", "年柱", "命局", "大运", "流年", "冲根"):
            self.assertIn(term, MINGLI_TERMS)

    def test_emphasis_rejects_fragment_without_terminal_punctuation(self) -> None:
        section = {
            "paragraphs": ["你更适合职责清楚、评价明确的环境。后面是完整解释。"],
            "paragraph_claim_map": [["claim_1", "claim_2"]],
            "emphasis_spans": [{"paragraph_index": 0, "text": "你更适合职责清楚、评价明确的环境", "claim_ids": ["claim_1"]}],
        }
        errors: list[str] = []
        _validate_emphasis(section, 0, 1, "section", errors)
        self.assertTrue(any("句末标点" in item for item in errors))

    def test_sparse_emphasis_may_be_empty(self) -> None:
        section = {"paragraphs": ["这是完整判断。后面是解释。"], "paragraph_claim_map": [["claim_1", "claim_2"]], "emphasis_spans": []}
        errors: list[str] = []
        _validate_emphasis(section, 0, 1, "section", errors)
        self.assertEqual(errors, [])

    def test_primary_and_stable_render_modes_both_finish(self) -> None:
        text = "前一句解释条件。你更适合职责清楚、评价明确的环境。后一句说明边界。"
        emphasis = "你更适合职责清楚、评价明确的环境。"
        pdf_renderer.RENDER_STYLE = "primary"
        primary = pdf_renderer.Page(5, "六个现实领域", compact=True)
        primary.paragraph_emphasis(text, emphasis, size=23)
        self.assertGreater(primary.y, 158)
        pdf_renderer.RENDER_STYLE = "stable"
        stable = pdf_renderer.Page(5, "六个现实领域", compact=True)
        stable.paragraph_emphasis(text, emphasis, size=23)
        self.assertGreater(stable.y, 158)

    def test_stable_mode_does_not_block_on_visual_emphasis_mismatch(self) -> None:
        text = "这是已经通过内容校验的完整正文。"
        pdf_renderer.RENDER_STYLE = "primary"
        with self.assertRaisesRegex(ValueError, "精确子串"):
            pdf_renderer.Page(5, "六个现实领域", compact=True).paragraph_emphasis(text, "不存在的重点句。", size=23)
        pdf_renderer.RENDER_STYLE = "stable"
        page = pdf_renderer.Page(5, "六个现实领域", compact=True)
        page.paragraph_emphasis(text, "不存在的重点句。", size=23)
        self.assertGreater(page.y, 158)


if __name__ == "__main__":
    unittest.main()
