---
name: rensheng-youji-report-writer
description: 人生有迹内部人物写作层。接收已校验的report-content-brief.json，把Core支持的事实、形成链和领域联动组织成完整人生主线、六个现实领域与当前问题回应的中文初稿。用于完整报告成稿；不重新推命、不新增职业经历或家庭关系事实、不校准、不渲染PDF。
---

# 人物写作层

1. 完整读取 [portrait-writing.md](references/portrait-writing.md)。
2. 先由程序把事实提纲编译成紧凑写作任务包。程序按“主要表现与行为→形成经历与现实条件→重复挑战、阶段变化与应对”分配段落角色，而不是把判断按编号轮流塞进段落；同时删除写作AI不需要的哈希、证据登记和技术机制字段：

```bash
python scripts/run_in_env.py internal/rensheng-youji-report-writer/scripts/build_report_writing_pack.py \
  --brief work/report-content-brief.json \
  --analysis work/analysis-output-calibrated.json \
  --output work/report-writing-pack.json
```

AI只读取这份任务包，逐一填写 `slot_id` 对应的自然中文段落，并填写2—4项能力与资源、阶段、20年观察、行动和2—5个待观察问题。完整人生主线、形成过程和当前问题已经在段落槽中，不得再生成最终报告不会使用的重复摘要。不得读取原始四柱重新推命。
3. 完整人生主线和当前问题回应都继承事实提纲的 `delivery_mode`：`normal` 写2—4段、500—700字，`shortened` 写2—3段、320—500字，`minimal` 写1—2段、180—320字，`evidence_gap` 写1段、60—180字。证据充足时完整综述，证据不足时只写可靠边界。
4. 六个现实领域在 `normal` 模式下各写2—4个自然段、500—700个汉字；`shortened` 写2—3段、320—500字；`minimal` 写1—2段、180—320字；`evidence_gap` 只用1段、60—180字说明可靠边界。每章以领域专属判断为主，人生主线最多占30%；不得机械套用“好处—代价—建议”，也不得为了统一篇幅重复结论。
5. 当前问题回应在现有证据允许时写主要判断、成立条件、阶段变化和行动方向；只有一条阶段判断时不得为了达到完整篇幅重复扩写，也不把关注方向带入其他章节。
6. AI不填写判断编号、覆盖项、`paragraph_claim_map`、哈希或来源审计。任务包已经把相关判断按叙事关系分配到每个段落槽；AI按照每个槽位的 `narrative_role` 写成连续文章，相邻句必须构成因果、递进或转折，不能只把几条判断并排改写。
7. 每个槽位中的 `must_include_exact` 必须完整出现一次。完成语义补丁后，由程序自动生成正式初稿与全部来源映射：

```bash
python scripts/run_in_env.py internal/rensheng-youji-report-writer/scripts/compile_report_draft.py \
  --brief work/report-content-brief.json \
  --writing-pack work/report-writing-pack.json \
  --semantic-patch work/report-semantic-patch.json \
  --output work/report-draft.json
```
8. 用户可见正文一律使用第二人称“你”。禁止出现“这个人、他、她、命主、本人”等第三人称或内部称呼。
9. 主要确认项写成主要表现；可共存但未选项只用于刻画另一面；条件项必须写明阶段或情境；排除项不得出现。不得因用户选择一个答案就把所有章节写成同一种特点。
10. 正文保持纯文本。重点判断由程序根据事实提纲中的 `emphasis_claim_ids` 和正文真实出现位置生成；AI不手工填写样式坐标。
11. 生成 `schema_version=1.6.0` 的 `report-draft.json` 后运行：

```bash
python scripts/run_in_env.py internal/rensheng-youji-report-writer/scripts/validate_report_draft.py \
  work/report-draft.json --brief work/report-content-brief.json
```

写作层只负责组织人物材料，不负责数据库式来源登记或最后中文润色。不得用固定“好处—代价—建议”模板，不显示校准结果，不新增Core没有授权的行业、岗位、经历、关系状态或年份。

内部来源字段允许保留藏干、十神、透干等技术词；术语禁令只检查用户可见标题和正文，不能为了通过检查删除Core机制。
