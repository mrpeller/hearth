"""A short in-memory log of what the TV and the bridge did, readable at /api/events."""
import collections
import os
import time

_log = collections.deque(maxlen=120)
DEBUG = os.environ.get("HEARTH_DEBUG", "0") not in ("", "0")


def add(source, message):
    _log.append({"t": round(time.time(), 2), "source": source, "message": message})
    if DEBUG:
        print(f"[{source}] {message}", flush=True)


def recent():
    return list(_log)
