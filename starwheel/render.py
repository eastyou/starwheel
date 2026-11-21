"""把星表渲染成自包含、可打印的 A4 三页 HTML。"""

from __future__ import annotations

import html
import math
from typing import List, Sequence, Tuple

from .model import (
    MAX_MONTH,
    MaskWindow,
    Star,
    compass_direction,
    local_sidereal_hours,
    mask_window,
    project_star,
    rotation_angle,
    star_radius,
    validate_catalog,
    validate_hour,
    validate_latitude,
    validate_month,
    validate_title,
    visible_stars,
)

PAGE_WIDTH_MM = 210.0
PAGE_HEIGHT_MM = 297.0
DISK_CENTER_X = 105.0
DISK_CENTER_Y = 154.0
DISK_RADIUS_MM = 84.0
PAGE_COUNT = 3
TABLE_TOP_MM = 56.2
TABLE_BOTTOM_MM = 240.0
MAX_ROW_HEIGHT_MM = 5.4


def _num(value: float) -> str:
    """格式化毫米/角度数字，最多保留两位小数。"""
    text = "%.2f" % value
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text == "-0":
        text = "0"
    return text


def _esc(text: str) -> str:
    return html.escape(text, quote=True)


def _text(
    x: float,
    y: float,
    text: str,
    cls: str = "",
    anchor: str = "start",
    baseline: str = "",
) -> str:
    attrs: List[str] = ['x="%s"' % _num(x), 'y="%s"' % _num(y)]
    if cls:
        attrs.append('class="%s"' % cls)
    if anchor:
        attrs.append('text-anchor="%s"' % anchor)
    if baseline:
        attrs.append('dominant-baseline="%s"' % baseline)
    return "<text %s>%s</text>" % (" ".join(attrs), _esc(text))


def _line(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    cls: str = "",
    extra: str = "",
) -> str:
    attrs: List[str] = [
        'x1="%s"' % _num(x1),
        'y1="%s"' % _num(y1),
        'x2="%s"' % _num(x2),
        'y2="%s"' % _num(y2),
    ]
    if cls:
        attrs.append('class="%s"' % cls)
    if extra:
        attrs.append(extra)
    return "<line %s/>" % " ".join(attrs)


def _circle(
    cx: float,
    cy: float,
    radius: float,
    cls: str = "",
    extra: str = "",
) -> str:
    attrs: List[str] = [
        'cx="%s"' % _num(cx),
        'cy="%s"' % _num(cy),
        'r="%s"' % _num(radius),
    ]
    if cls:
        attrs.append('class="%s"' % cls)
    if extra:
        attrs.append(extra)
    return "<circle %s/>" % " ".join(attrs)


def _svg(label: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %s %s" '
        'width="%smm" height="%smm" role="img" aria-label="%s">'
        "<title>%s</title>%s</svg>"
        % (
            _num(PAGE_WIDTH_MM),
            _num(PAGE_HEIGHT_MM),
            _num(PAGE_WIDTH_MM),
            _num(PAGE_HEIGHT_MM),
            _esc(label),
            _esc(label),
            body,
        )
    )


def _heading(title: str, subtitle: str, page_label: str) -> str:
    return (
        _text(PAGE_WIDTH_MM / 2.0, 16.5, title, "page-title", "middle")
        + _text(PAGE_WIDTH_MM / 2.0, 23.2, subtitle, "page-subtitle", "middle")
        + _text(PAGE_WIDTH_MM - 14.0, 10.5, page_label, "page-number", "end")
    )


def _footer(lines: Sequence[str]) -> str:
    start = 264.0
    return "".join(
        _text(
            PAGE_WIDTH_MM / 2.0,
            start + index * 7.2,
            line,
            "footer-text",
            "middle",
        )
        for index, line in enumerate(lines)
    )


def _format_ra(ra_hours: float) -> str:
    total_minutes = int(round((ra_hours % 24.0) * 60.0)) % (24 * 60)
    hours, minutes = divmod(total_minutes, 60)
    return "%02dh%02dm" % (hours, minutes)


def _format_dec(dec_degrees: float) -> str:
    return "%+.1f°" % dec_degrees


def _format_azimuth(azimuth: float) -> str:
    return "%s %.0f°" % (compass_direction(azimuth), azimuth % 360.0)


