#!/usr/bin/env python3
"""
Weather Page Builder
Reads weather_data.json and generates the filled-in index.html.
Run after fetch_weatherbm.py to update the page with fresh data.
"""
import json, os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(SCRIPT_DIR, "weather_data.json")
TEMPLATE_PATH = os.path.join(SCRIPT_DIR, "index.html")
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "index.html")

# Read data
with open(DATA_PATH) as f:
    data = json.load(f)

# Read template
with open(TEMPLATE_PATH) as f:
    html = f.read()

# === ALERTS ===
alerts = data.get("alerts", [])
if alerts:
    # Build alert banner HTML
    alert_items = []
    for a in alerts:
        title = a.get("title", "Alert")
        valid = a.get("valid") or a.get("updated") or ""
        alert_items.append(f'<div class="alert-item"><strong>{title}</strong><span class="alert-valid">{valid}</span></div>')
    
    alert_html = '\n'.join(alert_items)
    # Replace placeholder alert banner
    html = html.replace(
        '<div class="alert-banner" id="alert-banner">\n    <strong id="alert-title"></strong>\n    <span id="alert-body"></span>\n    <div class="alert-valid" id="alert-valid"></div>\n  </div>',
        f'<div class="alert-banner" id="alert-banner">\n{alert_html}\n  </div>'
    )
    # Show banner
    html = html.replace(
        '.alert-banner {\n  display: none;',
        '.alert-banner {\n  display: block;'
    )
else:
    # Hide banner
    html = html.replace(
        '.alert-banner {\n  display: none;',
        '.alert-banner {\n  display: none;'
    )

# === LAST UPDATED ===
last_up = data.get("last_updated") or data.get("fetched_at", "No data")
html = html.replace('id="last-updated">Loading...</div>', f'id="last-updated">Updated: {last_up}</div>')

# === CURRENT CONDITIONS ===
c = data.get("current", {})
temp = c.get("temperature_c")
if temp is not None:
    html = html.replace('id="temp-value">--<', f'id="temp-value">{temp}<')
hum = c.get("humidity")
if hum is not None:
    html = html.replace('id="humidity-value">--<', f'id="humidity-value">{hum}<')

# === FORECAST ===
fc = data.get("forecast", {})
periods = fc.get("periods", []) if isinstance(fc, dict) else []

if periods:
    forecast_items = []
    for p in periods:
        if not isinstance(p, dict):
            continue
        name = p.get("name", "?")
        condition = p.get("condition", "")
        # Strip the name prefix from condition if present (e.g. "Today - ...")
        if condition.startswith(name):
            condition = condition[len(name):].strip().lstrip(" -")
        temp_high = p.get("temp_high")
        temp_low = p.get("temp_low")
        
        temps = ""
        if temp_high is not None:
            temps += f'<span class="forecast-temp">Hi <span>{temp_high}°C</span></span>'
        if temp_low is not None:
            temps += f'<span class="forecast-temp">Lo <span>{temp_low}°C</span></span>'
        
        forecast_items.append(
            f'<li class="forecast-item">'
            f'<span class="forecast-day">{name}</span>'
            f'<span class="forecast-text">{condition}</span>'
            f'{temps}'
            f'</li>'
        )
    
    forecast_html = "\n".join(forecast_items)
    html = html.replace(
        '<ul class="forecast-list" id="forecast-list">\n        <li class="forecast-item"><span class="forecast-day">Loading...</span></li>\n      </ul>',
        f'<ul class="forecast-list" id="forecast-list">\n{forecast_html}\n      </ul>'
    )

# === SUN TIMES ===
s = data.get("sun", {})
sunrise = s.get("sunrise") or s.get("sr")
sunset = s.get("sunset") or s.get("ss")
moon = s.get("moon_phase")

if sunrise:
    html = html.replace('id="sunrise-time">--:--', f'id="sunrise-time">{sunrise}')
if sunset:
    html = html.replace('id="sunset-time">--:--', f'id="sunset-time">{sunset}')
if moon:
    html = html.replace('id="moon-phase">--', f'id="moon-phase">{moon}')

# === TIDES ===
tides = data.get("tides", [])
if tides:
    tide_items = []
    for t in tides:
        if not isinstance(t, dict):
            continue
        ht = t.get("height_m")
        hf = t.get("height_ft")
        height_str = f"{ht}m" if ht is not None else ""
        if hf is not None:
            height_str += f" / {hf}ft" if height_str else f"{hf}ft"
        tide_items.append(
            f'<li class="tide-item">'
            f'<span class="tide-type">{t.get("time", "?")}</span>'
            f'<span class="tide-height">{height_str}</span>'
            f'</li>'
        )
    
    tide_html = "\n".join(tide_items)
    html = html.replace(
        '<ul class="tide-list" id="tide-list">\n          <li class="tide-item"><span class="tide-type">Loading...</span></li>\n        </ul>',
        f'<ul class="tide-list" id="tide-list">\n{tide_html}\n        </ul>'
    )

# === WRITE OUTPUT ===
with open(OUTPUT_PATH, "w") as f:
    f.write(html)

print(f"Built {OUTPUT_PATH}")
print(f"Alerts: {len(alerts)}")
print(f"Forecast periods: {len(periods)}")
print(f"Tides: {len(tides)}")
print(f"Sun: {sunrise} / {sunset} — {moon}")
c = data.get("current", {})
print(f"Temp: {c.get('temperature_c', '?')}°C — {c.get('condition', '?')} — Humidity {c.get('humidity', '?')}%")
