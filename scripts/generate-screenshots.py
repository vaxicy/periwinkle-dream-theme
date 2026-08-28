#!/usr/bin/env python3
"""Generate the two Chrome Web Store screenshots for Periwinkle Dream Theme.

Layout mirrors a real Chrome window (tab strip + toolbar + bookmarks bar + NTP):
  - Window controls (min/max/close) on the far right of the tab strip
  - Omnibox with home icon + Google G inside + tail icons
  - Bookmark bar: apps grid (left), divider, folder bookmarks, apps grid (right) + avatar
  - NTP: only 3 shortcuts (YouTube, Chrome Web Store, Add shortcut)

All colors are read from manifest.json so the screenshot always matches the
theme the user actually installs.
"""
import json
import os

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOTS = os.path.join(ROOT, "store-assets", "screenshots", "en")
os.makedirs(SHOTS, exist_ok=True)

W, H = 1280, 800


def load_colors():
    with open(os.path.join(ROOT, "manifest.json"), encoding="utf-8") as f:
        c = json.load(f)["theme"]["colors"]
    return {k: tuple(v) for k, v in c.items()}


C = load_colors()
FRAME = C["frame"]                    # #B1B2FF tab strip / non-active tab
FRAME_INACTIVE = C["frame_inactive"]  # #AAC4FF
TOOLBAR = C["toolbar"]                # #D2DAFF toolbar / active tab / bookmarks
TAB_TEXT = C["tab_text"]              # #3C4270 active tab text
TAB_BG_TEXT = C["tab_background_text"]  # #404676 inactive tab text
BOOKMARK_TEXT = C["bookmark_text"]
TB_ICON = C["toolbar_button_icon"]
OMNI_BG = C["omnibox_background"]
OMNI_TEXT = C["omnibox_text"]
NTP_BG = C["ntp_background"]
NTP_TEXT = C["ntp_text"]
NTP_LINK = C["ntp_link"]

SUB_INK = (78, 86, 135)


def rgb(c, a=None):
    if a is None:
        return "rgb(%d,%d,%d)" % c
    return "rgba(%d,%d,%d,%s)" % (c[0], c[1], c[2], a)


# --------------------------------------------------------------------------
# Shot 1: real Chrome layout with Periwinkle Dream applied
# --------------------------------------------------------------------------
# Layout y positions (measured against the real Chrome reference):
#   tab strip     0 - 44      (height 44)
#   toolbar       44 - 100    (height 56)
#   bookmarks     100 - 138   (height 38)
#   NTP           138 - 800

