# =============================
# 一、AI服务（FastAPI）
# 保存为: ai_server.py
# 运行: uvicorn ai_server:app --reload
# =============================

from fastapi import FastAPI
from pydantic import BaseModel
import base64
import numpy as np
import cv2

app = FastAPI()

class ImageRequest(BaseModel):
    image: str  # base64

@app.post("/analyze")
def analyze(req: ImageRequest):
    # 解码图像
    img_data = base64.b64decode(req.image)
    np_arr = np.frombuffer(img_data, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    # 简单分析（亮度 & 对比度）
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    brightness = float(np.mean(gray))
    contrast = float(np.std(gray))

    steps = []

    # 简单规则（白盒逻辑）
    if brightness < 100:
        steps.append({
            "tool": "levels",
            "suggestion": "提高亮度（建议调整输入黑场到20）"
        })

    if contrast < 50:
        steps.append({
            "tool": "curves",
            "suggestion": "增加对比度（建议S曲线）"
        })

    return {
        "analysis": {
            "brightness": brightness,
            "contrast": contrast
        },
        "steps": steps
    }

