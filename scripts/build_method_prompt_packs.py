#!/usr/bin/env python3
"""Build nine compact, isolated prompt packs without loading the full Core manual."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from core_synthesis_contract import ALL_METHODS


ROOT = Path(__file__).resolve().parent.parent
PROMPT_ROOT = ROOT / "internal/rensheng-youji-mingli-core/method-prompts"
MANIFEST = PROMPT_ROOT / "manifest.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(method_input: dict, method_id: str, manifest: dict) -> tuple[str, dict]:
    if method_id not in ALL_METHODS:
        raise ValueError(f"未知方法：{method_id}")
    method = manifest["methods"][method_id]
    common_path = ROOT / manifest["common_rules"]
    guide_path = ROOT / method["guide"]
    sources = [ROOT / item for item in method["sources"]]
    for path in [common_path, guide_path, *sources]:
        if not path.is_file():
            raise ValueError(f"方法提示引用不存在：{path.relative_to(ROOT)}")
    source_receipt = [
        {"path": str(path.relative_to(ROOT)), "sha256": digest(path)} for path in sources
    ]
    prompt = "\n\n".join([
        f"# 人生有迹独立方法任务：{method_id}",
        "本提示包已经从完整规则中按方法提炼。运行时不要再读取完整Core Skill、其他方法提示、完整Core Schema、校准或报告文件。",
        common_path.read_text(encoding="utf-8").strip(),
        guide_path.read_text(encoding="utf-8").strip(),
        "## 规则来源回执\n\n" + json.dumps(source_receipt, ensure_ascii=False, indent=2),
        "## 本次唯一输入：method-input.json\n\n```json\n" + json.dumps(method_input, ensure_ascii=False, indent=2) + "\n```",
    ]) + "\n"
    receipt = {
        "method_id": method_id,
        "guide": method["guide"],
        "sources": source_receipt,
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "prompt_bytes": len(prompt.encode("utf-8")),
    }
    return prompt, receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("method_input", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        method_input = json.loads(args.method_input.read_text(encoding="utf-8"))
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        if set(manifest.get("methods") or {}) != ALL_METHODS:
            raise ValueError("方法提示清单必须恰好包含九种方法")
        args.output_dir.mkdir(parents=True, exist_ok=True)
        receipts = []
        for method_id in sorted(ALL_METHODS):
            prompt, receipt = build(method_input, method_id, manifest)
            (args.output_dir / f"{method_id}.prompt.md").write_text(prompt, encoding="utf-8")
            receipts.append(receipt)
        result = {"schema_version": "1.0.0", "prompt_count": 9, "methods": receipts}
        (args.output_dir / "prompt-pack-manifest.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "ok", "output_dir": str(args.output_dir), "prompt_count": 9}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
