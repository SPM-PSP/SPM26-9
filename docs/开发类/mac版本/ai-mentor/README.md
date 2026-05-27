# GIMP AI Mentor — 智能照片编辑助手

GIMP 3.2 Python 插件。通过自然语言或内置配方，由 AI 分析图像并提供分步编辑指导，一键执行。

## 架构总览

```
ai-mentor/
├── ai-mentor.py            ← 插件入口，PDB 注册，启动主界面
├── config.json             ← 用户配置 (API key, model 等)
├── recipes/                ← 用户自定义配方存储 (.gimp-ai-recipe)
└── src/
    ├── ai/                 ← AI 客户端 & 响应解析
    │   ├── client.py       ← OpenAI 兼容 API 调用 (含 mock 模式)
    │   └── parser.py       ← AI 响应解析，17 种操作注册表
    ├── core/               ← 编辑引擎 & 基础设施
    │   ├── engine.py       ← GIMP PDB/GEGL 执行引擎
    │   ├── layer_manager.py← 非破坏性图层管理
    │   ├── state_machine.py← 工作流状态机
    │   ├── history_stack.py← 独立撤销/重做栈
    │   ├── logger.py       ← 结构化日志 (轮转)
    │   └── monitor.py      ← 性能监控 & SLA
    ├── recipes/            ← 配方系统
    │   ├── manager.py      ← 配方存取/导入导出/验证
    │   └── presets.py      ← 10 个内置预设配方
    └── ui/                 ← GTK 3 用户界面
        ├── dialog.py       ← 主对话框 (聊天 + 步骤 + 配方)
        ├── diagnosis_panel.py ← AI 诊断结果卡片
        ├── step_guide.py   ← 交互式步骤列表
        ├── recipe_browser.py  ← 配方浏览器
        ├── guide_overlay.py   ← 步骤浮动提示窗 (已废弃)
        └── toast.py        ← Toast 通知
```

---

# 目录

