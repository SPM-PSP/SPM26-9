#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
独立运行入口（无 GIMP 环境时调试 UI）。

用法::

    cd gimp_ai_mentor/
    python standalone.py

所有 GIMP 依赖走 Mock，UI 面板独立弹出。
"""

from __future__ import unicode_literals

import sys
import os

# 确保本目录在 sys.path 中
_plug_dir = os.path.dirname(os.path.abspath(__file__))
if _plug_dir not in sys.path:
    sys.path.insert(0, _plug_dir)

try:
    import gtk
except ImportError:
    print("错误：需要 PyGTK (GTK 2)，请安装 python-gtk2 / pygtk 后重试。")
    sys.exit(1)

from mentorlib.ui.ui_manager import UIManager


def main():
    mgr = UIManager()  # 不调用 set_gimp_context → 自动走 Mock
    window = mgr.create_panel()
    window.connect("destroy", lambda *_: gtk.main_quit())
    mgr._panel.show_toast("独立模式 · AI 接口走 Mock", "info")
    gtk.main()
    return 0


if __name__ == "__main__":
    sys.exit(main())
