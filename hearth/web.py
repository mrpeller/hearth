"""The web server: the phone remote at /, the TV home screen at /tv/, and a small JSON API."""
import json
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import config, events, network

# Artwork and the font never change under the same name, so the TV may keep them.
LONG_CACHE = ("/tv/logos/", "/tv/sites/", "/tv/bg/", "/tv/outfit.ttf")


def make_handler(app):
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(config.WEB), **kwargs)

        def log_message(self, fmt, *args):
            if events.DEBUG:
                super().log_message(fmt, *args)

        def end_headers(self):
            path = getattr(self, "path", "")
            self.send_header("Cache-Control", "public, max-age=604800" if path.startswith(LONG_CACHE) else "no-cache")
            super().end_headers()

        def _json(self, obj, code=200):
            body = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _tv_home(self):
            """The TV page with its script and current data built in, so it draws without further requests."""
            html = (config.WEB / "tv" / "index.html").read_text(encoding="utf-8")
            brands = (config.WEB / "brands.js").read_text(encoding="utf-8")
            boot = json.dumps(app.status()).replace("</", "<\\/")
            head = '<link rel="preload" href="/tv/outfit.ttf" as="font" type="font/ttf" crossorigin>'
            html = html.replace('<script src="/brands.js"></script>',
                                f"{head}<script>{brands}</script><script>window.__BOOT={boot};</script>", 1)
            body = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        # ---- GET ----------------------------------------------------
        def do_GET(self):
            url = urlparse(self.path)
            if url.path in ("/tv/", "/tv/index.html"):
                return self._tv_home()
            if url.path == "/api/status":
                return self._json(app.status())
            if url.path == "/api/volwait":
                try:
                    seq = int(parse_qs(url.query).get("seq", ["-1"])[0])
                except ValueError:
                    seq = -1
                return self._json(app.tv.wait_volume(seq))
            if url.path == "/api/scan":
                return self._json({"found": network.scan(), "subnet": network.local_ip()})
            if url.path == "/api/events":
                return self._json(events.recent())
            if url.path.startswith("/api/"):
                return self._json({"error": "unknown endpoint"}, 404)
            return super().do_GET()

        # ---- POST ---------------------------------------------------
        def do_POST(self):
            try:
                length = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(length) or b"{}")
                if not isinstance(body, dict):
                    raise ValueError("expected a JSON object")
                route = ROUTES.get(urlparse(self.path).path)
                if not route:
                    return self._json({"error": "unknown endpoint"}, 404)
                result = route(app, body)
                return self._json(result if isinstance(result, dict) else {"ok": True})
            except Exception as e:  # noqa: BLE001 - report any failure to the page
                return self._json({"ok": False, "error": str(e)}, 400)

    return Handler


def _config(app, body):
    s = app.settings
    if body.get("mood") in config.MOODS:
        s.set(mood=body["mood"])
    if isinstance(body.get("own_home"), bool):
        s.set(own_home=body["own_home"])
    if isinstance(body.get("household"), str):
        s.set(household=body["household"].strip()[:60])
    for key in ("dock", "hidden"):
        if isinstance(body.get(key), list):
            s.set(**{key: [str(x) for x in body[key]]})


def _connect(app, body):
    ok = app.tv.connect(str(body["ip"]).strip())
    return {"ok": ok, **app.status()}


def _adblock(app, body):
    app.adblock.enabled = bool(body.get("enabled", True))
    app.settings.set(adblock_on=app.adblock.enabled)


def _saver(app, _body):
    app.saver_req = int(time.time() * 1000)


ROUTES = {
    "/api/connect": _connect,
    "/api/pair": lambda app, b: app.tv.pair(b["code"]),
    "/api/repin": lambda app, b: app.tv.request_pin(),
    "/api/key": lambda app, b: app.tv.key(str(b["key"])),
    "/api/volume": lambda app, b: app.tv.set_volume(b["value"]),
    "/api/source": lambda app, b: app.tv.source(b["sourceid"], b["sourcename"]),
    "/api/launch": lambda app, b: app.tv.launch(b),
    "/api/intent": lambda app, b: app.do_intent(str(b.get("text", ""))),
    "/api/home": lambda app, b: app.tv.open_home(),
    "/api/refresh": lambda app, b: app.tv.refresh(),
    "/api/wake": lambda app, b: app.tv.wake(),
    "/api/mac": lambda app, b: app.tv.store.update(mac=str(b["mac"])),
    "/api/ready": lambda app, b: app.tv.page_ready(),
    "/api/config": _config,
    "/api/adblock": _adblock,
    "/api/saver": _saver,
}


def serve(app, host="0.0.0.0"):
    server = ThreadingHTTPServer((host, app.port), make_handler(app))
    server.daemon_threads = True
    return server
