# assets

Static files the build copies into `site/` as-is (see `render_html.py`).

- `favicon-32.png` — browser-tab icon for browsers that don't use `favicon.svg`
- `apple-touch-icon.png` — 180×180 icon for iPhone/iPad home screens (dark `#0B0B0C` background, helmet at 78%)

Both are rendered from `site/favicon.svg`, which the build generates from `helmets.favicon_svg()`
(the gray "unknown" helmet with a thicker white sticker outline). The build has no SVG
rasterizer, so if the favicon artwork changes, re-render these two from the new SVG — e.g. draw
it onto a canvas in a browser at 32×32 (transparent) and 180×180 (on `#0B0B0C`, scaled to 78%)
and save the PNGs here.
