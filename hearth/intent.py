"""Content-first decision model: turns "what I want to watch" into a TV action.

Rules are checked in order; the first match wins. Each rule names either an app
(matched against the TV's own app list) or an input source.
"""
import re

RULES = [
    # (keywords regex, kind, target, why)
    (r"champions league|\bucl\b|uefa|europa league", "app", "UEFA.tv", "UEFA competitions stream on UEFA.tv"),
    (r"\bufc\b|\bmma\b", "app", "UFC", "UFC fights are on the UFC app"),
    (r"\bnba\b|basketball", "app", "NBA", "NBA games are on the NBA app"),
    (r"boxing|\bdazn\b", "app", "DAZN", "Boxing and DAZN events"),
    (r"premier league|\bepl\b|supersport|football|soccer|\bmatch\b|arsenal|chelsea|liverpool|man(chester)? (united|city)|super eagles|afcon",
     "app", "DStv Now", "Live football is on SuperSport via DStv Now"),
    (r"\bnews\b|headlines|breaking", "app", "Haystack TV Local + World News", "Haystack has live world news"),
    (r"kids?|children|cartoon|toddler|nursery", "app", "Kidoodle TV", "Kidoodle TV is made for kids"),
    (r"podcast|spotify|playlist|\bsongs?\b|music|album|afrobeats?", "app", "Spotify : Music & Podcasts", "Music and podcasts on Spotify"),
    (r"deezer", "app", "DEEZER", "You asked for Deezer"),
    (r"arthouse|indie film|\bmubi\b|criterion", "app", "MUBI", "MUBI curates arthouse cinema"),
    (r"\bplex\b|my (movies|media|files)", "app", "Plex", "Your own media is on Plex"),
    (r"nollywood|african movies?", "app", "AfroLandTV", "AfroLandTV focuses on African films"),
    (r"reacher|the boys|rings of power|\bprime\b|amazon|invincible", "app", "Prime Video", "That's a Prime Video title"),
    (r"youtube|trailer|tutorial|vlog|how to|music video|\bclip\b", "app", "YouTube", "Short videos and trailers live on YouTube"),
    (r"stranger things|wednesday|squid game|money heist|bridgerton|\bnetflix\b", "app", "Netflix", "That's a Netflix title"),
    (r"live tv|antenna|\bchannels?\b|broadcast|terrestrial", "source", "TV", "Switching to live TV"),
    (r"hdmi ?1", "source", "HDMI1", "Switching to HDMI 1"),
    (r"hdmi ?2", "source", "HDMI2", "Switching to HDMI 2"),
    (r"hdmi ?3", "source", "HDMI3", "Switching to HDMI 3"),
    (r"playstation|\bps[45]\b|xbox|console|nintendo|switch|gaming|play a game", "source", "HDMI1", "Consoles are usually on HDMI 1"),
    (r"\bav\b|dvd|decoder", "source", "AV", "Switching to AV"),
    # Broad moods last, so specific titles and services win.
    (r"movie|film|series|\bshow\b|binge|drama|thriller|comedy|funny|horror|romance|documentar|something to watch|bored",
     "app", "Netflix", "Netflix has the broadest movie and series catalogue"),
]

# Mood chips shown on the TV home: label -> phrase fed to decide().
MOODS = [
    ("Live football", "football"),
    ("Movies & series", "movie"),
    ("News", "news"),
    ("Music", "music"),
    ("Kids", "kids"),
    ("Live TV", "live tv"),
]


def _norm(s):
    return re.sub(r"[^a-z0-9 ]+", " ", (s or "").lower()).strip()


def find_app(apps, name):
    n = _norm(name)
    for a in apps:
        if _norm(a.get("name")) == n:
            return a
    for a in apps:
        an = _norm(a.get("name"))
        if an and (an.startswith(n) or n.startswith(an)):
            return a
    return None


def decide(text, apps, sources):
    """Return {"kind": "app"|"source", "target": <app dict or source dict>, "label", "why"} or None."""
    t = _norm(text)
    if not t:
        return None
    # 1. The person named an app outright ("open plex", "dstv").
    for a in sorted(apps, key=lambda a: -len(a.get("name", ""))):
        an = _norm(a.get("name"))
        short = an.split(" ")[0] if an else ""
        if an and (an in t or (len(short) >= 4 and re.search(rf"\b{re.escape(short)}\b", t))):
            return {"kind": "app", "target": a, "label": a["name"], "why": f"Opening {a['name']}"}
    # 2. Content and mood rules.
    for pattern, kind, target, why in RULES:
        if not re.search(pattern, t):
            continue
        if kind == "app":
            app = find_app(apps, target)
            if app:
                return {"kind": "app", "target": app, "label": app["name"], "why": why}
        else:
            src = next((s for s in sources if _norm(s.get("sourcename")) == _norm(target)), None)
            if src:
                return {"kind": "source", "target": src, "label": src.get("displayname") or src["sourcename"], "why": why}
    return None
