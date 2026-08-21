#!/usr/bin/env python3
"""人生有迹完整报告 JSON -> Markdown 确定性验收。"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent.parent
RENDERER = ROOT / "skills/rensheng-youji-growth-map/scripts/render_report.py"


def _dimension(identifier: str, title: str, core_sections: list[str]) -> dict:
    return {
        "id": identifier,
        "title": title,
        "finding": "这个领域的表现来自多项条件共同作用，需要结合现实经历确认。",
        "reality_findings": ["你可能已经形成一套稳定做法，同时也在承担这套做法带来的代价。"],
        "analysis": [
            "固定验收样例只用于检查结构。正式报告应说明这种方式怎样形成、在现实中怎样表现，以及什么条件改变后可能出现另一种结果。",
            "相关判断必须区分用户事实、命理推断、社会常见路径和仍待验证的候选。",
        ],
        "current_focus": "把当前最具体的选择拆成可以核对的现实条件。",
        "suggestions": ["记录正在权衡的两个选项及各自需要的时间、能力和支持。"],
        "confidence": "中等置信",
        "audit": {
            "core_sections": core_sections,
            "user_facts": [],
            "social_priors": [],
            "needs_validation": "需要真实经历继续确认。",
        },
    }


def _report() -> dict:
    dimensions = [
        _dimension("self_growth", "1｜性格与内在成长", ["complete_self_portrait", "reality_domains.growth"]),
        _dimension("love_partner", "2｜恋爱与伴侣", ["relationship_system", "partner_profiles"]),
        _dimension("career", "3｜事业发展", ["reality_domains.career", "resource_relationship"]),
        _dimension("finance_resources", "4｜财务与资源", ["reality_domains.wealth", "resource_relationship"]),
        _dimension("body_emotion", "5｜身体与情绪", ["reality_domains.health", "safety_boundaries"]),
        _dimension("family_growth", "6｜家庭与成长环境", ["family_system", "reality_domains.family"]),
    ]
    years = [
        {
            "year": year,
            "theme": "积累与调整",
            "carry_in": "上一年留下的能力和责任",
            "likely_expression": "可能继续处理工作、收入与关系之间的时间分配。",
            "seed_for_next": "留下更清楚的选择条件",
            "confidence": "中等置信",
        }
        for year in range(2021, 2041)
    ]
    return {
        "schema_version": "2.0.0",
        "source": {
            "analysis_id": "fixture-full-report-v2",
            "core_version": "0.2.0",
            "analysis_as_of": "2026-08-20",
            "calibration_status": "calibrated",
        },
        "title": "人生有迹｜完整报告",
        "subtitle": "看见你带来的能力，理解你走过的路，也寻找新的可能",
        "generated_on": "2026-08-20",
        "brand": "人生有迹 by 景行",
        "profile": {
            "name": "示例",
            "identity_option": "女",
            "birth": "1994-10-02 14:24（普通钟表时间）",
            "location": "湖北省武汉市",
            "focus": "事业发展",
            "question": "未来两年更适合继续积累还是承担新的责任",
        },
        "chart": {
            "pillars": ["甲戌", "癸酉", "丁卯", "丁未"],
            "luck_start": "1998-01-01 00:00:00",
            "current_luck_cycle": "示例大运（2024—2033）",
            "time_basis": "普通钟表时间输入，已进行真太阳时校正",
            "uncertainty": "不接近时辰边界",
        },
        "calibration": {
            "summary": "五条中三条符合、一条部分符合、一条不确定。",
            "birth_time_status": "稳定",
            "confirmed": ["工作中经常承担收尾责任"],
            "partial": ["学习路径有调整"],
            "rejected": [],
            "uncertain": ["家庭分工仍需确认"],
        },
        "executive_summary": {
            "life_theme": "你可能一直在学习怎样把能力、责任和自己的选择放在同一条线上。",
            "capabilities_resources": [
                "能够整理复杂信息并形成清楚判断。",
                "在规则明确的环境中容易积累可信度。",
                "愿意为长期结果持续投入。",
            ],
            "formation": "这些能力可能同时受到家庭期待、教育训练和现实选择的影响。",
            "current_situation": "事情越做越多，但需要判断新增责任是否真的带来成长和更多选择。",
            "direct_answer": "先比较两个方向能否带来明确职责、学习空间和可见成果，再决定是否承担新的责任。",
        },
        "stage_story": {
            "previous_foundation": "已经积累了处理复杂任务和与不同人沟通的经验。",
            "recent_development": "近几年责任增加，也更在意投入能否形成长期结果。",
            "present_task": "把能做的事情与真正值得长期投入的事情区分开。",
            "next_direction": "未来两三年更适合围绕清楚职责和可见成果逐步增加责任。",
            "long_range": "较长阶段的重点是让能力、职位、收入与生活安排逐渐形成稳定关系。",
        },
        "dimensions": dimensions,
        "yearly_outlook": {
            "start_year": 2021,
            "end_year": 2040,
            "summary": "这二十年更像一段持续积累、调整责任并逐步留下结果的过程。",
            "years": years,
        },
        "action_guide": {
            "priority_actions": [
                "明确下一阶段最希望增加的一项能力。",
                "比较不同选择能否带来职位、收入或作品。",
                "为工作、关系与休息分别保留固定时间。",
            ],
            "reduce": "减少在信息不足时同时准备过多方案。",
            "traditional_preferences": [
                {"area": "家居与工作区", "advice": "保持明亮、整洁，并为重要任务留出固定位置。"},
                {"area": "人情往来", "advice": "重要责任提前说清范围，减少模糊答应后再独自完成。"},
            ],
        },
        "open_questions": ["家庭对职业选择的实际影响仍需确认。"],
        "assisted_service_note": "本Skill可免费自行生成；如果你的AI无法运行Skill，或希望获得人工校准、PDF整理和问题解释，可以联系景行。",
        "author": {
            "name": "景行",
            "bio": "持续整理传统命理与现实经历之间可以核对的联系。",
            "github": "https://github.com/bobbybluemoment-afk/rensheng-youji-api",
            "web": "https://rensheng-youji-web.bobbybluemoment.workers.dev",
            "wechat_image": "https://raw.githubusercontent.com/bobbybluemoment-afk/rensheng-youji-api/main/assets/wechat-contact.jpg",
            "wechat_note": "添加时建议备注：人生有迹",
        },
        "boundaries": [
            "本报告用于传统文化体验与自我观察，不构成医疗、心理、法律、投资或其他专业意见。",
            "报告提供的是有条件、可验证的倾向，不代表唯一解释或必然命运。",
        ],
    }


class FullReportPipelineTest(unittest.TestCase):
    def test_report_json_to_markdown(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rensheng-youji-report-") as temp_dir:
            work = Path(temp_dir)
            source = work / "report.json"
            output = work / "report.md"
            source.write_text(json.dumps(_report(), ensure_ascii=False, indent=2), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(RENDERER), str(source), "--out", str(output)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            rendered = output.read_text(encoding="utf-8")
            self.assertIn("# 人生有迹｜完整报告", rendered)
            self.assertIn("## 能力与可用资源", rendered)
            self.assertIn("## 6｜家庭与成长环境", rendered)
            self.assertIn("| 2040 |", rendered)
            self.assertIn("本Skill可免费自行生成", rendered)
            self.assertNotIn("初始角色", rendered)
            self.assertNotIn("主线任务", rendered)


if __name__ == "__main__":
    unittest.main()
