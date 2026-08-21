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
DELIVERY_GENERATOR = ROOT / "skills/rensheng-youji-growth-map/scripts/generate_full_report.py"
PREFLIGHT = ROOT / "skills/rensheng-youji-growth-map/scripts/preflight_report.py"


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
    specifics = {
        "self_growth": {
            "daily_habits": ["接到模糊任务时先列步骤和缺少的资料", "交付前会反复核对容易出错的细节"],
            "decision_style": "先比较风险、时间和后续影响，确认关键条件后才决定",
            "conflict_response": "被催促或质疑时先把事情做完，之后才说明自己的不同意见",
            "recovery_pattern": "压力大时需要暂时减少社交，通过独处、整理或规律作息恢复",
        },
        "love_partner": {
            "attraction_traits": ["说话直接并愿意把现实安排讲清楚", "做事有自己的专业标准和稳定节奏"],
            "long_term_traits": ["遇到分歧愿意讨论而不是突然失联回避", "能够共同商量金钱、城市与家庭边界"],
            "high_friction_traits": ["行动果断但习惯替别人决定重要事情", "吸引力强却不愿说明关系和未来安排"],
            "interaction_pattern": "通常先观察对方是否可靠，确认回应稳定后才逐步增加投入和表达",
        },
        "career": {
            "industry_candidates": ["金融与风险管理", "数据与研究服务"],
            "role_candidates": ["产品策划与项目运营", "研究分析与风险控制"],
            "task_pattern": "更适合把复杂资料整理成方案、规则或可交付成果，并持续跟进结果",
            "unsuitable_environment": "不适合长期处在职责模糊、只靠人情推动且成果归属不清的团队",
        },
        "finance_resources": {
            "primary_source": "主要依靠稳定工资和专业能力形成的职位溢价",
            "secondary_source": "第二来源较像项目奖金、绩效或阶段性合作收入",
            "unstable_source": "朋友合作、短期机会或未经验证的投资回报波动更大",
            "leakage_risk": "容易在人情往来、模糊分工或先垫付后结算的情形中损失钱和时间",
            "retention_method": "适合先固定储蓄和长期账户，再安排可以承受损失的尝试预算",
        },
        "body_emotion": {
            "stress_signals": ["连续忙碌后容易睡前仍反复整理未完成事项", "任务堆积时更容易减少休息或回避交流"],
            "recovery_conditions": "先减少同时处理的任务数量，再通过规律睡眠和轻度活动恢复",
            "sustainable_rhythm": "适合有明确截止时间，也能保留固定休息和独处时间的生活安排",
            "evidence_limit": "这些只是压力与恢复方式候选，不能据此诊断任何器官或疾病",
        },
        "family_growth": {
            "support_source": "支持更可能来自愿意提供教育信息、实际安排或关键费用的家庭角色",
            "expectation_source": "压力更可能来自强调结果、稳定收入和家庭责任的权威角色",
            "family_role": "家里遇到需要协调或收尾的事情时，容易成为被询问和托付的人",
            "boundary_pattern": "常先把家人的需要处理好，再说明自己的时间和选择边界",
            "education_path_candidate": "学习路径更像先完成较稳妥的学历训练，再通过实习、证书或项目调整方向",
        },
    }[identifier]
    return {
        "id": identifier,
        "title": title,
        "finding": _repeat("这个领域需要把已有能力、现实责任和自己的选择放在一起判断。", 35),
        "specific_judgments": specifics,
        "analysis": [
            _repeat("这种方式不是由单一性格决定，更可能受到家庭要求、教育训练、工作分工和近年经历共同影响。它带来可靠与细致，也可能让你在责任增加时忽略自己的需要。", 120),
            _repeat("当前阶段更值得观察的是，投入能否形成清楚结果，以及相关的人、时间和收入安排是否可持续。条件改变以后，同一套能力也可能表现为更主动的选择，而不是被动增加任务。", 120),
        ],
        "current_focus": _repeat("先把正在面对的选择拆成可以核对的现实条件。", 30),
        "suggestions": [_repeat("连续记录两周实际投入、得到的支持和形成的结果，再决定下一步。", 28)],
        "confidence": "中等置信",
        "audit": {
            "core_sections": [extra_source, "root_seed_flower_fruit_map", "cross_method_analysis"],
            "evidence_lenses": ["root_seed_flower_fruit_map", "cross_method_analysis"],
            "specific_judgment_sources": {key: [extra_source, "root_seed_flower_fruit_map"] for key in specifics},
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
            "likely_expression": _repeat("这一年可能继续处理工作、收入与关系之间的时间分配，并在行动反馈中逐步确认什么更值得长期投入。", 48),
            "seed_for_next": _repeat("留下更清楚的选择条件和可以继续使用的经验。", 24),
            "confidence": "中等置信",
        }
        for year in range(2021, 2041)
    ]
    return {
        "schema_version": "2.2.0",
        "document_mode": "full_calibrated",
        "source": {"analysis_id": "fixture-v2-pipeline", "core_version": "0.3.0", "analysis_as_of": "2026-08-20", "calibration_status": "calibrated"},
        "title": "人生有迹｜完整报告",
        "subtitle": "看见你带来的能力，理解你走过的路，也寻找新的可能",
        "generated_on": "2026-08-20",
        "brand": "人生有迹 by 景行",
        "profile": {"name": "示例", "identity_option": "女", "birth": "1994-10-02 14:24（普通钟表时间）", "location": "湖北省武汉市", "focus": "事业发展", "question": "未来两年更适合继续积累还是承担新的责任"},
        "chart": {"pillars": ["甲戌", "癸酉", "丁卯", "丁未"], "luck_start": "1998-01-01 00:00:00", "current_luck_cycle": "阶段示例（2024—2033）", "time_basis": "普通钟表时间输入，已进行真太阳时校正", "uncertainty": "不接近时辰边界", "formal_report_allowed": True},
        "calibration": {
            "summary": "五题均已作答，其中四题形成较清楚的现实路径，一题仍不确定。",
            "birth_time_status": "稳定",
            "responses": [
                {"question_number": index, "domain": domain, "choice": "A" if index < 5 else "D", "selected_text": "先收集资料和比较风险，想清楚后再行动" if index < 5 else "都不符合或暂时不确定，需要以后再观察", "candidate_id": f"c{index:02d}1" if index < 5 else None, "user_note": ""}
                for index, domain in enumerate(["事业与组织", "家庭与教育", "关系", "财务", "迁移"], start=1)
            ],
            "confirmed": ["工作中经常承担收尾责任", "重要选择通常会比较长期结果", "近年更在意投入是否值得"],
            "partial": ["学习路径曾经出现调整"],
            "rejected": [],
            "uncertain": ["家庭分工仍需确认"],
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
            "priority_actions": [_repeat("明确下一阶段最希望增加的一项能力，以及它能形成什么现实结果。", 38), _repeat("比较不同选择能否带来职位、收入、作品或更清楚的职责范围。", 38), _repeat("为工作、关系与休息分别保留固定时间，每月核对一次真实投入。", 38)],
            "reduce": _repeat("减少在信息不足时同时准备过多方案，先验证最关键的一个条件。", 38),
            "traditional_preferences": [{"area": "家居与工作区", "advice": _repeat("保持明亮整洁，并为重要任务留出固定位置和连续时间。", 32)}, {"area": "人情往来", "advice": _repeat("重要责任提前说清范围，减少模糊答应后再独自完成。", 32)}],
        },
        "open_questions": ["家庭对职业选择的实际影响仍需确认。", "当前两个工作选项的收入和职责差异仍需补充。"],
        "assisted_service_note": "本Skill可免费自行生成；如果你的AI无法运行Skill，或希望获得人工校准、PDF整理和问题解释，可以联系景行。",
        "author": {"name": "景行", "bio": "持续整理传统命理与现实经历之间可以核对的联系。", "github": "https://github.com/bobbybluemoment-afk/rensheng-youji-api", "web": "https://rensheng-youji-web.bobbybluemoment.workers.dev", "wechat_image": "assets/wechat-contact.jpg", "wechat_note": "添加时建议备注：人生有迹"},
        "boundaries": ["本报告用于传统文化体验与自我观察，不构成医疗、心理、法律、投资或其他专业意见。", "报告提供的是有条件、可验证的倾向，不代表唯一解释或必然命运。"],
    }


