#!/usr/bin/env python3
"""Generate Cyberpunk-2077-style activity panel SVG from GitHub contribution data.

Scrapes the public contributions calendar (no token needed), computes streak
stats, and renders assets/activity-panel.svg in the same visual language as
the other HUD panels. Run daily via GitHub Actions.
"""

import re
import sys
import urllib.request
from datetime import date, timedelta
from pathlib import Path

USERNAME = "tothanhnguyen"
REPO_ROOT = Path(__file__).resolve().parent.parent
WEEKS_SHOWN = 52  # heatmap columns

# Cyberpunk 2077 palette — panel is self-contained dark, works on both themes
T = {
    "panel_fill": "#0B0E13", "panel_stroke": "#26333C",
    "yellow": "#FCEE0A", "cyan": "#00F0FF", "cyan_soft": "#5EF6FF",
    "red": "#FF003C", "text": "#EAF6F9", "muted": "#6B7A85",
    "faint": "#3D4A54", "divider": "#26333C",
    # heatmap intensity levels 0..4 (dark -> neon cyan)
    "levels": ["#101820", "#0B3B46", "#086B7E", "#04ABC4", "#00F0FF"],
}


def fetch_contributions():
    """Return (total_contributions, [(date, level), ...]) sorted by date."""
    url = f"https://github.com/users/{USERNAME}/contributions"
    req = urllib.request.Request(url, headers={"User-Agent": "activity-panel-generator"})
    html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8")

    total_match = re.search(r"([\d,]+)\s+contributions?\s+in the last year", html)
    total = int(total_match.group(1).replace(",", "")) if total_match else 0

    days = []
    for tag in re.findall(r"<td[^>]*ContributionCalendar-day[^>]*>", html):
        date_m = re.search(r'data-date="(\d{4}-\d{2}-\d{2})"', tag)
        level_m = re.search(r'data-level="(\d)"', tag)
        if date_m and level_m:
            days.append((date.fromisoformat(date_m.group(1)), int(level_m.group(1))))
    days.sort()
    if not days:
        sys.exit("ERROR: no contribution days parsed — GitHub HTML may have changed.")
    return total, days


def compute_stats(days):
    """Streaks and active-day count from (date, level) pairs (level>0 = active)."""
    active = {d for d, lvl in days if lvl > 0}
    longest = run = 0
    for d, lvl in days:
        run = run + 1 if lvl > 0 else 0
        longest = max(longest, run)

    # current streak: walk backwards from the last day; today with 0 doesn't break it
    current = 0
    cursor = days[-1][0]
    if cursor not in active:
        cursor -= timedelta(days=1)
    while cursor in active:
        current += 1
        cursor -= timedelta(days=1)
    return current, longest, len(active)


def heatmap_cells(days):
    """SVG rects for the last WEEKS_SHOWN weeks, GitHub-style grid (Sunday top)."""
    days = days[-(WEEKS_SHOWN * 7):]
    first = days[0][0]
    first_sunday = first - timedelta(days=(first.weekday() + 1) % 7)
    x0, y0, step, size = 40, 170, 16, 13
    rects = []
    for d, lvl in days:
        col = (d - first_sunday).days // 7
        row = (d.weekday() + 1) % 7  # Sunday=0
        rects.append(
            f'<rect x="{x0 + col * step}" y="{y0 + row * step}" width="{size}" '
            f'height="{size}" rx="2" fill="{T["levels"][lvl]}"/>'
        )
    return "\n    ".join(rects)


def stat_block(x, label, value, value_color):
    return f'''<text class="mono" x="{x}" y="100" font-size="11" letter-spacing="2" fill="{T["muted"]}">{label}</text>
    <text class="mono" x="{x}" y="134" font-size="30" font-weight="700" fill="{value_color}">{value}</text>'''


def render(total, current, longest, active_days, days):
    synced = days[-1][0].isoformat()
    blocks = "\n    ".join([
        stat_block(40, "CONTRIBUTIONS / YR", f"{total:,}", T["yellow"]),
        stat_block(280, "CURRENT STREAK", f"{current}d", T["text"]),
        stat_block(520, "LONGEST STREAK", f"{longest}d", T["text"]),
        stat_block(760, "ACTIVE DAYS", str(active_days), T["text"]),
    ])
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 980 344" role="img" aria-label="GitHub activity">
  <style>
    .mono {{ font-family: ui-monospace, 'SF Mono', 'JetBrains Mono', Menlo, Consolas, monospace; }}
    .fade {{ opacity: 0; animation: fade .7s ease forwards; }}
    .f1 {{ animation-delay: .15s }} .f2 {{ animation-delay: .35s }}
    @keyframes fade {{ to {{ opacity: 1 }} }}
    .dot {{ animation: blink 1.6s steps(2, start) infinite; }}
    @keyframes blink {{ 50% {{ opacity: .15 }} }}
    .scan {{ animation: scan 7s linear infinite; }}
    @keyframes scan {{ from {{ transform: translateY(0) }} to {{ transform: translateY(232px) }} }}
  </style>
  <defs>
    <pattern id="hz" width="8" height="8" patternTransform="rotate(45)" patternUnits="userSpaceOnUse">
      <rect width="4" height="8" fill="{T["yellow"]}"/>
    </pattern>
  </defs>

  <path d="M0.5 0.5 H961.5 L979.5 18.5 V343.5 H18.5 L0.5 325.5 Z" fill="{T["panel_fill"]}" stroke="{T["panel_stroke"]}"/>
  <rect x="1" y="1" width="90" height="4" fill="url(#hz)" opacity=".9"/>
  <rect x="840" y="1" width="70" height="2" fill="{T["red"]}"/>

  <circle class="dot" cx="40" cy="39" r="4" fill="{T["yellow"]}"/>
  <text class="mono" x="54" y="44" font-size="13" font-weight="600" letter-spacing="2" fill="{T["yellow"]}">ACTIVITY.SYS</text>
  <text class="mono" x="178" y="44" font-size="12" letter-spacing="1" fill="{T["muted"]}">— NET TELEMETRY · 52W</text>
  <text class="mono" x="940" y="44" font-size="11" letter-spacing="1" fill="{T["muted"]}" text-anchor="end">SYNC {synced}</text>
  <line x1="24" y1="62" x2="956" y2="62" stroke="{T["divider"]}"/>

  <rect class="scan" x="1" y="66" width="978" height="2" fill="{T["cyan"]}" opacity=".07"/>

  <g class="fade f1">
    {blocks}
  </g>
  <line x1="24" y1="152" x2="956" y2="152" stroke="{T["divider"]}"/>

  <g class="fade f2">
    {heatmap_cells(days)}
  </g>

  <line x1="24" y1="306" x2="956" y2="306" stroke="{T["divider"]}"/>
  <text class="mono" x="40" y="326" font-size="10" letter-spacing="2" fill="{T["muted"]}">// SYNCED DAILY VIA GITHUB ACTIONS</text>
  <text class="mono" x="940" y="326" font-size="10" letter-spacing="2" fill="{T["muted"]}" text-anchor="end">NIGHT CITY ⇌ HCMC</text>
</svg>
'''


def main():
    total, days = fetch_contributions()
    current, longest, active_days = compute_stats(days)
    out = REPO_ROOT / "assets" / "activity-panel.svg"
    out.parent.mkdir(exist_ok=True)
    out.write_text(render(total, current, longest, active_days, days), encoding="utf-8")
    print(f"wrote {out}")
    print(f"total={total} current_streak={current} longest_streak={longest} active_days={active_days}")


if __name__ == "__main__":
    main()
