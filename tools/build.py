#!/usr/bin/env python3
"""Generate every SVG for the profile README, light and dark.

Run from the repo root:  uv run --with fonttools --with brotli tools/build.py

Design tokens live in THEMES. Each SVG embeds a subset of the two typefaces
(Latin Modern Roman for display text, JetBrains Mono for labels) as base64
WOFF2 so GitHub's <img> rendering shows the intended faces.
"""
from __future__ import annotations

import base64
import io
import math
from dataclasses import dataclass
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
FONT_DIR = ROOT / "tools" / "fonts"
OUT = ROOT / "assets"
OUT.mkdir(exist_ok=True)

# ---------------------------------------------------------------- fonts
FONT_FILES = {
    "display": FONT_DIR / "lmroman17-regular.otf",
    "serif": FONT_DIR / "lmroman10-regular.otf",
    "serif-italic": FONT_DIR / "lmroman10-italic.otf",
    "serif-bold": FONT_DIR / "lmroman10-bold.otf",
    "mono": FONT_DIR / "JetBrainsMono-Regular.ttf",
}
_FONTS = {k: TTFont(str(v)) for k, v in FONT_FILES.items()}


def measure(text: str, face: str, size: float) -> float:
    """Advance width of text (no kerning) in px at the given font size."""
    f = _FONTS[face]
    cmap = f.getBestCmap()
    hmtx = f["hmtx"]
    upm = f["head"].unitsPerEm
    total = 0
    for ch in text:
        gid = cmap.get(ord(ch))
        if gid is None:
            gid = cmap.get(ord("?"))
        total += hmtx[gid][0]
    return total * size / upm


def wrap(text: str, face: str, size: float, max_w: float) -> list[str]:
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if measure(trial, face, size) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def subset_b64(face: str, chars: set[str]) -> str:
    """Subset a face to the given characters and return base64 WOFF2."""
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.desubroutinize = True
    opts.hinting = False
    opts.layout_features = ["kern", "liga"]
    opts.name_IDs = []
    opts.notdef_outline = True
    font = TTFont(str(FONT_FILES[face]))
    sub = subset.Subsetter(opts)
    sub.populate(text="".join(sorted(chars)) + " ?")
    sub.subset(font)
    buf = io.BytesIO()
    font.flavor = "woff2"
    font.save(buf)
    return base64.b64encode(buf.getvalue()).decode()


FACE_CSS = {
    "display": "LMDisplay",
    "serif": "LMSerif",
    "serif-italic": "LMSerifItalic",
    "serif-bold": "LMSerifBold",
    "mono": "JBMono",
}
FALLBACK = {
    "display": "'Latin Modern Roman', 'CMU Serif', Georgia, 'Times New Roman', serif",
    "serif": "'Latin Modern Roman', 'CMU Serif', Georgia, 'Times New Roman', serif",
    "serif-italic": "'Latin Modern Roman', 'CMU Serif', Georgia, 'Times New Roman', serif",
    "serif-bold": "'Latin Modern Roman', 'CMU Serif', Georgia, 'Times New Roman', serif",
    "mono": "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
}


# ---------------------------------------------------------------- themes
@dataclass(frozen=True)
class Theme:
    name: str
    ink: str        # primary text
    muted: str      # secondary text
    faint: str      # tertiary text / light marks
    rule: str       # borders
    hairline: str   # grid, dividers
    card: str       # card fill
    canvas: str     # page background (used only behind clipped areas)
    accent: str     # the one hue: live things, the drone, the cursor
    accent_soft: str


THEMES = {
    "light": Theme(
        name="light",
        ink="#1F2328", muted="#656D76", faint="#8C959F",
        rule="#D0D7DE", hairline="#E6EAEF", card="#F6F8FA", canvas="#FFFFFF",
        accent="#2F7D6B", accent_soft="#CFE3DC",
    ),
    "dark": Theme(
        name="dark",
        ink="#E6EDF3", muted="#8B949E", faint="#6E7681",
        rule="#30363D", hairline="#21262D", card="#161B22", canvas="#0D1117",
        accent="#5DB39E", accent_soft="#1E3B34",
    ),
}


