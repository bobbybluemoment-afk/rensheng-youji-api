from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "skills/rensheng-youji-growth-map/scripts"))
sys.path.insert(0, str(ROOT / "internal/rensheng-youji-chinese-editor/scripts"))

from build_calibration_questions import build as build_questions  # noqa: E402
from compile_calibration_delta import compile_delta  # noqa: E402
from compile_final_report import compile_report, digest as report_digest  # noqa: E402
from core_baseline import digest  # noqa: E402
from scan_report_language import scan  # noqa: E402
from apply_editorial_patch import apply as apply_editorial, apply_all as apply_all_editorial  # noqa: E402
from validate_calibration_free_text import validate as validate_free_text  # noqa: E402


DOMAINS = ["self_growth", "love_partner", "career", "finance_resources", "body_emotion", "family_growth"]


def calibration_baseline() -> dict:
    candidates = []
    claims = []
    specs = [
        ("c1", "career", "stable_pattern"),
        ("c2", "family_growth", "objective_state"),
        ("c3", "love_partner", "stable_pattern"),
        ("c4", "finance_resources", "objective_state"),
        ("c5", "body_emotion", "timed_event"),
    ]
    for index, (candidate_id, domain, kind) in enumerate(specs, 1):
        claim_id = f"claim_{candidate_id}"
        claims.append({"claim_id": claim_id, "claim_class": "calibration_pending"})
        candidates.append({
            "candidate_id": candidate_id,
            "domain": domain,
            "candidate_kind": kind,
            "reality_dimension": f"axis_{index}",
            "label": f"现实轴{index}",
            "time_scope": "过去五年" if kind == "timed_event" else "长期",
            "calibration_targets": ["annual_theme_activation" if kind == "timed_event" else "portrait_thesis"],
            "statement": f"第{index}种表现更接近我的经历。",
            "observable_examples": ["可以核对的行为一", "可以核对的行为二"],
            "alternative_statement": f"第{index}种表现并不常见。",
            "source_layers": ["annual"] if kind == "timed_event" else ["chart"],
            "related_claim_ids": [claim_id],
            "confidence": "to_verify",
            "validation_question": f"第{index}个现实侧面，哪一种更接近你？",
            "status": "unverified",
        })
    return {
        "analysis_meta": {"analysis_id": "v220-calibration", "core_version": "0.15.0"},
        "reality_candidate_pool": candidates,
        "report_claim_ledger": claims,
    }


def editorial_draft() -> dict:
    def section(section_id: str, text: str) -> dict:
        return {
            "id": section_id,
            "paragraphs": [text],
            "source_claim_ids": [],
            "claim_realization_map": [],
        }

    clean = "你通常会先核对条件，再用一个小范围尝试观察真实反馈，随后决定是否继续投入。"
    return {
        "draft_id": "draft-v220",
        "life_overview": section("life_overview", clean),
        "dimensions": [section(domain, clean) for domain in DOMAINS],
        "current_question": section("current_question", clean),
    }


