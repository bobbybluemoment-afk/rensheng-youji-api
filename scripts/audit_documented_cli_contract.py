#!/usr/bin/env python3
"""Check documented production commands against each script's required argparse options."""

from __future__ import annotations

import argparse
import ast
import json
import re
import shlex
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DOCUMENTS = (
    "skills/rensheng-youji-growth-map/SKILL.md",
    "internal/rensheng-youji-mingli-core/SKILL.md",
    "internal/rensheng-youji-mingli-core/references/core-production-bridge.md",
    "internal/rensheng-youji-report-content-brief/SKILL.md",
    "internal/rensheng-youji-report-writer/SKILL.md",
    "internal/rensheng-youji-chinese-editor/SKILL.md",
    "internal/rensheng-youji-free-card-output/SKILL.md",
)


def _parser_scopes(tree: ast.AST) -> dict[str, str]:
    scopes: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        value = node.value
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not isinstance(value, ast.Call) or not isinstance(value.func, ast.Attribute) or value.func.attr != "add_parser":
            continue
        if not value.args or not isinstance(value.args[0], ast.Constant) or not isinstance(value.args[0].value, str):
            continue
        for target in targets:
            if isinstance(target, ast.Name):
                scopes[target.id] = value.args[0].value
    return scopes


def required_options(script: Path, subcommand: str | None = None) -> set[str]:
    tree = ast.parse(script.read_text(encoding="utf-8"), filename=str(script))
    scopes = _parser_scopes(tree)
    result: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute) or node.func.attr != "add_argument":
            continue
        if not node.args or not isinstance(node.args[0], ast.Constant) or not isinstance(node.args[0].value, str):
            continue
        option = node.args[0].value
        if not option.startswith("--"):
            continue
        receiver = node.func.value.id if isinstance(node.func.value, ast.Name) else ""
        scope = scopes.get(receiver)
        if scope is not None and scope != subcommand:
            continue
        required = next((item.value.value for item in node.keywords if item.arg == "required" and isinstance(item.value, ast.Constant)), False)
        if required is True:
            result.add(option)
    return result


def documented_commands(text: str) -> list[list[str]]:
    commands: list[list[str]] = []
    for block in re.findall(r"```(?:bash|sh)\s*\n(.*?)```", text, flags=re.DOTALL):
        logical = ""
        for raw in block.splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            logical = f"{logical} {line}".strip()
            if logical.endswith("\\"):
                logical = logical[:-1].rstrip()
                continue
            try:
                tokens = shlex.split(logical)
            except ValueError:
                tokens = []
            if len(tokens) >= 3 and tokens[0] in {"python", "python3"} and tokens[1] == "scripts/run_in_env.py" and not tokens[2].startswith("-"):
                commands.append(tokens)
            logical = ""
    return commands


def audit(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    seen_scripts: set[str] = set()
    for relative in DOCUMENTS:
        path = root / relative
        if not path.is_file():
            errors.append(f"缺少生产说明文件：{relative}")
            continue
        for tokens in documented_commands(path.read_text(encoding="utf-8")):
            script_relative = tokens[2]
            script = root / script_relative
            if not script.is_file() or script.suffix != ".py":
                continue
            seen_scripts.add(script_relative)
            tree = ast.parse(script.read_text(encoding="utf-8"), filename=str(script))
            subcommands = set(_parser_scopes(tree).values())
            subcommand = tokens[3] if len(tokens) > 3 and tokens[3] in subcommands else None
            missing = sorted(required_options(script, subcommand) - {item for item in tokens[3:] if item.startswith("--")})
            if missing:
                errors.append(f"{relative}调用{script_relative}缺少脚本必填参数：{missing}")
    critical = {
        "scripts/prepare_core_synthesis.py",
        "scripts/validate_core_synthesis.py",
        "scripts/prepare_calibration_probes.py",
        "scripts/validate_calibration_probe_patch.py",
        "scripts/finalize_core_analysis.py",
        "scripts/pipeline_gate.py",
    }
    missing_coverage = sorted(critical - seen_scripts)
    if missing_coverage:
        errors.append(f"关键生产脚本没有出现在受审计说明中：{missing_coverage}")
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
