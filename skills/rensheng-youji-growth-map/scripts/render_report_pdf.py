#!/usr/bin/env python3
"""把已校验的正式报告和新版卡片确定性排成固定10页PDF。"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


SKILL_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = SKILL_ROOT.parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from render_report import DIMENSION_HEADINGS, DIMENSION_PARAGRAPHS, FIXED_REPORT_INTRO, cjk_count, validate  # noqa: E402


WIDTH, HEIGHT = 1240, 1754
MARGIN_X, TOP, BOTTOM = 88, 98, 92
BG = "#F6F0E5"
INK = "#303638"
TEAL = "#315B63"
GOLD = "#B89552"
PINK = "#D77F91"
MUTED = "#74736E"
LIGHT_TEAL = "#DDE8E5"
HEADING_FONT_PATH = REPO_ROOT / "assets/fonts/noto/NotoSansCJKsc-Regular.otf"
BODY_FONT_PATH = REPO_ROOT / "assets/fonts/lxgw/LXGWWenKai-Regular.ttf"
WECHAT_PATH = REPO_ROOT / "assets/wechat-contact.jpg"
LOGO_PATH = REPO_ROOT / "assets/rensheng-youji-logo.png"
ASSET_MANIFEST_PATH = REPO_ROOT / "assets/asset-manifest.json"
RENDER_STYLE = "primary"


def normalize_display_text(value: Any) -> str:
    text = str(value).translate(str.maketrans({"％": "%", "﹪": "%", "–": "-", "‑": "-"}))
    text = re.sub(r"(\d+(?:\.\d+)?)%\s*[—-]\s*(\d+(?:\.\d+)?)%", r"百分之\1到百分之\2", text)
    return re.sub(r"(\d+(?:\.\d+)?)%", r"百分之\1", text)


def year_story(item: dict[str, Any], index: int) -> str:
    """Join continuity fields without repeating the same label twenty times."""
    clean = lambda value: re.sub(r"[。！？；，：\s]+$", "", str(value).strip())
    carry = clean(item.get("carry_in", ""))
    signal = clean(item.get("real_world_signal", ""))
    seed = clean(item.get("seed_for_next", ""))
    patterns = (
        f"{carry}。这一年，{signal}。{seed}。",
        f"带着{carry}，{signal}。随后，{seed}。",
        f"{carry}会继续影响这一年。{signal}；{seed}。",
        f"这一年承接{carry}，主要表现为{signal}。最终，{seed}。",
    )
    return patterns[index % len(patterns)]


def canonical_wechat_asset() -> tuple[Path, str]:
    if not ASSET_MANIFEST_PATH.exists():
        raise ValueError("缺少正式资源清单 assets/asset-manifest.json")
    manifest = json.loads(ASSET_MANIFEST_PATH.read_text(encoding="utf-8"))
    expected = manifest.get("assets", {}).get("wechat_contact", {})
    if expected.get("path") != "assets/wechat-contact.jpg":
        raise ValueError("正式资源清单中的微信图片路径无效")
    if not WECHAT_PATH.exists():
        raise ValueError("缺少正式工作微信图片 assets/wechat-contact.jpg；禁止生成占位图")
    digest = hashlib.sha256(WECHAT_PATH.read_bytes()).hexdigest()
    if digest != expected.get("sha256"):
        raise ValueError("工作微信图片与正式资源清单不一致；禁止使用替代图或占位图")
    with Image.open(WECHAT_PATH) as source:
        if list(source.size) != [expected.get("width"), expected.get("height")]:
            raise ValueError("工作微信图片尺寸与正式资源清单不一致")
    return WECHAT_PATH, digest


def canonical_logo_asset() -> tuple[Path, str]:
    if not ASSET_MANIFEST_PATH.exists():
        raise ValueError("缺少正式资源清单 assets/asset-manifest.json")
    manifest = json.loads(ASSET_MANIFEST_PATH.read_text(encoding="utf-8"))
    expected = manifest.get("assets", {}).get("report_logo", {})
    if expected.get("path") != "assets/rensheng-youji-logo.png":
        raise ValueError("正式资源清单中的报告Logo路径无效")
    if not LOGO_PATH.exists():
        raise ValueError("缺少正式报告Logo assets/rensheng-youji-logo.png")
    digest = hashlib.sha256(LOGO_PATH.read_bytes()).hexdigest()
    if digest != expected.get("sha256"):
        raise ValueError("报告Logo与正式资源清单不一致")
    with Image.open(LOGO_PATH) as source:
        if list(source.size) != [expected.get("width"), expected.get("height")]:
            raise ValueError("报告Logo尺寸与正式资源清单不一致")
    return LOGO_PATH, digest


def canonical_body_font() -> tuple[Path, str]:
    if not ASSET_MANIFEST_PATH.exists():
        raise ValueError("缺少正式资源清单 assets/asset-manifest.json")
    manifest = json.loads(ASSET_MANIFEST_PATH.read_text(encoding="utf-8"))
    expected = manifest.get("assets", {}).get("report_body_font", {})
    if expected.get("path") != "assets/fonts/lxgw/LXGWWenKai-Regular.ttf":
        raise ValueError("正式资源清单中的报告正文字体路径无效")
    if not BODY_FONT_PATH.exists():
        raise ValueError("缺少正式报告正文字体 assets/fonts/lxgw/LXGWWenKai-Regular.ttf")
    digest = hashlib.sha256(BODY_FONT_PATH.read_bytes()).hexdigest()
    if digest != expected.get("sha256"):
        raise ValueError("报告正文字体与正式资源清单不一致")
    return BODY_FONT_PATH, digest


def font(size: int, *, role: str = "body") -> ImageFont.FreeTypeFont:
    path = HEADING_FONT_PATH if role == "heading" else BODY_FONT_PATH
    return ImageFont.truetype(str(path), size=size)


def wrap(draw: ImageDraw.ImageDraw, text: str, text_font: ImageFont.FreeTypeFont, width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in normalize_display_text(text).splitlines() or [""]:
        if not paragraph:
            lines.append("")
            continue
        current = ""
        for char in paragraph:
            candidate = current + char
            if current and draw.textlength(candidate, font=text_font) > width:
                if char in "，。！？；：、）》】」』”’":
                    lines.append(candidate.rstrip())
                    current = ""
                else:
                    lines.append(current.rstrip())
                    current = char.lstrip()
            else:
                current = candidate
        if current:
            lines.append(current.rstrip())
    return lines


class Page:
    def __init__(self, number: int, title: str, *, compact: bool = False) -> None:
        self.number = number
        self.image = Image.new("RGB", (WIDTH, HEIGHT), BG)
        self.draw = ImageDraw.Draw(self.image)
        self.y = TOP
        self.compact = compact
        self.overflow = False
        self.text_render_completed = True
        self.draw.rounded_rectangle((54, 40, WIDTH - 54, 70), 15, fill=TEAL)
        self.draw.text((MARGIN_X, 88), title, font=font(38, role="heading"), fill=TEAL)
        self.y = 158

    def heading(self, text: str, *, color: str = GOLD, size: int = 30) -> None:
        self._space(12)
        self.draw.text((MARGIN_X, self.y), text, font=font(size, role="heading"), fill=color)
        self.y += size + 20

    def paragraph(self, text: str, *, size: int | None = None, color: str = INK, gap: int = 14, indent: bool = False, bold: bool = False) -> None:
        size = size or (22 if self.compact else 26)
        text_font = font(size, role="heading" if bold else "body")
        value = ("　　" + text) if indent else text
        line_height = size + (8 if self.compact and size >= 23 else 11 if self.compact else 14)
        for line in wrap(self.draw, value, text_font, WIDTH - 2 * MARGIN_X):
            self._ensure(line_height)
            self.draw.text((MARGIN_X, self.y), line, font=text_font, fill=color)
            self.y += line_height
        self.y += gap

    def paragraph_emphasis(self, text: str, emphasis: str | None, *, size: int | None = None, gap: int = 14) -> None:
        """重点判断独立成行；稳定模式完全关闭重点样式，避免视觉增强阻塞交付。"""
        if not emphasis or RENDER_STYLE == "stable":
            self.paragraph(text, size=size, gap=gap)
            return
        size = size or (22 if self.compact else 26)
        value = normalize_display_text(text)
        target = normalize_display_text(emphasis)
        start = value.find(target)
        if start < 0:
            raise ValueError("重点句不是对应正文的精确子串")
        end = start + len(target)
        before, after = value[:start].strip(), value[end:].strip()
        if before:
            self.paragraph(before, size=size, gap=5)
        judgment_font = font(size, role="heading")
        lines = wrap(self.draw, target, judgment_font, WIDTH - 2 * MARGIN_X - 24)
        line_height = size + (9 if self.compact else 12)
        self._ensure(line_height * len(lines) + 10)
        top = self.y
        self.draw.rounded_rectangle((MARGIN_X, top + 2, MARGIN_X + 7, top + line_height * len(lines) - 3), 3, fill=TEAL)
        for line in lines:
            self.draw.text((MARGIN_X + 20, self.y), line, font=judgment_font, fill=TEAL)
            self.y += line_height
        self.y += 6
        if after:
            self.paragraph(after, size=size, gap=gap)
        else:
            self.y += max(0, gap - 6)

    def bullet(self, text: str, *, size: int | None = None, accent: str = GOLD) -> None:
        size = size or (22 if self.compact else 25)
        text_font = font(size)
        left = MARGIN_X + 30
        line_height = size + (10 if self.compact else 13)
        lines = wrap(self.draw, text, text_font, WIDTH - left - MARGIN_X)
        self._ensure(line_height * len(lines) + 10)
        self.draw.ellipse((MARGIN_X, self.y + 9, MARGIN_X + 11, self.y + 20), fill=accent)
        for line in lines:
            self.draw.text((left, self.y), line, font=text_font, fill=INK)
            self.y += line_height
        self.y += 8

    def label(self, label: str, text: str, *, size: int = 23) -> None:
        self.paragraph(f"{label}｜{text}", size=size, color=INK, gap=9)

    def divider(self) -> None:
        self._space(10)
        self.draw.line((MARGIN_X, self.y, WIDTH - MARGIN_X, self.y), fill=LIGHT_TEAL, width=3)
        self.y += 20

    def callout(self, label: str, text: str, *, size: int = 27, fill: str = "#E7EFEA") -> None:
        text_font = font(size)
        lines = wrap(self.draw, text, text_font, WIDTH - 2 * (MARGIN_X + 34))
        line_height = size + 14
        label_space = 62 if label else 25
        height = label_space + len(lines) * line_height + 24
        self._ensure(height)
        top = self.y
        self.draw.rounded_rectangle((MARGIN_X, top, WIDTH - MARGIN_X, top + height), 22, fill=fill)
        if label:
            self.draw.text((MARGIN_X + 30, top + 22), label, font=font(23, role="heading"), fill=TEAL)
        text_y = top + label_space
        for line in lines:
            self.draw.text((MARGIN_X + 30, text_y), line, font=text_font, fill=INK)
            text_y += line_height
        self.y = top + height + 18

    def _space(self, amount: int) -> None:
        self._ensure(amount)
        self.y += amount

    def _ensure(self, height: int) -> None:
        if self.y + height > HEIGHT - BOTTOM:
            self.overflow = True
            raise ValueError(f"第{self.number}页内容溢出；请按报告字段字数限制压缩正文")

    def finish(self) -> Image.Image:
        footer_y = HEIGHT - 62
        self.draw.line((MARGIN_X, footer_y - 18, WIDTH - MARGIN_X, footer_y - 18), fill="#D9D3C8", width=2)
        self.draw.text((MARGIN_X, footer_y), "人生有迹 by 景行", font=font(18), fill=MUTED)
        page_text = f"{self.number} / 10"
        self.draw.text((WIDTH - MARGIN_X - self.draw.textlength(page_text, font=font(18)), footer_y), page_text, font=font(18), fill=MUTED)
        self.image.info["overflow"] = self.overflow
        self.image.info["text_render_completed"] = self.text_render_completed
        self.image.info["max_content_y"] = self.y
        return self.image


def cover(data: dict[str, Any]) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((72, 62, WIDTH - 72, HEIGHT - 62), 32, outline=TEAL, width=4)
    draw.rectangle((72, 62, WIDTH - 72, 92), fill=TEAL)
    logo_path, _ = canonical_logo_asset()
    with Image.open(logo_path) as logo_source:
        logo = logo_source.convert("RGBA")
    corner = logo.getpixel((0, 0))[:3]
    pixels = []
    for red, green, blue, alpha in logo.getdata():
        distance = abs(red - corner[0]) + abs(green - corner[1]) + abs(blue - corner[2])
        pixels.append((red, green, blue, 0 if distance < 28 else alpha))
    logo.putdata(pixels)
    logo = logo.resize((270, 270), Image.Resampling.LANCZOS)
    image.paste(logo, ((WIDTH - logo.width) // 2, 135), logo)

    title_font = font(60, role="heading")
    title_x = (WIDTH - draw.textlength(data["title"], font=title_font)) / 2
    draw.text((title_x, 440), data["title"], font=title_font, fill=TEAL)
    subtitle_font = font(28)
    subtitle_x = (WIDTH - draw.textlength(data["subtitle"], font=subtitle_font)) / 2
    draw.text((subtitle_x, 535), data["subtitle"], font=subtitle_font, fill=GOLD)
    draw.line((190, 600, WIDTH - 190, 600), fill=GOLD, width=3)

    draw.rounded_rectangle((112, 665, WIDTH - 112, 1115), 28, fill="#E7EFEA")
    draw.text((154, 710), "关于这份报告", font=font(31, role="heading"), fill=TEAL)
    intro_y = 780
    for line in wrap(draw, FIXED_REPORT_INTRO, font(28), WIDTH - 308):
        draw.text((154, intro_y), line, font=font(28), fill=INK)
        intro_y += 46
    draw.rounded_rectangle((150, 1185, WIDTH - 150, 1285), 20, outline=GOLD, width=3)
    contact = "阅读后如果还有想继续了解的问题，请查看第10页联系方式。"
    contact_font = font(24)
    contact_x = (WIDTH - draw.textlength(contact, font=contact_font)) / 2
    draw.text((contact_x, 1218), contact, font=contact_font, fill=TEAL)
    name = data["profile"].get("name") or "专属"
    meta = f"{name}｜生成日期 {data['generated_on']}"
    meta_font = font(22)
    draw.text(((WIDTH - draw.textlength(meta, font=meta_font)) / 2, 1390), meta, font=meta_font, fill=MUTED)
    draw.text((112, HEIGHT - 150), "人生有迹 by 景行", font=font(25, role="heading"), fill=TEAL)
    draw.text((WIDTH - 180, HEIGHT - 150), "1 / 10", font=font(20), fill=MUTED)
    return image


def card_page(card_path: Path) -> Image.Image:
    page = Page(2, "人生主线卡片")
    with Image.open(card_path) as source:
        card = source.convert("RGB")
    if card.size != (1242, 1660):
        raise ValueError("报告必须嵌入1242×1660的新版人生卡片")
    max_w, max_h = WIDTH - 176, HEIGHT - 270
    scale = min(max_w / card.width, max_h / card.height)
    resized = card.resize((round(card.width * scale), round(card.height * scale)), Image.Resampling.LANCZOS)
    x = (WIDTH - resized.width) // 2
    y = 170
    page.image.paste(resized, (x, y))
    page.draw.rounded_rectangle((x - 3, y - 3, x + resized.width + 3, y + resized.height + 3), 8, outline=GOLD, width=3)
    return page.finish()


def page_three(data: dict[str, Any]) -> Image.Image:
    page = Page(3, "人生主线与能力")
    summary = data["executive_summary"]
    body_size = 23
    bullet_size = 22
    page.heading("完整人生主线", color=TEAL, size=32)
    if data.get("schema_version") in {"2.7.0", "2.8.0", "2.9.0", "2.10.0", "2.11.0", "2.12.0", "2.13.0", "2.14.0"}:
        spans = {item["paragraph_index"]: item["text"] for item in summary["life_overview"].get("emphasis_spans") or []}
        for index, paragraph in enumerate(summary["life_overview"]["paragraphs"]):
            page.paragraph_emphasis(paragraph, spans.get(index), size=body_size, gap=18)
        page.divider()
        page.heading("你已经带来的能力", size=29)
        for item in summary["capabilities_resources"]:
            page.bullet(item, size=bullet_size)
    else:
        page.callout("这条主线怎样贯穿不同阶段", summary["life_theme"], size=body_size)
        page.divider()
        page.heading("你已经带来的能力", size=31)
        for item in summary["capabilities_resources"]:
            page.bullet(item, size=bullet_size)
        page.divider()
        page.heading("这些方式怎样形成", color=TEAL, size=31)
        page.paragraph(summary["formation"], size=body_size, gap=20)
    return page.finish()


def page_four(data: dict[str, Any]) -> Image.Image:
    page = Page(4, "当前阶段与问题回应")
    summary, stage = data["executive_summary"], data["stage_story"]
    answer_size = 27
    label_size = 22
    page.paragraph("你想问｜" + data["profile"]["question"], size=26, color=PINK, gap=18)
    if data.get("schema_version") in {"2.7.0", "2.8.0", "2.9.0", "2.10.0", "2.11.0", "2.12.0", "2.13.0", "2.14.0"}:
        page.heading("对当前问题的直接回应", color=TEAL, size=29)
        current = data["current_question_narrative"]
        spans = {item["paragraph_index"]: item["text"] for item in current.get("emphasis_spans") or []}
        for index, paragraph in enumerate(current["paragraphs"]):
            page.paragraph_emphasis(paragraph, spans.get(index), size=22, gap=10)
    else:
        page.callout("对当前问题的直接回应", summary["direct_answer"], size=answer_size, fill="#F2E4E6")
    page.heading("阶段怎样一步步走到现在", color=TEAL, size=31)
    for label, key in [("上一阶段", "previous_foundation"), ("近几年", "recent_development"), ("现在", "present_task"), ("未来两三年", "next_direction"), ("更长阶段", "long_range")]:
        page.label(label, stage[key], size=label_size)
    return page.finish()


def dimensions_page(data: dict[str, Any], number: int, indexes: tuple[int, int]) -> Image.Image:
    page = Page(number, "六个现实领域", compact=True)
    for position, index in enumerate(indexes):
        section = data["dimensions"][index]
        block_top, block_bottom = ((172, 835), (850, 1584))[position]
        page.draw.rounded_rectangle(
            (MARGIN_X - 18, block_top, WIDTH - MARGIN_X + 18, block_bottom),
            24, fill="#FBF7EF", outline=LIGHT_TEAL, width=3,
        )
        page.y = block_top + 18
        page.draw.text((MARGIN_X, page.y), section["title"], font=font(28, role="heading"), fill=TEAL)
        page.y += 44
        if data.get("schema_version") in {"2.7.0", "2.8.0", "2.9.0", "2.10.0", "2.11.0", "2.12.0", "2.13.0", "2.14.0"}:
            spans = {item["paragraph_index"]: item["text"] for item in section.get("emphasis_spans") or []}
            for paragraph_index, paragraph in enumerate(section["paragraphs"]):
                page.paragraph_emphasis(paragraph, spans.get(paragraph_index), size=23 if data.get("schema_version") in {"2.10.0", "2.11.0", "2.12.0", "2.13.0", "2.14.0"} else 22, gap=8)
        else:
            page.callout("", section["overview"], size=22, fill="#E7EFEA")
            for key, heading in zip(DIMENSION_PARAGRAPHS[section["id"]], DIMENSION_HEADINGS[section["id"]]):
                page.draw.text((MARGIN_X, page.y), heading, font=font(19, role="heading"), fill=GOLD)
                page.y += 29
                page.paragraph(section["paragraphs"][key], size=20, gap=7)
        if page.y > block_bottom - 16:
            raise ValueError(f"第{number}页领域内容溢出；请压缩第{index + 1}个领域")
    return page.finish()


def years_page(data: dict[str, Any], number: int, start: int) -> Image.Image:
    page = Page(number, f"逐年观察｜{start + 1}—{start + 10}", compact=True)
    if start == 0:
        page.paragraph(data["yearly_outlook"]["summary"], size=18, color=TEAL, gap=8)
    for local_index, item in enumerate(data["yearly_outlook"]["years"][start:start + 10]):
        page._ensure(32)
        accent = PINK if item["key_year"] else GOLD
        marker = "重点年｜" if item["key_year"] else ""
        page.draw.text((MARGIN_X, page.y), f"{item['year']}｜{marker}{item['theme']}", font=font(20, role="heading"), fill=accent)
        page.y += 30
        story = year_story(item, start + local_index)
        page.paragraph(story, size=20, gap=3)
    return page.finish()


def final_page(data: dict[str, Any]) -> Image.Image:
    page = Page(10, "行动建议与联系方式", compact=True)
    guide = data["action_guide"]
    page.heading("现在最值得做的三件事", color=TEAL, size=28)
    for item in guide["priority_actions"]:
        page.bullet(item, size=21)
    page.paragraph("需要减少｜" + guide["reduce"], size=21, color=PINK)
    page.heading("仍需继续验证", size=26)
    for item in data["open_questions"]:
        page.bullet(item, size=20)
    page.heading("关于景行", color=TEAL, size=26)
    page.paragraph(data["author"]["bio"], size=20, gap=6)
    page.paragraph("GitHub｜" + data["author"]["github"], size=18, gap=4)
    page.paragraph("免费网页｜" + data["author"]["web"], size=18, gap=4)
    page.paragraph(data.get("assisted_service_note", ""), size=19, color=TEAL, gap=8)

    wechat_path, _ = canonical_wechat_asset()
    with Image.open(wechat_path) as qr_source:
        qr = qr_source.convert("RGB")
    qr.thumbnail((330, 420), Image.Resampling.LANCZOS)
    qr_x, qr_y = WIDTH - MARGIN_X - qr.width, min(page.y + 8, HEIGHT - BOTTOM - qr.height - 125)
    page.image.paste(qr, (qr_x, qr_y))
    page.draw.text((MARGIN_X, qr_y + 22), "工作微信", font=font(24, role="heading"), fill=TEAL)
    page.draw.text((MARGIN_X, qr_y + 66), data["author"]["wechat_note"], font=font(20), fill=INK)
    boundary_y = qr_y + qr.height + 20
    page.draw.text((MARGIN_X, boundary_y), "阅读边界", font=font(21, role="heading"), fill=GOLD)
    boundary_y += 38
    for item in data["boundaries"]:
        for line in wrap(page.draw, item, font(17), WIDTH - 2 * MARGIN_X):
            page.draw.text((MARGIN_X, boundary_y), line, font=font(17), fill=MUTED)
            boundary_y += 27
    if boundary_y > HEIGHT - BOTTOM:
        raise ValueError("第10页内容溢出")
    return page.finish()


def render_pdf(data: dict[str, Any], card_path: Path, output: Path, pages_dir: Path | None = None, style_mode: str = "primary") -> dict[str, Any]:
    global RENDER_STYLE
    if style_mode not in {"primary", "stable"}:
        raise ValueError("style_mode 必须是primary或stable")
    RENDER_STYLE = style_mode
    validate(data)
    if data["document_mode"] != "full_calibrated":
        raise ValueError("未完成五条校准时只生成初步分析，不生成正式PDF")
    _, wechat_sha256 = canonical_wechat_asset()
    _, logo_sha256 = canonical_logo_asset()
    _, body_font_sha256 = canonical_body_font()
    pages = [
        cover(data), card_page(card_path), page_three(data), page_four(data),
        dimensions_page(data, 5, (0, 1)), dimensions_page(data, 6, (2, 3)), dimensions_page(data, 7, (4, 5)),
        years_page(data, 8, 0), years_page(data, 9, 10), final_page(data),
    ]
    if len(pages) != 10:
        raise ValueError("PDF页数必须恰好为10页")
    overflow = any(bool(page.info.get("overflow", False)) for page in pages)
    text_render_completed = all(bool(page.info.get("text_render_completed", True)) for page in pages)
    if overflow or not text_render_completed:
        raise ValueError("PDF渲染完整性检查未通过")
    if pages_dir:
        pages_dir.mkdir(parents=True, exist_ok=True)
        for index, image in enumerate(pages, start=1):
            image.save(pages_dir / f"page-{index:02d}.png", format="PNG")
    output.parent.mkdir(parents=True, exist_ok=True)
    pages[0].save(output, format="PDF", save_all=True, append_images=pages[1:], resolution=150.0, quality=92)
    return {"pages": 10, "page_size": [WIDTH, HEIGHT], "card_size": [1242, 1660], "wechat_embedded": True, "wechat_asset": "assets/wechat-contact.jpg", "wechat_sha256": wechat_sha256, "logo_embedded": True, "logo_asset": "assets/rensheng-youji-logo.png", "logo_sha256": logo_sha256, "body_font": "assets/fonts/lxgw/LXGWWenKai-Regular.ttf", "body_font_sha256": body_font_sha256, "render_mode": style_mode, "overflow": overflow, "text_render_completed": text_render_completed}


def main() -> int:
    parser = argparse.ArgumentParser(description="生成固定10页人生有迹完整报告PDF")
    parser.add_argument("input", type=Path, help="已校验 report.json")
    parser.add_argument("--card", type=Path, required=True, help="新版1242×1660人生卡片PNG")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--pages-dir", type=Path)
    parser.add_argument("--style-mode", choices=("primary", "stable"), default="primary")
    args = parser.parse_args()
    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
        result = render_pdf(data, args.card, args.out, args.pages_dir, args.style_mode)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "ok", "output": str(args.out), **result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