def _star_markup(star: Star, x: float, y: float) -> str:
    radius = star_radius(star.magnitude)
    color = "#b91c1c" if star.name == "北极星" else "#1e3a8a"
    return (
        '<circle cx="%s" cy="%s" r="%s" fill="%s" stroke="#ffffff" '
        'stroke-width="0.18"><title>%s · %.2f 等</title></circle>'
        % (
            _num(x),
            _num(y),
            _num(radius),
            color,
            _esc(star.name),
            star.magnitude,
        )
    )


def _text_box(
    x: float, y: float, text: str, anchor: str
) -> Tuple[float, float, float, float]:
    width = len(text) * 3.0 + 0.8
    if anchor == "middle":
        left = x - width / 2.0
    elif anchor == "end":
        left = x - width
    else:
        left = x
    return left, y - 2.5, left + width, y + 0.9


def _overlaps(
    box: Tuple[float, float, float, float],
    occupied: Sequence[Tuple[float, float, float, float]],
) -> bool:
    for other in occupied:
        if not (
            box[2] + 1.0 < other[0]
            or box[0] - 1.0 > other[2]
            or box[3] + 1.0 < other[1]
            or box[1] - 1.0 > other[3]
        ):
            return True
    return False


def _place_labels(
    stars: Sequence[Star],
    positions: Sequence[Tuple[Star, float, float]],
    occupied: List[Tuple[float, float, float, float]],
) -> str:
    coordinates = {star.name: (x, y) for star, x, y in positions}
    candidates: Tuple[Tuple[float, float, str], ...] = (
        (2.1, -1.1, "start"),
        (-2.1, -1.1, "end"),
        (2.1, 3.4, "start"),
        (-2.1, 3.4, "end"),
        (0.0, -3.4, "middle"),
        (0.0, 4.8, "middle"),
        (3.6, -2.8, "start"),
        (-3.6, -2.8, "end"),
        (3.6, 5.0, "start"),
        (-3.6, 5.0, "end"),
    )
    markup: List[str] = []
    for star in stars:
        base_x, base_y = coordinates[star.name]
        chosen: Tuple[float, float, str] = candidates[0]
        chosen_box = _text_box(
            base_x + chosen[0], base_y + chosen[1], star.name, chosen[2]
        )
        for candidate in candidates:
            box = _text_box(
                base_x + candidate[0], base_y + candidate[1], star.name, candidate[2]
            )
            inside = (
                box[0] >= 2.0
                and box[2] <= PAGE_WIDTH_MM - 2.0
                and box[1] >= 2.0
                and box[3] <= PAGE_HEIGHT_MM - 2.0
            )
            if inside and not _overlaps(box, occupied):
                chosen = candidate
                chosen_box = box
                break
        occupied.append(chosen_box)
        markup.append(
            _text(
                base_x + chosen[0],
                base_y + chosen[1],
                star.name,
                "star-label",
                chosen[2],
            )
        )
    return "".join(markup)


