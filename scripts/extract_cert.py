#!/usr/bin/env python3
"""Copy the VIDAA app's client certificate into certs/.

Newer Hisense VIDAA TVs only accept remote-control connections that present the client
certificate shipped inside the official "VIDAA Smart TV" Android app
(package com.universal.remote.multi). Get that app's .apk / .apkm / .xapk yourself, then:

    python3 scripts/extract_cert.py path/to/vidaa-app.apkm

The certificate belongs to Hisense: keep it on your own machine and don't publish it.
"""
import io
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from hearth.certs import p12_to_pem  # noqa: E402

CERTS = ROOT / "certs"
NAMES = ("client_mobile_android.p12", "El.p12", "rcamobile.p12")


def find_p12(zf, depth=0):
    """Search an APK (and APKs nested inside .apkm/.xapk bundles) for the keystore."""
    for info in zf.infolist():
        if info.filename.rsplit("/", 1)[-1] in NAMES:
            return info.filename.rsplit("/", 1)[-1], zf.read(info)
    if depth < 2:
        for info in zf.infolist():
            if info.filename.endswith(".apk"):
                with zipfile.ZipFile(io.BytesIO(zf.read(info))) as inner:
                    found = find_p12(inner, depth + 1)
                    if found:
                        return found
    return None


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    path = Path(sys.argv[1]).expanduser()
    try:
        with zipfile.ZipFile(path) as zf:
            found = find_p12(zf)
    except (OSError, zipfile.BadZipFile) as e:
        sys.exit(f"Couldn't open {path}: {e}")
    if not found:
        sys.exit("No VIDAA client certificate found in that file. Is it the VIDAA Smart TV app?")
    name, data = found
    CERTS.mkdir(exist_ok=True)
    p12 = CERTS / name
    p12.write_bytes(data)
    cert, key = p12.with_name(p12.stem + "_cert.pem"), p12.with_name(p12.stem + "_key.pem")
    if not p12_to_pem(p12, cert, key):
        sys.exit(f"Saved {p12.name}, but couldn't convert it (is the openssl tool installed?).")
    print(f"Saved the certificate to certs/{cert.name} and certs/{key.name}")


if __name__ == "__main__":
    main()
