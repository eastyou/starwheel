"""数据模型、投影与可见性计算单元测试。"""

from __future__ import annotations

import math
import unittest
from typing import List

from starwheel.data import STARS
from starwheel.model import (
    MAX_LATITUDE,
    MAX_MAGNITUDE,
    MAX_MONTH,
    MIN_LATITUDE,
    MaskWindow,
    Star,
    StarwheelError,
    altitude_degrees,
    azimuth_degrees,
    compass_direction,
    hour_angle_hours,
    local_sidereal_hours,
    mask_window,
    project_star,
    rotation_angle,
    solar_ra_hours,
    star_radius,
    validate_catalog,
    validate_hour,
    validate_latitude,
    validate_month,
    validate_title,
    visible_stars,
)


def make_star(index: int, name: str = "") -> Star:
    return Star(
        name=name or ("测试星%d" % index),
        ra_hours=(index % 24) + 0.25,
        dec_degrees=(index % 80) - 40.0,
        magnitude=1.0,
    )


def make_catalog(count: int = 50) -> List[Star]:
    return [make_star(index) for index in range(count)]


class StarValidationTest(unittest.TestCase):
    def test_valid_star(self) -> None:
        star = Star("测试星", 6.5, 20.0, 2.5)
        self.assertEqual(star.name, "测试星")
        self.assertEqual(star.ra_hours, 6.5)

    def test_name_is_stripped(self) -> None:
        self.assertEqual(Star("  天狼星  ", 6.7, -16.7, -1.4).name, "天狼星")

    def test_empty_name_rejected(self) -> None:
        with self.assertRaises(StarwheelError):
            Star("   ", 1.0, 1.0, 1.0)

    def test_non_text_name_rejected(self) -> None:
        with self.assertRaises(StarwheelError):
            Star(123, 1.0, 1.0, 1.0)  # type: ignore[arg-type]

    def test_negative_ra_rejected(self) -> None:
        with self.assertRaises(StarwheelError):
            Star("测试星", -0.1, 0.0, 1.0)

    def test_ra_above_24_rejected(self) -> None:
        with self.assertRaises(StarwheelError):
            Star("测试星", 24.1, 0.0, 1.0)

    def test_ra_24_is_allowed(self) -> None:
        self.assertEqual(Star("测试星", 24.0, 0.0, 1.0).ra_hours, 24.0)

    def test_dec_above_90_rejected(self) -> None:
        with self.assertRaises(StarwheelError):
            Star("测试星", 0.0, 90.1, 1.0)

    def test_dec_below_minus_90_rejected(self) -> None:
        with self.assertRaises(StarwheelError):
            Star("测试星", 0.0, -90.1, 1.0)

    def test_dec_boundaries_allowed(self) -> None:
        self.assertEqual(Star("南星", 0.0, -90.0, 1.0).dec_degrees, -90.0)
        self.assertEqual(Star("北星", 0.0, 90.0, 1.0).dec_degrees, 90.0)

    def test_magnitude_too_faint_rejected(self) -> None:
        with self.assertRaises(StarwheelError):
            Star("测试星", 0.0, 0.0, MAX_MAGNITUDE + 0.01)

    def test_magnitude_boundary_allowed(self) -> None:
        self.assertEqual(
            Star("测试星", 0.0, 0.0, MAX_MAGNITUDE).magnitude, MAX_MAGNITUDE
        )

    def test_nan_magnitude_rejected(self) -> None:
        with self.assertRaises(StarwheelError):
            Star("测试星", 0.0, 0.0, float("nan"))

    def test_bool_ra_rejected(self) -> None:
        with self.assertRaises(StarwheelError):
            Star("测试星", True, 0.0, 1.0)  # type: ignore[arg-type]

    def test_northern_property(self) -> None:
        self.assertTrue(Star("北星", 0.0, 0.0, 1.0).is_northern)
        self.assertFalse(Star("南星", 0.0, -0.1, 1.0).is_northern)


class CatalogValidationTest(unittest.TestCase):
    def test_too_few_stars_rejected(self) -> None:
        with self.assertRaises(StarwheelError):
            validate_catalog(make_catalog(10))

    def test_duplicate_names_rejected(self) -> None:
        stars = make_catalog(50)
        stars[-1] = make_star(0)
        with self.assertRaises(StarwheelError):
            validate_catalog(stars)

    def test_non_star_item_rejected(self) -> None:
        stars: List[object] = list(make_catalog(50))
        stars[0] = "不是星"
        with self.assertRaises(StarwheelError):
            validate_catalog(stars)  # type: ignore[arg-type]

    def test_text_input_rejected(self) -> None:
        with self.assertRaises(StarwheelError):
            validate_catalog("星表")  # type: ignore[arg-type]

    def test_valid_catalog_returned_as_tuple(self) -> None:
        stars = make_catalog(50)
        catalog = validate_catalog(stars)
        self.assertIsInstance(catalog, tuple)
        self.assertEqual(len(catalog), 50)


