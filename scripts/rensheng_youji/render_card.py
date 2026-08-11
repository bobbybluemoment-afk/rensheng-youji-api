"""渲染 1242×1660 人生有迹免费卡片。"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
W, H = 1242, 1660
BG, INK, MUTED = "#F4F0E6", "#26312D", "#59635E"
GREEN, RULE, VERMILION = "#627B6B", "#C8CEC3", "#C96855"
GOLD, PALE_GREEN, PALE_GOLD = "#B89552", "#E6EBE3", "#EEE7D7"
TREND = "#A9823B"
ISSUE_BLUE, ISSUE_BLUE_MUTED, PALE_BLUE = "#3F6072", "#607D8A", "#E5ECEE"
SECTION_X = 90
SECTION_TITLE_SIZE = 32
SECTION_TITLE_TRACKING = 3
BODY_SIZE = 29
BODY_LINE_HEIGHT = 43
TITLE_BODY_GAP = 48
SECTION_GAP = 42
FONT_DIR = ROOT / "assets/fonts/noto"
REGULAR = FONT_DIR / "NotoSansCJKsc-Regular.otf"
MEDIUM = REGULAR


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size)


def draw_tracking(draw, xy, text, fnt, fill, tracking):
    x, y = xy
    for char in text:
        draw.text((x, y), char, font=fnt, fill=fill, anchor="la")
        x += draw.textlength(char, font=fnt) + tracking


def draw_wenkai(draw, xy, text, size, fill, tracking=1):
    x, y = xy
    # 免费公开包使用一套完整中文字体，避免不同运行环境出现缺字方框。
    wenkai = font(REGULAR, size)
    for char in text:
        draw.text((x, y), char, font=wenkai, fill=fill, anchor="la")
        x += draw.textlength(char, font=wenkai) + tracking
    return x


def draw_section_title(draw, y, text):
    draw_wenkai(draw, (SECTION_X, y), text, SECTION_TITLE_SIZE, GREEN, SECTION_TITLE_TRACKING)


def draw_body_lines(draw, y, lines):
    body_font = font(REGULAR, BODY_SIZE)
    for index, line in enumerate(lines):
        draw.text((SECTION_X, y + index * BODY_LINE_HEIGHT), line, font=body_font, fill=INK, anchor="la")
    return y + (len(lines) - 1) * BODY_LINE_HEIGHT + BODY_SIZE


def draw_text_section(draw, y, title, lines):
    draw_section_title(draw, y, title)
    return draw_body_lines(draw, y + TITLE_BODY_GAP, lines)


def wrap(draw, text, fnt, max_width, max_lines=2):
    if max_lines == 2 and draw.textlength(text, font=fnt) > max_width:
        closing = set("，。！？；：、）》】”’")
        opening = set("《【“‘（")
        candidates = []
        for index in range(1, len(text)):
            left, right = text[:index], text[index:]
            left_width = draw.textlength(left, font=fnt)
            right_width = draw.textlength(right, font=fnt)
            if left_width <= max_width and right_width <= max_width:
                penalty = abs(left_width - right_width)
                if right[0] in closing or left[-1] in opening:
                    penalty += max_width
                candidates.append((penalty, left, right))
        if candidates:
            _, left, right = min(candidates, key=lambda item: item[0])
            return [left, right]

    lines, current = [], ""
    for char in text:
        trial = current + char
        if current and draw.textlength(trial, font=fnt) > max_width:
            lines.append(current)
            current = char
            if len(lines) == max_lines - 1:
                break
        else:
            current = trial
    consumed = sum(len(line) for line in lines)
    rest = text[consumed:]
    if len(lines) < max_lines and rest:
        current = ""
        for char in rest:
            if draw.textlength(current + char, font=fnt) <= max_width:
                current += char
        lines.append(current)
    return lines[:max_lines]


def _validate(data):
    pillars = data["pillars"]
    if len(pillars) != 4:
        raise ValueError("pillars must contain exactly four values")
    timeline = data.get("timeline", [])
    if len(timeline) != 20:
        raise ValueError("timeline must contain exactly 20 years")
    center_year = data.get("center_year")
    if center_year not in [item.get("year") for item in timeline]:
        raise ValueError("center_year must exist in timeline")
    for item in timeline:
        values = [item.get(key) for key in ("open", "high", "low", "close")]
        if any(not isinstance(value, (int, float)) or not 0 <= value <= 100 for value in values):
            raise ValueError("timeline OHLC values must be numeric values from 0 to 100")
        if not item["low"] <= min(item["open"], item["close"]) <= max(item["open"], item["close"]) <= item["high"]:
            raise ValueError("invalid timeline OHLC ordering")


def render_card(data, out_path):
    """渲染新版六段式卡片并返回 PNG 的绝对路径。"""

    _validate(data)
    pillars = data["pillars"]
    timeline = data["timeline"]
    center_year = data["center_year"]

    image = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(image)

    logo = Image.open(ROOT / "assets/logo.png").convert("RGB").resize((76, 76), Image.Resampling.LANCZOS)
    image.paste(logo, (88, 46))
    draw_tracking(draw, (178, 61), "人生有迹", font(MEDIUM, 38), INK, 4)

    if data.get("name"):
        draw.text((90, 137), data["name"], font=font(REGULAR, 38), fill=INK, anchor="la")
        meta_y, rule_y, first_title_y = 187, 235, 262
    else:
        meta_y, rule_y, first_title_y = 155, 213, 225
    draw.text(
        (90, meta_y),
        f'{data["birth"]}      {data["location"]}',
        font=font(REGULAR, 25),
        fill=MUTED,
        anchor="la",
    )
    draw.line((90, rule_y, 1152, rule_y), fill=RULE, width=2)

    draw_section_title(draw, first_title_y, "出生配置")
    x, pillar_font = 90, font(REGULAR, 28)
    for index, value in enumerate(pillars):
        color = VERMILION if index == 2 else MUTED
        draw.text((x, first_title_y + 48), value, font=pillar_font, fill=color, anchor="la")
        x += draw.textlength(value, font=pillar_font) + 10
        if index < 3:
            draw.text((x, first_title_y + 48), "｜", font=pillar_font, fill=MUTED, anchor="la")
            x += draw.textlength("｜", font=pillar_font) + 5
    content_bottom = first_title_y + 78

    talent_title_y = content_bottom + SECTION_GAP
    talent_lines = wrap(draw, data["talent_description"], font(REGULAR, BODY_SIZE), 1050, 2)
    content_bottom = draw_text_section(draw, talent_title_y, "初始天赋", talent_lines)

    core_title_y = content_bottom + SECTION_GAP
    core_lines = wrap(draw, data["core_mystic"], font(REGULAR, BODY_SIZE), 1050, 2)
    core_lines.extend(data["core_plain"][:2])
    if len(core_lines) > 4:
        raise ValueError("core configuration must fit within four body lines")
    content_bottom = draw_text_section(draw, core_title_y, "核心配置", core_lines)

    main_title_y = content_bottom + SECTION_GAP
    task_font = font(REGULAR, BODY_SIZE)
    if draw.textlength(data["main_task"], font=task_font) > 1050:
        raise ValueError("main_task must fit on one line; shorten the copy")
    content_bottom = draw_text_section(draw, main_title_y, "主线任务", [data["main_task"]])

    timeline_title_y = content_bottom + SECTION_GAP
    draw_section_title(draw, timeline_title_y, "人生K线")
    stage_label = data.get("stage_label", "")
    if stage_label:
        label_font = font(REGULAR, 20)
        label_width = draw.textlength(stage_label, font=label_font) + 34
        draw.rounded_rectangle(
            (1152 - label_width, timeline_title_y - 1, 1152, timeline_title_y + 33),
            radius=17,
            outline=GOLD,
            width=2,
        )
        draw.text((1135, timeline_title_y + 2), stage_label, font=label_font, fill=GOLD, anchor="ra")

    chart_left, chart_top, chart_right = 90, timeline_title_y + TITLE_BODY_GAP, 1098
    chart_bottom = chart_top + 360
    plot_top, plot_bottom = chart_top + 24, chart_bottom - 60
    candle_step = (chart_right - chart_left) / len(timeline)

    band_start = 0
    band_index = 0
    for index in range(1, len(timeline) + 1):
        if index == len(timeline) or timeline[index].get("dayun") != timeline[band_start].get("dayun"):
            fill = PALE_GREEN if band_index % 2 == 0 else PALE_GOLD
            band_left = chart_left + band_start * candle_step
            band_right = chart_left + index * candle_step
            draw.rectangle((band_left, plot_top, band_right, plot_bottom), fill=fill)
            luck_label = timeline[band_start].get("dayun")
            if luck_label:
                draw.text(
                    ((band_left + band_right) / 2, plot_top + 7),
                    f"{luck_label}运",
                    font=font(REGULAR, 17),
                    fill=MUTED,
                    anchor="ma",
                )
            if index < len(timeline):
                x_line = chart_left + index * candle_step
                draw.line((x_line, plot_top, x_line, plot_bottom), fill=GOLD, width=2)
            band_start = index
            band_index += 1

    raw_min = min(item["low"] for item in timeline)
    raw_max = max(item["high"] for item in timeline)
    axis_min = max(0, math.floor((raw_min - 3) / 10) * 10)
    axis_max = min(100, math.ceil((raw_max + 3) / 10) * 10)
    if axis_max - axis_min < 40:
        pad = (40 - (axis_max - axis_min)) / 2
        axis_min = max(0, math.floor((axis_min - pad) / 10) * 10)
        axis_max = min(100, math.ceil((axis_max + pad) / 10) * 10)

    def scale_y(value):
        return plot_bottom - (value - axis_min) / (axis_max - axis_min) * (plot_bottom - plot_top)

    axis_font = font(REGULAR, 17)
    for level in range(axis_min, axis_max + 1, 10):
        y = scale_y(level)
        draw.line((chart_left, y, chart_right, y), fill=RULE, width=1)
        draw.text((chart_right + 16, y), str(level), font=axis_font, fill=MUTED, anchor="lm")

    averages = [item.get("average", item["close"]) for item in timeline]
    trend_points = []
    for index in range(len(averages)):
        x = chart_left + (index + 0.5) * candle_step
        window = averages[max(0, index - 2):index + 1]
        trend_points.append((x, scale_y(sum(window) / len(window))))
    draw.line(trend_points, fill=TREND, width=4, joint="curve")

    year_font, ganzhi_font = font(REGULAR, 18), font(REGULAR, 17)
    for index, item in enumerate(timeline):
        x = chart_left + (index + 0.5) * candle_step
        y_high, y_low = scale_y(item["high"]), scale_y(item["low"])
        y_open, y_close = scale_y(item["open"]), scale_y(item["close"])
        color = VERMILION if item["close"] >= item["open"] else GREEN
        draw.line((x, y_high, x, y_low), fill=color, width=3)
        top, bottom = min(y_open, y_close), max(y_open, y_close)
        if bottom - top < 3:
            draw.line((x - 8, top, x + 8, top), fill=color, width=4)
        else:
            draw.rectangle((x - 8, top, x + 8, bottom), fill=color)
        if index % 2 == 0 or item["year"] == center_year:
            label_color = GOLD if item["year"] == center_year else MUTED
            draw.text((x, chart_bottom - 36), str(item["year"])[2:], font=year_font, fill=label_color, anchor="ma")
            draw.text((x, chart_bottom - 13), item["ganzhi"], font=ganzhi_font, fill=label_color, anchor="ma")

    legend_y = chart_bottom + 13
    draw.line((90, legend_y + 7, 120, legend_y + 7), fill=TREND, width=4)
    draw.text((130, legend_y - 7), "三年趋势", font=font(REGULAR, 20), fill=MUTED, anchor="la")
    draw.text((252, legend_y - 7), "影线＝变化幅度", font=font(REGULAR, 20), fill=MUTED, anchor="la")
    draw.text((1152, legend_y - 7), "阶段指数，不代表事件保证", font=font(REGULAR, 18), fill=MUTED, anchor="ra")

    issue_title_y = legend_y + 50
    draw_section_title(draw, issue_title_y, "当前课题")
    issue = data.get("current_issue")
    if not isinstance(issue, dict):
        raise ValueError("current_issue must be an object")
    domain, headline, example = issue.get("domain", ""), issue.get("headline", ""), issue.get("example", "")
    if not all(isinstance(value, str) and value for value in (domain, headline, example)):
        raise ValueError("current_issue requires domain, headline and example")
    if not 2 <= len(domain) <= 6:
        raise ValueError("current_issue.domain must contain 2 to 6 characters")
    if not 18 <= len(headline) <= 32:
        raise ValueError("current_issue.headline must contain 18 to 32 characters")
    if not 22 <= len(example) <= 44:
        raise ValueError("current_issue.example must contain 22 to 44 characters")

    issue_label_font = font(REGULAR, 19)
    issue_label_width = draw.textlength(domain, font=issue_label_font) + 32
    draw.rounded_rectangle(
        (1152 - issue_label_width, issue_title_y - 1, 1152, issue_title_y + 32),
        radius=16,
        fill=PALE_BLUE,
        outline=ISSUE_BLUE,
        width=1,
    )
    draw.text((1136, issue_title_y + 1), domain, font=issue_label_font, fill=ISSUE_BLUE, anchor="ra")

    headline_font = font(REGULAR, 32)
    headline_lines = wrap(draw, headline, headline_font, 994, 2)
    if "".join(headline_lines) != headline:
        raise ValueError("current_issue.headline must fit within two lines")
    example_font = font(REGULAR, 24)
    example_lines = wrap(draw, example, example_font, 994, 2)
    if "".join(example_lines) != example:
        raise ValueError("current_issue.example must fit within two lines")

    box_top = issue_title_y + 46
    example_y = box_top + 18 + len(headline_lines) * 40 + 7
    content_bottom = example_y + (len(example_lines) - 1) * 33 + 30
    box_bottom = max(box_top + 124, content_bottom)
    if box_bottom > 1550:
        raise ValueError("current_issue content exceeds the available card height")
    draw.rounded_rectangle((90, box_top, 1152, box_bottom), radius=18, fill="#EFE8D9", outline="#D8C7A5", width=2)
    for index, line in enumerate(headline_lines):
        draw.text((118, box_top + 18 + index * 40), line, font=headline_font, fill=ISSUE_BLUE, anchor="la")
    for index, line in enumerate(example_lines):
        draw.text((118, example_y + index * 33), line, font=example_font, fill=ISSUE_BLUE_MUTED, anchor="la")

    draw.text(
        (W // 2, 1616),
        "输入出生时间，看看你正走到人生哪一段",
        font=font(REGULAR, 23),
        fill=GREEN,
        anchor="mm",
    )
    out_path = Path(out_path)
    image.save(out_path, format="PNG", optimize=True)
    return out_path.resolve()
