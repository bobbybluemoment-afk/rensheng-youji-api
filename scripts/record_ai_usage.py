#!/usr/bin/env python3
"""Append one AI call's usage, elapsed time and retry cause to the run cost ledger."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


INPUT_USD = 4.0
CACHED_INPUT_USD = 0.4
OUTPUT_USD = 20.0
LONG_CONTEXT_THRESHOLD = 272_000


def cost(input_tokens: int, cached_tokens: int, output_tokens: int) -> float:
    uncached = max(0, input_tokens - cached_tokens)
    long = input_tokens > LONG_CONTEXT_THRESHOLD
    input_multiplier = 2.0 if long else 1.0
    output_multiplier = 1.5 if long else 1.0
    return (
        uncached / 1_000_000 * INPUT_USD * input_multiplier
        + cached_tokens / 1_000_000 * CACHED_INPUT_USD * input_multiplier
        + output_tokens / 1_000_000 * OUTPUT_USD * output_multiplier
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--stage", required=True)
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument("--input-tokens", type=int, required=True)
    parser.add_argument("--cached-input-tokens", type=int, default=0)
    parser.add_argument("--output-tokens", type=int, required=True, help="含reasoning tokens的计费输出总数")
    parser.add_argument("--reasoning-tokens", type=int, default=0, help="仅作观察，已经包含在output-tokens中")
    parser.add_argument("--elapsed-seconds", type=float, required=True)
    parser.add_argument("--retry-reason")
    parser.add_argument("--usd-cny", type=float, default=7.2)
    args = parser.parse_args()
    try:
        run_dir = args.run_dir.resolve()
        state = json.loads((run_dir / "run-state.json").read_text(encoding="utf-8"))
        if Path(state["work_dir"]).resolve() != run_dir:
            raise ValueError("用量记录与本次运行目录不一致")
        if min(args.input_tokens, args.cached_input_tokens, args.output_tokens, args.reasoning_tokens) < 0:
            raise ValueError("Token数量不得为负")
        if args.cached_input_tokens > args.input_tokens or args.reasoning_tokens > args.output_tokens:
            raise ValueError("缓存或推理Token不能超过对应总数")
        usd = cost(args.input_tokens, args.cached_input_tokens, args.output_tokens)
        entry: dict[str, Any] = {
            "stage": args.stage, "model": args.model,
            "input_tokens": args.input_tokens, "cached_input_tokens": args.cached_input_tokens,
            "output_tokens": args.output_tokens, "reasoning_tokens": args.reasoning_tokens,
            "elapsed_seconds": args.elapsed_seconds, "retry_reason": args.retry_reason,
            "long_context_multiplier_applied": args.input_tokens > LONG_CONTEXT_THRESHOLD,
            "estimated_api_cost_usd": round(usd, 4),
            "estimated_api_cost_cny": round(usd * args.usd_cny, 2),
        }
        path = run_dir / "ai-usage-ledger.json"
        ledger = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {
            "schema_version": "1.0.0", "run_id": state["run_id"],
            "pricing": {"model": "gpt-5.6-sol", "input_usd_per_million": INPUT_USD, "cached_input_usd_per_million": CACHED_INPUT_USD, "output_usd_per_million": OUTPUT_USD, "usd_cny_assumption": args.usd_cny},
            "calls": [],
        }
        ledger["calls"].append(entry)
        ledger["totals"] = {
            "calls": len(ledger["calls"]),
            "input_tokens": sum(item["input_tokens"] for item in ledger["calls"]),
            "output_tokens": sum(item["output_tokens"] for item in ledger["calls"]),
            "elapsed_seconds": round(sum(item["elapsed_seconds"] for item in ledger["calls"]), 2),
            "estimated_api_cost_usd": round(sum(item["estimated_api_cost_usd"] for item in ledger["calls"]), 4),
            "estimated_api_cost_cny": round(sum(item["estimated_api_cost_cny"] for item in ledger["calls"]), 2),
        }
        path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False)); return 1
    print(json.dumps({"status": "ok", "ledger": str(path), "totals": ledger["totals"]}, ensure_ascii=False)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
