"""Where things live, and the settings that shape the home screen.

Settings are layered, later layers winning:
  1. DEFAULTS below
  2. settings.json in the project root (your household, sites, favourite apps...)
  3. data/prefs.json (changes made from the phone remote or the TV, saved automatically)

data/state.json holds the TV session (address, login tokens, cached app list). It is
private to your machine and never committed.
"""
import copy
import json
import os
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
DATA = Path(os.environ.get("HEARTH_DATA", ROOT / "data"))
CERTS = Path(os.environ.get("HEARTH_CERTS", ROOT / "certs"))
ADBLOCK = ROOT / "adblock"
SETTINGS_FILE = Path(os.environ.get("HEARTH_SETTINGS", ROOT / "settings.json"))

MOODS = ("auto", "peaceful", "strong", "grateful", "comfort", "hopeful", "rest")

DEFAULTS = {
    # Shown in the greeting: "Good morning, <household>".
    "household": "",
    # Quick access row, by app name (a prefix is enough: "Spotify" matches "Spotify : Music & Podcasts").
    "dock": ["Netflix", "YouTube", "Spotify", "Apple TV"],
    # Preinstalled apps kept off the home screen (still reachable from the phone remote's editor).
    "hidden": [
        "VIDAA Art", "Vidaa Smart Life", "E-Manual", "V Home", "APP STORE", "Vod On Demand",
        "A to Z Movie Box", "TV Browser", "AccuWeather",
    ],
    # Websites shown under "Recent sites": {name, url, icon, bg, fit: contain|cover, glow, sub}.
    "sites": [],
    # Apps that aren't on every VIDAA store, opened as web pages.
    "extra_apps": [{"appId": "appletv-web", "name": "Apple TV", "url": "https://tv.apple.com/"}],
    # Screensaver verse mood; "auto" follows the time of day.
    "mood": "auto",
    # Replace VIDAA's launcher with Hearth whenever it appears.
    "own_home": True,
    "http_port": 8765,
    # Pull new versions from GitHub (when this folder is a git clone) and restart.
    "auto_update": True,
    "update_minutes": 5,
    # Network ad blocker (DNS). Port 53 needs extra permission on Linux; see README.
    "adblock": True,          # run the DNS server at all
    "adblock_on": True,       # blocking switched on (the remote's switch pauses it)
    "dns_port": 53,
    "upstream_dns": ["1.1.1.1", "8.8.8.8"],
}


class JsonStore:
    """A small JSON file that is read once and written atomically on every change."""

    def __init__(self, path):
        self.path = Path(path)
        self._lock = threading.RLock()
        self.data = self._read()

    def _read(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def get(self, key, default=None):
        with self._lock:
            return self.data.get(key, default)

    def update(self, **values):
        with self._lock:
            self.data.update(values)
            self.save()

    def pop(self, *keys):
        with self._lock:
            for k in keys:
                self.data.pop(k, None)
            self.save()

    def replace(self, data):
        with self._lock:
            self.data = dict(data)
            self.save()

    def save(self):
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            os.replace(tmp, self.path)


class Settings:
    """DEFAULTS, then settings.json, then the saved preferences from the remote."""

    def __init__(self, settings_file=SETTINGS_FILE, prefs_file=None):
        self.file = JsonStore(settings_file)
        self.prefs = JsonStore(prefs_file or DATA / "prefs.json")

    def get(self, key):
        if key in self.prefs.data:
            return copy.deepcopy(self.prefs.data[key])
        if key in self.file.data:
            return copy.deepcopy(self.file.data[key])
        return copy.deepcopy(DEFAULTS.get(key))

    def set(self, **values):
        self.prefs.update(**values)
