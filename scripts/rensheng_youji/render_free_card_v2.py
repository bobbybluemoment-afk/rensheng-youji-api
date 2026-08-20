"""用 Pillow 渲染 1242×1660 人生有迹新版免费卡片。"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
W, H = 1242, 1660
FONT = ROOT / "assets/fonts/noto/NotoSansCJKsc-Regular.otf"

C = {
    "bg": "#F6F0E5", "ink": "#303638", "muted": "#74786F", "teal": "#315B63",
    "coral": "#B96545", "gold": "#B89552", "panel": "#FBF8F0", "grid": "#D8CFC0",
    "border": "#CEC4B4", "peach": "#D77F91", "branch": "#765D4D",
    "ingot": "#F4C542", "ingot_hi": "#FFE78A", "ingot_stroke": "#C38712",
}

PLOT_X, PLOT_RIGHT = 190, 1140
STEP = (PLOT_RIGHT - PLOT_X) / 20


def _font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT), size)


def _x(index: int) -> float:
    return PLOT_X + STEP * (index + 0.5)


def _wrap(text: str, max_chars: int, max_lines: int) -> list[str]:
    raw = str(text or "").strip()
    lines: list[str] = []
    cursor = 0
    punctuation = "，。；：、？"
    while cursor < len(raw) and len(lines) < max_lines:
        end = min(cursor + max_chars, len(raw))
        if end < len(raw):
            candidates = [raw.rfind(mark, cursor, end + 1) for mark in punctuation]
            punct = max(candidates)
            if punct >= cursor + int(max_chars * 0.62):
                end = punct + 1
        lines.append(raw[cursor:end])
        cursor = end
    if cursor < len(raw) and lines:
        lines[-1] = lines[-1][:-1] + "…"
    return lines


def _text_lines(draw: ImageDraw.ImageDraw, lines: Iterable[str], xy: tuple[int, int], size: int,
                fill: str, line_height: int, anchor: str = "ls") -> None:
    x, y = xy
    fnt = _font(size)
    for index, line in enumerate(lines):
        draw.text((x, y + index * line_height), line, font=fnt, fill=fill, anchor=anchor)


def _validate(data: dict) -> tuple[list[dict], int]:
    years = data["trend_panel"]["years"]
    if len(years) != 20:
        raise ValueError("trend_panel.years 必须为20年")
    current = next((i for i, item in enumerate(years) if item.get("is_current")), -1)
    if current != 5:
        raise ValueError("当前年必须位于第6个位置")
    for index, item in enumerate(years):
        if index and item["year"] != years[index - 1]["year"] + 1:
            raise ValueError("20个年份必须连续")
        wealth = item["wealth"]
        if wealth["display_ingot_count"] != 2 * wealth["ingot_count"] - 2:
            raise ValueError(f'{item["year"]} 元宝显示尺度不一致')
        if item["peach"]["blossoms"] not in (0, 1, 3, 5, 7):
            raise ValueError(f'{item["year"]} 桃花朵数无效')
    return years, current


def _quad(draw: ImageDraw.ImageDraw, p0, p1, p2, fill: str, width: int) -> None:
    points = []
    for i in range(25):
        t = i / 24
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1]
        points.append((x, y))
    draw.line(points, fill=fill, width=width, joint="curve")


def _blossom(draw: ImageDraw.ImageDraw, cx: float, cy: float, r: float) -> None:
    for i in range(5):
        angle = math.radians(-90 + i * 72)
        px = cx + math.cos(angle) * r * 0.82
        py = cy + math.sin(angle) * r * 0.82
        pr = r * 0.58
        draw.ellipse((px - pr, py - pr, px + pr, py + pr), fill=C["peach"])
    cr = r * 0.30
    draw.ellipse((cx - cr, cy - cr, cx + cr, cy + cr), fill="#F3C96A")


def _ingot(draw: ImageDraw.ImageDraw, cx: float, cy: float, scale: float = 0.62) -> None:
    points = [
        (cx - 9 * scale, cy + 1 * scale), (cx - 6 * scale, cy - 4 * scale),
        (cx - 3 * scale, cy - 2.6 * scale), (cx, cy - 8 * scale),
        (cx + 3 * scale, cy - 2.6 * scale), (cx + 6 * scale, cy - 4 * scale),
        (cx + 9 * scale, cy + 1 * scale), (cx + 6 * scale, cy + 6 * scale),
        (cx, cy + 7.6 * scale), (cx - 6 * scale, cy + 6 * scale),
    ]
    draw.polygon(points, fill=C["ingot"], outline=C["ingot_stroke"])
    rx, ry = 3.5 * scale, 1.8 * scale
    draw.ellipse((cx - rx, cy + 1.2 * scale - ry, cx + rx, cy + 1.2 * scale + ry),
                 fill=C["ingot_hi"], outline=C["ingot_stroke"])


def render_free_card(data: dict, output: Path) -> Path:
    years, current = _validate(data)
    image = Image.new("RGB", (W, H), C["bg"])
    draw = ImageDraw.Draw(image)

    # Header
    _quad(draw, (72, 96), (94, 46), (184, 82), C["teal"], 4)
    draw.ellipse((153, 80, 167, 94), fill=C["teal"])
    draw.text((204, 78), "人生有迹", font=_font(34), fill=C["ink"], anchor="ls")
    draw.text((204, 106), "看见你反复走的人生轨迹", font=_font(17), fill=C["muted"], anchor="ls")
    identity = data["identity"]
    birth = identity["birth_text"].split("（", 1)[0]
    case_text = f'{birth} · {identity["birthplace"]} · {identity["gender_label"]}'
    draw.text((1170, 70), case_text, font=_font(17), fill=C["muted"], anchor="rs")
    draw.text((1170, 98), "免费体验卡 · 20年趋势", font=_font(13), fill=C["muted"], anchor="rs")
    draw.line((72, 139, 1170, 139), fill=C["border"], width=1)

    # 命局分析
    draw.rounded_rectangle((72, 164, 1170, 434), radius=16, fill=C["panel"], outline=C["border"])
    mingju = data["mingju_analysis"]
    draw.text((100, 210), "命局分析", font=_font(22), fill=C["teal"], anchor="ls", stroke_width=0)
    draw.text((100, 260), "　".join(mingju["pillars"]), font=_font(38), fill=C["ink"], anchor="ls")
    _text_lines(draw, _wrap(mingju["structure_text"], 47, 2), (100, 304), 17, C["ink"], 29)
    draw.line((100, 360, 1140, 360), fill=C["border"], width=1)
    _text_lines(draw, _wrap("人生主线：" + mingju["life_theme_text"], 46, 2), (100, 397), 20, C["teal"], 29)

    # 行情盘标题与容器
    draw.text((72, 486), "你的20年人生行情盘", font=_font(35), fill=C["ink"], anchor="ls")
    draw.text((1170, 482), "过去5年＋当前年＋未来14年", font=_font(17), fill=C["muted"], anchor="rs")
    draw.rounded_rectangle((72, 510, 1170, 1350), radius=18, fill=C["panel"], outline=C["border"])
    for y_line in (811, 982, 1154, 1282):
        draw.line((86, y_line, 1156, y_line), fill=C["grid"], width=1)
    labels = [(594, "综合", "人生K线"), (874, "事业", "步步高升"),
              (1025, "财运", "元宝积累"), (1200, "桃花", "关系花期")]
    for y_label, title, sub in labels:
        draw.text((92, y_label), title, font=_font(21), fill=C["ink"], anchor="ls")
        draw.text((92, y_label + 30), sub, font=_font(14), fill=C["muted"], anchor="ls")

    # K线
    top, chart_h = 550, 236
    lows = [item["life_kline"]["low"] for item in years]
    highs = [item["life_kline"]["high"] for item in years]
    raw_span = max(highs) - min(lows)
    padding = max(2, raw_span * 0.12)
    min_tick = math.floor((min(lows) - padding) / 5) * 5
    max_tick = math.ceil((max(highs) + padding) / 5) * 5
    if max_tick - min_tick < 20:
        center = (max_tick + min_tick) / 2
        min_tick = math.floor((center - 10) / 5) * 5
        max_tick = min_tick + 20

    def ky(value: float) -> float:
        return top + chart_h - (value - min_tick) / (max_tick - min_tick) * chart_h

    for tick in range(min_tick, max_tick + 1, 5):
        y_tick = ky(tick)
        for gx in range(PLOT_X, PLOT_RIGHT, 9):
            draw.line((gx, y_tick, min(gx + 3, PLOT_RIGHT), y_tick), fill=C["grid"], width=1)
        draw.text((1162, y_tick), str(tick), font=_font(13), fill=C["muted"], anchor="lm")
    for index in range(19):
        draw.line((_x(index) + 6.5, ky(years[index]["life_kline"]["close"]),
                   _x(index + 1) - 6.5, ky(years[index + 1]["life_kline"]["open"])),
                  fill="#A9AAA4", width=1)
    for index, item in enumerate(years):
        candle = item["life_kline"]
        up = candle["close"] >= candle["open"]
        color = C["gold"] if index == current else (C["coral"] if up else C["teal"])
        cx = _x(index)
        draw.line((cx, ky(candle["high"]), cx, ky(candle["low"])), fill=color, width=3)
        body_top = ky(max(candle["open"], candle["close"]))
        body_bottom = ky(min(candle["open"], candle["close"]))
        if body_bottom - body_top < 6:
            body_bottom = body_top + 6
        draw.rounded_rectangle((cx - 6, body_top, cx + 6, body_bottom), radius=2,
                               fill=color if up else C["panel"], outline=color, width=2)

    # 事业台阶与当前年小人
    def career_y(level: float) -> float:
        return 963 - (level - 1) / 8 * 112

    for index, item in enumerate(years):
        cy = career_y(item["career"]["level"])
        color = C["gold"] if index == current else C["teal"]
        draw.rounded_rectangle((_x(index) - 15, cy - 3, _x(index) + 15, cy + 12),
                               radius=3, fill=C["panel"], outline=color, width=2)
    avatar_x, avatar_y = _x(current), career_y(years[current]["career"]["level"]) - 7
    avatar = "#6E748D"
    draw.ellipse((avatar_x - 7, avatar_y - 27, avatar_x + 7, avatar_y - 13),
                 fill="#FFF7E6", outline=avatar, width=3)
    draw.line((avatar_x, avatar_y - 12, avatar_x - 2, avatar_y - 3, avatar_x + 1, avatar_y + 5), fill=avatar, width=3)
    draw.line((avatar_x - 1, avatar_y - 7, avatar_x - 12, avatar_y + 2), fill=avatar, width=3)
    draw.line((avatar_x - 1, avatar_y - 7, avatar_x + 11, avatar_y - 16), fill=avatar, width=3)
    draw.line((avatar_x + 1, avatar_y + 5, avatar_x - 9, avatar_y + 14), fill=avatar, width=3)
    draw.line((avatar_x + 1, avatar_y + 5, avatar_x + 10, avatar_y + 13), fill=avatar, width=3)

    # 财运连续元宝堆：先画完整元宝层，再用年度高度多边形裁切。
    wealth_base = 1138
    counts = [item["wealth"]["display_ingot_count"] for item in years]

    def wealth_top(count: int) -> float:
        return wealth_base - 30 - ((count - 4) / 18) * 115

    mask = Image.new("L", (W, H), 0)
    mask_draw = ImageDraw.Draw(mask)
    area = [(PLOT_X, wealth_base), (PLOT_X, wealth_top(counts[0]))]
    area.extend((_x(i), wealth_top(count)) for i, count in enumerate(counts))
    area.extend([(PLOT_RIGHT, wealth_top(counts[-1])), (PLOT_RIGHT, wealth_base)])
    mask_draw.polygon(area, fill=255)
    ingot_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ingot_draw = ImageDraw.Draw(ingot_layer)
    for row in range(13):
        cy = wealth_base - 6 - row * 10.5
        shift = 8 if row % 2 else 0
        cx = PLOT_X - 7 + shift
        while cx < PLOT_RIGHT + 12:
            _ingot(ingot_draw, cx, cy)
            cx += 16
    image.paste(ingot_layer, (0, 0), Image.composite(ingot_layer.getchannel("A"), Image.new("L", (W, H), 0), mask))
    draw = ImageDraw.Draw(image)

    # 桃花枝
    positions = [(-22, -51), (22, -66), (-5, -67), (24, -48), (-3, -39), (10, -56), (-18, -66)]
    for index, item in enumerate(years):
        if not item["peach"]["highlight"]:
            continue
        cx, base = _x(index), 1264
        _quad(draw, (cx - 22, base), (cx - 6, base - 20), (cx, base - 43), C["branch"], 3)
        _quad(draw, (cx, base - 43), (cx + 5, base - 58), (cx + 23, base - 69), C["branch"], 3)
        _quad(draw, (cx - 3, base - 34), (cx - 19, base - 41), (cx - 23, base - 53), C["branch"], 3)
        _quad(draw, (cx + 4, base - 50), (cx + 18, base - 48), (cx + 25, base - 59), C["branch"], 3)
        for blossom_index, (dx, dy) in enumerate(positions[:item["peach"]["blossoms"]]):
            _blossom(draw, cx + dx, base + dy, 5.4 + (blossom_index % 2) * 0.5)

    # 年份与说明
    for index, item in enumerate(years):
        if index % 2 and index != current:
            continue
        color = C["gold"] if index == current else C["muted"]
        draw.text((_x(index), 1310), str(item["year"])[-2:], font=_font(13), fill=color, anchor="ms")
    draw.text((190, 1335), "元宝堆积＝资源积累与留存条件　·　桃花枝＝只标记明显关系机会　·　均不代表金额、人数或事件保证",
              font=_font(13), fill=C["muted"], anchor="ls")

    # 当前课题与页脚
    draw.rounded_rectangle((72, 1372, 1170, 1582), radius=16, fill="#ECE5D8", outline=C["border"])
    issue = data["current_issue"]
    draw.text((100, 1415), "当前课题 · " + issue["title"], font=_font(18), fill=C["coral"], anchor="ls")
    _text_lines(draw, _wrap(issue["body"], 39, 2), (100, 1460), 25, C["ink"], 39)
    _text_lines(draw, _wrap(issue["example"], 56, 1), (100, 1548), 17, C["muted"], 25)
    draw.text((72, 1624), "想看更长时间？完整版将展开逐年伏笔与事业、财务、关系之间的传导",
              font=_font(13), fill=C["muted"], anchor="ls")
    draw.text((1170, 1624), "人生有迹 by 景行", font=_font(13), fill=C["muted"], anchor="rs")

    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, "PNG", optimize=True)
    return output