class ProjectionTest(unittest.TestCase):
    def test_north_pole_projects_to_origin(self) -> None:
        self.assertEqual(project_star(0.0, 90.0), (0.0, 0.0))

    def test_equator_projects_to_unit_circle(self) -> None:
        x, y = project_star(0.0, 0.0)
        self.assertAlmostEqual(math.hypot(x, y), 1.0, places=9)

    def test_ra_rotates_counterclockwise(self) -> None:
        x, y = project_star(6.0, 0.0)
        self.assertAlmostEqual(x, 0.0, places=9)
        self.assertAlmostEqual(y, 1.0, places=9)

    def test_dec_60_formula(self) -> None:
        x, y = project_star(0.0, 60.0)
        self.assertAlmostEqual(math.hypot(x, y), math.tan(math.radians(15.0)), places=9)

    def test_dec_45_formula(self) -> None:
        x, y = project_star(0.0, 45.0)
        self.assertAlmostEqual(math.hypot(x, y), math.tan(math.radians(22.5)), places=9)

    def test_dec_30_formula(self) -> None:
        x, y = project_star(0.0, 30.0)
        self.assertAlmostEqual(math.hypot(x, y), math.tan(math.radians(30.0)), places=9)

    def test_southern_star_is_clamped_to_unit_circle(self) -> None:
        x, y = project_star(0.0, -30.0)
        self.assertAlmostEqual(math.hypot(x, y), 1.0, places=9)

    def test_ra_24_equals_ra_0(self) -> None:
        self.assertEqual(project_star(24.0, 0.0), project_star(0.0, 0.0))

    def test_polaris_is_near_center(self) -> None:
        polaris = next(star for star in STARS if star.name == "北极星")
        x, y = project_star(polaris.ra_hours, polaris.dec_degrees)
        self.assertLess(math.hypot(x, y), 0.01)

    def test_all_catalog_stars_inside_unit_circle(self) -> None:
        for star in STARS:
            x, y = project_star(star.ra_hours, star.dec_degrees)
            self.assertLessEqual(math.hypot(x, y), 1.0 + 1e-9, star.name)

    def test_invalid_ra_rejected(self) -> None:
        with self.assertRaises(StarwheelError):
            project_star(-0.1, 0.0)

    def test_invalid_dec_rejected(self) -> None:
        with self.assertRaises(StarwheelError):
            project_star(0.0, 91.0)

    def test_nan_input_rejected(self) -> None:
        with self.assertRaises(StarwheelError):
            project_star(float("nan"), 0.0)

    def test_text_input_rejected(self) -> None:
        with self.assertRaises(StarwheelError):
            project_star("6", 0.0)  # type: ignore[arg-type]


class MagnitudeTest(unittest.TestCase):
    def test_bright_star_is_larger(self) -> None:
        self.assertGreater(star_radius(-1.46), star_radius(3.5))

    def test_radius_has_upper_bound(self) -> None:
        self.assertLessEqual(star_radius(-1.46), 2.2)

    def test_radius_has_lower_bound(self) -> None:
        self.assertGreaterEqual(star_radius(3.5), 0.7)

    def test_invalid_magnitude_rejected(self) -> None:
        with self.assertRaises(StarwheelError):
            star_radius(4.0)