def _calibration_questions() -> dict:
    domains = ["事业与组织", "家庭与教育", "关系", "财务", "迁移"]
    questions = []
    for index, domain in enumerate(domains, start=1):
        candidate_ids = [f"c{index:02d}{choice}" for choice in (1, 2, 3)]
        questions.append({
            "display": {
                "number": index,
                "domain": domain,
                "prompt": "遇到一个重要但条件还不清楚的选择时，你通常怎样处理？",
                "choices": [
                    {"key": "A", "text": "先收集资料和比较风险，想清楚后再行动"},
                    {"key": "B", "text": "先尝试一个小步骤，再根据结果继续调整"},
                    {"key": "C", "text": "先询问信任的人，得到确认后再作决定"},
                    {"key": "D", "text": "都不符合／不确定（可补充）"},
                ],
            },
            "audit": {"candidate_ids": candidate_ids, "choice_meanings": {"A": candidate_ids[0], "B": candidate_ids[1], "C": candidate_ids[2], "D": "uncertain"}, "evidence_lenses": ["root_seed_flower_fruit_map", "resource_relationship"], "core_sections": ["reality_candidate_pool", "reality_domains"], "alternatives": ["现实环境也可能形成相似经历"], "birth_time_dependency": "partial", "confidence": "medium"},
        })
    return {"schema_version": "2.0.0", "questions": questions}


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
    analysis.write_text(json.dumps({"analysis_meta": {"status": "complete", "analysis_id": "fixture-v2-pipeline", "core_version": "0.3.0", "analysis_as_of": "2026-08-20"}}, ensure_ascii=False), encoding="utf-8")
    content.write_text(json.dumps(_card_content(), ensure_ascii=False), encoding="utf-8")
    _run("internal/rensheng-youji-free-card-output/scripts/build_visual_series.py", str(signals), "--output", str(series))
    _run("scripts/assemble_free_card.py", "--analysis", str(analysis), "--content", str(content), "--series", str(series), "--output", str(output))
    return output


