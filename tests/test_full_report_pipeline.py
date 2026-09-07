#!/usr/bin/env python3
"""校准题 -> 新版卡片 -> Markdown -> 固定10页PDF 确定性验收。"""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

from PIL import Image


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))
from test_free_card_v2_pipeline import _card_content, _visual_signals  # noqa: E402

REPORT_RENDERER = ROOT / "skills/rensheng-youji-growth-map/scripts/render_report.py"
CALIBRATION_VALIDATOR = ROOT / "skills/rensheng-youji-growth-map/scripts/validate_calibration_questions.py"
CALIBRATION_BUILDER = ROOT / "skills/rensheng-youji-growth-map/scripts/build_calibration_questions.py"
DELIVERY_GENERATOR = ROOT / "skills/rensheng-youji-growth-map/scripts/generate_full_report.py"
PREFLIGHT = ROOT / "skills/rensheng-youji-growth-map/scripts/preflight_report.py"
sys.path.insert(0, str(ROOT / "skills/rensheng-youji-growth-map/scripts"))
from render_report_pdf import normalize_display_text  # noqa: E402
from build_calibration_questions import build as build_calibration_questions  # noqa: E402


def _repeat(seed: str, target: int) -> str:
    value = ""
    count = 0
    while count < target:
        for char in seed:
            value += char
            if re.match(r"[\u3400-\u9fff]", char):
                count += 1
            if count >= target:
                return value + "。"
    return value


def _dimension(identifier: str, title: str, extra_source: str) -> dict:
    content = {
        "self_growth": (
            "你做事重视把情况弄清楚，也愿意为结果负责。面对重要选择时，你通常先确认风险、时间和可用条件，再决定是否投入，不喜欢在毫无准备时仓促行动。",
            {
                "behavior_and_decision": "接到陌生任务后，你会先补齐资料，列出任务清单，再按轻重缓急推进。交付复核是你很重视的一步，所以复杂事情交到你手里通常不容易漏项。",
                "formation_and_experience": "这种谨慎可能来自较早形成的责任感。家庭或教育经历让你习惯先满足明确要求，再考虑自己的偏好；长期得到的肯定也多半与可靠、守时和少出错有关。",
                "recurring_challenge_and_change": "当任务边界含糊或别人不断追加要求时，你容易先把事情做完，事后才表达不满。久而久之，周围人会默认你负责收尾，你也会开始怀疑自己的投入是否值得。",
                "response": "接下来需要练习的不是降低责任感，而是在开始前说清目标、权限和完成标准。遇到陌生机会，可以先做一个小范围版本，用真实反馈代替长时间准备。",
            },
            ["任务清单", "交付复核"],
        ),
        "love_partner": (
            "你对关系的判断比较实际。真正让你投入的，不只是短期热情，而是对方能否稳定回应、认真安排见面，并愿意讨论两个人今后的生活选择。",
            {
                "attraction_and_needs": "你容易被做事利落、说到做到、对未来有安排的人吸引。外表和情绪张力会带来最初好感，但能否守约、尊重你的决定，才会影响你是否继续投入。",
                "interaction_and_experience": "关系建立以后，你会通过见面频率、回复节奏和共同计划判断对方是否认真。你不一定经常表达依赖，却会主动处理城市选择和金钱安排等现实问题。",
                "conflict_and_change": "如果对方习惯替你决定，或长期回避未来安排，你最初可能先观察和忍耐，等失望积累后才明显退开。工作压力较大时，这种延迟表达会让误会持续更久。",
                "response": "更合适的做法是在关系仍然平稳时说明需要，而不是等到无法忍受再结束讨论。涉及见父母、城市和共同支出时，先确认双方真实意愿，再决定推进速度。",
            },
            ["见面频率", "城市选择", "金钱安排"],
        ),
        "career": (
            "你的职业优势是整理复杂信息、识别关键风险，并把分散任务推进到完整交付。相比只靠人情协调，你更容易凭专业判断、执行质量和长期信誉获得位置。",
            {
                "ability_and_formation": "学习和工作经历容易把你训练成先理解规则、再处理细节的人。你适合研究分析、方案设计和项目交付，也能够在反复复核中发现别人容易忽略的问题。",
                "organization_role_environment": "更适合制度和分工成熟的单位，例如大型国企或成熟科技公司。产品运营、项目管理、风险控制等岗位能让专业积累被看见，也有较清楚的晋升标准。",
                "recurring_problem_and_change": "真正的问题不是能力不足，而是容易接下职责不清的收尾工作。成果归属没有提前说清时，你可能做了大量协调，却没有同步获得职位、收入或决策权限。",
                "response": "下一阶段应争取完整负责一个能说明结果的项目，并在开始前确认权限、评价标准和成果归属。若考虑创业，先用副项目验证获客和交付，不宜马上放弃已有积累。",
            },
            ["大型国企", "成熟科技公司", "项目交付"],
        ),
        "finance_resources": (
            "你的财富增长更依赖长期职业积累，而不是依靠一次高风险机会。你会先保证日常现金流和必要支出，再考虑收益上限，对没有清楚规则的项目通常比较谨慎。",
            {
                "resource_start_and_attitude": "家庭或早期环境可能让你较早重视稳定和责任，因此花钱前会考虑后续安排。你并非不愿承担风险，而是希望先知道最坏结果是否会影响正常生活。",
                "income_and_accumulation": "收入主轴更适合放在固定工资、年度绩效和项目奖金。职位提升与专业定价能够逐步提高上限，咨询或内容收入可以作为第二来源，但需要先形成重复需求。",
                "leakage_and_change": "比冲动消费更需要留意的是人情垫付和口头分成。只要分工、报价和结算日期没有写清，你就可能先投入时间，最后回款慢于交付，甚至只留下人情。",
                "response": "积累财富时应先保留稳定储蓄，再给新机会设置明确预算。额外合作至少确认工作范围、交付节点和付款日期，不把尚未到账的收入提前计入日常安排。",
            },
            ["固定工资", "年度绩效", "项目奖金"],
        ),
        "body_emotion": (
            "你的压力往往不是当场爆发，而是先维持正常工作，等到独处或准备休息时才明显感到疲惫。未完成的事情越多，脑中越容易继续复盘和安排。",
            {
                "trigger_and_signal": "并行任务过多、责任边界不清时，最先出现的通常是睡前反复想工作、颈肩紧张和三餐推迟。白天仍能处理事情，不代表身体没有持续消耗。",
                "coping_and_cycle": "你习惯先把问题排清楚，再允许自己休息。短时间独处、减少信息输入和恢复固定睡眠，比继续刷手机或安排更多娱乐更容易让状态真正缓下来。",
                "impact_and_change": "如果长期依靠意志维持，工作效率可能仍然稳定，但耐心和表达会先受影响。你会减少与人沟通，或者对小问题变得敏感，之后才发现自己已经很累。",
                "response": "需要把恢复时间当作固定安排，而不是等事情全部结束后再休息。上述内容只用于观察压力节奏，不构成疾病诊断；持续不适应以正规医疗评估为准。",
            },
            ["睡前反复想工作", "颈肩紧张", "三餐推迟"],
        ),
        "family_growth": (
            "你在家庭中较容易成为处理实际问题的人。家里的支持和要求往往同时存在：关键时候愿意提供条件，也希望你做事可靠、选择稳妥，并承担相应责任。",
            {
                "climate_and_resources": "家庭影响更容易通过学费证书、住房安排和工作信息体现。家人可能在重要节点提供费用或建议，同时也会关心选择是否稳定、能否形成长期结果。",
                "role_and_boundary": "遇到长辈照护或家庭分工时，你往往先处理联系、付款或收尾，再讨论自己的时间。久而久之，家人容易默认你会负责，个人安排便被不断往后放。",
                "repeated_issue_and_change": "真正容易产生矛盾的不是是否愿意帮忙，而是谁负责、需要投入多少以及何时结束没有提前说清。责任长期模糊时，你会一边承担，一边积累不满。",
                "response": "处理家庭事务时，可以把任务拆成出钱、联系、执行和决定四部分，明确每个人负责什么。建立边界不是减少往来，而是让支持与责任保持相对平衡。",
            },
            ["学费证书", "住房安排", "长辈照护"],
        ),
    }[identifier]
    overview, paragraphs, anchor_terms = content
    return {
        "id": identifier,
        "title": title,
        "overview": overview,
        "paragraphs": paragraphs,
        "confidence": "中等置信",
        "audit": {
            "core_sections": [extra_source, "root_seed_flower_fruit_map", "cross_method_analysis"],
            "evidence_lenses": ["root_seed_flower_fruit_map", "cross_method_analysis"],
            "verdict_sources": [extra_source, "cross_method_analysis"],
            "reality_anchor_terms": anchor_terms,
            "reality_anchor_sources": {term: [extra_source, "root_seed_flower_fruit_map"] for term in anchor_terms},
            "anchor_precision": "multi_method",
            "user_facts": [],
            "social_priors": [],
            "needs_validation": "需要真实经历继续确认。",
        },
    }


