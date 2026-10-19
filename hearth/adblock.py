"""Network-wide ad blocker: a small DNS server.

Point the TV's DNS at the machine running Hearth and every app and site on the TV stops
reaching the ad and tracker domains in adblock/. Everything else is forwarded upstream.
"""
import collections
import socket
import struct
import threading
import time

from .config import ADBLOCK


def load_domains(*names, folder=ADBLOCK):
    domains = set()
    for name in names:
        try:
            with open(folder / name, encoding="utf-8") as f:
                domains.update(line.strip().lower() for line in f if line.strip() and not line.startswith("#"))
        except OSError:
            pass
    return domains


def parse_question(packet):
    """(name, qtype, end offset) of a DNS query's first question."""
    i, labels = 12, []
    while packet[i] != 0:
        n = packet[i]
        labels.append(packet[i + 1:i + 1 + n].decode("ascii", "ignore"))
        i += 1 + n
    i += 1
    qtype = struct.unpack("!H", packet[i:i + 2])[0]
    return ".".join(labels).lower(), qtype, i + 4


def blocked_answer(packet, qtype, end):
    """A reply saying the domain is 0.0.0.0 (for A queries) or has no records (anything else)."""
    tid, flags = struct.unpack("!HH", packet[:4])
    rd = flags & 0x0100
    question = packet[12:end]
    if qtype == 1:
        header = struct.pack("!HHHHHH", tid, 0x8080 | rd, 1, 1, 0, 0)
        answer = b"\xc0\x0c" + struct.pack("!HHIH", 1, 1, 300, 4) + b"\x00\x00\x00\x00"
        return header + question + answer
    return struct.pack("!HHHHHH", tid, 0x8080 | rd, 1, 0, 0, 0) + question


class AdBlocker:
    def __init__(self, port=53, upstreams=("1.1.1.1", "8.8.8.8"), enabled=True, folder=ADBLOCK):
        self.port = port
        self.upstreams = list(upstreams)
        self.enabled = enabled
        self.block = load_domains("blocklist.txt", "base.txt", folder=folder)
        self.allow = load_domains("allowlist.txt", folder=folder)
        self.running = False
        self.error = ""
        self.total = 0
        self.blocked = 0
        self.recent = collections.deque(maxlen=40)
        self.clients = set()

    def is_blocked(self, name):
        """True if the name or any parent domain is listed (and not allow-listed)."""
        parts = name.lower().strip(".").split(".")
        for i in range(len(parts) - 1):
            domain = ".".join(parts[i:])
            if domain in self.allow:
                return False
            if domain in self.block:
                return True
        return False

    def _forward(self, packet):
        for upstream in self.upstreams:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(2.5)
            try:
                s.sendto(packet, (upstream, 53))
                return s.recvfrom(4096)[0]
            except OSError:
                continue
            finally:
                s.close()
        return None

    def _handle(self, sock, packet, addr):
        try:
            name, qtype, end = parse_question(packet)
        except (IndexError, struct.error):
            return
        self.total += 1
        self.clients.add(addr[0])
        if self.enabled and self.is_blocked(name):
            self.blocked += 1
            self.recent.appendleft({"domain": name, "client": addr[0], "t": int(time.time())})
            sock.sendto(blocked_answer(packet, qtype, end), addr)
            return
        reply = self._forward(packet)
        if reply:
            try:
                sock.sendto(reply, addr)
            except OSError:
                pass

    def _serve(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.bind(("0.0.0.0", self.port))
        except OSError as e:
            self.error = f"Couldn't start the ad blocker on port {self.port}: {e}"
            print(self.error, flush=True)
            return
        self.running = True
        print(f"Ad blocker listening on port {self.port} ({len(self.block):,} domains)", flush=True)
        while True:
            try:
                packet, addr = sock.recvfrom(4096)
            except OSError:   # e.g. Windows' WSAECONNRESET after an unreachable client; not fatal
                continue
            threading.Thread(target=self._handle, args=(sock, packet, addr), daemon=True).start()

    def start(self):
        threading.Thread(target=self._serve, daemon=True).start()
        return self

    def status(self):
        return {
            "running": self.running, "enabled": self.enabled, "error": self.error,
            "domains": len(self.block), "total": self.total, "blocked": self.blocked,
            "recent": list(self.recent)[:15], "clients": sorted(self.clients),
        }
