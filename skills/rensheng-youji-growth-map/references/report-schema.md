# 人生有迹完整报告 JSON

把已校验的 Core 母稿提取为 UTF-8 `report.json`，再运行 `scripts/render_report.py`。`audit` 只用于核对来源，默认不进入正文。

```json
{
  "schema_version": "2.0.0",
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
    "uncertainty": "出生时间不接近时辰边界"
  },
  "calibration": {
    "summary": "五条中三条符合、一条部分符合、一条不确定。",
    "birth_time_status": "稳定",
    "confirmed": ["已确认事实"],
    "partial": ["部分符合内容"],
    "rejected": [],
    "uncertain": ["仍不确定内容"]
  },
  "executive_summary": {
    "life_theme": "完整人生主线。",
    "capabilities_resources": ["能力或资源一", "能力或资源二", "能力或资源三"],
    "formation": "家庭、教育与社会环境怎样共同形成这些方式。",
    "current_situation": "当前阶段最需要处理的具体矛盾。",
    "direct_answer": "对用户问题的直接回应。"
  },
  "stage_story": {
    "previous_foundation": "上一阶段留下的能力、关系、责任和资源。",
    "recent_development": "近几年怎样逐步形成现在的问题。",
    "present_task": "当前年正在处理什么。",
    "next_direction": "未来两三年的延续、条件与风险。",
    "long_range": "更长大运阶段的主线概括。"
  },
  "dimensions": [
    {
      "id": "self_growth",
      "title": "1｜性格与内在成长",
      "finding": "一句明确结论",
      "reality_findings": ["一至三条具体表现"],
      "analysis": ["两至四段白话分析"],
      "current_focus": "现在最值得处理的事情",
      "suggestions": ["一至三条现实建议"],
      "confidence": "中等置信",
      "audit": {
        "core_sections": ["complete_self_portrait", "reality_domains.growth"],
        "user_facts": [],
        "social_priors": [],
        "needs_validation": "仍需核对什么"
      }
    }
  ],
  "yearly_outlook": {
    "start_year": 2021,
    "end_year": 2040,
    "summary": "二十年连续过程的总体说明。",
    "years": [
      {
        "year": 2021,
        "theme": "年度主题",
        "carry_in": "从上一年带入什么",
        "likely_expression": "现实中可能怎样表现",
        "seed_for_next": "给下一年留下什么",
        "confidence": "中等置信"
      }
    ]
  },
  "action_guide": {
    "priority_actions": ["行动一", "行动二", "行动三"],
    "reduce": "需要减少的一种消耗",
    "traditional_preferences": [
      {"area": "家居与工作区", "advice": "传统取向、现实作用和轻量尝试。"}
    ]
  },
  "open_questions": ["真正影响结论、仍需核对的事项"],
  "assisted_service_note": "本Skill可免费自行生成；如果你的AI无法运行Skill，或希望获得人工校准、PDF整理和问题解释，可以联系景行。",
  "author": {
    "name": "景行",
    "bio": "作者介绍",
    "github": "https://github.com/bobbybluemoment-afk/rensheng-youji-api",
    "web": "https://rensheng-youji-web.bobbybluemoment.workers.dev",
    "wechat_image": "https://raw.githubusercontent.com/bobbybluemoment-afk/rensheng-youji-api/main/assets/wechat-contact.jpg",
    "wechat_note": "添加时建议备注：人生有迹"
  },
  "boundaries": [
    "本报告用于传统文化体验与自我观察，不构成医疗、心理、法律、投资或其他专业意见。",
    "报告提供的是有条件、可验证的倾向，不代表唯一解释或必然命运。"
  ]
}
```

## 固定校验

- `schema_version` 必须为 `2.0.0`；
- `source.analysis_id/core_version/analysis_as_of` 必须与实际 Core 母稿一致；
- `source.calibration_status` 只能是 `calibrated` 或 `skipped`；
- `dimensions` 固定顺序为 `self_growth`、`love_partner`、`career`、`finance_resources`、`body_emotion`、`family_growth`；
- `confidence` 只能是“高置信／中等置信／待验证”；
- `yearly_outlook.years` 必须按年份连续，并与起止年份一致；
- `action_guide.priority_actions` 恰好三条，`traditional_preferences` 为2—5条；
- 不再出现 `initial_role`、`core_configuration`、`main_task`、`portrait` 等旧字段。
