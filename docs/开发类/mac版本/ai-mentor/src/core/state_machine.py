"""
Guide State Machine — central coordinator for the AI Mentor workflow.

States: IDLE → ANALYZING → GUIDING → EXECUTING → IDLE
Error transitions to ERROR state, recoverable back to IDLE.

All state transitions fire callbacks so the UI can react without polling.
"""

import threading
from enum import Enum, auto


class State(Enum):
    IDLE = auto()
    ANALYZING = auto()
    GUIDING = auto()
    EXECUTING = auto()
    ERROR = auto()


class GuideStateMachine:
    """Manages the full 'analyze → guide → execute' workflow state."""

    def __init__(self):
        self._state = State.IDLE
        self._lock = threading.RLock()
        self._listeners = []
        self._context = {}  # arbitrary payload carried across transitions

    # ── Public API ──────────────────────────────────────────

    @property
    def state(self):
        with self._lock:
            return self._state

    @property
    def context(self):
        with self._lock:
            return dict(self._context)

    def can_transition(self, target):
        """Check if a transition is valid from current state."""
        return target in self._valid_transitions()

    def transition(self, target, **ctx):
        """
        Attempt a state transition. Returns True on success.
        Silently ignored if the transition is invalid.
        """
        with self._lock:
            if not self._valid_transitions() or target not in self._valid_transitions():
                return False
            old = self._state
            self._state = target
            self._context.update(ctx)
        self._fire(old, target)
        return True

    def subscribe(self, callback):
        """Register a callback(old_state, new_state, context)."""
        self._listeners.append(callback)

    def unsubscribe(self, callback):
        try:
            self._listeners.remove(callback)
        except ValueError:
            pass

    def reset(self):
        """Force-reset to IDLE, clearing context."""
        with self._lock:
            old = self._state
            self._state = State.IDLE
            self._context.clear()
        self._fire(old, State.IDLE)

    # ── Internals ───────────────────────────────────────────

    def _valid_transitions(self):
        return _TRANSITIONS.get(self._state, set())

    def _fire(self, old, new):
        ctx = dict(self._context)
        for cb in self._listeners:
            try:
                cb(old, new, ctx)
            except Exception:
                pass


_TRANSITIONS = {
    State.IDLE:      {State.ANALYZING, State.GUIDING},
    State.ANALYZING: {State.GUIDING, State.ERROR, State.IDLE},
    State.GUIDING:   {State.EXECUTING, State.IDLE, State.ERROR},
    State.EXECUTING: {State.GUIDING, State.IDLE, State.ERROR},
    State.ERROR:     {State.IDLE},
}
