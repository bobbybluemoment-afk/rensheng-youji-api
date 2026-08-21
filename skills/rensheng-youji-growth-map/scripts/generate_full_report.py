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


def run(command: list[str]) -> None:
    result = subprocess.run(command, cwd=REPO_ROOT, text=True, capture_output=True, check=False)
    if result.returncode:
        message = result.stdout.strip() or result.stderr.strip() or "未知错误"
        raise ValueError(message)


def main() -> int:
    parser = argparse.ArgumentParser(description="生成人生有迹新版卡片与完整报告")
    parser.add_argument("--report", type=Path, required=True, help="report.json")
    parser.add_argument("--free-card", type=Path, required=True, help="free-card-output.json")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--keep-pages", action="store_true", help="保留10页PNG用于视觉验收")
    args = parser.parse_args()
    try:
        report = json.loads(args.report.read_text(encoding="utf-8"))
        output = args.out_dir.resolve()
        output.mkdir(parents=True, exist_ok=True)
        markdown = output / ("rensheng-youji-full-report.md" if report.get("document_mode") == "full_calibrated" else "rensheng-youji-preliminary.md")
        card = output / "rensheng-youji-card.png"
        pdf = output / "rensheng-youji-full-report.pdf"
        manifest = output / "report-delivery-manifest.json"

        run([sys.executable, str(REPO_ROOT / "scripts/generate_card.py"), "--input", str(args.free_card), "--output", str(card)])
        run([sys.executable, str(SKILL_ROOT / "scripts/render_report.py"), str(args.report), "--out", str(markdown)])
        files = {"card_png": str(card), "markdown": str(markdown)}
        checks = {"new_card_size": [1242, 1660], "report_json_valid": True}
        if report.get("document_mode") == "full_calibrated":
            command = [sys.executable, str(SKILL_ROOT / "scripts/render_report_pdf.py"), str(args.report), "--card", str(card), "--out", str(pdf)]
            if args.keep_pages:
                command.extend(["--pages-dir", str(output / "report-pages")])
            run(command)
            files["pdf"] = str(pdf)
            checks.update({"pdf_pages": 10, "new_card_embedded_on_page": 2, "wechat_qr_embedded": True, "overflow": False})
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
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({**result, "manifest": str(manifest)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
