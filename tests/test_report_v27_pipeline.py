#!/usr/bin/env python3
"""Core v0.5 -> 事实提纲 -> 人物初稿 -> 中文编辑 -> 10页PDF。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))
from test_full_report_pipeline import _assemble_free_card, _calibration_questions, _repeat, _report  # noqa: E402
sys.path.insert(0, str(ROOT / "internal/rensheng-youji-mingli-core/scripts"))
from validate_analysis_output import self_test_fixture  # noqa: E402

DELIVERY = ROOT / "skills/rensheng-youji-growth-map/scripts/generate_full_report.py"
DIMENSIONS = [
    ("self_growth", "1｜性格与内在成长"),
    ("love_partner", "2｜恋爱与伴侣"),
    ("career", "3｜事业发展"),
    ("finance_resources", "4｜财富与资源"),
    ("body_emotion", "5｜身体与情绪"),
    ("family_growth", "6｜家庭与成长环境"),
]
CLAIMS = [f"claim_self_{index}" for index in range(1, 9)]
COVERAGE = ["feature", "behavior", "formation", "challenge", "current_change", "response"]


def _section(seed_a: str, seed_b: str, each: int = 200) -> dict:
    return {
        "paragraphs": [_repeat(seed_a, each), _repeat(seed_b, each)],
        "source_claim_ids": CLAIMS[:6],
    }


def _artifacts() -> tuple[dict, dict, dict, dict, dict]:
    report = _report()
    report.update({
        "schema_version": "2.7.0",
        "report_id": "report-v27-fixture",
        "source": {"analysis_id": "fixture-v2-pipeline", "core_version": "0.5.0", "analysis_as_of": "2026-08-20", "calibration_status": "calibrated"},
        "source_artifacts": {"content_brief_id": "brief-v27-fixture", "report_draft_id": "draft-v27-fixture", "editorial_review_id": "review-v27-fixture"},
        "focus_scope": {
            "selected_focus": "事业发展",
            "protected_sections": ["life_overview", "dimensions"],
            "emphasis_sections": ["current_question_narrative", "stage_story.present_task", "stage_story.next_direction", "yearly_outlook", "action_guide.priority_actions"],
            "topic_keywords": ["承担新责任"],
        },
        "editorial_review": {"version": "2.0.0", "review_id": "review-v27-fixture"},
    })
    life_final = _section(
        "你面对重要事情时通常先了解要求、比较条件，再决定怎样行动。这种方式让你处理复杂任务时比较稳，也使你不容易在准备不足时贸然承诺。",
        "家庭和学习经历可能让你较早重视实际结果。进入工作以后，你更适合通过专业积累和完整项目逐步扩大职责，同时需要更及时地说明自己的成果和要求。",
        190,
    )
    report["executive_summary"] = {
        "life_overview": {**life_final, "coverage": ["personality", "formation", "family_education", "career_finance", "relationship", "current_stage"]},
        "capabilities_resources": [
            "能够把复杂信息整理成清楚步骤，并持续完成较长任务。",
            "做事重视复核和实际结果，容易积累可靠的专业信誉。",
            "面对变化时会比较条件，能够控制不必要的冒险。",
        ],
    }
    final_dimensions = []
    for identifier, title in DIMENSIONS:
        first = "你在这个领域通常先观察现实条件，再决定投入多少。过去形成的责任感让你愿意把事情处理完整，也使你容易在边界不清时承担额外工作。"
        second = "当前阶段需要保留原有的认真和耐心，同时更早说明自己的需要、权限和完成标准。遇到新机会时，可以先用小范围尝试核对结果，再决定是否增加长期投入。"
        if identifier == "body_emotion":
            second = "压力增加时，你容易先继续处理任务，休息和表达则被往后放。需要把恢复时间提前安排；这些内容只用于观察压力节奏，不构成疾病诊断，持续不适应以正规医疗评估为准。"
        section = _section(first, second, 200)
        final_dimensions.append({"id": identifier, "title": title, **section, "coverage": COVERAGE, "confidence": "中等置信", "audit": {"allowed_examples": [], "evidence_gaps": []}})
    report["dimensions"] = final_dimensions
    report["current_question_narrative"] = {
        **_section(
            "你现在需要判断的不是要不要承担责任，而是新增责任能否带来清楚的权限、学习机会和实际结果。如果工作只增加任务，却没有相应支持，就不适合立即全部接下。",
            "未来两三年可以优先选择职责明确、能够独立完成并留下成果的项目。开始前先确认评价标准和成果归属，再根据真实反馈决定是否继续扩大范围。",
            150,
        ),
    }

    draft = {
        "schema_version": "1.0.0",
        "draft_id": "draft-v27-fixture",
        "brief_id": "brief-v27-fixture",
        "life_overview": _section("你通常会先了解要求再行动，也愿意为结果负责。", "这些习惯受到家庭、学习和工作经历影响，并继续影响事业和关系。", 190),
        "dimensions": [],
        "current_question": _section("现在需要比较新增责任是否真的带来成长和结果。", "未来可以先核对权限和评价标准，再决定投入多少。", 150),
    }
    for identifier, _ in DIMENSIONS:
        section = _section("你会先观察条件，再决定怎样处理，并努力把事情完成。", "这些方式带来稳定表现，也需要在当前阶段调整边界。", 200)
        draft["dimensions"].append({"id": identifier, **section, "coverage": COVERAGE})

    def brief_section() -> dict:
        return {"claim_ids": CLAIMS[:6], "formation_chain_ids": ["formation_1"], "linkage_chain_ids": ["linkage_1"], "allowed_examples": [], "prohibited_claims": ["不能断定唯一职业"], "coverage": COVERAGE}

    brief = {
        "schema_version": "1.0.0",
        "brief_id": "brief-v27-fixture",
        "source": {"analysis_id": "fixture-v2-pipeline", "core_version": "0.5.0"},
        "focus_scope": {"protected_sections": ["life_overview", "dimensions"]},
        "life_overview": brief_section(),
        "dimensions": [{"id": identifier, **brief_section()} for identifier, _ in DIMENSIONS],
        "current_question": brief_section(),
        "calibration_internal": {"confirmed_claim_ids": [], "partial_claim_ids": [], "rejected_claim_ids": [], "uncertain_claim_ids": []},
    }

    def sha(section: dict) -> str:
        return hashlib.sha256("\n".join(section["paragraphs"]).encode("utf-8")).hexdigest()

    draft_map = {"life_overview": draft["life_overview"], "current_question": draft["current_question"]}
    final_map = {"life_overview": report["executive_summary"]["life_overview"], "current_question": report["current_question_narrative"]}
    for item in draft["dimensions"]:
        draft_map[f"dimension:{item['id']}"] = item
    for item in report["dimensions"]:
        final_map[f"dimension:{item['id']}"] = item
    review = {
        "version": "2.0.0",
        "review_id": "review-v27-fixture",
        "draft_id": "draft-v27-fixture",
        "final_report_id": "report-v27-fixture",
        "sections": [
            {"section_id": key, "draft_sha256": sha(draft_map[key]), "final_sha256": sha(final_map[key]), "source_claim_ids": CLAIMS[:6], "changes": ["补全主体和现实动作"]}
            for key in draft_map
        ],
        "checks": {"facts_preserved": True, "no_new_claims": True, "natural_chinese": True, "no_template_repetition": True, "calibration_hidden": True},
    }

    analysis = self_test_fixture()
    analysis["analysis_meta"]["analysis_id"] = "fixture-v2-pipeline"
    analysis["analysis_meta"]["core_version"] = "0.5.0"
    return report, brief, draft, review, analysis


class ReportV27PipelineTest(unittest.TestCase):
    def test_v27_full_delivery(self) -> None:
        report, brief, draft, review, analysis = _artifacts()
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            free_card = _assemble_free_card(work)
            card_data = json.loads(free_card.read_text(encoding="utf-8"))
            card_data["source"]["core_version"] = "0.5.0"
            free_card.write_text(json.dumps(card_data, ensure_ascii=False), encoding="utf-8")
            files = {
                "report": report,
                "brief": brief,
                "draft": draft,
                "review": review,
                "analysis": analysis,
                "questions": _calibration_questions(),
            }
            paths: dict[str, Path] = {}
            for name, data in files.items():
                path = work / f"{name}.json"
                path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                paths[name] = path
            delivery = work / "delivery"
            result = subprocess.run([
                sys.executable, str(DELIVERY),
                "--report", str(paths["report"]),
                "--content-brief", str(paths["brief"]),
                "--report-draft", str(paths["draft"]),
                "--editorial-review", str(paths["review"]),
                "--analysis", str(paths["analysis"]),
                "--free-card", str(free_card),
                "--calibration-questions", str(paths["questions"]),
                "--out-dir", str(delivery), "--keep-pages", "--allow-test-fixture",
            ], cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            manifest = json.loads((delivery / "report-delivery-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["checks"]["pdf_pages"], 10)
            self.assertTrue(manifest["checks"]["traceable_editorial_review_valid"])
            markdown = (delivery / "rensheng-youji-full-report.md").read_text(encoding="utf-8")
            self.assertNotIn("校准后的现实线索", markdown)
            self.assertNotIn("校准结果", markdown)


if __name__ == "__main__":
    unittest.main()
