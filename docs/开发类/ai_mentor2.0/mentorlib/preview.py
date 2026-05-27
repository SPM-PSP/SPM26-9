# -*- coding: utf-8 -*-
"""
核心流程：获取方案 → 复制整幅图像 → 在副本上应用白名单 PDB → 新建独立预览窗口。

不修改用户当前图像；方案文本由调用方（UI 面板）展示。
"""

from __future__ import unicode_literals

from gimpfu import *

from mentorlib import llm_stub as llm
from mentorlib import pdb_runner as runner
from mentorlib import schema


def run_preview(image, drawable, user_prompt=""):
    """
    完整预览流程

    返回
    ----
    (preview_image, display_id, plan_dict)
        或 (None, None, plan_dict) 当副本创建失败时仅返回方案文本。
    """
    plan = llm.request_preview_plan(image, drawable, user_prompt)
    schema.validate_plan(plan)

    preview_image = pdb.gimp_image_duplicate(image)
    if preview_image is None:
        # 副本失败 → 仅返回方案文本，由调用方展示
        return None, None, plan

    preview_drawable = pdb.gimp_image_get_active_drawable(preview_image)
    if preview_drawable is None:
        pdb.gimp_image_delete(preview_image)
        return None, None, plan

    pdb.gimp_image_undo_group_start(preview_image)
    try:
        runner.apply_ops_sequence(
            preview_image, preview_drawable, plan.get("ops", [])
        )
    finally:
        pdb.gimp_image_undo_group_end(preview_image)

    display_id = pdb.gimp_display_new(preview_image)
    return preview_image, display_id, plan