def _star_chart_page(
    stars: Sequence[Star],
    latitude: float,
    month: int,
    hour: float,
    title: str,
) -> str:
    parts: List[str] = [
        '<rect x="0" y="0" width="210" height="297" fill="#ffffff"/>',
        _heading(
            title,
            "北纬 %s° · %d 月 %s 时 · 第 1 页 星盘"
            % (_num(latitude), month, _num(hour)),
            "1 / 3",
        ),
    ]
    parts.append(
        '<circle cx="%s" cy="%s" r="%s" fill="#fbfdff" stroke="#94a3b8" '
        'stroke-width="0.35"/>'
        % (
            _num(DISK_CENTER_X),
            _num(DISK_CENTER_Y),
            _num(DISK_RADIUS_MM),
        )
    )

    for dec in (30.0, 60.0, 75.0):
        radius = DISK_RADIUS_MM * math.tan(math.radians((90.0 - dec) / 2.0))
        parts.append(
            _circle(
                DISK_CENTER_X,
                DISK_CENTER_Y,
                radius,
                "grid",
                'stroke-dasharray="1.2 1.8"',
            )
        )

    for hour_index in range(0, 24, 2):
        angle = math.radians(hour_index * 15.0)
        parts.append(
            _line(
                DISK_CENTER_X,
                DISK_CENTER_Y,
                DISK_CENTER_X + DISK_RADIUS_MM * math.cos(angle),
                DISK_CENTER_Y - DISK_RADIUS_MM * math.sin(angle),
                "grid",
            )
        )

    parts.append(
        _circle(DISK_CENTER_X, DISK_CENTER_Y, DISK_RADIUS_MM + 6.0, "ring")
    )
    for hour_index in range(24):
        angle = math.radians(hour_index * 15.0)
        inner = DISK_RADIUS_MM + 1.0
        outer = DISK_RADIUS_MM + 6.0
        parts.append(
            _line(
                DISK_CENTER_X + inner * math.cos(angle),
                DISK_CENTER_Y - inner * math.sin(angle),
                DISK_CENTER_X + outer * math.cos(angle),
                DISK_CENTER_Y - outer * math.sin(angle),
                "tick-major" if hour_index % 2 == 0 else "tick-minor",
            )
        )
        if hour_index % 2 == 0:
            label_radius = DISK_RADIUS_MM + 11.0
            parts.append(
                _text(
                    DISK_CENTER_X + label_radius * math.cos(angle),
                    DISK_CENTER_Y - label_radius * math.sin(angle),
                    "%dh" % hour_index,
                    "hour-label",
                    "middle",
                    "middle",
                )
            )

    month_radius = DISK_RADIUS_MM * 0.78
    occupied: List[Tuple[float, float, float, float]] = []
    for month_index in range(1, MAX_MONTH + 1):
        angle = math.radians(90.0 - (month_index - 1) * 30.0)
        parts.append(
            _line(
                DISK_CENTER_X + month_radius * math.cos(angle),
                DISK_CENTER_Y - month_radius * math.sin(angle),
                DISK_CENTER_X + (month_radius + 4.0) * math.cos(angle),
                DISK_CENTER_Y - (month_radius + 4.0) * math.sin(angle),
                "month-tick",
            )
        )
        label_radius = month_radius - 4.0
        label_x = DISK_CENTER_X + label_radius * math.cos(angle)
        label_y = DISK_CENTER_Y - label_radius * math.sin(angle)
        parts.append(
            _text(
                label_x,
                label_y,
                "%d月" % month_index,
                "month-label",
                "middle",
                "middle",
            )
        )
        occupied.append(_text_box(label_x, label_y, "%d月" % month_index, "middle"))

    chart_stars = [star for star in stars if star.is_northern]
    positions: List[Tuple[Star, float, float]] = []
    for star in chart_stars:
        x, y = project_star(star.ra_hours, star.dec_degrees)
        screen_x = DISK_CENTER_X + x * DISK_RADIUS_MM
        screen_y = DISK_CENTER_Y - y * DISK_RADIUS_MM
        positions.append((star, screen_x, screen_y))
        parts.append(_star_markup(star, screen_x, screen_y))

    labelled = sorted(
        (star for star in chart_stars if star.name != "北极星"),
        key=lambda star: (star.magnitude, star.name),
    )[:15]
    occupied.append(
        _text_box(
            DISK_CENTER_X + 4.2,
            DISK_CENTER_Y + 3.8,
            "北极星",
            "start",
        )
    )
    parts.append(_place_labels(labelled, positions, occupied))

    parts.append(
        _line(
            DISK_CENTER_X - 3.0,
            DISK_CENTER_Y,
            DISK_CENTER_X + 3.0,
            DISK_CENTER_Y,
            "center-cross",
        )
    )
    parts.append(
        _line(
            DISK_CENTER_X,
            DISK_CENTER_Y - 3.0,
            DISK_CENTER_X,
            DISK_CENTER_Y + 3.0,
            "center-cross",
        )
    )
    parts.append(
        _text(
            DISK_CENTER_X + 4.2,
            DISK_CENTER_Y + 3.8,
            "北极星",
            "center-label",
            "start",
        )
    )
    parts.append(
        _text(
            DISK_CENTER_X,
            DISK_CENTER_Y + DISK_RADIUS_MM - 5.0,
            "北天半球 · 赤纬 ≥ 0°",
            "disk-note",
            "middle",
        )
    )

    parts.append(
        _footer(
            (
                "组装：沿外圈实线剪下星盘；沿内圈月份刻度对齐遮罩页。",
                "使用：转动星盘，使当天月份对准当前小时，窗口内即为可见星空。",
                "说明：星盘绘制北天亮星；天狼星等南天亮星见第 3 页当夜星空表。",
            )
        )
    )
    return _svg("%s · 星盘页" % title, "".join(parts))


