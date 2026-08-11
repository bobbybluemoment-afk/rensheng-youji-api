"""真太阳时换算。

采用经度时差加 NOAA 近似均时差。城市坐标只用于确定城市中心经度，
因此换算结果应理解为城市级近似值，而不是具体产房坐标的测量结果。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from math import cos, pi, sin
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class CityLocation:
    longitude: float
    timezone: str = "Asia/Shanghai"


_CHINA_CITIES = {
    "北京": 116.4074, "上海": 121.4737, "天津": 117.2008, "重庆": 106.5516,
    "广州": 113.2644, "深圳": 114.0579, "杭州": 120.1551, "南京": 118.7969,
    "苏州": 120.5853, "武汉": 114.3054, "成都": 104.0665, "西安": 108.9398,
    "郑州": 113.6254, "长沙": 112.9388, "合肥": 117.2272, "济南": 117.1201,
    "青岛": 120.3826, "厦门": 118.0894, "泉州": 118.6759, "福州": 119.2965,
    "南昌": 115.8582, "昆明": 102.8329, "贵阳": 106.6302, "南宁": 108.3669,
    "海口": 110.1983, "三亚": 109.5119, "哈尔滨": 126.6424, "长春": 125.3235,
    "沈阳": 123.4315, "大连": 121.6147, "石家庄": 114.5149, "太原": 112.5492,
    "呼和浩特": 111.7492, "乌鲁木齐": 87.6168, "拉萨": 91.1322, "兰州": 103.8343,
    "西宁": 101.7782, "银川": 106.2309,
}

CITY_LOCATIONS = {name: CityLocation(lon) for name, lon in _CHINA_CITIES.items()}
CITY_LOCATIONS.update({
    "香港": CityLocation(114.1694, "Asia/Hong_Kong"),
    "澳门": CityLocation(113.5439, "Asia/Macau"),
    "台北": CityLocation(121.5654, "Asia/Taipei"),
})


def normalize_city(city: str) -> str:
    value = city.strip()
    for suffix in ("特别行政区", "自治州", "地区", "市", "县", "区"):
        if value.endswith(suffix):
            value = value[: -len(suffix)]
            break
    return value


def resolve_location(city: str, longitude: float | None, timezone: str | None) -> CityLocation:
    known = CITY_LOCATIONS.get(normalize_city(city))
    if longitude is None:
        if known is None:
            raise ValueError("当前城市库尚未收录该城市，请同时提供 longitude 和 timezone。")
        longitude = known.longitude
    timezone = timezone or (known.timezone if known else None)
    if not timezone:
        raise ValueError("未收录城市必须提供 IANA timezone，例如 Asia/Shanghai。")
    try:
        ZoneInfo(timezone)
    except Exception as exc:
        raise ValueError("timezone 必须是有效的 IANA 时区名称。") from exc
    return CityLocation(longitude=longitude, timezone=timezone)


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
    """把当地法定时间换算为城市中心近似真太阳时。

    返回：(真太阳时、总校正分钟数、当地 UTC 偏移小时数)。
    """
    aware = local_civil.replace(tzinfo=ZoneInfo(location.timezone))
    utc_offset = aware.utcoffset()
    if utc_offset is None:
        raise ValueError("无法确定出生时刻的当地法定时区偏移。")
    offset_hours = utc_offset.total_seconds() / 3600
    correction = equation_of_time_minutes(local_civil) + 4 * location.longitude - 60 * offset_hours
    return local_civil + timedelta(minutes=correction), correction, offset_hours