# ---------------------------------------------------------------- svg builder
class SVG:
    def __init__(self, w: int, h: int, t: Theme, title: str):
        self.w, self.h, self.t, self.title = w, h, t, title
        self.parts: list[str] = []
        self.used: dict[str, set[str]] = {k: set() for k in FONT_FILES}

    def text(self, x, y, s, face="serif", size=14, fill=None, anchor="start",
             opacity=None, letter_spacing=None, extra=""):
        self.used[face].update(s)
        fill = fill or self.t.ink
        attrs = [f'x="{x:.1f}"', f'y="{y:.1f}"', f'class="{face}"',
                 f'font-size="{size}"', f'fill="{fill}"']
        if anchor != "start":
            attrs.append(f'text-anchor="{anchor}"')
        if opacity is not None:
            attrs.append(f'opacity="{opacity}"')
        if letter_spacing is not None:
            attrs.append(f'letter-spacing="{letter_spacing}"')
        w = measure(s, face, size)
        right = x + (w if anchor == "start" else w / 2 if anchor == "middle" else 0)
        if right > self.w - 2:
            print(f"  ! overflow in {self.title[:30]!r}: {s[:40]!r} ends at {right:.0f} > {self.w}")
        self.parts.append(f"<text {' '.join(attrs)} {extra}>{esc(s)}</text>")

    def raw(self, s: str):
        self.parts.append(s)

    def render(self) -> str:
        faces = []
        for face, chars in self.used.items():
            if not chars:
                continue
            b64 = subset_b64(face, chars)
            faces.append(
                f"@font-face{{font-family:'{FACE_CSS[face]}';"
                f"src:url(data:font/woff2;base64,{b64}) format('woff2');}}"
            )
        css_classes = "".join(
            f".{face}{{font-family:'{FACE_CSS[face]}',{FALLBACK[face]};}}"
            for face in self.used if self.used[face]
        )
        style = "".join(faces) + css_classes
        body = "\n".join(self.parts)
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
            f'viewBox="0 0 {self.w} {self.h}" role="img" aria-labelledby="t">\n'
            f"<title id=\"t\">{esc(self.title)}</title>\n"
            f"<style>{style}</style>\n{body}\n</svg>\n"
        )


def esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def write(name: str, svg: SVG):
    path = OUT / f"{name}-{svg.t.name}.svg"
    path.write_text(svg.render(), encoding="utf-8")
    print(f"  {path.relative_to(ROOT)}  {path.stat().st_size/1024:.1f} KB")


# ---------------------------------------------------------------- pieces
W = 900  # README column width the SVGs are designed for


