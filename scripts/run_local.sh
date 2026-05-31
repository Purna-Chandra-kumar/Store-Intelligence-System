#!/usr/bin/env bash
# Local dev convenience runner — assumes Docker is available.
set -euo pipefail
cd "$(dirname "$0")/.."
cp -n .env.example .env || true
./scripts/download_sample_video.sh
docker compose up --build
