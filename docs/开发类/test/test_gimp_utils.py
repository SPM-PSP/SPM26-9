#!/usr/bin/env python
# -*- coding: utf-8 -*-
from gimpfu import *
import sys, os

# 导入你们后端组写好的真实封装函数
# （图中路径在 plug-ins/gimp_utils.py 里）
sys.path.append(os.path.join(os.path.dirname(__file__), 'plug-ins'))
from gimp_utils import adjust_image_brightness 

#在后台执行，并把结果打印到控制台
#在非交互模式，GIMP不会太初对话框，直接大隐刀终端礼
#如果adjust内部报错，程序不会直接崩溃，跳到except块，把具体报错打印出来
def test_run(image, drawable):
    # 在后台默默执行，并把结果打印到控制台
    pdb.gimp_message(">>> 集成测试开始：正在调用后端封装函数...")
    try:
        adjust_image_brightness(image, 50) # 真的去调亮度！
        pdb.gimp_message(">>> 集成测试成功：GIMP PDB接口调用无误！")
    except Exception as e:
        pdb.gimp_message(">>> 集成测试失败：" + str(e))

# 注册成一个插件
# （注意：menu="" 表示它不会出现在菜单栏，是隐藏的）
register("test-real-backend", "", "", "", "", "2026", "", "*",
    [(PF_IMAGE, "image", "", None), (PF_DRAWABLE, "drawable", "", None)], [],
    test_run, menu="") 
main()