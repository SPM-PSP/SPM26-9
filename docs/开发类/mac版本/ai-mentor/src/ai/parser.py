"""
AI response parser module.

Extracts structured edit actions AND diagnosis results from AI responses.
Supports both JSON and free-text formats.
"""

import json
import re
import sys

# ─── Supported Action Types ────────────────────────────────────

ACTION_REGISTRY = {
    "diagnosis": {
        "label": "Image Diagnosis",
        "params": {
            "problem_type": {"type": "string", "default": ""},
            "region": {"type": "string", "default": "全局"},
            "severity": {"type": "string", "default": "中"},
            "summary": {"type": "string", "default": ""}
        }
    },
    "brightness_contrast": {
        "label": "Brightness / Contrast",
        "params": {
            "brightness": {"type": "int", "min": -127, "max": 127, "default": 0},
            "contrast": {"type": "int", "min": -127, "max": 127, "default": 0}
        }
    },
    "levels": {
        "label": "Levels",
        "params": {
            "channel": {"type": "choice", "options": ["value", "red", "green", "blue"], "default": "value"},
            "low": {"type": "float", "min": 0, "max": 255, "default": 0},
            "high": {"type": "float", "min": 0, "max": 255, "default": 255},
            "gamma": {"type": "float", "min": 0.1, "max": 10, "default": 1.0}
        }
    },
    "hue_saturation": {
        "label": "Hue / Saturation",
        "params": {
            "hue": {"type": "int", "min": -180, "max": 180, "default": 0},
            "saturation": {"type": "int", "min": -100, "max": 100, "default": 0},
            "lightness": {"type": "int", "min": -100, "max": 100, "default": 0}
        }
    },
    "color_balance": {
        "label": "Color Balance",
        "params": {
            "shadows_cyan_red": {"type": "int", "min": -100, "max": 100, "default": 0},
            "shadows_magenta_green": {"type": "int", "min": -100, "max": 100, "default": 0},
            "shadows_yellow_blue": {"type": "int", "min": -100, "max": 100, "default": 0},
            "midtones_cyan_red": {"type": "int", "min": -100, "max": 100, "default": 0},
            "midtones_magenta_green": {"type": "int", "min": -100, "max": 100, "default": 0},
            "midtones_yellow_blue": {"type": "int", "min": -100, "max": 100, "default": 0}
        }
    },
    "curves": {
        "label": "Curves",
        "params": {
            "channel": {"type": "choice", "options": ["value", "red", "green", "blue"], "default": "value"},
            "points": {"type": "points", "default": [0, 0, 255, 255]}
        }
    },
    "desaturate": {
        "label": "Desaturate",
        "params": {}
    },
    "sharpen": {
        "label": "Sharpen",
        "params": {
            "radius": {"type": "float", "min": 0.1, "max": 50, "default": 5.0},
            "amount": {"type": "float", "min": 0, "max": 1, "default": 0.5}
        }
    },
    "unsharp_mask": {
        "label": "Unsharp Mask",
        "params": {
            "radius": {"type": "float", "min": 0.1, "max": 500, "default": 5.0},
            "amount": {"type": "float", "min": 0, "max": 10, "default": 0.5},
            "threshold": {"type": "int", "min": 0, "max": 255, "default": 0}
        }
    },
    "gaussian_blur": {
        "label": "Gaussian Blur",
        "params": {
            "radius": {"type": "float", "min": 0.1, "max": 500, "default": 5.0}
        }
    },
    "invert": {
        "label": "Invert Colors",
        "params": {}
    },
    "auto_stretch": {
        "label": "Auto Stretch Contrast",
        "params": {}
    },
    "layer_duplicate": {
        "label": "Duplicate Layer",
        "params": {
            "name": {"type": "string", "default": "Copy"}
        }
    },
    "layer_new": {
        "label": "New Layer",
        "params": {
            "name": {"type": "string", "default": "New Layer"},
            "mode": {"type": "choice", "options": ["normal", "multiply", "screen", "overlay"], "default": "normal"},
            "opacity": {"type": "int", "min": 0, "max": 100, "default": 100}
        }
    },
    "resize": {
        "label": "Resize Image",
        "params": {
            "width": {"type": "int", "min": 1, "default": None},
            "height": {"type": "int", "min": 1, "default": None}
        }
    },
    "crop": {
        "label": "Crop",
        "params": {
            "x": {"type": "int", "min": 0, "default": 0},
            "y": {"type": "int", "min": 0, "default": 0},
            "width": {"type": "int", "min": 1, "default": None},
            "height": {"type": "int", "min": 1, "default": None}
        }
    },
    "vignette": {
        "label": "Vignette",
        "params": {
            "radius": {"type": "float", "min": 0.1, "max": 2.0, "default": 1.0},
            "softness": {"type": "float", "min": 0, "max": 1, "default": 0.5},
            "darkness": {"type": "float", "min": 0, "max": 1, "default": 0.5}
        }
    },
}


