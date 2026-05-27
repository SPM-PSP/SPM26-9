# -*- coding: utf-8 -*-
import os
import json
import base64
import re
import requests
import traceback
import sys
import urllib2
import ssl

class GimpAIClient:
    def __init__(self, api_key, model_name="qwen-vl-max-latest"):
        # Python 2.7 不支持 .strip() 直接在可能为 None 的变量上，确保 key 存在
        self.api_key = api_key.strip() if api_key else ""
        self.model_name = model_name
        self.url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"

        if not self.api_key:
            raise ValueError("API Key 不能为空")

    def get_suggestion(self, image_base64, user_demand=""):
        try:
            # Python 2.7 不支持 f-string，改为 + 号拼接或 .format()
            image_data_uri = "data:image/png;base64," + image_base64
        except Exception as e:
            print("错误: 图片数据处理失败: " + str(e))
            return None

        system_prompt = """
你是专业GIMP修图分析助手。
【强制固定六大评测与调整维度，严格遵守】
1.亮度 2.对比度 3.饱和度 4.锐度 5.色温 6.高斯模糊
永久剔除：亮暗部维度，不再使用。

规则说明：
1.先对图片完成以上6个维度逐一打分(1-10分)并撰写较为精细评价，生成完整诊断报告；
2.用户可自由输入任意修图需求，你仅在上面6个支持维度内给出对应GIMP实操调整建议；
3.超出六大维度的需求（磨皮、抠图、裁剪、调色风格、特效、修复等）全部无视，不生成对应操作步骤；
4.输出的修图操作必须为GIMP通用基础功能，适配常规调用接口，禁止冷门功能。

输出规范：
最终必须返回标准纯净JSON，禁止markdown代码块、多余解释、多余话术。
"""

        format_rule = """
诊断字段固定键名：
brightness 亮度
contrast 对比度
saturation 饱和度
sharpness 锐度
color_temp 色温
gaussian_blur 高斯模糊

每个维度结构统一：{"score":分数,"comment":简短评价}
修图动作action_plan数组内每条必须包含：
step序号、tool工具名、menu_path菜单路径、action操作动作、value调整数值/参数、reason调整原因。
建议数量控制在3-5条以内，全部限定在六大维度对应操作。
"""

        json_example = '''
{
  "diagnosis": {
    "brightness": {"score": 4, "comment": "整体画面偏暗，曝光不足"},
    "contrast": {"score": 5, "comment": "层次偏弱，画面偏灰"},
    "saturation": {"score": 6, "comment": "色彩表现力一般"},
    "sharpness": {"score": 7, "comment": "主体清晰度尚可"},
    "color_temp": {"score": 5, "comment": "色调偏中性偏冷"},
    "gaussian_blur": {"score": 3, "comment": "画面轻微杂点，可适度柔化降噪"}
  },
  "action_plan": [
    {
      "step": 1,
      "tool": "色阶",
      "menu_path": "颜色 -> 色阶",
      "action": "调整中间调亮度",
      "value": "中间调数值调至1.20",
      "reason": "提升整体画面曝光，改善偏暗问题"
    },
    {
      "step": 2,
      "tool": "高斯模糊",
      "menu_path": "滤镜 -> 模糊 -> 高斯模糊",
      "action": "设置模糊半径",
      "value": "半径0.5-1.0像素",
      "reason": "轻微柔化去除画面细碎噪点"
    }
  ]
}
'''
        # 替代 f-string
        user_prompt = "{0}\n{1}\n用户修图需求：{2}\n严格按照下方JSON格式返回结果：\n{3}".format(
            system_prompt, format_rule, user_demand, json_example
        )

        headers = {
            "Authorization": "Bearer " + self.api_key,
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model_name,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"image": image_data_uri},
                            {"text": user_prompt}
                        ]
                    }
                ]
            },
            "parameters": {
                "result_format": "message",
                "temperature": 0.1
            }
        }

        try:
            '''
            response = requests.post(self.url, headers=headers, json=payload, timeout=30)
            if response.status_code != 200:
                print("错误: API 请求失败 {0}: {1}".format(response.status_code, response.text))
                return None
            '''
            req = urllib2.Request(self.url, data=json.dumps(payload), headers=headers)
            # 忽略 SSL 证书检查
            context = ssl._create_unverified_context()
            response = urllib2.urlopen(req, context=context, timeout=30)
            res_body = response.read()
            res = json.loads(res_body)

            #res = response.json()
            choices = res.get('output', {}).get('choices', [])
            if not choices:
                print("错误: 未获取到AI返回内容")
                return None

            text = choices[0]['message']['content'][0]['text']

            # 使用正则提取 JSON 内容，替代 json_repair
            try:
                # 优先寻找 markdown 代码块
                json_match = re.search(r'```json\s*([\s\S]*?)```', text)
                if json_match:
                    clean_json_str = json_match.group(1).strip()
                else:
                    # 其次寻找第一个 { 到最后一个 } 之间的内容
                    json_match = re.search(r'\{[\s\S]*\}', text)
                    clean_json_str = json_match.group(0) if json_match else text

                data = json.loads(clean_json_str)
                return data
            except Exception as e:
                print("错误: JSON解析失败: " + str(e))
                return None

        except Exception as e:
            print("错误: 网络或调用异常: " + str(e))
            return None

    def _get_fallback_result(self):
        """服务异常兜底默认数据"""
        return {
            "error": "AI服务暂时不可用",
            "diagnosis": {
                "brightness": {"score": 5, "comment": "服务异常，默认中等水平"},
                "contrast": {"score": 5, "comment": "服务异常，默认中等水平"},
                "saturation": {"score": 5, "comment": "服务异常，默认中等水平"},
                "sharpness": {"score": 5, "comment": "服务异常，默认中等水平"},
                "color_temp": {"score": 5, "comment": "服务异常，默认中等水平"},
                "gaussian_blur": {"score": 5, "comment": "服务异常，默认中等水平"}
            },
            "action_plan": [
                {
                    "step": 1,
                    "tool": "通用调试",
                    "menu_path": "无",
                    "action": "检查网络并重试",
                    "value": "重新发起请求",
                    "reason": "AI接口暂时无法连通，请稍后尝试"
                }
            ]
        }
