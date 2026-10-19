---
name: hearth-setup
description: Set up Hearth (this repo) for someone's Hisense VIDAA TV - check Python/TLS, start the bridge, find and pair the TV, add the VIDAA certificate, personalise settings.json, install the background service and optionally the ad blocker. Use when the user asks to set up, install, pair, configure or troubleshoot Hearth or their Hisense/VIDAA TV home screen.
---

# Setting up Hearth

Hearth is a Python bridge (`hearth/`) plus two web pages (`web/`): a phone remote and a TV home
screen. Work through these steps in order, checking each before moving on. Read README.md for detail.

## 1. Python with TLS 1.3

The TV only speaks TLS 1.3. Check: `python3 -c "import ssl; print(ssl.HAS_TLSv1_3)"`.
`start.sh` finds a suitable Python itself, or uses `uv` if it's installed. If neither exists,
ask the user to install uv or Homebrew Python; don't install system software without asking.

## 2. The VIDAA client certificate

Check `certs/` for a `.p12` or `*_cert.pem` + `*_key.pem`. If missing, the user needs the
"VIDAA Smart TV" Android app (`com.universal.remote.multi`) as an .apk/.apkm. Ask them to download
it from a source they trust, or ask permission before downloading it yourself. Then run
`python3 scripts/extract_cert.py <file>`. Never commit, upload or share anything in `certs/`.

## 3. Start the bridge

Run `./start.sh` in the background (it keeps running). It prints the phone remote address.
Confirm with `curl -s localhost:8765/api/status`.

## 4. Find and pair the TV

- Find it: `curl -s localhost:8765/api/scan` (addresses with port 36669 open). The TV must be on.
- Connect: `curl -s -X POST localhost:8765/api/connect -H 'Content-Type: application/json' -d '{"ip":"<tv-ip>"}'`.
- The TV shows a 4-digit PIN. **Ask the user to read it to you** (you can't see the screen), then
  `POST /api/pair {"code":"1234"}`. Codes expire within a minute or two; `POST /api/repin` shows a new one.
- Check `/api/status`: `connected` and `paired` should both be true, and `apps` should list the TV's apps.

## 5. Personalise

Copy `settings.example.json` to `settings.json` and fill in what the user wants: household name,
Quick access apps (`dock`), apps to hide, websites (`sites`, with an icon in `web/tv/sites/`),
verse mood. App names must match the TV's (see `apps` in `/api/status`; a prefix is enough).
Optionally run `scripts/fetch_photos.py` and `scripts/fetch_logos.py`.
Open the home screen on the TV with `POST /api/home` and ask the user how it looks.

## 6. Keep it running

`./scripts/install_service.sh` (LaunchAgent on macOS, systemd on Linux). Explain that the TV only
shows Hearth while this machine is on and at home; a Raspberry Pi is the usual always-on choice.

## 7. Ad blocker (optional, ask first)

It blocks ad domains for the whole TV once the TV's DNS points at this machine. Warn the user
that the TV loses internet whenever this machine is off, unless they also set a fallback DNS.
They change the TV's DNS themselves in its network settings. Verify via `adblock.clients` in `/api/status`.

## Things you can't do

You can't see the TV screen: ask the user what it shows before pressing keys in VIDAA's own
menus, one key at a time. VIDAA's launcher can't be removed and its volume bar can't be hidden;
don't attempt firmware changes or workarounds beyond the documented remote-control protocol.

## Troubleshooting

`GET /api/events` shows recent TV events. `HEARTH_DEBUG=1 ./start.sh` logs them.
`python -m unittest discover tests` runs the tests.