def _report() -> dict:
    dimensions = [
        _dimension("self_growth", "1｜性格与内在成长", "complete_self_portrait"),
        _dimension("love_partner", "2｜恋爱与伴侣", "relationship_system"),
        _dimension("career", "3｜事业发展", "reality_domains.career"),
        _dimension("finance_resources", "4｜财务与资源", "reality_domains.wealth"),
        _dimension("body_emotion", "5｜身体与情绪", "reality_domains.health"),
        _dimension("family_growth", "6｜家庭与成长环境", "family_system"),
    ]
    years = [
        {
            "year": year,
            "theme": "积累形成清楚结果",
            "carry_in": _repeat("上一年留下的能力、责任和待处理选择继续影响现在。", 25),
            "real_world_signal": _repeat("这一年的变化主要落在项目交付：责任是否写进职责、成果是否能换来职位或收入，会比口头评价更重要。", 48),
            "signal_terms": ["项目交付"],
            "key_year": year in {2026, 2030, 2034, 2038},
            "seed_for_next": _repeat("留下更清楚的选择条件和可以继续使用的经验。", 24),
            "confidence": "中等置信",
        }
        for year in range(2021, 2041)
    ]
    calibration_questions = _calibration_questions()["questions"]
    response_choices = ["A", "A", "A", "A", "D"]
    responses = []
    for question, choice in zip(calibration_questions, response_choices):
        display, audit = question["display"], question["audit"]
        choice_text = {item["key"]: item["text"] for item in display["choices"]}[choice]
        responses.append({
            "question_number": display["number"],
            "template_id": audit["template_id"],
            "domain": display["domain"],
            "choice": choice,
            "selected_text": choice_text,
            "selected_value": choice.lower(),
            "candidate_updates": [] if choice == "D" else audit["candidate_effects"][choice],
            "user_note": "",
        })
    return {
        "schema_version": "2.6.0",
        "document_mode": "full_calibrated",
        "source": {"analysis_id": "fixture-v2-pipeline", "core_version": "0.4.0", "analysis_as_of": "2026-08-20", "calibration_status": "calibrated"},
        "title": "人生有迹｜完整报告",
        "subtitle": "看见你带来的能力，理解你走过的路，也寻找新的可能",
        "generated_on": "2026-08-20",
        "brand": "人生有迹 by 景行",
        "profile": {"name": "示例", "identity_option": "女", "birth": "1994-10-02 14:24（普通钟表时间）", "location": "湖北省武汉市", "focus": "事业发展", "question": "未来两年更适合继续积累还是承担新的责任"},
        "focus_scope": {
            "selected_focus": "事业发展",
            "emphasis_sections": ["executive_summary.current_situation", "executive_summary.direct_answer", "stage_story.present_task", "stage_story.next_direction", "yearly_outlook", "action_guide.priority_actions"],
            "excluded_sections": ["executive_summary.life_theme", "executive_summary.capabilities_resources", "executive_summary.formation", "stage_story.previous_foundation", "stage_story.long_range", "dimensions"],
            "overview_domains": ["self_growth", "love_partner", "career", "finance_resources", "body_emotion", "family_growth"],
            "topic_keywords": ["承担新责任"],
        },
        "cross_output_consistency": {"relationship_opportunity_years": [2026, 2032, 2037]},
        "chart": {"pillars": ["甲戌", "癸酉", "丁卯", "丁未"], "luck_start": "1998-01-01 00:00:00", "current_luck_cycle": "阶段示例（2024—2033）", "time_basis": "普通钟表时间输入，已进行真太阳时校正", "uncertainty": "不接近时辰边界", "formal_report_allowed": True},
        "calibration": {
            "question_schema_version": "3.0.0",
            "template_version": "2.0.0",
            "summary": "五题均已作答，其中四题形成较清楚的现实路径，一题仍不确定。",
            "birth_time_status": "稳定",
            "responses": responses,
            "confirmed": ["工作中经常承担收尾责任", "重要选择通常会比较长期结果", "近年更在意投入是否值得"],
            "partial": ["学习路径曾经出现调整"],
            "rejected": [],
            "uncertain": ["家庭分工仍需确认"],
        },
        "editorial_review": {
            "version": "1.0.0",
            "fact_preservation_checked": True,
            "calibration_paraphrased": True,
            "natural_chinese_checked": True,
            "template_repetition_checked": True,
        },
        "executive_summary": {
            "life_theme": _repeat("你可能一直在学习怎样把能力、责任和自己的选择放在同一条线上，并让长期投入形成看得见的结果。", 65),
            "capabilities_resources": [_repeat("能够整理复杂信息，并把模糊任务变成可以执行的步骤。", 28), _repeat("在规则清楚的环境中容易积累可信度，也能持续完成长期任务。", 30), _repeat("遇到变化时会先核对条件，再决定是否增加责任和投入。", 28)],
            "formation": _repeat("这些能力可能同时受到家庭期待、教育训练和现实选择影响。较早形成的责任感帮助你适应规则，也可能让你习惯先完成别人需要的事。后来的工作经验逐步让你看见，可靠之外还需要明确自己的方向。", 120),
            "current_situation": _repeat("事情越做越多，但需要判断新增责任是否真的带来成长、收入或更多选择。", 48),
            "direct_answer": _repeat("先比较两个方向能否带来明确职责、学习空间和可见成果，再决定是否承担新的责任；如果只有任务增加而支持条件不变，更适合先谈清范围。", 85),
        },
        "stage_story": {
            "previous_foundation": _repeat("已经积累处理复杂任务、核对细节和与不同人沟通的经验。", 38),
            "recent_development": _repeat("近几年责任增加，也更在意投入能否形成职位、收入或长期作品。", 40),
            "present_task": _repeat("把能够完成的事情与真正值得长期投入的事情明确区分开。", 36),
            "next_direction": _repeat("未来两三年更适合围绕清楚职责和可见成果逐步增加责任，同时保留调整空间。", 48),
            "long_range": _repeat("较长阶段的重点是让能力、职位、收入与生活安排逐渐形成稳定关系。", 42),
        },
        "dimensions": dimensions,
        "yearly_outlook": {"start_year": 2021, "end_year": 2040, "summary": _repeat("这二十年更像一段持续积累、调整责任并逐步留下结果的过程。年份之间存在前后联系，变化主要来自已经形成的能力、关系与现实选择，不宜单独判断某年一定好或坏。", 95), "years": years},
        "action_guide": {
            "priority_actions": [_repeat("明确下一阶段最希望增加的一项能力，以及它能形成什么现实结果。", 38), "将每月可支配收入的20％—30％先转入独立储蓄账户，再安排可以承受损失的尝试预算。", _repeat("为工作、关系与休息分别保留固定时间，每月核对一次真实投入。", 38)],
            "reduce": _repeat("减少在信息不足时同时准备过多方案，先验证最关键的一个条件。", 38),
            "traditional_preferences": [{"area": "家居与工作区", "advice": _repeat("保持明亮整洁，并为重要任务留出固定位置和连续时间。", 32)}, {"area": "人情往来", "advice": _repeat("重要责任提前说清范围，减少模糊答应后再独自完成。", 32)}],
        },
        "open_questions": ["家庭对职业选择的实际影响仍需确认。", "当前两个工作选项的收入和职责差异仍需补充。"],
        "assisted_service_note": "本Skill可免费自行生成；如果你的AI无法运行Skill，或希望获得人工校准、PDF整理和问题解释，可以联系景行。",
        "author": {"name": "景行", "bio": "持续整理传统命理与现实经历之间可以核对的联系。", "github": "https://github.com/bobbybluemoment-afk/rensheng-youji-api", "web": "https://rensheng-youji-web.bobbybluemoment.workers.dev", "wechat_image": "assets/wechat-contact.jpg", "wechat_note": "添加时建议备注：人生有迹"},
        "boundaries": ["本报告用于传统文化体验与自我观察，不构成医疗、心理、法律、投资或其他专业意见。", "报告提供的是有条件、可验证的倾向，不代表唯一解释或必然命运。"],
    }


