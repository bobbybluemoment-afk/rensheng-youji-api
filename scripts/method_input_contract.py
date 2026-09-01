#!/usr/bin/env python3
"""Build the topic-isolated input view used by every independent method."""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any


def canonical_digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_method_input(analysis_input: dict[str, Any]) -> dict[str, Any]:
    """Remove user facts, questions and calibration before chart-method analysis."""
    result = copy.deepcopy(analysis_input)
    result["reality_context"] = {"facts": [], "questions": []}
    result["calibration"] = {
        "candidate_feedback": [],
        "confirmed_events": [],
        "rejected_claims": [],
    }
    return result


def build_core_synthesis_input(analysis_input: dict[str, Any]) -> dict[str, Any]:
    """Keep factual context but remove the user's requested topic from Core synthesis."""
    result = copy.deepcopy(analysis_input)
    reality = result.get("reality_context") or {}
    reality["questions"] = []
    reality["current_concerns"] = []
    result["reality_context"] = reality
    result["calibration"] = {
        "candidate_feedback": [],
        "confirmed_events": [],
        "rejected_claims": [],
    }
    return result
