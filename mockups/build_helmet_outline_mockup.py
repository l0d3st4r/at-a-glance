"""
Helmet outline mockup (2026-09-24) -- NOT part of the live build.

Builds mockups/helmet-outlines.html: every team's helmet, straight from
helmets.helmet_svg(), with a white outline added so dark shells (CHI, ATL,
LV, ...) don't sink into the dark-mode background. The page has live
controls for the outline style and width, so the options can be compared
before anything changes in helmets.py.

The outline is an SVG filter inside each helmet file (no CSS needed, so it
works anywhere the <img> goes):
  * "Outline"  -- a ring around the whole helmet's outer edge only. The thin
                  gaps between shell, ear piece and facemask stay see-through.
  * "Sticker"  -- the same ring, but it also fills those gaps with white, so
                  the helmet reads like a die-cut sticker.
  * "Sticker + filled facemask" -- the sticker, plus the facemask's openings
                  filled solid white (a white copy of the facemask's outer
                  shape drawn under the bars).
The viewBox grows by the outline width so the ring never gets cut off, and
the preview grows the <img> by the same ratio so the helmet itself stays the
size it is today.

Run:
    python mockups/build_helmet_outline_mockup.py
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import helmets  # noqa: E402

OUT = os.path.join(ROOT, "mockups", "helmet-outlines.html")

PAGE = r"""<meta charset="utf-8">
<title>Helmet Outlines</title>
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&family=Saira:ital,wdth,wght@1,95,800&display=swap" rel="stylesheet">
<style>
:root{
  --ground:#F3F3F1; --panel:#FFFFFF; --ink:#0B0B0C; --ink-2:rgba(11,11,12,.62); --ink-3:rgba(11,11,12,.4);
  --line:rgba(11,11,12,.12); --seg:#E6E6E3; --seg-on:#FFFFFF;
  /* the app's own surfaces, fixed regardless of the viewer's theme */
  --app-dark:#0B0B0C; --app-dark-tile:#161618; --app-dark-line:rgba(255,255,255,.12); --app-dark-ink:#F2F2F2;
  --app-light:#FFFFFF; --app-light-line:rgba(0,0,0,.12); --app-light-ink:#000;
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){color-scheme:dark;
    --ground:#050506; --panel:#111113; --ink:#F2F2F2; --ink-2:rgba(242,242,242,.62); --ink-3:rgba(242,242,242,.4);
    --line:rgba(255,255,255,.12); --seg:#1C1C1F; --seg-on:#34343A}
}
:root[data-theme="dark"]{color-scheme:dark;
  --ground:#050506; --panel:#111113; --ink:#F2F2F2; --ink-2:rgba(242,242,242,.62); --ink-3:rgba(242,242,242,.4);
  --line:rgba(255,255,255,.12); --seg:#1C1C1F; --seg-on:#34343A}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--ink);font:400 15px/1.5 Inter,system-ui,-apple-system,sans-serif;
  -webkit-font-smoothing:antialiased;padding-inline:16px;padding-block:40px 64px}
.wrap{max-width:1040px;margin:0 auto;display:flex;flex-direction:column;gap:28px}
.eyebrow{font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-3);margin:0 0 6px}
h1{font-family:Saira,Inter,sans-serif;font-style:italic;font-weight:800;font-variation-settings:'wdth' 95;
  font-size:clamp(34px,5vw,52px);line-height:1;letter-spacing:.01em;margin:0;text-wrap:balance}
.lede{max-width:62ch;color:var(--ink-2);margin:10px 0 0}
.controls{display:flex;flex-wrap:wrap;gap:16px 28px;align-items:flex-end}
.ctl{display:flex;flex-direction:column;gap:6px}
.ctl-label{font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-3)}
.seg{display:inline-flex;flex-wrap:wrap;padding:3px;border-radius:999px;background:var(--seg);gap:2px}
.seg button{font:500 14px/1 Inter,system-ui,sans-serif;color:var(--ink-2);background:none;border:0;border-radius:999px;
  padding:9px 14px;cursor:pointer;transition:background-color .2s,color .2s}
