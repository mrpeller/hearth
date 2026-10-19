# Hearth

**A calm, content-first home screen and phone remote for Hisense VIDAA TVs.**

VIDAA's own launcher is busy, slow and full of promoted apps. Hearth replaces it with a
dark, Apple TV–style home screen that you design, and gives you a proper remote on your phone.
It runs on a computer in your home (Windows, Mac, Raspberry Pi or any Linux box) and talks to the TV
over Wi-Fi. Nothing is installed on the TV and nothing on it is changed.

## What you get

**On the TV**
- A clean home screen over rotating photos and frosted glass, with a clock and a greeting for your household.
- **Quick access** row for your favourite apps, **Recent sites** for websites you open on the TV, and every other app below. Preinstalled clutter can be hidden.
- Your own **Settings** menu (Wi-Fi, volume, brightness, contrast, inputs) and **Inputs** menu, moved with left/right like the pills on an Apple TV.
- A **volume display** that appears when the volume changes.
- A **screensaver** with Bible verses (KJV) on frosted glass, chosen by mood or time of day.
- **Hearth stays on screen.** Whenever VIDAA's launcher appears (the Home button, switching on), Hearth swaps it out within about a second.

**On your phone**
- A remote with a touch pad, volume, inputs, a keyboard shortcut layer, and "What do you want to watch?" (type "the Arsenal match" or "something funny" and it opens the right app).
- Edit which apps are in Quick access and which are hidden, pick the verse mood, and switch features on and off.

**On your network**
- An optional **ad blocker** (a small DNS server) that stops every app and site on the TV from reaching ~45,000 ad and tracker domains.

## What it can't do

These are limits of VIDAA, not bugs:
- VIDAA's launcher can't be uninstalled or replaced as the default. Hearth reopens itself whenever the launcher shows, so you'll see it for about a second after Home or power-on.
- VIDAA's own volume bar can't be turned off on most models, so it shows alongside Hearth's.
- The TV doesn't let apps join Wi-Fi networks. The Wi-Fi menu lists networks and hands off to the TV's settings to join.
- Hearth only works while the computer running it is on, awake and at home. Use a Raspberry Pi or a machine that stays plugged in (see below).

## Requirements

