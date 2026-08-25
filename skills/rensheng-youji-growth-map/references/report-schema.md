# 人生有迹报告 JSON v2.4.0

把已校验的 Core 母稿提取为 UTF-8 `report.json`。内部 `audit` 只用于核对来源，永远不进入正文。

## 模式

- 正式报告：`document_mode=full_calibrated`、`source.calibration_status=calibrated`、标题“人生有迹｜完整报告”。必须完成五条校准并通过时间边界预检，才能生成10页PDF。
- 未校准版：`document_mode=preliminary_uncalibrated`、`source.calibration_status=skipped`、标题“人生有迹｜初步分析”。只交付初步Markdown与新版卡片，不生成正式PDF。

## 顶层结构

```json
{
  "schema_version": "2.4.0",
  "document_mode": "full_calibrated",
  "source": {
    "analysis_id": "与Core一致",
    "core_version": "0.3.0",
    "analysis_as_of": "2026-08-20",
    "calibration_status": "calibrated"
  },
  "title": "人生有迹｜完整报告",
  "subtitle": "看见你带来的能力，理解你走过的路，也寻找新的可能",
  "generated_on": "2026-08-20",
  "brand": "人生有迹 by 景行",
  "profile": {
    "name": "",
    "identity_option": "女",
    "birth": "1991-10-07 21:56（出生地当地法定时间）",
    "location": "北京",
    "focus": "事业发展",
    "question": "未来两年更适合继续深耕专业还是尝试管理"
  },
  "focus_scope": {
    "selected_focus": "事业发展",
    "emphasis_sections": [
      "executive_summary.current_situation",
      "executive_summary.direct_answer",
      "stage_story.present_task",
      "stage_story.next_direction",
      "yearly_outlook",
      "action_guide.priority_actions"
    ],
    "excluded_sections": [
      "executive_summary.life_theme",
      "executive_summary.capabilities_resources",
      "executive_summary.formation",
      "stage_story.previous_foundation",
      "stage_story.long_range",
      "dimensions"
    ],
    "overview_domains": [
      "self_growth", "love_partner", "career", "finance_resources", "body_emotion", "family_growth"
    ],
    "topic_keywords": ["深耕专业", "尝试管理"]
  },
  "cross_output_consistency": {
    "relationship_opportunity_years": [2027, 2031]
  },
  "chart": {
    "pillars": ["辛未", "丁酉", "庚戌", "丁亥"],
    "luck_start": "1992-03-07 21:56:00",
    "current_luck_cycle": "辛丑（2022—2031）",
    "time_basis": "普通钟表时间输入，已进行真太阳时校正",
    "uncertainty": "出生时间不接近时辰边界",
    "formal_report_allowed": true
  },
  "calibration": {
    "summary": "五条中三条符合、一条部分符合、一条不确定。",
    "birth_time_status": "稳定",
    "responses": [
      {
        "question_number": 1,
        "domain": "事业与组织",
        "choice": "A",
        "selected_text": "先收集资料和比较风险，想清楚后再行动",
        "candidate_id": "c011",
        "user_note": "用户可选补充的具体事实或年份，没有则为空字符串"
      }
    ],
    "confirmed": ["已确认事实一", "已确认事实二", "已确认事实三"],
    "partial": ["部分符合内容"],
    "rejected": [],
    "uncertain": ["仍不确定内容"]
  },
  "executive_summary": {
    "life_theme": "35—120个汉字的人生主线。",
    "capabilities_resources": ["每项16—65个汉字，共2—3项"],
    "formation": "70—240个汉字，说明家庭、教育与现实条件怎样共同形成这些方式。",
    "current_situation": "25—110个汉字的当前具体矛盾。",
    "direct_answer": "35—150个汉字，直接回答用户问题。"
  },
  "stage_story": {
    "previous_foundation": "25—110个汉字",
    "recent_development": "25—110个汉字",
    "present_task": "25—110个汉字",
    "next_direction": "25—110个汉字",
    "long_range": "25—110个汉字"
  },
  "dimensions": [
    {
      "id": "self_growth",
      "title": "1｜性格与内在成长",
      "main_verdict": "22—90个汉字，只下一个最重要判断",
      "reality_anchor": "30—140个汉字，写现实机制与有证据的具体名词",
      "pattern_and_cost": "45—170个汉字，写行为顺序、重复情境与结果或代价",
      "verification_point": "18—85个汉字，只留一个能收窄结论的核对点",
      "confidence": "中等置信",
      "audit": {
        "core_sections": ["complete_self_portrait", "root_seed_flower_fruit_map"],
        "evidence_lenses": ["natal_structure", "root_seed_flower_fruit_map"],
        "verdict_sources": ["complete_self_portrait", "cross_method_analysis"],
        "reality_anchor_terms": ["任务清单", "交付复核"],
        "reality_anchor_sources": {
          "任务清单": ["complete_self_portrait.action_execution", "root_seed_flower_fruit_map"],
          "交付复核": ["complete_self_portrait.action_execution", "cross_method_analysis"]
        },
        "anchor_precision": "multi_method",
        "user_facts": [],
        "social_priors": [],
        "needs_validation": "仍需核对什么"
      }
    }
  ],
  "yearly_outlook": {
    "start_year": 2021,
    "end_year": 2040,
    "summary": "45—160个汉字",
    "years": [
      {
        "year": 2021,
        "theme": "4—14个汉字的现实主题",
        "carry_in": "10—50个汉字",
        "real_world_signal": "22—90个汉字，写现实载体，不统一使用‘可能表现’",
        "signal_terms": ["项目交付"],
        "key_year": false,
        "seed_for_next": "10—50个汉字",
        "confidence": "中等置信"
      }
    ]
  },
  "action_guide": {
    "priority_actions": ["每项18—75个汉字，恰好三项"],
    "reduce": "18—80个汉字",
    "traditional_preferences": [
      {"area": "家居与工作区", "advice": "18—80个汉字"}
    ]
  },
  "open_questions": ["真正会改变结论、仍需核对的2—5项"],
  "assisted_service_note": "本Skill可免费自行生成；如果你的AI无法运行Skill，或希望获得人工校准、PDF整理和问题解释，可以联系景行。",
  "author": {
    "name": "景行",
    "bio": "作者介绍",
    "github": "https://github.com/bobbybluemoment-afk/rensheng-youji-api",
    "web": "https://rensheng-youji-web.bobbybluemoment.workers.dev",
    "wechat_image": "assets/wechat-contact.jpg",
    "wechat_note": "添加时建议备注：人生有迹"
  },
  "boundaries": [
    "本报告用于传统文化体验与自我观察，不构成医疗、心理、法律、投资或其他专业意见。",
    "报告提供的是有条件、可验证的倾向，不代表唯一解释或必然命运。"
  ]
}
```

