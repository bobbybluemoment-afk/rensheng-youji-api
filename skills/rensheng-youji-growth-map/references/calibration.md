# 五条事实校准规范 v2.1

## 目的与边界

校准用于在 Core 已经支持的多种现实表现中确认实际落点，并判断当前大运、流年通过什么现实载体执行。它可以调整现实映射、候选状态、排序和置信度，但不能修改四柱、原局结构或时运事实，也不能把用户答案倒推成命理证据。

五题至少覆盖四个生活领域，同一领域最多两题，用户关注方向最多两题。至少两题必须核对客观状态或已经发生的事件，至少一题必须带明确时间窗口并绑定 `candidate_kind=timed_event` 的 Core 候选。这样五题不会退化成性格问卷。

## 固定题型而不是自由写题

用户模型不得自行撰写题干和选项。完整读取 [calibration-question-templates.json](calibration-question-templates.json)，只负责：

1. 从 Core 候选池判断哪五个比较轴最有信息量；
2. 选择五个不重复的 `template_id`；
3. 把A、B、C分别绑定到候选状态变化；
4. 填写内部证据、来源、替代解释和时柱依赖；
5. 运行构建器生成固定用户可见文字。

固定题型已经为每题锁定：生活领域、比较轴、时间窗口、选择规则、题干、A/B/C互斥值、受影响的Core结论和证据类型。用户模型不能改写“过去一年”为“近几年”，不能把收入来源、投资习惯和收入趋势混进同一道题，也不能把家庭财务矛盾放进身心题。

## Core候选要求

每条 `reality_candidate_pool` 候选必须包含：

- `domain`：固定为八个现实领域之一；
- `candidate_kind`：`stable_pattern`、`objective_state`、`timed_event` 或 `current_stage`；
- `time_scope`：长期、当前阶段或明确年份范围；
- `calibration_targets`：答案实际会调整的1—4个Core结论路径；
- 原有结论、可观察表现、替代解释、来源、置信度、验证问题和状态。

带时间窗口的题必须绑定至少一个 `timed_event` 候选，且该候选必须具有大运或流年证据。只由日主旺衰或单个十神支持的候选不得进入五题。

## calibration-plan.json

模型只生成内部计划，不生成用户可见题目：

```json
{
  "schema_version": "1.0.0",
  "questions": [
    {
      "template_id": "finance.primary_income_source",
      "candidate_effects": {
        "A": [{"candidate_id": "c07", "status": "match"}],
        "B": [{"candidate_id": "c07", "status": "partial"}],
        "C": [{"candidate_id": "c07", "status": "reject"}]
      },
      "evidence_lenses": ["resource_relationship", "cross_method_analysis"],
      "core_sections": ["reality_candidate_pool", "reality_domains.wealth"],
      "alternatives": ["现实职业结构也会直接影响收入来源"],
      "birth_time_dependency": "none",
      "confidence": "medium"
    }
  ]
}
```

每个选项必须对至少一个真实 Core 候选产生 `match`、`partial` 或 `reject` 影响；A、B、C的影响组合不得完全相同。三项可以作用于同一个候选，也可以分别支持不同候选，但所有候选必须存在于初始母稿并与题型领域一致。

## 确定性生成与校验

先构建，再校验并生成唯一可发给用户的Markdown：

```bash
python scripts/run_in_env.py skills/rensheng-youji-growth-map/scripts/build_calibration_questions.py \
  --plan work/calibration-plan.json \
  --analysis work/analysis-output-initial.json \
  --output work/calibration-questions.json

python scripts/run_in_env.py skills/rensheng-youji-growth-map/scripts/validate_calibration_questions.py \
  work/calibration-questions.json \
  --analysis work/analysis-output-initial.json \
  --visible-out work/calibration-visible.md
```

`calibration-questions.json` 使用 `schema_version=2.1.0`。构建器从模板原样填充 `display`，校验器逐字比对；任何模型自行改写的题干或选项都会失败。内部候选编号、命理证据、置信度和替代解释永远不进入 `calibration-visible.md`。

## 回写规则

- A、B或C：记录对应 `template_id`、固定 `selected_value` 和该选项的 `candidate_updates`；
- D：`selected_value=uncertain`、`candidate_updates=[]`，不能默认支持最接近的候选；
- 用户补充事实：同时写入 `reality_context`、报告 `user_note` 和相关Core候选的用户事实来源；
- `match` 只提高对应候选，`partial` 保留条件，`reject` 降低或删除该现实映射；
- 用户选择不能让无关领域顺带提高置信度；
- 多题与Core时运候选持续冲突时，复查地点、真太阳时、起运和相邻时柱，而不是修改既定盘面迎合答案。

报告中的每条校准响应必须能够回答：“这道题改变了哪个现实候选和哪一段报告？”如果选择A、B、C后报告完全不变，这道题没有实现校准功能。
