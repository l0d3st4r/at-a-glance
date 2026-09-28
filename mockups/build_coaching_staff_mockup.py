"""
Coaching staff mockup (2026-09-28) -- NOT part of the live build.

Builds mockups/coaching-staff.html: one self-contained page of phone frames, each running a
real rendered game page (its own markup, CSS and script) opened straight to a team page, so
the new staff row on the Overview card (head coach + offensive/defensive play-callers, from
coaches.py) can be judged in place, next to everything else on the card.

The four teams cover the four cases:
  * DAL -- head coach calls the offense, and the longest name in the league appears twice
           (Schottenheimer), so it's the worst case for fitting three columns on a phone
  * DEN -- head coach (Payton) calls neither side's plays this year; OC Davis Webb does
  * BAL -- head coach (Minter) calls the defense
  * NYG -- head coach calls neither side (both coordinators call)

Controls at the top switch the theme, the phone size, and the layout:
  * A "Columns" -- what's built: three columns under the next-game row
  * B "Rows"    -- the alternative: one line each, label left and name right, which never
                   has to wrap a name but repeats the head coach's name on its own line
Option B is CSS injected into the frames only; the live build is option A.

Each frame loads from a blob: URL ending in #/away-team or #/home-team -- the page's own
hash routing then opens that team page, same as tapping the team card. Helmet images are
inlined as data: URIs so the file opens anywhere.

Run after a normal build (so site/ exists):
    python build_data.py && python render_html.py
    python mockups/build_coaching_staff_mockup.py
"""

import base64
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
OUT = os.path.join(ROOT, "mockups", "coaching-staff.html")

# (label, game page, which team page, what it shows)
FRAMES = [
    ("DAL", "2026_04_DAL_HOU", "away", "HC calls the offense · longest name (worst case)"),
    ("DEN", "2026_04_DEN_SF", "away", "HC calls neither side · OC Davis Webb calls the offense"),
    ("BAL", "2026_04_TEN_BAL", "home", "HC calls the defense"),
    ("NYG", "2026_04_ARI_NYG", "home", "HC calls neither side"),
]

# Option B, injected into each frame's #p1-css when the Rows layout is picked.
ROWS_CSS = """
html[data-mock-layout=rows] .ov-staff{display:flex;flex-direction:column;gap:5px}
html[data-mock-layout=rows] .ov-coach{flex-direction:row;justify-content:space-between;align-items:baseline;gap:10px}
html[data-mock-layout=rows] .ov-coach-lbl{font-size:10px;white-space:nowrap}
html[data-mock-layout=rows] .ov-coach-name{font-size:13px;text-align:right}
"""

# Runs inside each frame: applies the parent page's theme/layout picks, which ride on the
# iframe's name (window.name) since a blob: URL can't carry a query string.
FRAME_JS = """
(function(){try{var o=JSON.parse(window.name||'{}');
if(o.theme)document.documentElement.setAttribute('data-theme',o.theme);
if(o.layout)document.documentElement.setAttribute('data-mock-layout',o.layout);}catch(e){}})();
"""