def _calibration_questions() -> dict:
    return build_calibration_questions(_calibration_analysis(), "事业发展")


def _calibration_analysis() -> dict:
    candidates = []
    specs = [
        ("c1", "career", "stable_pattern", "原局长期", ["complete_self_portrait.cognition_and_decision"]),
        ("c2", "family_growth", "objective_state", "近几年", ["family_system.role_position"]),
        ("c3", "love_partner", "stable_pattern", "长期重复", ["partner_profiles.attraction"]),
        ("c4", "finance_resources", "objective_state", "过去一年", ["reality_domains.wealth"]),
        ("c5", "body_emotion", "timed_event", "过去五年", ["annual_theme_activation"]),
    ]
    claims = []
    for index, (candidate_id, domain, kind, time_scope, targets) in enumerate(specs, 1):
        claim_id = f"claim_{candidate_id}"
        claims.append({"claim_id": claim_id, "claim_class": "calibration_pending" if index <= 2 else "conditional_judgment"})
        candidates.append({
            "candidate_id": candidate_id, "domain": domain, "candidate_kind": kind,
            "reality_dimension": f"axis_{index}", "label": f"现实核对点{index}",
            "time_scope": time_scope, "calibration_targets": targets,
            "statement": f"第{index}种具体表现更接近我的实际经历。",
            "observable_examples": ["现实中有明确行为可以核对", "能够说明候选是否符合"],
            "alternative_statement": f"第{index}种表现并不常见，我更接近相反做法。",
            "source_layers": ["annual", "annual_theme_activation"] if kind == "timed_event" else ["chart", "cross_method"],
            "related_claim_ids": [claim_id],
            "confidence": "to_verify", "validation_question": f"关于第{index}个现实侧面，哪一种描述更接近你？", "status": "unverified",
        })
    return {"analysis_meta": {"analysis_id": "fixture-calibration-v3", "core_version": "0.15.0"}, "reality_candidate_pool": candidates, "report_claim_ledger": claims}