class V220SemanticCompilerTest(unittest.TestCase):
    def test_questions_are_bound_to_the_exact_frozen_baseline(self) -> None:
        baseline = calibration_baseline()
        questions = build_questions(baseline, "事业")
        lock = {"analysis_id": "v220-calibration", "baseline_sha256": digest(baseline)}
        answers = {"responses": [{"question_number": number, "choice": "A"} for number in range(1, 6)]}

        delta = compile_delta(baseline, lock, questions, answers)

        self.assertEqual(questions["source"]["baseline_sha256"], lock["baseline_sha256"])
        self.assertEqual(len(delta["responses"]), 5)
        tampered = copy.deepcopy(questions)
        tampered["source"]["baseline_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "校准题没有绑定"):
            compile_delta(baseline, lock, tampered, answers)

    def test_question_selector_does_not_hide_a_needed_lower_ranked_domain(self) -> None:
        baseline = calibration_baseline()
        candidates = []
        claims = []
        for index in range(1, 20):
            domain = ("career", "finance_resources", "self_growth")[(index - 1) % 3] if index < 19 else "love_partner"
            kind = "timed_event" if index == 1 else "objective_state" if index == 2 else "stable_pattern"
            candidate = copy.deepcopy(baseline["reality_candidate_pool"][0])
            candidate.update({
                "candidate_id": f"pool_{index:02d}", "domain": domain, "candidate_kind": kind,
                "reality_dimension": f"pool_axis_{index}", "related_claim_ids": [f"pool_claim_{index:02d}"],
                "confidence": "high" if index < 19 else "to_verify",
            })
            candidates.append(candidate)
            claims.append({
                "claim_id": f"pool_claim_{index:02d}",
                "claim_class": "calibration_pending" if index < 19 else "primary_judgment",
            })
        baseline["reality_candidate_pool"] = candidates
        baseline["report_claim_ledger"] = claims

        questions = build_questions(baseline)

        chosen = {item["audit"]["candidate_ids"][0] for item in questions["questions"]}
        self.assertIn("pool_19", chosen)

    def test_free_text_patch_contains_only_meaning_and_updates_one_bound_candidate(self) -> None:
        baseline = calibration_baseline()
        questions = build_questions(baseline)
        candidate_id = questions["questions"][0]["audit"]["candidate_ids"][0]
        patch = {
            "schema_version": "1.0.0",
            "responses": [{
                "question_number": 1,
                "user_text": "我通常会先试一小步，再根据结果调整。",
                "facts": ["用户会先做小范围尝试"],
                "candidate_updates": [{"candidate_id": candidate_id, "status": "partial", "reason": "用户描述了条件式表现"}],
            }],
        }
        self.assertEqual(validate_free_text(patch, baseline, questions), [])

        broken = copy.deepcopy(patch)
        broken["responses"][0]["candidate_updates"] = []
        self.assertTrue(validate_free_text(broken, baseline, questions))

    def test_editor_repairs_every_flagged_paragraph_and_may_skip_clean_draft(self) -> None:
        draft = editorial_draft()
        clean_scan = scan(draft)
        edited, review = apply_editorial(draft, clean_scan, None)
        self.assertEqual(edited, draft)
        self.assertEqual(review["scan_status"], "pass")

        draft["dimensions"][0]["paragraphs"][0] = "你不是缺少行动力，而是会先反复确认条件，等自己觉得足够稳妥以后才开始推进。"
        draft["dimensions"][1]["paragraphs"][0] = "这个人通常会先核对全部要求，再决定怎样回应关系中的具体问题。"
        problem_scan = scan(draft)
        only_one = {
            "schema_version": "1.0.0",
            "draft_id": draft["draft_id"],
            "repairs": [{"slot_id": "self_growth:1", "text": "你通常会先确认关键条件，再用实际行动逐步推进，并根据结果调整后续安排。"}],
        }
        with self.assertRaisesRegex(ValueError, "全部段落"):
            apply_editorial(draft, problem_scan, only_one)

        complete = copy.deepcopy(only_one)
        complete["repairs"].append({"slot_id": "love_partner:1", "text": "你在关系里通常会先核对双方要求，再用具体沟通确认接下来怎样共同推进。"})
        _, review = apply_editorial(draft, problem_scan, complete)
        self.assertEqual(review["scan_status"], "repair_required")

    def test_report_semantic_summary_has_no_unused_duplicate_fields(self) -> None:
        schema = json.loads((ROOT / "internal/rensheng-youji-report-writer/schemas/report-semantic-patch.schema.json").read_text(encoding="utf-8"))
        summary = schema["properties"]["summary"]
        self.assertEqual(summary["required"], ["capabilities_resources"])
        self.assertNotIn("formation", summary["properties"])
        self.assertEqual(schema["properties"]["open_questions"]["minItems"], 2)

    def test_editor_scans_and_repairs_non_paragraph_report_text(self) -> None:
        draft = editorial_draft()
        semantic = {
            "summary": {"capabilities_resources": ["你能把复杂信息整理成清楚步骤。", "你能持续完成需要耐心的任务。"]},
            "stage_story": {
                "previous_foundation": "你已经积累了可以继续使用的经验。",
                "recent_development": "你不是缺少行动力，而是仍在确认条件。",
                "present_task": "你正在练习把判断变成具体行动。",
                "next_direction": "你可以先完成小范围尝试，再观察反馈。",
                "long_range": "你会逐步形成更稳定的选择方法。",
            },
            "yearly_outlook": {"summary": "未来的变化需要结合真实选择持续观察。", "years": []},
            "action_guide": {"priority_actions": [], "reduce": "减少同时准备过多方案。", "traditional_preferences": []},
            "open_questions": ["目前最重要的现实条件是什么？", "哪些经验值得继续保留？"],
        }
        combined_scan = scan(draft, semantic)
        self.assertEqual(combined_scan["issues"][0]["slot_id"], "semantic.stage_story.recent_development")
        patch = {
            "schema_version": "1.0.0",
            "draft_id": draft["draft_id"],
            "repairs": [{
                "slot_id": "semantic.stage_story.recent_development",
                "text": "你可能仍在确认关键条件，因此会先观察一段时间，再决定怎样开始行动。",
            }],
        }
        edited_draft, edited_semantic, review = apply_all_editorial(draft, semantic, combined_scan, patch)
        self.assertEqual(edited_draft, draft)
        self.assertNotEqual(edited_semantic, semantic)
        self.assertEqual(review["semantic_final_sha256"], scan(draft, edited_semantic)["semantic_sha256"])

    def test_final_report_uses_only_the_semantic_text_bound_by_editor(self) -> None:
        analysis = {
            "analysis_meta": {"analysis_id": "report-v220", "core_version": "0.15.0", "analysis_as_of": "2026-09-07"},
            "chart_facts": {"pillars": [{"stem": "甲", "branch": "戌"}] * 4},
            "chart_audit": {"boundary_dependencies": []},
            "reality_candidate_pool": [],
        }
        analysis_hash = report_digest(analysis)
        resolved = {"source": {"analysis_id": "report-v220", "analysis_sha256": analysis_hash}}
        resolved["resolved_sha256"] = report_digest(resolved)
        brief = {
            "brief_id": "brief-v220",
            "source": {"analysis_id": "report-v220", "analysis_sha256": analysis_hash, "resolved_source_sha256": resolved["resolved_sha256"]},
            "focus_scope": {"user_focus": "事业发展"},
        }
        draft = {
            "brief_id": "brief-v220", "draft_id": "draft-v220",
            "life_overview": {}, "dimensions": [], "current_question": {},
        }
        semantic = {
            "brief_id": "brief-v220",
            "summary": {"capabilities_resources": ["你能整理复杂信息。", "你能持续完成任务。"]},
            "stage_story": {}, "yearly_outlook": {}, "action_guide": {}, "open_questions": [],
        }
        baseline_sha = "b" * 64
        questions = {"schema_version": "3.0.0", "template_version": "2.0.0", "source": {"analysis_id": "report-v220", "baseline_sha256": baseline_sha}}
        delta = {"analysis_id": "report-v220", "baseline_sha256": baseline_sha, "responses": [{}] * 5, "candidate_updates": []}
        free_card = {
            "source": {"analysis_id": "report-v220", "core_version": "0.15.0", "calibrated_sha256": analysis_hash, "resolved_source_sha256": resolved["resolved_sha256"]},
            "trend_panel": {"years": []},
        }
        review = {
            "version": "2.5.0", "review_id": "review-v220", "draft_id": "draft-v220",
            "scan_status": "pass", "semantic_final_sha256": report_digest(semantic),
        }
        profile = {"gender": "男", "birthplace": "泉州", "time": {"input_local_time": "1999-01-22 17:45"}, "bazi": {"pillars": ["甲戌"] * 4, "da_yun": []}}

        report, _ = compile_report(analysis, profile, brief, draft, semantic, questions, delta, resolved, free_card, review)
        self.assertEqual(report["source_artifacts"]["report_semantic_sha256"], report_digest(semantic))
        changed = copy.deepcopy(semantic)
        changed["summary"]["capabilities_resources"][0] = "这段文字绕过了编辑记录。"
        with self.assertRaisesRegex(ValueError, "没有绑定最终使用"):
            compile_report(analysis, profile, brief, draft, changed, questions, delta, resolved, free_card, review)


if __name__ == "__main__":
    unittest.main()
