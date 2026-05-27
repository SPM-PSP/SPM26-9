"""
PDB operation execution engine.

Maps parsed action commands to GIMP PDB calls, executes them
with undo support, and reports results.

Non-destructive by default: duplicates active layer as [AI Mentor Preview]
before applying any destructive operations.
"""

import gi
gi.require_version('Gimp', '3.0')
from gi.repository import Gimp
from gi.repository import GLib
from gi.repository import Gio
gi.require_version('Gegl', '0.4')
from gi.repository import Gegl

import sys
import traceback

from core.layer_manager import (
    duplicate_layer, new_layer, add_white_mask, get_active_drawable,
    create_preview_layer,
)


class ExecutionResult:
    """Result of executing a single action."""

    def __init__(self, success=True, message="", action=None):
        self.success = success
        self.message = message
        self.action = action or {}

    def __bool__(self):
        return self.success


class Engine:
    """
    Executes parsed AI actions on a GIMP image.

    Usage:
        engine = Engine(image)
        results = engine.execute(actions, step_callback=None)
    """

    def __init__(self, image):
        self.image = image
        self.results = []
        self._preview_layer = None
        self._preview_created = False

    def execute(self, actions, step_callback=None):
        """
        Execute a list of action commands.

        Args:
            actions: List of {"action": str, "params": dict, "description": str}
            step_callback: Optional callable(index, total, status) for progress

        Returns:
            List of ExecutionResult
        """
        self.results = []
        self._preview_created = False

        if not actions:
            return [ExecutionResult(False, "No actions to execute.")]

        Gimp.context_push()
        self.image.undo_group_start()

        try:
            for i, action in enumerate(actions):
                if step_callback:
                    step_callback(i, len(actions), "active")
                result = self._execute_one(action)
                self.results.append(result)
                if step_callback:
                    status = "completed" if result.success else "failed"
                    step_callback(i, len(actions), status)
                if not result.success:
                    break
        finally:
            self.image.undo_group_end()
            Gimp.context_pop()

        Gimp.displays_flush()
        return self.results

    def execute_single(self, action):
        """Execute a single action step (used for per-step execution)."""
        self.image.undo_group_start()
        try:
            result = self._execute_one(action)
        finally:
            self.image.undo_group_end()
        Gimp.displays_flush()
        return result

    def _execute_one(self, action):
        action_name = action.get("action", "text_step")
        params = action.get("params", {})
        desc = action.get("description", action_name)

        # Auto-create preview layer before first destructive edit
        if action_name not in ("diagnosis", "text_step", "layer_duplicate", "layer_new"):
            self._ensure_preview_layer()

        handler = getattr(self, f"_do_{action_name}", None)
        if handler is None:
            return ExecutionResult(False, f"Unknown action: {action_name}", action)

        try:
            handler(params)
            return ExecutionResult(True, desc, action)
        except Exception as e:
            msg = f"Failed: {desc} — {e}"
            print(msg, file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            return ExecutionResult(False, msg, action)

    def _ensure_preview_layer(self):
        """Create a preview layer if one doesn't already exist."""
        if self._preview_created:
            return
        layer = create_preview_layer(self.image)
        if layer:
            self._preview_layer = layer
            self._preview_created = True

    # ── Action Handlers ──────────────────────────────────────

    def _get_layer(self):
        return get_active_drawable(self.image)

    # --- Diagnosis (no-op for engine, handled by UI) ---

    def _do_diagnosis(self, params):
        pass

    # --- Adjustments ---

    def _do_brightness_contrast(self, params):
        drawable = self._get_layer()
        if not drawable:
            raise RuntimeError("No active drawable")
        brightness = float(params.get("brightness", 0))
        contrast = float(params.get("contrast", 0))
        # GIMP 3 uses range [-1.0, 1.0]; AI may return GIMP 2.x scale values [-127, 127]
        if abs(brightness) > 1.0:
            brightness = brightness / 127.0
        if abs(contrast) > 1.0:
            contrast = contrast / 127.0
        brightness = max(-1.0, min(1.0, brightness))
        contrast = max(-1.0, min(1.0, contrast))
        proc = Gimp.get_pdb().lookup_procedure("gimp-drawable-brightness-contrast")
        if not proc:
            raise RuntimeError("gimp-drawable-brightness-contrast not found")
        cfg = proc.create_config()
        cfg.set_property("drawable", drawable)
        cfg.set_property("brightness", brightness)
        cfg.set_property("contrast", contrast)
        result = proc.run(cfg)
        if result.index(0) != Gimp.PDBStatusType.SUCCESS:
            raise RuntimeError("brightness-contrast failed")

    def _do_levels(self, params):
        drawable = self._get_layer()
        if not drawable:
            raise RuntimeError("No active drawable")
        low = float(params.get("low", 0))
        high = float(params.get("high", 255))
        gamma = float(params.get("gamma", 1.0))
        # Normalize 0-255 legacy values to GEGL 0.0-1.0 range
        if low > 1.0:
            low = low / 255.0
        if high > 1.0:
            high = high / 255.0

        proc = Gimp.get_pdb().lookup_procedure("gimp-drawable-gegl")
        if not proc:
            raise RuntimeError("gegl not found")
        cfg = proc.create_config()
        cfg.set_property("drawable", drawable)
        cfg.set_property("operation", "gegl:levels")
        config = {
            "low-input": GLib.Variant("double", low),
            "high-input": GLib.Variant("double", high),
            "gamma": GLib.Variant("double", gamma),
            "low-output": GLib.Variant("double", 0.0),
            "high-output": GLib.Variant("double", 1.0),
        }
        cfg.set_property("config", GLib.Variant("a{sv}", config))
        result = proc.run(cfg)
        if result and result.index(0) != Gimp.PDBStatusType.SUCCESS:
            raise RuntimeError("levels failed")

    def _do_hue_saturation(self, params):
        drawable = self._get_layer()
        if not drawable:
            raise RuntimeError("No active drawable")
        hue = float(params.get("hue", 0))
        saturation = float(params.get("saturation", 0))
        lightness = float(params.get("lightness", 0))
        # Normalize legacy ranges to GIMP 3 [-1.0, 1.0]
        if abs(hue) > 1.0:
            hue = hue / 180.0
        if abs(saturation) > 1.0:
            saturation = saturation / 100.0
        if abs(lightness) > 1.0:
            lightness = lightness / 100.0
        hue = max(-1.0, min(1.0, hue))
        saturation = max(-1.0, min(1.0, saturation))
        lightness = max(-1.0, min(1.0, lightness))

        # GIMP 3 PDB uses normalized [-1.0, 1.0] range
        proc = Gimp.get_pdb().lookup_procedure("gimp-drawable-hue-saturation")
        if not proc:
            raise RuntimeError("gimp-drawable-hue-saturation not found")
        cfg = proc.create_config()
        cfg.set_property("drawable", drawable)
        cfg.set_property("hue-offset", hue)
        cfg.set_property("saturation", saturation)
        cfg.set_property("lightness", lightness)
        result = proc.run(cfg)
        if result.index(0) != Gimp.PDBStatusType.SUCCESS:
            raise RuntimeError("hue-saturation failed")

    def _do_color_balance(self, params):
        drawable = self._get_layer()
        if not drawable:
            raise RuntimeError("No active drawable")
        cr = float(params.get("midtones_cyan_red", 0))
        mg = float(params.get("midtones_magenta_green", 0))
        yb = float(params.get("midtones_yellow_blue", 0))
        # Normalize legacy [-100, 100] to [-1.0, 1.0]
        if abs(cr) > 1.0:
            cr = cr / 100.0
        if abs(mg) > 1.0:
            mg = mg / 100.0
        if abs(yb) > 1.0:
            yb = yb / 100.0
        cr = max(-1.0, min(1.0, cr))
        mg = max(-1.0, min(1.0, mg))
        yb = max(-1.0, min(1.0, yb))

        # Attempt 1: PDB gimp-drawable-color-balance
        proc = Gimp.get_pdb().lookup_procedure("gimp-drawable-color-balance")
        if proc:
            try:
                cfg = proc.create_config()
                cfg.set_property("drawable", drawable)
                try:
                    cfg.set_property("range", 1)
                except Exception:
                    pass
                cfg.set_property("cyan-red", cr)
                cfg.set_property("magenta-green", mg)
                cfg.set_property("yellow-blue", yb)
                result = proc.run(cfg)
                if result.index(0) == Gimp.PDBStatusType.SUCCESS:
                    return
            except Exception:
                pass

        # Attempt 2: emulate via per-channel gimp-drawable-levels on R, G, B
        # +cr → more red → brighten red midtones → lower gamma (< 1.0)
        # -cr → more cyan → darken red midtones → higher gamma (> 1.0)
        channels = [
            (Gimp.HistogramChannel.RED,   cr),
            (Gimp.HistogramChannel.GREEN, mg),
            (Gimp.HistogramChannel.BLUE,  yb),
        ]
        levels_proc = Gimp.get_pdb().lookup_procedure("gimp-drawable-levels")
        if not levels_proc:
            raise RuntimeError("gimp-drawable-levels not found")
        for channel, shift in channels:
            if abs(shift) < 0.001:
                continue
            gamma = 1.0 / (1.0 + shift)
            gamma = max(0.1, min(10.0, gamma))
            cfg = levels_proc.create_config()
            cfg.set_property("drawable", drawable)
            cfg.set_property("channel", channel)
            cfg.set_property("gamma", gamma)
            result = levels_proc.run(cfg)
            if result.index(0) != Gimp.PDBStatusType.SUCCESS:
                raise RuntimeError(f"color-balance channel {int(channel)} failed")

    def _do_curves(self, params):
        drawable = self._get_layer()
        if not drawable:
            raise RuntimeError("No active drawable")
        channel_map = {
            "value": Gimp.HistogramChannel.VALUE,
            "red": Gimp.HistogramChannel.RED,
            "green": Gimp.HistogramChannel.GREEN,
            "blue": Gimp.HistogramChannel.BLUE,
        }
        channel = channel_map.get(params.get("channel", "value"), Gimp.HistogramChannel.VALUE)
        points = params.get("points", [0, 0, 255, 255])

        proc = Gimp.get_pdb().lookup_procedure("gimp-drawable-curves-spline")
        if not proc:
            proc = Gimp.get_pdb().lookup_procedure("gimp-drawable-curves-explicit")
        if not proc:
            raise RuntimeError("curves not found")

        cfg = proc.create_config()
        cfg.set_property("drawable", drawable)
        cfg.set_property("channel", channel)
        cfg.set_property("control-pts", list(points))
        result = proc.run(cfg)
        if result.index(0) != Gimp.PDBStatusType.SUCCESS:
            raise RuntimeError("curves failed")

    def _do_desaturate(self, params):
        drawable = self._get_layer()
        if not drawable:
            raise RuntimeError("No active drawable")
        proc = Gimp.get_pdb().lookup_procedure("gimp-drawable-desaturate")
        if not proc:
            raise RuntimeError("gimp-drawable-desaturate not found")
        cfg = proc.create_config()
        cfg.set_property("drawable", drawable)
        result = proc.run(cfg)
        if result.index(0) != Gimp.PDBStatusType.SUCCESS:
            raise RuntimeError("desaturate failed")

    def _do_invert(self, params):
        drawable = self._get_layer()
        if not drawable:
            raise RuntimeError("No active drawable")
        proc = Gimp.get_pdb().lookup_procedure("gimp-drawable-invert")
        if not proc:
            raise RuntimeError("gimp-drawable-invert not found")
        cfg = proc.create_config()
        cfg.set_property("drawable", drawable)
        cfg.set_property("linear", False)
        result = proc.run(cfg)
        if result.index(0) != Gimp.PDBStatusType.SUCCESS:
            raise RuntimeError("invert failed")

    def _do_auto_stretch(self, params):
        drawable = self._get_layer()
        if not drawable:
            raise RuntimeError("No active drawable")
        proc = Gimp.get_pdb().lookup_procedure("gimp-drawable-stretch")
        if not proc:
            raise RuntimeError("gimp-drawable-stretch not found")
        cfg = proc.create_config()
        cfg.set_property("drawable", drawable)
        result = proc.run(cfg)
        if result.index(0) != Gimp.PDBStatusType.SUCCESS:
            raise RuntimeError("auto-stretch failed")

    # --- Filters ---

    def _do_sharpen(self, params):
        drawable = self._get_layer()
        if not drawable:
            raise RuntimeError("No active drawable")
        radius = float(params.get("radius", 5.0))
        amount = float(params.get("amount", 0.5))

        proc = Gimp.get_pdb().lookup_procedure("gimp-drawable-sharpen")
        if proc:
            cfg = proc.create_config()
            cfg.set_property("drawable", drawable)
            cfg.set_property("radius", radius)
            cfg.set_property("amount", amount)
        else:
            # GIMP 3 removed gimp-drawable-sharpen; fall back to gegl:unsharp-mask
            proc = Gimp.get_pdb().lookup_procedure("gimp-drawable-gegl")
            if not proc:
                raise RuntimeError("gegl not found")
            cfg = proc.create_config()
            cfg.set_property("drawable", drawable)
            cfg.set_property("operation", "gegl:unsharp-mask")
            config = {
                "std-dev": GLib.Variant("double", radius),
                "scale": GLib.Variant("double", amount),
            }
            cfg.set_property("config", GLib.Variant("a{sv}", config))

        result = proc.run(cfg)
        if result and result.index(0) != Gimp.PDBStatusType.SUCCESS:
            raise RuntimeError("sharpen failed")

    def _do_unsharp_mask(self, params):
        drawable = self._get_layer()
        if not drawable:
            raise RuntimeError("No active drawable")
        radius = params.get("radius", 5.0)
        amount = params.get("amount", 0.5)
        threshold = params.get("threshold", 0)

        proc = Gimp.get_pdb().lookup_procedure("gimp-drawable-gegl")
        if not proc:
            raise RuntimeError("gegl not found")
        cfg = proc.create_config()
        cfg.set_property("drawable", drawable)
        cfg.set_property("operation", "gegl:unsharp-mask")
        config = {
            "std-dev": GLib.Variant("double", float(radius)),
            "scale": GLib.Variant("double", float(amount)),
        }
        cfg.set_property("config", GLib.Variant("a{sv}", config))
        result = proc.run(cfg)
        if result and result.index(0) != Gimp.PDBStatusType.SUCCESS:
            raise RuntimeError("unsharp-mask failed")

    def _do_gaussian_blur(self, params):
        drawable = self._get_layer()
        if not drawable:
            raise RuntimeError("No active drawable")
        radius = params.get("radius", 5.0)

        proc = Gimp.get_pdb().lookup_procedure("gimp-drawable-gaussian-blur")
        if proc:
            cfg = proc.create_config()
            cfg.set_property("drawable", drawable)
            cfg.set_property("radius", float(radius))
        else:
            proc = Gimp.get_pdb().lookup_procedure("gimp-drawable-gegl")
            if not proc:
                raise RuntimeError("gaussian-blur not found")
            cfg = proc.create_config()
            cfg.set_property("drawable", drawable)
            cfg.set_property("operation", "gegl:gaussian-blur")
            cfg.set_property("config", GLib.Variant("a{sv}", {
                "std-dev-x": GLib.Variant("double", float(radius)),
                "std-dev-y": GLib.Variant("double", float(radius)),
            }))

        result = proc.run(cfg)
        if result and result.index(0) != Gimp.PDBStatusType.SUCCESS:
            raise RuntimeError("gaussian-blur failed")

    def _do_vignette(self, params):
        drawable = self._get_layer()
        if not drawable:
            raise RuntimeError("No active drawable")
        proc = Gimp.get_pdb().lookup_procedure("gimp-drawable-gegl")
        if not proc:
            raise RuntimeError("gegl not found")
        cfg = proc.create_config()
        cfg.set_property("drawable", drawable)
        cfg.set_property("operation", "gegl:vignette")
        config = {
            "radius": GLib.Variant("double", float(params.get("radius", 1.0))),
            "softness": GLib.Variant("double", float(params.get("softness", 0.5))),
            "gamma": GLib.Variant("double", float(params.get("darkness", 0.5))),
        }
        cfg.set_property("config", GLib.Variant("a{sv}", config))
        result = proc.run(cfg)
        if result and result.index(0) != Gimp.PDBStatusType.SUCCESS:
            raise RuntimeError("vignette failed")

    def _do_noise_reduction(self, params):
        drawable = self._get_layer()
        if not drawable:
            raise RuntimeError("No active drawable")
        proc = Gimp.get_pdb().lookup_procedure("gimp-drawable-gegl")
        if not proc:
            raise RuntimeError("gegl not found")
        cfg = proc.create_config()
        cfg.set_property("drawable", drawable)
        cfg.set_property("operation", "gegl:noise-reduction")
        config = {
            "strength": GLib.Variant("double", float(params.get("strength", 0.5))),
        }
        cfg.set_property("config", GLib.Variant("a{sv}", config))
        result = proc.run(cfg)
        if result and result.index(0) != Gimp.PDBStatusType.SUCCESS:
            raise RuntimeError("noise-reduction failed")

    # --- Layers ---

    def _do_layer_duplicate(self, params):
        name = params.get("name", "AI Copy")
        layer = duplicate_layer(self.image, name)
        if not layer:
            raise RuntimeError("Failed to duplicate layer")
        self._preview_layer = layer
        self._preview_created = True

    def _do_layer_new(self, params):
        name = params.get("name", "AI Layer")
        layer = new_layer(self.image, name)
        if not layer:
            raise RuntimeError("Failed to create layer")

    # --- Transform ---

    def _do_resize(self, params):
        width = params.get("width", self.image.get_width())
        height = params.get("height", self.image.get_height())
        proc = Gimp.get_pdb().lookup_procedure("gimp-image-resize")
        if not proc:
            raise RuntimeError("gimp-image-resize not found")
        cfg = proc.create_config()
        cfg.set_property("image", self.image)
        cfg.set_property("new-width", int(width))
        cfg.set_property("new-height", int(height))
        cfg.set_property("x", 0)
        cfg.set_property("y", 0)
        result = proc.run(cfg)
        if result.index(0) != Gimp.PDBStatusType.SUCCESS:
            raise RuntimeError("resize failed")

    def _do_crop(self, params):
        proc = Gimp.get_pdb().lookup_procedure("gimp-image-crop")
        if not proc:
            raise RuntimeError("gimp-image-crop not found")
        cfg = proc.create_config()
        cfg.set_property("image", self.image)
        cfg.set_property("new-width", int(params.get("width", self.image.get_width())))
        cfg.set_property("new-height", int(params.get("height", self.image.get_height())))
        cfg.set_property("x", int(params.get("x", 0)))
        cfg.set_property("y", int(params.get("y", 0)))
        result = proc.run(cfg)
        if result.index(0) != Gimp.PDBStatusType.SUCCESS:
            raise RuntimeError("crop failed")

    # --- Text step (no-op) ---

    def _do_text_step(self, params):
        pass
