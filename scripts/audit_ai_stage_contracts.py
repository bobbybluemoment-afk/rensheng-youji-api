#!/usr/bin/env python3
"""Ensure every AI-authored production artifact has a discoverable contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def audit(root: Path, contract: dict[str, object]) -> list[str]:
    errors: list[str] = []
    for stage in contract.get("stages", []):
        if not isinstance(stage, dict) or stage.get("producer") != "ai_constrained":
            continue
        stage_id = str(stage.get("id"))
        for key in ("contract", "output_contract", "validator"):
            value = stage.get(key)
            if not isinstance(value, str) or not value:
                errors.append(f"{stage_id}缺少{key}")
                continue
            if not value.startswith("dynamic:") and not (root / value).is_file():
                errors.append(f"{stage_id}.{key}引用文件不存在：{value}")
    methods = next(
        (item for item in contract.get("stages", []) if isinstance(item, dict) and item.get("id") == "independent_methods"),
        {},
    )
    if not isinstance(methods, dict) or not methods.get("scaffold"):
        errors.append("independent_methods必须声明九方法草稿生成器")
    elif not (root / str(methods["scaffold"])).is_file():
        errors.append("independent_methods草稿生成器不存在")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        contract = json.loads((root / "internal/pipeline-contract.json").read_text(encoding="utf-8"))
        errors = audit(root, contract)
    except (OSError, json.JSONDecodeError) as exc:
        errors = [str(exc)]
    print(json.dumps({"status": "ok" if not errors else "error", "errors": errors}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
