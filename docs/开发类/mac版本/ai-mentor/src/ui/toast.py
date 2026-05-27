"""
Toast notification overlay.

Displays brief messages (info/warning/error) at the bottom of the
dialog window, auto-dismissing after 3 seconds.
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib


def _(message):
    return GLib.dgettext(None, message)


LEVEL_STYLES = {
    "info":    ("#1a73e8", "#e8f0fe", "ℹ"),
    "warning": ("#e37400", "#fef7e0", "⚠"),
    "error":   ("#d93025", "#fce8e6", "✖"),
    "success": ("#188038", "#e6f4ea", "✓"),
}


class Toast(Gtk.Overlay):
    """Overlay that slides up a toast message and auto-dismisses."""

    def __init__(self, parent_widget):
        super().__init__()
        self._parent = parent_widget
        self._timeout_id = None

        self.revealer = Gtk.Revealer()
        self.revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_UP)
        self.revealer.set_transition_duration(250)
        self.revealer.set_halign(Gtk.Align.CENTER)
        self.revealer.set_valign(Gtk.Align.END)
        self.add_overlay(self.revealer)

        self.toast_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.toast_box.set_margin_bottom(8)
        self.toast_box.get_style_context().add_class("toast")

        self.icon_label = Gtk.Label()
        self.toast_box.pack_start(self.icon_label, False, False, 0)

        self.msg_label = Gtk.Label()
        self.msg_label.set_line_wrap(True)
        self.msg_label.set_max_width_chars(60)
        self.msg_label.set_xalign(0)
        self.toast_box.pack_start(self.msg_label, True, True, 0)

        self.revealer.add(self.toast_box)
        self.show_all()

    def show(self, message, level="info"):
        """Show a toast message. level: info, warning, error, success."""
        if self._timeout_id:
            GLib.source_remove(self._timeout_id)

        style = LEVEL_STYLES.get(level, LEVEL_STYLES["info"])

        # Style the toast box
        css = """
        .toast {{
            background: {};
            border: 1px solid {};
            border-radius: 6px;
            padding: 8px 16px;
        }}
        """.format(style[1], style[0])
        provider = Gtk.CssProvider()
        provider.load_from_data(css.encode())
        ctx = self.toast_box.get_style_context()
        ctx.add_provider(provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self.icon_label.set_text(style[2])
        self.msg_label.set_markup(
            '<span foreground="{}">{}</span>'.format(style[0], GLib.markup_escape_text(message))
        )
        self.revealer.set_reveal_child(True)

        self._timeout_id = GLib.timeout_add(3000, self._dismiss)

    def _dismiss(self):
        self.revealer.set_reveal_child(False)
        self._timeout_id = None
        return False
