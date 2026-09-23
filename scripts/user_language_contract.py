#!/usr/bin/env python3
"""Shared deterministic rules for user-visible Chinese across Core and report stages."""

from __future__ import annotations

import re


# Do not ban a normal word globally when only an artificial phrase is the
# problem.  For example, "兑现承诺" is ordinary Chinese, while the phrases
# below turn a concrete situation into consultant/AI shorthand.
UNNATURAL_REALIZATION_PHRASES = {
    "兑现能力",
    "兑现价值",
    "成果兑现",
    "兑现条件",
    "判断兑现",
    "价值兑现",
}

# These patterns are not globally forbidden Chinese.  They are specifically
# unsuitable for ``plain_claim`` because that field is copied verbatim into the
# report and cannot be repaired by the downstream editor.
LOCKED_CLAIM_DEFENSIVE_PATTERNS = (
    r"不是没有[^。！？]{0,30}而是",
    r"并非[^。！？；]{0,30}[；，]真正",
    r"(?:突破点|真正影响|真正需要|真正重要)[^。！？]{0,60}而不是",
    r"(?:不只是|而不只是)[^。！？]{0,40}",
)

# Calibration changes selection and confidence internally.  The visible report
# must describe the resulting reality directly instead of narrating the survey
# or the program's decision process.
CALIBRATION_META_PATTERNS = (
    r"你(?:已经|没有|尚未)确认",
    r"校准(?:结果|答案|选项|后|确认)",
    r"(?:选择|选了)[A-DＡ-Ｄ](?:项|选项)?",
    r"因此报告(?:不会|不再|将不)",
    r"报告不会把[^。！？]{0,40}(?:写成|当作)",
)

BODY_EMOTION_SAFETY_NOTE = "以上内容不构成疾病诊断，持续不适请咨询医生。"
BODY_EMOTION_SAFETY_MARKERS = (
    "不构成疾病诊断",
    "不能据此诊断",
    "应以正规医疗评估为准",
)


def unnatural_realization_phrases(text: str) -> list[str]:
    return sorted(phrase for phrase in UNNATURAL_REALIZATION_PHRASES if phrase in text)


def locked_claim_language_issues(text: str) -> list[str]:
    """Return formulaic contrasts that must be repaired before Core freeze."""
    return [pattern for pattern in LOCKED_CLAIM_DEFENSIVE_PATTERNS if re.search(pattern, text)]


def calibration_meta_language_issues(text: str) -> list[str]:
    """Return visible wording that exposes calibration operations."""
    return [pattern for pattern in CALIBRATION_META_PATTERNS if re.search(pattern, text)]


def has_body_emotion_safety_note(text: str) -> bool:
    return any(marker in text for marker in BODY_EMOTION_SAFETY_MARKERS)
