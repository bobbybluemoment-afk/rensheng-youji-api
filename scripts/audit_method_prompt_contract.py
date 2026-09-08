#!/usr/bin/env python3
"""Audit that nine compact method prompts stay isolated, complete and small."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from core_synthesis_contract import ALL_METHODS
from method_input_contract import METHOD_INPUT_PROFILES


ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "internal/rensheng-youji-mingli-core/method-prompts/manifest.json"
FORBIDDEN_SOURCES = {
    "internal/rensheng-youji-mingli-core/references/calibration-confidence.md",
    "internal/rensheng-youji-mingli-core/references/candidate-relations-and-calibrated-synthesis.md",
    "internal/rensheng-youji-mingli-core/references/core-production-bridge.md",
    "internal/rensheng-youji-mingli-core/references/post-calibration-report-selection.md",
    "internal/rensheng-youji-mingli-core/references/report-grade-reality-mapping.md",
}


def audit(root: Path) -> list[str]:
    errors: list[str] = []
    manifest = json.loads((root / MANIFEST.relative_to(ROOT)).read_text(encoding="utf-8"))
    if manifest.get("schema_version") != "1.0.0":
        errors.append("方法提示清单版本必须为1.0.0")
    methods = manifest.get("methods") or {}
    if set(methods) != ALL_METHODS:
        errors.append("方法提示清单必须恰好包含九种方法")
    common = root / str(manifest.get("common_rules"))
    if not common.is_file():
        errors.append("缺少九方法共同短规则")
    else:
        text = common.read_text(encoding="utf-8")
        for required in (
            "不得读取用户关注问题", "不得读取", "其他方法结果", "domain_limits",
            "只输出 JSON", "8—14条", "最多18条", "最多12条",
        ):
            if required not in text:
                errors.append(f"共同短规则缺少关键边界：{required}")
        if common.stat().st_size > 7000:
            errors.append("共同短规则超过7000字节，已经失去精简作用")
    for method_id, item in methods.items():
        if item.get("input_profile") != METHOD_INPUT_PROFILES.get(method_id):
            errors.append(f"{method_id}输入画像与确定性投影契约不一致")
        guide = root / str(item.get("guide"))
        if not guide.is_file():
            errors.append(f"{method_id}缺少专用提示")
            continue
        guide_text = guide.read_text(encoding="utf-8")
        if method_id not in guide_text:
            errors.append(f"{method_id}专用提示没有声明自身方法编号")
        if guide.stat().st_size > 3500:
            errors.append(f"{method_id}专用提示超过3500字节")
        sources = set(item.get("sources") or [])
        if not sources:
            errors.append(f"{method_id}没有登记完整规则来源")
        if sources & FORBIDDEN_SOURCES:
            errors.append(f"{method_id}错误引用了校准、综合或报告阶段规则")
        for source in sources:
            if not (root / source).is_file():
                errors.append(f"{method_id}规则来源不存在：{source}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        errors = audit(args.root.resolve())
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        errors = [str(exc)]
    print(json.dumps({"status": "ok" if not errors else "error", "errors": errors}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
