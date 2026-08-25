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
sys.path.insert(0, str(ROOT / "skills/rensheng-youji-growth-map/scripts"))
from render_report_pdf import normalize_display_text  # noqa: E402


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
            "你不是边做边想的人；遇到重要选择，先把风险与步骤排清楚才会行动。",
            "现实里最常见的是任务清单和交付复核：接到模糊任务先补资料，提交前再查一遍容易出错的细节。",
            "这让你在复杂事务中很少漏项，但被连续催促时会先压住分歧把事情做完，事后才说明不满，责任因此容易越接越多。",
            "可核对最近三次临时任务，你是否都先整理条件，并在完成后才表达异议。",
            ["任务清单", "交付复核"],
        ),
        "love_partner": (
            "你真正看重的不是一时热烈，而是对方能否把承诺变成稳定回应和现实安排。",
            "判断一段关系时，你会看见面频率、城市选择和金钱安排，而不是只听口头表态；这三件事比浪漫表达更影响投入。",
            "你会被做事利落、标准明确的人吸引，但若对方习惯替你决定或回避未来计划，最初的欣赏很快会变成控制与失望。",
            "可核对过往最深的一次关系摩擦，是否最终落在时间、城市或钱没有说清。",
            ["见面频率", "城市选择", "金钱安排"],
        ),
        "career": (
            "你的优势不在泛泛协调，而在把复杂信息整理成规则、方案并盯到可交付结果。",
            "现实落点优先看大型国企或成熟科技公司的产品运营、项目管理与风险控制；核心任务是项目交付，不是单纯维系人情。",
            "这类岗位给你明确标准和积累路径，做久后能形成信誉；职责模糊、成果归属不清的团队则会让你不断收尾，却换不来职位或收入。",
            "若用户没有真实职业资料，组织与岗位只能作为同一工作机制下的优先方向，还需用履历收窄。",
            ["大型国企", "成熟科技公司", "项目交付"],
        ),
        "finance_resources": (
            "你的钱主要靠长期职业积累，而不是靠一次机会翻倍；收入增长先跟职责和专业定价走。",
            "最能留下来的来源是固定工资、年度绩效和项目奖金；朋友合作或口头约定的分成不适合作为主要预算。",
            "只要分工和结算日期不清楚，你就容易先垫时间甚至垫钱，最后得到人情却没有完整回款；这也是比消费冲动更明显的漏财处。",
            "可核对最近两笔额外收入，是否有书面范围、结算日期，以及实际到账是否晚于交付。",
            ["固定工资", "年度绩效", "项目奖金"],
        ),
        "body_emotion": (
            "你的压力往往不是当场爆发，而是白天继续处理，到了晚上仍停不下对未完成事项的复盘。",
            "现实里先看睡前反复想工作、颈肩紧张和三餐推迟；这三类信号通常在并行任务过多时一起出现。",
            "你靠减少输入、独处和恢复固定睡眠比继续娱乐更容易缓过来；这些只是压力节奏的观察，不能据此诊断器官或疾病。",
            "若不忙时仍长期失眠、疼痛或食欲异常，应以正规医疗评估为准，报告不作疾病判断。",
            ["睡前反复想工作", "颈肩紧张", "三餐推迟"],
        ),
        "family_growth": (
            "你在家中较容易成为处理实际问题的人，支持与压力都围绕是否能把事情安排妥当。",
            "常见载体是学费证书、住房安排和长辈照护：家里愿意在关键费用或信息上帮忙，也会期待你回报稳定和责任。",
            "你通常先接下任务再谈自己的时间，久而久之会被默认负责协调；真正的边界不是减少联系，而是把谁出钱、谁执行、何时完成说清。",
            "可核对近一年一次家庭任务，最后是否由你负责联系、付款或收尾中的至少一项。",
            ["学费证书", "住房安排", "长辈照护"],
        ),
    }[identifier]
    verdict, anchor, pattern, verification, anchor_terms = content
    return {
        "id": identifier,
        "title": title,
        "main_verdict": verdict,
        "reality_anchor": anchor,
        "pattern_and_cost": pattern,
        "verification_point": verification,
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
    return {
        "schema_version": "2.4.0",
        "document_mode": "full_calibrated",
        "source": {"analysis_id": "fixture-v2-pipeline", "core_version": "0.3.0", "analysis_as_of": "2026-08-20", "calibration_status": "calibrated"},
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
    def test_skill_keeps_reality_details_optional(self) -> None:
        skill_text = (ROOT / "skills/rensheng-youji-growth-map/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("两轮收集输入", skill_text)
        self.assertIn("学历、专业、当前职业或学习状态；每项都非必答", skill_text)
        self.assertIn("当前关系状态、反复出现的相处情况；每项都非必答", skill_text)
        self.assertIn("相关家庭关系、正在发生的矛盾或责任；每项都非必答", skill_text)
        self.assertIn("用户可以只回复五个字母，忽略全部可选补充", skill_text)
        self.assertIn("不得再次追问、降低交付规格", skill_text)
        self.assertNotIn("不知道时明确写“不知道”", skill_text)

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
            self.assertEqual(manifest["checks"]["cover_logo_asset"], "assets/rensheng-youji-logo.png")
            self.assertEqual(manifest["checks"]["cover_logo_sha256"], "25de53816f50fe9cfa7d56f6c0c6ee15727b455b5f1171300b4ccf6c47ae2a57")
            self.assertEqual(len(list((delivery / "report-pages").glob("page-*.png"))), 10)
            self.assertEqual(len(re.findall(rb"/Type\s*/Page\b", pdf.read_bytes())), 10)
            with Image.open(card) as image:
                self.assertEqual(image.size, (1242, 1660))
            rendered = markdown.read_text(encoding="utf-8")
            self.assertIn("# 人生有迹｜完整报告", rendered)
            self.assertIn("这份报告根据你的出生信息、完整命盘和现实校准生成", rendered)
            self.assertIn("## 完整人生主线", rendered)
            self.assertNotIn("初始角色", rendered)
            self.assertNotIn("主线任务", rendered)

    def test_vague_reality_anchor_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rensheng-youji-vague-") as temp_dir:
            source = Path(temp_dir) / "report.json"
            report = _report()
            report["dimensions"][2]["audit"]["reality_anchor_terms"] = ["相关行业"]
            report["dimensions"][2]["audit"]["reality_anchor_sources"] = {"相关行业": ["reality_domains.career", "root_seed_flower_fruit_map"]}
            report["dimensions"][2]["reality_anchor"] = _repeat("现实落点仍是相关行业，需要以后继续核对。", 40)
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

    def test_main_verdict_cannot_stack_hedges(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rensheng-youji-hedges-") as temp_dir:
            source = Path(temp_dir) / "report.json"
            report = _report()
            report["dimensions"][2]["main_verdict"] = "你可能更适合在规则清楚的组织里负责复杂任务，并把它推进到交付。"
            source.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run([sys.executable, str(REPORT_RENDERER), str(source), "--out", str(Path(temp_dir) / "report.md")], cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 1)
            self.assertIn("只能保留一个必要的条件词", result.stdout)

    def test_category_only_anchor_requires_boundary(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rensheng-youji-category-boundary-") as temp_dir:
            source = Path(temp_dir) / "report.json"
            report = _report()
            report["dimensions"][2]["audit"]["anchor_precision"] = "category_only"
            report["dimensions"][2]["verification_point"] = "可核对过往工作是否也以复杂资料、跨部门推进和最终交付为主。"
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
            source = Path(temp_dir) / "questions.json"
            data = _calibration_questions()
            for index, domain in enumerate(["事业与组织", "事业与组织", "关系", "关系", "财务"]):
                data["questions"][index]["display"]["domain"] = domain
            source.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run([sys.executable, str(CALIBRATION_VALIDATOR), str(source)], cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 3)
            self.assertIn("至少覆盖四个生活领域", result.stdout)

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
            report["dimensions"][2]["pattern_and_cost"] = _repeat("丙午透出以后食伤更明显，因此适合开始承担新的工作责任。", 90)
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
            for index in range(3):
                report["dimensions"][2]["pattern_and_cost"] = _repeat("玄学副业需要先完成服务样板并核对真实反馈。", 120)
            source.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run([sys.executable, str(REPORT_RENDERER), str(source), "--out", str(Path(temp_dir) / "report.md")], cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 1)
            self.assertIn("过度进入六领域基础分析", result.stdout)

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
            result = subprocess.run([sys.executable, str(DELIVERY_GENERATOR), "--report", str(report_json), "--free-card", str(free_card), "--out-dir", str(work / "delivery")], cwd=ROOT, text=True, capture_output=True, check=False)
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
