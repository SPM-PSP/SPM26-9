"""
Diagnosis panel — structured display of AI image diagnosis.

Shows collapsible cards with: problem_type, region, severity, summary.
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib


def _(message):
    return GLib.dgettext(None, message)


SEVERITY_COLORS = {
    "高": ("#d93025", "#fce8e6"),
    "中": ("#e37400", "#fef7e0"),
    "低": ("#188038", "#e6f4ea"),
}


class DiagnosisPanel(Gtk.Frame):
    """Collapsible panel showing structured AI diagnosis results."""

    def __init__(self):
        super().__init__(label=_("Image Diagnosis"))
        self.get_label_widget().set_markup("<b>{}</b>".format(_("Image Diagnosis")))
        self._build_ui()
        self.clear()

    def _build_ui(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        outer.set_margin_top(8)
        outer.set_margin_bottom(8)
        outer.set_margin_start(8)
        outer.set_margin_end(8)
        self.add(outer)

        # Expander for collapsible behavior
        self.expander = Gtk.Expander.new(_("Show Details"))
        self.expander.set_expanded(True)
        outer.pack_start(self.expander, False, False, 0)

        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.expander.add(self.content_box)

        # Summary label
        self.summary_label = Gtk.Label()
        self.summary_label.set_line_wrap(True)
        self.summary_label.set_xalign(0)
        self.summary_label.set_margin_bottom(4)
        self.content_box.pack_start(self.summary_label, False, False, 0)

        # Problem cards container
        self.cards_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.content_box.pack_start(self.cards_box, False, False, 0)

        self.show_all()

    def set_diagnosis(self, diagnosis):
        """Populate with a diagnosis dict."""
        if not diagnosis:
            self.clear()
            return

        # Clear old cards
        for child in self.cards_box.get_children():
            self.cards_box.remove(child)

        problem_type = diagnosis.get("problem_type", "")
        region = diagnosis.get("region", _("Global"))
        severity = diagnosis.get("severity", "中")
        summary = diagnosis.get("summary", "")

        # Summary
        self.summary_label.set_markup(
            '<span size="large">{}</span>'.format(GLib.markup_escape_text(summary))
        )

        # Build severity card
        card = self._make_card(problem_type, region, severity)
        self.cards_box.pack_start(card, False, False, 0)

        self.show_all()

    def clear(self):
        for child in self.cards_box.get_children():
            self.cards_box.remove(child)
        self.summary_label.set_text("")
        self.show_all()

    def _make_card(self, problem_type, region, severity):
        card = Gtk.Frame()
        card.set_shadow_type(Gtk.ShadowType.ETCHED_IN)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        box.set_margin_start(10)
        box.set_margin_end(10)
        card.add(box)

        # Problem type
        type_label = Gtk.Label()
        type_label.set_markup("<b>{}</b>".format(GLib.markup_escape_text(problem_type or _("Unknown Issue"))))
        type_label.set_xalign(0)
        box.pack_start(type_label, False, False, 0)

        # Severity and region row
        info_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        sev_color = SEVERITY_COLORS.get(severity, ("#666", "#eee"))
        sev_label = Gtk.Label()
        sev_label.set_markup(
            '<span foreground="{}" background="{}" font="10"> {} </span>'.format(
                sev_color[0], sev_color[1],
                _("Severity: {}").format(severity)
            )
        )
        info_box.pack_start(sev_label, False, False, 0)

        reg_label = Gtk.Label()
        reg_label.set_markup(
            '<span foreground="#5f6368"> {}: {}</span>'.format(_("Region"), region)
        )
        info_box.pack_start(reg_label, False, False, 0)

        box.pack_start(info_box, False, False, 0)

        return card
