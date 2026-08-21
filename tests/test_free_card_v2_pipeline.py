#!/usr/bin/env python3
"""新版免费卡片确定性链路验收测试。

该测试从一份固定的、已脱敏的视觉信号样例开始，依次执行：
视觉信号校验 -> 20年序列生成 -> 卡片数据组装 -> PNG渲染。
AI 生成 Core 母稿的步骤不属于确定性测试范围。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image


ROOT = Path(__file__).resolve().parent.parent
CENTER_YEAR = 2026


def _baseline(value: float, confidence: str = "medium") -> dict:
    return {
        "facts": value,
        "prior_cycles": value,
        "natal": value,
        "social_stage": value,
        "weighted_score": value,
        "confidence": confidence,
        "basis": ["固定验收样例"],
    }


def _visual_signals() -> dict:
    years = []
    for index, year in enumerate(range(CENTER_YEAR - 5, CENTER_YEAR + 15)):
        strong_relationship_year = index in {5, 11, 16}
        pressure_year = index in {7, 8}
        years.append({
            "year": year,
            "age": 27 + index,
            "theme": "积累逐步形成结果",
            "direction": "pressure" if pressure_year else "support",
            "luck_bias": -0.5 if pressure_year else 0.6,
            "stage_target_shift": round(-1.5 + index * 0.24, 2),
            "opportunity": 1.0 if pressure_year else 2.0,
            "cost": 2.2 if pressure_year else 1.0,
            "realization": -0.5 if pressure_year else 0.6,
            "durable_shift": -0.2 if pressure_year else 0.25,
            "change_intensity": "high" if index in {7, 12} else "medium",
            "activation_strength": 2 if index in {5, 7, 12} else 1,
            "reversal_level": 1 if pressure_year else 0,
            "major_transition": index in {7, 12},
            "confirmed_major_event": False,
            "career_outcome": "rebuild" if index == 7 else "rise" if index in {4, 5, 11, 12, 17} else "consolidate",
            "career_strength": 2.2 if index in {4, 5, 11, 12, 17} else 1.2,
            "learning_carry": 1.2 if index in {3, 4, 10, 11} else 0.4,
            "wealth_inflow": 2.0 if index in {5, 11, 12, 17} else 1.2,
            "wealth_outflow": 2.2 if pressure_year else 0.8,
            "resource_restructure": pressure_year,
            "relationship_natal_entry": 1.2,
            "relationship_luck_environment": 1.4 if strong_relationship_year else 0.6,
            "relationship_opportunity": 2.4 if strong_relationship_year else 0.8,
            "relationship_carry": 0.6 if strong_relationship_year else 0.2,
            "relationship_confirmed_context": 0.4 if strong_relationship_year else 0.0,
            "relationship_conflict_only": False,
            "confidence": "medium",
            "basis": ["固定验收样例"],
        })
    return {
        "schema_version": "1.3.0",
        "analysis_id": "fixture-v2-pipeline",
        "center_year": CENTER_YEAR,
        "evidence_mode": "birth_only",
        "window_start_state": {
            "start_year": CENTER_YEAR - 5,
            "overall": _baseline(0.25),
            "career": _baseline(0.20),
            "wealth": _baseline(0.10),
            "relationship_carry": {
                "strength": 0.2,
                "type": "latent",
                "confidence": "medium",
                "basis": ["固定验收样例"],
            },
        },
        "annual_visual_signals": years,
    }


def _card_content() -> dict:
    return {
        "identity": {
            "name": None,
            "gender_label": "女",
            "birth_text": "1994-10-02 14:24（普通钟表时间）",
            "birthplace": "湖北省武汉市",
            "time_basis_note": "已按出生地中心经度进行真太阳时近似校正",
        },
        "mingju_analysis": {
            "pillars": ["甲戌", "癸酉", "丁卯", "丁未"],
            "structure_text": "命局中的表达、规则与资源关系彼此牵动，做事时既重视结果，也会反复确认选择是否真正适合自己。",
            "life_theme_text": "把长期积累转化为能够留下的成果，同时减少为了照顾外界期待而反复调整自己的方向。",
            "time_dependency_note": "部分现实落点受到时柱影响。",
            "confidence": "medium",
            "basis": ["固定验收样例"],
        },
        "current_issue": {
            "domain": "career",
            "title": "工作选择怎样落下来",
            "body": "你现在可能不是没有方向，而是在几个都能做的选择之间，很难判断哪一个值得长期投入。",
            "example": "例如继续积累现有经验，还是争取一个责任更大、但不确定性也更高的位置。",
            "basis": ["固定验收样例"],
            "confidence": "medium",
        },
        "full_report_hint": {
            "title": "继续查看完整报告",
            "text": "完整报告将展开更长时间和逐年分析。",
        },
        "disclaimers": {
            "trend": "趋势为相对阶段表达，不代表真实金额、职位或事件概率。",
            "general": "内容用于传统文化体验与自我观察。",
        },
    }


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise AssertionError(
            f"命令失败：{' '.join(args)}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


class FreeCardV2PipelineTest(unittest.TestCase):
    def test_visual_signals_to_png(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rensheng-youji-v2-") as temp_dir:
            work = Path(temp_dir)
            signals_path = work / "visual-signals.json"
            series_path = work / "visual-series.json"
            analysis_path = work / "analysis-output.json"
            content_path = work / "card-content.json"
            card_output_path = work / "free-card-output.json"
            png_path = work / "rensheng-youji-card.png"

            signals_path.write_text(
                json.dumps(_visual_signals(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            analysis_path.write_text(
                json.dumps({
                    "analysis_meta": {
                        "status": "complete",
                        "analysis_id": "fixture-v2-pipeline",
                        "core_version": "0.2.0",
                        "analysis_as_of": "2026-08-20",
                    }
                }, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            content_path.write_text(
                json.dumps(_card_content(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            _run(
                "internal/rensheng-youji-free-card-output/scripts/validate_visual_signals.py",
                str(signals_path),
            )
            _run(
                "internal/rensheng-youji-free-card-output/scripts/build_visual_series.py",
                str(signals_path),
                "--output",
                str(series_path),
            )
            _run(
                "scripts/assemble_free_card.py",
                "--analysis",
                str(analysis_path),
                "--content",
                str(content_path),
                "--series",
                str(series_path),
                "--output",
                str(card_output_path),
            )
            _run(
                "scripts/generate_card.py",
                "--input",
                str(card_output_path),
                "--output",
                str(png_path),
            )

            output = json.loads(card_output_path.read_text(encoding="utf-8"))
            years = output["trend_panel"]["years"]
            self.assertEqual(len(years), 20)
            self.assertEqual(years[5]["year"], CENTER_YEAR)
            self.assertTrue(years[5]["is_current"])
            self.assertTrue(all(
                years[index]["life_kline"]["open"] == years[index - 1]["life_kline"]["close"]
                for index in range(1, 20)
            ))
            self.assertTrue(all(
                item["wealth"]["display_ingot_count"] == 2 * item["wealth"]["ingot_count"] - 2
                for item in years
            ))
            self.assertTrue(all(
                not item["peach"]["highlight"] or item["peach"]["color_role"] == "peach_pink"
                for item in years
            ))

            with Image.open(png_path) as image:
                self.assertEqual(image.format, "PNG")
                self.assertEqual(image.size, (1242, 1660))


if __name__ == "__main__":
    unittest.main()
