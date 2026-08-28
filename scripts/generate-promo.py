#!/usr/bin/env python3
"""Generate the Chrome Web Store promo tiles for Periwinkle Dream Theme.

  store-assets/periwinkle-dream-small-promo.png   440 x 280
  store-assets/periwinkle-dream-marquee-promo.png 1400 x 560

English only. No Chrome or Google logos, no people, no third-party artwork.
All colors are read from manifest.json.

Layout guards (asserted at runtime, not eyeballed):
  - subtitle top >= title bottom + 8px
  - chip row does not overlap the CTA button
  - CTA bottom <= canvas height - 12px
  - every text block stays inside the canvas horizontally
"""
import json
import os

from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(ROOT, "store-assets")
os.makedirs(STORE, exist_ok=True)

FONT_BOLD = "C:/Windows/Fonts/segoeuib.ttf"
FONT_REG = "C:/Windows/Fonts/segoeui.ttf"
FONT_LIGHT = "C:/Windows/Fonts/segoeuil.ttf"


def load_colors():
    with open(os.path.join(ROOT, "manifest.json"), encoding="utf-8") as f:
        c = json.load(f)["theme"]["colors"]
    return {k: tuple(v) for k, v in c.items()}


C = load_colors()
PERI = C["frame"]              # #B1B2FF
SKY = C["frame_inactive"]      # #AAC4FF
CLOUD_LAV = C["toolbar"]       # #D2DAFF
DREAM = C["ntp_background"]    # #EEF1FF
LINK = C["ntp_link"]           # #5A63C8 deep periwinkle accent
INK = C["tab_text"]            # #3C4270 primary text
SUB_INK = (78, 86, 135)        # muted deep periwinkle
WHITE = (255, 255, 255)


def vgrad(w, h, stops):
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
    base = im.convert("RGBA")
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    steps = 48
    for i in range(steps, 0, -1):
        rr = r * i / steps
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=color + (strength,))
    im.paste(Image.alpha_composite(base, layer).convert("RGB"), (0, 0))


def text_size(d, s, f):
    b = d.textbbox((0, 0), s, font=f)
    return b[2] - b[0], b[3] - b[1], b[0], b[1]


def draw_center(d, cx, cy, s, f, fill):
    """True visual centering: align the text bounding box center to (cx, cy)."""
    b = d.textbbox((0, 0), s, font=f)
    w, h = b[2] - b[0], b[3] - b[1]
    d.text((cx - w / 2 - b[0], cy - h / 2 - b[1]), s, font=f, fill=fill)


def draw_left(d, x, cy, s, f, fill):
    b = d.textbbox((0, 0), s, font=f)
    w, h = b[2] - b[0], b[3] - b[1]
    d.text((x - b[0], cy - h / 2 - b[1]), s, font=f, fill=fill)
    return w, h


