# -*- coding: utf-8 -*-
"""
小组「AI 层」HTTP / 网关 接入点（本文件不依赖 gimpfu，便于在 IDE 里单测）。

实现 fetch_raw_response 后，llm_stub 会尝试把返回值解析为带 ops 的 JSON 方案；
若尚未实现，将回退到 llm_stub 内的示例方案。
"""

from __future__ import unicode_literals


def fetch_raw_response(image, drawable):
    """
    调用你们后端，返回模型完整输出字符串（UTF-8 / Unicode）。

    推荐返回格式见 mentorlib.structured_plan.prompt_json_fence_instruction_zh()：
    前面中文建议 + 末尾 ```json { "summary", "steps_for_user", "ops" } ```。

    image / drawable：GIMP 对象；导出缩略图、尺寸、图层名等上下文时在此使用。

    未接好接口前保持 NotImplementedError，插件仍可用占位方案跑通预览。
    """
    raise NotImplementedError(
        "在 mentorlib/ai_client.py 中实现 fetch_raw_response："
        "请求小组 AI 接口并返回原始文本。"
    )
