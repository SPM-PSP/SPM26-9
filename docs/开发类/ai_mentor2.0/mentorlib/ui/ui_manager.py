# -*- coding: utf-8 -*-
"""
面板生命周期管理。

两种运行模式：
1. GIMP 插件模式 — 通过 ``create_panel(image, drawable)`` 传入 GIMP 对象
2. 独立调试模式 — ``create_panel(None, None)`` 走 Mock
"""

from __future__ import unicode_literals

import os
import sys
import traceback
import threading
import gtk
import gobject

# PyGTK 必须在线程启动前初始化，否则 idle_add 静默失效
gobject.threads_init()
fs_encoding = sys.getfilesystemencoding() or "gbk"
# 将 __file__ 显式解码为 unicode
try:
    # 取得当前文件的绝对路径并转为 unicode
    curr_file = __file__.decode(fs_encoding)
except Exception:
    curr_file = __file__
# 调试日志（写入 gimp_ai_mentor/ 根目录）
_DEBUG_LOG = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    u"debug.log")


def _debug(msg):
    try:
        with open(_DEBUG_LOG, "a") as f:
            f.write(msg + "\n")
    except Exception:
        pass

from mentorlib.ui.theme import apply_theme
from mentorlib.ui.main_panel import MainPanel


# ===== 临时方案：估算雷达图指标（后期由 AI 诊断提供） =====
def _mock_metrics():
    """返回默认雷达图指标。"""
    return {"曝光": 75, "构图": 85, "动态范围": 60, "色彩": 70, "清晰度": 80}


def _mock_diagnosis():
    return {
        "summary": "分析完成，内置示例方案已就绪。配置 DASHSCOPE_API_KEY 后可调用通义千问。",
        "health_score": 74,
        "metrics": _mock_metrics(),
    }


def _mock_steps():
    return [
        {"title": "色阶调整", "instruction": "调整输入色阶，压高光、提阴影"},
        {"title": "色相饱和度", "instruction": "小幅提高全图饱和度"},
        {"title": "USM 锐化", "instruction": "小半径锐化增强细节"},
        {"title": "色温校正", "instruction": "色彩平衡模拟色温调整"},
    ]


def _plan_to_diagnosis(plan):
    """从后端 plan dict 中提取诊断展示数据。"""
    summary = plan.get("summary", "")
    metrics = _mock_metrics()
    health = None

    # 若 plan 中附带了 structured_plan 的诊断评分（action_plan_adapter 的 diagnosis）
    raw_diag = plan.get("_raw_diagnosis")
    if isinstance(raw_diag, dict):
        mapped = _map_diagnosis_to_metrics(raw_diag)
        if mapped:
            metrics = mapped
            scores = [v for v in mapped.values() if isinstance(v, (int, float))]
            if scores:
                health = int(sum(scores) / len(scores))
    if health is None:
        health = 74

    return {"summary": summary, "health_score": health, "metrics": metrics}


def _map_diagnosis_to_metrics(raw):
    """将 AI 6 维评分映射到前端 5 维雷达图（raw 键为英文，值含 score 1-10）。"""
    mapping = {
        "brightness": "曝光",
        "contrast": "对比度",
        "saturation": "色彩",
        "sharpness": "清晰度",
    }
    out = {}
    for eng, cn in mapping.items():
        block = raw.get(eng)
        if isinstance(block, dict):
            s = block.get("score")
            if s is not None:
                out[cn] = max(0, min(100, int(s) * 10))
    return out if len(out) >= 3 else None


def _plan_to_steps(plan):
    """将 plan 的 steps_for_user 转为 UI 步骤列表。"""
    steps_for_user = plan.get("steps_for_user", [])
    if not steps_for_user:
        return _mock_steps()

    result = []
    for text in steps_for_user:
        # 按第一个冒号或全角冒号分割=> title / instruction
        title = text
        instruction = ""
        for sep in ("：", ":"):
            if sep in text:
                parts = text.split(sep, 1)
                title = parts[0].strip()
                instruction = parts[1].strip()
                break
        result.append({"title": title, "instruction": instruction})
    return result


# =====================================================================


