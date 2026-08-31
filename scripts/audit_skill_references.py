#!/usr/bin/env python3
"""Audit local Markdown dependencies reachable from every Skill entrypoint."""

from __future__ import annotations

import argparse
import json
import re
from collections import deque
from pathlib import Path
from urllib.parse import unquote


LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
IGNORED_PREFIXES = ("http://", "https://", "mailto:", "sandbox:", "#")


def local_target(source: Path, raw: str) -> Path | None:
    value = raw.strip().strip("<>").split("#", 1)[0].split("?", 1)[0]
    if not value or value.startswith(IGNORED_PREFIXES):
        return None
    return (source.parent / unquote(value)).resolve()


def audit(root: Path) -> list[str]:
    root = root.resolve()
    entries = [root / "SKILL.md"] if (root / "SKILL.md").is_file() else []
    entries += sorted((root / "skills").glob("*/SKILL.md")) if (root / "skills").is_dir() else []
    entries += sorted((root / "internal").glob("*/SKILL.md")) if (root / "internal").is_dir() else []
    queue = deque(path.resolve() for path in entries)
    visited: set[Path] = set()
    errors: list[str] = []
    while queue:
        source = queue.popleft()
        if source in visited:
            continue
        visited.add(source)
        try:
            text = source.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"cannot read {source.relative_to(root)}: {exc}")
            continue
        for raw in LINK.findall(text):
            target = local_target(source, raw)
            if target is None:
                continue
            try:
                relative_source = source.relative_to(root)
                relative_target = target.relative_to(root)
            except ValueError:
                errors.append(f"{source.relative_to(root)} points outside repository: {raw}")
                continue
            if not target.exists():
                errors.append(f"{relative_source} -> missing {relative_target}")
            elif target.is_file() and target.suffix.lower() == ".md":
                queue.append(target)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, nargs="?", default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    errors = audit(args.root)
    print(json.dumps({"status": "ok" if not errors else "error", "checked_root": str(args.root.resolve()), "errors": errors}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
