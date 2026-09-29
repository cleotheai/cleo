#!/usr/bin/env bash
# Weather page daily updater
# Fetches fresh data from weather.bm, builds the page, and pushes to GitHub
set -e

WEATHER_DIR="/home/cleo/sites/cleo/weather"
REPO_DIR="/home/cleo/sites/cleo"
LOG="/home/cleo/sites/cleo/weather/update.log"

cd "$WEATHER_DIR"

echo "=== $(date -u '+%Y-%m-%d %H:%M:%S UTC') ===" >> "$LOG"

echo "[1/3] Fetching weather.bm data..."
if python3 fetch_weatherbm.py >> "$LOG" 2>&1; then
    echo "[1/3] Fetch OK" >> "$LOG"
else
    echo "[1/3] Fetch FAILED" >> "$LOG"
    exit 1
fi

echo "[2/3] Building index.html..."
if python3 build_page.py >> "$LOG" 2>&1; then
    echo "[2/3] Build OK" >> "$LOG"
else
    echo "[2/3] Build FAILED" >> "$LOG"
    exit 1
fi

cd "$REPO_DIR"

# Only commit/push if something changed
if git diff --quiet -- weather/weather_data.json weather/index.html; then
    echo "[3/3] No changes — nothing to push" >> "$LOG"
    exit 0
fi

echo "[3/3] Committing & pushing..." >> "$LOG"
git add weather/weather_data.json weather/index.html
git commit -m "weather: daily refresh ($(date -u '+%Y-%m-%d %H:%M UTC'))"
if git push origin main >> "$LOG" 2>&1; then
    echo "[3/3] Push OK" >> "$LOG"
else
    echo "[3/3] Push FAILED" >> "$LOG"
    exit 1
fi

echo "=== Done ===" >> "$LOG"
