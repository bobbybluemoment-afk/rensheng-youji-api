---
name: rensheng-youji-report-content-brief
description: 人生有迹内部报告事实整理层。接收已冻结并以校准增量合成的0.10.0 Core母稿和确定性校准后选材，从六领域独立判断、方法综合、人物形成链与领域联动链中实体化证据、必须兑现的白话判断和校准变化，生成不含用户文章的report-content-brief.json。用于完整报告写作前锁定事实与判断；不负责排盘、重新推命、自由选择报告结论、写正文或渲染PDF。
---

# 报告事实整理层

## 工作顺序

1. 读取校准后的 Core 母稿，确认 `core_version=0.10.0`，并确认它已通过Baseline冻结校验。
2. 读取 [content-brief.md](references/content-brief.md)。
3. 优先选择 `match`，同时保留能够共存的 `supported_unselected`、明确场景的 `conditional`、降低优先的 `weakened`，以及确有多方法支持的 `unverified`；禁止使用 `reject`。
4. 分别为完整人生主线、六个现实领域和当前问题准备材料。
5. 用户关注方向只进入当前阶段、问题回应、相关年份与行动建议，不改变完整人生主线和六领域基础内容。
6. 先运行校准后确定性选材程序。不得由模型手工删除、补充或替换判断：

```bash
python scripts/resolve_report_sources.py \
  work/analysis-output-calibrated.json \
  --output work/resolved-report-sources.json
```

7. 生成 `report-content-selection.json`，只补充允许例子和禁止外推；正式判断名单、覆盖项、重点句、必进句和降级模式必须来自 `resolved-report-sources.json`。
8. 用确定性脚本把每条判断、实体证据、人物形成链、领域联动链、盲派现实取象、根苗花果领域生命周期、候选关系、校准变化和哈希写入事实提纲：

```bash
python internal/rensheng-youji-report-content-brief/scripts/materialize_content_brief.py \
  work/report-content-selection.json \
  --analysis work/analysis-output-calibrated.json \
  --resolved-sources work/resolved-report-sources.json \
  --output work/report-content-brief.json
```

9. 运行：

```bash
python internal/rensheng-youji-report-content-brief/scripts/validate_content_brief.py \
  work/report-content-brief.json \
  --analysis work/analysis-output-calibrated.json \
  --resolved-sources work/resolved-report-sources.json
```

## 约束

- 事实提纲不写用户可见散文。
- 所有结论必须引用Core的 `claim_id`，写作时直接读取实体化的判断、证据、形成链、联动链、现实取象、候选关系和限制，不得只凭编号或允许例子自由补写。
- 每个内容区必须原样携带1—2条 `mandatory_claims`，包括 `claim_id`、`plain_claim`、判断家族、机制家族和新增信息。后续写作必须逐字兑现 `plain_claim`；事实提纲不能自行概括。
- 写作层只能读取实体化提纲，不重新读取原始四柱自行推命。具体行业、岗位、家庭状态、收入来源、关系特征和年份必须来自实体化材料。
- 完整人生主线和六个领域至少八成判断来自 `chart_baseline` 或 `timing_baseline`；每个内容区最多使用一条 `user_fact_refinement`。当前问题可以更多使用校准结果，但不得制造新命理结论。
- 具体组织、行业、岗位、收入或伴侣特征只能来自 Core 允许例子或开放候选。
- 校准答案只作为内部筛选依据，不形成用户可见栏目。
- 证据不足时记录缺口，不用常见人生路径补造。
- `delivery_mode=normal` 时使用完整篇幅；`shortened`、`minimal` 或 `evidence_gap` 时按模式缩短对应章节，不得补入被排除判断，也不得阻塞其他可靠章节。
