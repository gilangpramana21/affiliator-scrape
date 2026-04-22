#!/usr/bin/env bash
set -euo pipefail

python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt
./venv/bin/playwright install chromium

mkdir -p logs output config

if [ ! -f config/config.safe.json ]; then
  cp config/config.template.json config/config.safe.json
fi

if [ ! -f config/cookies.json ]; then
  cp config/cookies.example.json config/cookies.json
fi

echo "Single-machine setup complete."
echo "Next: make preflight && make run-safe"