SHELL = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Coaching Staff Mockup</title>
<style>
:root{--bg:#f3f3f1;--text:#1a1a1a;--text-2:#666;--frame:#1a1a1a;--pill:#fff;--pill-on:#1a1a1a;--pill-on-text:#fff;--line:#ddd}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#111;--text:#eee;--text-2:#999;--frame:#444;--pill:#222;--pill-on:#eee;--pill-on-text:#111;--line:#333}}
:root[data-theme=dark]{--bg:#111;--text:#eee;--text-2:#999;--frame:#444;--pill:#222;--pill-on:#eee;--pill-on-text:#111;--line:#333}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:14px/1.45 Inter,system-ui,-apple-system,sans-serif;padding:24px 16px 48px}
h1{font-size:20px;margin:0 0 4px}
.lede{color:var(--text-2);margin:0 0 18px;max-width:760px}
.controls{display:flex;flex-wrap:wrap;gap:14px 22px;margin-bottom:22px}
.ctl{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.ctl > span{font-size:11px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--text-2)}
.seg{display:inline-flex;border:1px solid var(--line);border-radius:999px;overflow:hidden;background:var(--pill)}
.seg button{border:0;background:none;color:var(--text);font:inherit;font-size:13px;padding:6px 12px;cursor:pointer}
.seg button[aria-pressed=true]{background:var(--pill-on);color:var(--pill-on-text)}
.frames{display:flex;flex-wrap:wrap;gap:28px 24px;align-items:flex-start}
figure{margin:0;display:flex;flex-direction:column;gap:8px;max-width:100%}
.phone{border:6px solid var(--frame);border-radius:28px;overflow:hidden;background:#fff;max-width:calc(100vw - 32px)}
.phone iframe{display:block;border:0}
figcaption b{display:block;font-size:14px}
figcaption span{color:var(--text-2);font-size:12px}
</style></head><body>
<h1>Overview card: coaching staff</h1>
<p class="lede">Head coach plus who actually calls each side's plays, under the next-game row. The tag by each
label says whether that's the head coach (HC) or a coordinator (OC / DC). These are the real rendered pages; swipe
or scroll inside a phone as usual. <b>A (Columns)</b> is what's built on the branch; <b>B (Rows)</b> is an alternative.</p>
<div class="controls">
  <div class="ctl"><span>Layout</span><div class="seg" data-ctl="layout">
    <button data-v="cols" aria-pressed="true">A · Columns</button><button data-v="rows" aria-pressed="false">B · Rows</button></div></div>
  <div class="ctl"><span>Theme</span><div class="seg" data-ctl="theme">
    <button data-v="light" aria-pressed="true">Light</button><button data-v="dark" aria-pressed="false">Dark</button></div></div>
  <div class="ctl"><span>Phone</span><div class="seg" data-ctl="size">
    <button data-v="360x740" aria-pressed="false">360</button><button data-v="375x667" aria-pressed="false">375 (SE)</button>
    <button data-v="390x844" aria-pressed="true">390</button><button data-v="430x932" aria-pressed="false">430</button></div></div>
</div>
<div class="frames" id="frames"></div>
<!--MOCK_DATA-->
<script>
(function(){
  var state = {layout:'cols', theme:'light', size:'390x844'};
  var urls = {};
  function url(f){ if(!urls[f.key]) urls[f.key] = URL.createObjectURL(new Blob([MOCK_PAGES[f.key]], {type:'text/html'})); return urls[f.key] + '#/' + f.which + '-team'; }
  function render(){
    var wh = state.size.split('x'), w = +wh[0], h = +wh[1];
    var box = document.getElementById('frames'); box.innerHTML = '';
    MOCK_FRAMES.forEach(function(f){
      var fig = document.createElement('figure');
      var ph = document.createElement('div'); ph.className = 'phone';
      var fr = document.createElement('iframe'); fr.width = w; fr.height = h; fr.title = f.label + ' team page';
      fr.name = JSON.stringify({theme: state.theme, layout: state.layout});
      fr.src = url(f);
      ph.appendChild(fr); fig.appendChild(ph);
      var cap = document.createElement('figcaption');
      cap.innerHTML = '<b></b><span></span>'; cap.firstChild.textContent = f.label; cap.lastChild.textContent = f.note;
      fig.appendChild(cap); box.appendChild(fig);
    });
  }
  document.querySelectorAll('.seg').forEach(function(seg){
    seg.addEventListener('click', function(e){
      var b = e.target.closest('button'); if(!b) return;
      state[seg.dataset.ctl] = b.dataset.v;
      seg.querySelectorAll('button').forEach(function(x){ x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
      if (seg.dataset.ctl === 'theme') document.documentElement.setAttribute('data-theme', b.dataset.v);
      render();
    });
  });
  render();
})();
</script>
</body></html>
"""


def read(path):
    with open(os.path.join(SITE, path), encoding="utf-8") as f:
        return f.read()


def helmet_uri(name, cache={}):
    if name not in cache:
        with open(os.path.join(SITE, "helmets", name), "rb") as f:
            cache[name] = "data:image/svg+xml;base64," + base64.b64encode(f.read()).decode()
    return cache[name]


def dress(html):
    html = re.sub(r'(["\'])\.\./helmets/([^"\']+\.svg)\1', lambda m: m.group(1) + helmet_uri(m.group(2)) + m.group(1), html)
    html, n = re.subn(r"(<style id='p1-css'>.*?)(</style>)", lambda m: m.group(1) + ROWS_CSS + m.group(2), html, count=1, flags=re.S)
    if not n:
        raise SystemExit("game page has no #p1-css -- has the markup changed?")
    if 'class="ov-staff"' not in html:
        raise SystemExit("no staff row on the team pages -- build from the branch with coaches.py")
    # FRAME_JS goes after the page's own theme script so the mockup's theme pick wins
    return html.replace("</head>", f"<script>{FRAME_JS}</script></head>", 1)


def js_string(s):
    return json.dumps(s).replace("</", "<\\/")


def main():
    pages, frames = {}, []
    for label, game, which, note in FRAMES:
        pages[game] = dress(read(f"game/{game}.html"))
        frames.append({"key": game, "which": which, "label": label, "note": note})
    data = ("<script>window.MOCK_PAGES = {" + ",".join(f"{json.dumps(k)}:{js_string(v)}" for k, v in pages.items()) + "};"
            f"window.MOCK_FRAMES = {js_string(json.dumps(frames))};"
            "window.MOCK_FRAMES = JSON.parse(window.MOCK_FRAMES);</script>")
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(SHELL.replace("<!--MOCK_DATA-->", data))
    print(f"Wrote {OUT} ({os.path.getsize(OUT) // 1024} KB)")


if __name__ == "__main__":
    main()
