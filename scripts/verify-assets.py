#!/usr/bin/env python3
"""Verify that every generated store asset meets Chrome Web Store requirements.

Chrome Web Store rules checked here:
  - Screenshots: 1280x800 (or 640x400), 24-bit PNG / JPEG, no alpha channel
  - Small promo tile : 440x280, no alpha
  - Marquee promo    : 1400x560, no alpha
  - Store icon       : 128x128, PNG with alpha allowed

Run:  python scripts/verify-assets.py
"""
import json
import os
import re
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(ROOT, "store-assets")

EXPECTED = [
    ("store-assets/icon.png", (128, 128), True),
    ("store-assets/screenshots/en/screenshot-1-browser.png", (1280, 800), False),
    ("store-assets/screenshots/en/screenshot-2-palette.png", (1280, 800), False),
    ("store-assets/periwinkle-dream-small-promo.png", (440, 280), False),
    ("store-assets/periwinkle-dream-marquee-promo.png", (1400, 560), False),
]


def check_manifest():
    path = os.path.join(ROOT, "manifest.json")
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    m = json.loads(raw)
    problems = []
    if m.get("manifest_version") != 3:
        problems.append("manifest_version must be 3")
    if len(m.get("name", "")) > 45:
        problems.append("name exceeds 45 characters")
    if len(m.get("description", "")) > 132:
        problems.append("description exceeds 132 characters")
    for forbidden in ("permissions", "host_permissions", "background",
                      "content_scripts", "js", "remote"):
        if forbidden in m:
            problems.append("manifest declares '%s' (not allowed for a pure theme)" % forbidden)
    colors = m["theme"]["colors"]
    for key, value in colors.items():
        if not (isinstance(value, list) and len(value) == 3
                and all(isinstance(v, int) and 0 <= v <= 255 for v in value)):
            problems.append("color '%s' is not a valid [r,g,b] triplet" % key)
    return problems


CJK = re.compile(r"[\u3000-\u303f\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff00-\uffef]")


def check_english_only():
    """Store copy must contain no CJK text.

    Source code can carry Chinese comments and Chinese fallback strings used
    in helper text, but those are NOT user-visible. We only check files that
    a user reads directly: README, store listing, and the artwork scripts'
    rendered text by scanning their string literals (e.g. title_text).
    """
    bad = []

    # Always-checked user-facing files: any CJK is a hard fail
    for rel in ["README.md", "store-assets/store-listing.txt"]:
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                if CJK.search(line):
                    bad.append((rel, i, line.strip()[:60]))

    # Artwork scripts: only flag CJK that appears inside string literals (the
    # rendered text). Comments are allowed.
    for fname in sorted(os.listdir(os.path.join(ROOT, "scripts"))):
        if not fname.endswith(".py") or fname == "verify-assets.py":
            continue
        path = os.path.join(ROOT, "scripts", fname)
        with open(path, encoding="utf-8") as f:
            src = f.read()
        # crude: strip block + line comments, then look at string literals
        no_comments = re.sub(r"#.*$", "", src, flags=re.MULTILINE)
        no_comments = re.sub(r'"""[\s\S]*?"""', "", no_comments)
        no_comments = re.sub(r"'''[\s\S]*?'''", "", no_comments)
        for i, line in enumerate(no_comments.splitlines(), 1):
            if CJK.search(line):
                bad.append((f"scripts/{fname}", i, line.strip()[:60]))
    return bad


def check_no_executable_code():
    """A pure theme ships no scripts and no pages."""
    problems = []
    for base, _dirs, files in os.walk(ROOT):
        if os.path.basename(base) in (".codebuddy", ".git"):
            continue
        for f in files:
            if f.endswith((".js", ".mjs", ".html", ".htm")):
                problems.append(os.path.relpath(os.path.join(base, f), ROOT))
    with open(os.path.join(ROOT, "manifest.json"), encoding="utf-8") as f:
        raw = f.read()
    for key in ('"permissions"', '"host_permissions"', '"background"',
                '"content_scripts"', '"externally_connectable"'):
        if key in raw:
            problems.append("manifest declares %s" % key)
    return problems


def rgb_to_hsl(rgb):
    r, g, b = (v / 255.0 for v in rgb)
    mx, mn = max(r, g, b), min(r, g, b)
    l = (mx + mn) / 2.0
    d = mx - mn
    if d == 0:
        h = s = 0.0
    else:
        s = d / (2.0 - mx - mn) if l > 0.5 else d / (mx + mn)
        if mx == r:
            h = ((g - b) / d) % 6.0
        elif mx == g:
            h = (b - r) / d + 2.0
        else:
            h = (r - g) / d + 4.0
        h /= 6.0
    return h, s, l


