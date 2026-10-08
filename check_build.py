"""
Smoke check run in CI between render_html.py and the GitHub Pages deploy step.
Not a real test suite -- just a last line of defense so a broken build never
silently goes live: if the pipeline threw away all its data (bad nflverse
response, empty schedule, etc.) but still exited 0, this catches it before
deploy instead of after.

Run with: python check_build.py         (the NFL pages)
          python check_build.py --nba   (the NBA section)
"""

import glob
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE_DIR = os.path.join(ROOT, "site")

MIN_INDEX_BYTES = 5_000     # a real Week N page is tens of KB; a near-empty file means something broke
MIN_GAME_PAGES = 1
MIN_HELMET_FILES = 2        # at least one team + its mirrored copy
# the site's icons (logo.py), at its root; every page must link them, the NFL's and the NBA's alike
ICON_FILES = ("favicon.svg", "favicon-32.png", "favicon-dark-32.png", "apple-touch-icon.png", "apple-touch-icon-dark.png")


def fail(message):
    print(f"check_build: FAIL -- {message}")
    sys.exit(1)


def check_icons(pages, where):
    """The icon files are at the site's root, and every one of `pages` links them."""
    missing = [n for n in ICON_FILES if not os.path.isfile(os.path.join(SITE_DIR, n))]
    if missing:
        fail(f"site/ is missing {', '.join(missing)} -- logo.write_icons() should put them there")
    bare = []
    for path in pages:
        with open(path, encoding="utf-8") as f:
            if "favicon.svg" not in f.read(4096 * 4):
                bare.append(os.path.relpath(path, SITE_DIR))
    if bare:
        fail(f"{len(bare)} page(s) in {where} have no favicon links (logo.favicon_links()), e.g. {bare[0]}")


def check_nba():
    """The NBA section (site/nba/, render_nba.py, 2026-10-08), checked on its own (--nba): the workflow
    runs it as a separate step that flags a broken NBA build without holding back the NFL pages."""
    nba = os.path.join(SITE_DIR, "nba")
    for name in ("index.html", "standings.html", "leaders.html"):
        path = os.path.join(nba, name)
        if not os.path.isfile(path) or os.path.getsize(path) < MIN_INDEX_BYTES:
            fail(f"site/nba/{name} is missing or nearly empty")
    pages = glob.glob(os.path.join(nba, "game", "*.html"))
    if len(pages) < MIN_GAME_PAGES:
        fail(f"site/nba/game/ has {len(pages)} page(s), expected at least {MIN_GAME_PAGES}")
    for shared in ("game.css", "game.js"):
        if not os.path.isfile(os.path.join(nba, "game", shared)):
            fail(f"site/nba/game/{shared} is missing -- every game page needs it")
    ball_files = glob.glob(os.path.join(nba, "balls", "*.svg"))
    if len(ball_files) < MIN_HELMET_FILES:
        fail(f"site/nba/balls/ has {len(ball_files)} file(s), expected at least {MIN_HELMET_FILES}")
    check_icons(glob.glob(os.path.join(nba, "**", "*.html"), recursive=True), "site/nba/")
    print(f"check_build: NBA OK -- {len(pages)} game page(s), {len(ball_files)} ball file(s)")


def main():
    if "--nba" in sys.argv[1:]:
        check_nba()
        return
    index_path = os.path.join(SITE_DIR, "index.html")
    if not os.path.isfile(index_path):
        fail(f"{index_path} does not exist")

    size = os.path.getsize(index_path)
    if size < MIN_INDEX_BYTES:
        fail(f"site/index.html is only {size} bytes (expected at least {MIN_INDEX_BYTES}) -- looks empty or broken")

    game_pages = glob.glob(os.path.join(SITE_DIR, "game", "*.html"))
    if len(game_pages) < MIN_GAME_PAGES:
        fail(f"site/game/ has {len(game_pages)} page(s), expected at least {MIN_GAME_PAGES}")

    helmet_files = glob.glob(os.path.join(SITE_DIR, "helmets", "*.svg"))
    if len(helmet_files) < MIN_HELMET_FILES:
        fail(f"site/helmets/ has {len(helmet_files)} file(s), expected at least {MIN_HELMET_FILES}")

    nba = os.path.join(SITE_DIR, "nba") + os.sep
    check_icons([p for p in glob.glob(os.path.join(SITE_DIR, "**", "*.html"), recursive=True) if not p.startswith(nba)], "site/")
    print(f"check_build: OK -- index.html {size} bytes, {len(game_pages)} game page(s), {len(helmet_files)} helmet file(s)")


if __name__ == "__main__":
    main()
