"""
Performance monitor for AI Mentor plugin.

Tracks timing on key paths:
- Image encode (capture_image_b64)
- AI request (AI client send)
- JSON parse (parse_response)
- PDB execute (engine.execute)

Logs warnings when any step exceeds 80% of its SLA.
"""

import time


# SLA thresholds in seconds
SLA = {
    "image_encode":   2.0,
    "ai_request":    30.0,
    "json_parse":     0.5,
    "pdb_execute":    0.5,
    "preview_update": 0.5,
}


class PerfMonitor:
    """Collects and reports performance metrics."""

    def __init__(self, logger=None):
        self.logger = logger
        self.metrics = []

    def measure(self, name):
        """Context manager style: returns a timer callable."""
        return _PerfTimer(name, self)


class _PerfTimer:
    def __init__(self, name, monitor):
        self.name = name
        self.monitor = monitor
        self.start = None

    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.time() - self.start
        threshold = SLA.get(self.name, 1.0)
        warn_at = threshold * 0.8

        self.monitor.metrics.append({
            "name": self.name,
            "elapsed": round(elapsed, 4),
            "threshold": threshold,
            "warning": elapsed > warn_at,
        })

        if self.monitor.logger:
            level = "WARNING" if elapsed > warn_at else "DEBUG"
            flag = " ⚠" if elapsed > threshold else ""
            getattr(self.monitor.logger, level.lower())(
                "Perf",
                f"[{self.name}] {elapsed:.3f}s (SLA: {threshold}s){flag}"
            )

    @property
    def elapsed(self):
        if self.start is None:
            return 0
        return time.time() - self.start


def format_metrics(metrics):
    """Return a human-readable summary of collected metrics."""
    lines = []
    for m in metrics:
        flag = " ⚠ OVER SLA" if m["elapsed"] > m["threshold"] else ""
        lines.append(f"  {m['name']}: {m['elapsed']:.3f}s{flag}")
    return "\n".join(lines) if lines else "No metrics collected."
