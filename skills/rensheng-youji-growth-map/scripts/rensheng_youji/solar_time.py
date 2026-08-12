"""出生地解析与真太阳时换算。

中国地点优先从 Skill 内置的省、市、县区三级数据中解析。换算采用
城市或县区中心经度加 NOAA 近似均时差，因此结果仍是地点中心近似值，
不是具体出生地址的测量结果。
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
from math import cos, pi, sin
from pathlib import Path
import re
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class CityLocation:
    longitude: float
    timezone: str = "Asia/Shanghai"
    resolved_name: str = ""


_DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "china_county_locations.json"
_COUNTRY_PREFIXES = ("中华人民共和国", "中国")
_SEPARATORS = re.compile(r"[\s,，/\\·、—_-]+")
_SUFFIXES = tuple(sorted((
    "维吾尔自治区", "壮族自治区", "回族自治区", "特别行政区",
    "自治州", "自治县", "自治旗", "自治区", "地区", "林区",
    "矿区", "新区", "开发区", "管理区", "特区", "街道", "省",
    "市", "县", "区", "旗", "盟",
), key=len, reverse=True))

_LOCATION_INDEX: dict[str, list[dict]] | None = None


def _clean(value: str) -> str:
    result = _SEPARATORS.sub("", value.strip())
    for prefix in _COUNTRY_PREFIXES:
        if result.startswith(prefix):
            result = result[len(prefix):]
            break
    return result


def _strip_suffix(value: str) -> str:
    cleaned = _clean(value)
    for suffix in _SUFFIXES:
        if cleaned.endswith(suffix) and len(cleaned) > len(suffix):
            return cleaned[:-len(suffix)]
    return cleaned


def normalize_city(city: str) -> str:
    """保留旧接口：清理国家前缀、分隔符和末尾行政区后缀。"""

    return _strip_suffix(city)


def _location_variants(record: dict) -> set[str]:
    parts = [_clean(part) for part in record["p"]]
    short = [_strip_suffix(part) for part in record["p"]]
    variants = {
        _clean(record["n"]),
        _strip_suffix(record["n"]),
        "".join(parts),
        "".join(short),
    }
    if len(parts) >= 2:
        variants.update({
            "".join(parts[-2:]),
            "".join(short[-2:]),
            parts[0] + parts[-1],
            short[0] + short[-1],
        })
    return {value for value in variants if value}


def _load_location_index() -> dict[str, list[dict]]:
    global _LOCATION_INDEX
    if _LOCATION_INDEX is not None:
        return _LOCATION_INDEX
    try:
        payload = json.loads(_DATA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("内置中国地点库无法读取，请重新安装完整 Skill。") from exc

    index: dict[str, list[dict]] = defaultdict(list)
    for record in payload["locations"]:
        for variant in _location_variants(record):
            index[variant].append(record)
    _LOCATION_INDEX = dict(index)
    return _LOCATION_INDEX


def _describe(record: dict) -> str:
    return "·".join(record["p"])


def _choose_location(city: str, candidates: list[dict]) -> dict:
    unique: dict[tuple, dict] = {}
    for record in candidates:
        key = (tuple(record["p"]), record["x"], record["z"])
        unique[key] = record
    values = list(unique.values())
    if len(values) == 1:
        return values[0]

    # 北京、上海等省级与地级记录坐标几乎一致时，采用更具体的一条。
    longitudes = [float(item["x"]) for item in values]
    if max(longitudes) - min(longitudes) <= 0.08:
        return max(values, key=lambda item: len(item["p"]))

    choices = "、".join(_describe(item) for item in values[:6])
    if len(values) > 6:
        choices += "等"
    raise ValueError(
        f"出生地“{city}”存在重名，请补充省或地级市。可选地点：{choices}。"
    )


def resolve_location(city: str, longitude: float | None, timezone: str | None) -> CityLocation:
    raw_key = _clean(city)
    short_key = _strip_suffix(city)
    candidates: list[dict] = []
    if longitude is None:
        index = _load_location_index()
        candidates = index.get(raw_key, []) or index.get(short_key, [])
        if not candidates:
            raise ValueError(
                "当前地点库尚未匹配到该出生地。中国地点请补充省/市/县区；"
                "海外地点请提供 longitude 和 IANA timezone。"
            )
        selected = _choose_location(city, candidates)
        longitude = float(selected["x"])
        timezone = timezone or selected["z"]
        resolved_name = _describe(selected)
    else:
        resolved_name = city.strip()

    if not timezone:
        raise ValueError("海外或自定义地点必须提供 IANA timezone，例如 Asia/Tokyo。")
    try:
        ZoneInfo(timezone)
    except Exception as exc:
        raise ValueError("timezone 必须是有效的 IANA 时区名称。") from exc
    return CityLocation(
        longitude=longitude,
        timezone=timezone,
        resolved_name=resolved_name,
    )


def equation_of_time_minutes(value: datetime) -> float:
    """NOAA 五项近似公式，返回均时差（分钟）。"""

    day_of_year = value.timetuple().tm_yday
    gamma = 2 * pi / 365 * (day_of_year - 1 + (value.hour - 12) / 24)
    return 229.18 * (
        0.000075
        + 0.001868 * cos(gamma)
        - 0.032077 * sin(gamma)
        - 0.014615 * cos(2 * gamma)
        - 0.040849 * sin(2 * gamma)
    )


def adjust_to_true_solar(local_civil: datetime, location: CityLocation) -> tuple[datetime, float, float]:
    """把当地法定时间换算为地点中心近似真太阳时。

    返回：(真太阳时、总校正分钟数、当地 UTC 偏移小时数)。
    """

    aware = local_civil.replace(tzinfo=ZoneInfo(location.timezone))
    utc_offset = aware.utcoffset()
    if utc_offset is None:
        raise ValueError("无法确定出生时刻的当地法定时区偏移。")
    offset_hours = utc_offset.total_seconds() / 3600
    correction = equation_of_time_minutes(local_civil) + 4 * location.longitude - 60 * offset_hours
    return local_civil + timedelta(minutes=correction), correction, offset_hours
