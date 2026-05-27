"""
10 Built-in preset recipes for the AI Mentor plugin.

Each preset is a .gimp-ai-recipe compatible dict with metadata,
diagnosis_template, and steps.
"""

import time


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


PRESETS = [
    {
        "version": 1,
        "metadata": {
            "id": "preset_portrait_soft_skin",
            "name": "人像柔肤",
            "name_en": "Portrait Soft Skin",
            "author": "GIMP AI Mentor",
            "created_at": _now(),
            "tags": ["人像", "皮肤", "柔化"],
        },
        "diagnosis_template": {
            "problem_type": "人像肤色偏黄、皮肤质感需要柔化",
            "region": "局部（面部区域）",
            "severity": "中",
            "summary": "肤色略偏黄，建议调整色彩平衡增加红润感，并进行轻度柔肤处理。"
        },
        "steps": [
            {"step_id": 1, "action": "layer_duplicate", "params": {"name": "AI Mentor Preview"}, "description": "复制图层创建预览层"},
            {"step_id": 2, "action": "color_balance", "params": {"midtones_cyan_red": 12, "midtones_magenta_green": -6, "midtones_yellow_blue": -10}, "description": "色彩平衡：增加红色、减少黄色，让肤色更红润"},
            {"step_id": 3, "action": "gaussian_blur", "params": {"radius": 1.5}, "description": "轻度高斯模糊（半径1.5），柔化皮肤质感"},
            {"step_id": 4, "action": "brightness_contrast", "params": {"brightness": 5, "contrast": 8}, "description": "微调亮度+5，对比度+8"}
        ]
    },
    {
        "version": 1,
        "metadata": {
            "id": "preset_landscape_enhance",
            "name": "风景增强",
            "name_en": "Landscape Enhance",
            "author": "GIMP AI Mentor",
            "created_at": _now(),
            "tags": ["风景", "风光", "增强"],
        },
        "diagnosis_template": {
            "problem_type": "风景层次感不足、天空细节丢失",
            "region": "全局",
            "severity": "中",
            "summary": "风景照片前景和背景层次感不足，建议增强对比度和饱和度，强化天空细节。"
        },
        "steps": [
            {"step_id": 1, "action": "layer_duplicate", "params": {"name": "AI Mentor Preview"}, "description": "创建预览层"},
            {"step_id": 2, "action": "levels", "params": {"channel": "value", "low": 8, "high": 235, "gamma": 1.08}, "description": "色阶：压缩高光、提亮暗部"},
            {"step_id": 3, "action": "hue_saturation", "params": {"hue": 0, "saturation": 22, "lightness": -3}, "description": "饱和度+22，画面更鲜艳"},
            {"step_id": 4, "action": "sharpen", "params": {"radius": 3.0, "amount": 0.35}, "description": "锐化增强远景细节（半径3.0）"}
        ]
    },
    {
        "version": 1,
        "metadata": {
            "id": "preset_vintage_film",
            "name": "复古胶片",
            "name_en": "Vintage Film",
            "author": "GIMP AI Mentor",
            "created_at": _now(),
            "tags": ["复古", "胶片", "怀旧"],
        },
        "diagnosis_template": {
            "problem_type": "风格化需求：模拟复古胶片质感",
            "region": "全局",
            "severity": "低",
            "summary": "为图像添加复古胶片效果：降低饱和度、添加暖色调、增加颗粒感和暗角。"
        },
        "steps": [
            {"step_id": 1, "action": "layer_duplicate", "params": {"name": "AI Mentor Preview"}, "description": "创建预览层"},
            {"step_id": 2, "action": "hue_saturation", "params": {"hue": 5, "saturation": -30, "lightness": 0}, "description": "降低饱和度-30，模拟褪色胶片"},
            {"step_id": 3, "action": "color_balance", "params": {"midtones_cyan_red": 15, "midtones_magenta_green": -5, "midtones_yellow_blue": -20}, "description": "色彩平衡：增加暖黄色调"},
            {"step_id": 4, "action": "brightness_contrast", "params": {"brightness": -8, "contrast": 12}, "description": "稍降亮度、提升对比度"},
            {"step_id": 5, "action": "vignette", "params": {"radius": 1.2, "softness": 0.6, "darkness": 0.4}, "description": "添加暗角效果"}
        ]
    },
    {
        "version": 1,
        "metadata": {
            "id": "preset_japanese_fresh",
            "name": "日系小清新",
            "name_en": "Japanese Fresh",
            "author": "GIMP AI Mentor",
            "created_at": _now(),
            "tags": ["日系", "清新", "明亮"],
        },
        "diagnosis_template": {
            "problem_type": "风格化需求：日系小清新风格",
            "region": "全局",
            "severity": "低",
            "summary": "创建日系小清新风格：提亮整体画面、降低对比度、偏青蓝色调、柔和质感。"
        },
        "steps": [
            {"step_id": 1, "action": "layer_duplicate", "params": {"name": "AI Mentor Preview"}, "description": "创建预览层"},
            {"step_id": 2, "action": "brightness_contrast", "params": {"brightness": 20, "contrast": -10}, "description": "亮度+20，降低对比度获得柔和质感"},
            {"step_id": 3, "action": "color_balance", "params": {"midtones_cyan_red": -8, "midtones_magenta_green": 5, "midtones_yellow_blue": 10}, "description": "色彩平衡：偏青蓝色清新色调"},
            {"step_id": 4, "action": "hue_saturation", "params": {"hue": 0, "saturation": -10, "lightness": 5}, "description": "轻微降低饱和度，亮度+5"}
        ]
    },
    {
        "version": 1,
        "metadata": {
            "id": "preset_high_contrast_bw",
            "name": "黑白高对比",
            "name_en": "High Contrast B&W",
            "author": "GIMP AI Mentor",
            "created_at": _now(),
            "tags": ["黑白", "高对比", "纪实"],
        },
        "diagnosis_template": {
            "problem_type": "风格化需求：高对比度黑白效果",
            "region": "全局",
            "severity": "低",
            "summary": "将图像转换为高对比度黑白效果，适合纪实和街拍风格。"
        },
        "steps": [
            {"step_id": 1, "action": "layer_duplicate", "params": {"name": "AI Mentor Preview"}, "description": "创建预览层"},
            {"step_id": 2, "action": "desaturate", "params": {}, "description": "去色：转换为黑白"},
            {"step_id": 3, "action": "levels", "params": {"channel": "value", "low": 15, "high": 230, "gamma": 1.2}, "description": "色阶：压缩暗部和亮部，增加对比"},
            {"step_id": 4, "action": "brightness_contrast", "params": {"brightness": 0, "contrast": 25}, "description": "对比度+25，强化黑白层次"}
        ]
    },
    {
        "version": 1,
        "metadata": {
            "id": "preset_food_photography",
            "name": "美食摄影",
            "name_en": "Food Photography",
            "author": "GIMP AI Mentor",
            "created_at": _now(),
            "tags": ["美食", "暖调", "鲜艳"],
        },
        "diagnosis_template": {
            "problem_type": "美食照片色彩偏冷、质感不够突出",
            "region": "全局",
            "severity": "中",
            "summary": "美食照片需要温暖饱和的色调，增加食欲感。建议增强暖色调和锐化细节。"
        },
        "steps": [
            {"step_id": 1, "action": "layer_duplicate", "params": {"name": "AI Mentor Preview"}, "description": "创建预览层"},
            {"step_id": 2, "action": "color_balance", "params": {"midtones_cyan_red": 10, "midtones_magenta_green": 5, "midtones_yellow_blue": -15}, "description": "色彩平衡：增加暖色调，看起来更美味"},
            {"step_id": 3, "action": "hue_saturation", "params": {"hue": 0, "saturation": 18, "lightness": 0}, "description": "饱和度+18，食物色彩更鲜艳"},
            {"step_id": 4, "action": "sharpen", "params": {"radius": 2.5, "amount": 0.4}, "description": "锐化增强食物纹理细节"},
            {"step_id": 5, "action": "brightness_contrast", "params": {"brightness": 8, "contrast": 12}, "description": "微调亮度和对比度"}
        ]
    },
    {
        "version": 1,
        "metadata": {
            "id": "preset_night_scene",
            "name": "夜景增强",
            "name_en": "Night Scene",
            "author": "GIMP AI Mentor",
            "created_at": _now(),
            "tags": ["夜景", "暗光", "降噪"],
        },
        "diagnosis_template": {
            "problem_type": "夜景曝光不足、噪点较多",
            "region": "全局",
            "severity": "高",
            "summary": "夜景照片偏暗且存在噪点。建议提亮暗部、降噪并增强灯光色彩。"
        },
        "steps": [
            {"step_id": 1, "action": "layer_duplicate", "params": {"name": "AI Mentor Preview"}, "description": "创建预览层"},
            {"step_id": 2, "action": "levels", "params": {"channel": "value", "low": 0, "high": 200, "gamma": 1.3}, "description": "色阶：大幅提亮暗部（gamma=1.3）"},
            {"step_id": 3, "action": "noise_reduction", "params": {"strength": 0.6}, "description": "降噪处理，减少暗部噪点"},
            {"step_id": 4, "action": "hue_saturation", "params": {"hue": 0, "saturation": 15, "lightness": 0}, "description": "饱和度+15，增强灯光色彩"},
            {"step_id": 5, "action": "sharpen", "params": {"radius": 1.5, "amount": 0.25}, "description": "轻度锐化保持细节"}
        ]
    },
    {
        "version": 1,
        "metadata": {
            "id": "preset_golden_hour",
            "name": "暖调黄金时刻",
            "name_en": "Warm Golden Hour",
            "author": "GIMP AI Mentor",
            "created_at": _now(),
            "tags": ["黄金时刻", "暖调", "日落"],
        },
        "diagnosis_template": {
            "problem_type": "风格化需求：日落/黄金时刻暖调效果",
            "region": "全局",
            "severity": "低",
            "summary": "创建电影感黄金时刻暖调效果：增强暖色、柔和高光、添加轻微暗角。"
        },
        "steps": [
            {"step_id": 1, "action": "layer_duplicate", "params": {"name": "AI Mentor Preview"}, "description": "创建预览层"},
            {"step_id": 2, "action": "color_balance", "params": {"midtones_cyan_red": 18, "midtones_magenta_green": 0, "midtones_yellow_blue": -20}, "description": "色彩平衡：强烈暖色调（金橙色）"},
            {"step_id": 3, "action": "levels", "params": {"channel": "value", "low": 0, "high": 220, "gamma": 1.05}, "description": "色阶：柔和高光区域"},
            {"step_id": 4, "action": "vignette", "params": {"radius": 1.1, "softness": 0.5, "darkness": 0.35}, "description": "添加轻微暗角增强氛围"}
        ]
    },
    {
        "version": 1,
        "metadata": {
            "id": "preset_cool_cinematic",
            "name": "冷调电影感",
            "name_en": "Cool Cinematic",
            "author": "GIMP AI Mentor",
            "created_at": _now(),
            "tags": ["电影感", "冷调", "青橙"],
        },
        "diagnosis_template": {
            "problem_type": "风格化需求：好莱坞冷调青橙电影感",
            "region": "全局",
            "severity": "低",
            "summary": "创建好莱坞电影感青橙色调：阴影偏青蓝、高光偏橙、提升对比度。"
        },
        "steps": [
            {"step_id": 1, "action": "layer_duplicate", "params": {"name": "AI Mentor Preview"}, "description": "创建预览层"},
            {"step_id": 2, "action": "color_balance", "params": {"midtones_cyan_red": -5, "midtones_magenta_green": 0, "midtones_yellow_blue": 12}, "description": "色彩平衡：偏青蓝色电影色调"},
            {"step_id": 3, "action": "brightness_contrast", "params": {"brightness": -5, "contrast": 20}, "description": "提升对比度，营造电影质感"},
            {"step_id": 4, "action": "vignette", "params": {"radius": 1.3, "softness": 0.4, "darkness": 0.5}, "description": "暗角效果增强画面聚焦"}
        ]
    },
    {
        "version": 1,
        "metadata": {
            "id": "preset_hdr_effect",
            "name": "HDR效果",
            "name_en": "HDR Effect",
            "author": "GIMP AI Mentor",
            "created_at": _now(),
            "tags": ["HDR", "高动态", "细节"],
        },
        "diagnosis_template": {
            "problem_type": "图像动态范围不足，暗部和亮部细节丢失",
            "region": "全局",
            "severity": "中",
            "summary": "通过调整色阶和锐化增强整体动态范围，模拟HDR效果。"
        },
        "steps": [
            {"step_id": 1, "action": "layer_duplicate", "params": {"name": "AI Mentor Preview"}, "description": "创建预览层"},
            {"step_id": 2, "action": "levels", "params": {"channel": "value", "low": 10, "high": 240, "gamma": 1.0}, "description": "色阶：扩展动态范围"},
            {"step_id": 3, "action": "unsharp_mask", "params": {"radius": 2.0, "amount": 0.8, "threshold": 2}, "description": "USM锐化：增强局部对比度"},
            {"step_id": 4, "action": "hue_saturation", "params": {"hue": 0, "saturation": 15, "lightness": 0}, "description": "饱和度+15，色彩更饱满"},
            {"step_id": 5, "action": "brightness_contrast", "params": {"brightness": 0, "contrast": 15}, "description": "对比度+15，强化HDR质感"}
        ]
    },
]

BUILTIN_PRESETS = PRESETS


def list_presets():
    """Return list of (id, name, tags) for all built-in presets."""
    return [(p["metadata"]["id"], p["metadata"]["name"], p["metadata"].get("tags", []))
            for p in PRESETS]


def get_preset(preset_id):
    """Get a preset by ID. Returns None if not found."""
    for p in PRESETS:
        if p["metadata"]["id"] == preset_id:
            return dict(p)  # return a copy
    return None
