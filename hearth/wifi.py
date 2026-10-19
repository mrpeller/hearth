"""Nearby Wi-Fi networks, for the Wi-Fi menu on the TV.

The TV won't share its own scan, so the machine running Hearth scans instead (it's in
the same home). macOS uses system_profiler; Linux uses NetworkManager's nmcli.
"""
import subprocess
import threading
import time

from . import network


def _run(cmd, timeout=30):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def parse_system_profiler(out):
    """(current network, [nearby networks]) from `system_profiler SPAirPortDataType`."""
    current, nearby, section, entry = "", {}, None, None
    for raw in out.splitlines():
        line = raw.strip()
        indent = len(raw) - len(raw.lstrip())
        if line == "Current Network Information:":
            section = "current" if not current else None
            continue
        if line == "Other Local Wi-Fi Networks:":
            section = "other"
            continue
        if line.startswith(("awdl", "Software Versions")):
            section = None
        if not section or not line:
            continue
        if line.endswith(":") and indent <= 14:
            name = line[:-1]
            if section == "current":
                current = name
            entry = nearby.setdefault(name, {"ssid": name})
            continue
        if entry is not None and ":" in line:
            k, v = (x.strip() for x in line.split(":", 1))
            if k == "Channel":
                entry["band"] = "5 GHz" if "5GHz" in v else "6 GHz" if "6GHz" in v else "2.4 GHz"
            elif k == "Security":
                entry["security"] = v
            elif k == "Signal / Noise":
                try:
                    entry["signal"] = int(v.split()[0])
                except ValueError:
                    pass
    return current, list(nearby.values())


def parse_nmcli(out):
    """(current, nearby) from `nmcli -t -f IN-USE,SSID,SECURITY,FREQ,SIGNAL device wifi list`."""
    current, nearby = "", {}
    for line in out.splitlines():
        parts = line.replace("\\:", "\0").split(":")
        if len(parts) < 5:
            continue
        in_use, ssid, security, freq, signal = (p.replace("\0", ":") for p in parts[:5])
        if not ssid:
            continue
        mhz = int("".join(ch for ch in freq if ch.isdigit()) or 0)
        band = "6 GHz" if mhz >= 5925 else "5 GHz" if mhz >= 4900 else "2.4 GHz"
        entry = nearby.setdefault(ssid, {"ssid": ssid, "band": band, "security": security or "None"})
        if in_use.strip() == "*":
            current = ssid
            entry["signal"] = int(signal or 0)
    return current, list(nearby.values())


def scan():
    """{"ssid": current, "nearby": [...]} for this machine's Wi-Fi."""
    if network.is_linux():
        current, nearby = parse_nmcli(_run(["nmcli", "-t", "-f", "IN-USE,SSID,SECURITY,FREQ,SIGNAL", "device", "wifi", "list"]))
        saved = {line.split(":")[0] for line in _run(["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show"]).splitlines()
                 if line.endswith(":802-11-wireless")}
    else:
        current, nearby = parse_system_profiler(_run(["system_profiler", "SPAirPortDataType"]))
        lines = _run(["networksetup", "-listpreferredwirelessnetworks", "en0"]).splitlines()[1:]
        saved = {x.strip() for x in lines if x.strip()}
    for n in nearby:
        n["known"] = n["ssid"] in saved
    return {"ssid": current, "nearby": nearby, "scanned": int(time.time())}


class Watcher:
    """Rescans in the background every 30 seconds (scans take a few seconds)."""

    def __init__(self, interval=30):
        self.interval = interval
        self.latest = {"ssid": "", "nearby": [], "scanned": 0}

    def start(self):
        threading.Thread(target=self._loop, daemon=True).start()
        return self

    def _loop(self):
        while True:
            self.latest = scan()
            time.sleep(self.interval)
