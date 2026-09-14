#!/usr/bin/env python3
"""Shared semantic QA for past/current five-question calibration candidates."""

from __future__ import annotations

import re
from typing import Any


ADVICE_PATTERNS = (
    "建议",
    "应该",
    "最好",
    "不妨",
    "有助于",
    "会明显帮助",
    "能够帮助",
    "更适合你",
)

# A calibration answer must sound like the named life area even when its title
# is removed.  In particular, a finance question must ask about money rather
# than relabeling career output as "回报".
DOMAIN_REALITY_TERMS = {
    "self_growth": ("选择", "犹豫", "在意", "认可", "要求自己", "习惯", "表达", "比较", "安心"),
    "love_partner": ("喜欢", "关系", "伴侣", "靠近", "回应", "承诺", "失望", "争执", "陪伴", "相处"),
    "career": ("工作", "岗位", "职位", "领导", "同事", "项目", "面试", "职业", "升职", "职责"),
    "finance_resources": ("收入", "工资", "奖金", "存钱", "储蓄", "消费", "花钱", "预算", "价格", "积蓄", "报酬", "现金", "负债", "借款", "资产"),
    "body_emotion": ("睡眠", "睡不着", "累", "疲劳", "紧绷", "烦躁", "情绪", "注意力", "休息", "身体", "胃口", "恢复"),
    "family_growth": ("父母", "家人", "亲友", "家庭", "支持", "求助", "独立", "照顾", "期待"),
}

# Used only together with multiple connectors, so a natural list of income
# types is not mistaken for several questions bundled into one answer.
ACTIVITY_TERMS = (
    "调整", "重排", "增加", "形成", "影响", "学习", "比较", "表达", "试错",
    "面试", "汇报", "交付", "负责", "选择", "改变", "转岗", "离职", "求职",
)


def years_in(value: Any) -> list[int]:
    return [int(item) for item in re.findall(r"(?<!\d)(20\d{2})(?!\d)", str(value or ""))]


def quality_errors(candidate: dict[str, Any], analysis_year: int, *, strict_semantics: bool = True) -> list[str]:
    """Return reasons a candidate is unsuitable for a user-facing question."""
    errors: list[str] = []
    scope = str(candidate.get("answerable_time_scope", candidate.get("time_scope", "")))
    observation = str(candidate.get("answerable_observation", ""))
    alternative = str(candidate.get("answerable_alternative", ""))
    combined = " ".join((scope, observation, alternative))

    future_years = sorted({year for year in years_in(combined) if year > analysis_year})
    if future_years:
        errors.append(f"包含尚未发生的年份：{future_years}")

    # Historical fixtures and pre-0.16 Core files did not provide dedicated
    # answerable text.  They retain the original future-date protection, while
    # every current production Core uses the complete semantic checks below.
    if not strict_semantics:
        return errors

    window = years_in(scope)
    long_open_window = len(window) == 1 and analysis_year - window[0] > 6 and any(term in scope for term in ("起", "至今", "以来", "到现在"))
    if (len(window) >= 2 and max(window) - min(window) > 6) or long_open_window:
        errors.append("时间范围超过六年，用户很难用一个选项概括整段经历")

    if any(term in observation or term in alternative for term in ADVICE_PATTERNS):
        errors.append("A/B选项写成了建议或解决办法，不是已经发生或当前可观察的事实")

    domain = str(candidate.get("domain", ""))
    terms = DOMAIN_REALITY_TERMS.get(domain, ())
    if terms and not any(term in observation or term in alternative for term in terms):
        errors.append("A/B选项没有使用本领域可核对的现实语言")

    connector_count = sum((observation + alternative).count(term) for term in ("、", "以及", "或"))
    activity_count = sum(term in observation or term in alternative for term in ACTIVITY_TERMS)
    if connector_count >= 2 and activity_count >= 2:
        errors.append("一道题混入多个行为或变化轴，无法判断用户究竟确认了哪一点")

    if observation.strip() == alternative.strip():
        errors.append("A/B选项没有形成可区分的两种现实表现")
    return errors
