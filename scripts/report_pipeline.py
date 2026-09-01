#!/usr/bin/env python3
"""Report the next declared production stage for a persistent report run."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CORE_SCRIPTS = ROOT / "internal/rensheng-youji-mingli-core/scripts"
sys.path.insert(0, str(CORE_SCRIPTS))

from validate_method_packet import validate as validate_method_packet  # noqa: E402
STAGES = [
    ("core_input", "deterministic", ("core-input.json", "profile.json"), "scripts/prepare_core_input.py"),
    ("time_preflight", "deterministic", ("report-preflight.json",), "skills/rensheng-youji-growth-map/scripts/preflight_report.py"),
    ("method_input", "deterministic", ("method-input.json",), "scripts/prepare_method_input.py"),
    ("method_packet_drafts", "deterministic", ("method-packet-drafts",), "scripts/initialize_method_packets.py"),
    ("independent_methods", "ai_constrained", ("method-packets",), "internal/rensheng-youji-mingli-core/schemas/method-packet.schema.json"),
    ("synthesis_input", "deterministic", ("core-synthesis-input.json",), "scripts/prepare_core_synthesis.py"),
    ("semantic_synthesis", "ai_constrained", ("core-semantic-analysis.json",), "internal/rensheng-youji-mingli-core/references/core-production-bridge.md"),
    ("initial_core", "deterministic", ("analysis-output-initial.json",), "scripts/finalize_core_analysis.py"),
    ("baseline_freeze", "deterministic", ("analysis-baseline.json", "analysis-baseline-lock.json"), "scripts/core_baseline.py"),
    ("calibration_plan", "ai_constrained", ("calibration-plan.json",), "skills/rensheng-youji-growth-map/references/calibration.md"),
    ("calibration_questions", "deterministic", ("calibration-questions.json", "calibration-visible.md"), "skills/rensheng-youji-growth-map/scripts/build_calibration_questions.py"),
    ("calibration_delta", "ai_constrained", ("calibration-delta.json",), "skills/rensheng-youji-growth-map/SKILL.md"),
    ("calibrated_core", "deterministic", ("analysis-output-calibrated.json",), "scripts/apply_calibration_delta.py"),
    ("report_sources", "deterministic", ("resolved-report-sources.json",), "scripts/resolve_report_sources.py"),
    ("content_selection", "ai_constrained", ("report-content-selection.json",), "internal/rensheng-youji-report-content-brief/SKILL.md"),
    ("content_brief", "deterministic", ("report-content-brief.json",), "internal/rensheng-youji-report-content-brief/scripts/materialize_content_brief.py"),
    ("report_draft", "ai_constrained", ("report-draft.json",), "internal/rensheng-youji-report-writer/SKILL.md"),
    ("edited_report", "ai_constrained", ("report.json", "editorial-review.json"), "internal/rensheng-youji-chinese-editor/SKILL.md"),
    ("free_card_semantics", "ai_constrained", ("card-content.json", "visual-signals.json"), "internal/rensheng-youji-free-card-output/SKILL.md"),
    ("free_card_visual_series", "deterministic", ("visual-series.json",), "internal/rensheng-youji-free-card-output/scripts/build_visual_series.py"),
    ("free_card_output", "deterministic", ("free-card-output.json",), "scripts/assemble_free_card.py"),
    ("delivery", "deterministic", ("delivery/report-delivery-manifest.json",), "skills/rensheng-youji-growth-map/scripts/generate_full_report.py"),
]


def status(run_dir: Path) -> dict[str, object]:
    run_dir = run_dir.resolve()
    expected_root = (ROOT / "work/runs").resolve()
    if expected_root not in run_dir.parents:
        raise ValueError("run_dir必须位于当前仓库work/runs内")
    state_path = run_dir / "run-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    if state.get("repo_root") != str(ROOT) or state.get("work_dir") != str(run_dir):
        raise ValueError("运行状态与当前仓库或目录不一致")
    for stage_id, producer, artifacts, contract in STAGES:
        paths = [run_dir / artifact for artifact in artifacts]
        path = paths[0]
        complete = all(item.is_file() for item in paths)
        if stage_id == "method_packet_drafts":
            complete = path.is_dir() and len(list(path.glob("*.draft.json"))) == 9
        elif stage_id == "independent_methods":
            complete = path.is_dir() and len(list(path.glob("*.json"))) == 9
            if complete:
                packet_errors: list[str] = []
                for packet_path in sorted(path.glob("*.json")):
                    try:
                        packet = json.loads(packet_path.read_text(encoding="utf-8"))
                        errors = validate_method_packet(packet, packet_path.stem)
                    except (OSError, json.JSONDecodeError) as exc:
                        errors = [str(exc)]
                    packet_errors.extend(f"{packet_path.name}: {item}" for item in errors)
                if packet_errors:
                    return {
                        "status": "in_progress",
                        "run_id": state["run_id"],
                        "next_stage": stage_id,
                        "producer": producer,
                        "required_artifacts": [str(item) for item in paths],
                        "contract_or_script": contract,
                        "validation_errors": packet_errors,
                    }
        if not complete:
            return {
                "status": "in_progress",
                "run_id": state["run_id"],
                "next_stage": stage_id,
                "producer": producer,
                "required_artifacts": [str(item) for item in paths],
                "contract_or_script": contract,
            }
    return {"status": "complete", "run_id": state["run_id"], "next_stage": None}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["status"])
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = status(args.run_dir)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        result = {"status": "error", "message": str(exc)}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
