#!/usr/bin/env python3
"""Shared deterministic rules for user-visible Chinese across Core and report stages."""

from __future__ import annotations


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

BODY_EMOTION_SAFETY_NOTE = "以上内容不构成疾病诊断，持续不适请咨询医生。"
BODY_EMOTION_SAFETY_MARKERS = (
    "不构成疾病诊断",
    "不能据此诊断",
    "应以正规医疗评估为准",
)


def unnatural_realization_phrases(text: str) -> list[str]:
    return sorted(phrase for phrase in UNNATURAL_REALIZATION_PHRASES if phrase in text)


def has_body_emotion_safety_note(text: str) -> bool:
    return any(marker in text for marker in BODY_EMOTION_SAFETY_MARKERS)
