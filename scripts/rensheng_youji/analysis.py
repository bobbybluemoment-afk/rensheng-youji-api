"""人生有迹免费卡片的公开本地分析与文案生成。"""

from __future__ import annotations

from typing import Any


STEM_COMBINATIONS = {
    frozenset(("甲", "己")): "甲己相合",
    frozenset(("乙", "庚")): "乙庚相合",
    frozenset(("丙", "辛")): "丙辛相合",
    frozenset(("丁", "壬")): "丁壬相合",
    frozenset(("戊", "癸")): "戊癸相合",
}

WAYS = {
    "正官": "建立规则并协调关系",
    "七杀": "用专精和执行推进",
    "正印": "用知识和标准建立可信度",
    "偏印": "从边缘经验中提炼方法",
    "食神": "让兴趣和能力持续产出",
    "伤官": "跳出安排并寻找新路径",
    "正财": "整理资源并建立稳定安排",
    "偏财": "整合现实资源",
    "比肩": "依靠自身能力开局",
    "劫财": "在合作与竞争中行动",
}

OUTCOMES = {
    "正官": "可协作的秩序",
    "七杀": "可以落实的结果",
    "正印": "容易获得认可的成果",
    "偏印": "不同于常规的方法",
    "食神": "可持续的产出",
    "伤官": "新的行动路径",
    "正财": "稳定可用的资源",
    "偏财": "更广的资源连接",
    "比肩": "自主行动的空间",
    "劫财": "可以共同推进的局面",
}

TENSION_LINES = {
    "正官": "当规则或位置不稳定时，你可能会更用力维持正确和可靠。",
    "七杀": "当压力缺少实际支撑时，你可能会用更高要求逼迫自己。",
    "正印": "当认可不够稳定时，你可能会更努力证明自己值得信任。",
    "偏印": "当独特经验得不到理解时，你可能会退回熟悉的小世界。",
    "食神": "当余裕不够稳定时，你可能会等到感觉合适才开始行动。",
    "伤官": "当行动空间受限时，你可能会把离开当成最快的解决办法。",
    "正财": "当稳定资源不足时，你可能会过度在意可控和确定。",
    "偏财": "当资源连接不稳定时，你可能会不断扩大关系和机会。",
    "比肩": "当自身支撑不够时，你可能会把所有事情都留给自己承担。",
    "劫财": "当合作或评价不够稳定时，你可能会更努力地证明自己有用、可靠。",
}

MAIN_TASKS = {
    "正官": "在建立规则和承担责任时，也为自己保留调整方向的空间。",
    "七杀": "把专精和执行从持续高压，变成能够按需调用的能力。",
    "正印": "让知识和认可成为支撑，而不是确认自身价值的唯一来源。",
    "偏印": "保留独特判断的同时，也让经验进入真实关系和生活。",
    "食神": "让从容和创造成为稳定能力，而不是只能等待合适条件。",
    "伤官": "把突破和变化变成主动选择，而不是遇到限制就离开。",
    "正财": "在经营稳定生活的同时，也为变化和真实需要留下空间。",
    "偏财": "把连接资源、扩大机会的能力，变成有边界且可以选择的工具。",
    "比肩": "让自立成为可以选择的能力，而不是凡事只能依靠自己。",
    "劫财": "在合作和竞争中确认边界，不再只靠比较证明自己的位置。",
}

QUOTES = {
    "正官": ("不以规矩，不能成方圆。", "《孟子·离娄上》"),
    "七杀": ("工欲善其事，必先利其器。", "《论语·卫灵公》"),
    "正印": ("学而不思则罔，思而不学则殆。", "《论语·为政》"),
    "偏印": ("独学而无友，则孤陋而寡闻。", "《礼记·学记》"),
    "食神": ("一张一弛，文武之道也。", "《礼记·杂记下》"),
    "伤官": ("穷则变，变则通，通则久。", "《周易·系辞下》"),
    "正财": ("仓廪实而知礼节，衣食足而知荣辱。", "《管子·牧民》"),
    "偏财": ("得道者多助，失道者寡助。", "《孟子·公孙丑下》"),
    "比肩": ("三人行，必有我师焉。", "《论语·述而》"),
    "劫财": ("二人同心，其利断金。", "《周易·系辞上》"),
}

