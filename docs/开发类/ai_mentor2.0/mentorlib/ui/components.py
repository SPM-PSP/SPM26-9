# -*- coding: utf-8 -*-
"""
可复用的 GTK 2 小组件：Toast、步骤行、雷达图。

GTK 2 (PyGTK)  版，全部使用 ``import gtk``。
"""

from __future__ import unicode_literals

import math

import gtk
import gobject
import cairo


# ============================== Toast ==============================
_TOAST_CLASS = {
    "info": "#2563eb",
    "success": "#16a34a",
    "warning": "#ca8a04",
    "error": "#dc2626",
}


class ToastManager(object):
    """简易 Toast：在传入容器顶部插入条状提示，3 秒后自动移除。"""

    def __init__(self, parent_box):
        """
        parent_box : gtk.VBox
            置于面板顶部的专用 Toast 容器。
        """
        self.parent = parent_box

    def show(self, msg, level="info"):
        gobject.idle_add(self._show_in_main, msg, level)

    def _show_in_main(self, msg, level):
        color = _TOAST_CLASS.get(level, "#2563eb")
        label = gtk.Label(msg)
        label.set_alignment(0.0, 0.5)
        label.set_line_wrap(True)
        label.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse(color))
        label.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse("#ffffff"))
        label.set_padding(8, 6)

        self.parent.pack_start(label, expand=False, fill=True, padding=2)
        label.show_all()

        def _remove():
            if label.get_parent() is not None:
                self.parent.remove(label)
            return False

        gobject.timeout_add(3000, _remove)
        return False


# ============================== 步骤行 ==============================
class StepRow(gtk.HBox):
    """单一步骤行（只读展示，无执行/忽略按钮）。"""

    def __init__(self, index, step):
        """
        Parameters
        ----------
        index : int  序号（从 0 开始）
        step  : dict 步骤数据（含 title / instruction / tool_name …）
        """
        super(StepRow, self).__init__(spacing=6)
        self.step = step
        self.set_border_width(6)
        # 深色背景、左侧橙色边框（手动修饰）
        self.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("#262626"))

        # 序号圆圈
        num_label = gtk.Label("{:02d}".format(index + 1))
        num_label.set_size_request(24, 24)
        num_label.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("#334155"))
        num_label.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse("#f97316"))
        self.pack_start(num_label, expand=False, fill=False, padding=2)

        # 文字
        text_box = gtk.VBox(spacing=1)
        title = step.get("title", "")
        title_lbl = gtk.Label()
        title_lbl.set_markup("<b>{}</b>".format(_esc(title)))
        title_lbl.set_alignment(0.0, 0.5)
        text_box.pack_start(title_lbl, expand=False, fill=True, padding=0)

        desc = step.get("instruction") or step.get("desc") or ""
        if desc:
            desc_lbl = gtk.Label(desc)
            desc_lbl.set_alignment(0.0, 0.5)
            desc_lbl.set_line_wrap(True)
            desc_lbl.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse("#737373"))
            text_box.pack_start(desc_lbl, expand=False, fill=True, padding=0)

        self.pack_start(text_box, expand=True, fill=True, padding=0)


# ============================== 雷达图 (Cairo) ==============================
class RadarChart(gtk.DrawingArea):
    """Cairo 自绘雷达图，默认 5 个维度。"""

    def __init__(self):
        super(RadarChart, self).__init__()
        self.set_size_request(-1, 160)
        self.metrics = {
            "曝光": 0,        # 曝光
            "构图": 0,        # 构图
            "动态范围": 0,  # 动态范围
            "色彩": 0,        # 色彩
            "清晰度": 0,  # 清晰度
        }
        self.connect("expose-event", self._on_expose)

    def set_metrics(self, metrics):
        """metrics: dict {name: 0..100}"""
        if metrics:
            self.metrics = metrics
        self.queue_draw()

    def _on_expose(self, widget, event):
        cr = widget.window.cairo_create()
        # 裁剪到事件区域
        cr.rectangle(event.area.x, event.area.y,
                     event.area.width, event.area.height)
        cr.clip()

        alloc = widget.get_allocation()
        w, h = alloc.width, alloc.height
        cx, cy = w / 2.0, h / 2.0
        radius = max(min(cx, cy) - 24, 20)

        names = list(self.metrics.keys())
        values = list(self.metrics.values())
        n = len(names)
        if n < 3:
            return False
        step_angle = 2 * math.pi / n

        # 背景网格（4 圈）
        cr.set_source_rgba(1, 1, 1, 0.1)
        cr.set_line_width(1)
        for level in range(1, 5):
            r = radius * level / 4.0
            cr.move_to(cx + r * math.cos(-math.pi / 2),
                       cy + r * math.sin(-math.pi / 2))
            for i in range(1, n + 1):
                a = i * step_angle - math.pi / 2
                cr.line_to(cx + r * math.cos(a), cy + r * math.sin(a))
            cr.close_path()
            cr.stroke()

        # 轴线
        for i in range(n):
            a = i * step_angle - math.pi / 2
            cr.move_to(cx, cy)
            cr.line_to(cx + radius * math.cos(a),
                       cy + radius * math.sin(a))
            cr.stroke()

        # 标签
        cr.set_source_rgb(0.6, 0.6, 0.6)
        cr.set_font_size(10)
        for i, name in enumerate(names):
            a = i * step_angle - math.pi / 2
            x = cx + (radius + 14) * math.cos(a)
            y = cy + (radius + 14) * math.sin(a)
            ext = cr.text_extents(name)
            cr.move_to(x - ext[2] / 2, y + ext[3] / 2)
            cr.show_text(name)

        # 数据多边形
        cr.set_source_rgba(1.0, 0.616, 0.0, 0.3)
        for i in range(n):
            a = i * step_angle - math.pi / 2
            r = radius * max(0, min(100, values[i])) / 100.0
            x = cx + r * math.cos(a)
            y = cy + r * math.sin(a)
            if i == 0:
                cr.move_to(x, y)
            else:
                cr.line_to(x, y)
        cr.close_path()
        cr.fill_preserve()
        cr.set_source_rgb(1.0, 0.616, 0.0)
        cr.set_line_width(2)
        cr.stroke()

        # 数据点
        cr.set_source_rgb(1.0, 0.616, 0.0)
        for i in range(n):
            a = i * step_angle - math.pi / 2
            r = radius * max(0, min(100, values[i])) / 100.0
            x = cx + r * math.cos(a)
            y = cy + r * math.sin(a)
            cr.arc(x, y, 3.5, 0, 2 * math.pi)
            cr.fill()

        return False


def _esc(text):
    """简易 XML 转义，用于 set_markup。"""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