def make_promo(W, H, cfg):
    from PIL import ImageFont

    f_title = ImageFont.truetype(FONT_BOLD, cfg["title"])
    f_sub = ImageFont.truetype(FONT_LIGHT, cfg["sub"])
    f_chip = ImageFont.truetype(FONT_REG, cfg["chip"])
    f_cta = ImageFont.truetype(FONT_BOLD, cfg["cta"])

    # ---------------- background ----------------
    im = vgrad(W, H, [(0.0, PERI), (0.38, SKY), (0.74, CLOUD_LAV), (1.0, DREAM)])
    # subtle glow (kept; no longer masked by cloud blobs)
    soft_glow(im, W * 0.80, H * 0.18, H * 0.55, DREAM, 18)
    soft_glow(im, W * 0.10, H * 0.92, H * 0.50, PERI, 14)
    im = im.filter(ImageFilter.GaussianBlur(cfg["blur"]))
    d = ImageDraw.Draw(im, "RGBA")

    LX = cfg["LX"]
    right_limit = W - cfg["margin_r"]

    # ---------------- title ----------------
    title = cfg["title_text"]
    tw, th, _, _ = text_size(d, title, f_title)
    assert LX + tw <= right_limit, "title overflows: %d > %d" % (LX + tw, right_limit)
    title_cy = cfg["title_cy"]
    title_top = title_cy - th / 2
    title_bottom = title_cy + th / 2
    draw_left(d, LX, title_cy, title, f_title, INK)

    # ---------------- subtitle ----------------
    sub = cfg["sub_text"]
    sw, sh, _, _ = text_size(d, sub, f_sub)
    assert LX + sw <= right_limit, "subtitle overflows: %d > %d" % (LX + sw, right_limit)
    sub_cy = title_bottom + cfg["gap_title_sub"] + sh / 2
    sub_bottom = sub_cy + sh / 2
    assert sub_cy - sh / 2 >= title_bottom + 8, "title/subtitle gap < 8px"
    draw_left(d, LX, sub_cy, sub, f_sub, SUB_INK)

    # ---------------- chips ----------------
    chip_h = cfg["chip_h"]
    chips_cy = sub_bottom + cfg["gap_sub_chip"] + chip_h / 2
    chips_bottom = chips_cy + chip_h / 2
    x = LX
    for ch in cfg["chips"]:
        cw = text_size(d, ch, f_chip)[0] + cfg["chip_pad"]
        assert x + cw <= right_limit, "chip row overflows"
        d.rounded_rectangle([x, chips_cy - chip_h / 2, x + cw, chips_cy + chip_h / 2],
                            radius=chip_h / 2, fill=WHITE + (205,))
        draw_center(d, x + cw / 2, chips_cy, ch, f_chip, INK)
        x += cw + cfg["chip_gap"]

    # ---------------- CTA ----------------
    btn_w, btn_h = cfg["btn_w"], cfg["btn_h"]
    cta_cy = H - cfg["cta_bottom_margin"] - btn_h / 2
    cta_top, cta_bottom = cta_cy - btn_h / 2, cta_cy + btn_h / 2
    assert cta_top >= chips_bottom + 10, "CTA overlaps chips"
    assert cta_bottom <= H - 12, "CTA bottom out of safe area: %.1f > %d" % (cta_bottom, H - 12)
    d.rounded_rectangle([LX, cta_top, LX + btn_w, cta_bottom],
                        radius=btn_h / 2, fill=LINK)
    draw_center(d, LX + btn_w / 2, cta_cy, cfg["cta_text"], f_cta, WHITE)

    return im.convert("RGB")


CFG_SMALL = dict(
    title=38, sub=14, chip=11, cta=14,
    blur=5,
    LX=34, margin_r=16,
    title_text="Periwinkle Dream",
    sub_text="Soft. Calm. Dreamy.",
    title_cy=96, gap_title_sub=14,
    chips=["Soft pastel", "Calm browsing", "Lightweight"],
    chip_h=26, chip_pad=20, chip_gap=8, gap_sub_chip=22,
    btn_w=150, btn_h=36, cta_bottom_margin=20,
    cta_text="Add to Chrome",
)

CFG_MARQUEE = dict(
    title=76, sub=27, chip=16, cta=21,
    blur=11,
    LX=88, margin_r=48,
    title_text="Periwinkle Dream",
    sub_text="Soft colors for calmer browsing.",
    title_cy=190, gap_title_sub=20,
    chips=["Soft pastel", "Calm browsing", "Lightweight"],
    chip_h=38, chip_pad=32, chip_gap=14, gap_sub_chip=34,
    btn_w=232, btn_h=56, cta_bottom_margin=44,
    cta_text="Add to Chrome",
)


def main():
    small = make_promo(440, 280, CFG_SMALL)
    small.save(os.path.join(STORE, "periwinkle-dream-small-promo.png"))
    print("periwinkle-dream-small-promo.png", small.size, small.mode)

    marquee = make_promo(1400, 560, CFG_MARQUEE)
    marquee.save(os.path.join(STORE, "periwinkle-dream-marquee-promo.png"))
    print("periwinkle-dream-marquee-promo.png", marquee.size, marquee.mode)


if __name__ == "__main__":
    main()