BROWSER_HTML = """
<!doctype html><html><head><meta charset="utf-8"><style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
  width:{W}px; height:{H}px; overflow:hidden; background:{NTP_BG};
  font-family:'Segoe UI Variable', 'Segoe UI', system-ui, -apple-system, 'Helvetica Neue', sans-serif;
  -webkit-font-smoothing:antialiased;
}}

/* ---------- tab strip ---------- */
.tabstrip {{
  position:absolute; top:0; left:0; right:0; height:44px; background:{FRAME};
  display:flex; align-items:flex-end; padding:0 132px 0 8px; gap:2px;
}}
.tab {{
  height:36px; display:flex; align-items:center; gap:8px; padding:0 10px 0 12px;
  border-radius:8px 8px 0 0; font-size:12.5px; position:relative;
  background:{FRAME}; color:{TAB_BG_TEXT};
}}
.tab.active {{ background:{TOOLBAR}; color:{TAB_TEXT}; font-weight:600;
  width:188px; height:40px; margin-bottom:-1px; border-radius:8px 8px 0 0;
  box-shadow:0 -1px 0 0 rgba(60,66,112,0.06); }}
.tab.idle   {{ width:188px; opacity:0.92; }}
.tab .dot {{ width:16px; height:16px; border-radius:50%; flex:none; display:flex;
  align-items:center; justify-content:center; font-size:9px; font-weight:700; color:#fff; }}
.tab.active .dot {{ background:linear-gradient(135deg,#7BC9F2,#4A90E2); }}
.tab.idle   .dot {{ background:linear-gradient(135deg,#9CC9A8,#7BAD8B); }}
.tab.idle:nth-of-type(3) .dot {{ background:linear-gradient(135deg,#E9A89F,#D87060); }}
.tab .x {{ opacity:0.35; font-size:13px; margin-left:4px; cursor:default;
  border-radius:50%; width:16px; height:16px; display:flex; align-items:center;
  justify-content:center; }}
.tab.active .x {{ opacity:0.55; }}
.tab.new {{ width:28px; height:28px; justify-content:center; padding:0;
  margin:0 2px 8px 2px; border-radius:50%; font-size:18px;
  background:rgba(255,255,255,0.10); color:{TAB_BG_TEXT}; }}

/* window controls (top-right) */
.winctrl {{ position:absolute; top:0; right:8px; height:44px; display:flex;
  align-items:flex-start; padding-top:14px; gap:14px; color:{TAB_TEXT}; }}
.winctrl .btn {{ width:11px; height:11px; display:flex; align-items:center;
  justify-content:center; }}
.winctrl svg {{ width:9px; height:9px; fill:currentColor; opacity:0.78; }}

/* ---------- toolbar ---------- */
.toolbar {{
  position:absolute; top:44px; left:0; right:0; height:56px; background:{TOOLBAR};
  display:flex; align-items:center; gap:8px; padding:0 14px;
}}
.nav {{ width:28px; height:28px; border-radius:50%; display:flex;
  align-items:center; justify-content:center; color:{TB_ICON}; opacity:0.72; flex:none; }}
.nav svg {{ width:18px; height:18px; }}
.nav.home {{ background:#fff; box-shadow:inset 0 0 0 1px rgba(60,66,112,0.08);
  border-radius:50%; color:{TB_ICON}; opacity:1; }}
.nav.home .g {{ font-size:14px; font-weight:700; color:#4A90E2; font-family:'Segoe UI',sans-serif; }}

.omni {{
  flex:1; height:38px; margin-left:6px; border-radius:19px; background:#fff;
  display:flex; align-items:center; gap:10px; padding:0 14px; color:{OMNI_TEXT};
  font-size:13.5px; box-shadow:inset 0 0 0 1px rgba(60,66,112,0.07);
}}
.omni .g {{ font-size:16px; font-weight:700; color:#4A90E2; font-family:'Segoe UI',sans-serif; flex:none; }}
.omni .sep {{ width:1px; height:20px; background:rgba(60,66,112,0.16); flex:none; }}
.omni .url {{ flex:1; opacity:0.75; }}
.omni .tail {{ display:flex; align-items:center; gap:14px; }}
.omni .tail svg {{ width:17px; height:17px; opacity:0.45; color:{TB_ICON}; }}

.ext {{ display:flex; align-items:center; gap:6px; margin-left:8px; }}
.ext .b {{ width:28px; height:28px; border-radius:50%; display:flex;
  align-items:center; justify-content:center; font-size:13px; font-weight:700;
  color:#fff; }}
.ext .dot-icon {{ width:18px; height:18px; display:flex; align-items:center;
  justify-content:center; }}
.ext .dot-icon svg {{ width:18px; height:18px; }}
.ext .menu {{ width:28px; height:28px; display:flex; align-items:center;
  justify-content:center; color:{TB_ICON}; opacity:0.62; }}
.ext .menu svg {{ width:18px; height:18px; }}

/* ---------- bookmarks bar ---------- */
.bookmarks {{
  position:absolute; top:100px; left:0; right:0; height:38px; background:{TOOLBAR};
  display:flex; align-items:center; gap:6px; padding:0 12px;
  color:{BOOKMARK_TEXT}; font-size:12.5px;
  box-shadow:inset 0 1px 0 rgba(60,66,112,0.06);
}}
.bookmarks .apps {{ width:26px; height:26px; display:flex; align-items:center;
  justify-content:center; opacity:0.62; cursor:default; }}
.bookmarks .apps svg {{ width:14px; height:14px; color:{TB_ICON}; }}
.bookmarks .sep {{ width:1px; height:18px; background:rgba(60,66,112,0.20);
  margin:0 6px; }}
.bookmarks .bm {{ display:flex; align-items:center; gap:6px; padding:0 8px;
  height:24px; border-radius:12px; opacity:0.78; }}
.bookmarks .bm i {{ width:14px; height:14px; border-radius:4px; display:block; }}
.bm.folder i {{ background:linear-gradient(135deg,#C8C8E0,#A8A8C8); }}
.bm.doc i {{ background:linear-gradient(135deg,#FFB8B8,#FF9090); }}
.bm.paint i {{ background:linear-gradient(135deg,#FFE3A8,#FFB060); }}
.bm.ai i {{ background:linear-gradient(135deg,#A8C8FF,#7090E0); }}
.bm.ui i {{ background:linear-gradient(135deg,#D8A8FF,#A868D0); }}
.bm.g i {{ background:linear-gradient(135deg,#A8D8C0,#60A890); }}
.bm.api i {{ background:linear-gradient(135deg,#FFC8E0,#FF80B0); }}
.bm.docs i {{ background:linear-gradient(135deg,#FFD8A8,#FF9040); }}
.bm.dev i {{ background:linear-gradient(135deg,#FFB060,#FF6020); }}

.bookmarks .right {{ margin-left:auto; display:flex; align-items:center; gap:14px; }}
.bookmarks .right .img {{ width:18px; height:18px; display:flex; align-items:center;
  justify-content:center; color:{TB_ICON}; opacity:0.58; }}
.bookmarks .right .img svg {{ width:16px; height:16px; }}
.bookmarks .right .apps2 {{ width:26px; height:26px; display:flex;
  align-items:center; justify-content:center; opacity:0.62; cursor:default; }}
.bookmarks .right .apps2 svg {{ width:16px; height:16px; color:{TB_ICON}; }}
.bookmarks .right .avatar {{ width:26px; height:26px; border-radius:50%;
  background:linear-gradient(135deg,#FF8E72,#FFB060); display:flex;
  align-items:center; justify-content:center; color:#fff; font-size:11px; font-weight:700; }}

/* ---------- new tab page ---------- */
.ntp {{ position:absolute; top:138px; left:0; right:0; bottom:0; background:{NTP_BG};
  text-align:center; }}

/* Chrome-computed periwinkle logo (ntp_logo_alternate:1 in chrome's algorithm)
   -- this is what the user actually sees with our manifest set. */
.logo {{ position:absolute; top:130px; left:0; right:0; font-size:84px; font-weight:500;
  letter-spacing:-2px; color:{LOGO_COLOR}; opacity:0.95;
  font-family:'Segoe UI','Arial',sans-serif; }}
.search {{ position:absolute; top:270px; left:50%; transform:translateX(-50%);
  width:600px; height:52px; border-radius:26px; background:#fff;
  display:flex; align-items:center; gap:12px; padding:0 22px; color:{SUB_INK};
  font-size:15px; box-shadow:0 1px 3px rgba(60,66,112,0.10), 0 6px 18px rgba(60,66,112,0.06); }}
.search svg {{ width:19px; height:19px; opacity:0.45; flex:none; }}
.search .ph {{ opacity:0.55; }}
.search .tail {{ margin-left:auto; display:flex; gap:14px; }}
.search .tail svg {{ width:19px; height:19px; opacity:0.38; color:{TB_ICON}; }}
.tiles {{ position:absolute; top:356px; left:50%; transform:translateX(-50%);
  display:flex; gap:64px; }}
.tile {{ width:64px; cursor:default; }}
.tile .ring {{ width:64px; height:64px; border-radius:50%; display:flex;
  align-items:center; justify-content:center; }}
.tile .ring svg {{ width:30px; height:30px; }}
.tile .lbl {{ margin-top:11px; font-size:13px; color:{NTP_TEXT}; opacity:0.78; }}

/* Customize Chrome button (bottom-right) */
.custom {{ position:absolute; bottom:18px; right:18px;
  display:flex; align-items:center; gap:9px;
  padding:9px 16px; border-radius:20px;
  background:rgba(60,66,112,0.84); color:#fff; font-size:13px;
  font-weight:500; }}
.custom svg {{ width:16px; height:16px; }}
</style></head><body>

<div class="tabstrip">
  <div class="tab active">
    <span class="dot"></span>New Tab<span class="x">&times;</span>
  </div>
  <div class="tab idle">
    <span class="dot"></span>Getting Started<span class="x">&times;</span>
  </div>
  <div class="tab idle">
    <span class="dot"></span>Reading List<span class="x">&times;</span>
  </div>
  <div class="tab new">+</div>
  <div class="winctrl">
    <div class="btn"><svg viewBox="0 0 10 10"><rect x="0.5" y="5" width="9" height="1"/></svg></div>
    <div class="btn"><svg viewBox="0 0 10 10"><rect x="0.5" y="0.5" width="9" height="9"
      fill="none" stroke="currentColor" stroke-width="1"/></svg></div>
    <div class="btn"><svg viewBox="0 0 10 10"><path d="M0.5 0.5 L9.5 9.5 M9.5 0.5 L0.5 9.5"
      stroke="currentColor" stroke-width="1"/></svg></div>
  </div>
</div>

<div class="toolbar">
  <div class="nav"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
    stroke-linecap="round" stroke-linejoin="round"><path d="M15 18l-6-6 6-6"/></svg></div>
  <div class="nav" style="opacity:.35"><svg viewBox="0 0 24 24" fill="none"
    stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M9 18l6-6-6-6"/></svg></div>
  <div class="nav"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
    stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 1 1-3-6.7"/>
    <path d="M21 4v5h-5"/></svg></div>
  <div class="nav home"><span class="g">G</span></div>
  <div class="omni">
    <span class="g">G</span>
    <span class="url">Search Google or type a URL</span>
    <span class="tail">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"
        stroke-linecap="round"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z"/>
        <path d="M19 11v1a7 7 0 0 1-14 0v-1"/><path d="M12 19v3"/></svg>
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"
        stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>
    </span>
  </div>
  <div class="ext">
    <div class="b" style="background:#C0E89A;color:#3D7A1E;">G</div>
    <div class="b" style="background:#FFB8B8;color:#A02828;">R</div>
    <div class="b" style="background:#FFD28A;color:#A0580A;">D</div>
    <div class="b" style="background:#A8C8FF;color:#2050B0;">8</div>
    <div class="b" style="background:#D8A8FF;color:#6028A0;">P</div>
    <div class="b" style="background:#FFD89E;color:#A0580A;">L</div>
    <div class="b" style="background:#A8D8C0;color:#207858;">T</div>
    <div class="menu"><svg viewBox="0 0 24 24" fill="currentColor">
      <circle cx="5" cy="12" r="1.6"/><circle cx="12" cy="12" r="1.6"/><circle cx="19" cy="12" r="1.6"/>
    </svg></div>
  </div>
</div>

<div class="bookmarks">
  <div class="apps"><svg viewBox="0 0 24 24" fill="currentColor">
    <path d="M4 4h4v4H4V4zm6 0h4v4h-4V4zm6 0h4v4h-4V4zM4 10h4v4H4v-4zm6 0h4v4h-4v-4zm6 0h4v4h-4v-4zM4 16h4v4H4v-4zm6 0h4v4h-4v-4zm6 0h4v4h-4v-4z"/></svg></div>
  <div class="sep"></div>
  <div class="bm folder"><i></i>Projects</div>
  <div class="bm doc"><i></i>Docs</div>
  <div class="bm paint"><i></i>Studio</div>
  <div class="bm ai"><i></i>AI</div>
  <div class="bm ui"><i></i>UI</div>
  <div class="bm g"><i></i>Garden</div>
  <div class="bm api"><i></i>API</div>
  <div class="bm docs"><i></i>Daily</div>
  <div class="bm dev"><i></i>Dev</div>
  <div class="right">
    <span style="font-size:12.5px;opacity:0.72;">Photos</span>
    <div class="img"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"
      stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="6" width="18" height="13" rx="2"/>
      <path d="M8 6l1.4-2h5.2L16 6"/><circle cx="12" cy="12.5" r="3"/></svg></div>
    <div class="apps2"><svg viewBox="0 0 24 24" fill="currentColor">
      <path d="M4 4h4v4H4V4zm6 0h4v4h-4V4zm6 0h4v4h-4V4zM4 10h4v4H4v-4zm6 0h4v4h-4v-4zm6 0h4v4h-4v-4zM4 16h4v4H4v-4zm6 0h4v4h-4v-4zm6 0h4v4h-4v-4z"/></svg></div>
    <div class="avatar">L</div>
  </div>
</div>

<div class="ntp">
  <div class="logo">Google</div>
  <div class="search">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
      stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>
    <span class="ph">Search Google or type a URL</span>
    <span class="tail">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"
        stroke-linecap="round"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z"/>
        <path d="M19 11v1a7 7 0 0 1-14 0v-1"/><path d="M12 19v3"/></svg>
      <svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2a4 4 0 0 0-4 4v2a4 4 0 0 0-2 7.5V14a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2v-1.5A4 4 0 0 0 16 8V6a4 4 0 0 0-4-4zm-2 4a2 2 0 1 1 4 0v2h-4V6z"/></svg>
    </span>
  </div>
  <div class="tiles">
    <div class="tile"><div class="ring" style="background:#F4D0C8">
      <svg viewBox="0 0 24 24" fill="#FF0000"><path d="M23 7s-1.4-.6-3.2-1c-.4-1.4-.9-2.5-.9-2.5s-1.6-.3-3 .4a11 11 0 0 0-3.4-.2C10 3.7 7.7 4.5 5.7 6c-1.5 0-3 .3-4.5.7 0 0-1.7 3-1.7 7 0 1.2.1 2.4.4 3.6 0 0 1.5 1.5 5.5 1.5L7 17c.4-.4 1-.9 1.4-1.3-1-.4-1.8-.9-2.6-1.6.2.1.4.2.6.3a15 15 0 0 0 5.5 1.5c1.4 0 2.7-.2 4-.6a13 13 0 0 0 1.8-1c-.7-.5-1.5-.9-2.5-1.3.5.4 1 .9 1.5 1.3 1.4-.4 2.4-1 2.4-1s.4-1.6.4-3.6c0-4-1.7-7-1.7-7l-.2-.1zM9.7 12.3c-.7 0-1.3-.7-1.3-1.6 0-.8.6-1.5 1.3-1.5.7 0 1.3.7 1.3 1.6 0 .8-.6 1.5-1.3 1.5zm4.6 0c-.7 0-1.3-.7-1.3-1.6 0-.8.6-1.5 1.3-1.5.7 0 1.3.7 1.3 1.6 0 .8-.6 1.5-1.3 1.5z"/></svg>
    </div><div class="lbl">YouTube</div></div>
    <div class="tile"><div class="ring" style="background:#DCEAF7">
      <svg viewBox="0 0 24 24" fill="#1A73E8"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12"
        r="3.6" fill="#fff"/><circle cx="12" cy="12" r="1.6"/></svg>
    </div><div class="lbl">Chrome Web Store</div></div>
    <div class="tile"><div class="ring" style="background:#E5E5EE">
      <svg viewBox="0 0 24 24" fill="none" stroke="#5F6368" stroke-width="1.8"
        stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>
    </div><div class="lbl">Add shortcut</div></div>
  </div>
</div>

<div class="custom">
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"
    stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l2.4 5 5.6.8-4 3.9 1 5.5-5-2.7-5 2.7 1-5.5-4-3.9 5.6-.8z"/></svg>
  Customize Chrome
</div>
</body></html>
""".format(
    W=W, H=H,
    FRAME=rgb(FRAME),
    TOOLBAR=rgb(TOOLBAR),
    TAB_TEXT=rgb(TAB_TEXT),
    TAB_BG_TEXT=rgb(TAB_BG_TEXT),
    BOOKMARK_TEXT=rgb(BOOKMARK_TEXT),
    TB_ICON=rgb(TB_ICON),
    OMNI_BG=rgb(OMNI_BG),
    OMNI_TEXT=rgb(OMNI_TEXT),
    NTP_BG=rgb(NTP_BG),
    NTP_TEXT=rgb(NTP_TEXT),
    SUB_INK=rgb(SUB_INK),
    PERI=rgb(C["frame"]),
    SKY=rgb(C["frame_inactive"]),
    CLOUD_LAV=rgb(C["toolbar"]),
    LINK=rgb(C["ntp_link"]),
    LOGO_COLOR=rgb((124, 134, 226)),
)


