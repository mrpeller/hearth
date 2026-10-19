"""Unit tests for the pieces that don't need a TV:  python -m unittest discover tests"""
import json
import struct
import tempfile
import unittest
from pathlib import Path

from hearth import config, intent, protocol, wifi
from hearth.adblock import AdBlocker, blocked_answer, parse_question


class ProtocolTest(unittest.TestCase):
    # Values cross-checked against the stevene1919/hisense_vidaa reference implementation.
    MAC, TS = "aa:bb:cc:dd:ee:ff", 1792337281

    def test_client_id(self):
        self.assertEqual(protocol.client_id(self.MAC), "aa:bb:cc:dd:ee:ff$his$617E95_vidaacommon_001")

    def test_logins(self):
        self.assertEqual(protocol.login(self.TS, "modern"), ("his$6239759786160114921", "58F775BC0FD15CDD13F02130A1355CC1"))
        self.assertEqual(protocol.login(self.TS, "middle"), ("his$6239759786160114921", "211A5D64E7146EF4EEEBA0F07C0AAF6A"))
        self.assertEqual(protocol.login(self.TS, "remotenow"), ("his$1792337281", "211A5D64E7146EF4EEEBA0F07C0AAF6A"))
        self.assertEqual(protocol.login(self.TS, "legacy"), ("hisenseservice", "multimqttservice"))

    def test_no_wildcard_subscriptions(self):
        subs = protocol.subscriptions("abc")
        self.assertTrue(subs)
        self.assertFalse(any("#" in t or "+" in t for t in subs))


class IntentTest(unittest.TestCase):
    APPS = [{"name": n} for n in ["Netflix", "YouTube", "Prime Video", "DStv Now", "UEFA.tv", "Spotify : Music & Podcasts",
                                  "Kidoodle TV", "Haystack TV Local + World News", "Plex"]]
    SOURCES = [{"sourcename": s, "sourceid": s} for s in ["TV", "HDMI1", "HDMI2"]]

    def decide(self, text):
        d = intent.decide(text, self.APPS, self.SOURCES)
        return d and d["label"]

    def test_examples(self):
        self.assertEqual(self.decide("arsenal vs chelsea"), "DStv Now")
        self.assertEqual(self.decide("champions league final"), "UEFA.tv")
        self.assertEqual(self.decide("play some afrobeats"), "Spotify : Music & Podcasts")
        self.assertEqual(self.decide("open plex"), "Plex")
        self.assertEqual(self.decide("hdmi 2"), "HDMI2")
        self.assertEqual(self.decide("stranger things"), "Netflix")
        self.assertIsNone(self.decide(""))

    def test_find_app_by_prefix(self):
        self.assertEqual(intent.find_app(self.APPS, "Spotify")["name"], "Spotify : Music & Podcasts")


class WifiParseTest(unittest.TestCase):
    def test_system_profiler(self):
        out = """
          Current Network Information:
            Home 5G:
              Channel: 149 (5GHz, 80MHz)
              Security: WPA2 Personal
              Signal / Noise: -38 dBm / -95 dBm
          Other Local Wi-Fi Networks:
            Cafe:
              Channel: 6 (2GHz, 20MHz)
              Security: None
        awdl0:
"""
        current, nearby = wifi.parse_system_profiler(out)
        self.assertEqual(current, "Home 5G")
        by_name = {n["ssid"]: n for n in nearby}
        self.assertEqual(by_name["Home 5G"]["band"], "5 GHz")
        self.assertEqual(by_name["Home 5G"]["signal"], -38)
        self.assertEqual(by_name["Cafe"]["security"], "None")

    def test_nmcli(self):
        out = "*:Home\\:5G:WPA2:5180 MHz:82\n :Cafe::2437 MHz:40\n :::2412 MHz:10\n"
        current, nearby = wifi.parse_nmcli(out)
        self.assertEqual(current, "Home:5G")
        self.assertEqual({n["ssid"] for n in nearby}, {"Home:5G", "Cafe"})
        self.assertEqual(next(n for n in nearby if n["ssid"] == "Cafe")["band"], "2.4 GHz")


class AdBlockTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        (self.dir / "blocklist.txt").write_text("# list\ndoubleclick.net\nads.example.com\n")
        (self.dir / "allowlist.txt").write_text("ok.doubleclick.net\n")
        self.ab = AdBlocker(folder=self.dir)

    def test_matching(self):
        self.assertTrue(self.ab.is_blocked("doubleclick.net"))
        self.assertTrue(self.ab.is_blocked("stats.g.doubleclick.net"))
        self.assertTrue(self.ab.is_blocked("ADS.example.com."))
        self.assertFalse(self.ab.is_blocked("example.com"))
        self.assertFalse(self.ab.is_blocked("ok.doubleclick.net"))
        self.assertFalse(self.ab.is_blocked("netflix.com"))

    def test_dns_answer(self):
        question = b"".join(bytes([len(p)]) + p.encode() for p in "ads.example.com".split(".")) + b"\0" + struct.pack("!HH", 1, 1)
        query = struct.pack("!HHHHHH", 0x1234, 0x0100, 1, 0, 0, 0) + question
        name, qtype, end = parse_question(query)
        self.assertEqual((name, qtype), ("ads.example.com", 1))
        reply = blocked_answer(query, qtype, end)
        self.assertEqual(reply[:2], b"\x12\x34")                 # same transaction id
        self.assertEqual(struct.unpack("!H", reply[6:8])[0], 1)   # one answer
        self.assertEqual(reply[-4:], b"\0\0\0\0")                # 0.0.0.0


class SettingsTest(unittest.TestCase):
    def test_layers(self):
        d = Path(tempfile.mkdtemp())
        (d / "settings.json").write_text(json.dumps({"household": "The Smiths", "mood": "rest"}))
        s = config.Settings(d / "settings.json", d / "prefs.json")
        self.assertEqual(s.get("household"), "The Smiths")          # from settings.json
        self.assertEqual(s.get("http_port"), 8765)                  # default
        s.set(mood="hopeful")                                        # from the remote
        self.assertEqual(config.Settings(d / "settings.json", d / "prefs.json").get("mood"), "hopeful")

    def test_store_is_atomic_json(self):
        d = Path(tempfile.mkdtemp())
        store = config.JsonStore(d / "state.json")
        store.update(ip="10.0.0.5", token="x")
        store.pop("token")
        self.assertEqual(json.loads((d / "state.json").read_text()), {"ip": "10.0.0.5"})


if __name__ == "__main__":
    unittest.main()
