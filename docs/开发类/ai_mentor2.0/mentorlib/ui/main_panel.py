# -*- coding: utf-8 -*-
"""
主控制面板（GTK 2 / PyGTK）。

布局（自上而下）：
  Header | Toast 容器 | AI 智能修图按钮 | 诊断卡片 | 输入框 | 步骤列表 | 状态栏

外部通过 ``set_analysis_callback(fn)`` 注册分析触发函数。
"""

from __future__ import unicode_literals
import os
import sys
import gtk
import gobject

from mentorlib.ui.components import RadarChart, StepRow, ToastManager, _esc

# 调试日志（与 ui_manager 写到同一文件）
_DEBUG_LOG = None

# PyGTK 必须在线程启动前初始化，否则 idle_add 静默失效
gobject.threads_init()
fs_encoding = sys.getfilesystemencoding() or "gbk"
# 将 __file__ 显式解码为 unicode
try:
    # 取得当前文件的绝对路径并转为 unicode
    curr_file = __file__.decode(fs_encoding)
except Exception:
    curr_file = __file__
def _debug(msg):
    global _DEBUG_LOG
    if _DEBUG_LOG is None:
        import os
        _DEBUG_LOG = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            u"debug.log")
    try:
        with open(_DEBUG_LOG, "a") as f:
            f.write("[main_panel] " + msg + "\n")
    except Exception:
        pass


