"""HTML/SVG 渲染单元测试。"""

from __future__ import annotations

import unittest
from typing import List

from starwheel.data import STARS
from starwheel.model import StarwheelError, visible_stars
from starwheel.render import PAGE_COUNT, render_html


def pages(page: str) -> List[str]:
    return page.split('<section class="sheet"')[1:]


class RenderDocumentTest(unittest.TestCase):
    def setUp(self) -> None:
        self.page = render_html(STARS, latitude=31.2, month=3, hour=21)

    def test_doctype_and_language(self) -> None:
        self.assertTrue(self.page.startswith("<!doctype html>"))
        self.assertIn('<html lang="zh-CN">', self.page)

    def test_exactly_three_pages(self) -> None:
        self.assertEqual(self.page.count('class="sheet"'), PAGE_COUNT)
        self.assertEqual(len(pages(self.page)), 3)

    def test_page_labels(self) -> None:
        chunks = pages(self.page)
        self.assertIn("星盘页", chunks[0])
        self.assertIn("遮罩页", chunks[1])
        self.assertIn("当夜星空页", chunks[2])

    def test_a4_portrait_print_rules(self) -> None:
        self.assertIn("@page { size: A4 portrait; margin: 0; }", self.page)
        self.assertIn("width: 210mm", self.page)
        self.assertIn("height: 297mm", self.page)

    def test_screen_does_not_overflow_horizontally(self) -> None:
        self.assertIn("overflow-x: hidden", self.page)
        self.assertIn("max-width: 100%", self.page)
        self.assertIn("aspect-ratio: 210 / 297", self.page)

    def test_page_break_rules(self) -> None:
        self.assertIn("page-break-after: always", self.page)
        self.assertIn("break-after: page", self.page)

    def test_self_contained_no_external_assets(self) -> None:
        self.assertNotIn("<link", self.page)
        self.assertNotIn("<script src", self.page)
        self.assertNotIn('src="http', self.page)
        self.assertNotIn('href="http', self.page)
        self.assertNotIn("url(http", self.page)
        self.assertNotIn("<img", self.page)

    def test_inline_svg_namespace_is_allowed(self) -> None:
        self.assertIn('xmlns="http://www.w3.org/2000/svg"', self.page)

    def test_print_button_is_inline(self) -> None:
        self.assertIn("window.print()", self.page)

    def test_instructions_present(self) -> None:
        self.assertIn("组装", self.page)
        self.assertIn("使用", self.page)
        self.assertIn("裁剪", self.page)


class StarChartPageTest(unittest.TestCase):
    def setUp(self) -> None:
        self.page = render_html(STARS, latitude=31.2, month=3, hour=21)
        self.chart = pages(self.page)[0]

    def test_polaris_label(self) -> None:
        self.assertIn("北极星", self.chart)

    def test_fifteen_star_labels(self) -> None:
        self.assertEqual(self.chart.count('class="star-label"'), 15)

    def test_24_hour_ticks(self) -> None:
        self.assertEqual(self.chart.count('class="tick-major"'), 12)
        self.assertEqual(self.chart.count('class="tick-minor"'), 12)

    def test_12_hour_labels(self) -> None:
        self.assertEqual(self.chart.count('class="hour-label"'), 12)

    def test_12_month_ticks_and_labels(self) -> None:
        self.assertEqual(self.chart.count('class="month-tick"'), 12)
        self.assertEqual(self.chart.count('class="month-label"'), 12)

    def test_center_cross_exists(self) -> None:
        self.assertGreaterEqual(self.chart.count('class="center-cross"'), 2)

    def test_northern_hemisphere_note(self) -> None:
        self.assertIn("北天半球", self.chart)

    def test_title_and_parameters_rendered(self) -> None:
        self.assertIn("旋转星图", self.chart)
        self.assertIn("31.2", self.chart)