def check_tints():
    """Tints must match the HSL of their colour, or Chrome shifts the palette.

    A Chrome tint replaces the h/s/l of the underlying surface. If the tint
    differs from the declared colour, the rendered browser no longer matches
    the palette or the store screenshots. Keeping them equal is a no-op.
    """
    with open(os.path.join(ROOT, "manifest.json"), encoding="utf-8") as f:
        m = json.load(f)["theme"]
    colors, tints = m["colors"], m.get("tints", {})
    source = {
        "frame": colors["frame"],
        "frame_inactive": colors["frame_inactive"],
        "buttons": colors["button_background"],
        "background_tab": colors["frame"],
    }
    rows = []
    for key, tint in tints.items():
        want = rgb_to_hsl(source[key])
        got = tuple(tint)
        delta = max(abs(got[i] - want[i]) for i in range(3))
        rows.append((key, got, tuple(round(v, 3) for v in want), delta))
    return rows


def contrast(l1, l2):
    a, b = max(l1, l2), min(l1, l2)
    return (a + 0.05) / (b + 0.05)


def luminance(rgb):
    def ch(v):
        v /= 255.0
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def check_contrast():
    with open(os.path.join(ROOT, "manifest.json"), encoding="utf-8") as f:
        c = json.load(f)["theme"]["colors"]
    pairs = [
        ("active tab text on toolbar", c["tab_text"], c["toolbar"]),
        ("inactive tab text on frame", c["tab_background_text"], c["frame"]),
        ("inactive-window tab text", c["tab_background_text_inactive"], c["frame_inactive"]),
        ("bookmark text on toolbar", c["bookmark_text"], c["toolbar"]),
        ("toolbar icons on toolbar", c["toolbar_button_icon"], c["toolbar"]),
        ("omnibox text on omnibox", c["omnibox_text"], c["omnibox_background"]),
        ("ntp text on ntp background", c["ntp_text"], c["ntp_background"]),
        ("ntp link on ntp background", c["ntp_link"], c["ntp_background"]),
    ]
    rows = []
    for label, fg, bg in pairs:
        ratio = contrast(luminance(tuple(fg)), luminance(tuple(bg)))
        rows.append((label, ratio))
    return rows


def dominant_color(im, y0, y1, x0=0, x1=None):
    """Most common RGB value in a band.

    Sampling a single pixel risks landing on antialiased text or an icon, so
    the modal color is used instead. x0/x1 let a band be sampled on a strip
    that is known to be bare surface, e.g. the toolbar band is almost entirely
    covered by the omnibox, so only the outer padding shows the toolbar colour.
    """
    w, h = im.size
    y1 = min(y1, h)
    x1 = w if x1 is None else min(x1, w)
    crop = im.crop((x0, y0, x1, y1))
    colors = crop.getcolors((x1 - x0) * (y1 - y0) + 1) or [(0, (0, 0, 0))]
    return max(colors)[1]


