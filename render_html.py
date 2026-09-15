"""
V0 output: dumps data/matchups.json as a completely unstyled HTML page.
No layout, no hierarchy, no design decisions -- that's intentional, this
is just proof the pipeline works end to end and is viewable in a browser.
Jason is handling the real organization/design pass on top of this later.

Run with: python render_html.py   (after build_data.py has run)
Outputs: site/index.html

2026-09-16 fix: updated field names to match the nflverse-based
build_data.py output (gameday/gametime/roof/surface instead of the old
ESPN-based date_utc/city/state, which no longer exist and were causing a
KeyError crash here). Also switched every direct dict[key] access to
.get() and wrapped each matchup in try/except, so a schema mismatch on
ONE matchup (or one field) prints a visible error inline instead of
taking down the whole page -- this class of bug (render code assuming
fields that build_data.py stopped producing) is exactly what silently
crashed this script last time, so being defensive here specifically
matters.
"""

import json
import os
import traceback

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "matchups.json")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "site", "index.html")


def dict_to_html(d, level=0):
    if isinstance(d, dict):
        rows = "".join(f"<li><b>{k}:</b> {dict_to_html(v, level+1)}</li>" for k, v in d.items())
        return f"<ul>{rows}</ul>"
    if isinstance(d, list):
        if not d:
            return "<i>(none)</i>"
        rows = "".join(f"<li>{dict_to_html(item, level+1)}</li>" for item in d)
        return f"<ol>{rows}</ol>"
    return str(d)


def render_matchup(m):
    away_team = (m.get("away") or {}).get("team", "?")
    home_team = (m.get("home") or {}).get("team", "?")
    parts = ["<hr>", f"<h2>{away_team} @ {home_team}</h2>"]
    parts.append(dict_to_html({
        "gameday": m.get("gameday"),
        "gametime": m.get("gametime"),
        "venue": m.get("venue"),
        "roof": m.get("roof"),
        "indoor": m.get("indoor"),
        "surface": m.get("surface"),
        "networks": m.get("networks"),
        "weather": m.get("weather"),
    }))
    parts.append("<h3>Away</h3>")
    parts.append(dict_to_html(m.get("away") or {}))
    parts.append("<h3>Home</h3>")
    parts.append(dict_to_html(m.get("home") or {}))
    return parts


def main():
    with open(DATA_PATH) as f:
        data = json.load(f)

    parts = [
        "<!doctype html><html><head><meta charset='utf-8'>",
        "<title>At a Glance -- v0 raw data</title></head><body>",
        f"<p><i>Generated {data.get('generated_at_utc')} -- season {data.get('season')}, week {data.get('week')}</i></p>",
    ]

    if data.get("warnings"):
        parts.append("<div style='background:#fee;padding:8px;margin-bottom:16px'>")
        parts.append(f"<b>{len(data['warnings'])} warning(s) from this run:</b><ul>")
        for w in data["warnings"]:
            parts.append(f"<li>{w}</li>")
        parts.append("</ul></div>")

    matchups = data.get("matchups", [])
    if not matchups:
        parts.append("<p><b>No matchups in the data file.</b> Either the week filter in "
                      "build_data.py didn't match any games, or the season has no games "
                      "scheduled right now -- check the warnings above and data/matchups.json directly.</p>")

    for m in matchups:
        try:
            parts.extend(render_matchup(m))
        except Exception:
            parts.append("<hr><div style='background:#fee;padding:8px'>"
                          f"<b>Failed to render one matchup</b><pre>{traceback.format_exc()}</pre></div>")

    parts.append("</body></html>")

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        f.write("".join(parts))
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
