#!/usr/bin/env python3
"""Create a persistent repository-local workspace for one report run."""

from __future__ import annotations

import argparse
import json
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "internal/core-manifest.json"
RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{2,63}$")


def create_run(run_id: str | None = None) -> dict[str, str]:
    temporary_roots = {Path("/tmp"), Path("/var/tmp"), Path("/private/tmp")}
    if any(temp == ROOT or temp in ROOT.parents for temp in temporary_roots):
        raise ValueError("仓库位于会被清理的临时目录；请先克隆到当前会话持久工作区")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if run_id is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_id = f"report-{stamp}-{secrets.token_hex(3)}"
    if not RUN_ID.fullmatch(run_id):
        raise ValueError("run_id只能包含字母、数字、下划线和连字符，长度3—64")
    work_dir = (ROOT / "work/runs" / run_id).resolve()
    allowed_root = (ROOT / "work/runs").resolve()
    if allowed_root not in work_dir.parents:
        raise ValueError("正式运行目录必须位于仓库work/runs内")
    if work_dir.exists():
        raise FileExistsError(f"运行目录已经存在：{work_dir}")
    for name in ("method-prompt-packs", "method-semantic-patches", "method-packets", "calibration", "report-writing", "editorial", "delivery"):
        (work_dir / name).mkdir(parents=True, exist_ok=True)
    state = {
        "schema_version": "1.0.0",
        "run_id": run_id,
        "repo_root": str(ROOT),
        "work_dir": str(work_dir),
        "package_version": str(manifest["version"]),
        "core_version": str(manifest["report_pipeline"]["core_version"]),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_status": "initialized",
    }
    (work_dir / "run-state.json").write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (work_dir / "run-checkpoints.json").write_text(
        json.dumps({"schema_version": "1.0.0", "run_id": run_id, "stages": []}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return state


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id")
    args = parser.parse_args()
    try:
        result = create_run(args.run_id)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "ok", **result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
