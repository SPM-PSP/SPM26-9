#!/usr/bin/env python
# -*- coding: utf-8 -*-
from gimpfu import *

def hello_ai_plugin(image, drawable):
    """主函数：插件被点击时执行"""
    # 1. 告诉GIMP开始一个操作组（方便撤销）
    pdb.gimp_image_undo_group_start(image)
    
    try:
        # 2. 弹出一个对话框，假装是AI在说话
        pdb.gimp_message("你好！我是AI修图助手，环境已打通！")
        
        # 3. 尝试创建一个新图层（测试后端PDB接口是否通畅）
        # 宽度高度取当前图片的尺寸
        width = image.width
        height = image.height
        new_layer = gimp.Layer(image, "AI诊断图层", width, height, RGBA_IMAGE, 100, NORMAL_MODE)
        image.add_layer(new_layer, 0)
        pdb.gimp_drawable_fill(new_layer, TRANSPARENT_FILL)
        
    except Exception as e:
        pdb.gimp_message("出错了: " + str(e))
    finally:
        # 4. 结束操作组
        pdb.gimp_image_undo_group_end(image)

# 注册插件（告诉GIMP你是谁，菜单在哪里）
register(
    "python-fu-hello-ai",      # 插件唯一标识名
    "AI Mentor",               # 描述
    "AI修图助手测试版",         # 帮助信息
    "Team成都",                # 作者
    "Team成都",                # 版权
    "2026",                    # 年份
    "AI修图助手...",            # 菜单上显示的名字（前面加下划线是快捷键）
    "*",                       # 支持的图像类型（*代表所有）
    [
        (PF_IMAGE, "image", "输入图像", None),
        (PF_DRAWABLE, "drawable", "输入图层", None),
    ],
    [],
    hello_ai_plugin,
    menu="<Image>/Filters",    # 菜单路径：放在“滤镜”菜单下
)

main()