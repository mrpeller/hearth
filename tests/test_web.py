"""The web server, with the TV, ad blocker and Wi-Fi scanner switched off."""
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from hearth import config
from hearth.app import App
from hearth.web import serve


class WebTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        d = Path(tempfile.mkdtemp())
        (d / "settings.json").write_text(json.dumps({"household": "Test House", "http_port": 0, "dock": ["Netflix"]}))
        settings = config.Settings(d / "settings.json", d / "prefs.json")
        state = config.JsonStore(d / "state.json")
        state.update(apps_cache=[{"appId": "1", "name": "Netflix", "url": "netflix"}])
        cls.app = App(settings=settings, state=state, cert_dir=d / "certs", start_services=False)
        cls.server = serve(cls.app, host="127.0.0.1")
        cls.app.port = cls.server.server_address[1]
        cls.base = f"http://127.0.0.1:{cls.app.port}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def get(self, path):
        with urllib.request.urlopen(self.base + path, timeout=5) as r:
            return r.status, r.headers, r.read()

    def post(self, path, body):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_status(self):
        status, _, body = self.get("/api/status")
        data = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(data["household"], "Test House")
        self.assertFalse(data["has_cert"])
        self.assertIn("Apple TV", [a["name"] for a in data["apps"]])   # extra app added
        self.assertEqual(data["dock"], ["Netflix"])

    def test_tv_home_has_data_built_in(self):
        status, headers, body = self.get("/tv/")
        html = body.decode()
        self.assertEqual(status, 200)
        self.assertIn("window.__BOOT=", html)
        self.assertIn("function tileHTML", html)
        self.assertNotIn('<script src="/brands.js">', html)
        self.assertEqual(headers["Cache-Control"], "no-cache")

    def test_static_files(self):
        status, _, body = self.get("/")
        self.assertEqual(status, 200)
        self.assertIn(b"<html", body)
        status, headers, _ = self.get("/tv/outfit.ttf")
        self.assertEqual(headers["Cache-Control"], "public, max-age=604800")

    def test_config_saved(self):
        self.assertEqual(self.post("/api/config", {"mood": "rest", "own_home": False})[0], 200)
        self.assertEqual(self.app.settings.get("mood"), "rest")
        self.assertFalse(self.app.settings.get("own_home"))
        self.post("/api/config", {"mood": "not-a-mood"})
        self.assertEqual(self.app.settings.get("mood"), "rest")

    def test_errors(self):
        self.assertEqual(self.post("/api/nope", {})[0], 404)
        code, body = self.post("/api/key", {"key": "KEY_OK"})   # no TV connected
        self.assertEqual(code, 400)
        self.assertIn("not connected", body["error"])
        with self.assertRaises(urllib.error.HTTPError):
            self.get("/api/nope")

    def test_volume_long_poll_returns(self):
        status, _, body = self.get("/api/volwait?seq=-1")
        self.assertEqual(json.loads(body)["seq"], 0)


if __name__ == "__main__":
    unittest.main()