.seg button[aria-pressed="true"]{background:var(--seg-on);color:var(--ink);box-shadow:0 1px 2px rgba(0,0,0,.12)}
.seg button:focus-visible{outline:2px solid var(--ink);outline-offset:2px}
.hint{font-size:13px;color:var(--ink-2);margin:0;max-width:62ch}
.board{border-radius:24px;padding:20px;display:flex;flex-direction:column;gap:14px}
.board.dark{background:var(--app-dark);color:var(--app-dark-ink)}
.board.light{background:var(--app-light);color:var(--app-light-ink);box-shadow:inset 0 0 0 1px var(--line)}
.board h2{margin:0;font-size:13px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;opacity:.6}
/* the four stand-in "game tiles" use the app's tile look */
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:10px}
.tile{display:flex;align-items:center;justify-content:space-between;padding:14px 18px;border-radius:20px;border:1px solid var(--app-dark-line);background:var(--app-dark-tile)}
.light .tile{border-color:var(--app-light-line);background:var(--app-light)}
.side{display:flex;flex-direction:column;align-items:center;gap:4px;width:64px}
.abbr{font-family:Saira,Inter,sans-serif;font-style:italic;font-weight:800;font-variation-settings:'wdth' 95;font-size:20px;line-height:24px;letter-spacing:.02em}
.mid{font-weight:700;font-size:18px;font-variant-numeric:tabular-nums}
.mid small{font-weight:400;font-size:11px;opacity:.62;margin-left:3px}
.hbox{width:48px;height:48px;display:flex;align-items:center;justify-content:center}
.hbox img{display:block;flex:none}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(72px,1fr));gap:12px 8px}
.cell{display:flex;flex-direction:column;align-items:center;gap:4px;font-size:12px;font-weight:500;opacity:.9}
.zoom{display:flex;flex-wrap:wrap;gap:12px}
.zoom .z{flex:1 1 180px;display:flex;flex-direction:column;align-items:center;gap:6px;padding:16px;border-radius:20px;background:var(--app-dark-tile);border:1px solid var(--app-dark-line);font-size:13px}
.zoom .hbox{width:140px;height:140px}
</style>
<div class="wrap">
  <header>
    <p class="eyebrow">At A Glance · Mockup</p>
    <h1>Helmet outlines</h1>
    <p class="lede">A white outline built into each helmet file, so dark helmets stand out on the dark-mode background. Try the styles and widths below. The helmet art stays the same size; only the outline is added around it.</p>
  </header>

  <div class="controls">
    <div class="ctl"><span class="ctl-label" id="l-style">Style</span>
      <div class="seg" role="group" aria-labelledby="l-style">
        <button type="button" id="st-off" data-style="off" aria-pressed="false">No outline</button>
        <button type="button" id="st-outline" data-style="outline" aria-pressed="false">Outline</button>
        <button type="button" id="st-sticker" data-style="sticker" aria-pressed="false">Sticker</button>
        <button type="button" id="st-filled" data-style="filled" aria-pressed="true">Sticker + filled facemask</button>
      </div></div>
    <div class="ctl"><span class="ctl-label" id="l-width">Width at 48px</span>
      <div class="seg" role="group" aria-labelledby="l-width">
        <button type="button" id="w-1" data-w="1.6" aria-pressed="false">Thin · ¾px</button>
        <button type="button" id="w-2" data-w="2.5" aria-pressed="true">Medium · 1¼px</button>
        <button type="button" id="w-3" data-w="3.6" aria-pressed="false">Bold · 1¾px</button>
      </div></div>
  </div>
  <p class="hint" id="hint"></p>

  <section class="board dark" aria-label="Dark mode">
    <h2>Dark mode · game tiles</h2>
    <div class="tiles" id="tiles-dark"></div>
  </section>

  <section class="board dark" aria-label="Close-up">
    <h2>Close-up · the darkest helmets</h2>
    <div class="zoom" id="zoom"></div>
  </section>

  <section class="board dark" aria-label="All teams on dark">
    <h2>All 32 teams · dark</h2>
    <div class="grid" id="grid-dark"></div>
  </section>

  <section class="board light" aria-label="Light mode">
    <h2>Light mode · game tiles</h2>
    <p class="hint" style="color:inherit;opacity:.62">White on white disappears, so light mode looks the same as today.</p>
    <div class="tiles" id="tiles-light"></div>
  </section>
