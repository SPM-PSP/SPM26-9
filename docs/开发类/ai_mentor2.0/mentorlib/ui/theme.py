# -*- coding: utf-8 -*-
"""
GTK 2 (PyGTK)  深色主题。
使用 gtk.rc 近似原型 HTML 的配色。
"""

from __future__ import unicode_literals

import gtk

RC_STYLE = """
# 全局默认
style "gimp-ai-default" {
    bg[NORMAL]   = { 0.17, 0.17, 0.17 }  /* #2c2c2c */
    bg[PRELIGHT] = { 0.25, 0.25, 0.25 }  /* #404040 */
    bg[SELECTED] = { 0.27, 0.27, 0.27 }  /* #444444 */
    fg[NORMAL]   = { 0.82, 0.82, 0.82 }  /* #d1d1d1 */
    fg[PRELIGHT] = { 1.00, 1.00, 1.00 }
    fg[SELECTED] = { 1.00, 0.62, 0.24 }  /* #ff9d00 */
    base[NORMAL] = { 0.09, 0.09, 0.09 }  /* #171717 */
    base[ACTIVE] = { 0.15, 0.15, 0.15 }  /* #262626 */
    text[NORMAL] = { 0.82, 0.82, 0.82 }
    text[SELECTED] = { 1.00, 0.62, 0.24 }
    font_name = "Sans 10"
}
class "GtkWindow"   style "gimp-ai-default"
class "GtkDialog"   style "gimp-ai-default"
class "GtkVBox"     style "gimp-ai-default"
class "GtkHBox"     style "gimp-ai-default"
class "GtkLabel"    style "gimp-ai-default"
class "GtkFrame"    style "gimp-ai-default"
class "GtkEventBox" style "gimp-ai-default"

# 按钮
style "gimp-ai-button" {
    bg[NORMAL]   = { 0.92, 0.35, 0.05 }  /* #ea580c */
    bg[PRELIGHT] = { 0.76, 0.25, 0.05 }  /* #c2410c */
    bg[ACTIVE]   = { 0.66, 0.20, 0.00 }
    fg[NORMAL]   = { 1.00, 1.00, 1.00 }
    font_name = "Sans 10"
}
widget_class "*.btn-primary" style "gimp-ai-button"

# 幽灵按钮
style "gimp-ai-ghost" {
    bg[NORMAL]   = { 0.00, 0.00, 0.00, 0.00 }  /* 透明 */
    bg[PRELIGHT] = { 0.25, 0.25, 0.25 }
    fg[NORMAL]   = { 0.82, 0.82, 0.82 }
}
widget_class "*.btn-ghost" style "gimp-ai-ghost"

# Footer / 状态栏
style "gimp-ai-footer" {
    bg[NORMAL] = { 0.15, 0.15, 0.15 }
    fg[NORMAL] = { 0.64, 0.64, 0.64 }
    font_name = "Sans 8"
}
widget_class "*.footer-bar" style "gimp-ai-footer"
"""


def apply_theme():
    """安装全局 GTK rc 主题。多次调用幂等。"""
    gtk.rc_parse_string(RC_STYLE)