def render(html, out_path):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": W, "height": H})
        page.set_content(html)
        page.wait_for_timeout(400)
        page.screenshot(path=out_path, clip={"x": 0, "y": 0, "width": W, "height": H})
        browser.close()
    im = Image.open(out_path).convert("RGB")
    im.save(out_path)
    print(os.path.relpath(out_path, ROOT), im.size, im.mode)


def main():
    render(BROWSER_HTML, os.path.join(SHOTS, "screenshot-1-browser.png"))
    render(PALETTE_HTML, os.path.join(SHOTS, "screenshot-2-palette.png"))


# --------------------------------------------------------------------------
# Shot 2: the four-colour palette
# --------------------------------------------------------------------------
SWATCHES = [
    ("Periwinkle", "#B1B2FF", C["frame"]),
    ("Soft Sky Blue", "#AAC4FF", C["frame_inactive"]),
    ("Cloud Lavender", "#D2DAFF", C["toolbar"]),
    ("Dream White", "#EEF1FF", C["ntp_background"]),
]

CARD_W, CARD_H, CARD_GAP = 236, 300, 30
CARDS_TOTAL = 4 * CARD_W + 3 * CARD_GAP
CARDS_X = (W - CARDS_TOTAL) // 2
CARDS_Y = 330

cards_html = "".join(
    """
  <div class="card">
    <div class="sw" style="background:%s"></div>
    <div class="cname">%s</div>
    <div class="chex">%s</div>
  </div>""" % (rgb(col), name, hexv)
    for name, hexv, col in SWATCHES
)

