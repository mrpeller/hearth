#!/usr/bin/env python3
"""Download the background photos (and pre-blurred copies for the glass panels).

    python3 scripts/fetch_photos.py              # the default set
    python3 scripts/fetch_photos.py 1015 1018    # your own picks from https://picsum.photos/images

Photos come from Unsplash via picsum.photos and are free to use under the Unsplash licence.
The photographer is credited on screen.
"""
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BG = ROOT / "web" / "tv" / "bg"
DEFAULT_IDS = [1015, 1018, 1019, 1043, 1067, 857, 866, 1016]
UA = {"User-Agent": "hearth-photos"}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read()


def main():
    ids = [int(x) for x in sys.argv[1:]] or DEFAULT_IDS
    (BG / "blur").mkdir(parents=True, exist_ok=True)
    photos = []
    for i in ids:
        info = json.loads(get(f"https://picsum.photos/id/{i}/info"))
        sharp, blur = get(f"https://picsum.photos/id/{i}/1920/1080.jpg"), get(f"https://picsum.photos/id/{i}/1280/720.jpg?blur=10")
        if sharp[:2] != b"\xff\xd8" or blur[:2] != b"\xff\xd8":
            print(f"Skipping {i}: not a JPEG")
            continue
        (BG / f"{i}.jpg").write_bytes(sharp)
        (BG / "blur" / f"{i}.jpg").write_bytes(blur)
        photos.append({"src": f"/tv/bg/{i}.jpg", "blur": f"/tv/bg/blur/{i}.jpg", "author": info["author"], "source": info["url"]})
        print(f"{i}: {info['author']}")
    (BG / "photos.json").write_text(json.dumps(photos, indent=1), encoding="utf-8")
    print(f"Saved {len(photos)} photos.")


if __name__ == "__main__":
    main()
