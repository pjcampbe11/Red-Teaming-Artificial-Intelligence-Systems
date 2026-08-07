#!/usr/bin/env bash
# Reset the range to a clean baseline (removes planted poison/state).
set -e
if command -v docker >/dev/null && docker compose ps >/dev/null 2>&1; then
  docker compose down
  docker compose up -d --build
else
  echo "Docker compose not detected. If running via run_all.py, stop it (Ctrl-C)"
  echo "and start it again to reset in-memory state."
fi
curl -s -X POST http://localhost:9000/reset >/dev/null 2>&1 || true
echo "reset complete."
