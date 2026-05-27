#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GIMP AI Mentor — Main frontend dialog.

Integrates AI client, parser, engine, state machine, diagnosis panel,
step guide, toast notifications, and guide overlay into a GTK chat interface.
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk
gi.require_version('Gimp', '3.0')
from gi.repository import Gimp
from gi.repository import GLib
from gi.repository import Gio
gi.require_version('Gegl', '0.4')
from gi.repository import Gegl
gi.require_version('GimpUi', '3.0')
from gi.repository import GimpUi

import os
import sys
import json
import threading
import base64
import traceback
import uuid
import time

KEY_ESC = 65307  # gdk key constant


def _(message):
    return GLib.dgettext(None, message)


# ─── Backend imports ──────────────────────────────────────────

from ai.client import AIClient
from ai.parser import parse_response, parse_actions, format_action_list, build_system_prompt_for_json
from core.engine import Engine
from core.state_machine import GuideStateMachine, State
from core.logger import Logger, init as log_init, get as log_get
from core.layer_manager import (
    get_active_drawable, get_selection_bounds,
    toggle_preview_visibility, is_preview_visible,
    apply_preview_to_original, remove_preview_layer,
)

# ─── UI component imports ─────────────────────────────────────

from ui.diagnosis_panel import DiagnosisPanel
from ui.step_guide import StepGuide
from ui.toast import Toast
from ui.recipe_browser import RecipeBrowser

# ─── Recipe system ────────────────────────────────────────────

from recipes.presets import list_presets, get_preset
from recipes.manager import RecipeManager


# ─── Settings ─────────────────────────────────────────────────

class Settings:
    """Plugin settings persistence."""

    DEFAULTS = {
        "api_url": "https://api.openai.com/v1/chat/completions",
        "api_key": "",
        "model": "gpt-4o",
        "system_prompt": (
            "You are a professional photo editing assistant. "
            "Analyze the user's image, identify areas for improvement, "
            "and provide clear step-by-step editing guidance."
        ),
        "auto_apply": False,
        "mock_mode": False,
        "log_level": "INFO",
    }

    def __init__(self, config_dir):
        self.config_dir = config_dir
        self.config_path = os.path.join(config_dir, "config.json")
        self.data = dict(self.DEFAULTS)
        self.load()

    def load(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    for k, v in loaded.items():
                        self.data[k] = v
            except Exception:
                self.data = dict(self.DEFAULTS)

    def save(self):
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Settings save error: {e}", file=sys.stderr)

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value


# ─── Image Capture & Thumbnail ───────────────────────────────

def capture_image_b64(image):
    """Export GIMP image to base64 PNG string."""
    path = _export_image_to_png(image, "gimp_ai_send.png")
    if path:
        try:
            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
            os.unlink(path)
            return b64
        except Exception:
            try:
                os.unlink(path)
            except Exception:
                pass
    return None


def load_thumbnail_pixbuf(image, max_w=280, max_h=200):
    """Export a thumbnail and return a GdkPixbuf.Pixbuf."""
    path = _export_image_to_png(image, "gimp_ai_thumb.png")
    if not path:
        return None
    try:
        gi.require_version('GdkPixbuf', '2.0')
        from gi.repository import GdkPixbuf
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, max_w, max_h, True)
        os.unlink(path)
        return pixbuf
    except Exception as e:
        print(f"Thumbnail error: {e}", file=sys.stderr)
        try:
            os.unlink(path)
        except Exception:
            pass
    return None


def _export_image_to_png(image, filename):
    if image is None:
        return None
    try:
        temp_dir = GLib.get_tmp_dir()
        temp_path = os.path.join(temp_dir, filename)
        export_proc = Gimp.get_pdb().lookup_procedure("gimp-file-export")
        if export_proc:
            cfg = export_proc.create_config()
            cfg.set_property("image", image)
            cfg.set_property("file", Gio.File.new_for_path(temp_path))
            cfg.set_property("run-mode", Gimp.RunMode.NONINTERACTIVE)
            export_proc.run(cfg)
        else:
            save_proc = Gimp.get_pdb().lookup_procedure("file-png-save")
            if save_proc:
                cfg = save_proc.create_config()
                cfg.set_property("image", image)
                cfg.set_property("file", Gio.File.new_for_path(temp_path))
                cfg.set_property("run-mode", Gimp.RunMode.NONINTERACTIVE)
                save_proc.run(cfg)
            else:
                return None
        return temp_path if os.path.exists(temp_path) else None
    except Exception as e:
        print(f"Image export error: {e}", file=sys.stderr)
    return None


