# starwheel

[![CI](https://github.com/eastyou/starwheel/actions/workflows/ci.yml/badge.svg)](https://github.com/eastyou/starwheel/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%2B-brightgreen.svg)](pyproject.toml)

一条命令生成 A4 可打印的**旋转星图（planisphere）**：星盘页、遮罩页、当夜星空页各一页。零第三方依赖、不联网、打印裁剪后即可组装使用。

星盘采用北天极极射赤面投影，外圈 24 小时刻度、内圈 12 个月份刻度；转动星盘并盖上按纬度裁好的遮罩，就能看到指定月份和时刻的可见星空。第三页同时给出当夜可见亮星表，便于核对名称、方位、高度与星等。

## 特性

- **三页 A4**：星盘、遮罩、当夜星空，固定输出，不再拼接额外页面
- **真实亮星表**：68 颗亮星，含北极星、天狼星、北斗七星、猎户座主要星等
- **极射赤面投影**：`r = tan((90° − δ) / 2)`，星点随赤经绕圆心旋转
- **星等区分大小**：最亮约 15 颗标中文名，中心标注北极星
- **纬度遮罩**：按 `--latitude` 生成椭圆窗口、裁剪线与中心十字
- **当夜星空表**：按 `--month/--hour` 估算恒星时与旋转角，列出名称、赤经、赤纬、方位、高度、星等
- **自包含 HTML**：内联 CSS/SVG，无网络资源；屏幕自适应不横向溢出
- **真实毫米打印**：`@page A4 portrait`，`210mm × 297mm`，打印即得实际尺寸
- **安全转义**：标题、星名等文本全部 HTML 转义
- **169 个单元测试**：覆盖星表、投影、旋转角、纬度边界、遮罩、可见性、转义、页数与 CLI 退出码

## 安装

```bash
pip install starwheel
```

也可以直接使用源码，在项目目录中运行：

```bash
python -m starwheel --help
```

要求 Python 3.9+，仅使用标准库。

## 用法

```bash
python -m starwheel --latitude 31.2 --month 3 --hour 21 --title 旋转星图 -o examples/旋转星图.html
```

生成后直接用浏览器打开 HTML。示例文件见 [`examples/旋转星图.html`](examples/旋转星图.html)。

### 参数

| 参数 | 说明 | 默认 |
| --- | --- | --- |
| `--latitude` | 观测纬度，范围 `-66~66` | `31.2` |
| `--month` | 月份，`1~12` | `3` |
| `--hour` | 整点时刻，`0~23` | `21` |
| `--title` | 页面标题，1~40 个字符 | `旋转星图` |
| `-o, --output` | 输出 HTML 路径 | `旋转星图.html` |
| `--version` | 显示版本 | - |

退出码：

- `0`：生成成功
- `2`：参数或数据不合法（中文错误提示）
- `1`：写入输出文件失败（如目录不存在、目标是目录、无权限）

## 打印、裁剪与组装

1. 用浏览器打开生成的 HTML，按 `Ctrl/Cmd + P`。
2. 纸张选 **A4 纵向**，边距选 **无**，勾选「背景图形 / Background graphics」。
3. 依次打印三页：星盘页、遮罩页、当夜星空页。建议使用 160g 以上的卡纸。
4. 沿星盘页最外圈实线剪下圆盘；沿遮罩页的蓝色虚线椭圆剪开，保留中心十字与「北」字。
5. 在星盘圆心（北极星处）打一个小孔，用图钉或铆钉穿过遮罩中心十字，使遮罩覆盖在星盘上。
6. 转动下层星盘，使**当天月份**刻度对准**当前小时**刻度；遮罩窗口内就是当夜可见星空。
7. 用第 3 页的当夜星空表核对亮星名称、方位与高度。方位以正北为 `0°`、顺时针增加，高度 `0°` 为地平线。

> 星盘页绘制赤纬 ≥ 0° 的北天亮星；天狼星、参宿七等南天亮星保留在星表中，并参与第 3 页的可见性计算。极射投影半径超出单位圆时会在边界截断，避免星点画到圆盘外。

## 星表来源

星表位于 [`starwheel/data.py`](starwheel/data.py)，共 **68 颗**，包含中文名、赤经（小时）、赤纬（度）和视星等。坐标依据公开亮星数据（如 Hipparcos/Tycho、Yale Bright Star Catalog 等）人工整理为 J2000.0 近似值，赤经与赤纬保留 4 位小数，星等取视星等并限制在 `≤ 3.5`。数据用于教学、打印和肉眼观测辅助，不用于精密星历、天文导航或专业测量。

星表在导入时通过 `validate_catalog` 校验：至少 50 颗、名称唯一、赤经 `0~24` 小时、赤纬 `-90~90` 度、视星等 `≤ 3.5`。

## 项目结构

```text
starwheel/
├── starwheel/
│   ├── __init__.py    # 包入口与公开 API
│   ├── __main__.py    # python -m starwheel
│   ├── cli.py         # 参数校验与退出码
│   ├── data.py        # 68 颗真实亮星
│   ├── model.py       # 星表校验、投影、恒星时、可见性、遮罩窗口
│   └── render.py      # 三页 A4 自包含 HTML/SVG
├── tests/             # 169 个 unittest
│   ├── test_cli.py
│   ├── test_data.py
│   ├── test_model.py
│   └── test_render.py
├── examples/          # 示例输出
├── .github/workflows/ci.yml
├── pyproject.toml
├── LICENSE
└── README.md
```

## 开发

运行全部测试：

```bash
python -m unittest discover -s tests -v
```

重新生成示例：

```bash
python -m starwheel --latitude 31.2 --month 3 --hour 21 --title 旋转星图 -o examples/旋转星图.html
```

CI 在 Ubuntu / macOS / Windows 上测试 Python 3.10 与 3.13，并额外覆盖 Ubuntu 22.04 + Python 3.9；单测之后会执行 CLI 冒烟、HTML 内容断言和非法参数退出码检查。

## 许可证

[MIT](LICENSE) © 2026 eastyou
