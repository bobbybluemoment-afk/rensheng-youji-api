# 校准后报告选材

Core负责冻结完整判断候选池，不在校准前决定最终报告名单。每个报告素材区必须提供：

- 至少8条候选判断和无重复的 `claim_priority`；
- 2—4条 `mandatory_candidate_ids`；
- 允许为空的 `emphasis_candidate_ids`；
- 六项通用人物覆盖，以及家庭、身心的专属覆盖；
- `coverage_claim_map`，每个覆盖项至少绑定两个按优先级排列的候选判断。

校准只改变候选与判断状态。完成校准后，运行：

```bash
python scripts/resolve_report_sources.py \
  work/analysis-output-calibrated.json \
  --output work/resolved-report-sources.json
```

该程序排除 `reject`，按冻结优先级和覆盖映射选择剩余判断，再确定正式 `mandatory_claim_ids` 与 `emphasis_claim_ids`。任何模型不得手工编辑选材结果。

章节按校准后可用证据进入四种模式：

- `normal`：至少6条，完整覆盖；
- `shortened`：至少4条，缩短表达并列出缺口；
- `minimal`：至少2条，只写可靠结论；
- `evidence_gap`：0—1条，明确暂不下结论。

单章降级不得阻塞其他可靠章节。只有确定性排盘、Core完整性、Baseline哈希或来源一致性失败，才停止整份交付。
