"""Keeps a Hearth install up to date with its GitHub repo.

Every few minutes it fetches from the repo this folder was cloned from. If there are new
commits it fast-forwards to them and exits with RESTART_CODE; the start script (or the
system service) then starts the new version. Local edits are never overwritten: if the
folder has changes of its own, it skips updating and logs why.
"""
import os
import threading
import time

from . import config, events, network

RESTART_CODE = 3


# Never stop to ask for a password in the background; a failed fetch just tries again later.
_ENV = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}


def _git(*args, timeout=60):
    return network.run(["git", "-C", str(config.ROOT), *args], timeout=timeout, env=_ENV).strip()


def is_git_checkout():
    return bool(_git("rev-parse", "--is-inside-work-tree") == "true" and _git("rev-parse", "--abbrev-ref", "@{u}"))


def check_once():
    """Pull new commits if there are any. Returns True if the code changed."""
    _git("fetch", "--quiet")
    local, remote = _git("rev-parse", "HEAD"), _git("rev-parse", "@{u}")
    if not local or not remote or local == remote:
        return False
    if _git("merge-base", "HEAD", "@{u}") != local:
        events.add("update", "local commits differ from GitHub; not updating")
        return False
    if _git("status", "--porcelain", "--untracked-files=no"):
        events.add("update", "this folder has local edits; not updating")
        return False
    _git("merge", "--ff-only", "@{u}")
    if _git("rev-parse", "HEAD") != remote:
        events.add("update", "update failed")
        return False
    events.add("update", f"updated to {remote[:7]}: {_git('log', '-1', '--format=%s')}")
    return True


class Updater:
    def __init__(self, interval=300):
        self.interval = interval

    def start(self):
        if not is_git_checkout():
            return self
        threading.Thread(target=self._loop, daemon=True).start()
        return self

    def _loop(self):
        while True:
            time.sleep(self.interval)
            if check_once():
                print("Updated from GitHub, restarting...", flush=True)
                time.sleep(1)   # let in-flight requests finish
                os._exit(RESTART_CODE)
