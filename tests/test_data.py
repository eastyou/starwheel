"""亮星星表单元测试。"""

from __future__ import annotations

import math
import unittest

from starwheel.data import NORTHERN_STARS, STARS
from starwheel.model import MAX_MAGNITUDE, project_star, validate_catalog


class StarCatalogTest(unittest.TestCase):
    def test_catalog_has_at_least_fifty_stars(self) -> None:
        self.assertGreaterEqual(len(STARS), 50)

    def test_catalog_names_are_unique(self) -> None:
        names = [star.name for star in STARS]
        self.assertEqual(len(names), len(set(names)))

    def test_catalog_names_are_non_empty_text(self) -> None:
        for star in STARS:
            self.assertIsInstance(star.name, str)
            self.assertTrue(star.name.strip())

    def test_catalog_names_use_chinese_characters(self) -> None:
        for star in STARS:
            self.assertTrue(
                any("\u4e00" <= char <= "\u9fff" for char in star.name),
                star.name,
            )

    def test_ra_hours_are_in_range(self) -> None:
        for star in STARS:
            self.assertGreaterEqual(star.ra_hours, 0.0, star.name)
            self.assertLessEqual(star.ra_hours, 24.0, star.name)

    def test_dec_degrees_are_in_range(self) -> None:
        for star in STARS:
            self.assertGreaterEqual(star.dec_degrees, -90.0, star.name)
            self.assertLessEqual(star.dec_degrees, 90.0, star.name)

    def test_magnitudes_are_bright_enough(self) -> None:
        for star in STARS:
            self.assertLessEqual(star.magnitude, MAX_MAGNITUDE, star.name)

    def test_contains_polaris(self) -> None:
        names = {star.name for star in STARS}
        self.assertIn("北极星", names)

    def test_contains_sirius(self) -> None:
        names = {star.name for star in STARS}
        self.assertIn("天狼星", names)

    def test_contains_all_seven_big_dipper_stars(self) -> None:
        names = {star.name for star in STARS}
        for name in ("天枢", "天璇", "天玑", "天权", "玉衡", "开阳", "摇光"):
            self.assertIn(name, names)

    def test_contains_orion_main_stars(self) -> None:
        names = {star.name for star in STARS}
        for name in ("参宿一", "参宿二", "参宿三", "参宿四", "参宿五", "参宿六", "参宿七"):
            self.assertIn(name, names)

    def test_polaris_dec_is_near_north_pole(self) -> None:
        polaris = next(star for star in STARS if star.name == "北极星")
        self.assertGreater(polaris.dec_degrees, 89.0)

    def test_sirius_is_brighter_than_first_magnitude(self) -> None:
        sirius = next(star for star in STARS if star.name == "天狼星")
        self.assertLess(sirius.magnitude, 0.0)

    def test_known_sirius_coordinates(self) -> None:
        sirius = next(star for star in STARS if star.name == "天狼星")
        self.assertAlmostEqual(sirius.ra_hours, 6.7525, places=4)
        self.assertAlmostEqual(sirius.dec_degrees, -16.7161, places=4)

    def test_known_vega_coordinates(self) -> None:
        vega = next(star for star in STARS if star.name == "织女星")
        self.assertAlmostEqual(vega.ra_hours, 18.6156, places=4)
        self.assertAlmostEqual(vega.dec_degrees, 38.7837, places=4)

    def test_known_betelgeuse_coordinates(self) -> None:
        betelgeuse = next(star for star in STARS if star.name == "参宿四")
        self.assertAlmostEqual(betelgeuse.ra_hours, 5.9195, places=4)
        self.assertAlmostEqual(betelgeuse.dec_degrees, 7.4071, places=4)

    def test_northern_catalog_is_large_enough(self) -> None:
        self.assertGreaterEqual(len(NORTHERN_STARS), 50)

    def test_northern_catalog_has_no_southern_stars(self) -> None:
        for star in NORTHERN_STARS:
            self.assertGreaterEqual(star.dec_degrees, 0.0, star.name)

    def test_all_projected_stars_stay_inside_unit_circle(self) -> None:
        for star in STARS:
            x, y = project_star(star.ra_hours, star.dec_degrees)
            self.assertLessEqual(math.hypot(x, y), 1.0 + 1e-9, star.name)

    def test_all_magnitudes_are_finite(self) -> None:
        for star in STARS:
            self.assertTrue(math.isfinite(star.magnitude), star.name)

    def test_validate_catalog_accepts_stars(self) -> None:
        catalog = validate_catalog(STARS)
        self.assertIsInstance(catalog, tuple)
        self.assertEqual(len(catalog), len(STARS))


if __name__ == "__main__":
    unittest.main()
