#!/usr/bin/env bash
# Keep Hearth running: start it at boot/login and restart it if it stops.
#   macOS:  a LaunchAgent for your user
#   Linux:  a systemd service (Raspberry Pi OS, Ubuntu, Debian...)
#   ./scripts/install_service.sh            install and start
#   ./scripts/install_service.sh uninstall  remove
set -euo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd)"
ACTION="${1:-install}"

if [ "$(uname)" = "Darwin" ]; then
  PLIST="$HOME/Library/LaunchAgents/com.hearth.tv.plist"
  if [ "$ACTION" = "uninstall" ]; then
    launchctl unload "$PLIST" 2>/dev/null || true; rm -f "$PLIST"; echo "Removed."; exit 0
  fi
  mkdir -p "$HOME/Library/LaunchAgents" "$DIR/data"
  cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.hearth.tv</string>
  <key>ProgramArguments</key><array><string>$DIR/start.sh</string></array>
  <key>WorkingDirectory</key><string>$DIR</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$DIR/data/hearth.log</string>
  <key>StandardErrorPath</key><string>$DIR/data/hearth.log</string>
</dict></plist>
EOF
  launchctl unload "$PLIST" 2>/dev/null || true
  launchctl load "$PLIST"
  echo "Hearth will now start at login. Log: $DIR/data/hearth.log"
  echo "Tip: stop the Mac from sleeping (System Settings > Battery/Energy) or the TV loses its home screen."
else
  UNIT=/etc/systemd/system/hearth.service
  if [ "$ACTION" = "uninstall" ]; then
    sudo systemctl disable --now hearth 2>/dev/null || true; sudo rm -f "$UNIT"; sudo systemctl daemon-reload; echo "Removed."; exit 0
  fi
  sudo tee "$UNIT" >/dev/null <<EOF
[Unit]
Description=Hearth TV home screen
After=network-online.target
Wants=network-online.target

[Service]
User=$USER
WorkingDirectory=$DIR
ExecStart=$DIR/start.sh
Restart=always
RestartSec=3
# Lets the ad blocker use DNS port 53 without running as root.
AmbientCapabilities=CAP_NET_BIND_SERVICE

[Install]
WantedBy=multi-user.target
EOF
  sudo systemctl daemon-reload
  sudo systemctl enable --now hearth
  echo "Hearth is running as a service. Logs: journalctl -u hearth -f"
fi
