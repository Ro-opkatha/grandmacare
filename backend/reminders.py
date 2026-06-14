"""Relative medicine reminders.

Pure, gradio-free logic for the server-side reminder engine. Reminders store an
absolute monotonic-ish deadline (``time.time()`` seconds) computed from a
relative "remind in N minutes" request, so they survive UI re-renders and make
no wall-clock/timezone assumptions (HF Spaces runs in UTC). app.py wraps these
with the Gradio Timer/State plumbing.
"""

import time


def schedule_reminder(alarms, minutes, name, say, now=None):
    """Append a reminder due ``minutes`` from now. Returns ``(alarms, minutes)``
    where ``minutes`` is the clamped integer used (>= 1)."""
    try:
        minutes = max(1, int(minutes))
    except (TypeError, ValueError):
        minutes = 1
    now = time.time() if now is None else now
    alarms = list(alarms or [])
    alarms.append({"deadline": now + minutes * 60, "med": name, "say": say or ""})
    return alarms, minutes


def split_due(alarms, now=None):
    """Partition reminders into ``(due, remaining)`` by deadline."""
    now = time.time() if now is None else now
    alarms = list(alarms or [])
    due = [a for a in alarms if a["deadline"] <= now]
    remaining = [a for a in alarms if a["deadline"] > now]
    return due, remaining
