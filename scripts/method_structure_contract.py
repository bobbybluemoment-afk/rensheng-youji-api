#!/usr/bin/env python3
"""Method-specific structure checks that prevent minimum-count early stopping."""

from __future__ import annotations

from typing import Any


METHOD_STRUCTURE_CHECKS: dict[str, tuple[tuple[str, str], ...]] = {
    "pattern_structure": (
        ("month_command_core", "月令核心、主气与内部结构怎样组织全盘"),
        ("revealed_hidden_configuration", "藏干、透干与各自位置带来什么新增信息"),
        ("structural_coordination", "主要力量怎样配合、牵制、救应或混杂"),
        ("success_failure_conditions", "结构成立、受损、转向和恢复分别需要什么条件"),
        ("positional_projection", "结构落到本人、事业、财富、关系与家庭时有何不同"),
        ("temporal_modification", "大运流年是否改变结构重心或现实表现"),
    ),
    "momentum_configuration": (
        ("concentration_direction", "力量集中在哪里，整体趋向是否完整"),
        ("source_support", "行动来源、根气与补给从哪里进入"),
        ("obstruction_diversion", "力量在哪里受阻、分流或转向"),
        ("outlet_completion", "结构通过什么出口形成现实结果"),
        ("configuration_conditions", "成方成局、顺势或逆势的条件是否完整"),
        ("temporal_redirection", "当前阶段是否改变原有流向"),
    ),
    "climate_adjustment": (
        ("seasonal_baseline", "季节寒暖燥湿的基础状态"),
        ("adjustment_supply", "需要的调节因素是否出现、透出或有根"),
        ("adjustment_usability", "调节因素能否真正发挥，是否受阻"),
        ("excess_deficiency", "调节不足与调节过度分别怎样表现"),
        ("environment_rhythm", "环境、行动节奏、压力反应与恢复条件"),
        ("temporal_adjustment", "大运流年怎样改变调节条件"),
    ),
    "ten_god_dynamics": (
        ("visible_hidden_network", "显性与隐性的十神怎样组成关系网络"),
        ("action_sequence", "输入、判断、表达、结果与责任按什么顺序发生"),
        ("repeated_relations", "重复出现的关系怎样加强或改变行动"),
        ("positional_roles", "同一关系落在不同位置时分别指向什么"),
        ("resource_exchange", "资源怎样获得、交换、保存和损耗"),
        ("responsibility_evaluation", "权责、评价、合作与回报怎样连接"),
        ("temporal_activation", "当前时运激活了网络中的哪一环"),
    ),
    "root_seed_flower_fruit": (
        ("root_source", "来源端提供哪些根基、资源与早期条件"),
        ("seed_cultivation", "环境怎样培养技能、习惯和适应方式"),
        ("flower_expression", "贴身生活、关系、作品与外在呈现怎样展开"),
        ("fruit_retention", "经验最后沉淀为职位、资产、方法、声誉或传承中的什么"),
        ("simultaneous_coexistence", "四个位置在当前如何同时作用"),
        ("transmission_breaks", "来源到呈现和沉淀之间在哪里连接、转化或中断"),
    ),
    "blind_school": (
        ("subject_object", "主体与反复处理的对象分别是什么"),
        ("body_use", "体与用怎样配合，命主依靠什么工具"),
        ("work_path", "做功从哪里开始、经过什么、怎样完成"),
        ("result_ownership", "结果怎样形成，最终归谁或在哪里留下"),
        ("cost_failure", "成本、虚实、不完整和失败条件在哪里"),
        ("seven_reality_dimensions", "组织、行业、职能、对象、发展、成果和环境分别能否取象"),
        ("relationship_anchor", "贴身关系和伴侣领域是否有本方法可用依据"),
    ),
    "timing_continuity": (
        ("natal_baseline", "原局长期主题怎样进入时间分析"),
        ("previous_cycle", "上一阶段形成了什么能力、惯性和未完成问题"),
        ("cycle_transition", "前后大运怎样交接，变化通过什么发生"),
        ("current_cycle", "当前大运增加了什么现实任务"),
        ("past_current_events", "过去至当前有哪些可核对的连续变化"),
        ("next_two_three_years", "未来两三年怎样承接当前阶段而不作事件保证"),
        ("continuity_carryover", "相邻年份带入、执行、沉淀和伏笔是否连贯"),
        ("domain_activation", "事业、财富、关系、家庭与身心哪些领域被真实激活"),
    ),
    "position_relationship": (
        ("year_source", "年位的家庭来源、远端资源与自主根基"),
        ("month_environment", "月位的成长环境、同伴与社会接口"),
        ("day_person_partner", "日位的贴身生活、本人选择与伴侣接口"),
        ("hour_retention", "时位的长期沉淀、规范与后续方向"),
        ("cross_position_links", "四个位置怎样连接、牵制或传递"),
        ("family_support_constraint", "家庭支持、限制、独立与回馈怎样共存"),
        ("relationship_anchor", "关系需要、吸引、承诺和共同生活是否有位置依据"),
    ),
    "stem_branch_dynamics": (
        ("root_support", "日主和关键力量是否有根、有助或受制"),
        ("visibility", "哪些力量透出，哪些只藏在内部"),
        ("strength_balance", "得令、得地、得助、受泄和受耗怎样共同作用"),
        ("regulation_flow", "生克、制化、通关和流通是否成立"),
        ("interactions", "刑冲合害破落在哪些位置并改变什么"),
        ("transformation_conditions", "合化、从势、墓库等条件是否完整"),
        ("temporal_activation", "大运流年怎样引动原局动力"),
        ("relationship_anchor", "日支及其连接对命主一侧关系模式提供什么依据"),
    ),
}


def compact_checks(method_id: str) -> list[dict[str, str]]:
    """Return the small prompt representation for one isolated method."""
    return [
        {"check_id": check_id, "question": question}
        for check_id, question in METHOD_STRUCTURE_CHECKS[method_id]
    ]


def expected_check_ids(method_id: str) -> set[str]:
    return {check_id for check_id, _ in METHOD_STRUCTURE_CHECKS[method_id]}


def structure_summary(patch: dict[str, Any]) -> dict[str, int]:
    counts = {"material": 0, "conditional": 0, "background": 0}
    for item in patch.get("structure_checks") or []:
        status = str(item.get("importance", ""))
        if status in counts:
            counts[status] += 1
    return counts