class MaskPageTest(unittest.TestCase):
    def setUp(self) -> None:
        self.page = render_html(STARS, latitude=31.2, month=3, hour=21)
        self.mask = pages(self.page)[1]

    def test_elliptical_window(self) -> None:
        self.assertIn("<ellipse", self.mask)
        self.assertIn('stroke-dasharray="2.4 1.8"', self.mask)

    def test_center_cross(self) -> None:
        self.assertGreaterEqual(self.mask.count('class="center-cross"'), 2)
        self.assertIn('class="center-dot"', self.mask)

    def test_window_label_and_north_mark(self) -> None:
        self.assertIn("可见天空窗口", self.mask)
        self.assertIn(">北<", self.mask)

    def test_latitude_is_shown(self) -> None:
        self.assertIn("北纬 31.2", self.mask)

    def test_window_changes_with_latitude(self) -> None:
        low = pages(render_html(STARS, latitude=0.0, month=3, hour=21))[1]
        high = pages(render_html(STARS, latitude=60.0, month=3, hour=21))[1]
        self.assertNotEqual(low, high)

    def test_outside_window_is_white(self) -> None:
        self.assertIn('fill="#ffffff"', self.mask)


class NightPageTest(unittest.TestCase):
    def setUp(self) -> None:
        self.page = render_html(STARS, latitude=31.2, month=1, hour=21)
        self.night = pages(self.page)[2]
        self.visible = visible_stars(STARS, 31.2, 1, 21)

    def test_table_headers(self) -> None:
        for header in ("名称", "赤经", "赤纬", "方位", "高度", "星等"):
            self.assertIn(header, self.night)

    def test_visible_star_appears(self) -> None:
        self.assertIn("天狼星", self.night)

    def test_all_visible_stars_are_listed(self) -> None:
        self.assertGreaterEqual(
            self.night.count('class="table-cell'), 6 * len(self.visible)
        )

    def test_rotation_angle_and_sidereal_time(self) -> None:
        self.assertIn("恒星时", self.night)
        self.assertIn("星盘旋转角", self.night)

    def test_all_visible_note(self) -> None:
        self.assertIn("已全部列出", self.night)

    def test_summer_page_excludes_sirius(self) -> None:
        summer = pages(render_html(STARS, latitude=31.2, month=7, hour=21))[2]
        self.assertNotIn("天狼星", summer)


class TitleEscapingTest(unittest.TestCase):
    def test_title_is_escaped(self) -> None:
        page = render_html(STARS, title='<星图> & "夜空"')
        self.assertIn("&lt;星图&gt; &amp; &quot;夜空&quot;", page)
        self.assertNotIn("<星图>", page)
        self.assertNotIn('<script>', page)

    def test_title_appears_in_title_tag(self) -> None:
        page = render_html(STARS, title="我的星图")
        self.assertIn("<title>我的星图</title>", page)

    def test_ampersand_in_title_is_escaped(self) -> None:
        page = render_html(STARS, title="A&B")
        self.assertIn("A&amp;B", page)


class RenderValidationTest(unittest.TestCase):
    def test_too_few_stars_rejected(self) -> None:
        with self.assertRaises(StarwheelError):
            render_html(STARS[:3])

    def test_invalid_latitude_rejected(self) -> None:
        with self.assertRaises(StarwheelError):
            render_html(STARS, latitude=70.0)

    def test_invalid_month_rejected(self) -> None:
        with self.assertRaises(StarwheelError):
            render_html(STARS, month=13)

    def test_invalid_hour_rejected(self) -> None:
        with self.assertRaises(StarwheelError):
            render_html(STARS, hour=24)

    def test_invalid_title_rejected(self) -> None:
        with self.assertRaises(StarwheelError):
            render_html(STARS, title="")

    def test_non_star_sequence_rejected(self) -> None:
        with self.assertRaises(StarwheelError):
            render_html(["星"])  # type: ignore[list-item]


class RenderBoundaryTest(unittest.TestCase):
    def test_latitude_boundaries_render(self) -> None:
        for latitude in (-66.0, 66.0):
            page = render_html(STARS, latitude=latitude, month=1, hour=0)
            self.assertEqual(page.count('class="sheet"'), 3)

    def test_month_and_hour_boundaries_render(self) -> None:
        page = render_html(STARS, latitude=0.0, month=12, hour=23)
        self.assertEqual(page.count('class="sheet"'), 3)

    def test_custom_title_renders(self) -> None:
        page = render_html(STARS, title="春季星空")
        self.assertIn("春季星空", page)


if __name__ == "__main__":
    unittest.main()
