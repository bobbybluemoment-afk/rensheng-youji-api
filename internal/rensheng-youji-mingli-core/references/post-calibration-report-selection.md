# 校准后报告选材

Core负责冻结完整判断候选池，不在校准前决定最终报告名单。每个报告素材区必须提供：

- 当前证据实际允许的候选判断和无重复的 `claim_priority`；
- 当前证据实际允许的0—2条 `mandatory_candidate_ids`；有可用判断时至少1条，稀疏的当前阶段来源允许只有1条；
- 允许为空的 `emphasis_candidate_ids`；
- 六项通用人物覆盖，以及家庭、身心的专属覆盖；
- `coverage_claim_map`，每个实际覆盖项至少绑定一个候选判断；缺少时记录证据缺口，不制造第二条近义判断。

校准只改变候选与判断状态。完成校准后，运行：

```bash
python scripts/run_in_env.py scripts/resolve_report_sources.py \
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
