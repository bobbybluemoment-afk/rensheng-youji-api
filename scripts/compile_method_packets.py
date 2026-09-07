#!/usr/bin/env python3
"""Compile all nine semantic answers and emit one concise METHOD GATE receipt."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from compile_method_packet import compile_packet  # noqa: E402
from core_synthesis_contract import ALL_METHODS, build_method_audit, canonical_digest  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--method-input", type=Path, required=True)
    parser.add_argument("--semantic-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--gate-output", type=Path, required=True)
    args = parser.parse_args()
    try:
        method_input = json.loads(args.method_input.read_text(encoding="utf-8"))
        patches = {
            method_id: json.loads((args.semantic_dir / f"{method_id}.json").read_text(encoding="utf-8"))
            for method_id in sorted(ALL_METHODS)
        }
        packets = {
            method_id: compile_packet(method_input, patches[method_id], method_id)
            for method_id in sorted(ALL_METHODS)
        }
        methods = [packets[method_id]["method_analysis"] for method_id in sorted(ALL_METHODS)]
        audit = build_method_audit(methods)
        gate = {
            "schema_version": "1.0.0",
            "status": "pass",
            "method_input_sha256": canonical_digest(method_input),
            "packet_count": 9,
            "completed_method_ids": audit["completed_method_ids"],
            "excluded_method_ids": audit["excluded_method_ids"],
            "delivery_decision": audit["delivery_decision"],
            "method_packets_sha256": canonical_digest(packets),
            "packet_sha256_by_method": {
                method_id: canonical_digest(packet) for method_id, packet in packets.items()
            },
        }
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for method_id, packet in packets.items():
            (args.output_dir / f"{method_id}.json").write_text(
                json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        args.gate_output.parent.mkdir(parents=True, exist_ok=True)
        args.gate_output.write_text(json.dumps(gate, ensure_ascii=False, indent=2), encoding="utf-8")
    except (OSError, KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "fail", "message": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(gate, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