def hero(t: Theme) -> SVG:
    H = 300
    s = SVG(W, H, t, "Ziyuan Zhao: robotics and computer vision for precision livestock farming")

    # --- left: words
    x = 4
    s.text(x, 60, "steven068zzy", "mono", 12, t.muted, letter_spacing=0.5)
    s.text(x + measure("steven068zzy", "mono", 12) + 18, 60, "College Station, TX",
           "mono", 12, t.faint, letter_spacing=0.5)

    s.text(x - 2, 128, "Ziyuan Zhao", "display", 62, t.ink)
    nw = measure("Ziyuan Zhao", "display", 62)
    s.text(x + nw + 16, 128, "Steven", "serif-italic", 30, t.muted)

    tag = ["Robotics & computer vision", "for precision livestock farming."]
    s.text(x, 176, tag[0], "serif-italic", 23, t.ink)
    s.text(x, 204, tag[1], "serif-italic", 23, t.ink)

    y = 252
    s.text(x, y, "PhD researcher, Texas A&M", "mono", 12.5, t.muted)
    x2 = x + measure("PhD researcher, Texas A&M", "mono", 12.5) + 14
    s.raw(f'<circle cx="{x2:.1f}" cy="{y-4}" r="1.6" fill="{t.faint}"/>')
    x2 += 14
    s.text(x2, y, "Co-founder, Smart Swine", "mono", 12.5, t.muted)

    # --- right: broiler house plan with a patrolling drone
    hx, hy, hw, hh = 520, 36, 376, 232     # house outline
    # notebook grid, clipped to the house
    s.raw(f'<defs><clipPath id="house"><rect x="{hx}" y="{hy}" width="{hw}" height="{hh}" rx="4"/></clipPath>'
          f'<pattern id="grid" width="16" height="16" patternUnits="userSpaceOnUse" x="{hx}" y="{hy}">'
          f'<path d="M16 0H0V16" fill="none" stroke="{t.hairline}" stroke-width="1"/></pattern></defs>')
    s.raw(f'<rect x="{hx}" y="{hy}" width="{hw}" height="{hh}" rx="4" fill="url(#grid)"/>')
    s.raw(f'<rect x="{hx}" y="{hy}" width="{hw}" height="{hh}" rx="4" fill="none" stroke="{t.rule}" stroke-width="1.2"/>')

    # feeder lines (solid) and drinker lines (dashed), running the long axis
    n_lines = 4
    pitch = hh / n_lines
    lane_y = []
    for i in range(n_lines):
        ly = hy + pitch * (i + 0.5)
        lane_y.append(ly)
        s.raw(f'<line x1="{hx+18}" y1="{ly:.1f}" x2="{hx+hw-18}" y2="{ly:.1f}" stroke="{t.muted}" stroke-width="1.6" stroke-linecap="round"/>')
        # feeder pans
        for px in range(int(hx + 34), int(hx + hw - 20), 34):
            s.raw(f'<circle cx="{px}" cy="{ly:.1f}" r="2.6" fill="{t.canvas}" stroke="{t.muted}" stroke-width="1.2"/>')
    for i in range(n_lines - 1):
        dy = (lane_y[i] + lane_y[i + 1]) / 2
        s.raw(f'<line x1="{hx+18}" y1="{dy:.1f}" x2="{hx+hw-18}" y2="{dy:.1f}" stroke="{t.faint}" stroke-width="1" stroke-dasharray="2 5" stroke-linecap="round"/>')

    # patrol path: serpentine through the gaps between lines, drawn once, flown repeatedly
    gaps = [hy + 14] + [(lane_y[i] + lane_y[i + 1]) / 2 for i in range(n_lines - 1)] + [hy + hh - 14]
    # fly the drinker gaps offset a little so the path does not sit on the dashed line
    ys = [gaps[0] + 2, gaps[1] - 9, gaps[2] + 9, gaps[3] - 9, gaps[4] - 2]
    xl, xr = hx + 30, hx + hw - 30
    d = f"M{xl},{ys[0]:.1f}"
    for i, yy in enumerate(ys):
        tx = xr if i % 2 == 0 else xl
        d += f" L{tx},{yy:.1f}"
        if i + 1 < len(ys):
            d += f" L{tx},{ys[i+1]:.1f}"
    s.raw(f'<path d="{d}" fill="none" stroke="{t.accent}" stroke-width="1.2" stroke-dasharray="1 6" stroke-linecap="round" opacity="0.9"/>')
    # drone: halo + body; both follow the path
    dur = "34s"
    s.raw(f'<g><circle r="9" fill="{t.accent}" opacity="0.18">'
          f'<animateMotion dur="{dur}" repeatCount="indefinite" path="{d}"/></circle>'
          f'<circle r="3.4" fill="{t.accent}">'
          f'<animateMotion dur="{dur}" repeatCount="indefinite" path="{d}"/></circle></g>')
    # tiny legend, mono, under the house
    s.text(hx, hy + hh + 20, "broiler house · feeder lines · UAV patrol", "mono", 10.5, t.faint, letter_spacing=0.3)
    return s


def now(t: Theme) -> SVG:
    H = 44
    s = SVG(W, H, t, "Now: LineGate-SLAM, a multi-object-tracking review, SPM-01")
    y = 27
    x = 4
    s.text(x, y, "~", "mono", 13, t.faint)
    x += measure("~ ", "mono", 13)
    s.text(x, y, "$", "mono", 13, t.accent)
    x += measure("$ ", "mono", 13)
    s.text(x, y, "now", "mono", 13, t.ink)
    x += measure("now", "mono", 13) + 22
    items = [
        "LineGate-SLAM, UAV patrol in broiler houses",
        "a review of multi-object tracking in livestock",
        "SPM-01 piglet monitor",
    ]
    for i, it in enumerate(items):
        s.text(x, y, it, "serif", 14.5, t.ink)
        x += measure(it, "serif", 14.5) + 12
        if i < len(items) - 1:
            s.raw(f'<circle cx="{x:.1f}" cy="{y-5}" r="1.6" fill="{t.faint}"/>')
            x += 12
    # blinking block cursor
    s.raw(f'<rect x="{x+2:.1f}" y="{y-12}" width="7" height="15" fill="{t.accent}">'
          f'<animate attributeName="opacity" values="1;1;0;0" dur="1.1s" repeatCount="indefinite"/></rect>')
    return s


CARD_W, CARD_H = 438, 150


