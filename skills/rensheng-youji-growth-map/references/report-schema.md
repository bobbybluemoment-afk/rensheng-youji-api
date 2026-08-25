# 人生有迹报告 JSON v2.7.0

## 目录

1. 模式
2. 来源链路
3. 用户可见内容
4. 完整人生主线
5. 六个现实领域
6. 当前问题与阶段
7. 校准
8. 中文编辑
9. 逐年与行动
10. 固定检查

## 1. 模式

- 正式报告：`document_mode=full_calibrated`，必须完成五条现实校准、事实提纲、人物初稿和中文编辑，生成10页PDF。
- 未校准版：`document_mode=preliminary_uncalibrated`，只生成初步Markdown与新版卡片，不生成正式PDF。

正式报告使用 `schema_version=2.7.0`，Core使用 `core_version=0.5.0`。

## 2. 来源链路

报告保存以下来源标识：

- 校准后Core分析编号；
- 报告事实提纲编号；
- 人物初稿编号；
- 中文编辑记录编号；
- 最终报告编号。

同一内容区在初稿和终稿中必须保留相同判断来源。编辑只能改文字，不能增加或删除现实判断。

正式 `report.json` 使用以下顶层结构：

```json
{
  "schema_version": "2.7.0",
  "report_id": "唯一报告编号",
  "document_mode": "full_calibrated",
  "source": {
    "analysis_id": "与Core和卡片一致",
    "core_version": "0.5.0",
    "analysis_as_of": "YYYY-MM-DD",
    "calibration_status": "calibrated"
  },
  "source_artifacts": {
    "content_brief_id": "事实提纲编号",
    "report_draft_id": "人物初稿编号",
    "editorial_review_id": "编辑记录编号"
  },
  "title": "人生有迹｜完整报告",
  "subtitle": "看见你带来的能力，理解你走过的路，也寻找新的可能",
  "generated_on": "YYYY-MM-DD",
  "brand": "人生有迹 by 景行",
  "profile": {},
  "focus_scope": {
    "selected_focus": "与profile.focus一致",
    "protected_sections": ["life_overview", "dimensions"],
    "emphasis_sections": ["current_question_narrative", "stage_story.present_task", "stage_story.next_direction", "yearly_outlook", "action_guide.priority_actions"],
    "topic_keywords": ["当前问题中的具体对象"]
  },
  "cross_output_consistency": {"relationship_opportunity_years": []},
  "chart": {},
  "calibration": {"responses": []},
  "editorial_review": {"version": "2.0.0", "review_id": "与source_artifacts一致"},
  "executive_summary": {
    "life_overview": {"paragraphs": [], "source_claim_ids": [], "coverage": []},
    "capabilities_resources": []
  },
  "current_question_narrative": {"paragraphs": [], "source_claim_ids": []},
  "stage_story": {},
  "dimensions": [],
  "yearly_outlook": {},
  "action_guide": {},
  "open_questions": [],
  "assisted_service_note": "",
  "author": {},
  "boundaries": []
}
```

`profile`、`chart`、`calibration`、`stage_story`、`yearly_outlook`、`action_guide`、`author` 和 `boundaries` 延续2.6.0已经确认的字段；只有用户可见长文结构与编辑来源链发生变化。

## 3. 用户可见内容

正式报告包含：

- 基本信息与排盘口径；
- 完整人生主线；
- 能力与可用资源；
- 当前阶段与问题回应；
- 六个现实领域；
- 连续20年逐年观察；
- 行动建议、仍需验证、品牌与边界。

校准回答、候选编号、盘面证据、置信推理、事实提纲和编辑记录永远不进入用户正文。

## 4. 完整人生主线

`executive_summary.life_overview` 包含：

- `paragraphs`：2—3个自然段，总计350—550个汉字；
- `source_claim_ids`：至少6个有效判断来源；
- `coverage`：至少覆盖性格、形成、家庭教育、事业财富、关系和当前阶段。

完整人生主线先综述这个人，不围绕用户关注方向集中取材。不得用一句口号或“先扎根后显声”等生造表达代替。

`capabilities_resources` 保留2—4项最有证据的能力与资源，不重复完整人生主线。

## 5. 六个现实领域

固定顺序为：

1. `self_growth` 性格与内在成长；
2. `love_partner` 恋爱与伴侣；
3. `career` 事业发展；
4. `finance_resources` 财富与资源；
5. `body_emotion` 身体与情绪；
6. `family_growth` 家庭与成长环境。

每个领域包含：

- `paragraphs`：2—4个自然段，总计380—650个汉字；
- `source_claim_ids`：至少4个有效判断来源；
- `coverage`：在内部记录特征、行为、形成、挑战、当前变化与应对是否覆盖；
- `confidence`：高置信、中等置信或待验证；
- `audit`：来源、具体例子和证据缺口，只用于内部检查。

用户页面只显示领域标题和自然段，不显示“怎样形成、好处、代价、核对点、可以怎样调整”等固定小标题。

身体与情绪章节必须明确不构成疾病诊断。关系不推断性取向或当前关系状态。家庭不猜父母具体职业。

## 6. 当前问题与阶段

`current_question_narrative` 包含2—4个自然段、280—600个汉字，记录判断来源。内容需要：

- 直接回答用户当前问题；
- 说明主要判断成立的条件；
- 说明当前阶段如何形成；
- 说明未来两三年的变化；
- 给出符合用户行为方式的应对。

关注方向只在这一节、相关年度和行动建议中加重，不改变完整人生主线和六领域基础判断。

## 7. 校准

`calibration` 保留五题响应和内部候选更新，供交付程序核对。所有校准摘要、确认项、部分符合项、排除项和用户原始答案都不得渲染到Markdown或PDF。

## 8. 中文编辑

`editorial_review` 只保存 `review_id` 和 `version=2.0.0`；完整记录放在独立 `editorial-review.json`。

交付时必须同时传入初稿和编辑记录，程序逐区核对：

- 初稿和终稿哈希；
- 判断来源一致；
- 至少三个内容区发生实际编辑；
- 没有新增判断；
- 没有展示校准过程；
- 没有固定模板和禁用表达。

不得再使用几个布尔值自行声明“中文已检查”。

## 9. 逐年与行动

逐年观察仍为当前年前5年、当前年和未来14年，共20年。每年保留上一年带入、本年现实表现和下一年伏笔。普通年份不强行虚构事件，重点年份才增加岗位调整、合同、考试、搬家、见父母、回款等现实载体。

行动建议恰好三项，优先回答当前问题。不得把过去年份写成未来任务。

## 10. 固定检查

- 报告、卡片、Core、事实提纲和初稿来源一致；
- 完整人生主线350—550字，六领域各380—650字；
- 六个领域为自然段，不使用固定小标题；
- 具体组织、行业、岗位、收入和对象特征来自Core开放候选或用户事实；
- 不把候选库全部列进正文；
- 不出现“校准后的现实线索、校准确认、符合某判断”；
- 不出现日主、十神、身强身弱、透干、根苗花果等内部命理术语；
- 不出现组织化过劳型、先扎根后显声、表达窗口、能力输出、可见度、物质与经营底色、资源伴随期待等表达；
- 正文有明确主体、动作和现实对象；
- PDF恰好10页，第2页嵌入同一Core生成的新版1242×1660卡片；
- Logo、固定字体、微信二维码、GitHub、颜色和免责声明正常；
- 无缺字、乱码、溢出、截断或段落左边缘不一致。
