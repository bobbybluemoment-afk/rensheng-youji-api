#!/usr/bin/env python3
"""校验人物初稿的来源、篇幅和结构。"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

DIMENSIONS = ["self_growth", "love_partner", "career", "finance_resources", "body_emotion", "family_growth"]
REQUIRED_COVERAGE = {"feature", "behavior", "formation", "challenge", "current_change", "response"}
BANNED = {"组织化过劳型", "先扎根后显声", "表达窗口", "能力输出", "可见度", "物质与经营底色", "资源伴随期待", "表达被规训", "经营责任", "经营基础", "进入经营期", "经营底色", "经营扩张", "输出与经营"}
THIRD_PERSON = {"这个人", "命主", "本人"}
MINGLI_TERMS = {"命盘", "命局", "原局", "年柱", "月柱", "日柱", "时柱", "天干", "地支", "干支", "日主", "身强", "身弱", "比肩", "劫财", "食神", "伤官", "食伤", "正印", "偏印", "正财", "偏财", "正官", "七杀", "格局", "调候", "喜用", "忌神", "大运", "流年", "藏干", "透干", "根苗花果", "根气", "冲根", "引动"}


def cjk(value: Any) -> int:
    return len(re.findall(r"[\u3400-\u9fff]", str(value)))


def check_section(section: Any, minimum: int, maximum: int, where: str, errors: list[str], require_map: bool = True) -> set[str]:
    if not isinstance(section, dict):
        errors.append(f"{where} 必须是对象")
        return set()
    paragraphs = section.get("paragraphs")
    if not isinstance(paragraphs, list) or not 2 <= len(paragraphs) <= 4 or any(not isinstance(item, str) for item in paragraphs):
        errors.append(f"{where}.paragraphs 必须包含2—4个自然段")
    else:
        count = cjk("".join(paragraphs))
        if not minimum <= count <= maximum:
            errors.append(f"{where} 应为{minimum}—{maximum}个汉字，当前{count}")
        for index, paragraph in enumerate(paragraphs):
            sentences = [item for item in re.split(r"[。！？]", paragraph) if cjk(item)]
            if any(cjk(sentence) > 70 for sentence in sentences):
                errors.append(f"{where}.paragraphs[{index}] 存在超过70个汉字的长句")
            if re.search(r"(?:与此同时|因为|但是|但|而|其中|意味着|例如|包括)[，：；]?\s*$", paragraph):
                errors.append(f"{where}.paragraphs[{index}] 以未完成连接语结束")
            suspicious = {"引", "的", "有", "但", "而", "与", "和", "或", "并", "是", "为"}
            if any(re.sub(r"[^\u3400-\u9fff]", "", sentence) in suspicious for sentence in sentences):
                errors.append(f"{where}.paragraphs[{index}] 含疑似残字或残句")
    claim_ids = section.get("source_claim_ids")
    minimum_claims = 6 if require_map else 4
    if not isinstance(claim_ids, list) or len(set(claim_ids)) < minimum_claims:
        errors.append(f"{where} 至少引用{minimum_claims}个不同判断")
        return set()
    if require_map:
        paragraph_map = section.get("paragraph_claim_map")
        if not isinstance(paragraph_map, list) or len(paragraph_map) != len(paragraphs or []):
            errors.append(f"{where}.paragraph_claim_map 必须与自然段逐项对应")
        else:
            for index, mapped in enumerate(paragraph_map):
                if not isinstance(mapped, list) or len(set(mapped)) < 2:
                    errors.append(f"{where}.paragraph_claim_map[{index}] 至少包含两个不同Core判断")
                elif set(mapped) - set(claim_ids):
                    errors.append(f"{where}.paragraph_claim_map[{index}] 引用了本节未声明的判断")
    return set(claim_ids)


def check_emphasis(section: Any, brief_section: Any, minimum: int, maximum: int, where: str, errors: list[str]) -> None:
    if not isinstance(section, dict) or not isinstance(brief_section, dict):
        return
    paragraphs = section.get("paragraphs") or []
    paragraph_map = section.get("paragraph_claim_map") or []
    allowed = set(brief_section.get("emphasis_claim_ids") or [])
    spans = section.get("emphasis_spans")
    if not isinstance(spans, list) or not minimum <= len(spans) <= maximum:
        errors.append(f"{where}.emphasis_spans 必须包含{minimum}—{maximum}条重点判断")
        return
    seen_paragraphs: set[int] = set()
    for index, span in enumerate(spans):
        path = f"{where}.emphasis_spans[{index}]"
        if not isinstance(span, dict) or set(span) != {"paragraph_index", "text", "claim_ids"}:
            errors.append(f"{path} 结构无效")
            continue
        paragraph_index = span.get("paragraph_index")
        text = span.get("text")
        claims = span.get("claim_ids")
        if not isinstance(paragraph_index, int) or not 0 <= paragraph_index < len(paragraphs):
            errors.append(f"{path}.paragraph_index 无效")
            continue
        if paragraph_index in seen_paragraphs:
            errors.append(f"{where} 每个自然段最多一条重点判断")
        seen_paragraphs.add(paragraph_index)
        if not isinstance(text, str) or text not in paragraphs[paragraph_index] or not 16 <= cjk(text) <= 70 or "**" in text or not re.search(r"[。！？]$", text.strip()):
            errors.append(f"{path}.text 必须是正文中16—70字、带句末标点的完整纯文本判断句")
        mapped = set(paragraph_map[paragraph_index]) if paragraph_index < len(paragraph_map) and isinstance(paragraph_map[paragraph_index], list) else set()
        if not isinstance(claims, list) or not claims or len(set(claims)) > 3 or not set(claims).issubset(allowed & mapped):
            errors.append(f"{path}.claim_ids 必须来自本段映射和Core指定重点判断")


def validate(data: Any, brief: Any | None = None) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["报告初稿必须是对象"]
    for key in ("schema_version", "draft_id", "brief_id", "life_overview", "dimensions", "current_question"):
        if key not in data:
            errors.append(f"缺少字段：{key}")
    is_v11 = data.get("schema_version") == "1.1.0"
    is_v12 = data.get("schema_version") == "1.2.0"
    is_v13 = data.get("schema_version") == "1.3.0"
    is_traced = is_v11 or is_v12 or is_v13
    if data.get("schema_version") not in {"1.0.0", "1.1.0", "1.2.0", "1.3.0"}:
        errors.append("schema_version 必须为1.0.0、1.1.0、1.2.0或1.3.0")
    used = check_section(data.get("life_overview"), 500 if is_traced else 350, 700 if is_traced else 550, "life_overview", errors, is_traced)
    dimensions = data.get("dimensions")
    if not isinstance(dimensions, list) or [item.get("id") for item in dimensions if isinstance(item, dict)] != DIMENSIONS:
        errors.append("dimensions 必须按固定顺序完整包含六个领域")
    else:
        for item in dimensions:
            used |= check_section(item, 500 if is_traced else 380, 700 if is_traced else 650, f"dimensions.{item.get('id')}", errors, is_traced)
            if not REQUIRED_COVERAGE.issubset(set(item.get("coverage") or [])):
                errors.append(f"dimensions.{item.get('id')} 缺少人物描述覆盖项")
    current = data.get("current_question")
    if isinstance(current, dict):
        used |= check_section(current, 320 if is_traced else 280, 650 if is_traced else 600, "current_question", errors, is_traced)
    else:
        errors.append("current_question 必须是对象")
    visible = json.dumps(data, ensure_ascii=False)
    found = sorted(term for term in BANNED if term in visible)
    if found:
        errors.append("初稿含有生硬或生造表达：" + "、".join(found))
    mingli_found = sorted(term for term in MINGLI_TERMS if term in visible)
    if mingli_found:
        errors.append("初稿含用户不可见的内部命理术语：" + "、".join(mingli_found))
    third_person_found = sorted(term for term in THIRD_PERSON if term in visible)
    if re.search(r"(?<!其)[他她](?:会|更|通常|可能|容易|需要|倾向|在|的|也|并|则|不|是|有|能|要|把|与|从|对|遇|面对)", visible):
        third_person_found.append("他／她")
    if third_person_found:
        errors.append("用户可见初稿必须统一使用第二人称“你”，禁止出现：" + "、".join(third_person_found))
    if "校准后的现实线索" in visible or "校准确认" in visible:
        errors.append("初稿不得展示校准过程")
    if visible.count("经营") > 2:
        errors.append("初稿中“经营”出现过多；仅在真实经商、创业或利润责任语境使用")
    if brief is not None and isinstance(brief, dict):
        if data.get("brief_id") != brief.get("brief_id"):
            errors.append("初稿与事实提纲来源不一致")
        allowed: set[str] = set()
        for section in [brief.get("life_overview"), brief.get("current_question"), *(brief.get("dimensions") or [])]:
            if isinstance(section, dict):
                allowed.update(section.get("claim_ids") or [])
        if used - allowed:
            errors.append("初稿使用了事实提纲没有授权的判断")
        selected_payload = {
            item.get("claim_id")
            for section in [brief.get("life_overview"), brief.get("current_question"), *(brief.get("dimensions") or [])]
            if isinstance(section, dict)
            for item in (section.get("selected_claims") or [])
            if isinstance(item, dict)
        }
        if is_traced and used - selected_payload:
            errors.append("初稿引用的判断没有实体化Core内容，禁止只凭编号写作")
        if is_v12 or is_v13:
            for index, section in enumerate([brief.get("life_overview"), brief.get("current_question"), *(brief.get("dimensions") or [])]):
                if not isinstance(section, dict):
                    continue
                for required in ("selected_evidence", "selected_formation_chains", "selected_linkage_chains", "selected_reality_candidates", "selected_candidate_relations", "portrait_context", "calibration_context"):
                    if required not in section:
                        errors.append(f"事实提纲第{index + 1}区缺少{required}，写作不得继续")
        if is_v13:
            check_emphasis(data.get("life_overview"), brief.get("life_overview"), 0, 2, "life_overview", errors)
            check_emphasis(data.get("current_question"), brief.get("current_question"), 0, 1, "current_question", errors)
            brief_dimensions = {item.get("id"): item for item in brief.get("dimensions") or [] if isinstance(item, dict)}
            for section in data.get("dimensions") or []:
                if isinstance(section, dict):
                    brief_section = brief_dimensions.get(section.get("id"))
                    check_emphasis(section, brief_section, 0, 1, f"dimensions.{section.get('id')}", errors)
                    for key in ("domain_specific_claim_ids", "mainline_claim_ids", "domain_mechanisms", "survives_without_mainline"):
                        if not isinstance(brief_section, dict) or section.get(key) != brief_section.get(key):
                            errors.append(f"dimensions.{section.get('id')}.{key} 必须原样继承事实提纲")
            if "**" in json.dumps(data, ensure_ascii=False):
                errors.append("初稿正文必须保存纯文本；加粗只由emphasis_spans和渲染器生成")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("draft", type=Path)
    parser.add_argument("--brief", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.draft.read_text(encoding="utf-8"))
        brief = json.loads(args.brief.read_text(encoding="utf-8")) if args.brief else None
        errors = validate(data, brief)
    except (OSError, json.JSONDecodeError) as exc:
        errors = [str(exc)]
    print(json.dumps({"status": "ok" if not errors else "error", "errors": errors}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