DAY_PILLAR_QUOTES = {
    "甲戌": ("合抱之木，生于毫末；九层之台，起于累土。", "《道德经》第六十四章"),
}

TIME_LINES = {
    "比肩": "越接近结果，你越希望保留自主决定和独立完成的空间。",
    "劫财": "越接近结果，你越会在合作、竞争和他人评价中确认位置。",
    "食神": "越接近结果，你越重视过程是否从容，并能形成持续产出。",
    "伤官": "越接近结果，你越希望打破限制，用自己的方式完成表达。",
    "偏财": "越接近结果，你越关注资源能否流动，并带来更多可能。",
    "正财": "越接近结果，你越在意安排是否稳定、具体并能够长期维持。",
    "七杀": "越接近结果，你越容易提高要求，希望尽快形成明确成果。",
    "正官": "越接近结果，你越在意责任、规则和长期安排是否清楚。",
    "偏印": "越接近结果，你越相信独特经验，并倾向保留自己的判断。",
    "正印": "越接近结果，你越重视知识、标准和外界认可是否可靠。",
}

TASK_OPENERS = {
    "比肩": "依靠自己打开局面时",
    "劫财": "在合作与竞争中行动时",
    "食神": "把兴趣变成持续产出时",
    "伤官": "打破旧安排寻找新路时",
    "偏财": "整合人与现实资源时",
    "正财": "经营稳定生活和资源时",
    "七杀": "面对压力推进任务时",
    "正官": "承担责任建立秩序时",
    "偏印": "依靠独特经验判断时",
    "正印": "依靠知识和标准判断时",
}

TASK_ENDINGS = {
    "比肩": "让自立成为选择，不必所有事都自己扛",
    "劫财": "先确认合作边界，不靠比较证明位置",
    "食神": "建立稳定节奏，不再等待完美状态",
    "伤官": "把变化变成选择，不因受限就急着离开",
    "偏财": "给机会设定边界，不必什么资源都接住",
    "正财": "为变化留下余地，不只追求绝对稳定",
    "七杀": "给压力设定上限，不再一直逼迫自己",
    "正官": "保留调整规则的空间，不只证明自己可靠",
    "偏印": "让独特经验进入现实，不退回自己的世界",
    "正印": "把认可当作支撑，不拿它衡量全部价值",
}


def _cn_join(values: list[str]) -> str:
    unique = list(dict.fromkeys(values))
    if not unique:
        return ""
    if len(unique) == 1:
        return unique[0]
    return "、".join(unique[:-1]) + "与" + unique[-1]


def _root_count(stem: str, pillars: list[dict[str, Any]]) -> int:
    return sum(stem in pillar["hidden_stems"] for pillar in pillars)


def _key_relation(pillars: list[dict[str, Any]], relations: list[dict[str, Any]]) -> str:
    stems = [pillar["stem"] for pillar in pillars]
    for left_index in range(len(stems)):
        for right_index in range(left_index + 1, len(stems)):
            label = STEM_COMBINATIONS.get(frozenset((stems[left_index], stems[right_index])))
            if label:
                return label

    if not relations:
        return ""
    relation = relations[0]
    relation_name = {
        "六合": "相合",
        "六冲": "相冲",
        "六害": "相害",
        "六破": "相破",
        "相刑": "相刑",
        "三刑": "成刑",
        "自刑": "自刑",
    }.get(relation["relation"], relation["relation"])
    return f'{relation["branches"]}{relation_name}'


