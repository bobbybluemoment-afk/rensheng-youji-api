#!/usr/bin/env python3
"""Record and verify hash-bound checkpoints inside one repository-local report run."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
RUN_ROOT = (ROOT / "work/runs").resolve()


def _allowed(run_dir: Path) -> Path:
    resolved = run_dir.resolve()
    if RUN_ROOT not in resolved.parents or not (resolved / "run-state.json").is_file():
        raise ValueError("run_dir必须是当前仓库work/runs内的正式运行目录")
    return resolved


def _digest_path(path: Path) -> str:
    if path.is_file():
        return hashlib.sha256(path.read_bytes()).hexdigest()
    if path.is_dir():
        digest = hashlib.sha256()
        files = sorted(item for item in path.rglob("*") if item.is_file())
        for item in files:
            digest.update(str(item.relative_to(path)).encode("utf-8"))
            digest.update(b"\0")
            digest.update(item.read_bytes())
            digest.update(b"\0")
        return digest.hexdigest()
    raise ValueError(f"检查点产物不存在：{path}")


def _relative(run_dir: Path, path: Path) -> str:
    resolved = path.resolve()
    if resolved != run_dir and run_dir not in resolved.parents:
        raise ValueError(f"检查点只能记录本次运行目录内的文件：{path}")
    return str(resolved.relative_to(run_dir))


def _snapshot(run_dir: Path, paths: list[Path]) -> dict[str, str]:
    return {_relative(run_dir, path): _digest_path(path.resolve()) for path in paths}


def record(run_dir: Path, stage: str, inputs: list[Path], outputs: list[Path]) -> dict[str, Any]:
    run_dir = _allowed(run_dir)
    if not stage or not outputs:
        raise ValueError("检查点必须有stage和至少一个输出产物")
    checkpoint_path = run_dir / "run-checkpoints.json"
    data = json.loads(checkpoint_path.read_text(encoding="utf-8")) if checkpoint_path.is_file() else {
        "schema_version": "1.0.0", "run_id": json.loads((run_dir / "run-state.json").read_text(encoding="utf-8"))["run_id"], "stages": []
    }
    entry = {
        "stage": stage,
        "inputs": _snapshot(run_dir, inputs),
        "outputs": _snapshot(run_dir, outputs),
    }
    data["stages"] = [item for item in data.get("stages") or [] if item.get("stage") != stage] + [entry]
    checkpoint_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return entry


def verify(run_dir: Path) -> list[str]:
    run_dir = _allowed(run_dir)
    checkpoint_path = run_dir / "run-checkpoints.json"
    if not checkpoint_path.is_file():
        return ["尚未记录任何检查点"]
    data = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    for entry in data.get("stages") or []:
        stage = str(entry.get("stage"))
        for group in ("inputs", "outputs"):
            for relative, expected in (entry.get(group) or {}).items():
                path = run_dir / relative
                try:
                    actual = _digest_path(path)
                except ValueError as exc:
                    errors.append(f"{stage}.{group}: {exc}")
                    continue
                if actual != expected:
                    errors.append(f"{stage}.{group}.{relative}哈希变化")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    record_parser = sub.add_parser("record")
    record_parser.add_argument("--run-dir", type=Path, required=True)
    record_parser.add_argument("--stage", required=True)
    record_parser.add_argument("--input", action="append", type=Path, default=[])
    record_parser.add_argument("--output", action="append", type=Path, required=True)
    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "record":
            result = record(args.run_dir, args.stage, args.input, args.output)
            payload = {"status": "ok", "checkpoint": result}
        else:
            errors = verify(args.run_dir)
            payload = {"status": "ok" if not errors else "error", "errors": errors}
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        payload = {"status": "error", "errors": [str(exc)]}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
