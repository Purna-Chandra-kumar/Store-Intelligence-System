#!/usr/bin/env bash
# Downloads a public pedestrian CCTV sample used by the ai-engine.
# Default: Oxford Town Centre (pedestrian dataset, public).
set -euo pipefail

mkdir -p ./data
OUT=./data/sample.mp4

if [[ -f "$OUT" ]]; then
  echo "Sample already present at $OUT"
  exit 0
fi

# Mirror used by many CV demos. Replace with your own URL if unavailable.
URL="${SAMPLE_URL:-https://motchallenge.net/sequenceVideos/MOT17-04-FRCNN-raw.webm}"

echo "Downloading sample CCTV video from $URL"
curl -L --fail -o "$OUT.tmp" "$URL"
mv "$OUT.tmp" "$OUT"
echo "Saved to $OUT"
