#!/usr/bin/env python3
"""把已校验的正式报告和新版卡片确定性排成固定10页PDF。"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


SKILL_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = SKILL_ROOT.parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from render_report import specific_lines, validate  # noqa: E402


WIDTH, HEIGHT = 1240, 1754
MARGIN_X, TOP, BOTTOM = 88, 98, 92
BG = "#F6F0E5"
INK = "#303638"
TEAL = "#315B63"
GOLD = "#B89552"
PINK = "#D77F91"
MUTED = "#74736E"
LIGHT_TEAL = "#DDE8E5"
FONT_PATH = REPO_ROOT / "assets/fonts/noto/NotoSansCJKsc-Regular.otf"
WECHAT_PATH = REPO_ROOT / "assets/wechat-contact.jpg"
ASSET_MANIFEST_PATH = REPO_ROOT / "assets/asset-manifest.json"


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


def font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_PATH), size=size)


def wrap(draw: ImageDraw.ImageDraw, text: str, text_font: ImageFont.FreeTypeFont, width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in str(text).splitlines() or [""]:
        if not paragraph:
            lines.append("")
            continue
        current = ""
        for char in paragraph:
            candidate = current + char
            if current and draw.textlength(candidate, font=text_font) > width:
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
        self.draw.rounded_rectangle((54, 40, WIDTH - 54, 70), 15, fill=TEAL)
        self.draw.text((MARGIN_X, 88), title, font=font(38), fill=TEAL, stroke_width=1)
        self.y = 158

    def heading(self, text: str, *, color: str = GOLD, size: int = 30) -> None:
        self._space(12)
        self.draw.text((MARGIN_X, self.y), text, font=font(size), fill=color, stroke_width=1)
        self.y += size + 20

    def paragraph(self, text: str, *, size: int | None = None, color: str = INK, gap: int = 14, indent: bool = False) -> None:
        size = size or (22 if self.compact else 26)
        text_font = font(size)
        value = ("　　" + text) if indent else text
        line_height = size + (11 if self.compact else 14)
        for line in wrap(self.draw, value, text_font, WIDTH - 2 * MARGIN_X):
            self._ensure(line_height)
            self.draw.text((MARGIN_X, self.y), line, font=text_font, fill=color)
            self.y += line_height
        self.y += gap

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

    def _space(self, amount: int) -> None:
        self._ensure(amount)
        self.y += amount

    def _ensure(self, height: int) -> None:
        if self.y + height > HEIGHT - BOTTOM:
            raise ValueError(f"第{self.number}页内容溢出；请按报告字段字数限制压缩正文")

    def finish(self) -> Image.Image:
        footer_y = HEIGHT - 62
        self.draw.line((MARGIN_X, footer_y - 18, WIDTH - MARGIN_X, footer_y - 18), fill="#D9D3C8", width=2)
        self.draw.text((MARGIN_X, footer_y), "人生有迹 by 景行", font=font(18), fill=MUTED)
        page_text = f"{self.number} / 10"
        self.draw.text((WIDTH - MARGIN_X - self.draw.textlength(page_text, font=font(18)), footer_y), page_text, font=font(18), fill=MUTED)
        return self.image


def cover(data: dict[str, Any]) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((72, 62, WIDTH - 72, HEIGHT - 62), 32, outline=TEAL, width=4)
    draw.rectangle((72, 62, WIDTH - 72, 92), fill=TEAL)
    draw.text((112, 210), data["title"], font=font(64), fill=TEAL, stroke_width=1)
    name = data["profile"].get("name") or "专属"
    draw.text((112, 325), f"{name}的人生主线与阶段观察", font=font(34), fill=GOLD)
    draw.line((112, 405, WIDTH - 112, 405), fill=GOLD, width=4)
    draw.text((112, 470), "人生主线", font=font(28), fill=MUTED)
    y = 530
    body_font = font(34)
    for line in wrap(draw, data["executive_summary"]["life_theme"], body_font, WIDTH - 224):
        draw.text((112, y), line, font=body_font, fill=INK)
        y += 54
    y += 30
    draw.rounded_rectangle((104, y, WIDTH - 104, y + 250), 24, fill="#E7EFEA")
    draw.text((134, y + 26), "当前最需要处理", font=font(27), fill=TEAL, stroke_width=1)
    body_y = y + 80
    for line in wrap(draw, data["executive_summary"]["current_situation"], font(29), WIDTH - 268):
        draw.text((134, body_y), line, font=font(29), fill=INK)
        body_y += 46
    chart = data["chart"]
    profile = data["profile"]
    info_y = 1240
    for label, value in [
        ("出生", f"{profile['birth']}　{profile['location']}"),
        ("四柱", "　".join(chart["pillars"])),
        ("关注", profile["focus"]),
        ("生成", data["generated_on"]),
    ]:
        draw.text((112, info_y), label, font=font(22), fill=MUTED)
        value_lines = wrap(draw, value, font(24), WIDTH - 332)
        for line_index, line in enumerate(value_lines):
            draw.text((220, info_y + line_index * 38), line, font=font(24), fill=INK)
        info_y += max(52, len(value_lines) * 38 + 10)
    draw.text((112, HEIGHT - 150), "人生有迹 by 景行", font=font(25), fill=TEAL)
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
    page = Page(3, "能力、资源与形成过程")
    summary = data["executive_summary"]
    page.heading("你已经带来的能力")
    for item in summary["capabilities_resources"]:
        page.bullet(item)
    page.divider()
    page.heading("这些方式怎样形成", color=TEAL)
    page.paragraph(summary["formation"], indent=True)
    page.heading("校准后的现实线索", color=PINK)
    calibration = data["calibration"]
    for item in (calibration["confirmed"] + calibration["partial"])[:4]:
        page.bullet(item, accent=PINK)
    return page.finish()


def page_four(data: dict[str, Any]) -> Image.Image:
    page = Page(4, "当前阶段与问题回应")
    summary, stage = data["executive_summary"], data["stage_story"]
    page.paragraph("你想问｜" + data["profile"]["question"], size=24, color=PINK)
    page.heading("对当前问题的直接回应")
    page.paragraph(summary["direct_answer"], size=29)
    page.heading("阶段怎样一步步走到现在", color=TEAL)
    for label, key in [("上一阶段", "previous_foundation"), ("近几年", "recent_development"), ("现在", "present_task"), ("未来两三年", "next_direction"), ("更长阶段", "long_range")]:
        page.label(label, stage[key])
    return page.finish()


def dimensions_page(data: dict[str, Any], number: int, indexes: tuple[int, int]) -> Image.Image:
    page = Page(number, "六个现实领域", compact=True)
    for position, index in enumerate(indexes):
        section = data["dimensions"][index]
        page.heading(section["title"], color=TEAL, size=28)
        page.paragraph("核心判断｜" + section["finding"], size=23, color=INK, gap=9)
        for item in specific_lines(section):
            page.bullet(item, size=18, accent=PINK if index == 1 else GOLD)
        for paragraph in section["analysis"]:
            page.paragraph(paragraph, size=21, gap=10, indent=True)
        page.paragraph("现阶段重点｜" + section["current_focus"], size=21, color=TEAL, gap=8)
        page.paragraph("可以尝试｜" + "；".join(section["suggestions"]), size=21, gap=8)
        if position == 0:
            page.divider()
    return page.finish()


def years_page(data: dict[str, Any], number: int, start: int) -> Image.Image:
    page = Page(number, f"逐年观察｜{start + 1}—{start + 10}", compact=True)
    if start == 0:
        page.paragraph(data["yearly_outlook"]["summary"], size=18, color=TEAL, gap=8)
    for item in data["yearly_outlook"]["years"][start:start + 10]:
        page._ensure(32)
        page.draw.text((MARGIN_X, page.y), f"{item['year']}｜{item['theme']}", font=font(20), fill=GOLD, stroke_width=1)
        page.y += 30
        story = f"带入：{item['carry_in']}。可能表现：{item['likely_expression']}。留下：{item['seed_for_next']}。"
        page.paragraph(story, size=16, gap=3)
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
    page.draw.text((MARGIN_X, qr_y + 22), "工作微信", font=font(24), fill=TEAL, stroke_width=1)
    page.draw.text((MARGIN_X, qr_y + 66), data["author"]["wechat_note"], font=font(20), fill=INK)
    boundary_y = qr_y + qr.height + 20
    page.draw.text((MARGIN_X, boundary_y), "阅读边界", font=font(21), fill=GOLD, stroke_width=1)
    boundary_y += 38
    for item in data["boundaries"]:
        for line in wrap(page.draw, item, font(17), WIDTH - 2 * MARGIN_X):
            page.draw.text((MARGIN_X, boundary_y), line, font=font(17), fill=MUTED)
            boundary_y += 27
    if boundary_y > HEIGHT - BOTTOM:
        raise ValueError("第10页内容溢出")
    return page.finish()


def render_pdf(data: dict[str, Any], card_path: Path, output: Path, pages_dir: Path | None = None) -> dict[str, Any]:
    validate(data)
    if data["document_mode"] != "full_calibrated":
        raise ValueError("未完成五条校准时只生成初步分析，不生成正式PDF")
    _, wechat_sha256 = canonical_wechat_asset()
    pages = [
        cover(data), card_page(card_path), page_three(data), page_four(data),
        dimensions_page(data, 5, (0, 1)), dimensions_page(data, 6, (2, 3)), dimensions_page(data, 7, (4, 5)),
        years_page(data, 8, 0), years_page(data, 9, 10), final_page(data),
    ]
    if len(pages) != 10:
        raise ValueError("PDF页数必须恰好为10页")
    if pages_dir:
        pages_dir.mkdir(parents=True, exist_ok=True)
        for index, image in enumerate(pages, start=1):
            image.save(pages_dir / f"page-{index:02d}.png", format="PNG")
    output.parent.mkdir(parents=True, exist_ok=True)
    pages[0].save(output, format="PDF", save_all=True, append_images=pages[1:], resolution=150.0, quality=92)
    return {"pages": 10, "page_size": [WIDTH, HEIGHT], "card_size": [1242, 1660], "wechat_embedded": True, "wechat_asset": "assets/wechat-contact.jpg", "wechat_sha256": wechat_sha256}


def main() -> int:
    parser = argparse.ArgumentParser(description="生成固定10页人生有迹完整报告PDF")
    parser.add_argument("input", type=Path, help="已校验 report.json")
    parser.add_argument("--card", type=Path, required=True, help="新版1242×1660人生卡片PNG")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--pages-dir", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
        result = render_pdf(data, args.card, args.out, args.pages_dir)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "ok", "output": str(args.out), **result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
