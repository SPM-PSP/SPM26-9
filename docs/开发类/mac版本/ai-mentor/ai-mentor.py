#!/Applications/GIMP.app/Contents/MacOS/python3.10
# -*- coding: utf-8 -*-

# GIMP AI Mentor - Smart Photo Editing Assistant Plugin
# Copyright (C) 2024 GIMP AI Mentor Team
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.

"""
GIMP AI Mentor plugin entry point.

Registers the plugin with GIMP and launches the frontend dialog.
The UI frontend is implemented in src/ui/dialog.py.
"""

import gi
gi.require_version('Gimp', '3.0')
from gi.repository import Gimp
from gi.repository import GObject
from gi.repository import GLib
from gi.repository import Gio
gi.require_version('Gegl', '0.4')
from gi.repository import Gegl
gi.require_version('GimpUi', '3.0')
from gi.repository import GimpUi

import sys
import os

# Add src directory to path for module imports
PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(PLUGIN_DIR, "src"))


def N_(message): return message
def _(message): return GLib.dgettext(None, message)

PROC_NAME = "python-fu-ai-mentor"


def run_plugin(procedure, run_mode, image, drawables, config, data):
    """Plugin entry point called by GIMP."""
    if image is None:
        return procedure.new_return_values(
            Gimp.PDBStatusType.CALLING_ERROR,
            GLib.Error(_("Please open an image first."))
        )

    if run_mode == Gimp.RunMode.INTERACTIVE:
        GimpUi.init("python-fu-ai-mentor")

        # Import frontend module
        from ui.dialog import AiMentorDialog
        dialog = AiMentorDialog(procedure, image, PLUGIN_DIR)
        return dialog.run()

    return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, GLib.Error())


class AiMentorPlugin(Gimp.PlugIn):
    """GIMP AI Mentor Plugin."""

    def do_set_i18n(self, procname):
        return True, 'gimp30-python', None

    def do_query_procedures(self):
        return [PROC_NAME]

    def do_create_procedure(self, name):
        procedure = Gimp.ImageProcedure.new(
            self, name,
            Gimp.PDBProcType.PLUGIN,
            run_plugin, None
        )

        procedure.set_image_types("RGB*, GRAY*")
        procedure.set_documentation(
            _("AI Photo Editing Assistant"),
            _("Interact with AI via natural language to get professional photo editing guidance."),
            name
        )
        procedure.set_menu_label(_("AI Photo Editing Assistant..."))
        procedure.set_attribution(
            "GIMP AI Mentor Team",
            "GIMP AI Mentor Team",
            "2024"
        )
        procedure.add_menu_path("<Image>/Filters/AI")

        return procedure


Gimp.main(AiMentorPlugin.__gtype__, sys.argv)
