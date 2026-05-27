"""
Interactive step guide panel.

Displays AI-generated editing steps with status indicators
and per-step Execute / Skip buttons.
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib


def _(message):
    return GLib.dgettext(None, message)


STATUS_ICONS = {
    "pending":   "○",
    "active":    "◉",
    "completed": "✓",
    "failed":    "✗",
    "ignored":   "⊘",
}

STATUS_COLORS = {
    "pending":   "#9aa0a6",
    "active":    "#1a73e8",
    "completed": "#188038",
    "failed":    "#d93025",
    "ignored":   "#9aa0a6",
}


class StepGuide(Gtk.Frame):
    """Interactive list of editing steps with per-step controls."""

    def __init__(self):
        super().__init__(label=_("Edit Steps"))
        self.get_label_widget().set_markup("<b>{}</b>".format(_("Edit Steps")))
        self._steps = []
        self._step_widgets = []
        self._current_index = -1
        self._on_step_execute = None
        self._on_step_skip = None
        self._on_step_select = None
        self._build_ui()

    def _build_ui(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        outer.set_margin_top(6)
        outer.set_margin_start(6)
        outer.set_margin_end(6)
        outer.set_margin_bottom(6)
        self.add(outer)

        # Step counter
        self.counter_label = Gtk.Label()
        self.counter_label.set_xalign(0)
        self.counter_label.set_margin_bottom(4)
        outer.pack_start(self.counter_label, False, False, 0)

        # Scrollable step list
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.set_min_content_height(150)

        self.step_list = Gtk.ListBox()
        self.step_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.step_list.connect("row-selected", self._on_row_selected)
        sw.add(self.step_list)
        outer.pack_start(sw, True, True, 0)

        # Batch action buttons
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        btn_box.set_margin_top(4)

        self.btn_apply_all = Gtk.Button.new_with_label(_("Apply All"))
        self.btn_apply_all.set_sensitive(False)
        self.btn_apply_all.connect("clicked", lambda w: self._emit_execute(None))
        btn_box.pack_start(self.btn_apply_all, True, True, 0)

        self.btn_reset = Gtk.Button.new_with_label(_("Reset All"))
        self.btn_reset.set_sensitive(False)
        self.btn_reset.connect("clicked", self._on_reset)
        btn_box.pack_start(self.btn_reset, False, False, 0)

        outer.pack_start(btn_box, False, False, 0)

        self.show_all()

    # ── Public API ──────────────────────────────────────────

    def set_steps(self, actions):
        """Load steps from parsed action list (excluding diagnosis)."""
        self._steps = [dict(a) for a in actions]
        self._step_widgets = []
        self._current_index = -1

        # Clear list
        for child in self.step_list.get_children():
            self.step_list.remove(child)

        for i, step in enumerate(self._steps):
            step["_status"] = "pending"
            step["_id"] = f"step_{i + 1:02d}"
            row = Gtk.ListBoxRow()
            row.step_index = i
            widget = self._make_step_row(i, step)
            row.add(widget)
            self.step_list.add(row)
            self._step_widgets.append(widget)

        self._update_counter()
        self.btn_apply_all.set_sensitive(len(self._steps) > 0)
        self.btn_reset.set_sensitive(False)
        self.show_all()

    def set_step_status(self, index, status):
        """Update the status of a specific step."""
        if 0 <= index < len(self._steps):
            self._steps[index]["_status"] = status
            self._refresh_row(index)
            self._update_counter()

    def get_current_step(self):
        """Return the active step index, or -1."""
        return self._current_index

    def connect_step_execute(self, callback):
        """callback(step_index) called when user clicks Execute on a step."""
        self._on_step_execute = callback

    def connect_step_skip(self, callback):
        """callback(step_index) called when user clicks Skip on a step."""
        self._on_step_skip = callback

    def connect_step_select(self, callback):
        """callback(step_index) called when user selects a step."""
        self._on_step_select = callback

    def set_apply_enabled(self, enabled):
        self.btn_apply_all.set_sensitive(enabled)

    # ── Internals ───────────────────────────────────────────

    def _make_step_row(self, index, step):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box.set_margin_top(4)
        box.set_margin_bottom(4)
        box.set_margin_start(4)
        box.set_margin_end(4)

        # Status icon
        icon = Gtk.Label()
        icon.set_markup(
            '<span foreground="{}" size="large">{}</span>'.format(
                STATUS_COLORS["pending"], STATUS_ICONS["pending"]
            )
        )
        icon.set_margin_end(4)
        box.pack_start(icon, False, False, 0)

        # Description
        desc = step.get("description", step.get("action", ""))
        desc_label = Gtk.Label(label=desc)
        desc_label.set_xalign(0)
        desc_label.set_line_wrap(True)
        desc_label.set_max_width_chars(40)
        box.pack_start(desc_label, True, True, 0)

        # Execute button
        btn_exec = Gtk.Button.new_with_label(_("Execute"))
        btn_exec.set_relief(Gtk.ReliefStyle.NONE)
        btn_exec.connect("clicked", lambda w, i=index: self._emit_execute(i))
        box.pack_end(btn_exec, False, False, 0)

        # Skip button
        btn_skip = Gtk.Button.new_with_label(_("Skip"))
        btn_skip.set_relief(Gtk.ReliefStyle.NONE)
        btn_skip.connect("clicked", lambda w, i=index: self._emit_skip(i))
        box.pack_end(btn_skip, False, False, 0)

        return box

    def _refresh_row(self, index):
        if index >= len(self._step_widgets):
            return
        step = self._steps[index]
        status = step.get("_status", "pending")
        widget = self._step_widgets[index]

        # Update icon
        icon_label = widget.get_children()[0]
        icon_label.set_markup(
            '<span foreground="{}" size="large">{}</span>'.format(
                STATUS_COLORS.get(status, "#9aa0a6"),
                STATUS_ICONS.get(status, "○")
            )
        )

        # Update buttons
        btn_exec = widget.get_children()[-2]
        btn_skip = widget.get_children()[-1]
        if status in ("completed", "failed"):
            btn_exec.set_sensitive(False)
            btn_skip.set_sensitive(False)
        else:
            btn_exec.set_sensitive(True)
            btn_skip.set_sensitive(True)

    def _update_counter(self):
        total = len(self._steps)
        done = sum(1 for s in self._steps if s.get("_status") in ("completed", "ignored", "failed"))
        self.counter_label.set_markup(
            '<span foreground="#5f6368">{}: {}/{}</span>'.format(_("Progress"), done, total)
        )
        has_pending = any(s.get("_status") == "pending" for s in self._steps)
        self.btn_reset.set_sensitive(done > 0)

    def _emit_execute(self, index):
        if self._on_step_execute:
            if index is not None:
                self._on_step_execute(index)
            else:
                # Apply all: trigger each pending step
                for i, s in enumerate(self._steps):
                    if s.get("_status") == "pending":
                        self._on_step_execute(i)

    def _emit_skip(self, index):
        if self._on_step_skip:
            self._on_step_skip(index)

    def _on_row_selected(self, listbox, row):
        if row and self._on_step_select:
            self._current_index = row.step_index
            self._on_step_select(row.step_index)

    def _on_reset(self, widget):
        for i in range(len(self._steps)):
            self._steps[i]["_status"] = "pending"
            self._refresh_row(i)
        self._update_counter()
