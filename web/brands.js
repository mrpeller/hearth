// Tile artwork for the TV's apps (the TV's own icons are locked to the TV).
// bg: tile background, glow: ambient colour behind the focused tile.
// logo: image under /tv/logos/ with logoH as % of tile height; label: optional text beside the logo.
// Apps without a usable logo fall back to a wordmark (mark/fg/w).
var LOGO = "/tv/logos/";
var VIDAA = { bg: "linear-gradient(140deg,#1d1d22,#0b0b0d)", logo: "vidaa.png", logoH: 46, round: true, glow: "#3a6df0" };
var BRANDS = {
  "netflix":      { bg: "#000", logo: "si-netflix.svg", logoH: 62, glow: "#c4000c" },
  "youtube":      { bg: "#f4f4f6", logo: "si-youtube.svg", logoH: 34, label: "YouTube", lc: "#0f0f0f", glow: "#d1001f" },
  "spotify":      { bg: "#121212", logo: "si-spotify.svg", logoH: 34, label: "Spotify", lc: "#fff", glow: "#139d48" },
  "prime video":  { bg: "linear-gradient(135deg,#1a98ff,#0057d9)", logo: "si-primevideo.svg", logoH: 62, glow: "#0a6cff" },
  "apple tv":     { bg: "linear-gradient(160deg,#2c2c2e,#000)", logo: "si-appletv.svg", logoH: 46, glow: "#6b6b70" },
  "dazn":         { bg: "#0c0c0c", logo: "si-dazn.svg", logoH: 52, glow: "#555" },
  "plex":         { bg: "#1f1f1f", logo: "si-plex.svg", logoH: 52, glow: "#b97f00" },
  "mubi":         { bg: "#000", logo: "si-mubi.svg", logoH: 42, label: "MUBI", lc: "#fff", glow: "#666" },
  "nba":          { bg: "linear-gradient(135deg,#1d428a,#c8102e)", logo: "si-nba.svg", logoH: 58, label: "NBA", lc: "#fff", glow: "#8b2a5e" },
  "ufc":          { bg: "#d20a0a", logo: "si-ufc.svg", logoH: 52, glow: "#c00" },
  "red bull tv":  { bg: "linear-gradient(135deg,#0f1e4a,#1d3b8f)", logo: "si-redbull.svg", logoH: 46, label: "TV", lc: "#fff", glow: "#d0103a" },
  "accuweather":  { bg: "linear-gradient(135deg,#f58220,#e04e14)", logo: "si-accuweather.svg", logoH: 44, label: "AccuWeather", lc: "#fff", glow: "#f05514" },
  "triller tv":   { bg: "#0b0b0b", logo: "si-triller.svg", logoH: 44, label: "Triller TV", lc: "#fff", glow: "#7a4dff" },
  "deezer":       { bg: "#0f0d13", logo: "deezer.png", logoH: 46, label: "Deezer", lc: "#fff", glow: "#8a2cff" },
  "iqiyi":        { bg: "#0a1f10", logo: "iqiyi.png", logoH: 52, round: true, glow: "#00b336" },
  "dstv now":     { bg: "#f4f4f6", logo: "dstv-now.png", logoH: 50, label: "DStv Now", lc: "#0b3a8c", glow: "#0b4fc0" },
  "kidoodle tv":  { bg: "linear-gradient(135deg,#4a2391,#2a0f5c)", logo: "kidoodle-tv.svg", logoH: 30, glow: "#e0a800" },
  "haystack tv local world news": { bg: "#f4f4f6", logo: "haystack.png", logoH: 46, label: "Haystack", lc: "#1a1a1a", glow: "#c62828" },
  "startimes on": { bg: "linear-gradient(135deg,#1c2a4a,#0b1120)", logo: "startimes-on.png", logoH: 50, label: "StarTimes", lc: "#fff", glow: "#ff6a00" },
  "sportytv free football live": { bg: "linear-gradient(135deg,#e41827,#8f0710)", logo: "sportytv.png", logoH: 50, round: true, label: "SportyTV", lc: "#fff", glow: "#c4101f" },
  "afrolandtv":   { bg: "#0d0d0d", logo: "afrolandtv.png", logoH: 46, round: true, label: "AfroLandTV", lc: "#fff", glow: "#2e8b57" },
  "mindset":      { bg: "#1c2b2e", logo: "mindset.webp", logoH: 50, round: true, label: "Mindset", lc: "#fff", glow: "#2aa3a8" },
  "iwant":        { bg: "#1a1a1a", logo: "iwant.png", logoH: 50, round: true, glow: "#888" },
  "chaupaltv":    { bg: "#141414", logo: "chaupaltv.ico", logoH: 40, label: "Chaupal", lc: "#fff", glow: "#e53935" },
  "toongoggles":  { bg: "#1d5fa8", logo: "toongoggles.png", logoH: 58, round: true, glow: "#2f80ed" },
  "mbc shahid":   { bg: "#0d1a17", logo: "mbc-shahid.png", logoH: 52, round: true, label: "Shahid", lc: "#fff", glow: "#2db36b" },
  "a to z movie box": { bg: "#0d1530", logo: "vlogbox.png", logoH: 50, round: true, label: "Movie Box", lc: "#fff", glow: "#2c5cd6" },
  "vidaa art": VIDAA, "vidaa smart life": VIDAA, "v home": VIDAA, "app store": VIDAA,
  "vod on demand": VIDAA, "e manual": VIDAA, "tv browser": VIDAA,
  // No usable logo: wordmarks.
  "uefa tv":      { bg: "linear-gradient(135deg,#00145c,#0a2fa8)", fg: "#fff", mark: "UEFA.tv", w: 700, glow: "#1b3fd1" },
  "tv channels":  { bg: "linear-gradient(135deg,#2b2d42,#11121b)", fg: "#fff", mark: "Live TV", w: 600, glow: "#5865f2" },
  "showmax":      { bg: "linear-gradient(135deg,#e4006d,#4d0025)", fg: "#fff", mark: "showmax", w: 800, glow: "#d0005f" }
};