def _primary_visible(visible: list[dict[str, Any]]) -> dict[str, Any]:
    # 年月决定较稳定的能力来源；时柱另作为“果/落点”单独进入文案。
    foundation = [item for item in visible if item["position"] in {"year", "month"}]
    position_priority = {"year": 1, "month": 2}
    return max(
        foundation,
        key=lambda item: (item["root_count"], position_priority[item["position"]]),
    )


def _fallback_tension(primary_god: str, relation: str) -> str:
    if "冲" in relation or "刑" in relation or "害" in relation or "破" in relation:
        return "当不同方向同时拉扯时，你可能会急着找出唯一正确的道路。"
    if "合" in relation:
        return "当合作成为主要支撑时，你可能会忽略自己真正想保留的部分。"
    return TENSION_LINES[primary_god]


def _count_hanzi(text: str) -> int:
    return sum("\u4e00" <= char <= "\u9fff" for char in text)


def _validate(copy: dict[str, Any]) -> None:
    if len(copy["core_mystic"]) > 90:
        raise ValueError("本地规则生成的命理句超过90字符")
    if any(len(line) > 34 for line in copy["core_plain"]):
        raise ValueError("本地规则生成的白话超过34字符")
    if not 20 <= _count_hanzi(copy["main_task"]) <= 36:
        raise ValueError("本地规则生成的主线任务须为20—36个汉字")


def generate_card_copy(bazi: dict[str, Any]) -> dict[str, Any]:
    """从确定性事实中生成免费卡片的一条主要读法。"""

    context = bazi["analysis_context"]
    pillars = context["pillars"]
    visible: list[dict[str, Any]] = []
    rooted_labels: list[str] = []
    unrooted_labels: list[str] = []

    for index, pillar in enumerate(pillars):
        count = _root_count(pillar["stem"], pillars)
        label = "日主" if index == 2 else pillar["stem_ten_god"]
        if count:
            rooted_labels.append(label)
        elif index != 2:
            unrooted_labels.append(label)
        if index != 2:
            visible.append({
                "position": pillar["position"],
                "stem": pillar["stem"],
                "ten_god": pillar["stem_ten_god"],
                "root_count": count,
            })

    relation = _key_relation(pillars, context["branch_relations"])
    visible_text = "、".join(f'{item["stem"]}{item["ten_god"]}' for item in visible)
    fact_parts = [f"{visible_text}透出"]
    if rooted_labels:
        fact_parts.append(f"{_cn_join(rooted_labels)}有根")
    if unrooted_labels:
        fact_parts.append(f"{_cn_join(unrooted_labels)}无根")
    if relation:
        fact_parts.append(relation)
    core_mystic = "；".join((fact_parts[0], "，".join(fact_parts[1:]))) + "。"

    primary = _primary_visible(visible)
    primary_god = primary["ten_god"]
    outcome_god = pillars[3]["stem_ten_god"]
    first_line = f"处理问题时，你会{WAYS[primary_god]}，并落实为{OUTCOMES[outcome_god]}。"
    second_line = TIME_LINES[outcome_god]
    unrooted = [item for item in visible if item["root_count"] == 0]
    tension_god = (
        max(unrooted, key=lambda item: {"year": 1, "month": 3, "time": 2}[item["position"]])["ten_god"]
        if unrooted else primary_god
    )
    main_task = f"{TASK_OPENERS[primary_god]}，{TASK_ENDINGS[outcome_god]}。"
    copy = {
        "core_mystic": core_mystic,
        "core_plain": [first_line, second_line],
        "main_task": main_task,
        "analysis_signature": {
            "primary_god": primary_god,
            "primary_position": primary["position"],
            "outcome_god": outcome_god,
            "tension_god": tension_god,
            "key_relation": relation,
            "task_code": f"{primary_god}-{outcome_god}",
        },
        "reading_note": "稳定能力取自年月结构，现实落点明确结合时柱；这不是唯一读法。",
    }
    _validate(copy)
    return copy
