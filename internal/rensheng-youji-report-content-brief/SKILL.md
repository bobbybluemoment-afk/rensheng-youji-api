---
name: rensheng-youji-report-content-brief
description: 人生有迹内部报告事实整理层。接收已校验且完成现实校准的0.6.0 Core母稿，从开放现实候选、判断台账、人物形成链与领域联动链中选择可进入完整报告的材料，并由脚本实体化Core判断与证据，生成不含用户文章的report-content-brief.json。用于完整报告写作前锁定事实、置信度、现实名词和关注方向范围；不负责排盘、重新推命、写正文或渲染PDF。
---

# 报告事实整理层

## 工作顺序

1. 读取校准后的 Core 母稿，确认 `core_version=0.6.0`。
2. 读取 [content-brief.md](references/content-brief.md)。
3. 只选择 `match`、`partial` 或仍可条件表达的 `unverified` 判断；禁止使用 `reject`。
4. 分别为完整人生主线、六个现实领域和当前问题准备材料。
5. 用户关注方向只进入当前阶段、问题回应、相关年份与行动建议，不改变完整人生主线和六领域基础内容。
6. 先生成 `report-content-selection.json`，只选择 `claim_ids`、形成链、联动链、允许例子和禁止外推，不手抄Core判断正文。
7. 用确定性脚本把每条判断的原文、机制、证据、反证、来源类型和哈希写入事实提纲：

```bash
python internal/rensheng-youji-report-content-brief/scripts/materialize_content_brief.py \
  work/report-content-selection.json \
  --analysis work/analysis-output-calibrated.json \
  --output work/report-content-brief.json
```

8. 运行：

```bash
python internal/rensheng-youji-report-content-brief/scripts/validate_content_brief.py \
  work/report-content-brief.json --analysis work/analysis-output-calibrated.json
```

## 约束

- 事实提纲不写用户可见散文。
- 所有结论必须引用Core的 `claim_id`，写作时直接读取 `selected_claims` 中的现实结论、机制链和限制，不得只凭编号或允许例子自由补写。
- 完整人生主线和六个领域至少八成判断来自 `chart_baseline` 或 `timing_baseline`；每个内容区最多使用一条 `user_fact_refinement`。当前问题可以更多使用校准结果，但不得制造新命理结论。
- 具体组织、行业、岗位、收入或伴侣特征只能来自 Core 允许例子或开放候选。
- 校准答案只作为内部筛选依据，不形成用户可见栏目。
- 证据不足时记录缺口，不用常见人生路径补造。
