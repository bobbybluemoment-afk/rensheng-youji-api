#!/usr/bin/env python3
"""Run one concise production gate and record a hash-bound resume checkpoint."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "internal/rensheng-youji-mingli-core/scripts"))
from core_synthesis_contract import ALL_METHODS, canonical_digest  # noqa: E402
from core_baseline import digest as core_digest, validate_quality_audit, verify as verify_baseline  # noqa: E402
from run_checkpoint import record as record_checkpoint  # noqa: E402
from validate_method_packet import validate as validate_method_packet  # noqa: E402
from validate_method_semantic_patch import validate as validate_method_semantic_patch  # noqa: E402
from method_structure_contract import structure_summary  # noqa: E402
from validate_calibration_probe_patch import validate as validate_calibration_probe_patch  # noqa: E402


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def run(script: str, *args: str) -> list[str]:
    result = subprocess.run([sys.executable, str(ROOT / script), *args], cwd=ROOT, text=True, capture_output=True, check=False)
    if result.returncode == 0:
        return []
    try:
        payload = json.loads(result.stdout)
        return [str(item) for item in payload.get("errors") or [payload.get("message") or result.stderr.strip()]]
    except json.JSONDecodeError:
        return [result.stdout.strip() or result.stderr.strip() or f"{script}失败"]


def method_gate(work: Path) -> tuple[list[str], list[Path], list[Path]]:
    errors: list[str] = []
    gate_path = work / "method-gate.json"
    gate = load(gate_path)
    packets = {}
    patches = {}
    for method_id in sorted(ALL_METHODS):
        semantic_path = work / "method-semantic-patches" / f"{method_id}.json"
        patch = load(semantic_path)
        patches[method_id] = patch
        errors.extend(f"{method_id}语义答卷: {item}" for item in validate_method_semantic_patch(patch, method_id))
        path = work / "method-packets" / f"{method_id}.json"
        packet = load(path)
        packets[method_id] = packet
        errors.extend(f"{method_id}: {item}" for item in validate_method_packet(packet, method_id))
    actual = {method_id: canonical_digest(packet) for method_id, packet in packets.items()}
    if gate.get("status") != "pass" or gate.get("packet_count") != 9 or gate.get("packet_sha256_by_method") != actual:
        errors.append("method-gate.json与当前九个方法包不一致")
    semantic_hashes = {method_id: canonical_digest(patch) for method_id, patch in patches.items()}
    structure_summaries = {
        method_id: structure_summary(patches[method_id])
        for method_id in sorted(ALL_METHODS)
    }
    if gate.get("method_semantic_schema_version") != "1.1.0":
        errors.append("method-gate.json未登记重要结构检查契约1.1.0")
    if gate.get("semantic_patch_sha256_by_method") != semantic_hashes:
        errors.append("method-gate.json与当前九份语义答卷哈希不一致")
    if gate.get("structure_check_summary_by_method") != structure_summaries:
        errors.append("method-gate.json与当前九份重要结构检查结果不一致")
    return errors, [work / "method-input.json", work / "method-prompt-packs", work / "method-semantic-patches"], [work / "method-packets", gate_path]


def core_gate(work: Path) -> tuple[list[str], list[Path], list[Path]]:
    analysis = work / "analysis-output-initial.json"
    audit = work / "core-quality-audit.json"
    errors = run("internal/rensheng-youji-mingli-core/scripts/validate_analysis_output.py", str(analysis))
    try:
        validate_quality_audit(analysis, audit)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        errors.append(str(exc))
    try:
        errors.extend(validate_calibration_probe_patch(
            load(work / "calibration-probe-input.json"),
            load(work / "calibration-probe-patch.json"),
        ))
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        errors.append(str(exc))
    baseline, lock = work / "analysis-baseline.json", work / "analysis-baseline-lock.json"
    outputs = [analysis, audit, baseline, lock]
    try:
        if load(baseline) != load(analysis):
            errors.append("冻结Baseline与通过审计的初始Core不一致")
        if core_digest(load(baseline)) != load(lock).get("baseline_sha256"):
            errors.append("冻结Baseline与锁文件哈希不一致")
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        errors.append(str(exc))
    return errors, [
        work / "core-synthesis-input.json",
        work / "core-compiler-source.json",
        work / "core-semantic-analysis.json",
        work / "calibration-probe-input.json",
        work / "calibration-probe-patch.json",
    ], outputs


def calibration_gate(work: Path) -> tuple[list[str], list[Path], list[Path]]:
    baseline, lock = work / "analysis-baseline.json", work / "analysis-baseline-lock.json"
    calibrated = work / "analysis-output-calibrated.json"
    errors: list[str] = []
    try:
        verify_baseline(baseline, lock, calibrated)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        errors.append(str(exc))
    errors.extend(run(
        "skills/rensheng-youji-growth-map/scripts/validate_calibration_questions.py",
        str(work / "calibration-questions.json"), "--analysis", str(baseline),
    ))
    inputs = [
        baseline,
        lock,
        work / "calibration-questions.json",
        work / "calibration-answers.json",
        work / "calibration-delta.json",
    ]
    free_text = work / "calibration-free-text-patch.json"
    if free_text.is_file():
        inputs.append(free_text)
    return errors, inputs, [calibrated]


def report_gate(work: Path) -> tuple[list[str], list[Path], list[Path]]:
    analysis = work / "analysis-output-calibrated.json"
    resolved = work / "resolved-report-sources.json"
    brief = work / "report-content-brief.json"
    draft = work / "report-draft.json"
    report = work / "report.json"
    review = work / "editorial-review-final.json"
    errors = run(
        "internal/rensheng-youji-report-content-brief/scripts/validate_content_brief.py",
        str(brief), "--analysis", str(analysis), "--resolved-sources", str(resolved),
    )
    errors.extend(run(
        "internal/rensheng-youji-report-writer/scripts/validate_report_draft.py",
        str(draft), "--brief", str(brief),
    ))
    errors.extend(run(
        "internal/rensheng-youji-chinese-editor/scripts/validate_editorial_review.py",
        str(review), "--draft", str(draft), "--report", str(report),
    ))
    errors.extend(run(
        "skills/rensheng-youji-growth-map/scripts/render_report.py",
        str(report), "--out", str(work / "report-gate-preview.md"),
    ))
    inputs = [
        analysis,
        work / "profile.json",
        resolved,
        brief,
        draft,
        work / "edited-report-draft.json",
        work / "edited-report-semantic.json",
        work / "calibration-questions.json",
        work / "calibration-delta.json",
        work / "free-card-output.json",
        work / "editorial-review.json",
    ]
    return errors, inputs, [report, review]


def delivery_gate(work: Path) -> tuple[list[str], list[Path], list[Path]]:
    manifest_path = work / "delivery/report-delivery-manifest.json"
    manifest = load(manifest_path)
    errors = [] if manifest.get("status") == "ok" else ["交付清单status不是ok"]
    outputs = [manifest_path]
    for label, raw in (manifest.get("files") or {}).items():
        path = Path(str(raw))
        if not path.is_absolute():
            path = ROOT / path
        if not path.is_file():
            errors.append(f"交付文件不存在：{label}")
        else:
            outputs.append(path)
    return errors, [
        work / "analysis-output-calibrated.json",
        work / "analysis-baseline.json",
        work / "analysis-baseline-lock.json",
        work / "calibration-delta.json",
        work / "calibration-questions.json",
        work / "resolved-report-sources.json",
        work / "report-content-brief.json",
        work / "report-draft.json",
        work / "report.json",
        work / "editorial-review-final.json",
        work / "free-card-output.json",
    ], outputs


GATES = {
    "METHOD_GATE": method_gate,
    "CORE_GATE": core_gate,
    "CALIBRATION_GATE": calibration_gate,
    "REPORT_GATE": report_gate,
    "DELIVERY_GATE": delivery_gate,
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gate", choices=sorted(GATES), required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        errors, inputs, outputs = GATES[args.gate](args.run_dir.resolve())
        if not errors:
            record_checkpoint(args.run_dir, args.gate, inputs, outputs)
        payload = {"gate": args.gate, "status": "PASS" if not errors else "FAIL", "errors": errors}
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        payload = {"gate": args.gate, "status": "FAIL", "errors": [str(exc)]}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
