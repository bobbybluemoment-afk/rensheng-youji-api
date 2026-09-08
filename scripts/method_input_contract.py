#!/usr/bin/env python3
"""Build the topic-isolated input view used by every independent method."""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any


METHOD_INPUT_PROFILES = {
    "pattern_structure": "natal_luck",
    "momentum_configuration": "natal_luck",
    "climate_adjustment": "natal_luck_annual",
    "ten_god_dynamics": "natal_luck_annual",
    "root_seed_flower_fruit": "natal_only",
    "blind_school": "natal_luck",
    "timing_continuity": "full_timing",
    "position_relationship": "natal_luck",
    "stem_branch_dynamics": "natal_luck_annual",
}


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


def _select(source: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    return {key: copy.deepcopy(source[key]) for key in keys if key in source}


def _compact_luck_cycles(source: Any) -> Any:
    if not isinstance(source, dict):
        return copy.deepcopy(source)
    result = _select(source, ("direction", "start_age", "start_datetime", "method"))
    cycles = []
    for item in source.get("cycles") or []:
        if not isinstance(item, dict):
            continue
        cycles.append(_select(item, (
            "index", "start_age", "end_age", "start_datetime", "end_datetime",
            "stem", "branch", "stem_ten_god", "hidden_stems",
        )))
    result["cycles"] = cycles
    return result


def _compact_annual_cycles(source: Any, *, full: bool) -> list[Any]:
    if not isinstance(source, list):
        return []
    if full:
        return copy.deepcopy(source)
    keys = (
        "year", "stem", "branch", "stem_ten_god", "hidden_stems",
        "luck_cycle_index",
    )
    return [_select(item, keys) for item in source if isinstance(item, dict)]


def build_method_input_view(method_input: dict[str, Any], method_id: str) -> dict[str, Any]:
    """Project the shared isolated input into the facts one method actually needs.

    The canonical method-input remains unchanged and supplies the common integrity
    hash.  This view only reduces prompt payload; it never adds inferred facts.
    """
    try:
        profile = METHOD_INPUT_PROFILES[method_id]
    except KeyError as exc:
        raise ValueError(f"未知方法：{method_id}") from exc

    request = _select(method_input.get("request") or {}, (
        "analysis_as_of", "calendar_basis", "target_range",
    ))
    person_source = method_input.get("person") or {}
    person = _select(person_source, ("gender",))
    person["birth"] = _select(person_source.get("birth") or {}, (
        "local_datetime", "place_name", "timezone", "longitude", "latitude",
        "time_precision",
    ))
    chart = _select(method_input.get("chart") or {}, ("day_master", "pillars"))
    boundaries_source = method_input.get("solar_terms_and_boundaries") or {}
    boundary_keys = (
        "timezone_resolved", "true_solar_time_applied", "true_solar_datetime",
        "nearest_solar_terms", "boundary_flags",
    ) if profile in {"natal_luck_annual", "full_timing"} else ("boundary_flags",)

    result: dict[str, Any] = {
        "request": request,
        "person": person,
        "chart": chart,
        "solar_terms_and_boundaries": _select(boundaries_source, boundary_keys),
    }
    if method_input.get("five_elements") is not None:
        result["five_elements"] = copy.deepcopy(method_input["five_elements"])
    if profile != "natal_only":
        result["luck_cycles"] = _compact_luck_cycles(method_input.get("luck_cycles"))
    if profile in {"natal_luck_annual", "full_timing"}:
        result["annual_cycles"] = _compact_annual_cycles(
            method_input.get("annual_cycles"), full=profile == "full_timing"
        )
    if profile == "full_timing" and method_input.get("monthly_cycles") is not None:
        result["monthly_cycles"] = copy.deepcopy(method_input["monthly_cycles"])
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
