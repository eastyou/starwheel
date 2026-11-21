"""命令行入口：生成 A4 可打印旋转星图。"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import NoReturn, Optional, Sequence

from .data import STARS
from .model import (
    MAX_HOUR,
    MAX_LATITUDE,
    MAX_MONTH,
    MAX_TITLE_LENGTH,
    MIN_HOUR,
    MIN_LATITUDE,
    MIN_MONTH,
    MIN_TITLE_LENGTH,
    StarwheelError,
)
from .render import render_html


class StarwheelArgumentParser(argparse.ArgumentParser):
    """把 argparse 的错误统一成中文并返回退出码 2。"""

    def format_usage(self) -> str:
        return super().format_usage().replace("usage: ", "用法: ", 1)

    def format_help(self) -> str:
        return super().format_help().replace("usage: ", "用法: ", 1)

    def error(self, message: str) -> NoReturn:
        detail = message
        if detail.startswith("argument "):
            detail = "参数 " + detail[len("argument ") :]
        detail = detail.replace("expected one argument", "需要一个值")
        detail = detail.replace("unrecognized arguments:", "无法识别的参数：")
        self.print_usage(sys.stderr)
        print("错误: %s" % detail, file=sys.stderr)
        raise SystemExit(2)


def _latitude_arg(text: str) -> float:
    try:
        value = float(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("纬度必须是数字") from exc
    if not math.isfinite(value):
        raise argparse.ArgumentTypeError("纬度必须是有限数字")
    if not MIN_LATITUDE <= value <= MAX_LATITUDE:
        raise argparse.ArgumentTypeError(
            "纬度必须在 %g~%g 度之间" % (MIN_LATITUDE, MAX_LATITUDE)
        )
    return value


def _month_arg(text: str) -> int:
    try:
        value = int(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("月份必须是整数") from exc
    if not MIN_MONTH <= value <= MAX_MONTH:
        raise argparse.ArgumentTypeError(
            "月份必须在 %d~%d 之间" % (MIN_MONTH, MAX_MONTH)
        )
    return value


def _hour_arg(text: str) -> int:
    try:
        value = int(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("小时必须是整数") from exc
    if not MIN_HOUR <= value <= MAX_HOUR:
        raise argparse.ArgumentTypeError(
            "小时必须在 %g~%g 之间" % (MIN_HOUR, MAX_HOUR)
        )
    return value


def _title_arg(text: str) -> str:
    value = text.strip()
    if not MIN_TITLE_LENGTH <= len(value) <= MAX_TITLE_LENGTH:
        raise argparse.ArgumentTypeError(
            "标题长度必须在 %d~%d 个字符之间"
            % (MIN_TITLE_LENGTH, MAX_TITLE_LENGTH)
        )
    return value


def build_parser() -> argparse.ArgumentParser:
    """构造命令行解析器。"""
    parser = StarwheelArgumentParser(
        prog="starwheel",
        description="旋转星图：一条命令生成 A4 可打印的星盘、遮罩与当夜星空页",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例：\n"
            "  python -m starwheel --latitude 31.2 --month 3 --hour 21 "
            "--title 旋转星图 -o examples/旋转星图.html"
        ),
    )
    parser.add_argument(
        "--version", action="version", version="starwheel 0.1.0"
    )
    parser.add_argument(
        "--latitude",
        type=_latitude_arg,
        default=31.2,
        metavar="纬度",
        help="观测纬度，范围 -66~66，默认 31.2",
    )
    parser.add_argument(
        "--month",
        type=_month_arg,
        default=3,
        metavar="月份",
        help="月份，1~12，默认 3",
    )
    parser.add_argument(
        "--hour",
        type=_hour_arg,
        default=21,
        metavar="小时",
        help="整点时刻，0~23，默认 21",
    )
    parser.add_argument(
        "--title",
        type=_title_arg,
        default="旋转星图",
        metavar="标题",
        help="页面标题，1~40 个字符",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="旋转星图.html",
        metavar="输出文件",
        help="输出 HTML 路径，默认 旋转星图.html",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """执行命令行流程：成功 0，参数错误 2，读写失败 1。"""
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        code = exc.code
        if isinstance(code, int):
            return code
        return 0 if code is None else 2

    try:
        page = render_html(
            STARS,
            latitude=args.latitude,
            month=args.month,
            hour=args.hour,
            title=args.title,
        )
    except StarwheelError as exc:
        print("错误: %s" % exc, file=sys.stderr)
        return 2

    try:
        Path(args.output).write_text(page, encoding="utf-8")
    except OSError as exc:
        print("错误: 写入输出文件失败: %s" % exc, file=sys.stderr)
        return 1

    print("已生成 %s：3 页 A4（星盘、遮罩、当夜星空）" % args.output)
    print("用浏览器打开后按 Ctrl/Cmd + P，纸张选 A4 纵向，边距选无即可打印")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
