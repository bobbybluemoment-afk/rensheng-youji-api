---
name: rensheng-youji-report-writer
description: 人生有迹内部人物写作层。接收已校验的report-content-brief.json，把Core支持的事实、形成链和领域联动组织成完整人生主线、六个现实领域与当前问题回应的中文初稿。用于完整报告成稿；不重新推命、不新增职业经历或家庭关系事实、不校准、不渲染PDF。
---

# 人物写作层

1. 完整读取 [portrait-writing.md](references/portrait-writing.md)。
2. 只使用事实提纲中的判断和允许例子。
3. 完整人生主线写2—3个自然段，共350—550个汉字。
4. 六个现实领域各写2—4个自然段，共380—650个汉字。
5. 当前问题回应写主要判断、成立条件、阶段变化和行动方向，不把关注方向带入其他章节。
6. 每个内容区记录使用的判断编号和覆盖项。
7. 生成 `report-draft.json` 后运行：

```bash
python internal/rensheng-youji-report-writer/scripts/validate_report_draft.py \
  work/report-draft.json --brief work/report-content-brief.json
```

写作层只负责组织人物材料，不负责最后中文润色。不得用固定“好处—代价—建议”模板，不显示校准结果。