def _calibration_plan() -> dict:
    template_candidates = [
        ("career.unclear_task_response", "c1"),
        ("family.primary_role", "c2"),
        ("relationship.first_attraction_signal", "c3"),
        ("finance.primary_income_source", "c4"),
        ("mobility.recent_move_reason", "c5"),
    ]
    questions = []
    for template_id, candidate_id in template_candidates:
        questions.append({
            "template_id": template_id,
            "candidate_effects": {
                "A": [{"candidate_id": candidate_id, "status": "match"}],
                "B": [{"candidate_id": candidate_id, "status": "partial"}],
                "C": [{"candidate_id": candidate_id, "status": "reject"}],
            },
            "evidence_lenses": ["root_seed_flower_fruit_map", "resource_relationship"],
            "core_sections": ["reality_candidate_pool", "reality_domains"],
            "alternatives": ["现实环境也可能形成相似经历"],
            "birth_time_dependency": "partial",
            "confidence": "medium",
        })
    return {"schema_version": "1.0.0", "questions": questions}


def _write_calibration_files(work: Path) -> tuple[Path, Path, Path]:
    analysis, plan, questions = work / "analysis-initial.json", work / "unused-calibration-plan.json", work / "calibration-questions.json"
    analysis.write_text(json.dumps(_calibration_analysis(), ensure_ascii=False, indent=2), encoding="utf-8")
    plan.write_text(json.dumps(_calibration_plan(), ensure_ascii=False, indent=2), encoding="utf-8")
    questions.write_text(json.dumps(_calibration_questions(), ensure_ascii=False, indent=2), encoding="utf-8")
    return analysis, plan, questions


def _run(*args: str, expected: int = 0) -> subprocess.CompletedProcess[str]:
    result = subprocess.run([sys.executable, *args], cwd=ROOT, text=True, capture_output=True, check=False)
    if result.returncode != expected:
        raise AssertionError(f"命令返回{result.returncode}：{' '.join(args)}\n{result.stdout}\n{result.stderr}")
    return result


def _assemble_free_card(work: Path) -> Path:
    signals = work / "visual-signals.json"
    series = work / "visual-series.json"
    analysis = work / "analysis-output.json"
    content = work / "card-content.json"
    output = work / "free-card-output.json"
    signals.write_text(json.dumps(_visual_signals(), ensure_ascii=False), encoding="utf-8")
    analysis.write_text(json.dumps({"analysis_meta": {"status": "complete", "analysis_id": "fixture-v2-pipeline", "core_version": "0.4.0", "analysis_as_of": "2026-08-20"}}, ensure_ascii=False), encoding="utf-8")
    content.write_text(json.dumps(_card_content(), ensure_ascii=False), encoding="utf-8")
    _run("internal/rensheng-youji-free-card-output/scripts/build_visual_series.py", str(signals), "--output", str(series))
    _run("scripts/assemble_free_card.py", "--analysis", str(analysis), "--content", str(content), "--series", str(series), "--output", str(output))
    return output