def _mask_page(latitude: float, title: str) -> str:
    window: MaskWindow = mask_window(latitude)
    radius_x = window.rx * DISK_RADIUS_MM
    radius_y = window.ry * DISK_RADIUS_MM
    parts: List[str] = [
        '<rect x="0" y="0" width="210" height="297" fill="#ffffff"/>',
        _heading(
            title,
            "北纬 %s° · 第 2 页 遮罩" % _num(latitude),
            "2 / 3",
        ),
        _circle(DISK_CENTER_X, DISK_CENTER_Y, DISK_RADIUS_MM, "guide"),
        '<ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="#eff6ff" '
        'stroke="#2563eb" stroke-width="0.55" stroke-dasharray="2.4 1.8"/>'
        % (
            _num(DISK_CENTER_X),
            _num(DISK_CENTER_Y),
            _num(radius_x),
            _num(radius_y),
        ),
        '<ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="none" '
        'stroke="#93c5fd" stroke-width="0.25"/>'
        % (
            _num(DISK_CENTER_X),
            _num(DISK_CENTER_Y),
            _num(radius_x - 1.2),
            _num(radius_y - 1.2),
        ),
        _line(
            DISK_CENTER_X - 9.0,
            DISK_CENTER_Y,
            DISK_CENTER_X + 9.0,
            DISK_CENTER_Y,
            "center-cross",
        ),
        _line(
            DISK_CENTER_X,
            DISK_CENTER_Y - 9.0,
            DISK_CENTER_X,
            DISK_CENTER_Y + 9.0,
            "center-cross",
        ),
        _circle(DISK_CENTER_X, DISK_CENTER_Y, 1.1, "center-dot"),
        _text(
            DISK_CENTER_X,
            DISK_CENTER_Y - radius_y - 4.0,
            "北",
            "north-label",
            "middle",
        ),
        _text(
            DISK_CENTER_X,
            DISK_CENTER_Y + radius_y - 5.0,
            "可见天空窗口",
            "window-label",
            "middle",
        ),
    ]
    parts.append(
        _footer(
            (
                "裁剪：沿蓝色虚线椭圆剪开，窗口外留白，中心十字务必保留。",
                "组装：把遮罩覆盖在星盘上，中心十字对准北极星，北字朝上。",
                "使用：转动下层星盘，使当天月份对准当前小时，窗口内即当夜星空。",
            )
        )
    )
    return _svg("%s · 遮罩页" % title, "".join(parts))


def _table_header(y: float) -> str:
    columns: Tuple[Tuple[float, str, str], ...] = (
        (14.0, "名称", "start"),
        (51.0, "赤经", "start"),
        (83.0, "赤纬", "start"),
        (112.0, "方位", "start"),
        (148.0, "高度", "start"),
        (196.0, "星等", "end"),
    )
    return "".join(
        _text(x, y, label, "table-head", anchor) for x, label, anchor in columns
    )