1. [ai-mentor.py](#ai-mentorpy)
2. [src/ai/client.py](#srcaiclientpy)
3. [src/ai/parser.py](#srcaiparserpy)
4. [src/core/engine.py](#srccoreenginepy)
5. [src/core/layer_manager.py](#srccorelayer_managerpy)
6. [src/core/state_machine.py](#srccorestate_machinepy)
7. [src/core/history_stack.py](#srccorehistory_stackpy)
8. [src/core/logger.py](#srccoreloggerpy)
9. [src/core/monitor.py](#srccoremonitorpy)
10. [src/recipes/manager.py](#srcrecipesmanagerpy)
11. [src/recipes/presets.py](#srcrecipespresetspy)
12. [src/ui/dialog.py](#srcuidialogpy)
13. [src/ui/diagnosis_panel.py](#srcuidiagnosis_panelpy)
14. [src/ui/step_guide.py](#srcuistep_guidepy)
15. [src/ui/recipe_browser.py](#srcuirecipe_browserpy)
16. [src/ui/guide_overlay.py](#srcuiguide_overlaypy)
17. [src/ui/toast.py](#srcuitoastpy)

---

## ai-mentor.py

**插件入口**。注册 GIMP PDB 过程 `python-fu-ai-mentor`，挂载到 `Filters > AI` 菜单。

### 类

| 名称 | 说明 |
|------|------|
| `AiMentorPlugin(Gimp.PlugIn)` | GIMP 3 插件注册类 |

### 方法

| 方法 | 说明 |
|------|------|
| `do_set_i18n(procname)` | 返回 `(True, 'gimp30-python', None)` |
| `do_query_procedures()` | 返回 `["python-fu-ai-mentor"]` |
| `do_create_procedure(name)` | 创建图像过程，菜单路径 `<Image>/Filters/AI`，支持 `RGB*, GRAY*` |

### 函数

| 函数 | 说明 |
|------|------|
| `run_plugin(procedure, run_mode, image, drawables, config, data)` | GIMP 回调；交互模式下启动 `AiMentorDialog` |
| `N_(message)` | 翻译标记占位 |
| `_(message)` | `GLib.dgettext` 翻译 |

### 接口

- 输入: GIMP 通过 PDB 调用，传入当前图像和绘制对象
- 输出: 启动 GTK 主循环，返回 `PDBStatusType.SUCCESS`

---

## src/ai/client.py

**AI 通信客户端**。OpenAI 兼容的聊天 API 封装，支持图片发送、重试、取消、token 统计和离线 mock 模式。

### 类: `AIClient`

| 方法 | 说明 |
|------|------|
| `__init__(settings)` | 注入 settings 对象；初始化 cancel 事件、mock 开关、token 计数器 |
| `api_url` (property) | 从 settings 读取 API 地址 |
| `api_key` (property) | 从 settings 读取 API Key |
| `model` (property) | 从 settings 读取模型名，默认 `gpt-4o` |
| `system_prompt` (property, setter) | 可覆盖系统提示 |
| `send(messages, image_b64, response_format)` | **核心方法**。发送多模态对话请求，最多重试 3 次 (0s/1s/2s/4s 退避)。返回响应文本 |
| `cancel()` | 设置取消标志，中断当前请求 |
| `reset_cancel()` | 清除取消标志 |
| `get_token_summary()` | 返回 `"Prompt: X | Completion: Y | Total: Z"` 格式的 token 摘要 |
| `_send_once(...)` | 单次 HTTP POST；30s 超时；检查取消标志 |
| `_mock_response(messages)` | 根据关键词匹配返回 6 套预置中文 mock 响应 |

### 接口

- `send()` 是唯一公开 API
- 通过 `settings` 对象获取配置 (lazy binding，动态读取)

---

## src/ai/parser.py

**AI 响应解析器**。从 AI 回复中提取诊断结果和可执行编辑步骤。支持 JSON 代码块、裸 JSON 和纯文本格式。

### 常量: `ACTION_REGISTRY`

17 种操作类型的参数 schema 注册表。每种操作定义了参数名、类型、范围、默认值：

| 操作 | 参数 |
|------|------|
| `diagnosis` | problem_type, region, severity, summary |
| `brightness_contrast` | brightness [-127,127], contrast [-127,127] |
| `levels` | channel, low [0,255], high [0,255], gamma |
| `hue_saturation` | hue [-180,180], saturation [-100,100], lightness [-100,100] |
| `color_balance` | midtones_cyan_red [-100,100], midtones_magenta_green [-100,100], midtones_yellow_blue [-100,100] |
| `curves` | channel, points |
| `desaturate` | (无参数) |
| `sharpen` | radius [0.1,50], amount [0,5] |
| `unsharp_mask` | radius [0.1,50], amount [0,5], threshold |
| `gaussian_blur` | radius [0.1,50] |
| `invert` | (无参数) |
| `auto_stretch` | (无参数) |
| `layer_duplicate` | name |
| `layer_new` | name, mode, opacity |
| `resize` | width, height |
| `crop` | x, y, width, height |
| `vignette` | radius, softness, darkness |

### 函数

| 函数 | 输入 | 输出 | 说明 |
|------|------|------|------|
| `parse_response(text)` | AI 原始回复 | `(diagnosis_dict, [action_dict, ...])` | **主解析器**。分离诊断与可执行步骤 |
| `parse_actions(text)` | AI 原始回复 | `[action_dict, ...]` | 向后兼容，诊断作为 action 返回 |
| `parse_diagnosis(text)` | AI 原始回复 | `dict` or `None` | 仅提取诊断 |
| `format_action_list(actions)` | action 列表 | `"1. desc\n2. desc\n..."` | 格式化步骤为文本 |
| `build_system_prompt_for_json()` | — | `str` | 生成 JSON 格式响应的系统提示追加文本 |
| `get_action_list()` | — | `[str, ...]` | 返回所有支持的操作名列表 |
| `get_action_info(action_name)` | 操作名 | `dict` or `None` | 返回操作的参数 schema |
| `_parse_actions_raw(text)` | 原始文本 | `[dict, ...]` | 内部：JSON → 文本 → 回退 |
| `_extract_json_block(text)` | 原始文本 | `[dict, ...]` or `None` | 提取 markdown 围栏 JSON |
| `_extract_standalone_json(text)` | 原始文本 | `[dict, ...]` or `None` | 提取裸 JSON 数组 |
| `_normalize_actions(actions)` | 原始列表 | `[{action, params, description}, ...]` | 规范化步骤格式 |
| `_extract_text_steps(text)` | 纯文本 | `[{action: "text_step", ...}]` | 纯文本回退解析 |

---

## src/core/engine.py

**GIMP 操作执行引擎**。将 AI 解析的 action 映射到 GIMP PDB/GEGL 调用。**非破坏性编辑**：在执行任何修改操作前自动创建 `[AI Mentor Preview]` 预览层。

### 类: `ExecutionResult`

| 属性 | 说明 |
|------|------|
| `success` | bool，操作是否成功 |
| `message` | str，操作描述或错误信息 |
| `action` | dict，原始 action 数据 |

### 类: `Engine`

| 方法 | 输入 | 输出 | 说明 |
|------|------|------|------|
| `__init__(image)` | GIMP Image | — | 绑定图像，初始化结果列表 |
| `execute(actions, step_callback)` | `[action, ...]`, callable | `[ExecutionResult, ...]` | **批量执行**。同一 undo group；`step_callback(i, total, status)` 报告进度 |
| `execute_single(action)` | action dict | `ExecutionResult` | **单步执行**。独立 undo group |
| `_execute_one(action)` | action dict | `ExecutionResult` | 分发到 `_do_{action}` 处理器；首次修改前创建预览层 |

### 操作处理器 (共 20 个)

每个 `_do_<action>(params)` 方法接收一个参数字典，执行对应的 GIMP 操作。

| 处理器 | GIMP API | 关键逻辑 |
|--------|----------|---------|
| `_do_brightness_contrast` | PDB `gimp-drawable-brightness-contrast` | 旧版 [-127,127] → 新版 [-1,1] 归一化 |
| `_do_levels` | GEGL `gegl:levels` | 旧版 [0,255] → [0,1] 归一化 |
| `_do_hue_saturation` | PDB `gimp-drawable-hue-saturation` | hue [-180,180]→[-1,1], sat/light [-100,100]→[-1,1] 归一化 |
| `_do_color_balance` | PDB `gimp-drawable-color-balance` → 逐通道 `gimp-drawable-levels` | **双路径回退**。[-100,100]→[-1,1] 归一化 |
| `_do_curves` | PDB `gimp-drawable-curves-spline` | 控制点数组 |
| `_do_desaturate` | PDB `gimp-drawable-desaturate` | 无参数 |
| `_do_invert` | PDB `gimp-drawable-invert` | 线性和非线性两种模式 |
| `_do_auto_stretch` | PDB `gimp-drawable-stretch` | 自动对比度拉伸 |
| `_do_sharpen` | PDB `gimp-drawable-sharpen` → GEGL `gegl:unsharp-mask` | PDB 不存在时回退到 USM |
| `_do_unsharp_mask` | GEGL `gegl:unsharp-mask` | std-dev + scale |
| `_do_gaussian_blur` | PDB `gimp-drawable-gaussian-blur` → GEGL `gegl:gaussian-blur` | 双路径回退 |
| `_do_vignette` | GEGL `gegl:vignette` | radius, softness, gamma(darkness) |
| `_do_noise_reduction` | GEGL `gegl:noise-reduction` | strength |
| `_do_layer_duplicate` | `layer_manager.duplicate_layer` | 复制当前图层 |
| `_do_layer_new` | `layer_manager.new_layer` | 创建透明图层 |
| `_do_resize` | PDB `gimp-image-resize` | 图像尺寸 |
| `_do_crop` | PDB `gimp-image-crop` | 裁剪区域 |
| `_do_diagnosis` | — | 无操作 (UI 处理) |
| `_do_text_step` | — | 无操作 (纯文字步骤) |

### 接口

- `engine.execute(actions)` → `[ExecutionResult, ...]`
- `engine.execute_single(action)` → `ExecutionResult`
- 图像通过 `image.undo_group_start()/end()` 包裹确保可撤销

---

## src/core/layer_manager.py

**非破坏性图层管理**。所有编辑操作在 `[AI Mentor Preview]` 预览层上进行，原始图层不受影响。

### 函数

| 函数 | 输入 | 输出 | 说明 |
|------|------|------|------|
| `duplicate_layer(image, name)` | GIMP Image, str | GimpLayer or None | 复制当前选中图层 |
| `create_preview_layer(image)` | GIMP Image | GimpLayer or None | 查找或创建 `[AI Mentor Preview]` 层 |
| `find_layer_by_name(image, name)` | GIMP Image, str | GimpLayer or None | 按名称搜索图层 |
| `toggle_preview_visibility(image)` | GIMP Image | bool | 切换预览层可见性 (Before/After) |
| `is_preview_visible(image)` | GIMP Image | bool | 检查预览层是否可见 |
| `apply_preview_to_original(image)` | GIMP Image | bool | 将预览层合并到原图层 |
| `remove_preview_layer(image)` | GIMP Image | bool | 删除预览层 (放弃修改) |
| `new_layer(image, name, ...)` | GIMP Image, 可选参数 | GimpLayer or None | 创建透明新图层 |
| `new_layer_group(image, name)` | GIMP Image, str | GimpGroupLayer or None | 创建图层组 |
| `add_white_mask(layer)` | GimpLayer | GimpLayerMask or None | 添加白色图层蒙版 |
| `add_black_mask(layer)` | GimpLayer | GimpLayerMask or None | 添加黑色图层蒙版 |
| `merge_visible(image)` | GIMP Image | GimpLayer or None | 合并所有可见图层 |
| `flatten_image(image)` | GIMP Image | — | 拼合图像 |
| `get_active_drawable(image)` | GIMP Image | GimpDrawable | 获取当前选中绘制对象 |
| `get_selection_bounds(image)` | GIMP Image | `(x1,y1,x2,y2)` or None | 获取选区边界 |

### 常量

`PREVIEW_LAYER_NAME = "[AI Mentor Preview]"`

---

## src/core/state_machine.py

**工作流状态机**。管理 `IDLE → ANALYZING → GUIDING → EXECUTING → IDLE` 生命周期。

### 枚举: `State`

| 值 | 说明 |
|----|------|
| `IDLE` | 空闲，等待用户输入 |
| `ANALYZING` | AI 正在分析图像 |
| `GUIDING` | 步骤已生成，等待用户操作 |
| `EXECUTING` | 正在执行编辑操作 |
| `ERROR` | 发生错误 |

### 类: `GuideStateMachine`

| 方法 | 说明 |
|------|------|
| `__init__()` | 初始化状态为 IDLE；创建 listeners 列表 |
| `state` (property) | 线程安全读取当前状态 |
| `context` (property) | 线程安全读取上下文数据 |
| `can_transition(target)` | 检查是否允许转换到目标状态 |
| `transition(target, **ctx)` | 执行状态转换；存储上下文；触发回调。返回 bool |
| `subscribe(callback)` | 注册状态变更监听器 `(old, new, context)` |
| `unsubscribe(callback)` | 移除监听器 |
| `reset()` | 强制重置到 IDLE，清空上下文 |

### 状态转换规则

```
IDLE      → ANALYZING, GUIDING
ANALYZING → GUIDING, ERROR, IDLE
GUIDING   → EXECUTING, IDLE, ERROR
EXECUTING → GUIDING, IDLE, ERROR
ERROR     → IDLE
```

---

## src/core/history_stack.py

**AI 操作撤销栈**。独立于 GIMP 原生撤销，支持撤销 AI 建议的所有操作。

### 类: `HistoryStack`

| 方法 | 说明 |
|------|------|
| `__init__(image, max_entries=50)` | 初始化双栈 (撤销/重做) |
| `record(operation_desc)` | 记录操作；清空重做栈 |
| `undo_last()` | PDB `gimp-image-undo` 撤销最近一步 |
| `redo_last()` | PDB `gimp-image-redo` 重做最近一步 |
| `undo_all()` | 撤销所有已记录操作 |
| `clear()` | 清空栈 (不影响 GIMP 状态) |
| `undo_count` (property) | 撤销栈长度 |
| `redo_count` (property) | 重做栈长度 |

---

## src/core/logger.py

**结构化日志**。线程安全的轮转文件日志，输出到 `<config_dir>/gimp-ai-mentor.log`。

### 类: `Logger`

| 方法 | 说明 |
|------|------|
| `__init__(log_dir, level="INFO")` | 初始化日志目录和级别 |
| `debug/info/warning/error(module, message)` | 按级别写入日志 |
| `set_level(level_name)` | 动态设置日志级别 |
| `get_log_path()` | 返回日志文件路径 |
| `get_recent_entries(count=50)` | 返回最近 N 行日志 |

### 模块级函数

`init(log_dir, level)`, `get()`, `debug(module, msg)`, `info(module, msg)`, `warning(module, msg)`, `error(module, msg)`

### 配置

- 最大 5 MB/文件，保留 3 个备份
- 格式: `YYYY-MM-DD HH:MM:SS LEVEL [Module] message`

---

## src/core/monitor.py

**性能监控**。追踪关键操作的执行时间，超过 SLA 80% 时告警。

### 常量: `SLA`

| 步骤 | 阈值 (秒) |
|------|----------|
| `image_encode` | 2.0 |
| `ai_request` | 30.0 |
| `json_parse` | 0.5 |
| `pdb_execute` | 0.5 |
| `preview_update` | 0.5 |

### 类: `PerfMonitor`

| 方法 | 说明 |
|------|------|
| `__init__(logger)` | 注入 logger；初始化 metrics 列表 |
| `measure(name)` | 返回上下文管理器 `_PerfTimer` |

### 类: `_PerfTimer`

上下文管理器。`__enter__` 记录开始时间，`__exit__` 计算耗时并记录。超 SLA 80% 时写 warning 日志。

### 函数

`format_metrics(metrics)` → 多行人类可读的性能摘要。

---

## src/recipes/manager.py

**配方管理器**。管理 `.gimp-ai-recipe` JSON 文件的存取、导入导出和验证。

### 类: `RecipeManager`

| 方法 | 输入 | 输出 | 说明 |
|------|------|------|------|
| `__init__(config_dir)` | 路径 | — | 创建 `recipes/` 子目录，初始化缓存 |
| `load_all()` | — | `[(id, name), ...]` | 加载所有用户配方 |
| `load_recipe(recipe_id)` | str | dict or None | 加载单个配方 (优先缓存) |
| `save_recipe(recipe)` | dict | bool | 保存配方；自动生成 UUID id 和时间戳 |
| `delete_recipe(recipe_id)` | str | bool | 删除配方文件 |
| `import_recipe(file_path)` | 路径 | `(dict or None, error or None)` | 导入外部配方文件；50KB 大小限制；验证通过后保存 |
| `export_recipe(recipe_id, output_path)` | str, 路径 | `(bool, error or None)` | 导出配方到文件 |
| `validate(recipe)` | dict | `[error, ...]` | 验证配方结构：version, metadata.id, metadata.name, steps 非空, 每个 step 有 action；嵌套深度 ≤20 |
| `_read_recipe_file(path)` | 路径 | dict or None | 读取并解析 JSON |
| `_nesting_depth(obj)` | JSON object | int | 计算 JSON 嵌套深度 (防炸弹) |

### 格式

```json
{
  "version": 1,
  "metadata": {
    "id": "...", "name": "...", "name_en": "...",
    "author": "...", "created_at": "2024-...", "tags": [...]
  },
  "diagnosis_template": { "problem_type": "...", ... },
  "steps": [
    { "step_id": 1, "action": "...", "params": {...}, "description": "..." },
    ...
  ]
}
```

---

## src/recipes/presets.py

**10 个内置预设配方**。只读参考，通过 `get_preset()` 获取副本。

### 函数

| 函数 | 输出 | 说明 |
|------|------|------|
| `list_presets()` | `[(id, name, tags), ...]` | 所有预设的摘要列表 |
| `get_preset(preset_id)` | dict or None | 返回预设配方副本 |

### 内置配方列表

| ID | 名称 | 步骤数 | 操作序列 |
|----|------|--------|---------|
| `preset_portrait_soft_skin` | 人像柔肤 | 4 | duplicate → color_balance → gaussian_blur → brightness_contrast |
| `preset_landscape_enhance` | 风景增强 | 4 | duplicate → levels → hue_saturation → sharpen |
| `preset_vintage_film` | 复古胶片 | 5 | duplicate → hue_saturation → color_balance → brightness_contrast → vignette |
| `preset_japanese_fresh` | 日系小清新 | 4 | duplicate → brightness_contrast → color_balance → hue_saturation |
| `preset_high_contrast_bw` | 黑白高对比 | 4 | duplicate → desaturate → levels → brightness_contrast |
| `preset_food_photography` | 美食摄影 | 5 | duplicate → color_balance → hue_saturation → sharpen → brightness_contrast |
| `preset_night_scene` | 夜景增强 | 5 | duplicate → levels → noise_reduction → hue_saturation → sharpen |
| `preset_golden_hour` | 暖调黄金时刻 | 4 | duplicate → color_balance → levels → vignette |
| `preset_cool_cinematic` | 冷调电影感 | 4 | duplicate → color_balance → brightness_contrast → vignette |
| `preset_hdr_effect` | HDR效果 | 5 | duplicate → levels → unsharp_mask → hue_saturation → brightness_contrast |

---

## src/ui/dialog.py

**主对话框**。GTK 3 聊天界面，集成全部子系统。左右分栏布局。

### 布局

```
┌─────────────────────────────────────────────────┐
│  Toolbar: [标题]        [Settings] [Clear] [Apply] [Cancel] │
├───────────────────┬─────────────────────────────┤
│  Left (主界面)     │  Right                       │
│  ┌─────────────┐  │  ┌─────────────────────────┐ │
│  │ Image info   │  │  │ Image Preview           │ │
│  │ Chat view    │  │  │ [Before/After toggle]   │ │
│  │ (expandable) │  │  ├─────────────────────────┤ │
│  │              │  │  │ Diagnosis Panel         │ │
│  ├─────────────┤  │  │ (collapsible card)      │ │
│  │ Step Guide   │  │  ├─────────────────────────┤ │
│  │ (interactive)│  │  │ Recipe Browser          │ │
│  ├─────────────┤  │  │ [Built-in | My Recipes] │ │
│  │ Input + Send │  │  └─────────────────────────┘ │
│  └─────────────┘  │                             │
├───────────────────┴─────────────────────────────┤
│  Status Bar: [进度]                    [选区信息] │
└─────────────────────────────────────────────────┘
```

### 类: `Settings`

| 方法 | 说明 |
|------|------|
| `__init__(config_dir)` | 加载 `config.json` |
| `load()`, `save()` | JSON 文件读写 |
| `get(key, default)`, `set(key, value)` | 键值存取 |

### 类: `SettingsDialog(Gtk.Dialog)`

| 方法 | 说明 |
|------|------|
| `__init__(parent, settings)` | Modal 设置对话框，540×480 |
| `_build_ui()` | API URL, API Key (密码框), Model, Mock Mode, Auto-apply, System Prompt 编辑器 |
| `apply()` | 回写 settings 并保存 |

### 类: `AiMentorDialog` — 核心编排器

#### UI 构建

| 方法 | 说明 |
|------|------|
| `_build_ui()` | 完整 UI 构建：工具栏 → 分栏 → 状态栏 |
| `_build_chat_area(parent)` | 左侧：图片信息 → 聊天视图 → **StepGuide** → 输入框 (500 字符限制) → Send 按钮 |
| `_build_right_panels(parent)` | 右侧：Image Preview (带 Before/After) → DiagnosisPanel → RecipeBrowser |

#### 图像处理

| 方法 | 说明 |
|------|------|
| `_update_image()` | 导出缩略图到 Preview；捕获 base64 供 AI 发送 |
| `_update_selection_status()` | 读取选区边界显示在状态栏 |

#### AI 对话

| 方法 | 说明 |
|------|------|
| `_on_send(widget)` | 验证 API key / mock；转换到 ANALYZING；启动后台线程 `_do_request` |
| `_do_request()` | 后台：合并 system prompt + JSON 指令；调用 `ai_client.send()`；回调 `_on_response` |
| `_on_response(text)` | 解析 AI 响应 → 更新 DiagnosisPanel + StepGuide；转换到 GUIDING |
| `_on_error(msg)` | 显示 error toast；转换到 ERROR |
| `_on_cancel(widget)` | 取消 AI 请求；重置到 IDLE |
| `_append(role, text)` | 格式化追加聊天气泡到 TextBuffer |

#### 步骤执行

| 方法 | 说明 |
|------|------|
| `_on_step_execute(index)` | 启动后台线程执行单步 |
| `_on_step_skip(index)` | 标记步骤为 ignored |
| `_on_step_select(index)` | 在聊天区显示步骤详情 |
| `_do_execute_single(index, action)` | 后台：`engine.execute_single()` |
| `_on_step_executed(index, result)` | 更新步骤状态；显示成功/失败 toast |
| `_on_apply(widget)` | **Apply All**：批量执行所有非诊断步骤 |
| `_on_executed(results)` | 报告批量执行结果 |

#### 其他

| 方法 | 说明 |
|------|------|
| `_on_before_after(widget)` | 切换预览层可见性 |
| `_on_settings(widget)` | 打开 SettingsDialog；保存后重建 AIClient |
| `_on_clear(widget)` | 清空全部状态：聊天、步骤、诊断 |
| `_on_recipe_apply(recipe)` | 加载配方到 UI：诊断 + 步骤 |
| `_on_state_changed(old, new, context)` | 状态变更日志 |
| `_on_key_press(widget, event)` | ESC 取消正在进行的 AI 请求 |
| `run()` | 加载 CSS → 显示窗口 → `Gtk.main()` → 返回 PDBSUCCESS |

### 辅助函数

| 函数 | 说明 |
|------|------|
| `capture_image_b64(image)` | 图像 → temp PNG → base64 |
| `load_thumbnail_pixbuf(image, max_w, max_h)` | 图像 → 缩略图 Pixbuf |
| `_export_image_to_png(image, filename)` | 底层 PNG 导出 (gimp-file-export / file-png-save) |
| `_ensure_tag(buf, name, **props)` | TextBuffer 标签创建/获取 |

---

## src/ui/diagnosis_panel.py

**AI 诊断结果面板**。可折叠卡片，显示问题类型、区域、严重程度、摘要。

### 类: `DiagnosisPanel(Gtk.Frame)`

| 方法 | 说明 |
|------|------|
| `__init__()` | 空面板；`_build_ui()` 创建 expander + summary + 卡片容器 |
| `set_diagnosis(diagnosis)` | 填入诊断数据；清空旧卡片 |
| `clear()` | 清空全部内容 |
| `_make_card(problem_type, region, severity)` | 创建严重度卡片 (彩色标签) |

### 接口

- `panel.set_diagnosis({"problem_type": "...", "region": "...", "severity": "中", "summary": "..."})`

### 严重度颜色

| 级别 | 前景色 | 背景色 |
|------|--------|--------|
| 高 | `#d93025` | `#fce8e6` |
| 中 | `#e37400` | `#fef7e0` |
| 低 | `#188038` | `#e6f4ea` |

---

## src/ui/step_guide.py

**交互式步骤指南**。在主界面聊天区下方显示，支持逐步骤执行/跳过，批量 Apply All。

### 类: `StepGuide(Gtk.Frame)`

| 方法 | 说明 |
|------|------|
| `set_steps(actions)` | 加载新步骤列表 (清除旧步骤) |
| `set_step_status(index, status)` | 更新步骤状态并刷新行 |
| `get_current_step()` | 返回当前选中步骤索引 |
| `connect_step_execute(callback)` | 绑定 Execute 按钮 → `callback(index)` |
| `connect_step_skip(callback)` | 绑定 Skip 按钮 → `callback(index)` |
| `connect_step_select(callback)` | 绑定行选中 → `callback(index)` |
| `set_apply_enabled(enabled)` | 启用/禁用 Apply All 按钮 |
| `_make_step_row(index, step)` | 创建步骤行：状态图标 + 描述 + Execute + Skip |
| `_refresh_row(index)` | 根据状态更新图标颜色和按钮状态 |
| `_update_counter()` | 更新进度计数 `"Progress: 2/5"` |
| `_on_reset(widget)` | 重置所有步骤为 pending |

### 状态系统

| 状态 | 图标 | 颜色 | 按钮行为 |
|------|------|------|---------|
| `pending` | ○ | `#9aa0a6` 灰 | 可操作 |
| `active` | ◉ | `#1a73e8` 蓝 | 当前执行中 |
| `completed` | ✓ | `#188038` 绿 | 按钮禁用 |
| `failed` | ✗ | `#d93025` 红 | 按钮禁用 |
| `ignored` | ⊘ | `#9aa0a6` 灰 | 按钮禁用 |

---

## src/ui/recipe_browser.py

**配方浏览器**。双标签面板 (Built-in / My Recipes)，支持选择加载、导入导出。

### 类: `RecipeBrowser(Gtk.Frame)`

| 方法 | 说明 |
|------|------|
| `__init__(recipe_manager, builtin_presets)` | 注入管理器；构建 UI |
| `_build_ui()` | 双标签 ListBox → Apply 按钮 (选中时启用) |
| `_refresh()` | 刷新两个标签的配方列表 |
| `_on_list_selection_changed(listbox, row)` | 控制 Apply 按钮启用状态 |
| `_on_apply(widget)` | 读取选中行 → `get_preset(id)` 或 `load_recipe(id)` → 调用 `_on_apply_recipe` |
| `_on_import(widget)` | FileChooserDialog 导入 `.gimp-ai-recipe` 文件 |
| `_on_export(widget)` | FileChooserDialog 导出选中配方 |
| `connect_apply(callback)` | 绑定配方应用回调 `callback(recipe_dict)` |
| `refresh()` | 公开刷新方法 |

### 交互方式

- **单选** → "Use This Recipe" 按钮启用
- **双击** → 直接应用配方 (row-activated 信号)
- **导入** → 文件选择器，验证后加入 My Recipes
- **导出** → 文件选择器，保存为 `.gimp-ai-recipe`

---

## src/ui/guide_overlay.py

**浮动步骤提示窗** (已废弃)。原设计为独立 POPUP 窗口显示步骤引导，现已被 StepGuide 在主界面内取代。

### 类: `GuideOverlay`

| 方法 | 说明 |
|------|------|
| `show_for_step(index, step, total)` | 显示步骤工具图标和说明 |
| `hide()`, `is_visible()`, `destroy()` | 窗口控制 |

### 常量: `TOOL_ICONS`

18 种操作到 Unicode 图标的映射 (例如 `sharpen="△"`, `crop="✂"`, `vignette="◉"`)。

---

## src/ui/toast.py

**Toast 通知**。底部滑入的非模态消息条，3 秒自动消失。

### 类: `Toast(Gtk.Overlay)`

| 方法 | 说明 |
|------|------|
| `__init__(parent_widget)` | 创建 `Gtk.Revealer` (SLIDE_UP, 250ms) |
| `show(message, level="info")` | 显示通知；3 秒后自动 `_dismiss()` |

### 通知级别

| 级别 | 颜色 | 图标 | 用途 |
|------|------|------|------|
| `info` | 蓝 `#1a73e8` | ℹ | 一般信息 |
| `warning` | 橙 `#e37400` | ⚠ | 警告 |
| `error` | 红 `#d93025` | ✖ | 错误 |
| `success` | 绿 `#188038` | ✓ | 成功 |

---

## 数据流

```
用户输入文字 → AIClient.send() ───→ AI API
                                  ↓
         解析 ← parser.parse_response()
          ↓
    Engine.execute() ← 用户点击 Execute/Apply All
          ↓
    GIMP PDB / GEGL 操作 → 图像修改

配方: RecipeBrowser._on_apply() → dialog._on_recipe_apply() → StepGuide.set_steps()
```

## 关键设计决策

1. **GIMP 3 兼容**：使用 PDB `gimp-drawable-gegl` 调用 GEGL 操作；所有旧版参数范围归一化到 GIMP 3 范围
2. **非破坏性编辑**：所有修改在预览层上进行，原始图像不受影响
3. **多线程安全**：AI 请求和 PDB 执行在后台线程，UI 更新通过 `GLib.idle_add` 回到主线程
4. **双路径回退**：优先 PDB，不存在时回退到 GEGL (如 sharpen、color_balance)
5. **离线 Demo**：Mock 模式提供 6 套中文预置响应，无需 API Key 即可体验
