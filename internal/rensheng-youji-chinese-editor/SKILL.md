---
name: rensheng-youji-chinese-editor
description: 人生有迹内部中文编辑层。接收已校验的人物初稿和事实提纲，在不改变判断、年份、置信度和现实候选的前提下，改成自然、准确、符合中国人阅读习惯的完整中文段落，并生成可追溯的编辑记录。用于完整报告定稿；不重新推命、不新增事实、不排版或渲染PDF。
---

# 中文编辑层

1. 完整读取 [natural-chinese.md](references/natural-chinese.md)。
2. 先让确定性扫描器检查完整人生主线、六个现实领域、当前问题、能力摘要、阶段说明、20年逐年文字、行动建议和待观察问题：

```bash
python scripts/run_in_env.py internal/rensheng-youji-chinese-editor/scripts/scan_report_language.py \
  --draft work/report-draft.json \
  --semantic work/report-semantic-patch.json \
  --output work/editorial-scan.json
```

3. `status=pass` 时不调用编辑AI，直接进入确定性组装；`status=repair_required` 时，只把扫描器点名的段落交给AI，补全主体和动作，拆分长句，消除名词堆叠、翻译腔、命理术语泄露和固定模板。
4. 保留初稿使用的所有判断编号、`paragraph_claim_map`、`claim_realization_map`、领域独立性字段、`delivery_mode` 与 `missing_coverage`，不得增加新编号或改变逐段来源。`claim_realization_map.exact_span` 及其所在段落中的完整原句不得改写；如确需修改判断，退回Core而不是在编辑层偷换。
5. 用户可见文字全部使用第二人称“你”，删除“这个人、他、她、命主、本人”等第三人称或内部称呼。
6. 检查“经营”等高频抽象词的实际语境，并检查章节之间是否重复整句或固定模板。
7. 可润色或删除不适合突出显示的重点句，但不得增加数量或改变Core来源。保留的重点句必须是带句末标点的完整判断；不得只保留半句、连接语、例子或解释。编辑后让精确句子继续写入 `emphasis_spans`。
8. 使用程序应用可选修订补丁并生成终稿初稿与独立编辑记录；编辑记录版本使用 `2.5.0`。不再要求至少修改几个章节：没有问题时零处修改就是正确结果。

```bash
python scripts/run_in_env.py internal/rensheng-youji-chinese-editor/scripts/apply_editorial_patch.py \
  --draft work/report-draft.json \
  --semantic work/report-semantic-patch.json \
  --scan work/editorial-scan.json \
  --patch work/editorial-repair-patch.json \
  --output work/edited-report-draft.json \
  --semantic-output work/edited-report-semantic.json \
  --review work/editorial-review.json
```

扫描通过时省略 `--patch`，程序仍会原样生成 `edited-report-semantic.json`。最终报告只读取这份已经扫描或局部修订的语义文件，不得回头读取未编辑的 `report-semantic-patch.json`。最终报告由 `compile_final_report.py` 确定性组装后，再运行：

```bash
python scripts/run_in_env.py internal/rensheng-youji-chinese-editor/scripts/validate_editorial_review.py \
  work/editorial-review.json --draft work/report-draft.json --report work/report.json
```

编辑后仍不通顺或必须补充新事实时，退回写作层或事实提纲层，不在编辑阶段自行补造。

术语检查只作用于用户可见标题与正文。内部机制、证据、来源映射必须保留真实技术词，不能清洗成空泛白话。