# ─── Text Tag Helpers ─────────────────────────────────────────

def _ensure_tag(buf, name, **props):
    tag = buf.get_tag_table().lookup(name)
    if tag is None:
        tag = buf.create_tag(name, **props)
    return tag


# ─── Settings Dialog ─────────────────────────────────────────

class SettingsDialog(Gtk.Dialog):
    """Plugin settings dialog."""

    def __init__(self, parent, settings):
        super().__init__(
            title=_("AI Settings"),
            parent=parent,
            flags=Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
            buttons=(_("Save"), Gtk.ResponseType.OK, _("Cancel"), Gtk.ResponseType.CANCEL)
        )
        self.set_default_size(540, 480)
        self.settings = settings
        self._build_ui()

    def _build_ui(self):
        content = self.get_content_area()
        content.set_border_width(12)
        content.set_spacing(8)

        content.pack_start(Gtk.Label.new(_("API URL")), False, False, 0)
        self.entry_url = Gtk.Entry.new()
        self.entry_url.set_text(self.settings.get("api_url", ""))
        self.entry_url.set_placeholder_text("https://api.openai.com/v1/chat/completions")
        content.pack_start(self.entry_url, False, False, 0)

        content.pack_start(Gtk.Label.new(_("API Key")), False, False, 0)
        self.entry_key = Gtk.Entry.new()
        self.entry_key.set_text(self.settings.get("api_key", ""))
        self.entry_key.set_visibility(False)
        content.pack_start(self.entry_key, False, False, 0)

        content.pack_start(Gtk.Label.new(_("Model")), False, False, 0)
        self.entry_model = Gtk.Entry.new()
        self.entry_model.set_text(self.settings.get("model", ""))
        self.entry_model.set_placeholder_text("gpt-4o / deepseek-chat / claude-3-sonnet")
        content.pack_start(self.entry_model, False, False, 0)

        # Mock mode
        self.check_mock = Gtk.CheckButton.new_with_label(_("Offline Demo Mode (use built-in mock responses)"))
        self.check_mock.set_active(self.settings.get("mock_mode", False))
        content.pack_start(self.check_mock, False, False, 0)

        # Auto-apply
        self.check_auto = Gtk.CheckButton.new_with_label(_("Auto-apply edit steps"))
        self.check_auto.set_active(self.settings.get("auto_apply", False))
        content.pack_start(self.check_auto, False, False, 0)

        content.pack_start(Gtk.Label.new(_("System Prompt")), False, False, 0)
        sw = Gtk.ScrolledWindow.new()
        sw.set_min_content_height(120)
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.buf_prompt = Gtk.TextBuffer.new()
        self.buf_prompt.set_text(self.settings.get("system_prompt", ""))
        txt = Gtk.TextView.new_with_buffer(self.buf_prompt)
        txt.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        sw.add(txt)
        content.pack_start(sw, True, True, 0)

        content.show_all()

    def apply(self):
        self.settings.set("api_url", self.entry_url.get_text().strip())
        self.settings.set("api_key", self.entry_key.get_text().strip())
        self.settings.set("model", self.entry_model.get_text().strip())
        self.settings.set("mock_mode", self.check_mock.get_active())
        self.settings.set("auto_apply", self.check_auto.get_active())
        start = self.buf_prompt.get_start_iter()
        end = self.buf_prompt.get_end_iter()
        self.settings.set("system_prompt", self.buf_prompt.get_text(start, end, True))
        self.settings.save()


# ─── Main Dialog ─────────────────────────────────────────────

