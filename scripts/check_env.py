#!/usr/bin/env python3
"""检查依赖、字体、排盘与新版免费卡片链路是否可用。"""

from __future__ import annotations

import sys
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))


def main() -> int:
    reference_test = subprocess.run(
        [sys.executable, str(ROOT / "scripts/audit_skill_references.py"), str(ROOT)],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    if reference_test.returncode:
        print("FAILED: Skill declares a missing local dependency")
        print(reference_test.stdout or reference_test.stderr)
        return 1
    pipeline_test = subprocess.run(
        [sys.executable, str(ROOT / "scripts/audit_pipeline_contract.py"), str(ROOT)],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    if pipeline_test.returncode:
        print("FAILED: production pipeline contains an unproduced input or missing stage contract")
        print(pipeline_test.stdout or pipeline_test.stderr)
        return 1
    runtime_test = subprocess.run(
        [sys.executable, str(ROOT / "scripts/audit_runtime_entry.py"), str(ROOT)],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    if runtime_test.returncode:
        print("FAILED: production instructions bypass the repository Python runtime")
        print(runtime_test.stdout or runtime_test.stderr)
        return 1
    ai_contract_test = subprocess.run(
        [sys.executable, str(ROOT / "scripts/audit_ai_stage_contracts.py"), str(ROOT)],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    if ai_contract_test.returncode:
        print("FAILED: an AI-authored production stage lacks a discoverable output contract")
        print(ai_contract_test.stdout or ai_contract_test.stderr)
        return 1
    method_schema_test = subprocess.run(
        [sys.executable, str(ROOT / "scripts/export_method_packet_schema.py"), "--check"],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    if method_schema_test.returncode:
        print("FAILED: standalone method packet schema differs from canonical Core definitions")
        print(method_schema_test.stdout or method_schema_test.stderr)
        return 1
    try:
        import lunar_python  # noqa: F401
        from PIL import Image  # noqa: F401
    except ImportError as exc:
        print(f"MISSING: {exc.name}")
        return 2

    required = [
        ROOT / "assets/icon.svg",
        ROOT / "assets/fonts/noto/NotoSansCJKsc-Regular.otf",
        ROOT / "assets/fonts/lxgw/LXGWWenKai-Regular.ttf",
        ROOT / "internal/rensheng-youji-mingli-core/SKILL.md",
        ROOT / "internal/rensheng-youji-mingli-core/references/method-failure-and-recovery.md",
        ROOT / "internal/rensheng-youji-mingli-core/references/core-production-bridge.md",
        ROOT / "internal/rensheng-youji-mingli-core/scripts/validate_method_packet.py",
        ROOT / "internal/rensheng-youji-mingli-core/schemas/method-packet.schema.json",
        ROOT / "internal/rensheng-youji-report-content-brief/SKILL.md",
        ROOT / "internal/rensheng-youji-report-content-brief/scripts/materialize_content_brief.py",
        ROOT / "internal/rensheng-youji-report-writer/SKILL.md",
        ROOT / "internal/rensheng-youji-chinese-editor/SKILL.md",
        ROOT / "internal/rensheng-youji-free-card-output/SKILL.md",
        ROOT / "internal/rensheng-youji-free-card-renderer/SKILL.md",
        ROOT / "skills/rensheng-youji-growth-map/SKILL.md",
        ROOT / "skills/rensheng-youji-growth-map/references/production-failure-policy.md",
        ROOT / "skills/rensheng-youji-growth-map/references/calibration-question-templates.json",
        ROOT / "skills/rensheng-youji-growth-map/scripts/build_calibration_questions.py",
        ROOT / "skills/rensheng-youji-growth-map/scripts/validate_calibration_questions.py",
        ROOT / "skills/rensheng-youji-growth-map/scripts/generate_full_report.py",
        ROOT / "skills/rensheng-youji-growth-map/scripts/render_report_pdf.py",
        ROOT / "scripts/core_baseline.py",
        ROOT / "internal/pipeline-contract.json",
        ROOT / "scripts/audit_pipeline_contract.py",
        ROOT / "scripts/core_synthesis_contract.py",
        ROOT / "scripts/run_in_env.py",
        ROOT / "scripts/audit_runtime_entry.py",
        ROOT / "scripts/audit_ai_stage_contracts.py",
        ROOT / "scripts/create_report_run.py",
        ROOT / "scripts/report_pipeline.py",
        ROOT / "scripts/export_method_packet_schema.py",
        ROOT / "scripts/initialize_method_packets.py",
        ROOT / "scripts/method_input_contract.py",
        ROOT / "scripts/prepare_method_input.py",
        ROOT / "scripts/prepare_core_synthesis.py",
        ROOT / "scripts/validate_core_synthesis.py",
        ROOT / "scripts/finalize_core_analysis.py",
        ROOT / "scripts/build_report_source_bundle.py",
        ROOT / "scripts/apply_calibration_delta.py",
        ROOT / "scripts/resolve_report_sources.py",
        ROOT / "scripts/report_source_contract.py",
        ROOT / "scripts/audit_claim_diversity.py",
        ROOT / "scripts/audit_report_claim_coverage.py",
        ROOT / "scripts/audit_skill_references.py",
        ROOT / "assets/wechat-contact.jpg",
        ROOT / "assets/rensheng-youji-logo.png",
        ROOT / "assets/asset-manifest.json",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        print("MISSING_ASSET: " + ", ".join(missing))
        return 3

    from rensheng_youji.local_engine import build_profile

    profile = build_profile(
        name="",
        birth="1999-01-22 17:45",
        gender="male",
        city="北京",
        time_basis="true_solar_adjusted",
        center_year=2026,
    )
    if profile["bazi"]["pillars"] != ["戊寅", "乙丑", "甲戌", "癸酉"]:
        print("FAILED: known chart mismatch")
        return 4
    timeline = profile["life_kline"]["timeline"]
    if len(timeline) != 20 or timeline[5]["year"] != 2026:
        print("FAILED: timeline mismatch")
        return 5
    report_test = subprocess.run(
        [
            sys.executable,
            "-m",
            "unittest",
            "tests.test_report_v27_pipeline.ReportV27PipelineTest.test_v27_full_delivery",
            "tests.test_report_v28_traceability.ReportV28TraceabilityTest",
            "tests.test_report_v211_delivery_safety.ReportV211DeliverySafetyTest",
            "tests.test_report_v212_core_traceability.ReportV212CoreTraceabilityTest",
            "tests.test_report_v213_post_calibration_selection.ReportV213PostCalibrationSelectionTest",
            "tests.test_core_v011_method_recovery.CoreV011MethodRecoveryTest",
            "tests.test_core_v012_production_bridge.CoreV012ProductionBridgeTest",
            "tests.test_pipeline_contract.PipelineContractTest",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if report_test.returncode:
        print("FAILED: report traceability, writing, editorial or fixed 10-page report pipeline")
        print(report_test.stdout or report_test.stderr)
        return 6
    core_test = subprocess.run(
        [sys.executable, str(ROOT / "internal/rensheng-youji-mingli-core/scripts/validate_analysis_output.py"), "--self-test"],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    if core_test.returncode:
        print("FAILED: v0.14.0 Core topic isolation, domain review, source coverage, synthesis validation or deterministic assembly")
        print(core_test.stdout or core_test.stderr)
        return 7
    print("READY: dependencies, chart, v2 card, Core v0.14.0 topic isolation, eight-domain method review, source coverage, semantic consensus, deterministic assembly and report sources, calibration delta, post-calibration source resolution, sparse emphasis, stable fallback and fixed 10-page report pipeline passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