class TimeAndRotationTest(unittest.TestCase):
    def test_solar_ra_is_in_range(self) -> None:
        for month in range(1, MAX_MONTH + 1):
            value = solar_ra_hours(month)
            self.assertGreaterEqual(value, 0.0)
            self.assertLess(value, 24.0)

    def test_solar_ra_differs_by_season(self) -> None:
        self.assertNotAlmostEqual(solar_ra_hours(3), solar_ra_hours(9), places=2)

    def test_local_sidereal_is_in_range(self) -> None:
        for hour in (0, 6, 12, 23):
            value = local_sidereal_hours(3, hour)
            self.assertGreaterEqual(value, 0.0)
            self.assertLess(value, 24.0)

    def test_one_hour_advances_sidereal_by_one_hour(self) -> None:
        before = local_sidereal_hours(5, 20)
        after = local_sidereal_hours(5, 21)
        self.assertAlmostEqual((after - before) % 24.0, 1.0, places=9)

    def test_rotation_angle_is_in_range(self) -> None:
        for month in range(1, MAX_MONTH + 1):
            for hour in (0, 11, 23):
                value = rotation_angle(month, hour)
                self.assertGreaterEqual(value, 0.0)
                self.assertLess(value, 360.0)

    def test_one_hour_rotates_fifteen_degrees(self) -> None:
        before = rotation_angle(3, 20)
        after = rotation_angle(3, 21)
        self.assertAlmostEqual((after - before) % 360.0, 345.0, places=6)

    def test_seasons_have_different_rotation(self) -> None:
        self.assertNotAlmostEqual(rotation_angle(1, 21), rotation_angle(7, 21), places=2)

    def test_hour_angle_same_ra_is_zero(self) -> None:
        self.assertAlmostEqual(hour_angle_hours(8.0, 8.0), 0.0)

    def test_hour_angle_range(self) -> None:
        for ra in (0.0, 6.0, 12.0, 18.0, 23.5):
            value = hour_angle_hours(8.0, ra)
            self.assertGreaterEqual(value, -12.0)
            self.assertLessEqual(value, 12.0)

    def test_invalid_month_rejected(self) -> None:
        with self.assertRaises(StarwheelError):
            local_sidereal_hours(0, 21)

    def test_invalid_hour_rejected(self) -> None:
        with self.assertRaises(StarwheelError):
            rotation_angle(3, 24)


class HorizontalCoordinateTest(unittest.TestCase):
    # 角度以度为单位，1e-4 度约 0.36 角秒，远严于教学用途所需精度，
    # 同时避免不同平台 libm 的最后一位差异造成假失败。
    ANGLE_DELTA = 1e-4

    def test_meridian_star_reaches_zenith(self) -> None:
        altitude = altitude_degrees(10.0, 31.2, 31.2, 10.0)
        self.assertAlmostEqual(altitude, 90.0, delta=self.ANGLE_DELTA)

    def test_meridian_equatorial_star_is_south(self) -> None:
        self.assertAlmostEqual(
            azimuth_degrees(10.0, 0.0, 31.2, 10.0), 180.0, delta=self.ANGLE_DELTA
        )

    def test_meridian_circumpolar_star_is_north(self) -> None:
        self.assertAlmostEqual(
            azimuth_degrees(10.0, 60.0, 31.2, 10.0), 0.0, delta=self.ANGLE_DELTA
        )

    def test_altitude_formula_at_meridian(self) -> None:
        altitude = altitude_degrees(10.0, 0.0, 31.2, 10.0)
        self.assertAlmostEqual(
            altitude, 90.0 - 31.2, delta=self.ANGLE_DELTA
        )

    def test_sirius_is_below_horizon_in_summer_evening(self) -> None:
        sidereal = local_sidereal_hours(7, 21)
        altitude = altitude_degrees(6.7525, -16.7161, 31.2, sidereal)
        self.assertLess(altitude, 0.0)

    def test_invalid_latitude_rejected(self) -> None:
        with self.assertRaises(StarwheelError):
            altitude_degrees(0.0, 0.0, 70.0, 0.0)

    def test_invalid_dec_rejected(self) -> None:
        with self.assertRaises(StarwheelError):
            altitude_degrees(0.0, 100.0, 31.2, 0.0)

    def test_invalid_ra_rejected(self) -> None:
        with self.assertRaises(StarwheelError):
            altitude_degrees(-1.0, 0.0, 31.2, 0.0)


class CompassTest(unittest.TestCase):
    def test_eight_directions(self) -> None:
        expected = ("北", "东北", "东", "东南", "南", "西南", "西", "西北")
        for index, name in enumerate(expected):
            self.assertEqual(compass_direction(index * 45.0), name)

    def test_near_north_wraps_around(self) -> None:
        self.assertEqual(compass_direction(359.0), "北")

    def test_negative_azimuth_is_normalized(self) -> None:
        self.assertEqual(compass_direction(-90.0), "西")