class AiMentorDialog:
    """Main AI Mentor frontend dialog — integrates all SDD modules."""

    MAX_CHARS = 500

    def __init__(self, procedure, image, config_dir):
        self.procedure = procedure
        self.image = image

        # Core infrastructure
        self.settings = Settings(config_dir)
        self.log = log_init(config_dir, self.settings.get("log_level", "INFO"))
        self.state_machine = GuideStateMachine()
        self.ai_client = AIClient(self.settings)
        self.ai_client.mock_mode = self.settings.get("mock_mode", False)
        self.engine = Engine(image)

        # State
        self.messages = []
        self.image_b64 = None
        self.last_actions = []
        self.last_diagnosis = None
        self._request_thread = None
        self._exec_thread = None
        self._session_id = uuid.uuid4().hex[:8]

        # Recipe system
        self.recipe_manager = RecipeManager(config_dir)
        self.builtin_presets = list_presets()

        # Subscribe to state changes
        self.state_machine.subscribe(self._on_state_changed)

        self._build_ui()

        self.log.info("UI", f"Dialog initialized, session={self._session_id}")

    # ── UI Construction ──

    def _build_ui(self):
        self.window = Gtk.Window.new(Gtk.WindowType.TOPLEVEL)
        self.window.set_title(_("AI Photo Editing Assistant"))
        self.window.set_default_size(960, 760)
        self.window.set_position(Gtk.WindowPosition.CENTER)
        self.window.set_border_width(8)
        self.window.connect("destroy", lambda w: Gtk.main_quit())
        self.window.connect("key-press-event", self._on_key_press)

        # Toast overlay wrapper
        self.toast = Toast(self.window)
        self.window.add(self.toast)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.toast.add(vbox)

        # ── Toolbar ──
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        toolbar.set_margin_bottom(4)

        title = Gtk.Label()
        title.set_markup("<b>{}</b>".format(_("AI Photo Editing Assistant")))
        title.set_halign(Gtk.Align.START)
        toolbar.pack_start(title, True, True, 0)

        self.btn_cancel = Gtk.Button.new_with_label(_("Cancel"))
        self.btn_cancel.set_sensitive(False)
        self.btn_cancel.connect("clicked", self._on_cancel)
        toolbar.pack_end(self.btn_cancel, False, False, 0)

        self.btn_apply = Gtk.Button.new_with_label(_("Apply Steps"))
        self.btn_apply.set_sensitive(False)
        self.btn_apply.connect("clicked", self._on_apply)
        toolbar.pack_end(self.btn_apply, False, False, 0)

        btn_clear = Gtk.Button.new_with_label(_("Clear"))
        btn_clear.connect("clicked", self._on_clear)
        toolbar.pack_end(btn_clear, False, False, 0)

        btn_settings = Gtk.Button.new_with_label(_("Settings"))
        btn_settings.connect("clicked", self._on_settings)
        toolbar.pack_end(btn_settings, False, False, 0)

        vbox.pack_start(toolbar, False, False, 0)

        # ── Paned layout (left: chat + input, right: panels) ──
        paned = Gtk.Paned.new(Gtk.Orientation.HORIZONTAL)
        vbox.pack_start(paned, True, True, 0)

        # LEFT SIDE
        left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        paned.add1(left_box)
        self._build_chat_area(left_box)

        # RIGHT SIDE
        right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        paned.add2(right_box)
        self._build_right_panels(right_box)

        paned.set_position(580)

        # ── Status bar ──
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        status_box.set_margin_top(2)

        self.status = Gtk.Label()
        self.status.set_halign(Gtk.Align.START)
        status_box.pack_start(self.status, True, True, 0)

        self.selection_label = Gtk.Label()
        self.selection_label.set_halign(Gtk.Align.END)
        status_box.pack_end(self.selection_label, False, False, 0)

        vbox.pack_start(status_box, False, False, 0)

        self._update_image()
        self._update_selection_status()
        self._show_welcome()
        self.window.show_all()

    def _build_chat_area(self, parent):
        self.img_label = Gtk.Label()
        self.img_label.set_halign(Gtk.Align.START)
        self.img_label.set_margin_bottom(2)
        parent.pack_start(self.img_label, False, False, 0)

        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.set_hexpand(True)
        sw.set_vexpand(True)

        self.chat_buf = Gtk.TextBuffer()
        self.chat_view = Gtk.TextView.new_with_buffer(self.chat_buf)
        self.chat_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.chat_view.set_editable(False)
        self.chat_view.set_cursor_visible(False)
        self.chat_view.set_left_margin(8)
        self.chat_view.set_right_margin(8)
        self.chat_view.set_top_margin(8)
        self.chat_view.set_bottom_margin(8)
        sw.add(self.chat_view)
        parent.pack_start(sw, True, True, 0)

        # Step guide — in main window between chat and input
        self.step_guide = StepGuide()
        self.step_guide.connect_step_execute(self._on_step_execute)
        self.step_guide.connect_step_skip(self._on_step_skip)
        self.step_guide.connect_step_select(self._on_step_select)
        self.step_guide.set_margin_top(4)
        parent.pack_start(self.step_guide, False, True, 0)

        # Input area
        input_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        input_box.set_margin_top(4)

        self.entry = Gtk.Entry()
        self.entry.set_placeholder_text(_("e.g. Adjust brightness, remove noise... (max {} chars)".format(self.MAX_CHARS)))
        self.entry.connect("activate", self._on_send)
        self.entry.connect("changed", self._on_entry_changed)
        input_box.pack_start(self.entry, True, True, 0)

        self.char_counter = Gtk.Label()
        self.char_counter.set_markup(
            '<span foreground="#9aa0a6">0/{}</span>'.format(self.MAX_CHARS)
        )
        input_box.pack_start(self.char_counter, False, False, 0)

        btn_send = Gtk.Button.new_with_label(_("Send"))
        btn_send.connect("clicked", self._on_send)
        input_box.pack_end(btn_send, False, False, 0)

        parent.pack_start(input_box, False, False, 0)

    def _build_right_panels(self, parent):
        # Preview
        preview_frame = Gtk.Frame.new(_("Image Preview"))
        preview_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        preview_box.set_margin_top(4)
        preview_box.set_margin_start(4)
        preview_box.set_margin_end(4)
        preview_box.set_margin_bottom(4)

        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.set_min_content_height(160)
        self.preview = Gtk.Image.new()
        self.preview.set_halign(Gtk.Align.CENTER)
        self.preview.set_valign(Gtk.Align.CENTER)
        sw.add(self.preview)
        preview_box.pack_start(sw, True, True, 0)

        # Before/After toggle
        self.btn_before_after = Gtk.ToggleButton.new_with_label(_("Before / After"))
        self.btn_before_after.set_sensitive(False)
        self.btn_before_after.connect("toggled", self._on_before_after)
        preview_box.pack_start(self.btn_before_after, False, False, 0)

        preview_frame.add(preview_box)
        parent.pack_start(preview_frame, False, False, 0)

        # Diagnosis panel
        self.diagnosis_panel = DiagnosisPanel()
        parent.pack_start(self.diagnosis_panel, False, False, 0)

        # Recipe browser
        self.recipe_browser = RecipeBrowser(self.recipe_manager, self.builtin_presets)
        self.recipe_browser.connect_apply(self._on_recipe_apply)
        parent.pack_start(self.recipe_browser, True, True, 0)

    # ── Image Handling ──

    def _update_image(self):
        if self.image is None:
            self.img_label.set_markup(_("No image open"))
            return
        w = self.image.get_width()
        h = self.image.get_height()
        gfile = self.image.get_file()
        name = gfile.get_basename() if gfile else "Untitled"
        self.img_label.set_markup("{}: {} x {} px | {}".format(_("Image"), w, h, name))
        self.image_b64 = capture_image_b64(self.image)
        pixbuf = load_thumbnail_pixbuf(self.image, 280, 200)
        if pixbuf:
            self.preview.set_from_pixbuf(pixbuf)

    def _update_selection_status(self):
        bounds = get_selection_bounds(self.image)
        if bounds:
            x1, y1, x2, y2 = bounds
            w, h = x2 - x1, y2 - y1
            self.selection_label.set_markup(
                '<span foreground="#1a73e8">{}: {} ({},{} {}x{})</span>'.format(
                    _("Selection"), _("Active"), x1, y1, w, h
                )
            )
            self._selection_active = True
            self._selection_bounds = bounds
        else:
            self.selection_label.set_markup(
                '<span foreground="#9aa0a6">{}: {}</span>'.format(_("Selection"), _("None"))
            )
            self._selection_active = False
            self._selection_bounds = None

    # ── Chat Logic ──

    def _show_welcome(self):
        self._append("AI", _(
            "Hello! I'm your AI photo editing assistant.\n\n"
            "1. Configure your API key in Settings, or enable Offline Demo Mode\n"
            "2. Describe what you want to improve (e.g. 'Make the photo brighter and warmer')\n"
            "3. I'll analyze your image and suggest editing steps\n"
            "4. Review the steps and click Execute on each, or Apply All\n\n"
            "Tip: Enable 'Offline Demo Mode' in Settings to try without an API key."
        ))

    def _append(self, role, text):
        end = self.chat_buf.get_end_iter()
        _ensure_tag(self.chat_buf, "role_user", weight=700,
                     foreground="#1a73e8", scale=1.1, pixels_below_lines=4)
        _ensure_tag(self.chat_buf, "role_ai", weight=700,
                     foreground="#0d652d", scale=1.1, pixels_below_lines=4)
        tag_name = "role_user" if role == "user" else "role_ai"
        prefix = _("You: ") if role == "user" else _("Assistant: ")
        self.chat_buf.insert_with_tags(end, prefix,
                                        self.chat_buf.get_tag_table().lookup(tag_name))
        self.chat_buf.insert(end, f"{text}\n\n")
        adj = self.chat_view.get_parent().get_vadjustment()
        if adj:
            GLib.idle_add(lambda: adj.set_value(adj.get_upper() - adj.get_page_size()))

    def _on_entry_changed(self, widget):
        text = self.entry.get_text()
        count = len(text)
        if count > self.MAX_CHARS:
            self.entry.set_text(text[:self.MAX_CHARS])
            count = self.MAX_CHARS
        color = "#d93025" if count > 400 else "#9aa0a6"
        self.char_counter.set_markup(
            '<span foreground="{}">{}/{}</span>'.format(color, count, self.MAX_CHARS)
        )

    def _on_send(self, widget=None):
        text = self.entry.get_text().strip()
        if not text:
            return
        if not self.settings.get("api_key") and not self.settings.get("mock_mode"):
            self._append("AI", _("Please configure your API key in Settings, or enable Offline Demo Mode."))
            self.toast.show(_("No API key configured. Enable Mock Mode in Settings to try offline."), "warning")
            return

        self.state_machine.transition(State.ANALYZING)
        self.entry.set_sensitive(False)
        self.btn_cancel.set_sensitive(True)
        self._update_selection_status()

        # Build user message with selection context
        if self._selection_active:
            bounds = self._selection_bounds
            meta_text = "{} ({}: x1={}, y1={}, w={}, h={})".format(
                text, _("Selection Active"),
                bounds[0], bounds[1], bounds[2] - bounds[0], bounds[3] - bounds[1]
            )
        else:
            meta_text = text

        self._append("user", text)
        self.messages.append({"role": "user", "content": meta_text})
        self.status.set_text(_("AI is analyzing the image..."))

        self._request_thread = threading.Thread(target=self._do_request, daemon=True)
        self._request_thread.start()

    def _do_request(self):
        try:
            system_json = build_system_prompt_for_json()
            original_prompt = self.settings.get("system_prompt", "")
            self.ai_client.system_prompt = original_prompt + "\n\n" + system_json
            self.ai_client.mock_mode = self.settings.get("mock_mode", False)
            self.ai_client.reset_cancel()

            t0 = time.time()
            response = self.ai_client.send(self.messages, image_b64=self.image_b64)
            elapsed = time.time() - t0
            self.log.info("AI", f"Request completed in {elapsed:.1f}s")
            GLib.idle_add(self._on_response, response)
        except Exception as e:
            self.log.error("AI", f"Request failed: {e}")
            GLib.idle_add(self._on_error, str(e))

    def _on_response(self, text):
        self.messages.append({"role": "assistant", "content": text})
        self._append("AI", text)

        # Parse diagnosis + actions
        diagnosis, actions = parse_response(text)
        self.last_diagnosis = diagnosis
        self.last_actions = actions

        # Update diagnosis panel
        self.diagnosis_panel.set_diagnosis(diagnosis)

        # Update step guide
        if actions:
            self.step_guide.set_steps(actions)
            self.btn_apply.set_sensitive(True)
            self.btn_before_after.set_sensitive(True)

            token_info = self.ai_client.get_token_summary()
            status_text = _("Ready — {} steps found").format(len(actions))
            if token_info:
                status_text += " | " + token_info
            self.status.set_text(status_text)

            # Transition to GUIDING
            self.state_machine.transition(State.GUIDING, step_count=len(actions))

            if self.settings.get("auto_apply", False):
                self._on_step_execute(0)
        else:
            # No structured actions found
            self.status.set_text(_("Ready"))
            self.state_machine.transition(State.IDLE)

        token_info = self.ai_client.get_token_summary()
        if token_info and not actions:
            self.status.set_text(self.status.get_text() + " | " + token_info)

        self.entry.set_sensitive(True)
        self.entry.set_text("")
        self.entry.grab_focus()
        self.btn_cancel.set_sensitive(False)
        self._request_thread = None

    def _on_error(self, msg):
        self._append("AI", "[Error] " + msg)
        self.entry.set_sensitive(True)
        self.btn_cancel.set_sensitive(False)
        self.status.set_text(_("Error"))
        self.state_machine.transition(State.ERROR, error=msg)
        self.toast.show(msg, "error")
        self.log.error("UI", msg)

    # ── Cancel ──

    def _on_cancel(self, widget=None):
        self.ai_client.cancel()
        self.status.set_text(_("Cancelling..."))
        self.toast.show(_("Request cancelled"), "warning")
        self.btn_cancel.set_sensitive(False)
        self.entry.set_sensitive(True)
        self.state_machine.transition(State.IDLE)
        self.log.info("UI", "Request cancelled by user")

    # ── Step Guide Callbacks ──

    def _on_step_execute(self, index):
        """Execute a single step by index."""
        if index is None or index < 0 or index >= len(self.last_actions):
            return

        self.state_machine.transition(State.EXECUTING)
        action = self.last_actions[index]

        # Skip diagnosis and text_step
        if action.get("action") in ("diagnosis", "text_step"):
            self.step_guide.set_step_status(index, "completed")
            self.state_machine.transition(State.GUIDING)
            return

        self.step_guide.set_step_status(index, "active")
        self.status.set_text(_("Executing: {}").format(action.get("description", "")))

        self._exec_thread = threading.Thread(
            target=self._do_execute_single, args=(index, action), daemon=True
        )
        self._exec_thread.start()

    def _on_step_skip(self, index):
        if 0 <= index < len(self.last_actions):
            self.step_guide.set_step_status(index, "ignored")
            self.toast.show(_("Step {} skipped").format(index + 1), "info")

    def _on_step_select(self, index):
        """Show selected step instruction in-chat."""
        if 0 <= index < len(self.last_actions):
            action = self.last_actions[index]
            total = len(self.last_actions)
            desc = action.get("description", action.get("action", ""))
            self._append("AI", _("Step {}/{}: {}").format(index + 1, total, desc))

    def _do_execute_single(self, index, action):
        try:
            t0 = time.time()
            result = self.engine.execute_single(action)
            elapsed = time.time() - t0
            self.log.info("Engine", f"Step {index} executed in {elapsed:.1f}s: {result.message}")
            GLib.idle_add(self._on_step_executed, index, result)
        except Exception as e:
            self.log.error("Engine", f"Step {index} failed: {e}")
            GLib.idle_add(self._on_step_error, index, str(e))

    def _on_step_executed(self, index, result):
        status = "completed" if result.success else "failed"
        self.step_guide.set_step_status(index, status)
        if result.success:
            self.toast.show(result.message, "success")
            self.btn_before_after.set_sensitive(True)
        else:
            self.toast.show(result.message, "error")

        self.state_machine.transition(State.GUIDING)
        self.status.set_text(_("Ready"))
        self._exec_thread = None

    def _on_step_error(self, index, msg):
        self.step_guide.set_step_status(index, "failed")
        self.toast.show(msg, "error")
        self.state_machine.transition(State.GUIDING)
        self._exec_thread = None

    # ── Apply All ──

    def _on_apply(self, widget=None):
        actions_to_exec = [a for a in self.last_actions
                          if a.get("action") not in ("diagnosis", "text_step")]
        if not actions_to_exec:
            self.toast.show(_("No executable steps found."), "warning")
            return

        self.state_machine.transition(State.EXECUTING)
        self.btn_apply.set_sensitive(False)
        self.status.set_text(_("Applying all steps..."))

        def step_cb(i, total, status):
            GLib.idle_add(lambda: self.step_guide.set_step_status(i, status))

        self._exec_thread = threading.Thread(
            target=self._do_execute_all, args=(actions_to_exec, step_cb), daemon=True
        )
        self._exec_thread.start()

    def _do_execute_all(self, actions, step_cb):
        try:
            results = self.engine.execute(actions, step_callback=step_cb)
            GLib.idle_add(self._on_executed, results)
        except Exception as e:
            self.log.error("Engine", f"Batch execute failed: {e}")
            GLib.idle_add(self._on_error, str(e))

    def _on_executed(self, results):
        success_count = sum(1 for r in results if r.success)
        fail_count = len(results) - success_count

        if fail_count == 0:
            msg = _("Successfully applied {} step(s). Use Ctrl+Z to undo.").format(success_count)
            self.toast.show(msg, "success")
        else:
            msg = _("Applied {} step(s), {} failed.").format(success_count, fail_count)
            self.toast.show(msg, "warning")

        self._append("AI", msg)
        self.status.set_text(msg)
        self.btn_apply.set_sensitive(True)
        self.btn_before_after.set_sensitive(True)
        self.state_machine.transition(State.IDLE)
        self._exec_thread = None

    # ── Before/After Toggle ──

    def _on_before_after(self, widget):
        if widget.get_active():
            widget.set_label(_("Show After"))
            # Hide preview layer (show original)
            toggle_preview_visibility(self.image)
            self.toast.show(_("Showing original image (Before)"), "info")
        else:
            widget.set_label(_("Before / After"))
            # Show preview layer
            toggle_preview_visibility(self.image)
            self.toast.show(_("Showing edited image (After)"), "info")

    # ── State Machine Observer ──

    def _on_state_changed(self, old_state, new_state, context):
        state_names = {
            State.IDLE: _("Idle"),
            State.ANALYZING: _("Analyzing..."),
            State.GUIDING: _("Guiding"),
            State.EXECUTING: _("Executing..."),
            State.ERROR: _("Error"),
        }
        self.log.debug("State", f"{old_state.name} → {new_state.name}")
        # UI state-dependent updates can go here

    # ── Key Press ──

    def _on_key_press(self, widget, event):
        if event.keyval == KEY_ESC:
            if self.state_machine.state == State.ANALYZING:
                self._on_cancel()
                return True
        return False

    # ── Actions ──

    def _on_settings(self, widget):
        dlg = SettingsDialog(self.window, self.settings)
        response = dlg.run()
        if response == Gtk.ResponseType.OK:
            dlg.apply()
            self.ai_client = AIClient(self.settings)
            self.ai_client.mock_mode = self.settings.get("mock_mode", False)
            self.toast.show(_("Settings saved."), "success")
        dlg.destroy()

    def _on_clear(self, widget):
        self.chat_buf.set_text("")
        self.messages = []
        self.last_actions = []
        self.last_diagnosis = None
        self.step_guide.set_steps([])
        self.diagnosis_panel.clear()
        self.btn_apply.set_sensitive(False)
        self.btn_before_after.set_sensitive(False)
        self.state_machine.reset()
        self._show_welcome()

    def _on_recipe_apply(self, recipe):
        """Apply a recipe: load diagnosis + steps into the UI."""
        diagnosis = recipe.get("diagnosis_template")
        steps = recipe.get("steps", [])

        self.diagnosis_panel.set_diagnosis(diagnosis)
        self.last_diagnosis = diagnosis

        # Convert recipe steps to action format
        actions = []
        for s in steps:
            actions.append({
                "action": s.get("action", "text_step"),
                "params": s.get("params", {}),
                "description": s.get("description", s.get("title", s.get("action", "")))
            })
        self.last_actions = actions
        self.step_guide.set_steps(actions)
        self.btn_apply.set_sensitive(True)
        self.btn_before_after.set_sensitive(True)

        recipe_name = recipe.get("metadata", {}).get("name", _("Recipe"))
        self._append("AI", _("Loaded recipe: {} ({} steps)").format(recipe_name, len(actions)))
        self.toast.show(_("Recipe '{}' loaded. Review steps and click Apply.").format(recipe_name), "success")
        self.state_machine.transition(State.GUIDING)

    # ── Entry Point ──

    def run(self):
        css_path = os.path.join(self.settings.config_dir, "src", "ui", "styles.css")
        if os.path.exists(css_path):
            try:
                provider = Gtk.CssProvider()
                provider.load_from_path(css_path)
                Gtk.StyleContext.add_provider_for_screen(
                    Gdk.Screen.get_default(), provider,
                    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
                )
            except Exception as e:
                print(f"CSS: {e}", file=sys.stderr)

        self.window.show_all()
        Gtk.main()
        return self.procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, GLib.Error())