# --- 兼容层处理 ---
PY3 = sys.version_info[0] >= 3

if PY3:
    unicode = str
    raw_input = input
    # Python 3 默认 print 是函数，这里做个简单映射
    def safe_encode(s):
        return s # Python 3 终端通常能自动处理编码
else:
    # Python 2 处理
    def safe_encode(s):
        if isinstance(s, unicode):
            return s.encode('gbk', 'ignore')
        return s


def get_input(prompt_text):
    """
    兼容 Py2/3 的输入函数
    """
    try:
        # 打印提示语
        msg = prompt_text
        if not PY3:
            msg = safe_encode(prompt_text)

        # 获取输入
        sys.stdout.write(msg)
        sys.stdout.flush()

        # 使用 input (Py3) 或 raw_input (Py2)
        res = raw_input()

        # 返回 unicode/str 对象
        if not PY3 and res is not None:
            return res.decode('gbk', 'ignore').strip()
        return res.strip()
    except EOFError:
        return None
    except Exception as e:
        print("\n[Input Error]: " + str(e))
        return None


if __name__ == "__main__":
    # --- 环境路径设置 ---
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _root not in sys.path:
        sys.path.insert(0, _root)

    # --- 配置区 ---
    API_KEY = "sk-e97eee460b9840bd8645f84557199a1e"
    default_img = u"D:\\work\\test.jpg"

    print("========================================")
    print("      GIMP AI Mentor Terminal Test      ")
    print("      Env: Python " + sys.version.split()[0])
    print("========================================")

    while True:
        # 1. 输入图片路径
        path_prompt = u"\n[1/2] Image Path (Default: %s, 'q' to quit): " % default_img
        img_path = get_input(path_prompt)

        if img_path is None or img_path.lower() == 'q':
            break
        if not img_path:
            img_path = default_img

        if not os.path.exists(img_path):
            print(safe_encode(u"❌ File not found: " + img_path))
            continue

        # 2. 输入需求
        demand_prompt = u"[2/2] Your Demand: "
        demand = get_input(demand_prompt)

        if demand is None: break
        if not demand:
            print(safe_encode(u"⚠️ Demand cannot be empty."))
            continue

        # 3. 执行分析
        try:
            print(safe_encode(u"Reading and uploading image..."))
            with open(img_path, "rb") as f:
                img_data = f.read()
                img_b64 = base64.b64encode(img_data)
                if PY3:  # Python 3 的 b64encode 返回 bytes，需要转成 str
                    img_b64 = img_b64.decode('ascii')

            print(safe_encode(u"Calling AI service..."))
            client = GimpAIClient(api_key=API_KEY)
            result = client.get_suggestion(image_base64=img_b64, user_demand=demand)

            if result:
                print(safe_encode(u"\n✅ Analysis Successful!"))
                # 格式化输出 JSON
                res_str = json.dumps(result, indent=2, ensure_ascii=False)
                print(safe_encode(res_str))
            else:
                print(safe_encode(u"\n❌ AI returned empty result."))

        except Exception as e:
            print("\n💥 Error details:")
            traceback.print_exc()

    print(safe_encode(u"\nTest exited."))
'''
# 本地测试入口
if __name__ == "__main__":
    # 确保能加载根目录下的 requests 等库
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _root not in sys.path:
        sys.path.insert(0, _root)
        
    # 兼容性处理：定义 input 函数
    try:
        input_func = raw_input
    except NameError:
        input_func = input

    # 这里填写你的 API KEY
    API_KEY = "sk-e97eee460b9840bd8645f84557199a1e"
    # 请确保这张图片确实存在
    # 修改为纯英文路径
    test_image_path = r"D:\work\test.jpg"

    if not os.path.exists(test_image_path):
        print(u"警告: 请确认测试图片路径正确: " + test_image_path)
    else:
        try:
            with open(test_image_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode()

            print(u"===== GIMP 图像分析助手 =====")
            user_demand = input_func(u"请输入修图需求: ").strip()

            print(u"\n正在分析图片并生成诊断报告与修图方案...")
            client = GimpAIClient(api_key=API_KEY)
            result = client.get_suggestion(image_base64=img_b64, user_demand=user_demand)

            if result:
                print(u"\n✅ 分析完成，结果如下:")
                # 修改后的兼容性打印逻辑
                json_str = json.dumps(result, indent=2, ensure_ascii=False)

                # 如果是 Python 2 (str)，需要 decode 才能正确显示中文
                # 如果是 Python 3 (str)，直接 print 即可
                if isinstance(json_str, bytes):
                    print(json_str.decode('utf-8'))
                else:
                    print(json_str)
            else:
                print(u"错误: 分析失败")

        except Exception as e:
            # 打印更详细的错误堆栈，方便定位
            import traceback

            print(u"错误: 运行异常:")
            traceback.print_exc()
'''