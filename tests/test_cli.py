"""命令行入口单元测试。"""

from __future__ import annotations

import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from typing import List, Tuple

from starwheel.cli import main


class CliTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.target = self.root / "旋转星图.html"
        self.old_cwd = Path.cwd()

    def tearDown(self) -> None:
        os.chdir(self.old_cwd)
        self.tmp.cleanup()

    def run_cli(self, argv: List[str]) -> Tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_generate_success(self) -> None:
        code, out, err = self.run_cli(
            [
                "--latitude", "31.2",
                "--month", "3",
                "--hour", "21",
                "--title", "旋转星图",
                "-o", str(self.target),
            ]
        )
        self.assertEqual(code, 0, err)
        self.assertTrue(self.target.exists())
        self.assertIn("已生成", out)

    def test_output_has_three_pages(self) -> None:
        code, _, _ = self.run_cli(["-o", str(self.target)])
        self.assertEqual(code, 0)
        page = self.target.read_text(encoding="utf-8")
        self.assertEqual(page.count('class="sheet"'), 3)
        self.assertIn("星盘页", page)
        self.assertIn("遮罩页", page)
        self.assertIn("当夜星空页", page)

    def test_custom_title_and_parameters(self) -> None:
        code, _, _ = self.run_cli(
            [
                "--latitude", "-45",
                "--month", "12",
                "--hour", "0",
                "--title", "冬季星空",
                "-o", str(self.target),
            ]
        )
        self.assertEqual(code, 0)
        page = self.target.read_text(encoding="utf-8")
        self.assertIn("冬季星空", page)
        self.assertIn("-45", page)
        self.assertIn("12 月", page)

    def test_default_output_path(self) -> None:
        os.chdir(self.root)
        code, out, _ = self.run_cli([])
        self.assertEqual(code, 0)
        self.assertTrue((self.root / "旋转星图.html").exists())
        self.assertIn("旋转星图.html", out)

    def test_latitude_boundaries(self) -> None:
        for latitude in ("-66", "66"):
            code, _, err = self.run_cli(
                ["--latitude", latitude, "-o", str(self.target)]
            )
            self.assertEqual(code, 0, err)

    def test_latitude_out_of_range(self) -> None:
        code, _, err = self.run_cli(["--latitude", "66.1", "-o", str(self.target)])
        self.assertEqual(code, 2)
        self.assertIn("纬度", err)
        self.assertFalse(self.target.exists())

    def test_latitude_not_a_number(self) -> None:
        code, _, err = self.run_cli(["--latitude", "abc", "-o", str(self.target)])
        self.assertEqual(code, 2)
        self.assertIn("纬度必须是数字", err)

    def test_month_out_of_range(self) -> None:
        for month in ("0", "13"):
            code, _, err = self.run_cli(["--month", month, "-o", str(self.target)])
            self.assertEqual(code, 2)
            self.assertIn("月份", err)

    def test_month_not_an_integer(self) -> None:
        code, _, err = self.run_cli(["--month", "3.5", "-o", str(self.target)])
        self.assertEqual(code, 2)
        self.assertIn("月份必须是整数", err)

    def test_hour_out_of_range(self) -> None:
        for hour in ("-1", "24"):
            code, _, err = self.run_cli(["--hour", hour, "-o", str(self.target)])
            self.assertEqual(code, 2)
            self.assertIn("小时", err)

    def test_empty_title(self) -> None:
        code, _, err = self.run_cli(["--title", "   ", "-o", str(self.target)])
        self.assertEqual(code, 2)
        self.assertIn("标题", err)

    def test_title_too_long(self) -> None:
        code, _, err = self.run_cli(
            ["--title", "星" * 41, "-o", str(self.target)]
        )
        self.assertEqual(code, 2)
        self.assertIn("标题", err)

    def test_title_at_max_length(self) -> None:
        code, _, err = self.run_cli(
            ["--title", "星" * 40, "-o", str(self.target)]
        )
        self.assertEqual(code, 0, err)

    def test_help_returns_zero(self) -> None:
        code, out, _ = self.run_cli(["--help"])
        self.assertEqual(code, 0)
        self.assertIn("用法", out)
        self.assertIn("旋转星图", out)

    def test_version_returns_zero(self) -> None:
        code, out, _ = self.run_cli(["--version"])
        self.assertEqual(code, 0)
        self.assertIn("starwheel 0.1.0", out)

    def test_unknown_argument(self) -> None:
        code, _, err = self.run_cli(["--unknown"])
        self.assertEqual(code, 2)
        self.assertIn("错误", err)

    def test_output_is_directory(self) -> None:
        code, _, err = self.run_cli(["-o", str(self.root)])
        self.assertEqual(code, 1)
        self.assertIn("写入输出文件失败", err)

    def test_output_parent_missing(self) -> None:
        code, _, err = self.run_cli(
            ["-o", str(self.root / "missing" / "out.html")]
        )
        self.assertEqual(code, 1)
        self.assertIn("写入输出文件失败", err)

    def test_errors_are_chinese(self) -> None:
        _, _, err = self.run_cli(["--latitude", "99"])
        self.assertIn("错误", err)

    def test_custom_title_is_escaped(self) -> None:
        code, _, _ = self.run_cli(
            ["--title", "<夜间>", "-o", str(self.target)]
        )
        self.assertEqual(code, 0)
        page = self.target.read_text(encoding="utf-8")
        self.assertIn("&lt;夜间&gt;", page)
        self.assertNotIn("<夜间>", page)

    def test_output_contains_polaris(self) -> None:
        code, _, _ = self.run_cli(["-o", str(self.target)])
        self.assertEqual(code, 0)
        page = self.target.read_text(encoding="utf-8")
        self.assertIn("北极星", page)
        self.assertIn("A4 portrait", page)

    def test_success_hint_mentions_print(self) -> None:
        code, out, _ = self.run_cli(["-o", str(self.target)])
        self.assertEqual(code, 0)
        self.assertIn("Ctrl/Cmd + P", out)


if __name__ == "__main__":
    unittest.main()
