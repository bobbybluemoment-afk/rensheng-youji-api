---
name: rensheng-youji-chinese-editor
description: 人生有迹内部中文编辑层。接收已校验的人物初稿和事实提纲，在不改变判断、年份、置信度和现实候选的前提下，改成自然、准确、符合中国人阅读习惯的完整中文段落，并生成可追溯的编辑记录。用于完整报告定稿；不重新推命、不新增事实、不排版或渲染PDF。
---

# 中文编辑层

1. 完整读取 [natural-chinese.md](references/natural-chinese.md)。
2. 对完整人生主线、六个现实领域和当前问题逐段执行第二遍编辑。
3. 补全主体和动作，拆分长句，消除名词堆叠、翻译腔、命理术语泄露和固定模板。
4. 保留初稿使用的所有判断编号、`paragraph_claim_map`、`claim_realization_map` 和领域独立性字段，不得增加新编号或改变逐段来源。`claim_realization_map.exact_span` 及其所在段落中的完整原句不得改写；如确需修改判断，退回Core而不是在编辑层偷换。
5. 用户可见文字全部使用第二人称“你”，删除“这个人、他、她、命主、本人”等第三人称或内部称呼。
6. 检查“经营”等高频抽象词的实际语境，并检查章节之间是否重复整句或固定模板。
7. 可润色或删除不适合突出显示的重点句，但不得增加数量或改变Core来源。保留的重点句必须是带句末标点的完整判断；不得只保留半句、连接语、例子或解释。编辑后让精确句子继续写入 `emphasis_spans`。
8. 输出终稿和独立编辑记录；编辑记录版本使用 `2.3.0`，并明确记录 `mandatory_claims_preserved=true`，不得只填写“已检查”。
9. 运行：

```bash
python internal/rensheng-youji-chinese-editor/scripts/validate_editorial_review.py \
  work/editorial-review.json --draft work/report-draft.json --report work/report.json
```

编辑后仍不通顺或必须补充新事实时，退回写作层或事实提纲层，不在编辑阶段自行补造。

术语检查只作用于用户可见标题与正文。内部机制、证据、来源映射必须保留真实技术词，不能清洗成空泛白话。
