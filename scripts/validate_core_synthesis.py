#!/usr/bin/env python3
"""Validate AI semantic synthesis against immutable method packets before writing Core."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from finalize_core_analysis import assemble


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("synthesis_input", type=Path)
    parser.add_argument("semantic_output", type=Path)
    parser.add_argument("--compiler-source", type=Path)
    args = parser.parse_args()
    try:
        synthesis_input = json.loads(args.synthesis_input.read_text(encoding="utf-8"))
        semantic = json.loads(args.semantic_output.read_text(encoding="utf-8"))
        compiler_source = json.loads(args.compiler_source.read_text(encoding="utf-8")) if args.compiler_source else None
        _, errors = assemble(synthesis_input, semantic, compiler_source)
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        errors = [str(exc)]
    print(json.dumps({"status": "ok" if not errors else "error", "errors": errors}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