def _night_page(
    stars: Sequence[Star],
    latitude: float,
    month: int,
    hour: float,
    title: str,
) -> str:
    sidereal = local_sidereal_hours(month, hour)
    angle = rotation_angle(month, hour)
    visible = visible_stars(stars, latitude, month, hour)
    shown = visible
    parts: List[str] = [
        '<rect x="0" y="0" width="210" height="297" fill="#ffffff"/>',
        _heading(
            title,
            "北纬 %s° · %d 月 %s 时 · 第 3 页 当夜星空"
            % (_num(latitude), month, _num(hour)),
            "3 / 3",
        ),
        '<rect x="12" y="29" width="186" height="16" rx="2" fill="#f1f5f9"/>',
        _text(
            18.0,
            35.2,
            "恒星时 %s · 星盘旋转角 %.1f°" % (_format_ra(sidereal), angle),
            "info-text",
            "start",
        ),
        _text(
            18.0,
            41.0,
            "可见亮星 %d 颗 · 按视星等从亮到暗排列" % len(visible),
            "info-text",
            "start",
        ),
        '<rect x="12" y="49" width="186" height="7.2" fill="#e2e8f0"/>',
        _table_header(54.0),
    ]

    row_height = min(
        MAX_ROW_HEIGHT_MM,
        (TABLE_BOTTOM_MM - TABLE_TOP_MM) / max(1, len(shown)),
    )
    row_height = max(2.9, row_height)
    top = TABLE_TOP_MM
    cell_class = "table-cell compact" if len(shown) > 42 else "table-cell"
    if shown:
        for index, item in enumerate(shown):
            row_y = top + index * row_height
            if index % 2 == 1:
                parts.append(
                    '<rect x="12" y="%s" width="186" height="%s" fill="#f8fafc"/>'
                    % (_num(row_y), _num(row_height))
                )
            baseline = row_y + min(3.9, row_height * 0.78)
            parts.append(_text(14.0, baseline, item.star.name, cell_class))
            parts.append(
                _text(51.0, baseline, _format_ra(item.star.ra_hours), cell_class)
            )
            parts.append(
                _text(
                    83.0,
                    baseline,
                    _format_dec(item.star.dec_degrees),
                    cell_class,
                )
            )
            parts.append(
                _text(112.0, baseline, _format_azimuth(item.azimuth), cell_class)
            )
            parts.append(
                _text(148.0, baseline, "%.0f°" % item.altitude, cell_class)
            )
            parts.append(
                _text(
                    196.0,
                    baseline,
                    "%.2f" % item.star.magnitude,
                    cell_class,
                    "end",
                )
            )
    else:
        parts.append(
            _text(
                PAGE_WIDTH_MM / 2.0,
                80.0,
                "当前时刻没有地平线以上的亮星。",
                "table-cell",
                "middle",
            )
        )

    note = "共 %d 颗可见亮星，已全部列出。" % len(visible)
    parts.append(_text(105.0, 250.0, note, "footer-text", "middle"))
    parts.append(
        _footer(
            (
                "使用：方位以正北为 0°、顺时针增加；高度 0° 为地平线。",
                "说明：星表坐标取 J2000.0，恒星时与旋转角为按月份和时刻的近似值。",
                "组装：本页可单独打印，也可与星盘页、遮罩页一起装订成三页手册。",
            )
        )
    )
    return _svg("%s · 当夜星空页" % title, "".join(parts))


