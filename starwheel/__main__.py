"""允许通过 ``python -m starwheel`` 运行。"""

from __future__ import annotations

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
