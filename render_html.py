"""
V0 output: dumps data/matchups.json as a completely unstyled HTML page.
No layout, no hierarchy, no design decisions -- that's intentional, this
is just proof the pipeline works end to end and is viewable in a browser.
Jason is handling the real organization/design pass on top of this later.

Run with: python render_html.py   (after build_data.py has run)
Outputs: site/index.html
"""

import json
import os

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


def main():
    with open(DATA_PATH) as f:
        data = json.load(f)

    parts = [
        "<!doctype html><html><head><meta charset='utf-8'>",
        "<title>At a Glance -- v0 raw data</title></head><body>",
        f"<p><i>Generated {data.get('generated_at_utc')}</i></p>",
    ]

    if data.get("warnings"):
        parts.append("<div style='background:#fee;padding:8px;margin-bottom:16px'>")
        parts.append(f"<b>{len(data['warnings'])} warning(s) from this run:</b><ul>")
        for w in data["warnings"]:
            parts.append(f"<li>{w}</li>")
        parts.append("</ul></div>")

    for m in data.get("matchups", []):
        parts.append("<hr>")
        parts.append(f"<h2>{m['away']['team']} @ {m['home']['team']}</h2>")
        parts.append(dict_to_html({
            "date_utc": m["date_utc"],
            "venue": m["venue"],
            "city": m["city"],
            "state": m["state"],
            "indoor": m["indoor"],
            "networks": m["networks"],
            "weather": m["weather"],
        }))
        parts.append("<h3>Away</h3>")
        parts.append(dict_to_html(m["away"]))
        parts.append("<h3>Home</h3>")
        parts.append(dict_to_html(m["home"]))

    parts.append("</body></html>")

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        f.write("".join(parts))
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
