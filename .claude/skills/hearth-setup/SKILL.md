---
name: hearth-setup
description: Set up Hearth (this repo) for someone's Hisense VIDAA TV on Windows, macOS or Linux - check Python/TLS, start the bridge, find and pair the TV, add the VIDAA certificate, personalise settings.json, install the background service, auto-updates and optionally the ad blocker. Use when the user asks to set up, install, pair, configure or troubleshoot Hearth or their Hisense/VIDAA TV home screen.
---

# Setting up Hearth

Hearth is a Python bridge (`hearth/`) plus two web pages (`web/`): a phone remote and a TV home
screen. Work through these steps in order, checking each before moving on. Read README.md for detail.

## 1. Python with TLS 1.3, and Git

The TV only speaks TLS 1.3. Check: `python3 -c "import ssl; print(ssl.HAS_TLSv1_3)"` (Windows: `py -3 -c ...`).
- Windows 10/11: Python from python.org (with "Add to PATH") and Git for Windows. Start with `start.cmd`.
- macOS: `start.sh` uses `uv` or Homebrew Python (the built-in one is too old).
- Linux / Raspberry Pi OS: system Python is fine. Start with `start.sh`.
Ask before installing anything system-wide. Git is needed for auto-updates (`hearth/updater.py`).

## 2. The VIDAA client certificate

Check `certs/` for a `.p12` or `*_cert.pem` + `*_key.pem`. If missing, the user needs the
"VIDAA Smart TV" Android app (`com.universal.remote.multi`) as an .apk/.apkm. Ask them to download
it from a source they trust, or ask permission before downloading it yourself. Then run
`.venv/bin/python scripts/extract_cert.py <file>` (Windows: `.venv\Scripts\python ...`; run the start
script once first so `.venv` exists). If another machine already has Hearth, copying its `certs/` folder
(and `data/state.json`, to skip pairing) is enough. Never commit, upload or share anything in `certs/`.

## 3. Start the bridge

Run `./start.sh` (Windows: `start.cmd`) in the background; it keeps running and restarts itself
after updates (exit code 3). It prints the phone remote address.
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

- macOS/Linux: `./scripts/install_service.sh` (LaunchAgent / systemd).
- Windows: `scripts\install_service.ps1` (asks for admin): a hidden scheduled task at sign-in, firewall rules
  for TCP 8765 and UDP 53, Wi-Fi set to Private, and with `-KeepAwake` no sleep on AC power or lid close.
  Ask the user before using `-KeepAwake`, since it changes the laptop's power settings.
Explain that the TV only shows Hearth while this machine is on, awake and at home; a Raspberry Pi is
the usual always-on choice. Updates arrive automatically from the GitHub repo every 5 minutes.

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
