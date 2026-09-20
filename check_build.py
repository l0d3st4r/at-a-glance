"""
Smoke check run in CI between render_html.py and the GitHub Pages deploy step.
Not a real test suite -- just a last line of defense so a broken build never
silently goes live: if the pipeline threw away all its data (bad nflverse
response, empty schedule, etc.) but still exited 0, this catches it before
deploy instead of after.

Run with: python check_build.py
"""

import glob
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE_DIR = os.path.join(ROOT, "site")

MIN_INDEX_BYTES = 5_000     # a real Week N page is tens of KB; a near-empty file means something broke
MIN_GAME_PAGES = 1
MIN_HELMET_FILES = 2        # at least one team + its mirrored copy


def fail(message):
    print(f"check_build: FAIL -- {message}")
    sys.exit(1)


def main():
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

    print(f"check_build: OK -- index.html {size} bytes, {len(game_pages)} game page(s), {len(helmet_files)} helmet file(s)")


if __name__ == "__main__":
    main()
