"""旋转星图的数据模型：星表校验、极射赤面投影与可见性计算。"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Sequence, Set, Tuple

MIN_CATALOG_SIZE = 50
MIN_LATITUDE = -66.0
MAX_LATITUDE = 66.0
MIN_MONTH = 1
MAX_MONTH = 12
MIN_HOUR = 0.0
MAX_HOUR = 23.0
MIN_MAGNITUDE = -5.0
MAX_MAGNITUDE = 3.5
MIN_TITLE_LENGTH = 1
MAX_TITLE_LENGTH = 40

_MONTH_MID_DAYS: Tuple[int, ...] = (15, 46, 74, 105, 135, 166, 196, 227, 258, 288, 319, 349)

_COMPASS_NAMES: Tuple[str, ...] = (
    "北",
    "东北",
    "东",
    "东南",
    "南",
    "西南",
    "西",
    "西北",
)


class StarwheelError(ValueError):
    """星表、参数或渲染数据不合法。"""


def _as_float(value: object, label: str) -> float:
    """把外部输入转换为有限浮点数，失败时抛出中文错误。"""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise StarwheelError("%s必须是数字" % label)
    number = float(value)
    if not math.isfinite(number):
        raise StarwheelError("%s必须是有限数字" % label)
    return number


def validate_latitude(latitude: float) -> float:
    """校验观测纬度，允许范围为 -66°~66°。"""
    value = _as_float(latitude, "纬度")
    if not MIN_LATITUDE <= value <= MAX_LATITUDE:
        raise StarwheelError(
            "纬度必须在 %g~%g 度之间，当前是 %g 度"
            % (MIN_LATITUDE, MAX_LATITUDE, value)
        )
    return value


def validate_month(month: int) -> int:
    """校验月份，允许范围为 1~12。"""
    if isinstance(month, bool) or not isinstance(month, int):
        raise StarwheelError("月份必须是整数")
    if not MIN_MONTH <= month <= MAX_MONTH:
        raise StarwheelError(
            "月份必须在 %d~%d 之间，当前是 %d"
            % (MIN_MONTH, MAX_MONTH, month)
        )
    return month


def validate_hour(hour: float) -> float:
    """校验小时，允许范围为 0~23（含端点）。"""
    value = _as_float(hour, "小时")
    if not MIN_HOUR <= value <= MAX_HOUR:
        raise StarwheelError(
            "小时必须在 %g~%g 之间，当前是 %g" % (MIN_HOUR, MAX_HOUR, value)
        )
    return value


def validate_title(title: str) -> str:
    """校验标题：去空白后 1~40 个字符。"""
    if not isinstance(title, str):
        raise StarwheelError("标题必须是文本")
    text = title.strip()
    if not MIN_TITLE_LENGTH <= len(text) <= MAX_TITLE_LENGTH:
        raise StarwheelError(
            "标题长度必须在 %d~%d 个字符之间" % (MIN_TITLE_LENGTH, MAX_TITLE_LENGTH)
        )
    return text


def validate_magnitude(magnitude: float) -> float:
    """校验视星等：亮星表只收录不暗于 3.5 等的星。"""
    value = _as_float(magnitude, "视星等")
    if not MIN_MAGNITUDE <= value <= MAX_MAGNITUDE:
        raise StarwheelError(
            "视星等必须在 %g~%g 之间，当前是 %g"
            % (MIN_MAGNITUDE, MAX_MAGNITUDE, value)
        )
    return value


@dataclass(frozen=True)
class Star:
    """一颗亮星：中文名、赤经（小时）、赤纬（度）与视星等。"""

    name: str
    ra_hours: float
    dec_degrees: float
    magnitude: float

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise StarwheelError("星名不能为空")
        name = self.name.strip()
        ra = _as_float(self.ra_hours, "赤经")
        dec = _as_float(self.dec_degrees, "赤纬")
        magnitude = validate_magnitude(self.magnitude)
        if not 0.0 <= ra <= 24.0:
            raise StarwheelError(
                "赤经必须在 0~24 小时之间，当前是 %g 小时" % ra
            )
        if not -90.0 <= dec <= 90.0:
            raise StarwheelError(
                "赤纬必须在 -90~90 度之间，当前是 %g 度" % dec
            )
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "ra_hours", ra)
        object.__setattr__(self, "dec_degrees", dec)
        object.__setattr__(self, "magnitude", magnitude)

    @property
    def is_northern(self) -> bool:
        """是否位于北天半球（赤纬不低于 0°）。"""
        return self.dec_degrees >= 0.0


def _normalize_stars(stars: Sequence[Star], minimum: int) -> Tuple[Star, ...]:
    if isinstance(stars, (str, bytes)):
        raise StarwheelError("星表必须是 Star 序列")
    try:
        items = tuple(stars)
    except TypeError as exc:
        raise StarwheelError("星表必须是 Star 序列") from exc
    if len(items) < minimum:
        raise StarwheelError("星表至少需要 %d 颗星，当前有 %d 颗" % (minimum, len(items)))
    seen: Set[str] = set()
    for star in items:
        if not isinstance(star, Star):
            raise StarwheelError("星表中的每一项都必须是 Star 对象")
        if star.name in seen:
            raise StarwheelError("星名重复：%s" % star.name)
        seen.add(star.name)
    return items


def validate_catalog(stars: Sequence[Star]) -> Tuple[Star, ...]:
    """校验完整星表：至少 50 颗、名称唯一、坐标与星等合法。"""
    return _normalize_stars(stars, MIN_CATALOG_SIZE)


def project_star(ra_hours: float, dec_degrees: float) -> Tuple[float, float]:
    """北天极极射赤面投影：r = tan((90° - δ) / 2)。

    赤经按逆时针方向绕圆心旋转。南天星的半径会超出单位圆，
    这里截断到单位圆边界，保证所有投影点都落在星盘范围内。
    """
    ra = _as_float(ra_hours, "赤经")
    dec = _as_float(dec_degrees, "赤纬")
    if not 0.0 <= ra <= 24.0:
        raise StarwheelError("赤经必须在 0~24 小时之间，当前是 %g 小时" % ra)
    if not -90.0 <= dec <= 90.0:
        raise StarwheelError("赤纬必须在 -90~90 度之间，当前是 %g 度" % dec)

    theta = math.radians((ra % 24.0) * 15.0)
    radius = math.tan(math.radians((90.0 - dec) / 2.0))
    if radius > 1.0:
        radius = 1.0
    if radius < 0.0:
        radius = 0.0
    return radius * math.cos(theta), radius * math.sin(theta)


def star_radius(magnitude: float) -> float:
    """按视星等换算星点绘制半径（毫米），越亮越大。"""
    value = validate_magnitude(magnitude)
    radius = 0.70 + (MAX_MAGNITUDE - value) * 0.32
    return max(0.70, min(2.20, radius))


def solar_ra_hours(month: int) -> float:
    """估算某月月中太阳的赤经（小时）。"""
    month = validate_month(month)
    day_index = float(_MONTH_MID_DAYS[month - 1] - 1)
    mean_anomaly = math.radians(357.529 + 0.98560028 * day_index)
    mean_longitude = (280.459 + 0.98564736 * day_index) % 360.0
    longitude = (
        mean_longitude
        + 1.915 * math.sin(mean_anomaly)
        + 0.020 * math.sin(2.0 * mean_anomaly)
    )
    obliquity = math.radians(23.439 - 0.00000036 * day_index)
    longitude_rad = math.radians(longitude)
    ra = math.degrees(
        math.atan2(
            math.cos(obliquity) * math.sin(longitude_rad),
            math.cos(longitude_rad),
        )
    ) % 360.0
    return ra / 15.0


def local_sidereal_hours(month: int, hour: float) -> float:
    """估算当地恒星时（小时）；忽略经度与均时差。"""
    month = validate_month(month)
    hour = validate_hour(hour)
    return (solar_ra_hours(month) + hour - 12.0) % 24.0


def rotation_angle(month: int, hour: float) -> float:
    """星盘旋转角（度）：把当前恒星时转到页面正上方。"""
    sidereal = local_sidereal_hours(month, hour)
    return (90.0 - sidereal * 15.0) % 360.0


def hour_angle_hours(sidereal_hours: float, ra_hours: float) -> float:
    """计算时角（小时），范围 -12~12。"""
    sidereal = _as_float(sidereal_hours, "恒星时")
    ra = _as_float(ra_hours, "赤经")
    if not 0.0 <= sidereal < 24.0:
        raise StarwheelError("恒星时必须在 0~24 小时之间")
    if not 0.0 <= ra <= 24.0:
        raise StarwheelError("赤经必须在 0~24 小时之间，当前是 %g 小时" % ra)
    return (sidereal - ra + 12.0) % 24.0 - 12.0


def _horizontal(
    ra_hours: float, dec_degrees: float, latitude: float, sidereal_hours: float
) -> Tuple[float, float]:
    dec_value = _as_float(dec_degrees, "赤纬")
    if not -90.0 <= dec_value <= 90.0:
        raise StarwheelError(
            "赤纬必须在 -90~90 度之间，当前是 %g 度" % dec_value
        )
    lat = math.radians(validate_latitude(latitude))
    dec = math.radians(dec_value)
    hour_angle = math.radians(hour_angle_hours(sidereal_hours, ra_hours) * 15.0)
    sin_altitude = (
        math.sin(lat) * math.sin(dec)
        + math.cos(lat) * math.cos(dec) * math.cos(hour_angle)
    )
    sin_altitude = max(-1.0, min(1.0, sin_altitude))
    altitude = math.degrees(math.asin(sin_altitude))
    cos_altitude = math.cos(math.radians(altitude))
    if abs(cos_altitude) < 1e-12:
        return altitude, 0.0
    east = -math.sin(hour_angle) * math.cos(dec)
    north = math.sin(dec) * math.cos(lat) - math.cos(dec) * math.sin(lat) * math.cos(
        hour_angle
    )
    azimuth = math.degrees(math.atan2(east, north)) % 360.0
    return altitude, azimuth


def altitude_degrees(
    ra_hours: float, dec_degrees: float, latitude: float, sidereal_hours: float
) -> float:
    """计算恒星的地平高度（度）。"""
    return _horizontal(ra_hours, dec_degrees, latitude, sidereal_hours)[0]


def azimuth_degrees(
    ra_hours: float, dec_degrees: float, latitude: float, sidereal_hours: float
) -> float:
    """计算恒星方位角（度）：正北为 0°，顺时针增加。"""
    return _horizontal(ra_hours, dec_degrees, latitude, sidereal_hours)[1]


def compass_direction(azimuth: float) -> str:
    """把方位角转换为八方位中文名。"""
    value = _as_float(azimuth, "方位角") % 360.0
    index = int((value + 22.5) // 45.0) % len(_COMPASS_NAMES)
    return _COMPASS_NAMES[index]


@dataclass(frozen=True)
class VisibleStar:
    """一颗当前可见的星及其地平坐标。"""

    star: Star
    altitude: float
    azimuth: float

    @property
    def direction(self) -> str:
        """八方位名称。"""
        return compass_direction(self.azimuth)


def visible_stars(
    stars: Sequence[Star],
    latitude: float,
    month: int,
    hour: float,
    min_altitude: float = 0.0,
) -> Tuple[VisibleStar, ...]:
    """返回当前时刻地平线以上的星，按视星等从亮到暗排序。"""
    items = _normalize_stars(stars, 1)
    lat = validate_latitude(latitude)
    month = validate_month(month)
    hour = validate_hour(hour)
    threshold = _as_float(min_altitude, "最低高度")
    if not -90.0 <= threshold <= 90.0:
        raise StarwheelError("最低高度必须在 -90~90 度之间")
    sidereal = local_sidereal_hours(month, hour)
    result: List[VisibleStar] = []
    for star in items:
        altitude, azimuth = _horizontal(
            star.ra_hours, star.dec_degrees, lat, sidereal
        )
        if altitude >= threshold:
            result.append(
                VisibleStar(star=star, altitude=altitude, azimuth=azimuth)
            )
    result.sort(key=lambda item: (item.star.magnitude, item.star.name))
    return tuple(result)


@dataclass(frozen=True)
class MaskWindow:
    """遮罩页的椭圆窗口，半轴以星盘半径为单位。"""

    rx: float
    ry: float

    def __post_init__(self) -> None:
        rx = _as_float(self.rx, "窗口横向半轴")
        ry = _as_float(self.ry, "窗口纵向半轴")
        if not 0.0 < rx <= 1.0 or not 0.0 < ry <= 1.0:
            raise StarwheelError("遮罩窗口半轴必须在 0~1 之间")
        object.__setattr__(self, "rx", rx)
        object.__setattr__(self, "ry", ry)


def mask_window(latitude: float) -> MaskWindow:
    """按纬度估算可打印遮罩的椭圆窗口。

    低纬度看到的天区较少，窗口较扁；高纬度拱极星更多，窗口更接近圆形。
    """
    lat = validate_latitude(latitude)
    ratio = abs(lat) / MAX_LATITUDE
    visible_fraction = 0.5 + 0.5 * ratio
    rx = 0.86 + 0.12 * visible_fraction
    ry = 0.52 + 0.44 * ratio
    return MaskWindow(rx=rx, ry=ry)
