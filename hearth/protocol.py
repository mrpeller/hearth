"""The VIDAA remote-control protocol: login credentials and MQTT topic names.

Newer VIDAA firmware runs an MQTT broker on port 36669 over TLS 1.3 and expects:
  * a client certificate from the official VIDAA phone app (see scripts/extract_cert.py),
  * a username/password derived from the TV's clock,
  * a 4-digit PIN shown on the TV, after which the TV issues an access token
    (used as the password from then on) and a longer-lived refresh token.

The derivation below follows the open-source stevene1919/hisense_vidaa project.
"""
import hashlib

MODERN_SALT = "h!i@s#$v%i^d&a*a"
STANDARD_SALT = "h*i&s%e!r^v0i1c9"
CLIENT_ID_PATTERN = "38D65DC30F45109A369A86FCE866A85B"
XOR_MASK = 6239759785777146216

# Login styles, tried in order until the TV accepts one.
PROFILES = ("modern", "middle", "remotenow", "legacy")


def client_id(mac):
    h = hashlib.md5(f"{CLIENT_ID_PATTERN}${mac}".encode()).hexdigest().upper()
    return f"{mac}$his${h[:6]}_vidaacommon_001"


def login(timestamp, profile):
    """(username, password) for the first, PIN-less connection."""
    if profile == "legacy":
        return "hisenseservice", "multimqttservice"
    salt = STANDARD_SALT if profile in ("middle", "remotenow") else MODERN_SALT
    user = f"his${timestamp}" if profile == "remotenow" else f"his${timestamp ^ XOR_MASK}"
    digit = sum(int(c) for c in str(timestamp)) % 10
    h3 = hashlib.md5(f"his{digit}{salt}".encode()).hexdigest().upper()
    return user, hashlib.md5(f"{timestamp}${h3[:6]}".encode()).hexdigest().upper()


def tv_topic(cid, service, kind, action):
    """A topic the TV listens on, e.g. tv_topic(cid, "ui_service", "actions", "launchapp")."""
    return f"/remoteapp/tv/{service}/{cid}/{kind}/{action}"


def subscriptions(cid):
    """Every topic we listen on. The TV refuses wildcards, so each is spelled out."""
    mine = f"/remoteapp/mobile/{cid}/"
    broadcast = "/remoteapp/mobile/broadcast/"
    return [mine + t for t in (
        "ui_service/data/authentication", "ui_service/data/authenticationcode",
        "ui_service/data/authenticationcodeclose", "ui_service/data/authenticationcodetoast",
        "ui_service/data/vidaa_app_connect", "platform_service/data/tokenissuance",
        "ui_service/data/sourcelist", "ui_service/data/applist", "ui_service/data/gettvstate",
        "ui_service/data/state", "platform_service/data/getvolume",
        "platform_service/data/getdeviceinfo", "platform_service/data/gettvinfo",
    )] + [broadcast + t for t in (
        "ui_service/state", "platform_service/actions/volumechange", "ui_service/volume",
        "platform_service/actions/tvsleep",
    )]