_STYLE = """
  :root { color-scheme: light; }
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; }
  body {
    background: #e2e8f0;
    color: #0f172a;
    font-family: "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif;
    overflow-x: hidden;
  }
  .toolbar {
    width: 210mm;
    max-width: calc(100% - 24px);
    margin: 0 auto 5mm;
    padding-top: 4mm;
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    justify-content: space-between;
    gap: 6px 12px;
    color: #334155;
    font-size: 13px;
  }
  .toolbar strong { font-size: 15px; letter-spacing: 1px; }
  .toolbar span { color: #64748b; font-size: 12px; }
  .toolbar button {
    border: 1px solid #94a3b8;
    background: #ffffff;
    color: #0f172a;
    border-radius: 4px;
    padding: 4px 12px;
    font: inherit;
    cursor: pointer;
  }
  .wrap { width: 100%; padding: 0 12px 10mm; }
  .sheet {
    width: 210mm;
    max-width: 100%;
    aspect-ratio: 210 / 297;
    margin: 0 auto 8mm;
    background: #ffffff;
    box-shadow: 0 6px 24px rgba(15, 23, 42, 0.16);
    overflow: hidden;
    break-after: page;
    page-break-after: always;
  }
  .sheet:last-child { break-after: auto; page-break-after: auto; }
  .sheet svg { display: block; width: 100%; height: 100%; }
  svg text { font-family: "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif; }
  .page-title { font-size: 6.2px; font-weight: 700; fill: #0f172a; letter-spacing: 0.8px; }
  .page-subtitle { font-size: 3.1px; fill: #475569; }
  .page-number { font-size: 2.6px; fill: #64748b; }
  .grid { fill: none; stroke: #e2e8f0; stroke-width: 0.18; }
  .ring { fill: none; stroke: #94a3b8; stroke-width: 0.35; }
  .tick-major { stroke: #475569; stroke-width: 0.38; }
  .tick-minor { stroke: #94a3b8; stroke-width: 0.22; }
  .hour-label { font-size: 2.5px; fill: #334155; }
  .month-tick { stroke: #94a3b8; stroke-width: 0.24; }
  .month-label { font-size: 2.55px; fill: #64748b; }
  .star-label {
    font-size: 2.75px;
    fill: #0f172a;
    paint-order: stroke;
    stroke: #ffffff;
    stroke-width: 0.75px;
    stroke-linejoin: round;
  }
  .center-cross { stroke: #0f172a; stroke-width: 0.3; }
  .center-dot { fill: #b91c1c; }
  .center-label {
    font-size: 2.9px;
    font-weight: 600;
    fill: #b91c1c;
    paint-order: stroke;
    stroke: #ffffff;
    stroke-width: 0.85px;
  }
  .disk-note { font-size: 2.5px; fill: #94a3b8; letter-spacing: 0.4px; }
  .guide { fill: none; stroke: #cbd5e1; stroke-width: 0.25; stroke-dasharray: 1.5 2; }
  .north-label { font-size: 4.2px; font-weight: 700; fill: #1d4ed8; }
  .window-label { font-size: 3.2px; fill: #1d4ed8; letter-spacing: 0.6px; }
  .info-text { font-size: 3.0px; fill: #334155; }
  .table-head { font-size: 3.0px; font-weight: 700; fill: #0f172a; }
  .table-cell { font-size: 3.0px; fill: #1e293b; }
  .table-cell.compact { font-size: 2.55px; }
  .footer-text { font-size: 2.7px; fill: #475569; }
  @page { size: A4 portrait; margin: 0; }
  @media screen and (max-width: 620px) {
    .wrap { padding: 0 8px 8mm; }
    .toolbar { max-width: calc(100% - 16px); padding-top: 3mm; }
    .toolbar span { flex: 1 1 100%; order: 3; font-size: 11px; }
    .toolbar button { flex: 1 1 100%; order: 2; margin-left: 0; padding: 3px 8px; }
  }
  @media print {
    body { background: #ffffff; }
    .toolbar { display: none; }
    .wrap { width: auto; padding: 0; }
    .sheet {
      width: 210mm;
      max-width: none;
      height: 297mm;
      aspect-ratio: auto;
      margin: 0;
      box-shadow: none;
    }
    * { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  }
"""


def render_html(
    stars: Sequence[Star],
    latitude: float = 31.2,
    month: int = 3,
    hour: float = 21.0,
    title: str = "旋转星图",
) -> str:
    """生成完整的三页 HTML：星盘、遮罩、当夜星空。"""
    catalog = validate_catalog(stars)
    latitude = validate_latitude(latitude)
    month = validate_month(month)
    hour = validate_hour(hour)
    title = validate_title(title)

    pages = (
        _star_chart_page(catalog, latitude, month, hour, title),
        _mask_page(latitude, title),
        _night_page(catalog, latitude, month, hour, title),
    )
    sections = (
        '<section class="sheet" aria-label="%s">%s</section>'
        % (_esc("%s · 星盘页" % title), pages[0]),
        '<section class="sheet" aria-label="%s">%s</section>'
        % (_esc("%s · 遮罩页" % title), pages[1]),
        '<section class="sheet" aria-label="%s">%s</section>'
        % (_esc("%s · 当夜星空页" % title), pages[2]),
    )
    toolbar = (
        '<header class="toolbar"><strong>%s</strong>'
        "<span>北纬 %s° · %d 月 %s 时 · 3 页 A4</span>"
        "<button type=\"button\" onclick=\"window.print()\">打印 / 另存为 PDF</button>"
        "</header>"
        % (_esc(title), _num(latitude), month, _num(hour))
    )
    return (
        "<!doctype html>\n"
        '<html lang="zh-CN">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<meta name="generator" content="starwheel 0.1.0">\n'
        "<title>%s</title>\n<style>%s</style>\n</head>\n<body>\n"
        '%s\n<main class="wrap">\n%s\n%s\n%s\n</main>\n</body>\n</html>\n'
        % (
            _esc(title),
            _STYLE,
            toolbar,
            sections[0],
            sections[1],
            sections[2],
        )
    )