## 固定校验

- `focus_scope` 三组列表必须与示例完全一致，`selected_focus` 必须等于 `profile.focus`。`topic_keywords` 提取1—4个当前问题里的具体对象或选项，不能使用“事业、感情、发展、选择”等宽泛类别。每个关键词在受保护章节中最多出现两次。关注方向只决定第4页“当前阶段与问题回应”、相关年度提醒及行动优先级，不得改写完整人生主线、能力资源、形成过程、长期主线或六领域基础判断。
- `cross_output_consistency.relationship_opportunity_years` 必须与 `free-card-output.json.trend_panel.years` 中 `peach.highlight=true` 的年份完全一致。空列表表示卡片留白，报告也不得把某年写成明显关系进入或发展机会。
- `source.analysis_as_of` 必须等于 `generated_on`。当前问题回应、当前重点、未来方向和行动建议不得使用早于 `generated_on` 的年份；过去年份只允许放在上一阶段、近几年和逐年回顾中。
- 用户可见正文不得出现日主、十神、天干地支、身强身弱、透干等内部命理术语；只保留现实判断。百分比由PDF渲染器统一写成“百分之20”这类中文形式，并拒绝 `□` 或乱码替代字符。
- 第1页使用渲染器内置的固定产品介绍与 Logo，不读取 `life_theme`、`current_situation`、四柱或关注方向。第3页先呈现完整人生主线，再呈现能力、资源与形成过程。

- 六个领域固定顺序为 `self_growth`、`love_partner`、`career`、`finance_resources`、`body_emotion`、`family_growth`；每个领域可见正文125—360个汉字。
- 每个领域只保留一个 `main_verdict`，后续字段用于落地、解释和核对，不再列2—4组互相分散的候选。主判断最多使用一个“可能、倾向、容易、更像、适合”等条件词。
- `reality_anchor_terms` 必须含1—4个现实可核对名词，并原样出现在 `reality_anchor`。不能用“能力、技术、管理、资源、平台、岗位、组织、稳定、成长”等宽泛词单独充当现实落点。
- `anchor_precision=user_confirmed` 时必须有用户明确事实；`multi_method` 时每个名词至少有两个独立来源；`category_only` 时必须在核对点中明确目前不足以收窄到唯一行业、岗位、对象或经历。
- 事业名词先由工作机制推出，再写大型国企、事业单位、互联网大厂、成熟科技公司、项目管理、风控合规等组织或岗位指向；这些只是可用名词类型，不是固定候选词库。关系不得猜对象具体职业，家庭不得猜父母职业，身体情绪不得诊断疾病。
- 六个领域合计必须实际引用 `root_seed_flower_fruit_map` 与 `cross_method_analysis`；每个领域至少两个Core来源和两个独立证据视角。
- 正式报告可见正文3400—5600个汉字；逐年观察恰好连续20年。
- 年度主题使用现实语言，不直接写十神、大运或流年名词。
- 年度 `real_world_signal` 必须包含1—3个 `signal_terms`，用项目交付、岗位调整、考试证书、合同、搬家、见父母、回款等现实载体表示连续变化；普通年份不强行虚构事件，`key_year=true` 的重点年才增加细节。
- 内部候选编号、盘面支持、置信推理和替代解释不得进入用户可见正文。
- `render_report_pdf.py` 只接受正式校准报告，固定生成10页；第2页嵌入同一流程生成的新版1242×1660卡片。
