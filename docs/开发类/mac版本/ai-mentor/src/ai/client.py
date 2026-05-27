"""
AI API client module.

OpenAI-compatible chat client with:
- Token tracking and error handling
- Request cancellation
- Retry with exponential backoff (1s, 2s, 4s, max 2 retries)
- 30s timeout per request
- Mock mode for offline demo
"""

import json
import urllib.request
import urllib.error
import sys
import time
import threading


class AIClient:
    """OpenAI-compatible chat API client."""

    def __init__(self, settings):
        self.settings = settings
        self.last_usage = {}
        self._system_prompt = None
        self._cancel_event = threading.Event()
        self.mock_mode = False

    @property
    def api_url(self):
        return self.settings.get("api_url", "")

    @property
    def api_key(self):
        return self.settings.get("api_key", "")

    @property
    def model(self):
        return self.settings.get("model", "gpt-4o")

    @property
    def system_prompt(self):
        return self._system_prompt if self._system_prompt is not None else self.settings.get("system_prompt", "")

    @system_prompt.setter
    def system_prompt(self, value):
        self._system_prompt = value

    def cancel(self):
        """Signal cancellation of the in-progress request."""
        self._cancel_event.set()

    def reset_cancel(self):
        self._cancel_event.clear()

    def send(self, messages, image_b64=None, response_format=None):
        """
        Send chat request with optional image.

        Returns:
            Response text string, or error string starting with '['
        """
        if self.mock_mode:
            return self._mock_response(messages)

        self._cancel_event.clear()

        last_error = None
        delays = [0, 1, 2, 4]  # first attempt immediate, then backoff

        for attempt, delay in enumerate(delays):
            if self._cancel_event.is_set():
                return "[Cancelled] Request cancelled by user."

            if delay > 0:
                time.sleep(delay)

            result = self._send_once(messages, image_b64, response_format)
            if not result.startswith("["):
                return result
            if "429" in result or "5" in result.split("Error ")[-1][:1] if "Error " in result else False:
                last_error = result
                continue
            return result

        return last_error or "[Error] All retries exhausted."

    def _send_once(self, messages, image_b64=None, response_format=None):
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        api_messages = [{"role": "system", "content": self.system_prompt}]
        for msg in messages:
            content = msg["content"]
            if isinstance(content, list):
                api_messages.append({"role": msg["role"], "content": content})
            else:
                api_messages.append({"role": msg["role"], "content": content})

        if image_b64:
            last_text = ""
            for m in reversed(messages):
                c = m.get("content", "")
                if isinstance(c, str):
                    last_text = c
                    break
            if not last_text:
                last_text = "Please analyze this image."
            api_messages[-1] = {
                "role": api_messages[-1]["role"],
                "content": [
                    {"type": "text", "text": last_text},
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/png;base64,{image_b64}",
                        "detail": "high"
                    }}
                ]
            }

        payload = {
            "model": self.model,
            "messages": api_messages,
            "max_tokens": 4096
        }
        if response_format:
            payload["response_format"] = response_format

        req = urllib.request.Request(
            self.api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                self.last_usage = result.get("usage", {})
                return result["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8")
            try:
                detail = json.loads(body)
                msg = detail.get("error", {}).get("message", body)
            except json.JSONDecodeError:
                msg = body
            return f"[API Error {e.code}] {msg}"
        except urllib.error.URLError as e:
            return f"[Connection Error] {e.reason}"
        except Exception as e:
            return f"[Error] {str(e)}"

    def _mock_response(self, messages):
        """Return a pre-canned response for offline demo mode."""
        user_text = ""
        for m in messages:
            if m.get("role") == "user":
                c = m.get("content", "")
                if isinstance(c, str):
                    user_text = c.lower()
                elif isinstance(c, list):
                    for part in c:
                        if isinstance(part, dict) and part.get("type") == "text":
                            user_text = part.get("text", "").lower()

        if any(w in user_text for w in ["bright", "亮", "曝光", "light"]):
            return MOCK_BRIGHTNESS_RESPONSE
        if any(w in user_text for w in ["color", "颜色", "色彩", "色调", "白平衡"]):
            return MOCK_COLOR_RESPONSE
        if any(w in user_text for w in ["portrait", "人像", "皮肤", "肤", "脸", "柔肤"]):
            return MOCK_PORTRAIT_RESPONSE
        if any(w in user_text for w in ["landscape", "风景", "风光", "景"]):
            return MOCK_LANDSCAPE_RESPONSE
        if any(w in user_text for w in ["sharpen", "锐化", "清晰", "模糊"]):
            return MOCK_SHARPEN_RESPONSE
        return MOCK_GENERAL_RESPONSE

    def get_token_summary(self):
        u = self.last_usage
        if not u:
            return ""
        prompt = u.get("prompt_tokens", 0)
        completion = u.get("completion_tokens", 0)
        total = u.get("total_tokens", 0)
        return f"Tokens: ↑{prompt} ↓{completion} ∑{total}"


# ── Mock Responses ──────────────────────────────────────────

MOCK_GENERAL_RESPONSE = """```json
[
  {
    "action": "diagnosis",
    "params": {
      "problem_type": "综合优化",
      "region": "全局",
      "severity": "中",
      "summary": "图像整体表现良好，建议进行基础优化：调整亮度和对比度以增强画面层次感，适当锐化提升细节表现。"
    }
  },
  {"action": "layer_duplicate", "params": {"name": "AI Mentor Preview"}, "description": "复制活动图层作为预览层"},
  {"action": "brightness_contrast", "params": {"brightness": 10, "contrast": 15}, "description": "调整亮度+10，对比度+15，增强画面层次"},
  {"action": "sharpen", "params": {"radius": 2.0, "amount": 0.3}, "description": "轻度锐化，半径2.0，强度0.3"}
]
```"""

MOCK_BRIGHTNESS_RESPONSE = """```json
[
  {
    "action": "diagnosis",
    "params": {
      "problem_type": "曝光不足与对比度偏低",
      "region": "全局",
      "severity": "高",
      "summary": "图像整体偏暗，中间调细节丢失。建议提亮中间调并增强对比度，使画面更加通透。"
    }
  },
  {"action": "layer_duplicate", "params": {"name": "AI Mentor Preview"}, "description": "创建预览层以保护原始图像"},
  {"action": "levels", "params": {"channel": "value", "low": 10, "high": 240, "gamma": 1.15}, "description": "色阶调整：提亮中间调，扩大动态范围"},
  {"action": "brightness_contrast", "params": {"brightness": 15, "contrast": 20}, "description": "亮度+15，对比度+20，画面更通透"}
]
```"""

MOCK_COLOR_RESPONSE = """```json
[
  {
    "action": "diagnosis",
    "params": {
      "problem_type": "色偏与白平衡问题",
      "region": "全局",
      "severity": "中",
      "summary": "图像存在轻微色偏，色彩偏冷。建议调整色彩平衡增加暖色调，并适度提升饱和度。"
    }
  },
  {"action": "layer_duplicate", "params": {"name": "AI Mentor Preview"}, "description": "创建预览层"},
  {"action": "color_balance", "params": {"midtones_cyan_red": 10, "midtones_magenta_green": -5, "midtones_yellow_blue": -15}, "description": "色彩平衡：中间调增加红色，减少蓝色偏色"},
  {"action": "hue_saturation", "params": {"hue": 0, "saturation": 15, "lightness": 0}, "description": "饱和度+15，色彩更鲜艳"}
]
```"""

MOCK_PORTRAIT_RESPONSE = """```json
[
  {
    "action": "diagnosis",
    "params": {
      "problem_type": "人像肤色偏黄、皮肤质感不足",
      "region": "局部（面部区域）",
      "severity": "中",
      "summary": "肤色略偏黄，建议调整色彩平衡增加红润感，并通过轻度柔化提升肤质。"
    }
  },
  {"action": "layer_duplicate", "params": {"name": "AI Mentor Preview"}, "description": "创建预览层"},
  {"action": "color_balance", "params": {"midtones_cyan_red": 12, "midtones_magenta_green": -8, "midtones_yellow_blue": -10}, "description": "色彩平衡：增加红润感，减少黄色"},
  {"action": "gaussian_blur", "params": {"radius": 1.5}, "description": "轻度高斯模糊（半径1.5），柔化皮肤质感"},
  {"action": "brightness_contrast", "params": {"brightness": 5, "contrast": 10}, "description": "微调亮度和对比度"}
]
```"""

MOCK_LANDSCAPE_RESPONSE = """```json
[
  {
    "action": "diagnosis",
    "params": {
      "problem_type": "风景层次感不足，天空细节丢失",
      "region": "全局",
      "severity": "中",
      "summary": "风景照片前景和背景层次感不足，天空区域过曝。建议增强对比度和饱和度，压暗高光区域。"
    }
  },
  {"action": "layer_duplicate", "params": {"name": "AI Mentor Preview"}, "description": "创建预览层"},
  {"action": "levels", "params": {"channel": "value", "low": 5, "high": 235, "gamma": 1.1}, "description": "色阶调整：压缩高光，提亮暗部"},
  {"action": "hue_saturation", "params": {"hue": 0, "saturation": 20, "lightness": -5}, "description": "饱和度+20，画面更生动"},
  {"action": "sharpen", "params": {"radius": 3.0, "amount": 0.4}, "description": "锐化增强细节（半径3.0）"}
]
```"""

MOCK_SHARPEN_RESPONSE = """```json
[
  {
    "action": "diagnosis",
    "params": {
      "problem_type": "图像清晰度不足",
      "region": "全局",
      "severity": "中",
      "summary": "图像整体偏软，细节不够锐利。建议使用锐化滤镜增强边缘对比度。"
    }
  },
  {"action": "layer_duplicate", "params": {"name": "AI Mentor Preview"}, "description": "创建预览层"},
  {"action": "sharpen", "params": {"radius": 5.0, "amount": 0.6}, "description": "锐化处理：半径5.0，强度0.6"},
  {"action": "brightness_contrast", "params": {"brightness": 5, "contrast": 8}, "description": "微调对比度增强清晰感"}
]
```"""
