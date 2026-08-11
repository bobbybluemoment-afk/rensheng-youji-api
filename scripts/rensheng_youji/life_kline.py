"""人生有迹 20 年连续人生 K 线。

原局确定长期使用方式，大运改变长期环境，流年只增加本年作用，
流月在年度路径附近形成 OHLC。数值表示阶段推进度，不表示吉凶、
财富、健康或事件发生概率。
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from math import ceil, floor
from typing import Any


STEMS = "甲乙丙丁戊己庚辛壬癸"
BRANCHES = "子丑寅卯辰巳午未申酉戌亥"
STEM_ELEMENT = {
    "甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土",
    "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水",
}
STEM_YANG = {
    "甲": True, "乙": False, "丙": True, "丁": False, "戊": True,
    "己": False, "庚": True, "辛": False, "壬": True, "癸": False,
}
PRODUCES = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
CONTROLS = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}
HIDDEN = {
    "子": ["癸"], "丑": ["己", "癸", "辛"], "寅": ["甲", "丙", "戊"], "卯": ["乙"],
    "辰": ["戊", "乙", "癸"], "巳": ["丙", "戊", "庚"], "午": ["丁", "己"],
    "未": ["己", "丁", "乙"], "申": ["庚", "壬", "戊"], "酉": ["辛"],
    "戌": ["戊", "辛", "丁"], "亥": ["壬", "甲"],
}

CLASHES = {"子午", "午子", "丑未", "未丑", "寅申", "申寅", "卯酉", "酉卯", "辰戌", "戌辰", "巳亥", "亥巳"}
HARMS = {"子未", "未子", "丑午", "午丑", "寅巳", "巳寅", "卯辰", "辰卯", "申亥", "亥申", "酉戌", "戌酉"}
COMBINES = {"子丑", "丑子", "寅亥", "亥寅", "卯戌", "戌卯", "辰酉", "酉辰", "巳申", "申巳", "午未", "未午"}
TRIADS = (
    ({"申", "子", "辰"}, "水"),
    ({"亥", "卯", "未"}, "木"),
    ({"寅", "午", "戌"}, "火"),
    ({"巳", "酉", "丑"}, "金"),
)
STEM_COMBINES = {frozenset(pair) for pair in (("甲", "己"), ("乙", "庚"), ("丙", "辛"), ("丁", "壬"), ("戊", "癸"))}

STATE_KEYS = ("root", "sprout", "flower", "fruit", "pressure")
STATE_CHANNEL = {0: "root", 1: "sprout", 2: "flower", 3: "fruit"}
NEXT_CHANNEL = {"root": "sprout", "sprout": "flower", "flower": "fruit", "fruit": "fruit"}

# 十神只定义通常进入哪一段，不直接定义吉凶。实际方向由它在原局中
# 是否有支撑、是否被过度使用以及当前大运共同决定。
GOD_CHANNELS = {
    "比肩": {"root": 1.0, "sprout": 0.8},
    "劫财": {"sprout": 1.0, "flower": 0.6},
    "食神": {"sprout": 0.5, "flower": 1.0, "fruit": 0.6},
    "伤官": {"flower": 1.0, "fruit": 0.6},
    "偏财": {"sprout": 0.5, "flower": 0.5, "fruit": 1.0},
    "正财": {"root": 0.4, "fruit": 1.0},
    "七杀": {"sprout": 0.5, "flower": 0.6, "fruit": 0.4},
    "正官": {"root": 0.3, "sprout": 0.6, "fruit": 0.5},
    "偏印": {"root": 1.0, "sprout": 0.6, "flower": -0.3},
    "正印": {"root": 1.0, "sprout": 0.6},
}
PRESSURE_WEIGHT = {
    "比肩": 0.2, "劫财": 0.7, "食神": 0.0, "伤官": 0.4, "偏财": 0.5,
    "正财": 0.3, "七杀": 1.0, "正官": 0.8, "偏印": 0.2, "正印": 0.1,
}


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def round1(value: float) -> float:
    return round(value, 1)


def ten_god(day_master: str, stem: str) -> str:
    day_element = STEM_ELEMENT[day_master]
    other_element = STEM_ELEMENT[stem]
    same_polarity = STEM_YANG[day_master] == STEM_YANG[stem]
    if other_element == day_element:
        return "比肩" if same_polarity else "劫财"
    if PRODUCES[day_element] == other_element:
        return "食神" if same_polarity else "伤官"
    if CONTROLS[day_element] == other_element:
        return "偏财" if same_polarity else "正财"
    if CONTROLS[other_element] == day_element:
        return "七杀" if same_polarity else "正官"
    return "偏印" if same_polarity else "正印"


def year_ganzhi(year: int) -> str:
    index = (year - 4) % 60
    return STEMS[index % 10] + BRANCHES[index % 12]


def month_ganzhis(year: int) -> list[str]:
    """返回该流年寅月至次年丑月的十二个月柱。

    年柱取立春后的干支，月干依五虎遁排列。卡片是阶段图，不承担
    节气交界日的择日功能，因此每月只使用该节月的干支。
    """

    year_stem = year_ganzhi(year)[0]
    tiger_start = {
        "甲": "丙", "己": "丙", "乙": "戊", "庚": "戊", "丙": "庚",
        "辛": "庚", "丁": "壬", "壬": "壬", "戊": "甲", "癸": "甲",
    }[year_stem]
    start_index = STEMS.index(tiger_start)
    month_branches = "寅卯辰巳午未申酉戌亥子丑"
    return [STEMS[(start_index + index) % 10] + branch for index, branch in enumerate(month_branches)]


def luck_for(bazi: dict[str, Any], year: int) -> dict[str, Any] | None:
    return next(
        (item for item in bazi["da_yun"] if item["start_year"] <= year <= item["end_year"]),
        None,
    )


def _stem_counts(bazi: dict[str, Any]) -> tuple[Counter[str], Counter[str], Counter[str]]:
    visible = Counter(
        pillar[0]
        for index, pillar in enumerate(bazi["pillars"])
        if index != 2
    )
    hidden = Counter(stem for pillar in bazi["pillars"] for stem in HIDDEN[pillar[1]])
    rooted = Counter()
    for stem, count in visible.items():
        if hidden[stem]:
            rooted[stem] = count
    return visible, hidden, rooted


def build_structure_profile(bazi: dict[str, Any], center_year: int) -> dict[str, Any]:
    """由原局与展示窗口前的大运生成紧凑状态档案。

    这里没有逐年文案，也不调用外部模型。关系只修正原局已经存在的
    功能方向，避免把刑冲合害数量直接换成运势分数。
    """

    day_master = bazi["day_master"]
    visible, hidden, rooted = _stem_counts(bazi)
    god_visible: Counter[str] = Counter()
    god_hidden: Counter[str] = Counter()
    god_rooted: Counter[str] = Counter()
    for stem, count in visible.items():
        god_visible[ten_god(day_master, stem)] += count
    for stem, count in hidden.items():
        god_hidden[ten_god(day_master, stem)] += count
    for stem, count in rooted.items():
        god_rooted[ten_god(day_master, stem)] += count

    monthly_effects: dict[str, int] = {}
    for god in GOD_CHANNELS:
        score = 0
        if god_rooted[god]:
            score += 1
        elif god_visible[god]:
            score -= 1
        elif god_hidden[god] >= 3:
            # 只藏不透通常是背景条件；重复达到三处时才作为稳定潜力。
            score += 1
        # 同一办法承担过多位置时，短期再来同类符号更容易形成负荷。
        if god_visible[god] + god_hidden[god] >= 5:
            score -= 1
        monthly_effects[god] = int(clamp(score, -2, 2))

    opening_year = center_year - 6
    opening_luck = luck_for(bazi, opening_year)
    opening = {"root": 0.8, "sprout": 0.8, "flower": 0.8, "fruit": 0.6, "pressure": 0.8}
    for index, pillar in enumerate(bazi["pillars"]):
        channel = STATE_CHANNEL[index]
        stem_god = ten_god(day_master, pillar[0]) if index != 2 else "比肩"
        hidden_gods = [ten_god(day_master, stem) for stem in HIDDEN[pillar[1]]]
        effect = monthly_effects[stem_god] * 0.35
        effect += sum(monthly_effects[god] for god in hidden_gods) * 0.10
        opening[channel] += effect
        opening["pressure"] += PRESSURE_WEIGHT[stem_god] * 0.08
    if opening_luck and opening_luck["pillar"]:
        luck_gods = [
            ten_god(day_master, opening_luck["pillar"][0]),
            ten_god(day_master, HIDDEN[opening_luck["pillar"][1]][0]),
        ]
        for god in luck_gods:
            for channel, weight in GOD_CHANNELS[god].items():
                opening[channel] += monthly_effects[god] * weight * 0.18
            opening["pressure"] += PRESSURE_WEIGHT[god] * 0.12
    for key in ("root", "sprout", "flower", "fruit"):
        opening[key] = round1(clamp(opening[key], -2.5, 3.5))
    opening["pressure"] = round1(clamp(opening["pressure"], 0, 3.5))

    annual_impacts = [
        _annual_impact(bazi, year, monthly_effects)
        for year in range(center_year - 5, center_year + 15)
    ]
    return {
        "opening_year": opening_year,
        "opening_state": opening,
        "monthly_relation_effects": monthly_effects,
        "annual_impacts": annual_impacts,
    }


def _relation_type(branch: str, other: str) -> str | None:
    pair = branch + other
    if pair in CLASHES:
        return "clash"
    if pair in HARMS:
        return "harm"
    if pair in COMBINES:
        return "combine"
    if branch == other:
        return "repeat"
    return None


def _complete_triad_element(branches: list[str]) -> str | None:
    branch_set = set(branches)
    return next((element for group, element in TRIADS if group.issubset(branch_set)), None)


def _element_representative(element: str, day_master: str) -> str:
    candidates = [stem for stem in STEMS if STEM_ELEMENT[stem] == element]
    return max(candidates, key=lambda stem: abs(STEM_YANG[stem] - STEM_YANG[day_master]))


def _annual_impact(
    bazi: dict[str, Any],
    year: int,
    monthly_effects: dict[str, int],
) -> dict[str, int]:
    day_master = bazi["day_master"]
    year_pillar = year_ganzhi(year)
    luck = luck_for(bazi, year)
    luck_pillar = luck["pillar"] if luck else ""
    sources: list[tuple[str, float]] = [(year_pillar[0], 1.0)]
    sources.extend((stem, weight) for stem, weight in zip(HIDDEN[year_pillar[1]], (0.62, 0.24, 0.12)))
    if luck_pillar:
        sources.append((luck_pillar[0], 0.42))
        sources.append((HIDDEN[luck_pillar[1]][0], 0.24))

    raw = {key: 0.0 for key in ("root", "sprout", "flower", "fruit")}
    pressure_raw = 0.0
    for stem, source_weight in sources:
        god = ten_god(day_master, stem)
        effect = monthly_effects[god]
        for channel, channel_weight in GOD_CHANNELS[god].items():
            raw[channel] += effect * channel_weight * source_weight
        pressure_raw += PRESSURE_WEIGHT[god] * source_weight * (1.0 if effect <= 0 else 0.65)

    natal_stems = [pillar[0] for pillar in bazi["pillars"]]
    natal_branches = [pillar[1] for pillar in bazi["pillars"]]
    relations: list[tuple[int, str]] = []
    for index, natal_branch in enumerate(natal_branches):
        relation = _relation_type(year_pillar[1], natal_branch)
        if relation:
            relations.append((index, relation))
    if luck_pillar:
        luck_relation = _relation_type(year_pillar[1], luck_pillar[1])
        if luck_relation:
            relations.append((1, luck_relation))

    # 关系只轻量改变被触及的根苗花果段，并把一部分变化传向下游。
    for index, relation in relations[:4]:
        channel = STATE_CHANNEL[min(index, 3)]
        if relation == "combine":
            raw[channel] += 0.35
        elif relation == "clash":
            raw[channel] -= 0.35
            raw[NEXT_CHANNEL[channel]] += 0.35
            pressure_raw += 0.35
        elif relation == "harm":
            raw[channel] -= 0.25
            pressure_raw += 0.35
        else:
            pressure_raw += 0.2

    triad_element = _complete_triad_element(natal_branches + [year_pillar[1]] + ([luck_pillar[1]] if luck_pillar else []))
    if triad_element:
        triad_god = ten_god(day_master, _element_representative(triad_element, day_master))
        triad_effect = monthly_effects[triad_god]
        for channel, weight in GOD_CHANNELS[triad_god].items():
            raw[channel] += triad_effect * weight * 0.28

    stem_activation = sum(
        1 for natal_stem in natal_stems
        if frozenset((year_pillar[0], natal_stem)) in STEM_COMBINES
    )
    activation = min(4, len(relations) + stem_activation + (1 if triad_element else 0))

    def to_integer(value: float) -> int:
        if value >= 1.25:
            return 2
        if value >= 0.28:
            return 1
        if value <= -1.25:
            return -2
        if value <= -0.28:
            return -1
        return 0

    result = {key: to_integer(value) for key, value in raw.items()}
    result["pressure"] = int(clamp(round(pressure_raw + activation * 0.18), 0, 2))
    result["activation"] = activation
    result["year"] = year
    return result


def _next_state(previous: dict[str, float], impact: dict[str, int]) -> dict[str, float]:
    return {
        "root": clamp(previous["root"] * 0.82 + impact["root"] * 1.35, -8, 8),
        "sprout": clamp(previous["sprout"] * 0.80 + previous["root"] * 0.10 + impact["sprout"] * 1.35, -8, 8),
        "flower": clamp(previous["flower"] * 0.78 + previous["sprout"] * 0.11 + impact["flower"] * 1.35, -8, 8),
        "fruit": clamp(previous["fruit"] * 0.74 + previous["flower"] * 0.12 + impact["fruit"] * 1.35, -8, 8),
        "pressure": clamp(previous["pressure"] * 0.55 + impact["pressure"] * 1.20, 0, 8),
    }


def _state_score(state: dict[str, float]) -> float:
    return clamp(
        50 + state["root"] * 0.8 + state["sprout"] * 1.0 + state["flower"] * 1.2
        + state["fruit"] * 1.5 - state["pressure"] * 1.6,
        15,
        85,
    )


def _pillar_month_effect(ganzhi: str, day_master: str, monthly_effects: dict[str, int]) -> float:
    value = monthly_effects[ten_god(day_master, ganzhi[0])] * 0.65
    for stem, weight in zip(HIDDEN[ganzhi[1]], (0.25, 0.07, 0.03)):
        value += monthly_effects[ten_god(day_master, stem)] * weight
    return value


def _relation_count(branch: str, other_branches: list[str]) -> int:
    count = 0
    for other in other_branches:
        pair = branch + other
        if pair in CLASHES:
            count += 2
        if pair in HARMS or pair in COMBINES:
            count += 1
        if branch == other:
            count += 1
    return count


def _triad_month_bonus(branches: list[str], day_master: str, monthly_effects: dict[str, int]) -> float:
    element = _complete_triad_element(branches)
    if not element:
        return 0.0
    stems = [stem for stem in STEMS if STEM_ELEMENT[stem] == element]
    return sum(monthly_effects[ten_god(day_master, stem)] for stem in stems) / len(stems)


def calculate_life_kline(
    bazi: dict[str, Any],
    profile: dict[str, Any],
    center_year: int,
) -> list[dict[str, Any]]:
    day_master = bazi["day_master"]
    monthly_effects = profile["monthly_relation_effects"]
    impacts = {item["year"]: item for item in profile["annual_impacts"]}
    natal_branches = [pillar[1] for pillar in bazi["pillars"]]
    state = dict(profile["opening_state"])
    previous_average = _state_score(state)
    timeline: list[dict[str, Any]] = []

    for year in range(center_year - 5, center_year + 15):
        impact = impacts[year]
        target = _next_state(state, impact)
        raw_target = _state_score(target)
        # 连续性优先：年度中枢最多移动 10 点，实际规则通常只移动 2—6 点。
        bounded_target = previous_average + clamp(raw_target - previous_average, -10, 10)
        target_shift = bounded_target - raw_target
        year_pillar = year_ganzhi(year)
        luck = luck_for(bazi, year)
        luck_pillar = luck["pillar"] if luck else ""
        values: list[float] = []
        month_rows: list[dict[str, Any]] = []

        for index, month_pillar in enumerate(month_ganzhis(year)):
            progress = (index + 1) / 12
            interpolated = {
                key: state[key] + (target[key] - state[key]) * progress
                for key in STATE_KEYS
            }
            base = _state_score(interpolated) + target_shift * progress
            other_branches = natal_branches + [year_pillar[1]] + ([luck_pillar[1]] if luck_pillar else [])
            relations = _relation_count(month_pillar[1], other_branches)
            modifier = _pillar_month_effect(month_pillar, day_master, monthly_effects) * 2.2
            modifier *= 1 + min(relations, 4) * 0.08
            modifier += _triad_month_bonus(other_branches + [month_pillar[1]], day_master, monthly_effects)
            value = clamp(base + clamp(modifier, -6, 6), 15, 85)
            values.append(value)

        max_range = 22 if impact["activation"] >= 4 else 18 if impact["activation"] == 3 else 15 if impact["activation"] == 2 else 12
        raw_low, raw_high = min(values), max(values)
        if raw_high - raw_low > max_range:
            middle = (raw_high + raw_low) / 2
            low_bound, high_bound = middle - max_range / 2, middle + max_range / 2
            values = [clamp(value, low_bound, high_bound) for value in values]

        for month_pillar, value in zip(month_ganzhis(year), values):
            month_rows.append({"ganzhi": month_pillar, "value": round1(value)})
        average = sum(values) / len(values)
        prior_luck = luck_for(bazi, year - 1)
        timeline.append({
            "year": year,
            "ganzhi": year_pillar,
            "dayun": luck_pillar,
            "open": round(values[0]),
            "high": round(max(values)),
            "low": round(min(values)),
            "close": round(values[-1]),
            "average": round1(average),
            "volatility": round(max(values) - min(values)),
            "change_luck": bool(luck and prior_luck and luck["pillar"] != prior_luck["pillar"]),
            "months": month_rows,
        })
        state = target
        previous_average = average
    return timeline


DOMAIN_WEIGHTS = {
    "比肩": {"城市与生活": 2.4, "家庭关系": 1.1},
    "劫财": {"感情关系": 2.4, "财务安排": 1.2},
    "食神": {"学习发展": 2.4, "感情关系": 1.0},
    "伤官": {"城市与生活": 2.4, "事业选择": 1.2},
    "偏财": {"财务安排": 2.4, "事业选择": 1.0},
    "正财": {"财务安排": 2.4, "家庭关系": 1.1},
    "七杀": {"事业选择": 2.4, "家庭关系": 1.2},
    "正官": {"事业选择": 2.2, "感情关系": 1.5},
    "偏印": {"学习发展": 2.4, "城市与生活": 1.2},
    "正印": {"家庭关系": 2.2, "学习发展": 1.8},
}

MECHANISM_BY_GOD = {
    "比肩": "自主边界", "伤官": "自主边界",
    "劫财": "合作位置",
    "食神": "能力产出",
    "偏财": "资源机会", "正财": "资源机会",
    "七杀": "责任压力", "正官": "责任压力",
    "偏印": "准备判断", "正印": "准备判断",
}

ISSUE_HEADLINES = {
    "事业选择": {
        "自主边界": "你最近可能在犹豫：继续适应现在的工作，还是去做更适合自己的事？",
        "合作位置": "你最近可能更烦的是：合作越来越多，但自己的位置和回报还不清楚？",
        "能力产出": "你最近可能在意：做了不少事情，为什么真正被看见的成果还不够？",
        "资源机会": "你最近可能在盘算：守住现有收入，还是为新的方向承担一点风险？",
        "责任压力": "你最近可能更累的是：责任越来越多，收入或位置却没有一起增加？",
        "准备判断": "你最近可能在怀疑：还要继续准备，还是该主动争取一次机会？",
    },
    "感情关系": {
        "自主边界": "你最近可能在想：这段关系里，自己的需要是不是总被放到后面？",
        "合作位置": "你最近可能在意：两个人关系不错，为什么一谈未来就容易反复？",
        "能力产出": "你最近可能困惑：明明有感情，为什么重要的话总是说不到一起？",
        "资源机会": "你最近可能在权衡：感情要继续，城市、住房和钱该怎么安排？",
        "责任压力": "你最近可能有压力：这段关系是不是已经走到必须表态的时候？",
        "准备判断": "你最近可能在观察：对方真的适合长期相处，还是只是目前习惯了？",
    },
    "财务安排": {
        "自主边界": "你最近可能想解决：怎样增加收入，又不把自己困在不喜欢的工作里？",
        "合作位置": "你最近可能在意：和别人一起做事，钱和责任到底该怎么分？",
        "能力产出": "你最近可能困惑：能力和时间投入不少，为什么还没有稳定变成收入？",
        "资源机会": "你最近可能在盘算：该继续存钱，还是拿一部分去尝试新的机会？",
        "责任压力": "你最近可能担心：收入看起来还行，为什么现金流仍让人没有安全感？",
        "准备判断": "你最近可能在想：还要先提升能力，还是现在就开始增加收入？",
    },
    "家庭关系": {
        "自主边界": "你最近可能在想：自己的决定，还要不要继续先得到家里同意？",
        "合作位置": "你最近可能为难：家里的事总要你协调，但你的需要由谁照顾？",
        "能力产出": "你最近可能不知道：怎样把自己的想法说清楚，又不让关系立刻变僵？",
        "资源机会": "你最近可能在权衡：要帮家里到什么程度，才不会影响自己的生活？",
        "责任压力": "你最近可能觉得累：家里的责任是不是越来越自然地落到你身上？",
        "准备判断": "你最近可能在反复确认：按家里的安排走，真的会更稳妥吗？",
    },
    "学习发展": {
        "自主边界": "你最近可能在犹豫：继续走熟悉的学习路线，还是换一个更想学的方向？",
        "合作位置": "你最近可能在意：跟着别人的节奏准备，真的适合自己吗？",
        "能力产出": "你最近可能在想：学了不少东西，什么时候才能真正派上用场？",
        "资源机会": "你最近可能在权衡：继续投入时间和钱学习，回报是否值得？",
        "责任压力": "你最近可能有压力：这次考试、申请或转方向，是不是不能再失败？",
        "准备判断": "你最近可能卡在：还要准备到什么程度，才算可以开始行动？",
    },
    "城市与生活": {
        "自主边界": "你最近可能在想：留在熟悉的地方，还是去更适合自己的城市？",
        "合作位置": "你最近可能为难：自己的发展和伴侣、家人的安排很难放在一起？",
        "能力产出": "你最近可能不确定：换个环境真的会变好，还是问题仍会跟着自己？",
        "资源机会": "你最近可能在权衡：更好的机会，值不值得承担房租和生活成本？",
        "责任压力": "你最近可能觉得被催着决定：工作、住房和落脚城市该先定哪一个？",
        "准备判断": "你最近可能在等待：是不是再准备充分一点，才适合离开现在的环境？",
    },
}

ISSUE_ALTERNATES = {
    ("事业选择", "责任压力"): [
        "你最近可能在纠结：该继续扛下更多责任，还是先把回报和位置谈清楚？",
        "你最近可能最不满的是：工作要求不断提高，属于你的机会却没有增加？",
    ],
    ("城市与生活", "自主边界"): [
        "你最近可能在犹豫：继续留在这里求稳，还是换个城市重新开始？",
        "你最近可能想弄清楚：不舒服来自这座城市，还是目前的生活方式？",
    ],
    ("财务安排", "资源机会"): [
        "你最近可能拿不准：手里的钱应该先留作安全感，还是用来争取新机会？",
        "你最近可能更在意：怎样让收入增加，又不把现有生活变得太冒险？",
    ],
    ("学习发展", "准备判断"): [
        "你最近可能在想：继续考证或深造，真的比现在开始实践更有用吗？",
        "你最近可能困惑：是不是总觉得还没准备好，所以一直没有真正开始？",
    ],
    ("家庭关系", "准备判断"): [
        "你最近可能在问自己：听家里的安排是稳妥，还是只是省去争执？",
    ],
    ("感情关系", "合作位置"): [
        "你最近可能在想：两个人迟迟谈不拢未来，是时机问题还是目标不同？",
    ],
}

DOMAIN_STAGE_EXAMPLES = {
    "事业选择": {
        "需要决定期": "可能是续约、转岗、离职或新机会同时出现，需要你尽快表态。",
        "逐渐展开期": "可能是新任务开始增加，但回报和长期位置还没有确定。",
        "调整安排期": "可能是原来的工作安排越来越难维持，需要重新分配时间和责任。",
        "成果积累期": "可能是成绩已经出现，但下一步该争取位置、收入还是空间还没想清。",
        "反复确认期": "可能是日常还能继续，却总觉得成长、收入或意义少了一块。",
    },
    "感情关系": {
        "需要决定期": "可能是结婚、分开、异地或见家长等问题已经很难继续回避。",
        "逐渐展开期": "可能是关系正在向前，但双方对未来节奏还没有完全一致。",
        "调整安排期": "可能是以前默认的相处方式开始失效，需要重新谈清边界和安排。",
        "成果积累期": "可能是关系已经稳定，下一步反而更需要谈现实生活怎么落地。",
        "反复确认期": "可能是相处没有大问题，但同一个顾虑一直没有真正解决。",
    },
    "财务安排": {
        "需要决定期": "可能是换工作、投资、买房或一笔较大支出正在逼近决定。",
        "逐渐展开期": "可能是收入机会开始增加，但能否持续、该投入多少还不确定。",
        "调整安排期": "可能是原来的收支方式不再合适，需要重新安排储蓄和现金流。",
        "成果积累期": "可能是手里的资源开始变多，但怎么分配才能更有效仍没想清。",
        "反复确认期": "可能是钱没有立刻出问题，却总觉得离真正安心还有距离。",
    },
    "家庭关系": {
        "需要决定期": "可能是住房、照顾家人或一项家庭决定需要你明确承担多少。",
        "逐渐展开期": "可能是家庭角色正在变化，别人开始对你提出更多现实期待。",
        "调整安排期": "可能是原有分工已经让你疲惫，需要重新谈谁负责什么。",
        "成果积累期": "可能是你已经能照顾很多事，但也开始想为自己留下更多空间。",
        "反复确认期": "可能是表面相处平稳，同一个边界问题却总在不同事情里出现。",
    },
    "学习发展": {
        "需要决定期": "可能是考试、申请、转专业或转方向已经到了必须选择的时候。",
        "逐渐展开期": "可能是新的学习机会出现，但投入后能走到哪里还不确定。",
        "调整安排期": "可能是原来的准备方式效率下降，需要重新安排时间和重点。",
        "成果积累期": "可能是能力已经积累不少，下一步更重要的是拿去解决真实问题。",
        "反复确认期": "可能是一直在准备，却总觉得还差一点才敢真正开始。",
    },
    "城市与生活": {
        "需要决定期": "可能是工作、租约、伴侣或家人的安排让落脚城市必须尽快确定。",
        "逐渐展开期": "可能是新的城市或生活方案开始可行，但现实成本还需要计算。",
        "调整安排期": "可能是现在的通勤、住房或生活节奏已经越来越难维持。",
        "成果积累期": "可能是生活逐渐稳定后，你反而开始考虑这里是否适合长期留下。",
        "反复确认期": "可能是眼下没有非走不可，却经常想象换个地方会不会更好。",
    },
}


def _add_domain_scores(scores: Counter[str], god: str, weight: float) -> None:
    # 每个作用只投向最相关的两个现实领域，避免“事业”因为出现在所有
    # 十神中被机械累加为几乎所有用户的第一名。
    ranked = sorted(
        DOMAIN_WEIGHTS[god].items(),
        key=lambda item: item[1],
        reverse=True,
    )
    scores[ranked[0][0]] += weight
    if len(ranked) > 1:
        scores[ranked[1][0]] += weight * 0.42


def _add_mechanism_score(scores: Counter[str], god: str, weight: float) -> None:
    scores[MECHANISM_BY_GOD[god]] += weight


def _stage_label(timeline: list[dict[str, Any]], center_year: int) -> str:
    current_index = next(index for index, item in enumerate(timeline) if item["year"] == center_year)
    current = timeline[current_index]
    previous = timeline[current_index - 1] if current_index else current
    delta = current["average"] - previous["average"]
    if current["volatility"] >= 14:
        return "需要决定期"
    if delta >= 2.5:
        return "逐渐展开期"
    if delta <= -2.5:
        return "调整安排期"
    if current["average"] >= 62:
        return "成果积累期"
    return "反复确认期"


def _select_headline(
    domain: str,
    mechanism: str,
    signature: dict[str, Any],
    stage_label: str,
    current_luck: dict[str, Any] | None,
) -> str:
    candidates = [ISSUE_HEADLINES[domain][mechanism]]
    candidates.extend(ISSUE_ALTERNATES.get((domain, mechanism), []))
    seed = signature["task_code"] + stage_label
    if current_luck:
        seed += current_luck.get("pillar", "")
    return candidates[sum(ord(char) for char in seed) % len(candidates)]


def generate_current_issue(
    bazi: dict[str, Any],
    timeline: list[dict[str, Any]],
    center_year: int,
    birth_year: int,
    card_copy: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    day_master = bazi["day_master"]
    scores: Counter[str] = Counter()
    mechanism_scores: Counter[str] = Counter()
    signature = card_copy["analysis_signature"]

    # 核心配置和主线任务直接进入当前课题，而不是只使用年龄段。
    for god, weight in (
        (signature["primary_god"], 1.6),
        (signature["outcome_god"], 1.3),
        (signature["tension_god"], 0.8),
    ):
        _add_domain_scores(scores, god, weight)
        _add_mechanism_score(mechanism_scores, god, weight)

    current_luck = luck_for(bazi, center_year)
    if current_luck and current_luck["pillar"]:
        luck_gods = (
            (ten_god(day_master, current_luck["pillar"][0]), 2.2),
            (ten_god(day_master, HIDDEN[current_luck["pillar"][1]][0]), 1.2),
        )
        for god, weight in luck_gods:
            _add_domain_scores(scores, god, weight)
            _add_mechanism_score(mechanism_scores, god, weight)
    for year, weight in ((center_year - 2, 0.6), (center_year - 1, 1.0), (center_year, 1.5)):
        pillar = year_ganzhi(year)
        year_gods = (
            (ten_god(day_master, pillar[0]), weight),
            (ten_god(day_master, HIDDEN[pillar[1]][0]), weight * 0.45),
        )
        for god, god_weight in year_gods:
            _add_domain_scores(scores, god, god_weight)
            _add_mechanism_score(mechanism_scores, god, god_weight)

    # 年龄只作轻量生活情境修正，不再直接决定二十多岁用户的课题。
    age = center_year - birth_year
    if 20 <= age <= 24:
        scores["学习发展"] += 0.20
        scores["城市与生活"] += 0.15
    elif 25 <= age <= 29:
        scores["事业选择"] += 0.20
        scores["财务安排"] += 0.15
        scores["感情关系"] += 0.10
    elif 30 <= age <= 34:
        scores["事业选择"] += 0.15
        scores["家庭关系"] += 0.15
        scores["感情关系"] += 0.10
    elif 35 <= age <= 40:
        scores["事业选择"] += 0.12
        scores["财务安排"] += 0.12
        scores["家庭关系"] += 0.12

    domain_order = list(ISSUE_HEADLINES)
    domain = max(domain_order, key=lambda item: (scores[item], -domain_order.index(item)))
    mechanism_order = list(next(iter(ISSUE_HEADLINES.values())))
    mechanism = max(
        mechanism_order,
        key=lambda item: (mechanism_scores[item], -mechanism_order.index(item)),
    )
    stage_label = _stage_label(timeline, center_year)

    issue = {
        "domain": domain,
        "mechanism": mechanism,
        "headline": _select_headline(domain, mechanism, signature, stage_label, current_luck),
        "example": DOMAIN_STAGE_EXAMPLES[domain][stage_label],
        "evidence": {
            "core": signature["task_code"],
            "current_luck": current_luck["pillar"] if current_luck else "",
            "recent_years": [year_ganzhi(year) for year in range(center_year - 2, center_year + 1)],
            "age_used_as_tiebreaker": True,
        },
    }
    return stage_label, issue


def build_kline_result(
    bazi: dict[str, Any],
    birth_year: int,
    card_copy: dict[str, Any],
    center_year: int | None = None,
) -> dict[str, Any]:
    center_year = center_year or datetime.now().year
    profile = build_structure_profile(bazi, center_year)
    timeline = calculate_life_kline(bazi, profile, center_year)
    stage_label, current_issue = generate_current_issue(
        bazi,
        timeline,
        center_year,
        birth_year,
        card_copy,
    )
    return {
        "center_year": center_year,
        "timeline_algorithm": "continuity-v3-structured-topic",
        "timeline": timeline,
        "stage_label": stage_label,
        "current_issue": current_issue,
    }


def visible_axis_range(timeline: list[dict[str, Any]]) -> tuple[int, int]:
    """供渲染测试复核纵轴至少展示 40 点范围。"""

    raw_min = min(item["low"] for item in timeline)
    raw_max = max(item["high"] for item in timeline)
    axis_min = max(0, floor((raw_min - 3) / 10) * 10)
    axis_max = min(100, ceil((raw_max + 3) / 10) * 10)
    if axis_max - axis_min < 40:
        pad = (40 - (axis_max - axis_min)) / 2
        axis_min = max(0, floor((axis_min - pad) / 10) * 10)
        axis_max = min(100, ceil((axis_max + pad) / 10) * 10)
    return axis_min, axis_max
