#!/usr/bin/env python3
"""Deterministically assemble the final report around AI-authored semantic prose."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def compile_report(analysis: dict[str, Any], profile: dict[str, Any], brief: dict[str, Any], draft: dict[str, Any], semantic: dict[str, Any], questions: dict[str, Any], delta: dict[str, Any], resolved: dict[str, Any], free_card: dict[str, Any], review: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    if semantic.get("brief_id") != brief.get("brief_id") or draft.get("brief_id") != brief.get("brief_id"):
        raise ValueError("最终报告输入没有绑定同一份事实提纲")
    meta = analysis["analysis_meta"]
    if meta.get("core_version") != "0.15.0":
        raise ValueError("2.14.0报告只能由0.15.0 Core编译")
    if brief.get("source", {}).get("analysis_id") != meta.get("analysis_id") or resolved.get("source", {}).get("analysis_id") != meta.get("analysis_id"):
        raise ValueError("事实提纲或报告选材没有绑定当前Core")
    analysis_hash = digest(analysis)
    if brief.get("source", {}).get("analysis_sha256") != analysis_hash or resolved.get("source", {}).get("analysis_sha256") != analysis_hash:
        raise ValueError("事实提纲或报告选材没有绑定当前Core哈希")
    resolved_hash = digest({key: value for key, value in resolved.items() if key != "resolved_sha256"})
    if resolved.get("resolved_sha256") != resolved_hash or brief.get("source", {}).get("resolved_source_sha256") != resolved_hash:
        raise ValueError("报告选材哈希无效，或事实提纲没有绑定同一份选材")
    if free_card.get("source", {}).get("analysis_id") != meta.get("analysis_id") or free_card.get("source", {}).get("core_version") != meta.get("core_version"):
        raise ValueError("卡片与最终报告不是来自同一Core")
    if free_card.get("source", {}).get("calibrated_sha256") != analysis_hash or free_card.get("source", {}).get("resolved_source_sha256") != resolved_hash:
        raise ValueError("卡片可见内容没有绑定当前校准后Core和报告选材")
    if questions.get("schema_version") != "3.0.0" or questions.get("template_version") != "2.0.0":
        raise ValueError("最终报告必须使用3.0.0个性化确定性校准题")
    if delta.get("analysis_id") != meta.get("analysis_id") or len(delta.get("responses") or []) != 5:
        raise ValueError("校准增量没有绑定当前Core或缺少五题响应")
    if questions.get("source") != {"analysis_id": meta.get("analysis_id"), "baseline_sha256": delta.get("baseline_sha256")}:
        raise ValueError("校准题与校准增量不是来自同一冻结Baseline")
    if review.get("draft_id") != draft.get("draft_id"):
        raise ValueError("中文编辑记录没有绑定当前报告初稿")
    if review.get("version") != "2.5.0" or review.get("scan_status") not in {"pass", "repair_required"}:
        raise ValueError("最终报告必须使用2.5.0按需中文编辑记录")
    if review.get("semantic_final_sha256") != digest(semantic):
        raise ValueError("中文编辑记录没有绑定最终使用的报告语义文字")
    focus = brief.get("focus_scope", {}).get("user_focus", "")
    report_id = "report-" + digest({"analysis": meta["analysis_id"], "draft": draft["draft_id"], "review": review["review_id"]})[:16]
    pillars = profile.get("bazi", {}).get("pillars") or [item.get("stem", "") + item.get("branch", "") for item in analysis["chart_facts"]["pillars"]]
    year = int(meta["analysis_as_of"][:4])
    current_luck = next((item for item in profile.get("bazi", {}).get("da_yun") or [] if item.get("start_year", 9999) <= year <= item.get("end_year", -1)), None)
    relationship_years = [item.get("year") for item in free_card.get("trend_panel", {}).get("years", []) if item.get("peach", {}).get("highlight") is True]
    summary = dict(semantic["summary"])
    summary["life_overview"] = draft["life_overview"]
    candidate_index = {item["candidate_id"]: item for item in analysis.get("reality_candidate_pool") or []}
    status_groups = {"match": "confirmed", "partial": "partial", "reject": "rejected", "uncertain": "uncertain"}
    calibrated_text = {key: [] for key in ("confirmed", "partial", "rejected", "uncertain")}
    for update in delta.get("candidate_updates") or []:
        candidate = candidate_index.get(update.get("candidate_id"), {})
        text = str(candidate.get("statement") or candidate.get("label") or "该现实侧面仍待核对")
        calibrated_text[status_groups.get(update.get("status"), "uncertain")].append(text)
    report = {
        "schema_version": "2.14.0", "report_id": report_id, "document_mode": "full_calibrated",
        "source": {"analysis_id": meta["analysis_id"], "core_version": meta["core_version"], "analysis_as_of": meta["analysis_as_of"], "calibration_status": "calibrated"},
        "source_artifacts": {"content_brief_id": brief["brief_id"], "report_draft_id": draft["draft_id"], "editorial_review_id": review["review_id"], "resolved_source_sha256": resolved["resolved_sha256"], "report_semantic_sha256": digest(semantic)},
        "title": "人生有迹｜完整报告", "subtitle": "看见你带来的能力，理解你走过的路，也寻找新的可能",
        "generated_on": meta["analysis_as_of"], "brand": "人生有迹 by 景行",
        "profile": {"name": profile.get("name", ""), "identity_option": profile.get("gender", ""), "birth": profile.get("time", {}).get("input_local_time", ""), "location": profile.get("birthplace", ""), "focus": focus, "question": focus},
        "focus_scope": {"selected_focus": focus, "protected_sections": ["life_overview", "dimensions"], "emphasis_sections": ["current_question_narrative", "stage_story.present_task", "stage_story.next_direction", "yearly_outlook", "action_guide.priority_actions"], "topic_keywords": [focus] if focus else []},
        "cross_output_consistency": {"relationship_opportunity_years": relationship_years},
        "chart": {"pillars": pillars, "luck_start": profile.get("bazi", {}).get("luck_start_local_time", ""), "current_luck_cycle": f"{current_luck['pillar']}（{current_luck['start_year']}—{current_luck['end_year']}）" if current_luck else "当前阶段待核对", "time_basis": profile.get("time", {}).get("note", "已按确定性排盘口径处理"), "uncertainty": "；".join(analysis.get("chart_audit", {}).get("boundary_dependencies") or ["不接近关键时间边界"]), "formal_report_allowed": True},
        "calibration": {"question_schema_version": questions["schema_version"], "template_version": questions["template_version"], "summary": "五道校准题已用于确认现实候选的主次。", "birth_time_status": "稳定", "responses": delta.get("responses") or [], **calibrated_text},
        "editorial_review": {"version": "2.5.0", "review_id": review["review_id"]},
        "executive_summary": summary, "current_question_narrative": draft["current_question"],
        "stage_story": semantic["stage_story"], "dimensions": draft["dimensions"],
        "yearly_outlook": semantic["yearly_outlook"], "action_guide": semantic["action_guide"],
        "open_questions": semantic["open_questions"],
        "assisted_service_note": "本Skill可免费自行生成；如果你的AI无法运行Skill，或希望获得人工校准、PDF整理和问题解释，可以联系景行。",
        "author": {"name": "景行", "bio": "持续整理传统命理与现实经历之间可以核对的联系。", "github": "https://github.com/bobbybluemoment-afk/rensheng-youji-api", "web": "https://rensheng-youji-web.bobbybluemoment.workers.dev", "wechat_image": "assets/wechat-contact.jpg", "wechat_note": "添加时建议备注：人生有迹"},
        "boundaries": ["本报告用于传统文化体验与自我观察，不构成医疗、心理、法律、投资或其他专业意见。", "报告提供的是有条件、可验证的倾向，不代表唯一解释或必然命运。"],
    }
    updated_review = json.loads(json.dumps(review, ensure_ascii=False))
    updated_review["final_report_id"] = report_id
    return report, updated_review


def main() -> int:
    parser = argparse.ArgumentParser()
    for name in ("analysis", "profile", "brief", "draft", "semantic", "questions", "delta", "resolved", "free_card", "review"):
        parser.add_argument("--" + name.replace("_", "-"), dest=name, type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True); parser.add_argument("--review-output", type=Path, required=True)
    args = parser.parse_args()
    try:
        load=lambda p: json.loads(p.read_text(encoding="utf-8"))
        report, review = compile_report(*[load(getattr(args, name)) for name in ("analysis", "profile", "brief", "draft", "semantic", "questions", "delta", "resolved", "free_card", "review")])
        args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        args.review_output.write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8")
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status":"error","message":str(exc)}, ensure_ascii=False)); return 1
    print(json.dumps({"status":"ok","output":str(args.output),"review":str(args.review_output)}, ensure_ascii=False)); return 0


if __name__ == "__main__": raise SystemExit(main())
