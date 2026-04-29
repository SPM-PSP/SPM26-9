# GIMP AI Mentor 项目开发规范 v1.0


## 1. 命名规范 (Naming Convention)

为了让大家一眼看出变量是干嘛的，请严格遵守以下命名法：

### 1.1 变量与函数 (Python标准)
- **规则**：全小写 + 下划线分隔 (snake_case)
- **示例**：
    - `user_prompt` (用户输入的提示词)
    - `get_ai_response` (获取AI回复的函数)
    - `image_width` (图片宽度)

### 1.2 类名 (Class)
- **规则**：首字母大写 (PascalCase)
- **示例**：
    - `AiClient` (AI客户端类)
    - `GimpUtils` (GIMP工具类)

### 1.3 UI 控件变量 (前端专用)
- **规则**：必须加 `ui_` 前缀，方便在回调函数中区分
- **示例**：
    - `ui_btn_submit` (提交按钮)
    - `ui_text_diagnosis` (诊断结果文本框)
    - `ui_layer_preview` (预览图层)

### 1.4 常量 (Constants)
- **规则**：全大写 + 下划线
- **示例**：
    - `API_KEY`
    - `MAX_RETRY_COUNT`

---

## 2. 代码注释规范 (Comments)

每个函数**必须**包含文档字符串 (Docstring)，说明它是干嘛的。

**标准模板：**
```python
def function_name(param1, param2):
    """
    一句话描述这个函数是干嘛的
    
    :param param1: 参数1的描述 (类型)
    :param param2: 参数2的描述 (类型)
    :return: 返回值的描述 (类型)
    """
    pass
