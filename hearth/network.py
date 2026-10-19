"""Finding the TV on the local network."""
import concurrent.futures as cf
import email.utils
import os
import re
import socket
import subprocess
import time
import urllib.request

TV_PORT = 36669  # the TV's remote-control (MQTT) port


def local_ip():
    """This machine's address on the home network."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))  # no packet is sent; this only picks the outgoing interface
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def port_open(ip, port=TV_PORT, timeout=1.5):
    s = socket.socket()
    s.settimeout(timeout)
    try:
        return s.connect_ex((ip, port)) == 0
    except OSError:
        return False
    finally:
        s.close()


def scan():
    """Addresses on this /24 network that answer on the TV's remote-control port."""
    base = local_ip().rsplit(".", 1)[0]
    ips = [f"{base}.{i}" for i in range(1, 255)]
    with cf.ThreadPoolExecutor(64) as ex:
        return [ip for ip, ok in zip(ips, ex.map(lambda ip: port_open(ip, timeout=0.6), ips)) if ok]


def mac_for(ip):
    """The TV's hardware address from the ARP table (used for Wake-on-LAN and the client id)."""
    try:
        with open("/proc/net/arp") as f:
            for line in f:
                parts = line.split()
                if parts and parts[0] == ip and parts[3] != "00:00:00:00:00:00":
                    return parts[3].lower()
    except OSError:
        pass
    try:
        out = subprocess.run(["arp", "-n", ip], capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return ""
    m = re.search(r"((?:[0-9a-fA-F]{1,2}:){5}[0-9a-fA-F]{1,2})", out)
    return ":".join(p.zfill(2) for p in m.group(1).lower().split(":")) if m else ""


def tv_clock(ip):
    """The TV's own time, from its UPnP server's Date header; login credentials depend on it."""
    for port in (38400, 18400):
        try:
            with urllib.request.urlopen(f"http://{ip}:{port}/MediaServer/rendererdevicedesc.xml", timeout=1.5) as r:
                date = r.headers.get("Date")
                if date:
                    return int(email.utils.parsedate_to_datetime(date).timestamp())
        except (OSError, ValueError):
            pass
    return int(time.time())


def wake_on_lan(mac):
    raw = bytes.fromhex(mac.replace(":", "").replace("-", ""))
    if len(raw) != 6:
        raise ValueError("set the TV's MAC address first")
    packet = b"\xff" * 6 + raw * 16
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    try:
        for port in (7, 9):
            s.sendto(packet, ("255.255.255.255", port))
    finally:
        s.close()


def is_linux():
    return os.uname().sysname == "Linux"
