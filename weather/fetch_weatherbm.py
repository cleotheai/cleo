#!/usr/bin/env python3
"""
Weather Bermuda Data Fetcher
Pulls data from weather.bm and writes weather_data.json.
Run after 5:30 AM ADT for the freshest forecast issue.
"""
import urllib.request, re, json, os
from html import unescape
from datetime import datetime, timezone, timedelta

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
ADT = timezone(timedelta(hours=-3))

URLS = {
    "homepage":  "https://www.weather.bm/",
    "forecast":  "https://www.weather.bm/ForecastpublicExtended.asp",
    "warnings":  "https://www.weather.bm/currentwarnings.asp",
    "marine":    "https://www.weather.bm/marineforecast.asp",
    "suntimes":  "https://www.weather.bm/Tools/DaylightTimes.asp?Month=9&Year=2026",
    "tides":     "https://www.weather.bm/Tools/TideTimes.asp?Month=9&Year=2026",
}

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        raw = r.read()
    try:
        return raw.decode(r.headers.get_content_charset() or "utf-8")
    except:
        return raw.decode("utf-8", errors="replace")

def clean(s):
    s = unescape(s).replace('&nbsp;', ' ')
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def strip_tags(s):
    return re.sub(r'<[^>]+>', ' ', s)

def local_now():
    return datetime.now(ADT)

def fetch_all():
    out = {}
    for name, url in URLS.items():
        try:
            out[name] = fetch(url)
            print(f"  OK  {name:10s} {len(out[name]):6d} bytes")
        except Exception as e:
            print(f"  FAIL {name}: {e}")
            out[name] = ""
    return out

def parse_current(html):
    c = {}
    m = re.search(
        r'Recorded at\s+(\d{1,2}:\d{2}\s*[ap]\.?m\.?)'
        r'.*?'
        r'<div>\s*([^<]+?)\s*</div>\s*'
        r'<div>\s*<div[^>]*>\s*Temp\.?:&nbsp;</div>\s*<div[^>]*>\s*([^<]+?)\s*</div>\s*</div>\s*'
        r'<div>\s*<div[^>]*>\s*Humidity:&nbsp;</div>\s*<div[^>]*>\s*(\d+)\s*%\s*</div>',
        html, re.DOTALL
    )
    if m:
        c["recorded_at"] = clean(m.group(1))
        c["condition"] = clean(m.group(2))
        nv = re.findall(r'-?\d+\.?\d*', m.group(3))
        if nv:
            c["temperature_c"] = round(float(nv[0]), 1)
        c["humidity"] = int(m.group(4))
    else:
        rec = re.search(r'Recorded at\s+(\d{1,2}:\d{2}\s*[ap]\.?m\.?)', html)
        if rec:
            c["recorded_at"] = clean(rec.group(1))
        cond = re.search(r'Recorded at[^<]*</div>\s*<div[^>]*>\s*([^<]+?)\s*</div>', html, re.DOTALL)
        if cond:
            c["condition"] = clean(cond.group(1))
        tmp = re.search(r'Temp\.?:&nbsp;</div>\s*<div[^>]*>\s*([^<]+?)\s*</div>', html)
        if tmp:
            nv = re.findall(r'-?\d+\.?\d*', tmp.group(1))
            if nv:
                c["temperature_c"] = round(float(nv[0]), 1)
        hum = re.search(r'Humidity:?&nbsp;</div>\s*<div[^>]*>\s*(\d+)\s*%', html)
        if hum:
            c["humidity"] = int(hum.group(1))
    return c