class UIManager(object):
    """管理 AI 修图助手面板的生命周期。"""

    def __init__(self):
        self._window = None
        self._panel = None
        # 由 set_gimp_context 设置
        self._image = None
        self._drawable = None
        self._gimp_available = False

    def set_gimp_context(self, image, drawable):
        """GIMP 插件入口调用，传入当前图像/图层。"""
        self._image = image
        self._drawable = drawable
        self._gimp_available = True

    def create_panel(self):
        """创建并返回 GTK 主窗口。

        独立模式下也可调用（image/drawable = None 则走 Mock）。
        """
        _debug("create_panel: entering")
        if self._window is not None:
            self._window.present()
            return self._window

        _debug("create_panel: applying theme")
        apply_theme()

        self._panel = MainPanel()
        self._panel.set_analysis_callback(self._on_analysis)

        window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        window.set_title("GIMP AI Mentor")
        window.set_default_size(380, 700)
        window.set_keep_above(True)
        window.add(self._panel)
        window.connect("destroy", self._on_destroy)
        window.show_all()

        self._window = window
        return window

    def destroy_panel(self):
        if self._window is None:
            return True
        self._window.destroy()
        self._window = None
        self._panel = None
        return True

    def _on_destroy(self, widget):
        self._window = None
        self._panel = None

    # ===== 分析回调（GIMP 嵌入式 Python 不支持 threading，直接运行） =====
    '''
    def _on_analysis(self, prompt):
        """用户点击「AI 智能修图」时触发。"""
        _debug("_on_analysis called, prompt=%r" % prompt)
        self._run_analysis_async(prompt)
    '''

    def _on_analysis(self, prompt):
        """按钮点击事件"""
        if not self._gimp_available:
            self._run_analysis_async(prompt)  # Standalone 模式走原来的 Mock
            return

        self._panel.run_btn.set_sensitive(False)
        self._panel.show_toast(u"AI 正在分析图片，请稍候...", "info")

        # 启动后台线程请求 AI
        t = threading.Thread(target=self._gimp_analysis_worker, args=(prompt,))
        t.daemon = True
        t.start()

    def _run_analysis_async(self, prompt):
        """执行分析 → 创建预览 → 更新 UI（在主线程运行，GIMP Python-Fu 不支持 threading）。"""
        _debug("_run_analysis_async started, gimp=%s" % self._gimp_available)
        try:
            if self._gimp_available and self._image is not None:
                _debug("  -> running GIMP analysis")
                plan = self._run_gimp_analysis()
            else:
                _debug("  -> running Mock analysis")
                plan = self._run_mock_analysis()

            _debug("  -> plan received, summary=%r" % plan.get("summary", "")[:60])
            diag = _plan_to_diagnosis(plan)
            steps = _plan_to_steps(plan)
            _debug("  -> updating UI, steps=%d" % len(steps))

            # 更新 UI（idle_add 会在当前事件处理完成后执行）
            if self._panel:
                self._panel.display_diagnosis(diag)
                self._panel.display_steps(steps)
                _debug("  -> display methods called OK")
        except Exception as e:
            err_msg = "AI 分析异常: %s" % e
            _debug("  -> EXCEPTION: %s" % traceback.format_exc())
            if self._panel:
                self._panel.show_toast(err_msg, "error")

    def _run_gimp_analysis(self):
        """真实 GIMP 环境：调用后端核心逻辑。"""
        #_debug("  _run_gimp_analysis: importing preview...")
        from mentorlib import preview as prv

        #_debug("  _run_gimp_analysis: calling run_preview...")
        _, _, plan = prv.run_preview(self._image, self._drawable)
        #_debug("  _run_gimp_analysis: done")
        return plan

    def _run_mock_analysis(self):
        """独立模式：直接返回 Mock 方案。"""
        import time
        time.sleep(0.5)
        diag = _mock_diagnosis()
        steps = _mock_steps()

        plan = {
            "summary": diag["summary"],
            "steps_for_user": [s["title"] + "：" + s["instruction"] for s in steps],
            "ops": [],
            "health_score": diag["health_score"],
            "metrics": diag["metrics"],
        }
        return plan

    def _gimp_analysis_worker(self, prompt):
        """后台线程"""
        try:
            from mentorlib import preview as prv
            # 真正调用后端
            # 注意：需要给 run_preview 增加 prompt 参数支持
            _, _, plan = prv.run_preview(self._image, self._drawable, prompt)

            # 通过 idle_add 回到 UI 线程更新界面
            gobject.idle_add(self._update_ui_finished, plan)
        except Exception as e:
            import traceback
            traceback.print_exc()
            gobject.idle_add(self._panel.show_toast, u"AI 分析失败: " + str(e), "error")
            gobject.idle_add(self._panel.run_btn.set_sensitive, True)

    def _update_ui_finished(self, plan):
        """主线程：更新面板"""
        diag = _plan_to_diagnosis(plan)
        steps = _plan_to_steps(plan)
        self._panel.display_diagnosis(diag)
        self._panel.display_steps(steps)
        self._panel.run_btn.set_sensitive(True)
        self._panel.show_toast(u"分析完成，预览已生成", "success")
        return False