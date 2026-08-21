# 人生有迹报告 JSON v2.1

把已校验的 Core 母稿提取为 UTF-8 `report.json`。内部 `audit` 只用于核对来源，永远不进入正文。

## 模式

- 正式报告：`document_mode=full_calibrated`、`source.calibration_status=calibrated`、标题“人生有迹｜完整报告”。必须完成五条校准并通过时间边界预检，才能生成10页PDF。
- 未校准版：`document_mode=preliminary_uncalibrated`、`source.calibration_status=skipped`、标题“人生有迹｜初步分析”。只交付初步Markdown与新版卡片，不生成正式PDF。

## 顶层结构

```json
{
  "schema_version": "2.1.0",
  "document_mode": "full_calibrated",
  "source": {
    "analysis_id": "与Core一致",
    "core_version": "0.2.0",
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
    "confirmed": ["已确认事实一", "已确认事实二", "已确认事实三"],
    "partial": ["部分符合内容"],
    "rejected": [],
    "uncertain": ["仍不确定内容"]
  },
  "executive_summary": {
    "life_theme": "35—120个汉字的人生主线。",
    "capabilities_resources": ["每项16—65个汉字，共3—5项"],
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
      "finding": "20—95个汉字",
      "reality_findings": ["每项15—75个汉字，共1—3项"],
      "analysis": ["每段70—190个汉字，共2—3段"],
      "current_focus": "20—85个汉字",
      "suggestions": ["每项15—70个汉字，共1—3项"],
      "confidence": "中等置信",
      "audit": {
        "core_sections": ["complete_self_portrait", "root_seed_flower_fruit_map"],
        "evidence_lenses": ["natal_structure", "root_seed_flower_fruit_map"],
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
        "likely_expression": "22—80个汉字",
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

- 六个领域固定顺序为 `self_growth`、`love_partner`、`career`、`finance_resources`、`body_emotion`、`family_growth`；每个领域可见正文330—520个汉字。
- 六个领域合计必须实际引用 `root_seed_flower_fruit_map` 与 `cross_method_analysis`；每个领域至少两个Core来源和两个独立证据视角。
- 正式报告可见正文4500—6500个汉字；逐年观察恰好连续20年。
- 年度主题使用现实语言，不直接写十神、大运或流年名词。
- 内部候选编号、盘面支持、置信推理和替代解释不得进入用户可见正文。
- `render_report_pdf.py` 只接受正式校准报告，固定生成10页；第2页嵌入同一流程生成的新版1242×1660卡片。