def card(t: Theme, key: str, eyebrow: str, title: str, body: str, draw) -> SVG:
    s = SVG(CARD_W, CARD_H, t, f"{title}: {body}")
    s.raw(f'<rect x="0.5" y="0.5" width="{CARD_W-1}" height="{CARD_H-1}" rx="6" fill="{t.card}" stroke="{t.rule}"/>')
    x = 22
    s.text(x, 32, eyebrow, "mono", 11, t.faint, letter_spacing=0.4)
    s.text(x, 62, title, "serif", 21, t.ink)
    lines = wrap(body, "serif", 13.5, 268)
    for i, ln in enumerate(lines[:3]):
        s.text(x, 88 + i * 19, ln, "serif", 13.5, t.muted)
    # illustration zone: x 312..418, y 22..128
    draw(s, t, 312, 22, 106, 106)
    return s


def ill_palette(s: SVG, t: Theme, x, y, w, h):
    # The Great Wave off Kanagawa, from the repository's own data
    cols = ["#B6A07E", "#31658A", "#2A4054", "#002542", "#92A2A5", "#576D7C", "#C2C9BA", "#F5EBD1"]
    cell, gap = 22, 6
    gw = 4 * cell + 3 * gap
    ox = x + (w - gw) / 2
    oy = y + 20
    for i, c in enumerate(cols):
        cx = ox + (i % 4) * (cell + gap)
        cy = oy + (i // 4) * (cell + gap)
        s.raw(f'<rect x="{cx:.1f}" y="{cy:.1f}" width="{cell}" height="{cell}" rx="3" fill="{c}" stroke="{t.rule}" stroke-width="0.6"/>')
    s.text(x + w / 2, oy + 2 * cell + gap + 22, "The Great Wave", "serif-italic", 11.5, t.faint, anchor="middle")


def ill_annotator(s: SVG, t: Theme, x, y, w, h):
    # three identity tracks, each a bar with a start and a duration; a playhead
    oy = y + 22
    rows = [(0.05, 0.55), (0.30, 0.95), (0.00, 0.35), (0.62, 1.0)]
    rh = 11
    for i, (a, b) in enumerate(rows):
        ry = oy + i * (rh + 9)
        s.raw(f'<line x1="{x}" y1="{ry+rh/2:.1f}" x2="{x+w}" y2="{ry+rh/2:.1f}" stroke="{t.hairline}" stroke-width="1"/>')
        fill = t.accent if i == 1 else t.faint
        s.raw(f'<rect x="{x+a*w:.1f}" y="{ry}" width="{(b-a)*w:.1f}" height="{rh}" rx="2" fill="{fill}" opacity="{1 if i==1 else 0.55}"/>')
    px = x + 0.46 * w
    s.raw(f'<line x1="{px:.1f}" y1="{y+10}" x2="{px:.1f}" y2="{y+h-4}" stroke="{t.ink}" stroke-width="1.2"/>')
    s.raw(f'<path d="M{px-4:.1f},{y+6} L{px+4:.1f},{y+6} L{px:.1f},{y+12} Z" fill="{t.ink}"/>')


def ill_sensor(s: SVG, t: Theme, x, y, w, h):
    # a sensor above a farrowing pen, two optical axes, floor line
    cx = x + w / 2
    top = y + 14
    s.raw(f'<rect x="{cx-11:.1f}" y="{top}" width="22" height="12" rx="2.5" fill="{t.ink}"/>')
    s.raw(f'<line x1="{cx:.1f}" y1="{y}" x2="{cx:.1f}" y2="{top}" stroke="{t.ink}" stroke-width="1.4"/>')
    floor = y + h - 12
    # depth axis straight down, RGB axis angled: two faint cones
    for dx, op in ((0, 0.9), (0.38, 0.55)):
        ax = cx + dx * w
        s.raw(f'<path d="M{cx:.1f},{top+12} L{ax-26:.1f},{floor} L{ax+26:.1f},{floor} Z" fill="{t.accent}" opacity="{0.12*op/0.9:.2f}"/>')
        s.raw(f'<line x1="{cx:.1f}" y1="{top+12}" x2="{ax:.1f}" y2="{floor}" stroke="{t.accent}" stroke-width="1.2" stroke-dasharray="2 4" opacity="{op}"/>')
    s.raw(f'<line x1="{x-4}" y1="{floor}" x2="{x+w+4}" y2="{floor}" stroke="{t.muted}" stroke-width="1.4"/>')
    # crate rails
    for rx in (x + 8, x + w - 8):
        s.raw(f'<line x1="{rx}" y1="{floor-26}" x2="{rx}" y2="{floor}" stroke="{t.rule}" stroke-width="2"/>')


def ill_wireframe(s: SVG, t: Theme, x, y, w, h):
    pw, ph = 78, 100
    ox = x + (w - pw) / 2
    oy = y + 3
    s.raw(f'<rect x="{ox:.1f}" y="{oy}" width="{pw}" height="{ph}" rx="3" fill="{t.canvas}" stroke="{t.rule}"/>')
    s.raw(f'<rect x="{ox:.1f}" y="{oy}" width="{pw}" height="10" rx="3" fill="{t.hairline}"/>')
    # avatar + title
    s.raw(f'<circle cx="{ox+12:.1f}" cy="{oy+26}" r="6" fill="{t.faint}" opacity="0.6"/>')
    s.raw(f'<rect x="{ox+23:.1f}" y="{oy+21}" width="34" height="4" rx="2" fill="{t.muted}"/>')
    s.raw(f'<rect x="{ox+23:.1f}" y="{oy+28}" width="22" height="3" rx="1.5" fill="{t.faint}" opacity="0.6"/>')
    # sidebar
    for i in range(4):
        s.raw(f'<rect x="{ox+6:.1f}" y="{oy+42+i*10}" width="18" height="3" rx="1.5" fill="{t.faint}" opacity="0.6"/>')
    # body lines, one accent (the publication list)
    for i in range(6):
        wdt = [42, 36, 44, 30, 40, 24][i]
        fill = t.accent if i == 0 else t.faint
        s.raw(f'<rect x="{ox+30:.1f}" y="{oy+42+i*9}" width="{wdt}" height="3" rx="1.5" fill="{fill}" opacity="{1 if i==0 else 0.6}"/>')


CARDS = [
    ("palettes", "Python · matplotlib",
     "Masterpiece palettes",
     "102 colour schemes for research figures, each extracted from a world-famous painting. Drops into matplotlib.",
     ill_palette),
    ("annotator", "Python · video annotation",
     "Spatiotemporal annotator",
     "Label animal video so every annotation carries both an identity and a duration.",
     ill_annotator),
    ("smartswine", "Company · SPM-01 Smart Piglet Monitor",
     "Smart Swine",
     "Sensing and robotics that predict piglet crushing and stillbirth risk, then intervene before losses happen.",
     ill_sensor),
    ("homepage", "Jekyll · SCSS",
     "Academic homepage template",
     "A clean, mobile-friendly template for personal academic sites: publications, projects, experience, reading.",
     ill_wireframe),
]


def research(t: Theme) -> SVG:
    H = 118
    s = SVG(W, H, t, "Research lines: UAV SLAM in broiler houses, broiler activity from overhead video, contactless respiration sensing")
    tiles = [
        ("UAV patrol & SLAM", "inside broiler houses", "LineGate-SLAM · in preparation"),
        ("Broiler activity & distribution", "from overhead video", "YOLO11 · under review"),
        ("Respiration sensing", "non-contact, sows and broilers", "video pipeline · under review"),
    ]
    n = len(tiles)
    gap = 18
    tw = (W - gap * (n - 1)) / n
    for i, (a, b, c) in enumerate(tiles):
        x = i * (tw + gap)
        s.raw(f'<rect x="{x+0.5:.1f}" y="0.5" width="{tw-1:.1f}" height="{H-1}" rx="6" fill="{t.card}" stroke="{t.rule}"/>')
        s.raw(f'<rect x="{x+1:.1f}" y="18" width="3" height="{H-36}" rx="1.5" fill="{t.accent}"/>')
        s.text(x + 24, 42, a, "serif", 19, t.ink)
        s.text(x + 24, 64, b, "serif-italic", 15, t.muted)
        s.text(x + 24, 94, c, "mono", 11, t.faint, letter_spacing=0.3)
    return s


# ---------------------------------------------------------------- main
if __name__ == "__main__":
    for t in THEMES.values():
        print(f"[{t.name}]")
        write("hero", hero(t))
        write("now", now(t))
        for key, eyebrow, title, body, draw in CARDS:
            write(f"card-{key}", card(t, key, eyebrow, title, body, draw))
        write("research", research(t))