class FullReportPipelineTest(unittest.TestCase):
    def test_skill_keeps_reality_details_optional(self) -> None:
        skill_text = (ROOT / "skills/rensheng-youji-growth-map/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("两轮收集输入", skill_text)
        self.assertIn("学历、专业、当前职业或学习状态；每项都非必答", skill_text)
        self.assertIn("当前关系状态、反复出现的相处情况；每项都非必答", skill_text)
        self.assertIn("相关家庭关系、正在发生的矛盾或责任；每项都非必答", skill_text)
        self.assertIn("用户可以只回复五个字母，忽略全部可选补充", skill_text)
        self.assertIn("不得再次追问、降低交付规格", skill_text)
        self.assertNotIn("不知道时明确写“不知道”", skill_text)

    def test_current_report_rejects_legacy_calibration_schema(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rensheng-youji-calibration-version-") as temp_dir:
            source = Path(temp_dir) / "report.json"
            report = _report()
            report["calibration"]["question_schema_version"] = "1.0.0"
            source.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(REPORT_RENDERER), str(source), "--out", str(Path(temp_dir) / "report.md")],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("受支持的确定性校准链路", result.stdout)

    def test_boundary_preflight_blocks_formal_report(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rensheng-youji-preflight-") as temp_dir:
            source = Path(temp_dir) / "core-input.json"
            source.write_text(json.dumps({
                "solar_terms_and_boundaries": {"boundary_flags": ["hour_branch_boundary"]},
                "person": {"birth": {"time_precision": "minute"}},
                "reality_context": {"education": "本科", "occupation": "产品经理", "current_role": "在职", "current_concerns": ["是否换工作"]},
            }, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run([sys.executable, str(PREFLIGHT), str(source), "--focus", "事业发展"], cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 3)
            self.assertIn('"formal_report_allowed": false', result.stdout)

    def test_calibration_visible_output_hides_internal_evidence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rensheng-youji-calibration-") as temp_dir:
            work = Path(temp_dir)
            analysis, _, source = _write_calibration_files(work)
            visible = work / "visible.md"
            _run(str(CALIBRATION_VALIDATOR), str(source), "--analysis", str(analysis), "--visible-out", str(visible))
            text = visible.read_text(encoding="utf-8")
            self.assertNotIn("c01", text)
            self.assertNotIn("盘面", text)
            self.assertNotIn("root_seed", text)
            self.assertIn("A. 第1种具体表现更接近我的实际经历。", text)
            self.assertIn("D. 自己描述", text)

    def test_calibration_builder_is_deterministic_and_personal(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rensheng-youji-calibration-builder-") as temp_dir:
            work = Path(temp_dir)
            analysis, _, _ = _write_calibration_files(work)
            output = work / "built-questions.json"
            _run(str(CALIBRATION_BUILDER), "--analysis", str(analysis), "--focus", "事业发展", "--output", str(output))
            data = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(data["schema_version"], "3.0.0")
            self.assertEqual(data["template_version"], "2.0.0")
            self.assertEqual(len(data["questions"]), 5)

    def test_visible_evidence_leak_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rensheng-youji-calibration-bad-") as temp_dir:
            work = Path(temp_dir)
            analysis, _, source = _write_calibration_files(work)
            data = _calibration_questions()
            data["questions"][0]["display"]["prompt"] = "日主身强且盘面证据明确时，你通常怎样处理重要工作？"
            source.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run([sys.executable, str(CALIBRATION_VALIDATOR), str(source), "--analysis", str(analysis)], cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 1)
            self.assertIn("泄露内部信息", result.stdout)

    def test_mixed_axis_user_sample_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rensheng-youji-mixed-axis-") as temp_dir:
            work = Path(temp_dir)
            analysis, _, source = _write_calibration_files(work)
            data = _calibration_questions()
            bad_displays = [
                ("财务", "过去一年，你的钱主要更像是下面哪种来路？", ["工资和平台项目占大头，很少做短线操作", "大额支出前会先核对计划，不轻易跟投", "近几年会明显感到机会变多、收入结构在变"]),
                ("事业与组织", "你现在的工作主线更像是哪一种？", ["在单位或平台里做专业，靠职级积累", "常会被要求兼顾经营和资源，落地有点难", "主要会留在稳定系统里，很少自己单独闯"]),
                ("关系", "在亲密关系里，你更容易被哪种人吸引？", ["会选稳重、有规划、情绪平和的人", "能一起把事做成、靠行动表达的人", "会选外表吸引强、但掌控或变动大的人"]),
                ("迁移", "过去几年，你搬家或换城市更可能因为什么？", ["因为换工作、单位调动而搬", "会因为资源或项目变动，考虑搬去别的城市", "一直比较安定，很少主动搬去外地"]),
                ("身心", "压力大的时候，你通常更像是哪种状态？", ["会失眠或胃紧，事后需要独处恢复", "会先整理和复盘，把事情排清楚再动", "会和家人商量财务，但容易因钱起争执"]),
            ]
            for index, (domain, prompt, choices) in enumerate(bad_displays):
                data["questions"][index]["display"] = {
                    "number": index + 1, "domain": domain, "prompt": prompt,
                    "choices": [{"key": key, "text": text} for key, text in zip("ABCD", choices + ["都不符合／不确定（可补充）"])],
                }
            source.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run([sys.executable, str(CALIBRATION_VALIDATOR), str(source), "--analysis", str(analysis)], cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 1)
            self.assertIn("没有由冻结Core候选确定性生成", result.stdout)

    def test_choice_effects_are_locked_by_validator(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rensheng-youji-same-effects-") as temp_dir:
            work = Path(temp_dir)
            analysis, _, questions = _write_calibration_files(work)
            data = _calibration_questions()
            data["questions"][0]["audit"]["candidate_effects"]["B"] = [{"candidate_id": "c1", "status": "match"}]
            questions.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run([sys.executable, str(CALIBRATION_VALIDATOR), str(questions), "--analysis", str(analysis)], cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 1)
            self.assertIn("答案影响不是确定性映射", result.stdout)

    def test_five_questions_require_timed_event(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rensheng-youji-no-timed-") as temp_dir:
            work = Path(temp_dir)
            analysis_data = _calibration_analysis()
            analysis_data["reality_candidate_pool"][-1]["candidate_kind"] = "stable_pattern"
            analysis, plan, output = work / "analysis.json", work / "plan.json", work / "questions.json"
            analysis.write_text(json.dumps(analysis_data, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run([sys.executable, str(CALIBRATION_BUILDER), "--analysis", str(analysis), "--output", str(output)], cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 2)
            self.assertIn("时间题覆盖", result.stdout)

    def test_new_card_and_fixed_ten_page_pdf(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rensheng-youji-report-") as temp_dir:
            work = Path(temp_dir)
            report_json = work / "report.json"
            report_json.write_text(json.dumps(_report(), ensure_ascii=False, indent=2), encoding="utf-8")
            free_card = _assemble_free_card(work)
            _, _, calibration_questions = _write_calibration_files(work)
            delivery = work / "delivery"
            _run(str(DELIVERY_GENERATOR), "--report", str(report_json), "--free-card", str(free_card), "--calibration-questions", str(calibration_questions), "--out-dir", str(delivery), "--keep-pages")

            markdown = delivery / "rensheng-youji-full-report.md"
            card = delivery / "rensheng-youji-card.png"
            pdf = delivery / "rensheng-youji-full-report.pdf"
            manifest = json.loads((delivery / "report-delivery-manifest.json").read_text(encoding="utf-8"))
            self.assertTrue(markdown.exists())
            self.assertTrue(pdf.exists())
            self.assertEqual(manifest["checks"]["pdf_pages"], 10)
            self.assertEqual(manifest["checks"]["wechat_asset"], "assets/wechat-contact.jpg")
            self.assertEqual(manifest["checks"]["wechat_sha256"], "bcfd93fb14cb90557504b23eb3b419fe55eb19f3a7062b77299d24f12d9677e8")
            self.assertEqual(manifest["checks"]["cover_logo_asset"], "assets/rensheng-youji-logo.png")
            self.assertEqual(manifest["checks"]["cover_logo_sha256"], "25de53816f50fe9cfa7d56f6c0c6ee15727b455b5f1171300b4ccf6c47ae2a57")
            self.assertEqual(manifest["checks"]["body_font"], "assets/fonts/lxgw/LXGWWenKai-Regular.ttf")
            self.assertEqual(manifest["checks"]["body_font_sha256"], "39ad71264b588165b469e35e6afb162a378dacd1f95348160240ba9038ac3009")
            self.assertEqual(len(list((delivery / "report-pages").glob("page-*.png"))), 10)
            self.assertEqual(len(re.findall(rb"/Type\s*/Page\b", pdf.read_bytes())), 10)
            with Image.open(card) as image:
                self.assertEqual(image.size, (1242, 1660))
            rendered = markdown.read_text(encoding="utf-8")
            self.assertIn("# 人生有迹｜完整报告", rendered)
            self.assertIn("这份报告根据你的出生信息、整体分析和现实校准生成", rendered)
            self.assertIn("## 完整人生主线", rendered)
            self.assertNotIn("初始角色", rendered)
            self.assertNotIn("主线任务", rendered)

    def test_vague_reality_anchor_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rensheng-youji-vague-") as temp_dir:
            source = Path(temp_dir) / "report.json"
            report = _report()
            report["dimensions"][2]["audit"]["reality_anchor_terms"] = ["相关行业"]
            report["dimensions"][2]["audit"]["reality_anchor_sources"] = {"相关行业": ["reality_domains.career", "root_seed_flower_fruit_map"]}
            report["dimensions"][2]["paragraphs"]["organization_role_environment"] = _repeat("目前只能判断与相关行业有关，需要以后继续确认具体工作。", 55)
            source.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run([sys.executable, str(REPORT_RENDERER), str(source), "--out", str(Path(temp_dir) / "report.md")], cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 1)
            self.assertIn("过于宽泛", result.stdout)

    def test_reality_anchor_requires_audited_source(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rensheng-youji-anchor-source-") as temp_dir:
            source = Path(temp_dir) / "report.json"
            report = _report()
            report["dimensions"][2]["audit"]["reality_anchor_sources"].pop("大型国企")
            source.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run([sys.executable, str(REPORT_RENDERER), str(source), "--out", str(Path(temp_dir) / "report.md")], cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 1)
            self.assertIn("必须逐项覆盖现实名词", result.stdout)

    def test_overview_cannot_stack_hedges(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rensheng-youji-hedges-") as temp_dir:
            source = Path(temp_dir) / "report.json"
            report = _report()
            report["dimensions"][2]["overview"] = _repeat("你可能更可能倾向于在规则清楚的单位负责复杂任务，并把它推进到交付。", 55)
            source.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run([sys.executable, str(REPORT_RENDERER), str(source), "--out", str(Path(temp_dir) / "report.md")], cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 1)
            self.assertIn("条件词过多", result.stdout)

    def test_category_only_anchor_requires_boundary(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rensheng-youji-category-boundary-") as temp_dir:
            source = Path(temp_dir) / "report.json"
            report = _report()
            report["dimensions"][2]["audit"]["anchor_precision"] = "category_only"
            report["dimensions"][2]["audit"]["needs_validation"] = "以后再观察。"
            source.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run([sys.executable, str(REPORT_RENDERER), str(source), "--out", str(Path(temp_dir) / "report.md")], cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 1)
            self.assertIn("必须明确收窄边界", result.stdout)

    def test_year_signal_term_must_be_visible(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rensheng-youji-year-signal-") as temp_dir:
            source = Path(temp_dir) / "report.json"
            report = _report()
            report["yearly_outlook"]["years"][0]["signal_terms"] = ["岗位调整"]
            source.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run([sys.executable, str(REPORT_RENDERER), str(source), "--out", str(Path(temp_dir) / "report.md")], cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 1)
            self.assertIn("必须实际出现年度现实载体", result.stdout)

    def test_focus_scope_rejects_overfocused_life_theme(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rensheng-youji-focus-") as temp_dir:
            source = Path(temp_dir) / "report.json"
            report = _report()
            report["profile"]["focus"] = "情感方向"
            report["focus_scope"]["selected_focus"] = "情感方向"
            report["executive_summary"]["life_theme"] = _repeat("你的感情关系与伴侣选择一直围绕亲密关系发展，并继续影响感情安排。", 65)
            source.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run([sys.executable, str(REPORT_RENDERER), str(source), "--out", str(Path(temp_dir) / "report.md")], cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 1)
            self.assertIn("关注方向过度进入完整人生主线", result.stdout)

    def test_calibration_must_cover_four_domains(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rensheng-youji-domain-") as temp_dir:
            work = Path(temp_dir)
            analysis, _, source = _write_calibration_files(work)
            data = _calibration_questions()
            for index, domain in enumerate(["事业与组织", "事业与组织", "关系", "关系", "财务"]):
                data["questions"][index]["display"]["domain"] = domain
            source.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run([sys.executable, str(CALIBRATION_VALIDATOR), str(source), "--analysis", str(analysis)], cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 1)
            self.assertIn("没有由冻结Core候选确定性生成", result.stdout)

    def test_past_year_cannot_appear_in_current_actions(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rensheng-youji-past-action-") as temp_dir:
            source = Path(temp_dir) / "report.json"
            report = _report()
            report["action_guide"]["priority_actions"][0] = _repeat("2025年先准备服务样板，再根据反馈调整下一步。", 30)
            source.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run([sys.executable, str(REPORT_RENDERER), str(source), "--out", str(Path(temp_dir) / "report.md")], cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 1)
            self.assertIn("不得使用过去年份", result.stdout)

    def test_visible_mingli_terms_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rensheng-youji-mingli-leak-") as temp_dir:
            source = Path(temp_dir) / "report.json"
            report = _report()
            report["dimensions"][2]["paragraphs"]["recurring_problem_and_change"] = _repeat("丙午透出以后食伤更明显，因此适合开始承担新的工作责任。", 70)
            source.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run([sys.executable, str(REPORT_RENDERER), str(source), "--out", str(Path(temp_dir) / "report.md")], cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 1)
            self.assertIn("不得直接出现内部命理术语", result.stdout)

    def test_question_keywords_cannot_dominate_dimensions(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rensheng-youji-topic-leak-") as temp_dir:
            source = Path(temp_dir) / "report.json"
            report = _report()
            report["profile"]["question"] = "未来两年是否适合开展玄学副业并形成收入"
            report["focus_scope"]["topic_keywords"] = ["玄学副业"]
            report["dimensions"][2]["paragraphs"]["ability_and_formation"] = _repeat("玄学副业需要先完成项目交付和服务样板，并核对真实反馈。", 70)
            report["dimensions"][2]["paragraphs"]["organization_role_environment"] = _repeat("玄学副业可以先在大型国企或成熟科技公司之外完成服务样板。", 70)
            report["dimensions"][2]["paragraphs"]["recurring_problem_and_change"] = _repeat("玄学副业需要先完成服务样板并核对真实反馈。", 70)
            source.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run([sys.executable, str(REPORT_RENDERER), str(source), "--out", str(Path(temp_dir) / "report.md")], cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 1)
            self.assertIn("过度进入六领域基础分析", result.stdout)

    def test_internal_editorial_labels_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rensheng-youji-editorial-label-") as temp_dir:
            source = Path(temp_dir) / "report.json"
            report = _report()
            report["dimensions"][3]["paragraphs"]["income_and_accumulation"] = _repeat("现实落点是固定工资、年度绩效和项目奖金，需要逐步形成稳定收入。", 60)
            source.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run([sys.executable, str(REPORT_RENDERER), str(source), "--out", str(Path(temp_dir) / "report.md")], cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 1)
            self.assertIn("生硬模板词", result.stdout)

    def test_calibration_choice_cannot_be_copied_into_report(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rensheng-youji-calibration-copy-") as temp_dir:
            source = Path(temp_dir) / "report.json"
            report = _report()
            selected = report["calibration"]["responses"][0]["selected_text"]
            report["dimensions"][2]["paragraphs"]["ability_and_formation"] = _repeat(selected + "，这也是你处理项目交付时最常使用的方法。", 60)
            source.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run([sys.executable, str(REPORT_RENDERER), str(source), "--out", str(Path(temp_dir) / "report.md")], cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 1)
            self.assertIn("不能原句复制", result.stdout)

    def test_each_dimension_requires_its_four_topics(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rensheng-youji-dimension-topics-") as temp_dir:
            source = Path(temp_dir) / "report.json"
            report = _report()
            report["dimensions"][3]["paragraphs"].pop("leakage_and_change")
            source.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run([sys.executable, str(REPORT_RENDERER), str(source), "--out", str(Path(temp_dir) / "report.md")], cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 1)
            self.assertIn("按领域固定顺序完整填写", result.stdout)

    def test_fullwidth_percent_is_normalized_for_pdf(self) -> None:
        self.assertEqual(normalize_display_text("每月转入20％—30％"), "每月转入百分之20到百分之30")

    def test_report_relationship_years_must_match_card(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rensheng-youji-relationship-match-") as temp_dir:
            work = Path(temp_dir)
            report = _report()
            report["cross_output_consistency"]["relationship_opportunity_years"] = []
            report_json = work / "report.json"
            report_json.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
            free_card = _assemble_free_card(work)
            _, _, calibration_questions = _write_calibration_files(work)
            result = subprocess.run([sys.executable, str(DELIVERY_GENERATOR), "--report", str(report_json), "--free-card", str(free_card), "--calibration-questions", str(calibration_questions), "--out-dir", str(work / "delivery")], cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 1)
            self.assertIn("明显关系机会年份与新版卡片桃花年份不一致", result.stdout)

    def test_unapproved_wechat_asset_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rensheng-youji-qr-") as temp_dir:
            source = Path(temp_dir) / "report.json"
            report = _report()
            report["author"]["wechat_image"] = "assets/placeholder.jpg"
            source.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run([sys.executable, str(REPORT_RENDERER), str(source), "--out", str(Path(temp_dir) / "report.md")], cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 1)
            self.assertIn("正式资源", result.stdout)

    def test_report_and_card_must_share_core_source(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rensheng-youji-source-") as temp_dir:
            work = Path(temp_dir)
            report_json = work / "report.json"
            report_json.write_text(json.dumps(_report(), ensure_ascii=False), encoding="utf-8")
            free_card = _assemble_free_card(work)
            data = json.loads(free_card.read_text(encoding="utf-8"))
            data["source"]["analysis_id"] = "different-core-analysis"
            free_card.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            _, _, calibration_questions = _write_calibration_files(work)
            result = subprocess.run([sys.executable, str(DELIVERY_GENERATOR), "--report", str(report_json), "--free-card", str(free_card), "--calibration-questions", str(calibration_questions), "--out-dir", str(work / "delivery")], cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 1)
            self.assertIn("不是来自同一Core母稿", result.stdout)

    def test_report_response_must_match_original_calibration_effect(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rensheng-youji-response-match-") as temp_dir:
            work = Path(temp_dir)
            report = _report()
            report["calibration"]["responses"][0]["candidate_updates"][0]["status"] = "partial"
            report_json = work / "report.json"
            report_json.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
            free_card = _assemble_free_card(work)
            _, _, calibration_questions = _write_calibration_files(work)
            result = subprocess.run([sys.executable, str(DELIVERY_GENERATOR), "--report", str(report_json), "--free-card", str(free_card), "--calibration-questions", str(calibration_questions), "--out-dir", str(work / "delivery")], cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 1)
            self.assertIn("没有忠实回写该选项的Core候选影响", result.stdout)

    def test_skipped_calibration_cannot_create_formal_pdf(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rensheng-youji-preliminary-") as temp_dir:
            work = Path(temp_dir)
            report = _report()
            report["document_mode"] = "preliminary_uncalibrated"
            report["source"]["calibration_status"] = "skipped"
            report["title"] = "人生有迹｜初步分析"
            report["chart"]["formal_report_allowed"] = False
            report["calibration"] = {"question_schema_version": "3.0.0", "template_version": "2.0.0", "summary": "用户跳过现实校准。", "birth_time_status": "待核对", "responses": [], "confirmed": [], "partial": [], "rejected": [], "uncertain": []}
            report_json = work / "report.json"
            report_json.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
            free_card = _assemble_free_card(work)
            _, _, calibration_questions = _write_calibration_files(work)
            delivery = work / "delivery"
            _run(str(DELIVERY_GENERATOR), "--report", str(report_json), "--free-card", str(free_card), "--calibration-questions", str(calibration_questions), "--out-dir", str(delivery))
            manifest = json.loads((delivery / "report-delivery-manifest.json").read_text(encoding="utf-8"))
            self.assertIn("formal_pdf_skipped", manifest["checks"])
            self.assertFalse((delivery / "rensheng-youji-full-report.pdf").exists())


if __name__ == "__main__":
    unittest.main()
