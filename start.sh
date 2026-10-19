#!/usr/bin/env bash
# Start Hearth (macOS / Linux). Creates a virtual environment on first run and restarts
# Hearth after it updates itself from GitHub. On Windows use start.cmd instead.
# The TV needs TLS 1.3, so this picks a Python whose SSL library supports it
# (macOS's built-in Python doesn't; `uv` or Homebrew Python do).
set -euo pipefail
cd "$(dirname "$0")"

has_tls13() { "$1" -c 'import ssl, sys; sys.exit(0 if ssl.HAS_TLSv1_3 and sys.version_info >= (3, 9) else 1)' 2>/dev/null; }

if [ ! -x .venv/bin/python ] || ! has_tls13 .venv/bin/python; then
  rm -rf .venv
  PY=""
  for c in ${HEARTH_PYTHON:-} python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$c" >/dev/null 2>&1 && has_tls13 "$(command -v "$c")"; then PY="$(command -v "$c")"; break; fi
  done
  UV="${UV:-$(command -v uv || true)}"
  if [ -n "$PY" ]; then
    echo "Setting up with $PY"
    "$PY" -m venv .venv
  elif [ -n "$UV" ]; then
    echo "Setting up with uv"
    "$UV" venv -q --python 3.12 .venv
  else
    echo "Hearth needs a Python with TLS 1.3. Install one of:"
    echo "  uv:        https://docs.astral.sh/uv/  (then run ./start.sh again)"
    echo "  Homebrew:  brew install python"
    exit 1
  fi
fi

# Install Python packages when requirements.txt is new or has changed (e.g. after an update).
sync_requirements() {
  local sum; sum="$(cksum requirements.txt | cut -d' ' -f1)"
  if [ "$(cat .venv/.requirements 2>/dev/null)" != "$sum" ]; then
    .venv/bin/python -m pip --version >/dev/null 2>&1 || .venv/bin/python -m ensurepip >/dev/null
    .venv/bin/python -m pip install -q --disable-pip-version-check -r requirements.txt
    echo "$sum" > .venv/.requirements
  fi
}

while true; do
  sync_requirements
  [ -f adblock/blocklist.txt ] || .venv/bin/python scripts/build_blocklist.py || echo "Ad block list not built; only adblock/base.txt will be used."
  code=0
  .venv/bin/python -m hearth || code=$?
  [ "$code" -eq 3 ] || exit "$code"   # 3 = updated from GitHub: start the new version
  echo "Restarting with the new version..."
done