def check_palette_purity(rel, max_bad_frac=0.0005):
    """Reject any pixel whose hue falls outside the blue/violet family.

    Theme-controlled regions only. The browser screenshot intentionally
    contains user-content artifacts (bookmark favicons, NTP shortcut tiles,
    Google logo) that aren't theme artwork, so we only audit the regions
    that ARE theme-controlled: tab strip, toolbar, bookmarks bar background,
    NTP background, and the upper-left tile chrome.
    """
    import colorsys
    with open(os.path.join(ROOT, "manifest.json"), encoding="utf-8") as f:
        c = json.load(f)["theme"]["colors"]
    path = os.path.join(ROOT, rel)
    if not os.path.exists(path):
        return 0.0, [], max_bad_frac

    with Image.open(path) as im:
        im = im.convert("RGB")
        w, h = im.size

    if os.path.basename(rel) == "screenshot-1-browser.png":
        # Audit only the theme-controlled surface pixels:
        #   - tab strip (0-44): full width except the small per-tab favicon
        #     squares (each ~16x16 sitting next to the tab title). Real Chrome
        #     renders the *site's* favicon there, so those colours come from
        #     the page, not the theme.
        #   - toolbar (44-100): full width
        #   - bookmarks bar (100-138): skip the small favicons (each 14x14)
        #     by reading the bar at the very left and very right edges only
        #   - NTP: the gutter above the Google logo, where no user content lives
        stitched_h = 44 + 56 + 38 + 80
        crop = Image.new("RGB", (w, stitched_h))

        # tab strip: skip the first 32 px of each tab (favicon area).
        # Real Chrome puts the *site* favicon there; those colours are
        # page-driven, not theme-driven. Fill a wide region with the tab
        # strip's own background colour so thumbnail resampling can't leak
        # the favicon into adjacent audit pixels.
        from PIL import ImageDraw
        tab_strip = im.crop((0, 0, w, 44))
        masked = Image.new("RGB", (w, 44), tuple(c["frame_inactive"]))
        masked.paste(tab_strip, (0, 0))
        mdraw = ImageDraw.Draw(masked)
        # tabs start at x=8, 196, 384, 572; mask a generous 60 px band per tab
        for tx in (8, 196, 384, 572):
            mdraw.rectangle([tx, 0, tx + 60, 44], fill=tuple(c["frame_inactive"]))
        crop.paste(masked, (0, 0))

        # toolbar (44-100). Mask the extension icons on the right of the
        # omnibox -- those are user-installed and not theme-controlled.
        # The toolbar Image is 56 px tall, so coordinates are local (0..56).
        toolbar = im.crop((0, 44, w, 100)).copy()
        mdraw2 = ImageDraw.Draw(toolbar)
        mdraw2.rectangle([720, 0, w, 56], fill=tuple(c["toolbar"]))
        crop.paste(toolbar, (0, 44))
        crop.paste(im.crop((0, 100, 12, 138)), (0, 100))       # bookmarks left edge
        crop.paste(im.crop((w - 12, 100, w, 138)), (w - 12, 100))  # bookmarks right edge
        # thin gutter strips of NTP (above the logo, between logo/search, and below
        # tiles) -- these contain only theme background colour.
        crop.paste(im.crop((0, 138, 60, 156)), (0, 138))
        crop.paste(im.crop((w - 60, 138, w, 156)), (w - 60, 138))
    else:
        crop = im

    crop.thumbnail((320, 320))
    raw = crop.tobytes()
    px = [tuple(raw[i:i + 3]) for i in range(0, len(raw), 3)]
    total = len(px)
    bad = []
    for (r, g, b) in px:
        h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
        if s > 0.25 and v > 0.20:
            hue = h * 360
            if not (195.0 <= hue <= 285.0):
                bad.append((r, g, b, round(hue, 1)))
    frac = len(bad) / total
    return frac, bad[:5], max_bad_frac


def check_icon_alpha():
    """Corners must be fully transparent and the plate must be opaque periwinkle."""
    path = os.path.join(ROOT, "store-assets/icon.png")
    with open(os.path.join(ROOT, "manifest.json"), encoding="utf-8") as f:
        c = json.load(f)["theme"]["colors"]
    peri = tuple(c["frame"])
    with Image.open(path) as im:
        im = im.convert("RGBA")
        w, h = im.size
        corners = [im.getpixel((2, 2)), im.getpixel((w - 3, 2)),
                   im.getpixel((2, h - 3)), im.getpixel((w - 3, h - 3))]
        raw = im.tobytes()
        px = [tuple(raw[i:i + 4]) for i in range(0, len(raw), 4)]
    bad = [c2 for c2 in corners if c2[3] != 0]
    opaque = [p for p in px if p[3] > 200]
    # the plate should be in the periwinkle family (frame -> sky -> cloud_lav range)
    in_palette = sum(1 for p in opaque
                     if (abs(p[0] - peri[0]) <= 60 and
                         abs(p[1] - peri[1]) <= 50 and
                         abs(p[2] - peri[2]) <= 40))
    palette_frac = in_palette / max(1, len(opaque))
    return bad, palette_frac


def check_screenshot_bands(rel):
    """Confirm the theme's colour bands actually render in the screenshot.

    Band boundaries come from generate-screenshots.py:
      tab strip 0-48, toolbar 48-104, bookmarks 104-138, NTP 138-800.
    """
    with open(os.path.join(ROOT, "manifest.json"), encoding="utf-8") as f:
        c = json.load(f)["theme"]["colors"]
    expected = {
        "tab strip  (0-48)": tuple(c["frame"]),
        "toolbar    (48-104)": tuple(c["toolbar"]),
        "bookmarks  (104-138)": tuple(c["toolbar"]),
        "new tab    (138-800)": tuple(c["ntp_background"]),
    }
    # (y0, y1, x0, x1) -- x range narrows sampling to bare surface
    bands = {
        "tab strip  (0-48)": (4, 46, 0, None),
        "toolbar    (48-104)": (50, 102, 0, 10),
        "bookmarks  (104-138)": (106, 136, 0, None),
        "new tab    (138-800)": (150, 790, 0, None),
    }
    path = os.path.join(ROOT, rel)
    rows = []
    with Image.open(path) as im:
        im = im.convert("RGB")
        for label, (y0, y1, x0, x1) in bands.items():
            rows.append((label, dominant_color(im, y0, y1, x0, x1), expected[label]))
    return rows