</div>
<!--DATA-->
<script>
(function () {
  var H = window.HELMETS, state = { style: 'filled', w: 2.5 };
  var GAMES = [['CHI', 'ATL', '1:00', 'PM'], ['LV', 'NO', '4:25', 'PM'], ['BAL', 'PIT', '8:20', 'PM'], ['JAX', 'NYJ', '1:00', 'PM']];
  var ZOOM = ['CHI', 'ATL', 'LV', 'BAL'];
  var HINTS = {
    off: 'Today’s helmets. The dark shells blend into the background.',
    outline: 'A ring around the outer edge only. The small gaps between the shell, ear piece and facemask stay dark.',
    sticker: 'The ring also fills the small gaps between parts with white, like a die-cut sticker.',
    filled: 'The sticker, with every opening in the facemask filled solid white.'
  };
  // Adds the outline filter to one helmet SVG string. r = outline width in helmet units (the art is 100 wide).
  function outlined(svg, style, r) {
    var pad = style === 'off' ? 0 : Math.ceil(r + 1);
    if (!pad) return { svg: svg, scale: 1 };
    var v = (-pad) + ' ' + (-pad) + ' ' + (100 + 2 * pad) + ' ' + (100 + 2 * pad);
    var ring = style !== 'outline'
      ? '<feMorphology in="SourceAlpha" operator="dilate" radius="' + r + '" result="ring"/>'
      // outer edge only: grow the helmet, then cut out a copy with its small gaps closed
      : '<feMorphology in="SourceAlpha" operator="dilate" radius="' + r + '" result="grown"/>' +
        '<feMorphology in="SourceAlpha" operator="dilate" radius="5" result="c1"/>' +
        '<feMorphology in="c1" operator="erode" radius="5" result="closed"/>' +
        '<feComposite in="grown" in2="closed" operator="out" result="ring"/>';
    var filter = '<filter id="ol" x="-20%" y="-20%" width="140%" height="140%" color-interpolation-filters="sRGB">' + ring +
      '<feFlood flood-color="#fff"/><feComposite in2="ring" operator="in" result="white"/>' +
      '<feMerge><feMergeNode in="white"/><feMergeNode in="SourceGraphic"/></feMerge></filter>';
    svg = svg.replace('viewBox="0 0 100 100"', 'viewBox="' + v + '"')
             .replace('</defs>', filter + '</defs>')
             .replace(/<g( transform="[^"]*")?>/, function (m) { return '<g filter="url(#ol)">' + m; })
             .replace('</g></svg>', '</g></g></svg>');
    return { svg: svg, scale: (100 + 2 * pad) / 100 };
  }
  function img(team, mirrored, size) {
    var o = outlined(H[team][(mirrored ? 1 : 0) + (state.style === 'filled' ? 2 : 0)], state.style, state.w), px = Math.round(size * o.scale * 10) / 10;
    return '<span class="hbox" style="width:' + size + 'px;height:' + size + 'px"><img alt="" width="' + px + '" height="' + px +
      '" src="data:image/svg+xml;charset=utf-8,' + encodeURIComponent(o.svg) + '"></span>';
  }
  function tile(g) {
    return '<div class="tile"><div class="side">' + img(g[0], false, 48) + '<span class="abbr">' + g[0] + '</span></div>' +
      '<div class="mid">' + g[2] + '<small>' + g[3] + ' ET</small></div>' +
      '<div class="side">' + img(g[1], true, 48) + '<span class="abbr">' + g[1] + '</span></div></div>';
  }
  function render() {
    var tiles = GAMES.map(tile).join('');
    document.getElementById('tiles-dark').innerHTML = tiles;
    document.getElementById('tiles-light').innerHTML = tiles;
    document.getElementById('zoom').innerHTML = ZOOM.map(function (t) { return '<div class="z">' + img(t, false, 140) + '<span class="abbr">' + t + '</span></div>'; }).join('');
    document.getElementById('grid-dark').innerHTML = Object.keys(H).map(function (t) {
      return '<div class="cell">' + img(t, false, 48) + '<span>' + t + '</span></div>';
    }).join('');
    document.getElementById('hint').textContent = HINTS[state.style];
    [].forEach.call(document.querySelectorAll('[data-style]'), function (b) { b.setAttribute('aria-pressed', String(b.dataset.style === state.style)); });
    [].forEach.call(document.querySelectorAll('[data-w]'), function (b) {
      b.setAttribute('aria-pressed', String(+b.dataset.w === state.w));
      b.disabled = state.style === 'off';
    });
  }
  document.addEventListener('click', function (e) {
    var b = e.target.closest('button');
    if (!b) return;
    if (b.dataset.style) state.style = b.dataset.style;
    if (b.dataset.w) state.w = +b.dataset.w;
    render();
  });
  render();
})();
</script>
"""


# The facemask path's first sub-path is its outer edge; the rest are the openings between the bars.
MASK_OUTER = helmets.MASK_PATH.split(" Z ")[0] + " Z"


def filled_mask(svg):
    """Draw the facemask's outer shape in white right under the facemask, filling its openings."""
    mask = f'<path d="{helmets.MASK_PATH}"'
    if mask not in svg:
        raise SystemExit("facemask path not found in helmet SVG")
    return svg.replace(mask, f'<path d="{MASK_OUTER}" fill="#fff" transform="translate(47.641 42.126)"/>' + mask, 1)


def main():
    data = {t: [helmets.helmet_svg(t), helmets.helmet_svg(t, mirrored=True),
                filled_mask(helmets.helmet_svg(t)), filled_mask(helmets.helmet_svg(t, mirrored=True))]
            for t in sorted(helmets.TEAM_COLORS)}
    blob = "<script>window.HELMETS = " + json.dumps(data).replace("</", "<\\/") + ";</script>"
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(PAGE.replace("<!--DATA-->", blob))
    print(f"Wrote {OUT} ({os.path.getsize(OUT) // 1024} KB)")


if __name__ == "__main__":
    main()