def parse_alerts(html_hp, html_wr):
    alerts = []
    seen = set()
    for m in re.finditer(r'<a\s+href="[^"]*currentwarnings[^"]*"[^>]*>([^<]+)</a>', html_hp):
        title = clean(m.group(1))
        if not title or title == "Warnings":
            continue
        if title in seen:
            continue
        seen.add(title)
        ctx = html_hp[m.end():m.end()+400]
        vm = re.search(r'Valid\s+for\s+([^<]+?)(?:</span>|$)', ctx)
        alerts.append({"title": title, "valid": clean(vm.group(1)).strip() if vm else None})
    for m in re.finditer(r'<h2>([^<]+)</h2>', html_wr):
        title = clean(m.group(1))
        if not title or title in seen:
            continue
        seen.add(title)
        ctx = html_wr[m.end():m.end()+500]
        vm = re.search(r'Valid:\s*(.+?)(?:</div>|$)', ctx)
        um = re.search(r'Updated:\s*(.+?)(?:</div>|$)', ctx)
        a = {"title": title}
        if vm:
            a["valid"] = clean(vm.group(1))
        if um:
            a["updated"] = clean(um.group(1))
        alerts.append(a)
    return alerts

def parse_forecast(html):
    r = {"issue": None, "synopsis": None, "headline": None, "periods": []}
    m = re.search(r'Issued\s+at\s+(\d{1,2}:\d{2}\s*[ap]\.?m\.?)\s*[-–]\s*(.+?)(?:<br>|$)', html)
    if m:
        r["issue"] = f"{clean(m.group(1))} {clean(m.group(2))}"
    m = re.search(r'class="publicSynopsis"[^>]*>(.*?)</div>\s*<h4', html, re.DOTALL)
    if m:
        r["synopsis"] = clean(strip_tags(m.group(1)))
    m = re.search(r'<h4>Headline[^<]*</h4>\s*(.*?)(?:</div>|<div class="publicSynopsis")', html, re.DOTALL)
    if m:
        r["headline"] = clean(strip_tags(m.group(1)))
    for m in re.finditer(
        r'<div class="periodElement">(.*?)</div>\s*(?=<div class="periodElement">|<!--)',
        html, re.DOTALL
    ):
        block = m.group(1)
        hm = re.search(r'<h4>([^<]+?)\s*[-–—]?\s*</h4>', block)
        if not hm:
            continue
        name = clean(hm.group(1)).strip()
        text = clean(strip_tags(block))
        p = {"name": name, "condition": text}
        wi = text.lower().find("winds ")
        if wi > 5:
            p["condition"] = clean(text[:wi]).strip()
        hi = re.search(r'[Hh]igh\s+near\s+(\d+)', text)
        if hi:
            p["temp_high"] = int(hi.group(1))
        lo = re.search(r'[Ll]ow\s+near\s+(\d+)', text)
        if lo:
            p["temp_low"] = int(lo.group(1))
        wm = re.search(r'Winds\s+(.+?)(?:\.\s|$)', text)
        if wm:
            p["wind_text"] = clean(wm.group(1))
        r["periods"].append(p)
    return r

def parse_marine(html):
    r = {}
    m = re.search(r'Sea\s*Temp\.?:&nbsp;</div>\s*<div[^>]*>\s*([^<]+?)\s*</div>', html)
    if m:
        nv = re.findall(r'-?\d+\.?\d*', m.group(1))
        if nv:
            r["sea_temp_c"] = round(float(nv[0]), 1)
    m = re.search(r'class="publicSynopsis"[^>]*>(.*?)</div>\s*<h4', html, re.DOTALL)
    if m:
        r["synopsis"] = clean(strip_tags(m.group(1)))
    m = re.search(r'Issued\s+at\s+(\d{1,2}:\d{2}\s*[ap]\.?m\.?\s+\w+,\s+\w+\s+\d+,\s+\d{4})', html)
    if m:
        r["issued"] = clean(m.group(1))
    return r

