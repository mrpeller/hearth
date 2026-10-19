"""The VIDAA app's client certificate, which newer TVs require before they'll talk.

Put the .p12 from the VIDAA app (or a cert/key pair) in certs/. A .p12 is converted
to PEM files next to it on first use. scripts/extract_cert.py pulls it out of the app.
"""
import subprocess
from pathlib import Path

from .config import CERTS

# Passwords the VIDAA/RemoteNOW app keystores have used.
P12_PASSWORDS = ("186e990688070325a1c4b0ce275d2388", "", "remote", "hisense", "123456")

CERT_PAIRS = (
    ("El_cert.pem", "El_key.pem"),
    ("client_mobile_android_cert.pem", "client_mobile_android_key.pem"),
    ("vidaa_2024_cert.pem", "vidaa_2024_key.pem"),
    ("vidaa_client_v02.pem", "vidaa_client_v02.key"),
    ("vidaa_client_v01.pem", "vidaa_client_v01.key"),
    ("vidaa_client.pem", "vidaa_client.key"),
    ("rcm_certchain_pem.cer", "rcm_pem_privkey.pkcs8"),
    ("hisense.crt", "hisense.key"),
    ("cert.pem", "key.pem"),
)


def _with_cryptography(p12, cert_out, key_out):
    try:
        from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat, pkcs12
    except ImportError:
        return False
    data = Path(p12).read_bytes()
    for pw in P12_PASSWORDS:
        try:
            key, cert, _extra = pkcs12.load_key_and_certificates(data, pw.encode() or None)
        except ValueError:
            continue
        if key and cert:
            Path(cert_out).write_bytes(cert.public_bytes(Encoding.PEM))
            Path(key_out).write_bytes(key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()))
            return True
    return False


def p12_to_pem(p12, cert_out, key_out):
    """Convert a .p12 to PEM files, trying the known passwords.

    Uses the cryptography package (installed with Hearth, works everywhere), falling back to
    the openssl tool (with OpenSSL 3's -legacy for the keystore's old ciphers).
    """
    if _with_cryptography(p12, cert_out, key_out):
        return True
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    for pw in P12_PASSWORDS:
        for legacy in ([], ["-legacy"]):
            base = ["openssl", "pkcs12", *legacy, "-in", str(p12), "-passin", f"pass:{pw}"]
            try:
                a = subprocess.run(base + ["-clcerts", "-nokeys", "-out", str(cert_out)], capture_output=True, timeout=20, creationflags=flags)
                b = subprocess.run(base + ["-nocerts", "-nodes", "-out", str(key_out)], capture_output=True, timeout=20, creationflags=flags)
            except (OSError, subprocess.SubprocessError):
                return False
            if a.returncode == 0 and b.returncode == 0 and Path(cert_out).exists() and Path(cert_out).stat().st_size > 0:
                return True
    return False


def find(cert_dir=CERTS):
    """(certfile, keyfile) as strings, or (None, None) if there is no usable certificate."""
    cert_dir = Path(cert_dir)
    if not cert_dir.is_dir():
        return None, None
    for p12 in sorted(cert_dir.glob("*.p12")) + sorted(cert_dir.glob("*.pfx")):
        cert, key = p12.with_name(p12.stem + "_cert.pem"), p12.with_name(p12.stem + "_key.pem")
        if not (cert.exists() and key.exists()):
            p12_to_pem(p12, cert, key)
    for c, k in CERT_PAIRS:
        if (cert_dir / c).exists() and (cert_dir / k).exists():
            return str(cert_dir / c), str(cert_dir / k)
    for cert in sorted(cert_dir.glob("*_cert.pem")):
        key = cert.with_name(cert.name.replace("_cert.pem", "_key.pem"))
        if key.exists():
            return str(cert), str(key)
    return None, None
