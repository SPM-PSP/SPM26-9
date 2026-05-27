#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI 修图助手 — GIMP 2.10 插件入口。

安装
----
将本目录整体复制到 GIMP 插件目录（如 ~/.config/GIMP/2.10/plug-ins/ai-mentor/），
重启 GIMP，菜单路径为「滤镜 → AI修图助手」。

本文件同时支持独立调试：
    python -m gimp_ai_mentor.ai_mentor_standalone
"""

from __future__ import unicode_literals

import sys
import os

# 确保本目录在 sys.path 中，使 mentorlib 可导入
_plug_dir = os.path.dirname(os.path.abspath(__file__))
if _plug_dir not in sys.path:
    sys.path.insert(0, _plug_dir)

from gimpfu import *

try:
    import gtk
except ImportError:
    gtk = None


def ai_mentor_main(image, drawable):
    """菜单入口：创建并显示 AI 修图助手面板。"""
    if gtk is None:
        pdb.gimp_message("AI 修图助手需要 PyGTK (GTK 2) 支持，当前环境未安装。")
        return

    from mentorlib.ui.ui_manager import UIManager

    mgr = UIManager()
    mgr.set_gimp_context(image, drawable)
    window = mgr.create_panel()
    window.connect("destroy", lambda *_: gtk.main_quit())

    # 保持面板打开直到用户关闭
    gtk.main()


register(
    "python-fu-ai-mentor-open",
    "AI 修图助手",
    "AI 智能分析图像并生成修图方案预览",
    "Team Chengdu",
    "Team Chengdu",
    "2026",
    "AI修图助手...",
    "*",
    [
        (PF_IMAGE, "image", "输入图像", None),
        (PF_DRAWABLE, "drawable", "输入图层", None),
    ],
    [],
    ai_mentor_main,
    menu="<Image>/Filters",
)

main()