function brandKey(name) {
  return String(name || "").toLowerCase().replace(/[^a-z0-9 ]+/g, " ").replace(/\s+/g, " ").trim();
}

function brandFor(name) {
  var k = brandKey(name);
  if (BRANDS[k]) return BRANDS[k];
  var first = k.split(" ")[0];  // "Spotify : Music & Podcasts" -> "spotify"
  if (first.length > 3 && BRANDS[first]) return BRANDS[first];
  // Fallback: a calm gradient from a hue hashed from the name.
  var h = 0;
  for (var i = 0; i < k.length; i++) h = (h * 31 + k.charCodeAt(i)) % 360;
  return {
    bg: "linear-gradient(135deg,hsl(" + h + ",45%,32%),hsl(" + ((h + 40) % 360) + ",55%,16%))",
    fg: "#fff", mark: String(name || "").replace(/\s*[:▶].*$/, ""), w: 600, glow: "hsl(" + h + ",60%,35%)"
  };
}

function tileHTML(name, big) {
  var b = brandFor(name);
  var html = '<div class="art" style="background:' + b.bg + '">';
  if (b.logo) {
    html += '<span class="logoRow" style="height:' + b.logoH + '%">' +
      '<img class="logo' + (b.round ? " round" : "") + '" data-src="' + LOGO + b.logo + '" data-name="' + escapeHTML(name) + '" alt="">' +
      (b.label ? '<span class="logoLabel" style="color:' + b.lc + '">' + escapeHTML(b.label) + '</span>' : "") +
      '</span>';
  } else {
    var size = b.mark.length > 9 ? (big ? 0.9 : 0.8) : (big ? 1.25 : 1);
    html += '<span class="mark" style="color:' + b.fg + ';font-weight:' + b.w + ';letter-spacing:' + (b.ls || "-0.01em") +
            ';font-size:' + size + 'em">' + escapeHTML(b.mark) + '</span>';
  }
  return html + '</div>';
}

function escapeHTML(s) {
  return String(s).replace(/[&<>"']/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
  });
}
