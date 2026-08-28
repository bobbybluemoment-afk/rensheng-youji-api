#!/usr/bin/env python3
"""验证中文编辑不是自我勾选，并检查事实来源未改变。"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

BANNED = {"组织化过劳型", "先扎根后显声", "表达窗口", "能力输出", "可见度", "物质与经营底色", "资源伴随期待", "表达被规训", "花不显", "现实落点", "核对点", "经营责任", "经营基础", "进入经营期", "经营底色", "经营扩张", "输出与经营"}
MINGLI_TERMS = {"命盘", "命局", "原局", "年柱", "月柱", "日柱", "时柱", "天干", "地支", "干支", "日主", "身强", "身弱", "比肩", "劫财", "食神", "伤官", "食伤", "正印", "偏印", "正财", "偏财", "正官", "七杀", "格局", "调候", "喜用", "忌神", "大运", "流年", "藏干", "透干", "根苗花果", "根气", "冲根", "引动"}


def digest(paragraphs: list[str]) -> str:
    return hashlib.sha256("\n".join(paragraphs).encode("utf-8")).hexdigest()


def report_sections(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    sections = {"life_overview": report.get("executive_summary", {}).get("life_overview", {})}
    for item in report.get("dimensions", []):
        if isinstance(item, dict):
            sections[f"dimension:{item.get('id')}"] = item
    sections["current_question"] = report.get("current_question_narrative", {})
    return sections


def draft_sections(draft: dict[str, Any]) -> dict[str, dict[str, Any]]:
    sections = {"life_overview": draft.get("life_overview", {})}
    for item in draft.get("dimensions", []):
        if isinstance(item, dict):
            sections[f"dimension:{item.get('id')}"] = item
    sections["current_question"] = draft.get("current_question", {})
    return sections


def validate(review: Any, draft: Any, report: Any) -> list[str]:
    errors: list[str] = []
    if not all(isinstance(item, dict) for item in (review, draft, report)):
        return ["编辑记录、初稿和终稿都必须是对象"]
    is_v21 = review.get("version") == "2.1.0"
    is_v22 = review.get("version") == "2.2.0"
    is_v23 = review.get("version") == "2.3.0"
    if review.get("version") not in {"2.0.0", "2.1.0", "2.2.0", "2.3.0"}:
        errors.append("编辑记录版本必须为2.0.0—2.3.0中的受支持版本")
    if review.get("draft_id") != draft.get("draft_id") or review.get("final_report_id") != report.get("report_id"):
        errors.append("编辑记录与初稿或终稿来源不一致")
    draft_map, final_map = draft_sections(draft), report_sections(report)
    records = review.get("sections")
    if not isinstance(records, list) or set(item.get("section_id") for item in records if isinstance(item, dict)) != set(draft_map):
        errors.append("编辑记录必须逐项覆盖完整人生主线、六个领域和当前问题")
        records = []
    changed = 0
    for record in records:
        section_id = record.get("section_id")
        before = draft_map.get(section_id, {})
        after = final_map.get(section_id, {})
        before_text = before.get("paragraphs") or []
        after_text = after.get("paragraphs") or []
        if record.get("draft_sha256") != digest(before_text) or record.get("final_sha256") != digest(after_text):
            errors.append(f"{section_id} 的编辑哈希与实际文本不一致")
        if set(before.get("source_claim_ids") or []) != set(after.get("source_claim_ids") or []):
            errors.append(f"{section_id} 编辑前后判断来源发生变化")
        if set(record.get("source_claim_ids") or []) != set(after.get("source_claim_ids") or []):
            errors.append(f"{section_id} 编辑记录中的判断来源与终稿不一致")
        if (is_v21 or is_v22 or is_v23) and before.get("paragraph_claim_map") != after.get("paragraph_claim_map"):
            errors.append(f"{section_id} 编辑不得改变逐段Core判断映射")
        if is_v22 or is_v23:
            for key in ("domain_specific_claim_ids", "mainline_claim_ids", "mandatory_claim_ids", "domain_mechanisms", "survives_without_mainline"):
                if before.get(key) != after.get(key):
                    errors.append(f"{section_id} 编辑不得改变领域独立性字段：{key}")
            before_spans = before.get("emphasis_spans") or []
            after_spans = after.get("emphasis_spans") or []
            before_map = [(item.get("paragraph_index"), item.get("claim_ids")) for item in before_spans if isinstance(item, dict)]
            after_map = [(item.get("paragraph_index"), item.get("claim_ids")) for item in after_spans if isinstance(item, dict)]
            if len(after_map) > len(before_map) or any(item not in before_map for item in after_map):
                errors.append(f"{section_id} 编辑不得增加重点判断或改变其Core来源；只允许删除不适合突出显示的句子")
            for span in after_spans:
                paragraph_index = span.get("paragraph_index") if isinstance(span, dict) else None
                span_text = span.get("text") if isinstance(span, dict) else None
                if not isinstance(paragraph_index, int) or paragraph_index >= len(after_text) or not isinstance(span_text, str) or span_text not in after_text[paragraph_index] or not re.search(r"[。！？]$", span_text.strip()):
                    errors.append(f"{section_id} 编辑后的重点句必须是对应正文中带句末标点的完整句子")
        if is_v23:
            if before.get("claim_realization_map") != after.get("claim_realization_map"):
                errors.append(f"{section_id} 编辑不得改变Core锁定判断的落地位置或原句")
            for item in after.get("claim_realization_map") or []:
                if not isinstance(item, dict):
                    errors.append(f"{section_id} 含无效Core判断落地记录")
                    continue
                paragraph_index = item.get("paragraph_index")
                exact_span = item.get("exact_span")
                if not isinstance(paragraph_index, int) or not 0 <= paragraph_index < len(after_text) or not isinstance(exact_span, str) or exact_span not in after_text[paragraph_index]:
                    errors.append(f"{section_id} 的Core锁定判断未保留在终稿正文")
        if before_text != after_text:
            changed += 1
        if not isinstance(record.get("changes"), list):
            errors.append(f"{section_id} 缺少具体编辑记录")
    if changed < 3:
        errors.append("独立中文编辑必须对至少三个内容区产生实际修改")
    visible = json.dumps([
        {"title": section.get("title"), "paragraphs": section.get("paragraphs")}
        for section in final_map.values() if isinstance(section, dict)
    ], ensure_ascii=False)
    found = sorted(term for term in BANNED if term in visible)
    if found:
        errors.append("终稿仍含生硬或生造表达：" + "、".join(found))
    mingli_found = sorted(term for term in MINGLI_TERMS if term in visible)
    if mingli_found:
        errors.append("终稿仍含用户不可见的内部命理术语：" + "、".join(mingli_found))
    if re.search(r"校准后的现实线索|校准确认|符合.+判断", visible):
        errors.append("终稿不得展示校准过程")
    third_person = [term for term in ("这个人", "命主", "本人") if term in visible]
    if re.search(r"(?<!其)[他她](?:会|更|通常|可能|容易|需要|倾向|在|的|也|并|则|不|是|有|能|要|把|与|从|对|遇|面对)", visible):
        third_person.append("他／她")
    if third_person:
        errors.append("终稿必须统一使用第二人称“你”，禁止出现：" + "、".join(sorted(set(third_person))))
    for section_id, section in final_map.items():
        for index, paragraph in enumerate(section.get("paragraphs") or []):
            if not isinstance(paragraph, str):
                continue
            if re.search(r"(?:与此同时|因为|但是|但|而|其中|意味着|例如|包括)[，：；]?\s*$", paragraph):
                errors.append(f"{section_id} 第{index + 1}段以未完成连接语结束")
            fragments = [part.strip() for part in re.split(r"[。！？]", paragraph) if part.strip()]
            suspicious = {"引", "的", "有", "但", "而", "与", "和", "或", "并", "是", "为"}
            if any(re.sub(r"[^\u3400-\u9fff]", "", part) in suspicious for part in fragments):
                errors.append(f"{section_id} 第{index + 1}段含疑似残字或残句")
    if (is_v21 or is_v22 or is_v23) and visible.count("经营") > 2:
        errors.append("终稿中“经营”出现过多；仅可用于真实经商、创业或利润责任语境")
    sentences = [re.sub(r"[，；：、\s]", "", item) for item in re.split(r"[。！？]", visible) if len(re.findall(r"[\u3400-\u9fff]", item)) >= 12]
    duplicates = sorted({item for item in sentences if sentences.count(item) > 1})
    if (is_v21 or is_v22 or is_v23) and duplicates:
        errors.append("终稿跨章节重复完整句子，说明仍在套用模板")
    checks = review.get("checks", {})
    required = {"facts_preserved", "no_new_claims", "natural_chinese", "no_template_repetition", "calibration_hidden", "term_context_checked", "cross_section_repetition_checked", "calibration_dominance_checked", "emphasis_preserved", "domain_independence_checked", "mandatory_claims_preserved"} if is_v23 else {"facts_preserved", "no_new_claims", "natural_chinese", "no_template_repetition", "calibration_hidden", "term_context_checked", "cross_section_repetition_checked", "calibration_dominance_checked", "emphasis_preserved", "domain_independence_checked"} if is_v22 else {"facts_preserved", "no_new_claims", "natural_chinese", "no_template_repetition", "calibration_hidden", "term_context_checked", "cross_section_repetition_checked", "calibration_dominance_checked"} if is_v21 else {"facts_preserved", "no_new_claims", "natural_chinese", "no_template_repetition", "calibration_hidden"}
    if set(checks) != required or not all(checks.values()):
        errors.append("编辑记录必须完成对应版本的全部检查，并由实际文本与来源校验支持")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("review", type=Path)
    parser.add_argument("--draft", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        review = json.loads(args.review.read_text(encoding="utf-8"))
        draft = json.loads(args.draft.read_text(encoding="utf-8"))
        report = json.loads(args.report.read_text(encoding="utf-8"))
        errors = validate(review, draft, report)
    except (OSError, json.JSONDecodeError) as exc:
        errors = [str(exc)]
    print(json.dumps({"status": "ok" if not errors else "error", "errors": errors}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
