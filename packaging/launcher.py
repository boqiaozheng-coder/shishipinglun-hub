#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PyInstaller 打包入口：启动桌面窗口。"""

import sys

from shishipinglun.desktop import main


if __name__ == "__main__":
    sys.exit(main())
