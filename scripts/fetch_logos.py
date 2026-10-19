#!/usr/bin/env python3
"""Download app logos into web/tv/logos/.

    python3 scripts/fetch_logos.py

Brand marks come from Simple Icons (CC0, https://simpleicons.org), coloured for each tile.
Apps without a Simple Icon use the app icon published on the service's own website.
Logos are trademarks of their owners and are used only to label each app's tile.
Apps whose logo is missing simply show their name.
"""
import re
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGOS = ROOT / "web" / "tv" / "logos"
UA = {"User-Agent": "Mozilla/5.0 (hearth-logos)"}
SIMPLE_ICONS = "https://cdn.jsdelivr.net/npm/simple-icons@13.21.0/icons/{}.svg"

# Simple Icons slug -> colour for the mark on its tile.
SIMPLE = {
    "netflix": "#E50914", "youtube": "#FF0000", "spotify": "#1ED760", "primevideo": "#ffffff", "dazn": "#ffffff",
    "plex": "#EBAF00", "mubi": "#ffffff", "nba": "#ffffff", "ufc": "#ffffff", "redbull": "#ffffff",
    "appletv": "#ffffff", "accuweather": "#ffffff", "triller": "#ffffff",
}
# File name used in web/brands.js -> the service's home page, where its app icon is listed.
WEBSITES = {
    "deezer.png": "https://www.deezer.com/", "iqiyi.png": "https://www.iq.com/", "dstv-now.png": "https://www.dstv.com/",
    "kidoodle-tv.svg": "https://www.kidoodle.tv/", "haystack.png": "https://www.haystack.tv/",
    "startimes-on.png": "https://www.startimestv.com/", "sportytv.png": "https://www.sporty.com/",
    "afrolandtv.png": "https://www.afrolandtv.com/", "mindset.webp": "https://www.mindset.africa/",
    "iwant.png": "https://www.iwanttfc.com/", "chaupaltv.ico": "https://www.chaupal.tv/",
    "toongoggles.png": "https://www.toongoggles.com/", "mbc-shahid.png": "https://shahid.mbc.net/",
    "vlogbox.png": "https://vlogbox.com/", "vidaa.png": "https://www.vidaa.com/",
}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
        return r.geturl(), r.read()


def image_ext(data):
    if b"<svg" in data[:500]:
        return ".svg"
    if data[:4] == b"\x89PNG":
        return ".png"
    if data[:2] == b"\xff\xd8":
        return ".jpg"
    if data[8:12] == b"WEBP":
        return ".webp"
    if data[:4] == b"\x00\x00\x01\x00":
        return ".ico"
    return None


def site_icon(home):
    """The largest icon a home page declares, falling back to /apple-touch-icon.png."""
    base, html = get(home)
    html = html.decode("utf-8", "ignore")
    candidates = []
    for tag in re.findall(r"<link[^>]+>", html, re.I):
        rel, href = re.search(r'rel=["\']([^"\']+)', tag, re.I), re.search(r'href=["\']([^"\']+)', tag, re.I)
        if rel and href and "icon" in rel.group(1).lower():
            size = re.search(r'sizes=["\'](\d+)', tag)
            score = int(size.group(1)) if size else (180 if "apple" in rel.group(1).lower() else 32)
            candidates.append((score, urllib.parse.urljoin(base, href.group(1))))
    candidates.sort(reverse=True)
    candidates.append((0, urllib.parse.urljoin(base, "/apple-touch-icon.png")))
    for _, url in candidates:
        try:
            _, data = get(url)
        except OSError:
            continue
        ext = image_ext(data)
        if ext and len(data) > 300:
            return ext, data
    return None


def main():
    LOGOS.mkdir(parents=True, exist_ok=True)
    for slug, colour in SIMPLE.items():
        try:
            _, svg = get(SIMPLE_ICONS.format(slug))
        except OSError as e:
            print(f"  {slug}: {e}")
            continue
        svg = re.sub(r"<svg ", f'<svg fill="{colour}" ', svg.decode(), count=1)
        (LOGOS / f"si-{slug}.svg").write_text(svg, encoding="utf-8")
        print(f"si-{slug}.svg")
    for name, home in WEBSITES.items():
        try:
            found = site_icon(home)
        except OSError as e:
            found = None
            print(f"  {name}: {e}")
        # Browsers recognise PNG/JPEG/WebP/ICO by content, but an SVG must keep its .svg name.
        if found and (found[0] == ".svg") == name.endswith(".svg"):
            (LOGOS / name).write_bytes(found[1])
            print(name)
        else:
            print(f"  {name}: no icon found (the tile will show the app's name)")


if __name__ == "__main__":
    main()
