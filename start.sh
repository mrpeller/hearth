#!/usr/bin/env bash
# Start Hearth. Creates a virtual environment on first run.
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
    .venv/bin/pip install -q --upgrade pip
    .venv/bin/pip install -q -r requirements.txt
  elif [ -n "$UV" ]; then
    echo "Setting up with uv"
    "$UV" venv -q --python 3.12 .venv
    "$UV" pip install -q --python .venv/bin/python -r requirements.txt
  else
    echo "Hearth needs a Python with TLS 1.3. Install one of:"
    echo "  uv:        https://docs.astral.sh/uv/  (then run ./start.sh again)"
    echo "  Homebrew:  brew install python"
    exit 1
  fi
fi

[ -f adblock/blocklist.txt ] || .venv/bin/python scripts/build_blocklist.py || echo "Ad block list not built; only adblock/base.txt will be used."

exec .venv/bin/python -m hearth