- A Hisense TV running **VIDAA** (tested on VIDAA 9, model 50Q61QAVT), on the same network as:
- A computer that stays at home and on: **Windows 10/11**, **macOS** or **Linux** (a Raspberry Pi 4/5 is ideal).
- **Python 3.10+ with TLS 1.3** (the TV refuses older TLS):
  - Windows: install from [python.org](https://www.python.org/downloads/windows/) and tick *Add python.exe to PATH*.
  - macOS: the built-in Python is too old; `start.sh` uses [uv](https://docs.astral.sh/uv/) or Homebrew Python.
  - Raspberry Pi OS / Linux: the system Python is fine.
- **Git** (Windows: [Git for Windows](https://git-scm.com/download/win)), so Hearth can update itself.
- The **VIDAA Smart TV** Android app's certificate (step 2).

## Setup

Commands are shown for macOS/Linux, with the Windows version underneath where it differs.

### 1. Get Hearth

```bash
git clone https://github.com/mrpeller/hearth.git
cd hearth
```

Cloning a private repo on Windows opens a GitHub sign-in window once; Git remembers it, which
is what lets Hearth pull updates later.

### 2. Add the VIDAA app certificate

Newer VIDAA TVs only accept remote-control connections that present the client certificate
built into the official **VIDAA Smart TV** app (`com.universal.remote.multi`). Download that
app's `.apk`/`.apkm` from a source you trust, start Hearth once (step 3) so its Python is set up, then:

```bash
.venv/bin/python scripts/extract_cert.py ~/Downloads/vidaa-smart-tv.apkm
```
```bat
.venv\Scripts\python scripts\extract_cert.py %USERPROFILE%\Downloads\vidaa-smart-tv.apkm
```

This writes the certificate into `certs/`. Already have it on another machine? Just copy the
`certs` folder across. It belongs to Hisense: keep it on your machines and never commit or share
it (`certs/` is in `.gitignore`).

### 3. Start it and pair the TV

```bash
./start.sh
```
On Windows, double-click **`start.cmd`**.

It prints two addresses. Open the **phone remote** (`http://<computer-ip>:8765`) on your phone,
tap **Scan WiFi**, pick your TV and press **Connect**. The TV shows a 4-digit PIN; type it in.
After that Hearth reconnects by itself, even after restarts (the login token renews automatically).
Moving Hearth to another computer? Copy `data/state.json` across and you won't need a new PIN.

Press the remote's **⌂** button to open Hearth on the TV.

### 4. Make it yours

Copy `settings.example.json` to `settings.json` and edit it:

| Key | What it does |
|---|---|
| `household` | Name in the greeting: "Good evening, The Smiths" |
| `dock` | Quick access apps, by name (a prefix is enough: `"Spotify"`) |
| `hidden` | Apps kept off the home screen |
| `sites` | Websites for Recent sites: `name`, `url`, `icon` (put the image in `web/tv/sites/`), `bg`, `fit` (`contain`/`cover`), `glow`, `sub` |
| `mood` | Screensaver verses: `auto`, `peaceful`, `strong`, `grateful`, `comfort`, `hopeful`, `rest` |
| `own_home` | `false` to let VIDAA's launcher stay when it opens |
| `auto_update`, `update_minutes` | Pull new versions from GitHub automatically (default: on, every 5 minutes) |
| `http_port`, `dns_port`, `adblock`, `upstream_dns` | Server ports and the ad blocker |

Changes made from the phone remote are saved separately in `data/prefs.json` and win over `settings.json`.
The TV picks up edits to `settings.json` by itself within a few seconds.

Optional extras:

```bash
.venv/bin/python scripts/fetch_photos.py      # background photos for the home screen and screensaver
.venv/bin/python scripts/fetch_logos.py       # logos for apps beyond the built-in Simple Icons set
.venv/bin/python scripts/build_blocklist.py   # rebuild the ad blocker's list from EasyList
```

### 5. Keep it running

**macOS / Linux**

```bash
./scripts/install_service.sh
```

On macOS this adds a LaunchAgent; on Linux a systemd service (which also lets the ad blocker use port 53).
`./scripts/install_service.sh uninstall` removes it.

**Windows 10 / 11**: right-click `scripts\install_service.ps1` > *Run with PowerShell*, or from PowerShell:

```powershell
.\scripts\install_service.ps1 -KeepAwake
```

This starts Hearth hidden every time you sign in (and restarts it if it stops), opens the firewall for
the TV on your home network (setting the Wi-Fi to *Private* if it's *Public*), and with `-KeepAwake` stops
the laptop sleeping while it's plugged in, even with the lid closed. `-Uninstall` removes all of it.
For the Wi-Fi menu to list nearby networks, Windows 11 also needs **Settings → Privacy & security → Location** on.

**Whatever the machine**: Hearth only works while it's on, awake and at home. If it's off, the TV simply
behaves like a normal VIDAA TV until it's back.

### 6. Updating

Hearth checks its GitHub repo every 5 minutes. When there are new commits it pulls them and restarts
itself, so you can make changes on another computer, push them, and the machine running Hearth picks
them up on its own. It never overwrites local edits: if the folder has changes of its own, it skips
the update (see `/api/events`).

### 7. Ad blocker (optional)

On the TV: **Settings → Network → Network Configuration → your network → IP Settings → DNS: Manual**,
and enter the computer's address. The phone remote's Ad blocker card shows a tick once the TV is using it.

If the computer running Hearth is off, a TV pointed at it has no internet. Only do this with an always-on
machine, or add a public DNS such as `1.1.1.1` as the TV's second DNS (it lets some ads through).
If an app breaks, add its domain to `adblock/allowlist.txt`.

## Set up with Claude Code

This repo includes a Claude Code skill, `.claude/skills/hearth-setup`. Open the folder in
[Claude Code](https://claude.com/claude-code) and ask *"set up Hearth for my TV"*. It walks
through the steps above with you, including pairing and personalising `settings.json`.

## How it works

The TV runs an MQTT broker on port 36669 (TLS 1.3 with a client certificate). Hearth logs in
with credentials derived from the TV's clock, pairs with an on-screen PIN, and then uses the
access token the TV issues (renewed with a 30-day refresh token). Over that connection it sends
remote keys, launches apps and web pages, switches inputs, and listens to what the TV is showing.

The home screen is a web page served by Hearth and opened on the TV like any VIDAA web app. When
the TV reports VIDAA's launcher (`remote_launcher`) or wakes from standby, Hearth opens its page again.

```
hearth/      the bridge (Python): protocol, TV connection, web server, ad blocker, Wi-Fi scan, updater
web/         the phone remote (index.html) and the TV home screen (tv/index.html)
scripts/     certificate, photos, logos, block list, service installers (macOS/Linux and Windows)
start.sh     start on macOS / Linux        start.cmd   start on Windows
adblock/     domain lists for the ad blocker
tests/       python -m unittest discover tests
```

Useful endpoints: `/api/status` (everything the pages see) and `/api/events` (recent TV events).
Set `HEARTH_DEBUG=1` to log them to the console.

## Troubleshooting

- **"No VIDAA client certificate"**: run step 2.
- **Connect fails with "Not authorized" for every login style**: the certificate doesn't match your firmware; try a newer version of the VIDAA app.
- **Python/TLS error on start**: install a newer Python (see Requirements), delete `.venv`, start again.
- **Windows: the TV can't load the home screen**: run `install_service.ps1` again (firewall rules), and check the Wi-Fi network is *Private*.
- **Ad blocker "couldn't start on port 53"**: on Linux, use `install_service.sh`, or set `"dns_port"` and point the TV elsewhere.
- **TV shows a spinner forever**: Hearth reloads the page by itself after 7 seconds; check that the computer's firewall allows port 8765.

## Credits

- VIDAA protocol details: [stevene1919/hisense_vidaa](https://github.com/stevene1919/hisense_vidaa)
- Design inspiration: [tv-vibehack](https://github.com/Gathin23/tv-vibehack)
- Font: [Outfit](https://github.com/Outfitio/Outfit-Fonts) (SIL OFL 1.1)
- Logos: [Simple Icons](https://simpleicons.org) (CC0); trademarks belong to their owners
- Photos: [Unsplash](https://unsplash.com) via [Lorem Picsum](https://picsum.photos)
- Ad and tracker domains: [EasyList](https://easylist.to)
- Scripture: King James Version (public domain)

Hearth is not affiliated with or endorsed by Hisense or VIDAA. MIT licence.