PALETTE_HTML = """
<!doctype html><html><head><meta charset="utf-8"><style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
  width:{W}px; height:{H}px; overflow:hidden; position:relative;
  background:{NTP_BG};
  font-family:'Segoe UI', system-ui, -apple-system, 'Helvetica Neue', sans-serif;
  -webkit-font-smoothing:antialiased;
}}
.glow {{ position:absolute; border-radius:50%; filter:blur(90px); }}
.g1 {{ width:900px; height:900px; left:-180px; top:-620px; background:{PERI}; opacity:0.20; }}
.g2 {{ width:760px; height:760px; right:-220px; top:-300px; background:{SKY}; opacity:0.22; }}
.g3 {{ width:820px; height:820px; left:300px; bottom:-560px; background:{CLOUD_LAV}; opacity:0.28; }}

.eyebrow {{ position:absolute; top:140px; left:0; right:0; text-align:center;
  font-size:14px; font-weight:600; letter-spacing:3.4px; color:{LINK}; text-transform:uppercase; }}
.title {{ position:absolute; top:186px; left:0; right:0; text-align:center;
  font-size:52px; font-weight:600; letter-spacing:-0.8px; color:{NTP_TEXT}; }}
.subtitle {{ position:absolute; top:252px; left:0; right:0; text-align:center;
  font-size:20px; color:{SUB_INK}; }}

.cards {{ position:absolute; top:{CARDS_Y}px; left:{CARDS_X}px; display:flex; gap:{CARD_GAP}px; }}
.card {{ width:{CARD_W}px; height:{CARD_H}px; background:#fff; border-radius:22px;
  box-shadow:0 2px 6px rgba(60,66,112,0.07), 0 14px 34px rgba(60,66,112,0.09);
  padding:14px; }}
.sw {{ width:100%; height:170px; border-radius:14px; }}
.cname {{ margin-top:34px; text-align:center; font-size:22px; font-weight:600; color:{NTP_TEXT}; }}
.chex {{ margin-top:8px; text-align:center; font-size:17px; color:{LINK}; letter-spacing:0.6px; }}

.footer {{ position:absolute; top:700px; left:0; right:0; text-align:center;
  font-size:18px; color:{SUB_INK}; }}
</style></head><body>
<div class="glow g1"></div><div class="glow g2"></div><div class="glow g3"></div>
<div class="eyebrow">Periwinkle Dream Theme</div>
<div class="title">Soft colors. Calm browsing.</div>
<div class="subtitle">Four pastel tones working together across the whole browser.</div>
<div class="cards">{CARDS}</div>
<div class="footer">A soft periwinkle Chrome theme for calm, comfortable browsing.</div>
</body></html>
""".format(
    W=W, H=H,
    NTP_BG=rgb(C["ntp_background"]),
    PERI=rgb(C["frame"]),
    SKY=rgb(C["frame_inactive"]),
    CLOUD_LAV=rgb(C["toolbar"]),
    NTP_TEXT=rgb(C["ntp_text"]),
    SUB_INK=rgb(SUB_INK),
    LINK=rgb(C["ntp_link"]),
    CARDS_Y=CARDS_Y, CARDS_X=CARDS_X, CARD_GAP=CARD_GAP, CARD_W=CARD_W, CARD_H=CARD_H,
    CARDS=cards_html,
)


if __name__ == "__main__":
    main()