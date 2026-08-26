#!/usr/bin/env python3
"""一条命令生成新版人生卡片、报告Markdown、固定10页PDF和验收清单。"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = SKILL_ROOT.parents[1]


def run(command: list[str]) -> dict:
    result = subprocess.run(command, cwd=REPO_ROOT, text=True, capture_output=True, check=False)
    if result.returncode:
        message = result.stdout.strip() or result.stderr.strip() or "未知错误"
        raise ValueError(message)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError("生成程序没有返回可验证的JSON结果") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="生成人生有迹新版卡片与完整报告")
    parser.add_argument("--report", type=Path, required=True, help="report.json")
    parser.add_argument("--content-brief", type=Path, help="report-content-brief.json，v2.7.0及以上正式报告必填")
    parser.add_argument("--report-draft", type=Path, help="report-draft.json，v2.7.0及以上正式报告必填")
    parser.add_argument("--editorial-review", type=Path, help="editorial-review.json，v2.7.0及以上正式报告必填")
    parser.add_argument("--analysis", type=Path, help="analysis-output-calibrated.json，v2.7.0及以上正式报告必填")
    parser.add_argument("--free-card", type=Path, required=True, help="free-card-output.json")
    parser.add_argument("--calibration-questions", type=Path, required=True, help="已通过2.1.0校验的calibration-questions.json")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--keep-pages", action="store_true", help="保留10页PNG用于视觉验收")
    args = parser.parse_args()
    try:
        report = json.loads(args.report.read_text(encoding="utf-8"))
        free_card = json.loads(args.free_card.read_text(encoding="utf-8"))
        calibration_questions = json.loads(args.calibration_questions.read_text(encoding="utf-8"))
        is_traceable = report.get("schema_version") in {"2.7.0", "2.8.0"}
        if is_traceable:
            required_artifacts = {
                "--content-brief": args.content_brief,
                "--report-draft": args.report_draft,
                "--editorial-review": args.editorial_review,
                "--analysis": args.analysis,
            }
            missing = [name for name, value in required_artifacts.items() if value is None]
            if missing:
                raise ValueError("可追溯正式报告缺少来源文件：" + "、".join(missing))
            run([
                sys.executable,
                str(REPO_ROOT / "internal/rensheng-youji-report-content-brief/scripts/validate_content_brief.py"),
                str(args.content_brief), "--analysis", str(args.analysis),
            ])
            run([
                sys.executable,
                str(REPO_ROOT / "internal/rensheng-youji-report-writer/scripts/validate_report_draft.py"),
                str(args.report_draft), "--brief", str(args.content_brief),
            ])
            run([
                sys.executable,
                str(REPO_ROOT / "internal/rensheng-youji-chinese-editor/scripts/validate_editorial_review.py"),
                str(args.editorial_review), "--draft", str(args.report_draft), "--report", str(args.report),
            ])
        if calibration_questions.get("schema_version") != "2.1.0" or calibration_questions.get("template_version") != "1.0.0":
            raise ValueError("交付必须使用2.1.0固定题型校准结果")
        questions = calibration_questions.get("questions")
        responses = report.get("calibration", {}).get("responses", [])
        if not isinstance(questions, list) or len(questions) != 5:
            raise ValueError("calibration-questions.json 必须包含五道固定题型")
        if report.get("document_mode") == "full_calibrated" and len(responses) != 5:
            raise ValueError("正式报告必须包含五道校准响应")
        for index, response in enumerate(responses):
            question = questions[index]
            display, audit = question.get("display", {}), question.get("audit", {})
            if response.get("question_number") != display.get("number") or response.get("template_id") != audit.get("template_id") or response.get("domain") != display.get("domain"):
                raise ValueError(f"第{index + 1}条报告响应与固定校准题不一致")
            choice = response.get("choice")
            choices = {item.get("key"): item.get("text") for item in display.get("choices", [])}
            if response.get("selected_text") != choices.get(choice) or response.get("selected_value") != audit.get("choice_meanings", {}).get(choice):
                raise ValueError(f"第{index + 1}条报告响应的文本或值编码与用户实际选择不一致")
            expected_updates = [] if choice == "D" else audit.get("candidate_effects", {}).get(choice)
            if response.get("candidate_updates") != expected_updates:
                raise ValueError(f"第{index + 1}条报告响应没有忠实回写该选项的Core候选影响")
        report_source = report.get("source", {})
        card_source = free_card.get("source", {})
        for key in ("analysis_id", "core_version"):
            if report_source.get(key) != card_source.get(key):
                raise ValueError(f"报告与新版卡片不是来自同一Core母稿：source.{key}不一致")
        report_relationship_years = report.get("cross_output_consistency", {}).get("relationship_opportunity_years")
        card_relationship_years = [
            item.get("year")
            for item in free_card.get("trend_panel", {}).get("years", [])
            if item.get("peach", {}).get("highlight") is True
        ]
        if report_relationship_years != card_relationship_years:
            raise ValueError(
                "报告中的明显关系机会年份与新版卡片桃花年份不一致："
                f"report={report_relationship_years} card={card_relationship_years}"
            )
        output = args.out_dir.resolve()
        output.mkdir(parents=True, exist_ok=True)
        markdown = output / ("rensheng-youji-full-report.md" if report.get("document_mode") == "full_calibrated" else "rensheng-youji-preliminary.md")
        card = output / "rensheng-youji-card.png"
        pdf = output / "rensheng-youji-full-report.pdf"
        manifest = output / "report-delivery-manifest.json"

        run([sys.executable, str(REPO_ROOT / "scripts/generate_card.py"), "--input", str(args.free_card), "--output", str(card)])
        run([sys.executable, str(SKILL_ROOT / "scripts/render_report.py"), str(args.report), "--out", str(markdown)])
        files = {"card_png": str(card), "markdown": str(markdown)}
        checks = {"new_card_size": [1242, 1660], "report_json_valid": True, "relationship_years_match_card": True, "calibration_questions_match_report": True}
        if is_traceable:
            checks.update({
                "content_brief_valid": True,
                "report_draft_valid": True,
                "traceable_editorial_review_valid": True,
                "calibration_hidden_from_visible_report": True,
            })
        if report.get("document_mode") == "full_calibrated":
            command = [sys.executable, str(SKILL_ROOT / "scripts/render_report_pdf.py"), str(args.report), "--card", str(card), "--out", str(pdf)]
            if args.keep_pages:
                command.extend(["--pages-dir", str(output / "report-pages")])
            pdf_result = run(command)
            files["pdf"] = str(pdf)
            checks.update({
                "pdf_pages": pdf_result["pages"],
                "new_card_embedded_on_page": 2,
                "wechat_qr_embedded": pdf_result["wechat_embedded"],
                "wechat_asset": pdf_result["wechat_asset"],
                "wechat_sha256": pdf_result["wechat_sha256"],
                "cover_logo_embedded": pdf_result["logo_embedded"],
                "cover_logo_asset": pdf_result["logo_asset"],
                "cover_logo_sha256": pdf_result["logo_sha256"],
                "body_font": pdf_result["body_font"],
                "body_font_sha256": pdf_result["body_font_sha256"],
                "overflow": False,
            })
        else:
            checks["formal_pdf_skipped"] = "五条现实校准未完成"

        result = {
            "schema_version": "1.0.0",
            "status": "ok",
            "document_mode": report.get("document_mode"),
            "files": files,
            "checks": checks,
        }
        manifest.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({**result, "manifest": str(manifest)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