class FullReportPipelineTest(unittest.TestCase):
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
            source, visible = work / "questions.json", work / "visible.md"
            source.write_text(json.dumps(_calibration_questions(), ensure_ascii=False), encoding="utf-8")
            _run(str(CALIBRATION_VALIDATOR), str(source), "--visible-out", str(visible))
            text = visible.read_text(encoding="utf-8")
            self.assertNotIn("c01", text)
            self.assertNotIn("盘面", text)
            self.assertNotIn("root_seed", text)
            self.assertEqual(text.count("A. 先收集资料"), 5)

    def test_visible_evidence_leak_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rensheng-youji-calibration-bad-") as temp_dir:
            source = Path(temp_dir) / "questions.json"
            data = _calibration_questions()
            data["questions"][0]["display"]["prompt"] = "日主身强且盘面证据明确时，你通常怎样处理重要工作？"
            source.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run([sys.executable, str(CALIBRATION_VALIDATOR), str(source)], cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 3)
            self.assertIn("泄露内部术语", result.stdout)

    def test_new_card_and_fixed_ten_page_pdf(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rensheng-youji-report-") as temp_dir:
            work = Path(temp_dir)
            report_json = work / "report.json"
            report_json.write_text(json.dumps(_report(), ensure_ascii=False, indent=2), encoding="utf-8")
            free_card = _assemble_free_card(work)
            delivery = work / "delivery"
            _run(str(DELIVERY_GENERATOR), "--report", str(report_json), "--free-card", str(free_card), "--out-dir", str(delivery), "--keep-pages")

            markdown = delivery / "rensheng-youji-full-report.md"
            card = delivery / "rensheng-youji-card.png"
            pdf = delivery / "rensheng-youji-full-report.pdf"
            manifest = json.loads((delivery / "report-delivery-manifest.json").read_text(encoding="utf-8"))
            self.assertTrue(markdown.exists())
            self.assertTrue(pdf.exists())
            self.assertEqual(manifest["checks"]["pdf_pages"], 10)
            self.assertEqual(manifest["checks"]["wechat_asset"], "assets/wechat-contact.jpg")
            self.assertEqual(manifest["checks"]["wechat_sha256"], "bcfd93fb14cb90557504b23eb3b419fe55eb19f3a7062b77299d24f12d9677e8")
            self.assertEqual(len(list((delivery / "report-pages").glob("page-*.png"))), 10)
            self.assertEqual(len(re.findall(rb"/Type\s*/Page\b", pdf.read_bytes())), 10)
            with Image.open(card) as image:
                self.assertEqual(image.size, (1242, 1660))
            rendered = markdown.read_text(encoding="utf-8")
            self.assertIn("# 人生有迹｜完整报告", rendered)
            self.assertNotIn("初始角色", rendered)
            self.assertNotIn("主线任务", rendered)

    def test_vague_career_candidates_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rensheng-youji-vague-") as temp_dir:
            source = Path(temp_dir) / "report.json"
            report = _report()
            report["dimensions"][2]["specific_judgments"]["industry_candidates"] = ["相关行业", "综合岗位"]
            source.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run([sys.executable, str(REPORT_RENDERER), str(source), "--out", str(Path(temp_dir) / "report.md")], cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 1)
            self.assertIn("过于宽泛", result.stdout)

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
            result = subprocess.run([sys.executable, str(DELIVERY_GENERATOR), "--report", str(report_json), "--free-card", str(free_card), "--out-dir", str(work / "delivery")], cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 1)
            self.assertIn("不是来自同一Core母稿", result.stdout)

    def test_skipped_calibration_cannot_create_formal_pdf(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rensheng-youji-preliminary-") as temp_dir:
            work = Path(temp_dir)
            report = _report()
            report["document_mode"] = "preliminary_uncalibrated"
            report["source"]["calibration_status"] = "skipped"
            report["title"] = "人生有迹｜初步分析"
            report["chart"]["formal_report_allowed"] = False
            report["calibration"] = {"summary": "用户跳过现实校准。", "birth_time_status": "待核对", "responses": [], "confirmed": [], "partial": [], "rejected": [], "uncertain": []}
            report_json = work / "report.json"
            report_json.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
            free_card = _assemble_free_card(work)
            delivery = work / "delivery"
            _run(str(DELIVERY_GENERATOR), "--report", str(report_json), "--free-card", str(free_card), "--out-dir", str(delivery))
            manifest = json.loads((delivery / "report-delivery-manifest.json").read_text(encoding="utf-8"))
            self.assertIn("formal_pdf_skipped", manifest["checks"])
            self.assertFalse((delivery / "rensheng-youji-full-report.pdf").exists())


if __name__ == "__main__":
    unittest.main()