def get_action_list():
    """Return list of supported action keys."""
    return list(ACTION_REGISTRY.keys())


def get_action_info(action_name):
    """Return action metadata or None."""
    return ACTION_REGISTRY.get(action_name)


# ─── Parsing ───────────────────────────────────────────────────

def parse_response(text):
    """
    Parse AI response text into (diagnosis, actions) tuple.

    diagnosis: dict or None with keys problem_type, region, severity, summary
    actions: list of action dicts (excluding 'diagnosis' entries from executable list)
    """
    actions = _parse_actions_raw(text)
    diagnosis = None
    executable = []

    for a in actions:
        if a.get("action") == "diagnosis":
            diagnosis = a.get("params", {})
        else:
            executable.append(a)

    return diagnosis, executable


def parse_actions(text):
    """Backward-compatible: parse AI response into action list (keeps diagnosis inline)."""
    return _parse_actions_raw(text)


def parse_diagnosis(text):
    """Extract only the diagnosis from an AI response."""
    diagnosis, _ = parse_response(text)
    return diagnosis


def _parse_actions_raw(text):
    """Parse AI response text into a list of action commands."""
    actions = _extract_json_block(text)
    if actions:
        return _normalize_actions(actions)
    actions = _extract_standalone_json(text)
    if actions:
        return _normalize_actions(actions)
    return _extract_text_steps(text)


def _extract_json_block(text):
    pattern = r'```(?:json)?\s*\n?(.*?)\n?```'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1).strip())
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "steps" in data:
                return data["steps"]
            if isinstance(data, dict) and "actions" in data:
                return data["actions"]
            if isinstance(data, dict) and "diagnosis" in data:
                items = [{"action": "diagnosis", "params": data["diagnosis"]}]
                items.extend(data.get("steps", []))
                return items
        except json.JSONDecodeError:
            pass
    return None


def _extract_standalone_json(text):
    match = re.search(r'\[\s*\{.*?\}\s*\]', text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass
    return None


def _normalize_actions(actions):
    result = []
    for item in actions:
        if isinstance(item, str):
            result.append({
                "action": "text_step",
                "params": {},
                "description": item
            })
        elif isinstance(item, dict):
            action = item.get("action", item.get("type", "text_step"))
            params = item.get("params", {})
            if isinstance(params, str):
                params = {"value": params}
            desc = item.get("description", item.get("desc", item.get("title", "")))
            result.append({
                "action": action,
                "params": params,
                "description": desc
            })
    return result


def _extract_text_steps(text):
    lines = text.strip().split("\n")
    actions = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if re.match(r'^(?:\d+[\.\)]|[-*\•])\s+', line):
            clean = re.sub(r'^(?:\d+[\.\)]|[-*\•])\s+', '', line)
            actions.append({
                "action": "text_step",
                "params": {},
                "description": clean
            })
    return actions


def format_action_list(actions):
    """Format action list into readable step text."""
    lines = []
    for i, a in enumerate(actions, 1):
        desc = a.get("description") or a.get("action", "")
        lines.append(f"{i}. {desc}")
    return "\n".join(lines)


def build_system_prompt_for_json():
    """Return a system prompt that asks AI to respond with structured JSON."""
    action_names = ", ".join(get_action_list())
    return (
        "\n\nYou MUST respond ONLY with a JSON array of editing steps. "
        "The FIRST step MUST be a 'diagnosis' action describing what problems you found.\n"
        "Format:\n"
        '```json\n'
        '[\n'
        '  {"action": "diagnosis", "params": {"problem_type": "...", "region": "全局/局部", "severity": "高/中/低", "summary": "..."}},\n'
        '  {"action": "layer_duplicate", "params": {"name": "AI Mentor Preview"}, "description": "创建预览层"},\n'
        '  {"action": "levels", "params": {...}, "description": "..."}\n'
        ']\n'
        '```\n\n'
        f"Supported executable actions: {action_names}\n\n"
        "RULES:\n"
        "- First step MUST be 'diagnosis'.\n"
        "- Then create a preview layer with 'layer_duplicate'.\n"
        "- Then list executable actions from the supported list.\n"
        "- Use 'resize' with width/height for resize operations.\n"
        "- Use 'crop' with x/y/width/height for crop operations.\n"
        "- If no action is needed for a step, describe it in the 'description' field.\n"
        "- Respond with the JSON block ONLY, no explanations."
    )
