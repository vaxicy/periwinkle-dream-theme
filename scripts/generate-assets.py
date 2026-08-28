#!/usr/bin/env python3
"""Generate Periwinkle Dream Theme icon assets.

Outputs:
  assets/icon-source.png   512x512 master artwork (transparent corners)
  store-assets/icon.png    128x128 store listing icon

All colors are read from manifest.json so the artwork can never drift
away from the installed theme.
"""
import json
import os

from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
STORE = os.path.join(ROOT, "store-assets")
os.makedirs(ASSETS, exist_ok=True)


def load_colors():
    with open(os.path.join(ROOT, "manifest.json"), encoding="utf-8") as f:
        raw = json.load(f)["theme"]["colors"]
    return {k: tuple(v) for k, v in raw.items()}


C = load_colors()
PERI = C["frame"]              # #B1B2FF Periwinkle
SKY = C["frame_inactive"]      # #AAC4FF Soft Sky Blue
CLOUD = C["toolbar"]           # #D2DAFF Cloud Lavender
DREAM = C["ntp_background"]    # #EEF1FF Dream White
LINK = C["ntp_link"]           # #5A63C8 deep periwinkle accent


def vgrad(w, h, stops):
    """Vertical gradient; stops = [(pos0, color0), (pos1, color1), ...]."""
    im = Image.new("RGB", (w, h))
    px = im.load()
    for y in range(h):
        t = y / max(1, h - 1)
        col = stops[-1][1]
        for i in range(len(stops) - 1):
            p0, c0 = stops[i]
            p1, c1 = stops[i + 1]
            if p0 <= t <= p1:
                k = (t - p0) / (p1 - p0) if p1 > p0 else 0.0
                col = tuple(int(c0[j] + (c1[j] - c0[j]) * k) for j in range(3))
                break
        for x in range(w):
            px[x, y] = col
    return im


def soft_glow(im, cx, cy, r, color, strength):
    """Radial-ish glow built from stacked translucent ellipses."""
    base = im.convert("RGBA")
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    steps = 48
    for i in range(steps, 0, -1):
        rr = r * i / steps
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=color + (strength,))
    im.paste(Image.alpha_composite(base, layer).convert("RGB"), (0, 0))


def make_icon(size):
    """Rounded periwinkle plate with a centred soft circle, no clouds.

    The cloud was removed per user feedback ("promo 去掉这些云朵形状的").
    The icon now reads as a single soft periwinkle plate with a subtle
    inner glow + accent crescent, still abstract and dreamy.
    """
    s = size / 512.0

    # --- rounded-square plate: periwinkle -> sky -> cloud lavender ---
    im = vgrad(size, size, [(0.0, PERI), (0.55, SKY), (1.0, CLOUD)])

    # --- dreamy light bloom (top-left) ---
    soft_glow(im, size * 0.32, size * 0.28, size * 0.42, DREAM, 32)
    # --- gentle warm-up (bottom-right) ---
    soft_glow(im, size * 0.78, size * 0.82, size * 0.36, PERI, 26)

    d = ImageDraw.Draw(im, "RGBA")

    # --- centred soft white halo (no shape — just a radial wash) ---
    soft_glow(im, size * 0.5, size * 0.5, size * 0.30, DREAM, 60)

    # --- small accent dot (deep periwinkle) at upper-right ---
    d.ellipse([size * 0.74, size * 0.22, size * 0.82, size * 0.30],
              fill=LINK + (140,))

    # --- rounded corners, applied last ---
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [8 * s, 8 * s, size - 8 * s, size - 8 * s], radius=int(116 * s), fill=255
    )
    mask = mask.filter(ImageFilter.GaussianBlur(max(0.6, 0.8 * s)))

    out = im.convert("RGBA")
    out.putalpha(mask)
    return out


def main():
    master = make_icon(512)
    master.save(os.path.join(ASSETS, "icon-source.png"))

    icon = make_icon(128)
    icon.save(os.path.join(STORE, "icon.png"))

    print("icon-source.png:", master.size, master.mode)
    print("icon.png       :", icon.size, icon.mode)


if __name__ == "__main__":
    main()