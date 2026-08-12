"""地支关系的事实层提取，解释由调用模型完成。"""

from itertools import combinations


PAIR_RELATIONS = {
    "六合": ("子丑", "寅亥", "卯戌", "辰酉", "巳申", "午未"),
    "六冲": ("子午", "丑未", "寅申", "卯酉", "辰戌", "巳亥"),
    "六害": ("子未", "丑午", "寅巳", "卯辰", "申亥", "酉戌"),
    "六破": ("子酉", "丑辰", "寅亥", "卯午", "巳申", "未戌"),
}

THREE_PUNISHMENTS = (
    (frozenset("寅巳申"), "寅巳申三刑"),
    (frozenset("丑未戌"), "丑未戌三刑"),
)


def branch_relations(branches: list[str]) -> list[dict]:
    labels = ("year", "month", "day", "time")
    result: list[dict] = []
    for (left_i, left), (right_i, right) in combinations(enumerate(branches), 2):
        pair = frozenset((left, right))
        for relation, candidates in PAIR_RELATIONS.items():
            if any(pair == frozenset(candidate) for candidate in candidates):
                result.append({
                    "relation": relation,
                    "branches": left + right,
                    "positions": [labels[left_i], labels[right_i]],
                })
        if pair == frozenset("子卯"):
            result.append({"relation": "相刑", "branches": left + right, "positions": [labels[left_i], labels[right_i]]})

    present = set(branches)
    for members, name in THREE_PUNISHMENTS:
        if members.issubset(present):
            result.append({"relation": "三刑", "branches": name[:3], "positions": []})
    for branch in "辰午酉亥":
        if branches.count(branch) >= 2:
            positions = [labels[i] for i, value in enumerate(branches) if value == branch]
            result.append({"relation": "自刑", "branches": branch * 2, "positions": positions})
    return result

