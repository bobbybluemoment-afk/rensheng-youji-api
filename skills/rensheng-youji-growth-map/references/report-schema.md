# 成长地图报告 JSON

将校准后的内容写成 UTF-8 JSON，再用 `scripts/render_report.py` 生成 Markdown。正文不展示 `audit` 中的命理术语。

```json
{
  "title": "人生有迹｜成长地图",
  "subtitle": "看见你带来的能力，理解一路形成的选择，也为下一步寻找新的可能",
  "generated_on": "2026-08-12",
  "brand": "人生有迹 by 景行",
  "profile": {
    "name": "",
    "identity_option": "女",
    "birth": "1991-10-07 21:56（出生地当地法定时间）",
    "location": "美国·宾夕法尼亚州雷丁",
    "focus": "事业发展",
    "question": "未来两年应该继续深耕专业还是转向管理"
  },
  "chart": {
    "pillars": ["辛未", "丁酉", "庚戌", "丁亥"],
    "luck_start": "1992-03-07 21:56:00",
    "da_yun": ["戊戌（1992—2001）", "己亥（2002—2011）"],
    "current_da_yun": "辛丑（2022—2031）",
    "time_basis": "出生地当地法定时间；未校正真太阳时",
    "uncertainty": "出生时间不接近时辰边界"
  },
  "calibration": {
    "summary": "四条中三条符合、一条部分符合；主要读法可采用。",
    "matched": 3,
    "partial": 1,
    "mismatched": 0,
    "birth_time_status": "稳定"
  },
  "panorama": {
    "life_line": "150—250字的人生主线。",
    "reality_findings": [
      "你更可能通过正规教育、资格或成熟组织建立最初的位置，但真正让你长期留下来的，是能否拥有清楚的专业判断权。",
      "你的学习或工作路径里有过一次明显转向，最后使用的能力与最初专业并不完全相同。"
    ],
    "current_tension": "当前最重要的矛盾。",
    "direct_answer": "对用户具体问题的直接回应。"
  },
  "life_thread": {
    "initial_role": "免费卡片中的初始角色扩写",
    "core_configuration": "与免费卡片一致的稳定能力和时柱落点",
    "main_task": "与免费卡片一致的人生主线任务",
    "portrait": "人物小传",
    "stage_path": {
      "previous_foundation": "上一阶段留下的能力、资源、关系与责任",
      "recent_development": "近三年如何逐步形成现在的问题",
      "present_task": "现在正在处理的现实问题",
      "next_direction": "未来两三年的延续与条件"
    }
  },
  "dimensions": [
    {
      "id": "self_growth",
      "title": "1｜性格与内在成长",
      "finding": "一句明确结论",
      "reality_findings": ["一至三条具体判断"],
      "analysis": ["两至四段白话分析"],
      "current_focus": "这一维度现在最值得处理的事情",
      "suggestions": ["一至三条现实建议"],
      "confidence": "高置信",
      "audit": {
        "chart_basis": ["内部盘面依据，可含术语"],
        "life_basis": ["用户事实或尚未验证"],
        "social_basis": ["年龄、城市、教育或社会环境推理"],
        "needs_validation": "仍需核对什么"
      }
    }
  ],
  "prosperity_guide": {
    "priority_actions": ["现在最值得做的三件事"],
    "reduce": "需要减少的一种消耗",
    "traditional_preferences": [
      {
        "area": "家居与工作区",
        "advice": "传统取向、现实作用和轻量尝试写在同一段。"
      }
    ]
  },
  "open_questions": ["真正影响结论、仍需核对的事项"],
  "consultation_note": "如果你正处于重要选择期，需要结合真实经历进一步缩小判断范围，可以联系景行进行一对一分析。",
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

## `dimensions` 固定顺序

1. `self_growth`：性格与内在成长
2. `love_partner`：恋爱与伴侣
3. `career`：事业发展
4. `finance_resources`：财务与资源
5. `body_emotion`：身体与情绪
6. `family_growth`：家庭与成长环境

每个维度都必须有 `finding`、`reality_findings`、`analysis`、`current_focus`、`suggestions`、`confidence` 和 `audit`。`audit` 供质量检查，默认不进入正文。

## 置信度

- `高置信`：完整盘面多处支持，至少一种其他八字方法交叉支持，并有现实经历验证。
- `中等置信`：盘面结构清楚，但现实验证有限或存在另一种合理映射。
- `待验证`：依赖单一线索、时柱不稳、现实回答失配或高风险领域。

## 隐私

本人报告可保留必要出生信息。公开案例必须另行获得授权并删除姓名、精确出生资料、城市、单位、联系方式和可识别事件。报告正文和结构化分析不承诺固定保存天数。
