"""Wires everything together: the TV, the ad blocker, Wi-Fi scanning and the background loops."""
import json
import threading
import time

from . import config, intent, network
from .adblock import AdBlocker
from .certs import find as find_certs
from .tv import TV
from .updater import Updater
from .wifi import Watcher


class App:
    def __init__(self, settings=None, state=None, cert_dir=None, start_services=True):
        self.settings = settings or config.Settings()
        self.state = state or config.JsonStore(config.DATA / "state.json")
        self.port = int(self.settings.get("http_port"))
        self.cert_dir = cert_dir or config.CERTS
        self.tv = TV(self.state, self.settings, self.home_url, cert_dir=self.cert_dir)
        self.adblock = AdBlocker(port=int(self.settings.get("dns_port")), upstreams=self.settings.get("upstream_dns"),
                                 enabled=bool(self.settings.get("adblock_on")))
        self.wifi = Watcher()
        self.saver_req = 0
        if start_services:
            self.start()

    def start(self):
        if self.settings.get("adblock"):
            self.adblock.start()
        self.wifi.start()
        if self.settings.get("auto_update"):
            Updater(interval=60 * float(self.settings.get("update_minutes"))).start()
        threading.Thread(target=self._keep_connected, daemon=True).start()
        threading.Thread(target=self._watch_screen, daemon=True).start()

    # ---- background loops ---------------------------------------------
    def _keep_connected(self):
        """Reconnect within a couple of seconds whenever the TV comes back."""
        while True:
            if self.tv.ip and not self.tv.connected and not self.tv.needs_pairing and not self.tv.connecting:
                self.tv.connect(self.tv.ip)
            time.sleep(2)

    def _watch_screen(self):
        """Ask the TV what it's showing every 2 s, so the launcher swap reacts quickly."""
        while True:
            if self.tv.connected and self.tv.paired and self.settings.get("own_home"):
                try:
                    self.tv.poll_state()
                except RuntimeError:
                    pass
            time.sleep(2)

    # ---- helpers -------------------------------------------------------
    def home_url(self):
        return f"http://{network.local_ip()}:{self.port}/tv/"

    def web_build(self):
        """Changes when the TV home's files change, so an open TV page reloads itself."""
        files = [config.WEB / "tv" / "index.html", config.WEB / "brands.js", config.ROOT / "settings.json"]
        return int(max((f.stat().st_mtime for f in files if f.exists()), default=0))

    def apps(self):
        tv_apps = list(self.tv.apps)
        return tv_apps + [a for a in self.settings.get("extra_apps") if not intent.find_app(tv_apps, a["name"])]

    def _resolve(self, names, apps):
        """Settings name apps loosely ("Spotify"); the pages need the TV's exact names."""
        out = []
        for n in names:
            app = intent.find_app(apps, n)
            out.append(app["name"] if app else n)
        return out

    def photos(self):
        try:
            with open(config.WEB / "tv" / "bg" / "photos.json", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return []

    def wifi_status(self):
        for k, v in self.tv.info.items():
            if any(w in k.lower() for w in ("ssid", "wifi_name", "wifiname", "network_name")) and v:
                return {**self.wifi.latest, "ssid": str(v), "from": "tv"}
        return {**self.wifi.latest, "from": "host"}

    def status(self):
        apps = self.apps()
        tv = self.tv
        return {
            "connected": tv.connected, "paired": tv.paired, "needs_pairing": tv.needs_pairing,
            "has_cert": bool(find_certs(self.cert_dir)[0]), "error": tv.last_error,
            "ip": tv.ip, "mac": tv.store.get("mac", ""),
            "state": tv.state, "volume": tv.volume, "sources": tv.sources, "apps": apps,
            "dock": self._resolve(self.settings.get("dock"), apps),
            "hidden": self._resolve(self.settings.get("hidden"), apps),
            "sites": self.settings.get("sites"),
            "household": self.settings.get("household"),
            "mood": self.settings.get("mood"),
            "own_home": bool(self.settings.get("own_home")),
            "moods": [{"label": label, "phrase": phrase, "target": (intent.decide(phrase, apps, tv.sources) or {}).get("label", "")}
                      for label, phrase in intent.MOODS],
            "photos": self.photos(), "build": self.web_build(), "saver_req": self.saver_req,
            "home_ready": int(tv.last_ready),   # when the TV page last finished loading
            "home_url": self.home_url(), "dns_ip": network.local_ip(),
            "adblock": self.adblock.status(), "wifi": self.wifi_status(),
        }

    def do_intent(self, text):
        d = intent.decide(text, self.apps(), self.tv.sources)
        if not d:
            return {"ok": False, "why": "I couldn't match that to an app or input. Try naming the app or show."}
        if d["kind"] == "app":
            self.tv.launch(d["target"])
        else:
            self.tv.source(d["target"]["sourceid"], d["target"]["sourcename"])
        return {"ok": True, "label": d["label"], "why": d["why"]}