class VisibilityTest(unittest.TestCase):
    def test_winter_evening_includes_sirius(self) -> None:
        names = {item.star.name for item in visible_stars(STARS, 31.2, 1, 21)}
        self.assertIn("天狼星", names)

    def test_summer_evening_excludes_sirius(self) -> None:
        names = {item.star.name for item in visible_stars(STARS, 31.2, 7, 21)}
        self.assertNotIn("天狼星", names)

    def test_visible_list_is_sorted_by_magnitude(self) -> None:
        items = visible_stars(STARS, 31.2, 3, 21)
        magnitudes = [item.star.magnitude for item in items]
        self.assertEqual(magnitudes, sorted(magnitudes))

    def test_visible_altitudes_are_above_horizon(self) -> None:
        for item in visible_stars(STARS, 31.2, 3, 21):
            self.assertGreaterEqual(item.altitude, 0.0, item.star.name)

    def test_min_altitude_filter(self) -> None:
        items = visible_stars(STARS, 31.2, 1, 21, min_altitude=60.0)
        self.assertTrue(items)
        for item in items:
            self.assertGreaterEqual(item.altitude, 60.0)

    def test_visible_stars_accepts_single_star(self) -> None:
        sirius = next(star for star in STARS if star.name == "天狼星")
        items = visible_stars((sirius,), 31.2, 1, 21)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].star.name, "天狼星")

    def test_direction_property_is_text(self) -> None:
        item = visible_stars(STARS, 31.2, 1, 21)[0]
        self.assertIsInstance(item.direction, str)
        self.assertTrue(item.direction)

    def test_invalid_altitude_threshold_rejected(self) -> None:
        with self.assertRaises(StarwheelError):
            visible_stars(STARS, 31.2, 1, 21, min_altitude=100.0)


class MaskWindowTest(unittest.TestCase):
    def test_window_axes_are_in_unit_range(self) -> None:
        for latitude in (MIN_LATITUDE, -30.0, 0.0, 31.2, 60.0, MAX_LATITUDE):
            window = mask_window(latitude)
            self.assertGreater(window.rx, 0.0)
            self.assertLessEqual(window.rx, 1.0)
            self.assertGreater(window.ry, 0.0)
            self.assertLessEqual(window.ry, 1.0)

    def test_high_latitude_has_taller_window(self) -> None:
        self.assertGreater(mask_window(66.0).ry, mask_window(0.0).ry)

    def test_window_is_symmetric_in_hemispheres(self) -> None:
        north = mask_window(45.0)
        south = mask_window(-45.0)
        self.assertEqual(north, south)

    def test_invalid_window_axis_rejected(self) -> None:
        with self.assertRaises(StarwheelError):
            MaskWindow(0.0, 0.5)

    def test_window_axis_above_one_rejected(self) -> None:
        with self.assertRaises(StarwheelError):
            MaskWindow(1.1, 0.5)


class ParameterValidationTest(unittest.TestCase):
    def test_latitude_boundaries(self) -> None:
        self.assertEqual(validate_latitude(MIN_LATITUDE), MIN_LATITUDE)
        self.assertEqual(validate_latitude(MAX_LATITUDE), MAX_LATITUDE)

    def test_latitude_out_of_range_rejected(self) -> None:
        for latitude in (MIN_LATITUDE - 0.1, MAX_LATITUDE + 0.1):
            with self.assertRaises(StarwheelError):
                validate_latitude(latitude)

    def test_month_boundaries(self) -> None:
        self.assertEqual(validate_month(1), 1)
        self.assertEqual(validate_month(12), 12)

    def test_month_out_of_range_rejected(self) -> None:
        for month in (0, 13):
            with self.assertRaises(StarwheelError):
                validate_month(month)

    def test_month_must_be_integer(self) -> None:
        with self.assertRaises(StarwheelError):
            validate_month(3.5)  # type: ignore[arg-type]

    def test_hour_boundaries(self) -> None:
        self.assertEqual(validate_hour(0), 0.0)
        self.assertEqual(validate_hour(23), 23.0)

    def test_hour_out_of_range_rejected(self) -> None:
        for hour in (-1, 24):
            with self.assertRaises(StarwheelError):
                validate_hour(hour)

    def test_title_boundaries(self) -> None:
        self.assertEqual(validate_title(" 星 "), "星")
        self.assertEqual(len(validate_title("星" * 40)), 40)

    def test_title_empty_rejected(self) -> None:
        with self.assertRaises(StarwheelError):
            validate_title("   ")

    def test_title_too_long_rejected(self) -> None:
        with self.assertRaises(StarwheelError):
            validate_title("星" * 41)

    def test_title_must_be_text(self) -> None:
        with self.assertRaises(StarwheelError):
            validate_title(123)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
