#!/usr/bin/env bash
set -euo pipefail

./scripts/setup_single_machine.sh

if command -v docker >/dev/null 2>&1; then
  docker compose up -d redis
  echo "Redis started via docker compose."
else
  echo "Docker not found. Install/start Redis manually on localhost:6379."
fi

if [ ! -f config/config.distributed.json ]; then
  cp config/config.safe.json config/config.distributed.json
  echo "Created config/config.distributed.json (edit distributed fields before run)."
fi

echo "Distributed setup complete."
