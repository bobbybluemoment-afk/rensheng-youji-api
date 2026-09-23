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
  --focus "事业发展" \
  --output work/resolved-report-sources.json
```

该程序从用户可见选材中排除 `reject`、`weakened` 和 `uncertain`，按冻结优先级和覆盖映射选择剩余判断，再确定正式 `mandatory_claim_ids` 与 `emphasis_claim_ids`。这些状态仍留在校准后Core和增量记录中供审计，不等于删除原候选。关注方向会确定“当前问题”的直接判断领域；其他领域不能越过该筛选变成独立回答。任何模型不得手工编辑选材结果。

章节按校准后可用证据进入四种模式：

- `normal`：至少4条且关键解释角度完整；
- `shortened`：至少2条，或仍有覆盖缺口，缩短表达；
- `minimal`：仅1条，只写可靠结论；
- `evidence_gap`：0条，只说明可靠边界。

“当前问题”不是第二篇领域综述：优先选择当前阶段、现实挑战和应对方向，最多保留3条聚焦判断；有可靠判断时按压缩回答组织，没有判断时才进入证据缺口。

单章降级不得阻塞其他可靠章节。只有确定性排盘、Core完整性、Baseline哈希或来源一致性失败，才停止整份交付。
