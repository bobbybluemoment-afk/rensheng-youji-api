#!/usr/bin/env python3
"""Audit the repository-local Python runtime contract in production instructions."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
COMMAND = re.compile(r"^\s*(python3?|py)\s+([^\s`]+)", re.MULTILINE)
ALLOWED_TARGETS = {"scripts/setup_env.py", "scripts/run_in_env.py"}


def audit(root: Path) -> list[str]:
    errors: list[str] = []
    required = [
        root / "scripts/setup_env.py",
        root / "scripts/run_in_env.py",
        root / "scripts/check_env.py",
    ]
    for path in required:
        if not path.is_file():
            errors.append(f"运行入口文件不存在：{path.relative_to(root)}")

    instruction_files = [root / "README.md", root / "SKILL.md"]
    instruction_files.extend((root / "skills").rglob("*.md"))
    instruction_files.extend((root / "internal").rglob("*.md"))
    for path in instruction_files:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for match in COMMAND.finditer(text):
            target = match.group(2).replace("\\", "/")
            if target not in ALLOWED_TARGETS:
                line = text.count("\n", 0, match.start()) + 1
                errors.append(
                    f"{path.relative_to(root)}:{line} 绕过仓库运行入口：{match.group(0).strip()}"
                )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", type=Path, default=ROOT)
    args = parser.parse_args()
    errors = audit(args.root.resolve())
    print(json.dumps({"status": "ok" if not errors else "error", "errors": errors}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