class MainPanel(gtk.VBox):
    """AI 修图助手主面板。"""

    def __init__(self):
        _debug("MainPanel.__init__ entering")
        super(MainPanel, self).__init__(spacing=0)
        self.set_size_request(360, 600)
        self._analysis_callback = None  # fn(prompt_text) -> dict
        self._step_rows = []
        self._diagnosis_data = None

        # ---- Header ----
        header = gtk.HBox(spacing=8)
        header.set_border_width(8)
        header.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("#262626"))
        title = gtk.Label()
        title.set_markup("<b><span foreground='#fb923c'>✦  AI 智能修图助手</span></b>")
        title.set_alignment(0.0, 0.5)
        header.pack_start(title, expand=True, fill=True, padding=0)
        self.pack_start(header, expand=False, fill=True, padding=0)

        # ---- Toast 容器 ----
        self.toast_box = gtk.VBox(spacing=2)
        self.toast_box.set_border_width(6)
        self.pack_start(self.toast_box, expand=False, fill=True, padding=0)
        self.toast = ToastManager(self.toast_box)

        # ---- 滚动内容 ----
        scroller = gtk.ScrolledWindow()
        scroller.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        scroller.set_shadow_type(gtk.SHADOW_NONE)

        content = gtk.VBox(spacing=10)
        content.set_border_width(10)

        # --- AI 智能修图按钮 ---
        self.run_btn = gtk.Button("\U0001f50d  AI 智能修图")
        self.run_btn.set_name("btn-primary")
        self.run_btn.connect("clicked", self._on_run_clicked)
        content.pack_start(self.run_btn, expand=False, fill=True, padding=0)

        # --- 诊断卡片 ---
        self.diag_card = self._build_diagnosis_card()
        self.diag_card.hide()
        content.pack_start(self.diag_card, expand=False, fill=True, padding=0)

        # --- 输入框 ---
        prompt_label = gtk.Label()
        prompt_label.set_markup("<b>AI 指令中心</b>")
        prompt_label.set_alignment(0.0, 0.5)
        content.pack_start(prompt_label, expand=False, fill=True, padding=0)

        self.prompt_buffer = gtk.TextBuffer()
        self.prompt_view = gtk.TextView(self.prompt_buffer)
        self.prompt_view.set_wrap_mode(gtk.WRAP_WORD_CHAR)
        self.prompt_view.set_size_request(-1, 70)
        self.prompt_view.modify_base(gtk.STATE_NORMAL, gtk.gdk.color_parse("#171717"))
        self.prompt_view.modify_text(gtk.STATE_NORMAL, gtk.gdk.color_parse("#d1d1d1"))
        prompt_frame = gtk.Frame()
        prompt_frame.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        prompt_frame.add(self.prompt_view)
        content.pack_start(prompt_frame, expand=False, fill=True, padding=0)

        # 占位提示
        self._placeholder = "例如：把天空变成黄昏，增强肤色质感..."
        self.prompt_buffer.set_text(self._placeholder)
        self._has_placeholder = True

        def on_focus_in(widget, event):
            if self._has_placeholder:
                self.prompt_buffer.set_text("")
                self._has_placeholder = False
            return False

        def on_focus_out(widget, event):
            text = self._get_raw_text()
            if not text.strip():
                self.prompt_buffer.set_text(self._placeholder)
                self._has_placeholder = True
            return False

        self.prompt_view.connect("focus-in-event", on_focus_in)
        self.prompt_view.connect("focus-out-event", on_focus_out)

        # 发送按钮
        send_btn = gtk.Button("生成修图步骤  ➞")
        send_btn.set_name("btn-primary")
        send_btn.connect("clicked", self._on_send_clicked)
        content.pack_start(send_btn, expand=False, fill=True, padding=0)

        # --- 步骤列表 ---
        steps_header = gtk.HBox(spacing=6)
        steps_label = gtk.Label()
        steps_label.set_markup("<b>智能建议步骤</b>")
        steps_label.set_alignment(0.0, 0.5)
        steps_header.pack_start(steps_label, expand=True, fill=True, padding=0)

        self.step_count_label = gtk.Label("0 步可用")
        self.step_count_label.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse("#a3a3a3"))
        steps_header.pack_start(self.step_count_label, expand=False, fill=False, padding=0)
        content.pack_start(steps_header, expand=False, fill=True, padding=0)

        self.steps_box = gtk.VBox(spacing=4)
        content.pack_start(self.steps_box, expand=False, fill=True, padding=0)

        # 空状态
        self.empty_hint = gtk.Label("输入修图需求，AI 将生成具体步骤")
        self.empty_hint.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse("#737373"))
        self.empty_hint.set_padding(0, 20)
        content.pack_start(self.empty_hint, expand=False, fill=True, padding=0)

        scroller.add(content)
        self.pack_start(scroller, expand=True, fill=True, padding=0)

        # ---- 底部状态栏 ----
        footer = gtk.HBox(spacing=4)
        footer.set_border_width(4)
        footer.set_name("footer-bar")
        footer.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("#262626"))
        self.status_label = gtk.Label()
        self.status_label.set_markup("<span foreground='#22c55e'>●</span> AI 服务在线")
        footer.pack_start(self.status_label, expand=True, fill=True, padding=0)
        self.pack_start(footer, expand=False, fill=True, padding=0)

    # =========== 诊断卡片 ===========
    def _build_diagnosis_card(self):
        card = gtk.VBox(spacing=6)
        card.set_border_width(8)
        card.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("#1a1a1a"))

        title = gtk.Label()
        title.set_markup("<b>诊断报告</b>")
        title.set_alignment(0.0, 0.5)
        card.pack_start(title, expand=False, fill=True, padding=0)

        self.radar = RadarChart()
        card.pack_start(self.radar, expand=False, fill=True, padding=0)

        score_row = gtk.HBox(spacing=6)
        score_row.pack_start(gtk.Label("整体健康度:"), expand=True, fill=True, padding=0)
        self.score_label = gtk.Label("--")
        self.score_label.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse("#4ade80"))
        score_row.pack_start(self.score_label, expand=False, fill=False, padding=0)
        card.pack_start(score_row, expand=False, fill=True, padding=0)

        self.summary_label = gtk.Label("")
        self.summary_label.set_alignment(0.0, 0.0)
        self.summary_label.set_line_wrap(True)
        self.summary_label.set_size_request(280, -1)
        self.summary_label.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse("#d1d1d1"))
        card.pack_start(self.summary_label, expand=False, fill=True, padding=0)

        return card

    # =========== 外部接口 ===========
    def set_analysis_callback(self, fn):
        """fn(prompt_text) 将在后台线程执行，应通过 idle_add 更新 UI。"""
        self._analysis_callback = fn

    def show_toast(self, msg, level="info"):
        self.toast.show(msg, level)

    def display_diagnosis(self, diagnosis):
        """从后端 plan dict 中提取诊断信息并展示。"""
        gobject.idle_add(self._display_diagnosis_in_main, diagnosis)

    def display_steps(self, steps):
        """展示步骤列表。"""
        gobject.idle_add(self._display_steps_in_main, steps)

    # =========== UI 内部 ===========
    def _get_raw_text(self):
        start = self.prompt_buffer.get_start_iter()
        end = self.prompt_buffer.get_end_iter()
        return self.prompt_buffer.get_text(start, end, False)

    def get_prompt_text(self):
        if self._has_placeholder:
            return ""
        return self._get_raw_text().strip()

    def _on_run_clicked(self, btn):
        self._trigger_analysis()

    def _on_send_clicked(self, btn):
        prompt = self.get_prompt_text()
        if not prompt:
            self.show_toast("请先输入修图需求", "warning")
            return
        self._trigger_analysis(prompt)

    def _trigger_analysis(self, prompt=""):
        self.run_btn.set_sensitive(False)
        self.show_toast("AI 分析中...", "info")

        if self._analysis_callback:
            self._analysis_callback(prompt)

        def _restore():
            self.run_btn.set_sensitive(True)
            return False

        gobject.timeout_add(1500, _restore)

    # =========== UI 更新（主线程） ===========
    def _display_diagnosis_in_main(self, diag):
        summary = diag.get("summary") or ""
        self.summary_label.set_text(summary)

        # 健康度
        score = diag.get("health_score")
        if score is not None:
            self.score_label.set_text("{}%".format(int(score)))

        # 雷达图指标
        metrics = diag.get("metrics") or _infer_metrics(diag)
        if metrics:
            self.radar.set_metrics(metrics)

        self.diag_card.show_all()
        return False

    def _display_steps_in_main(self, steps):
        for child in self.steps_box.get_children():
            self.steps_box.remove(child)
        self._step_rows = []

        if not steps:
            self.empty_hint.show()
            self.step_count_label.set_text("0 步可用")
            return False

        self.empty_hint.hide()
        for idx, step in enumerate(steps):
            row = StepRow(idx, step)
            self.steps_box.pack_start(row, expand=False, fill=True, padding=0)
            self._step_rows.append(row)
        self.steps_box.show_all()
        self.step_count_label.set_text("{} 步可用".format(len(steps)))
        return False


# =========== 工具函数 ===========
def _infer_metrics(plan):
    """从 AI 返回的 plan 中尝试提取雷达图指标。
    若有 diagnosis 评分（1-10），映射为 0-100 并转中文。
    """
    # 从 summary 或 diagnosis 中提取
    # 后端 AI 返回的 diagnosis 6 维：brightness/contrast/saturation/sharpness/gaussian_blur/color_temp
    diag = plan.get("diagnosis") if isinstance(plan, dict) else None
    if not isinstance(diag, dict):
        return None

    key_map = {
        "brightness": "曝光",
        "contrast": "对比度",
        "saturation": "色彩",
        "sharpness": "清晰度",
        "gaussian_blur": "柔和度",
        "color_temp": "色温",
    }
    out = {}
    for eng, cn in key_map.items():
        block = diag.get(eng)
        if isinstance(block, dict):
            score = block.get("score")
            if score is not None:
                out[cn] = max(0, min(100, int(score) * 10))
        elif isinstance(block, (int, float)):
            out[cn] = max(0, min(100, int(block) * 10))
    return out if out else None
