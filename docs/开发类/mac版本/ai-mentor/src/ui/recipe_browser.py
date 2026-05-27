"""
Recipe Browser — GTK panel for browsing, loading, importing, and exporting recipes.
"""

import os
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib


def _(message):
    return GLib.dgettext(None, message)


class RecipeBrowser(Gtk.Frame):
    """Browse built-in and user recipe presets."""

    def __init__(self, recipe_manager, builtin_presets):
        super().__init__(label=_("Recipe Library"))
        self.get_label_widget().set_markup("<b>{}</b>".format(_("Recipe Library")))
        self._manager = recipe_manager
        self._builtins = builtin_presets or []
        self._on_apply_recipe = None
        self._build_ui()
        self._refresh()

    def _build_ui(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        outer.set_margin_top(6)
        outer.set_margin_start(6)
        outer.set_margin_end(6)
        outer.set_margin_bottom(6)
        self.add(outer)

        # Notebook tabs: Built-in | User
        notebook = Gtk.Notebook()
        notebook.set_tab_pos(Gtk.PositionType.TOP)

        # Tab 1: Built-in presets
        self.builtin_list = Gtk.ListBox()
        self.builtin_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.builtin_list.connect("row-selected", self._on_list_selection_changed)
        self.builtin_list.connect("row-activated", lambda w, r: self._on_apply(None))
        sw1 = Gtk.ScrolledWindow()
        sw1.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw1.set_min_content_height(180)
        sw1.add(self.builtin_list)
        notebook.append_page(sw1, Gtk.Label.new(_("Built-in")))

        # Tab 2: User recipes
        user_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)

        self.user_list = Gtk.ListBox()
        self.user_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.user_list.connect("row-selected", self._on_list_selection_changed)
        self.user_list.connect("row-activated", lambda w, r: self._on_apply(None))
        sw2 = Gtk.ScrolledWindow()
        sw2.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw2.set_min_content_height(150)
        sw2.add(self.user_list)
        user_box.pack_start(sw2, True, True, 0)

        btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        btn_import = Gtk.Button.new_with_label(_("Import"))
        btn_import.connect("clicked", self._on_import)
        btn_row.pack_start(btn_import, True, True, 0)

        btn_export = Gtk.Button.new_with_label(_("Export"))
        btn_export.connect("clicked", self._on_export)
        btn_row.pack_start(btn_export, True, True, 0)
        user_box.pack_start(btn_row, False, False, 0)

        notebook.append_page(user_box, Gtk.Label.new(_("My Recipes")))

        outer.pack_start(notebook, True, True, 0)

        # Apply button
        self.btn_apply_recipe = Gtk.Button.new_with_label(_("Use This Recipe"))
        self.btn_apply_recipe.set_sensitive(False)
        self.btn_apply_recipe.connect("clicked", self._on_apply)
        outer.pack_start(self.btn_apply_recipe, False, False, 0)

        self.show_all()

    def _refresh(self):
        """Reload both built-in and user recipe lists."""
        # Built-ins
        for child in self.builtin_list.get_children():
            self.builtin_list.remove(child)
        for pid, name, tags in self._builtins:
            row = Gtk.ListBoxRow()
            row.recipe_id = pid
            row.recipe_source = "builtin"
            label = Gtk.Label()
            label.set_markup("<b>{}</b>\n<span foreground='#5f6368' size='small'>{}</span>".format(
                GLib.markup_escape_text(name),
                GLib.markup_escape_text(", ".join(tags[:3]) if tags else "")
            ))
            label.set_xalign(0)
            label.set_margin_start(8)
            label.set_margin_top(4)
            label.set_margin_bottom(4)
            row.add(label)
            self.builtin_list.add(row)

        # User recipes
        for child in self.user_list.get_children():
            self.user_list.remove(child)
        user_recipes = self._manager.load_all()
        for rid, name in user_recipes:
            row = Gtk.ListBoxRow()
            row.recipe_id = rid
            row.recipe_source = "user"
            label = Gtk.Label()
            label.set_markup("<b>{}</b>".format(GLib.markup_escape_text(name)))
            label.set_xalign(0)
            label.set_margin_start(8)
            label.set_margin_top(4)
            label.set_margin_bottom(4)
            row.add(label)
            self.user_list.add(row)

        self.builtin_list.show_all()
        self.user_list.show_all()

    def _on_list_selection_changed(self, listbox, row):
        """Enable the apply button only when a row is actually selected."""
        self.btn_apply_recipe.set_sensitive(row is not None)

    def _on_apply(self, widget):
        """Load selected recipe and call the apply callback."""
        # Check built-in list first
        for row in self.builtin_list.get_children():
            if row.is_selected():
                rid = row.recipe_id
                if row.recipe_source == "builtin":
                    from recipes.presets import get_preset
                    recipe = get_preset(rid)
                    if recipe and self._on_apply_recipe:
                        self._on_apply_recipe(recipe)
                return

        # Check user list
        for row in self.user_list.get_children():
            if row.is_selected():
                rid = row.recipe_id
                recipe = self._manager.load_recipe(rid)
                if recipe and self._on_apply_recipe:
                    self._on_apply_recipe(recipe)
                return

    def _on_import(self, widget):
        """Open file dialog to import a recipe."""
        dlg = Gtk.FileChooserDialog(
            title=_("Import Recipe"), parent=self.get_toplevel(),
            action=Gtk.FileChooserAction.OPEN,
            buttons=(_("Cancel"), Gtk.ResponseType.CANCEL, _("Import"), Gtk.ResponseType.ACCEPT)
        )
        filt = Gtk.FileFilter()
        filt.set_name("GIMP AI Recipe (*.gimp-ai-recipe)")
        filt.add_pattern("*.gimp-ai-recipe")
        dlg.add_filter(filt)

        res = dlg.run()
        if res == Gtk.ResponseType.ACCEPT:
            path = dlg.get_filename()
            recipe, error = self._manager.import_recipe(path)
            if error:
                self._show_error(_("Import failed: {}").format(error))
            else:
                self._refresh()
                self._show_info(_("Recipe '{}' imported successfully.").format(
                    recipe["metadata"]["name"]
                ))
        dlg.destroy()

    def _on_export(self, widget):
        """Export selected user recipe to a file."""
        for row in self.user_list.get_children():
            if row.is_selected() and row.recipe_source == "user":
                rid = row.recipe_id
                recipe = self._manager.load_recipe(rid)
                if not recipe:
                    return
                dlg = Gtk.FileChooserDialog(
                    title=_("Export Recipe"), parent=self.get_toplevel(),
                    action=Gtk.FileChooserAction.SAVE,
                    buttons=(_("Cancel"), Gtk.ResponseType.CANCEL, _("Export"), Gtk.ResponseType.ACCEPT)
                )
                dlg.set_current_name(f"{rid}.gimp-ai-recipe")
                res = dlg.run()
                if res == Gtk.ResponseType.ACCEPT:
                    path = dlg.get_filename()
                    success, error = self._manager.export_recipe(rid, path)
                    if error:
                        self._show_error(_("Export failed: {}").format(error))
                    else:
                        self._show_info(_("Recipe exported successfully."))
                dlg.destroy()
                return

    def connect_apply(self, callback):
        """callback(recipe_dict) called when user clicks Use This Recipe."""
        self._on_apply_recipe = callback

    def refresh(self):
        self._refresh()

    def _show_error(self, msg):
        dlg = Gtk.MessageDialog(
            transient_for=self.get_toplevel(),
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text=msg
        )
        dlg.run()
        dlg.destroy()

    def _show_info(self, msg):
        dlg = Gtk.MessageDialog(
            transient_for=self.get_toplevel(),
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=msg
        )
        dlg.run()
        dlg.destroy()
