# 从独立方法包到完整Core

## 为什么需要生产桥

独立方法包只包含各方法自己的技术结论、现实候选和证据，不能直接作为完整Core。方法综合、人物画像、领域判断、年份连续性和报告判断台账需要语言模型完成语义分析，但排盘事实、方法包、证据、方法状态、校准初始状态和报告来源映射不得由模型手工拼装。

因此完整Core必须经过“确定性汇总—受约束语义综合—确定性组装”三段流程。

## 第一段：确定性汇总

九个规定方法包全部通过单方法校验或被合法记录为失败状态后，运行：

```bash
python3 scripts/prepare_core_synthesis.py analysis-input.json \
  --method-packet-dir method-packets \
  --output core-synthesis-input.json
```

脚本负责：

- 确认九个方法恰好各有一个方法包；
- 再次执行逐方法校验；
- 合并实体证据并拒绝跨方法重复编号；
- 确定性计算完整、降级或仅初步分析；
- 冻结输入哈希；
- 列出语义综合必须生成的全部区块。

## 第二段：受约束语义综合

语言模型读取 `core-synthesis-input.json`，生成 `core-semantic-analysis.json`。这是必要的分析环节，不属于绕过或手工拼Schema。

模型只能生成 `semantic_output_contract.required_sections` 中列出的区块。不得输出或改写：

- `analysis_meta`；
- `chart_facts` 与 `chart_audit`；
- `independent_method_analyses`；
- `method_execution_audit`；
- `evidence_registry`；
- `calibration_state` 与 `calibration_delta`；
- `report_source_bundle`。

综合判断必须引用方法包中真实存在的现实候选与证据。主要判断需要两个独立主要方法；单一主要方法只能形成补充或待验证判断。

## 第三段：校验与确定性组装

先运行：

```bash
python3 scripts/validate_core_synthesis.py \
  core-synthesis-input.json core-semantic-analysis.json
```

失败时只修复语义综合输出：

1. 第一轮修复缺失区块、未知区块和无效引用；
2. 第二轮修复方法独立性、判断角色和冲突关系；
3. 第三轮修复人物覆盖、年度连续性、候选池和领域映射。

不得重新运行已经通过的方法包。第三轮仍失败时停止完整Core交付，返回实际错误，不得补占位内容。

校验通过后运行：

```bash
python3 scripts/finalize_core_analysis.py \
  core-synthesis-input.json core-semantic-analysis.json \
  --output analysis-output-initial.json
```

该脚本确定性写入排盘事实、方法与证据、方法执行审计、校准初始状态，并自动生成 `report_source_bundle`，随后同时执行Schema和完整Core语义校验。成功输出可以直接进入Baseline冻结，不再需要模型创建 `analysis-output-before-sources.json`。

## 停止条件

- 方法包缺失或重复：停在确定性汇总；
- 输入哈希不一致：停在确定性组装；
- 语义综合三轮后仍不通过：停在完整Core综合；
- `delivery_decision=preliminary_only`：允许保存初步分析，但不得冻结Baseline或进入正式报告；
- `full` 或 `degraded` 且最终组装通过：进入Baseline冻结与校准。
