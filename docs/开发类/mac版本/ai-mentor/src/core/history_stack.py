"""
Independent operation history stack for AI Mentor.

Maintains a separate undo/redo history for AI-suggested operations,
independent of GIMP's native undo stack, enabling one-click rollback
of the entire AI session.
"""

import sys


class HistoryStack:
    """
    Records AI operations as discrete snapshots.
    Supports session-level undo (revert all AI changes) and redo.
    """

    def __init__(self, image, max_entries=50):
        self.image = image
        self.max_entries = max_entries
        self._undo_stack = []   # list of operation descriptions
        self._redo_stack = []

    def record(self, operation_desc):
        """Record an operation that was just applied."""
        self._undo_stack.append(operation_desc)
        self._redo_stack.clear()
        if len(self._undo_stack) > self.max_entries:
            self._undo_stack.pop(0)

    def undo_last(self):
        """Undo the last AI operation via GIMP's native undo. Returns True if undone."""
        if not self._undo_stack:
            return False
        try:
            import gi
            gi.require_version('Gimp', '3.0')
            from gi.repository import Gimp

            image_undo = Gimp.get_pdb().lookup_procedure("gimp-image-undo")
            if image_undo:
                cfg = image_undo.create_config()
                cfg.set_property("image", self.image)
                image_undo.run(cfg)
                self._redo_stack.append(self._undo_stack.pop())
                return True
        except Exception as e:
            print(f"History undo error: {e}", file=sys.stderr)
        return False

    def redo_last(self):
        """Redo the last undone AI operation. Returns True if redone."""
        if not self._redo_stack:
            return False
        try:
            import gi
            gi.require_version('Gimp', '3.0')
            from gi.repository import Gimp

            image_redo = Gimp.get_pdb().lookup_procedure("gimp-image-redo")
            if image_redo:
                cfg = image_redo.create_config()
                cfg.set_property("image", self.image)
                image_redo.run(cfg)
                self._undo_stack.append(self._redo_stack.pop())
                return True
        except Exception as e:
            print(f"History redo error: {e}", file=sys.stderr)
        return False

    def undo_all(self):
        """Undo all recorded AI operations."""
        count = 0
        while self._undo_stack:
            if self.undo_last():
                count += 1
            else:
                break
        return count

    def clear(self):
        """Clear history without affecting GIMP state."""
        self._undo_stack.clear()
        self._redo_stack.clear()

    @property
    def undo_count(self):
        return len(self._undo_stack)

    @property
    def redo_count(self):
        return len(self._redo_stack)
