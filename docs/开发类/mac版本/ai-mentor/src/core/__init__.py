# Core Module — lazy imports to avoid GIMP dependency at import time

def _lazy_import(name):
    import importlib
    return importlib.import_module(f".{name}", package="core")


def get_engine(*args, **kwargs):
    from core.engine import Engine, ExecutionResult
    return Engine(*args, **kwargs)


def get_layer_funcs():
    from core.layer_manager import (
        duplicate_layer, new_layer, new_layer_group,
        add_white_mask, add_black_mask,
        merge_visible, flatten_image, get_active_drawable,
        create_preview_layer, toggle_preview_visibility,
        is_preview_visible, apply_preview_to_original,
        remove_preview_layer, get_selection_bounds, find_layer_by_name,
    )
    return {k: v for k, v in locals().items()}


# These are safe to import (no GIMP dependency)
from core.state_machine import GuideStateMachine, State
from core.logger import Logger, init as log_init, get as log_get
from core.history_stack import HistoryStack
from core.monitor import PerfMonitor, SLA, format_metrics
