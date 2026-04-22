from gimpfu import *
import base64
import requests
import tempfile


def image_to_base64(image, drawable):
    # 保存临时PNG
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    pdb.file_png_save(image, drawable, tmp.name, tmp.name, 0, 9, 0, 0, 0, 0, 0)

    # 读取并编码
    with open(tmp.name, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def ai_assist(image, drawable):
    pdb.gimp_message("AI分析中...")

    try:
        img_base64 = image_to_base64(image, drawable)

        # 调用本地AI服务
        res = requests.post(
            "http://127.0.0.1:8000/analyze",
            json={"image": img_base64}
        )

        data = res.json()

        # 展示结果
        msg = "分析结果:\n"
        msg += "亮度: %.2f\n" % data["analysis"]["brightness"]
        msg += "对比度: %.2f\n\n" % data["analysis"]["contrast"]

        msg += "建议步骤:\n"
        for step in data["steps"]:
            msg += "- %s\n" % step["suggestion"]

        pdb.gimp_message(msg)

    except Exception as e:
        pdb.gimp_message("出错: " + str(e))


register(
    "python_fu_ai_assist",
    "AI辅助修图",
    "分析图像并给出修图建议",
    "you",
    "you",
    "2026",
    "AI修图助手",
    "RGB*, GRAY*",
    [],
    [],
    ai_assist,
    menu="<Image>/Filters/AI Tools"
)

main()