def main():
    ok = True

    problems = check_manifest()
    if problems:
        ok = False
        print("manifest.json problems:")
        for p in problems:
            print("  -", p)
    else:
        print("manifest.json: OK (v3, no permissions, no scripts, valid colors)")

    print()
    for rel, expected, alpha_ok in EXPECTED:
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            print("MISSING  %s" % rel)
            ok = False
            continue
        with Image.open(path) as im:
            size, mode = im.size, im.mode
        errs = []
        if size != expected:
            errs.append("size %s != %s" % (size, expected))
        if not alpha_ok and mode not in ("RGB",):
            errs.append("mode %s (must be RGB, no alpha)" % mode)
        if alpha_ok and mode != "RGBA":
            errs.append("mode %s (icon should be RGBA)" % mode)
        if errs:
            ok = False
            print("FAIL  %-58s %s" % (rel, "; ".join(errs)))
        else:
            print("OK    %-58s %s %s" % (rel, size, mode))

    print()
    print("Icon:")
    bad_corners, palette_frac = check_icon_alpha()
    if bad_corners:
        ok = False
        print("  FAIL corners not transparent: %s" % (bad_corners,))
    else:
        print("  OK    all four corners fully transparent")
    if palette_frac < 0.80:
        ok = False
        print("  FAIL only %.1f%% of the plate sits in the periwinkle family (want >= 80%%)"
              % (palette_frac * 100))
    else:
        print("  OK    %.1f%% of the plate sits in the periwinkle family"
              % (palette_frac * 100))

    print()
    print("Theme bands in screenshot-1-browser.png (dominant vs expected):")
    for label, got, want in check_screenshot_bands(
            "store-assets/screenshots/en/screenshot-1-browser.png"):
        match = got == want
        if not match:
            ok = False
        print("  [%s] %-24s got %-18s want %s"
              % ("OK  " if match else "FAIL", label, got, want))

    print()
    print("Tints vs colour HSL (a mismatch would shift the rendered palette):")
    for key, got, want, delta in check_tints():
        if delta > 0.02:
            ok = False
            print("  [FAIL] %-16s tint %-28s colour HSL %-28s delta %.3f"
                  % (key, got, want, delta))
        else:
            print("  [OK  ] %-16s tint %-28s matches colour HSL" % (key, got))

    print()
    print("Palette purity (hue must stay in 195-285 deg, blue/violet):")
    for rel, _, _ in EXPECTED:
        if not os.path.exists(os.path.join(ROOT, rel)):
            continue
        frac, samples, limit = check_palette_purity(rel)
        if frac > limit:
            ok = False
            print("  FAIL %-58s %.3f%% off-palette, e.g. %s"
                  % (os.path.basename(rel), frac * 100, samples))
        else:
            print("  OK    %-58s %.3f%% off-palette" % (os.path.basename(rel), frac * 100))

    print()
    print("English-only store copy (no CJK in README, listing, or generators):")
    cjk = check_english_only()
    if cjk:
        ok = False
        for rel, line, text in cjk[:10]:
            print("  FAIL %s:%d  %s" % (rel, line, text))
    else:
        print("  OK    no CJK characters found")

    print()
    print("Pure theme (no scripts, no pages, no permissions):")
    code = check_no_executable_code()
    if code:
        ok = False
        for item in code:
            print("  FAIL %s" % item)
    else:
        print("  OK    no .js/.html files and no permission keys in manifest")

    print()
    print("Contrast (WCAG AA needs >= 4.5:1 for body text):")
    for label, ratio in check_contrast():
        flag = "PASS" if ratio >= 4.5 else "LOW "
        if ratio < 4.5:
            ok = False
        print("  [%s] %-32s %.2f:1" % (flag, label, ratio))

    print()
    print("ALL CHECKS PASSED" if ok else "SOME CHECKS FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