def parse_sun(html, day):
    r = {}
    d = re.escape(str(day))
    # Sun cell: <td>...<div><b>26&nbsp;Full Moon</b></div><div>SR: ...</div>...</td>
    m = re.search(
        r'<td[^>]*>\s*(?:<div>\s*)?<b[^>]*>\s*' + d + r'\s*.*?</b>\s*</div>(.*?)</td>',
        html, re.DOTALL
    )
    if m:
        cell = m.group(1)
        for label in ["SR:", "SS:", "MR:", "MS:", "CR:"]:
            lm = re.search(r'<div>\s*[&nbsp;\s]*' + label + r'\s*([^<]+?)\s*</div>', cell)
            if lm:
                key = label.strip(':').lower()
                r["sunrise" if key == "sr" else "sunset" if key == "ss" else "moon_rise" if key == "mr" else "moon_set" if key == "ms" else key] = clean(lm.group(1))
        # Moon phase is inside the <b> tag with the day number
        bm = re.search(r'<b[^>]*>\s*' + d + r'\s*&nbsp;\s*(Full\s+Moon|New\s+Moon|First\s+Quarter|Last\s+Quarter)', html, re.DOTALL | re.IGNORECASE)
        if bm:
            r["moon_phase"] = clean(bm.group(1))
    return r

def parse_tides(html, day):
    r = []
    d = re.escape(str(day))
    m = re.search(r'<td[^>]*>\s*<div>\s*' + d + r'\s*</div>(.*?)</td>', html, re.DOTALL)
    if m:
        block = m.group(1)
        for tm in re.finditer(
            r'<div[^>]*class="time">([^<]+)</div>\s*'
            r'<div[^>]*class="heightm">\s*\|\s*([\d.]+)\s*</div>\s*'
            r'<div[^>]*class="heightf">\s*/\s*([\d.]+)\s*</div>',
            block
        ):
            r.append({
                "time": clean(tm.group(1)),
                "height_m": round(float(tm.group(2)), 1),
                "height_ft": round(float(tm.group(3)), 1),
            })
    return r

def main():
    print("Fetching weather.bm...")
    pages = fetch_all()
    day = local_now().day
    print(f"\nParsing (day {day})...")
    data = {
        "current": parse_current(pages.get("homepage", "")),
        "alerts": parse_alerts(pages.get("homepage", ""), pages.get("warnings", "")),
        "forecast": parse_forecast(pages.get("forecast", "")),
        "marine": parse_marine(pages.get("marine", "")),
        "sun": parse_sun(pages.get("suntimes", ""), day),
        "tides": parse_tides(pages.get("tides", ""), day),
        "fetched_at": local_now().strftime("%Y-%m-%d %H:%M:%S ADT"),
        "wind_from": "Windguru widget (sole wind/wave source — weather.bm wind/wave data excluded)",
    }
    if data["forecast"].get("issue"):
        data["last_updated"] = data["forecast"]["issue"]
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "weather_data.json")
    with open(out_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"\nWrote {out_path}")
    c = data["current"]
    print(f"\nCurrent: {c.get('temperature_c','?')}°C  {c.get('condition','?')}  Humidity {c.get('humidity','?')}%  ({c.get('recorded_at','?')})")
    print(f"Alerts: {len(data['alerts'])}")
    for a in data["alerts"]:
        v = a.get("valid") or a.get("updated") or ""
        print(f"  - {a['title']}" + (f" ({v})" if v else ""))
    fc = data["forecast"]
    periods = fc.get("periods", []) if isinstance(fc, dict) else []
    print(f"Forecast: {len(periods)} periods")
    for p in periods:
        t = ""
        if isinstance(p, dict):
            if p.get("temp_high") is not None:
                t += f" Hi{p['temp_high']}°C"
            if p.get("temp_low") is not None:
                t += f" Lo{p['temp_low']}°C"
            print(f"  {p.get('name','?'):14s} {str(p.get('condition',''))[:55]}...  {t}")
    s = data["sun"]
    print(f"Sun:    {s.get('sunrise','?')} / {s.get('sunset','?')}  Moon: {s.get('moon_phase','?')}")
    print(f"Tides ({len(data['tides'])}):")
    for t in data["tides"]:
        print(f"  {t['time']}  {t['height_m']}m / {t['height_ft']}ft")
    if data["marine"]:
        m = data["marine"]
        print(f"Marine: sea {m.get('sea_temp_c','?')}°C  issued {m.get('issued','?')}")

if __name__ == "__main__":
    main()
