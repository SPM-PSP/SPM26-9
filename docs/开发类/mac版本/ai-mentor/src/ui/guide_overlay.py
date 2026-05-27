"""
Floating guide overlay window.

Displays a non-modal floating window near the GIMP interface showing
the current step instruction with a tool icon and text description.

Non-invasive design (per SDD 3.2.3): separate floating window rather
than GIMP UI overlay.
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib


def _(message):
    return GLib.dgettext(None, message)


TOOL_ICONS = {
    "brightness_contrast": "☀",
    "levels": "◐",
    "hue_saturation": "🎨",
    "color_balance": "⚖",
    "curves": "〰",
    "desaturate": "○",
    "sharpen": "△",
    "unsharp_mask": "▽",
    "gaussian_blur": "◌",
    "invert": "◑",
    "auto_stretch": "↕",
    "layer_duplicate": "❐",
    "layer_new": "＋",
    "resize": "⬜",
    "crop": "✂",
    "vignette": "◉",
    "noise_reduction": "◫",
    "default": "▶",
}


class GuideOverlay:
    """Floating, non-modal window showing step guidance."""

    def __init__(self, parent=None):
        self.window = Gtk.Window.new(Gtk.WindowType.POPUP)
        if parent:
            self.window.set_transient_for(parent)
        self.window.set_title(_("Step Guide"))
        self.window.set_default_size(320, 120)
        self.window.set_resizable(False)
        self.window.set_decorated(True)
        self.window.set_skip_taskbar_hint(True)
        self.window.set_keep_above(True)
        self._build_ui()
        self.hide()

    def _build_ui(self):
        frame = Gtk.Frame()
        frame.set_margin_top(8)
        frame.set_margin_bottom(8)
        frame.set_margin_start(8)
        frame.set_margin_end(8)
        self.window.add(frame)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(16)
        box.set_margin_end(16)
        frame.add(box)

        # Header row: step number + title
        self.title_label = Gtk.Label()
        self.title_label.set_markup('<b><span size="large">{}</span></b>'.format(_("Step Guide")))
        self.title_label.set_xalign(0)
        box.pack_start(self.title_label, False, False, 0)

        # Separator
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        box.pack_start(sep, False, False, 0)

        # Tool icon (large)
        self.icon_label = Gtk.Label()
        self.icon_label.set_markup('<span size="xx-large">{}</span>'.format("▶"))
        self.icon_label.set_halign(Gtk.Align.CENTER)
        box.pack_start(self.icon_label, False, False, 0)

        # Instruction text
        self.instruction_label = Gtk.Label()
        self.instruction_label.set_line_wrap(True)
        self.instruction_label.set_max_width_chars(40)
        self.instruction_label.set_xalign(0)
        box.pack_start(self.instruction_label, False, False, 0)

        # Hint row
        self.hint_label = Gtk.Label()
        self.hint_label.set_markup(
            '<span foreground="#5f6368" size="small">{}</span>'.format(
                _("Follow the instruction below to complete this editing step.")
            )
        )
        self.hint_label.set_xalign(0)
        box.pack_start(self.hint_label, False, False, 0)

    def show_for_step(self, step_index, step, total_steps):
        """Display guidance for a specific step."""
        action = step.get("action", "")
        desc = step.get("description", step.get("title", ""))

        icon = TOOL_ICONS.get(action, TOOL_ICONS["default"])
        self.icon_label.set_markup('<span size="xx-large">{}</span>'.format(icon))

        self.title_label.set_markup(
            '<b><span size="large">{} {}/{}</span></b>'.format(
                _("Step"), step_index + 1, total_steps
            )
        )
        self.instruction_label.set_text(desc)

        self.window.show_all()
        # Position near bottom-right of parent
        self.window.set_gravity(Gdk.Gravity.SOUTH_EAST)

    def hide(self):
        self.window.hide()

    def is_visible(self):
        return self.window.get_visible()

    def destroy(self):
        self.window.destroy()
