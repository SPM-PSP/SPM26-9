# -*- coding: utf-8 -*-
"""
大模型编排入口 — 供前/后端统一调用。
由 ai_mentor.py 的菜单入口触发，也由 UI 面板在用户点击「AI 分析」时触发。

-  真正「接 DashScope」的函数在：mentorlib/ai_client.py → fetch_raw_response
- 中文 + JSON 混排解析在：mentorlib/structured_plan.py
- 白名单与字段校验在：mentorlib/schema.py
- PDB 执行在：mentorlib/pdb_runner.py
- 未配置云端密钥时走离线演示（内置示例方案）。

⚠️ 本文件不含任何 GUI 操作（gimp_message 等），纯业务编排。
"""

from __future__ import unicode_literals
import os
import base64
from mentorlib import schema
from mentorlib import structured_plan
import tempfile
from gimpfu import pdb
from mentorlib import schema
from mentorlib import ai_client2
from mentorlib.ai_client2 import GimpAIClient

def _get_image_base64(image, drawable):
    """将 GIMP 图像转换为 Base64 字符串"""
    # 导出为临时 JPEG
    tmp_path = os.path.join(tempfile.gettempdir(), "gimp_ai_temp.jpg")

    # 复制并合并图层
    tmp_img = pdb.gimp_image_duplicate(image)
    try:
        pdb.gimp_image_merge_visible_layers(tmp_img, 1)  # CLIP_TO_IMAGE
        merged_drawable = pdb.gimp_image_get_active_drawable(tmp_img)

        # 保存 JPEG
        pdb.file_jpeg_save(1, tmp_img, merged_drawable, tmp_path, tmp_path,
                           0.9, 0, 1, 0, "", 0, 1, 0, 0)

        with open(tmp_path, "rb") as f:
            return base64.b64encode(f.read()).decode('ascii')
    finally:
        pdb.gimp_image_delete(tmp_img)
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

# ---------------------------------------------------------------------------
# Mock 占位（无 AI 密钥 / 解析失败时兜底）
# ---------------------------------------------------------------------------
def _mock_plan():
    plan = {
        "summary": (
            "【示例方案】占位数据：轻微压高光、提一点饱和度并锐化；"
            "色温项为 color_balance 近似。"
        ),
        "steps_for_user": [
            "颜色 → 色阶：将高光滑块略向左收，压一点过曝高光。",
            "颜色 → 色相-饱和度：小幅提高全图饱和度。",
            "颜色 → 色彩平衡：按需在阴影/中间调/高光加青或加红微调。",
            "滤镜 → 增强 → 钝化蒙版(USM)：小半径、适中数量。",
        ],
        "ops": [
            {"op": "levels", "args": {"channel": "value", "low_input": 5, "high_input": 245,
                                       "low_output": 0, "high_output": 255, "gamma": 1.0}},
            {"op": "hue_saturation", "args": {"hue_range": "all", "hue": 0.0,
                                               "lightness": 0.0, "saturation": 8.0}},
            {"op": "unsharp_mask", "args": {"radius": 1.2, "amount": 0.35, "threshold": 3}},
            {"op": "color_temperature", "args": {"warmth": 6.0}},
        ],
    }
    return schema.validate_plan(plan)


# ---------------------------------------------------------------------------
# 公开调用入口
# ---------------------------------------------------------------------------
def request_preview_plan(image, drawable, user_prompt=""):
    """供 UI 调用：获取 AI 方案"""
    # 优先从环境变量获取，也可以直接在下面写死 API_KEY
    #api_key = os.environ.get("DASHSCOPE_API_KEY", "你的真实KEY")
    api_key = "sk-e97eee460b9840bd8645f84557199a1e"
    try:
        # 1. 转换图像
        img_b64 = _get_image_base64(image, drawable)

        # 2. 调用 AI
        client = GimpAIClient(api_key=api_key)
        result = client.get_suggestion(img_b64, user_demand=user_prompt)

        if not result:
            raise ValueError("AI returned empty result")

        # 3. 校验并返回（schema 确保数据格式符合 pdb_runner 要求）
        return schema.validate_plan(result)
    except Exception as e:
        # 这里可以记录日志或抛出，由 UI 层捕获
        print("LLM Stub Error: " + str(e))
        raise e
'''
def request_preview_plan(image, drawable):
    """
    参数
    ----
    image, drawable : GIMP 图像 / 图层对象（由 gimpfu 传入）

    返回
    ----
    dict — 已通过 schema.validate_plan 校验，包含：
        summary        str         方案摘要
        steps_for_user list[str]   给用户看的步骤文案
        ops            list[dict]  可供 pdb_runner 执行的指令序列
    """
    try:

        raw = ai_client2.fetch_raw_response(image, drawable)
        return structured_plan.parse_and_validate_plan(raw)
    except NotImplementedError:
        # 无 API 密钥 → 离线演示，返回内置示例
        return _mock_plan()
    except (ValueError, TypeError, KeyError):
        # JSON 解析失败或 schema 校验不通过 → 同样返回占位
        return _mock_plan()
'''
'''