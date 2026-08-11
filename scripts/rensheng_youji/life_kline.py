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
    "比肩": {"事业选择": 2, "感情关系": 1, "财务安排": 1, "城市与生活": 1},
    "劫财": {"事业选择": 2, "感情关系": 2, "财务安排": 1},
    "食神": {"事业选择": 2, "学习发展": 2, "城市与生活": 1},
    "伤官": {"事业选择": 3, "学习发展": 1, "城市与生活": 2},
    "偏财": {"财务安排": 3, "事业选择": 2, "家庭关系": 1},
    "正财": {"财务安排": 3, "事业选择": 2, "感情关系": 1},
    "七杀": {"事业选择": 3, "感情关系": 1, "家庭关系": 1},
    "正官": {"事业选择": 3, "感情关系": 2, "家庭关系": 1},
    "偏印": {"学习发展": 3, "事业选择": 1, "城市与生活": 1},
    "正印": {"学习发展": 2, "家庭关系": 2, "事业选择": 1},
}

ISSUE_COPY = {
    "事业选择": {
        "headline": "你最近可能在想：现在这份工作还值不值得继续？",
        "example": "可能是事情越做越多，但收入、位置或成长没有一起增加。",
    },
    "感情关系": {
        "headline": "你最近可能在想：这段关系要不要把未来说清楚？",
        "example": "可能是相处没有大问题，但结婚、城市或生活安排一直没谈明白。",
    },
    "财务安排": {
        "headline": "你最近可能更在意：怎样多赚一点，又不影响现有稳定？",
        "example": "例如想增加收入或尝试投资，但又担心存款、现金流或失败成本。",
    },
    "家庭关系": {
        "headline": "你最近可能在想：自己的决定还要不要继续让家里影响？",
        "example": "可能是想按自己的计划生活，又担心拒绝父母会让关系变紧张。",
    },
    "学习发展": {
        "headline": "你最近可能在想：还要继续准备，还是先把能力用起来？",
        "example": "例如想考证、读书或转方向，但担心投入不少，最后仍然用不上。",
    },
    "城市与生活": {
        "headline": "你最近可能在想：要留在这里，还是换个地方生活？",
        "example": "可能是工作、住房和家人各有牵制，很难同时顾到稳定与发展。",
    },
}


def _add_domain_scores(scores: Counter[str], god: str, weight: float) -> None:
    for domain, value in DOMAIN_WEIGHTS[god].items():
        scores[domain] += value * weight


def generate_current_issue(
    bazi: dict[str, Any],
    timeline: list[dict[str, Any]],
    center_year: int,
    birth_year: int,
) -> tuple[str, dict[str, Any]]:
    day_master = bazi["day_master"]
    scores: Counter[str] = Counter()

    for index, pillar in enumerate(bazi["pillars"]):
        if index != 2:
            _add_domain_scores(scores, ten_god(day_master, pillar[0]), 0.55)
    current_luck = luck_for(bazi, center_year)
    if current_luck and current_luck["pillar"]:
        _add_domain_scores(scores, ten_god(day_master, current_luck["pillar"][0]), 2.0)
        _add_domain_scores(scores, ten_god(day_master, HIDDEN[current_luck["pillar"][1]][0]), 1.1)
    for year, weight in ((center_year - 2, 0.6), (center_year - 1, 1.0), (center_year, 1.5)):
        pillar = year_ganzhi(year)
        _add_domain_scores(scores, ten_god(day_master, pillar[0]), weight)
        _add_domain_scores(scores, ten_god(day_master, HIDDEN[pillar[1]][0]), weight * 0.45)

    age = center_year - birth_year
    if 20 <= age <= 24:
        scores["学习发展"] += 0.8
        scores["城市与生活"] += 0.7
    elif 25 <= age <= 29:
        scores["事业选择"] += 0.8
        scores["财务安排"] += 0.5
        scores["感情关系"] += 0.4
    elif 30 <= age <= 34:
        scores["事业选择"] += 0.6
        scores["家庭关系"] += 0.5
        scores["感情关系"] += 0.4
    elif 35 <= age <= 40:
        scores["事业选择"] += 0.5
        scores["财务安排"] += 0.5
        scores["家庭关系"] += 0.5

    domain = max(ISSUE_COPY, key=lambda item: (scores[item], -list(ISSUE_COPY).index(item)))
    current_index = next(index for index, item in enumerate(timeline) if item["year"] == center_year)
    current = timeline[current_index]
    previous = timeline[current_index - 1] if current_index else current
    delta = current["average"] - previous["average"]
    if current["volatility"] >= 14:
        stage_label = "需要决定期"
    elif delta >= 2.5:
        stage_label = "逐渐展开期"
    elif delta <= -2.5:
        stage_label = "调整安排期"
    elif current["average"] >= 62:
        stage_label = "成果积累期"
    else:
        stage_label = "反复确认期"

    issue = {
        "domain": domain,
        **ISSUE_COPY[domain],
        "evidence": ["原局主线", "当前大运", "近三年"],
    }
    return stage_label, issue


def build_kline_result(bazi: dict[str, Any], birth_year: int, center_year: int | None = None) -> dict[str, Any]:
    center_year = center_year or datetime.now().year
    profile = build_structure_profile(bazi, center_year)
    timeline = calculate_life_kline(bazi, profile, center_year)
    stage_label, current_issue = generate_current_issue(
        bazi,
        timeline,
        center_year,
        birth_year,
    )
    return {
        "center_year": center_year,
        "timeline_algorithm": "continuity-v2-deterministic",
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
