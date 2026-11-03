#!/usr/bin/env python3
"""Generate the hero SVG for the profile README.

Run from the repo root:  uv run tools/build.py

One self-contained dark panel that reads the same on GitHub's light and dark
themes (no dependency on prefers-color-scheme). Text uses the viewer's system
fonts, nothing is embedded.
"""
from __future__ import annotations

import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets"
OUT.mkdir(exist_ok=True)

SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"

# panel palette (GitHub dark tokens + one accent)
PANEL = "#0D1117"
PANEL_EDGE = "#30363D"
FLOOR = "#161B22"
FLOOR_EDGE = "#30363D"
GRID = "#1C2129"
INK = "#E6EDF3"
MUTED = "#8B949E"
FAINT = "#6E7681"
LINE = "#484F58"
ACCENT = "#5DB39E"
ACCENT_DIM = "#2F5F53"
BIRD = "#E6EDF3"
BIRD_EDGE = "#9DA7B3"


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class SVG:
    def __init__(self, w: int, h: int, title: str):
        self.w, self.h, self.title = w, h, title
        self.parts: list[str] = []

    def raw(self, s: str):
        self.parts.append(s)

    def text(self, x, y, s, face="sans", size=14, fill=INK, weight=None, anchor="start", opacity=None):
        attrs = [f'x="{x:.1f}"', f'y="{y:.1f}"', f'class="{face}"', f'font-size="{size}"', f'fill="{fill}"']
        if weight:
            attrs.append(f'font-weight="{weight}"')
        if anchor != "start":
            attrs.append(f'text-anchor="{anchor}"')
        if opacity is not None:
            attrs.append(f'opacity="{opacity}"')
        self.parts.append(f"<text {' '.join(attrs)}>{esc(s)}</text>")

    def render(self) -> str:
        style = f".sans{{font-family:{SANS};}}.mono{{font-family:{MONO};}}"
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
            f'viewBox="0 0 {self.w} {self.h}" role="img" aria-labelledby="t">\n'
            f'<title id="t">{esc(self.title)}</title>\n<style>{style}</style>\n'
            + "\n".join(self.parts) + "\n</svg>\n"
        )


# ------------------------------------------------------------------ scene parts
def bird(s: SVG, x, y, ang_deg, sc=1.0):
    """A broiler seen from above: body, head, beak."""
    a = math.radians(ang_deg)
    hx, hy = x + math.cos(a) * 17 * sc, y + math.sin(a) * 17 * sc
    bx, by = x + math.cos(a) * 23 * sc, y + math.sin(a) * 23 * sc
    # shadow
    s.raw(f'<ellipse cx="{x+2:.1f}" cy="{y+3:.1f}" rx="{16*sc:.1f}" ry="{11*sc:.1f}" '
          f'transform="rotate({ang_deg} {x+2:.1f} {y+3:.1f})" fill="#000" opacity="0.35"/>')
    s.raw(f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{16*sc:.1f}" ry="{11*sc:.1f}" '
          f'transform="rotate({ang_deg} {x:.1f} {y:.1f})" fill="{BIRD}" stroke="{BIRD_EDGE}" stroke-width="0.8"/>')
    # wing crease
    s.raw(f'<path d="M{x-6*sc:.1f},{y:.1f} Q{x:.1f},{y-3*sc:.1f} {x+7*sc:.1f},{y:.1f}" fill="none" stroke="{BIRD_EDGE}" '
          f'stroke-width="0.7" opacity="0.7" transform="rotate({ang_deg} {x:.1f} {y:.1f})"/>')
    s.raw(f'<circle cx="{hx:.1f}" cy="{hy:.1f}" r="{5.6*sc:.1f}" fill="{BIRD}" stroke="{BIRD_EDGE}" stroke-width="0.8"/>')
    # beak
    pa = a + math.pi / 2
    s.raw(f'<path d="M{hx+math.cos(pa)*2.2:.1f},{hy+math.sin(pa)*2.2:.1f} L{bx:.1f},{by:.1f} '
          f'L{hx-math.cos(pa)*2.2:.1f},{hy-math.sin(pa)*2.2:.1f} Z" fill="#D9A441"/>')


def bird_bbox(x, y, ang_deg, sc=1.0):
    a = math.radians(ang_deg)
    rx, ry = 16 * sc, 11 * sc
    ex = math.sqrt((rx * math.cos(a)) ** 2 + (ry * math.sin(a)) ** 2)
    ey = math.sqrt((rx * math.sin(a)) ** 2 + (ry * math.cos(a)) ** 2)
    bx, by = x + math.cos(a) * 23 * sc, y + math.sin(a) * 23 * sc
    x0, x1 = min(x - ex, bx) - 4, max(x + ex, bx) + 4
    y0, y1 = min(y - ey, by) - 4, max(y + ey, by) + 4
    return x0, y0, x1 - x0, y1 - y0


def brackets(s: SVG, x, y, w, h, color=ACCENT, L=7, sw=1.5):
    """Corner brackets instead of a full box."""
    for cx, cy, dx, dy in ((x, y, 1, 1), (x + w, y, -1, 1), (x, y + h, 1, -1), (x + w, y + h, -1, -1)):
        s.raw(f'<path d="M{cx:.1f},{cy+dy*L:.1f} L{cx:.1f},{cy:.1f} L{cx+dx*L:.1f},{cy:.1f}" '
              f'fill="none" stroke="{color}" stroke-width="{sw}" stroke-linecap="round"/>')


def label(s: SVG, x, y, txt):
    w = 7 * len(txt) + 10
    s.raw(f'<rect x="{x:.1f}" y="{y-11:.1f}" width="{w}" height="14" rx="3" fill="{ACCENT}"/>')
    s.text(x + 5, y, txt, "mono", 10, PANEL, weight=600)


def trail(s: SVG, pts, color=ACCENT):
    d = "M" + " L".join(f"{px:.1f},{py:.1f}" for px, py in pts)
    s.raw(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.2" stroke-dasharray="3 4" opacity="0.7"/>')
    for px, py in pts[:-1]:
        s.raw(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="1.8" fill="{color}" opacity="0.7"/>')


def drone_shadow(s: SVG, x, y, sc=1.0):
    """Blurred shadow on the floor, offset so the aircraft reads as airborne."""
    s.raw(f'<ellipse cx="{x+12*sc:.1f}" cy="{y+22*sc:.1f}" rx="{40*sc:.1f}" ry="{26*sc:.1f}" fill="#000" opacity="0.5" filter="url(#blur)"/>')


def drone(s: SVG, x, y, sc=1.0):
    """Quadcopter from above, nose pointing left (toward its camera footprint)."""
    arm = 30 * sc
    s.raw(f'<g transform="translate({x:.1f},{y:.1f}) scale({sc})">')
    # prop discs first (they sit under the arms visually? no: props are on top, but the
    # translucent disc goes under so the arm stays visible through it)
    motors = [(45, 20), (135, 70), (225, 115), (315, 160)]
    for a, blade in motors:
        mx, my = math.cos(math.radians(a)) * 30, math.sin(math.radians(a)) * 30
        s.raw(f'<circle cx="{mx:.1f}" cy="{my:.1f}" r="15" fill="#FFFFFF" opacity="0.07"/>')
        s.raw(f'<circle cx="{mx:.1f}" cy="{my:.1f}" r="15" fill="none" stroke="#C9D1D9" stroke-width="0.6" opacity="0.45"/>')
    # arms
    for a, _ in motors:
        ax, ay = math.cos(math.radians(a)) * 30, math.sin(math.radians(a)) * 30
        s.raw(f'<line x1="0" y1="0" x2="{ax:.1f}" y2="{ay:.1f}" stroke="#C9D1D9" stroke-width="6" stroke-linecap="round"/>')
        s.raw(f'<line x1="0" y1="0" x2="{ax:.1f}" y2="{ay:.1f}" stroke="#6E7681" stroke-width="1.6" stroke-linecap="round"/>')
    # body: lower plate, upper plate, battery
    s.raw('<rect x="-17" y="-11" width="34" height="22" rx="7" fill="#E6EDF3"/>')
    s.raw('<rect x="-12" y="-7" width="24" height="14" rx="4" fill="#C9D1D9"/>')
    s.raw('<rect x="-3" y="-5" width="12" height="10" rx="2" fill="#8B949E"/>')
    # gimbal camera at the nose
    s.raw('<circle cx="-18" cy="0" r="6" fill="#30363D" stroke="#C9D1D9" stroke-width="1.2"/>')
    s.raw(f'<circle cx="-18" cy="0" r="2.8" fill="{ACCENT}"/>')
    # rear LED
    s.raw('<circle cx="15" cy="0" r="1.8" fill="#D9534F"/>')
    # motors and blades on top
    for a, blade in motors:
        mx, my = math.cos(math.radians(a)) * 30, math.sin(math.radians(a)) * 30
        s.raw(f'<ellipse cx="{mx:.1f}" cy="{my:.1f}" rx="14" ry="2.6" fill="#E6EDF3" opacity="0.9" '
              f'transform="rotate({blade} {mx:.1f} {my:.1f})"/>')
        s.raw(f'<circle cx="{mx:.1f}" cy="{my:.1f}" r="5" fill="#30363D" stroke="#C9D1D9" stroke-width="1.2"/>')
        s.raw(f'<circle cx="{mx:.1f}" cy="{my:.1f}" r="1.6" fill="#C9D1D9"/>')
    s.raw('</g>')


def scene(s: SVG, x, y, w, h):
    """Overhead camera view of a broiler pen, a drone's footprint, detections and tracks."""
    s.raw(f'<defs><clipPath id="floor"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8"/></clipPath>'
          f'<pattern id="tile" width="22" height="22" patternUnits="userSpaceOnUse" x="{x}" y="{y}">'
          f'<path d="M22 0H0V22" fill="none" stroke="{GRID}" stroke-width="1"/></pattern>'
          f'<radialGradient id="glow" cx="50%" cy="50%" r="50%">'
          f'<stop offset="0" stop-color="{ACCENT}" stop-opacity="0.22"/><stop offset="1" stop-color="{ACCENT}" stop-opacity="0"/></radialGradient>'
          f'<filter id="blur" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="5"/></filter></defs>')
    s.raw(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{FLOOR}"/>')
    s.raw(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="url(#tile)"/>')
    s.raw(f'<g clip-path="url(#floor)">')

    # feeder line with pans, and a drinker line
    fy = y + h * 0.62
    s.raw(f'<line x1="{x}" y1="{fy:.1f}" x2="{x+w}" y2="{fy:.1f}" stroke="{LINE}" stroke-width="2.2"/>')
    for px in range(int(x + 24), int(x + w), 46):
        s.raw(f'<circle cx="{px}" cy="{fy:.1f}" r="6" fill="{FLOOR}" stroke="{LINE}" stroke-width="1.8"/>')
        s.raw(f'<circle cx="{px}" cy="{fy:.1f}" r="2" fill="{LINE}"/>')
    dy = y + h * 0.22
    s.raw(f'<line x1="{x}" y1="{dy:.1f}" x2="{x+w}" y2="{dy:.1f}" stroke="{LINE}" stroke-width="1.2" stroke-dasharray="3 6"/>')

    # drone camera footprint: everything inside is what the model sees
    fx, fy0, fw, fh = x + 80, y + 34, 206, 150
    s.raw(f'<rect x="{fx}" y="{fy0}" width="{fw}" height="{fh}" rx="6" fill="url(#glow)"/>')
    s.raw(f'<rect x="{fx}" y="{fy0}" width="{fw}" height="{fh}" rx="6" fill="none" stroke="{ACCENT}" stroke-width="1" stroke-dasharray="4 5" opacity="0.8"/>')

    # birds: (x, y, heading, scale, detected?)
    birds = [
        (x + 44, y + 70, 200, 0.95, False),
        (x + 128, y + 66, 15, 1.0, True),
        (x + 196, y + 92, -40, 1.0, True),
        (x + 246, y + 76, 160, 0.9, True),
        (x + 150, y + 140, 70, 1.0, True),
        (x + 222, y + 150, -120, 0.95, True),
        (x + 332, y + 200, 110, 0.9, False),
        (x + 70, y + 196, 350, 0.95, False),
        (x + 250, y + 228, 30, 1.0, False),
        (x + 160, y + 230, 190, 0.9, False),
    ]
    # tracks for two birds (where they came from)
    trail(s, [(x + 60, y + 118), (x + 92, y + 134), (x + 122, y + 142), (x + 150, y + 140)])
    trail(s, [(x + 186, y + 192), (x + 202, y + 172), (x + 222, y + 150)])
    for bx, by, ang, sc, det in birds:
        bird(s, bx, by, ang, sc)
    for bx, by, ang, sc, det in birds:
        if det:
            brackets(s, *bird_bbox(bx, by, ang, sc))
    # two labels only, sitting on the top-left corner of their boxes
    for idx, conf in ((1, "broiler 0.97"), (5, "broiler 0.94")):
        bx, by, ang, sc, _ = birds[idx]
        x0, y0, _, _ = bird_bbox(bx, by, ang, sc)
        label(s, x0, y0 - 5, conf)

    dx_, dy_ = x + 334, y + 100
    drone_shadow(s, dx_, dy_, 1.0)
    s.raw("</g>")
    s.raw(f'<rect x="{x+0.5}" y="{y+0.5}" width="{w-1}" height="{h-1}" rx="8" fill="none" stroke="{FLOOR_EDGE}"/>')
    # the aircraft hovers to the right of its (forward-tilted) camera footprint
    drone(s, dx_, dy_, 1.0)


# ------------------------------------------------------------------ hero
W, H = 900, 372


def hero() -> SVG:
    s = SVG(W, H, "Ziyuan Zhao: robotics and computer vision for precision livestock farming. ziyuanzhao.org")
    s.raw(f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="10" fill="{PANEL}" stroke="{PANEL_EDGE}"/>')
    x = 40
    s.raw(f'<text x="{x-2}" y="118" class="sans">'
          f'<tspan font-size="56" font-weight="600" fill="{INK}">Ziyuan Zhao</tspan>'
          f'<tspan dx="14" font-size="24" fill="{MUTED}">Steven</tspan></text>')
    s.text(x, 166, "Robotics & computer vision", "sans", 22, INK)
    s.text(x, 196, "for precision livestock farming.", "sans", 22, INK)
    s.text(x, 238, "PhD researcher, Texas A&M  ·  Co-founder, Smart Swine", "sans", 15, MUTED)
    s.text(x, 280, "ziyuanzhao.org  →", "sans", 18, ACCENT, weight=600)

    scene(s, 486, 28, 384, 262)

    # now line along the bottom
    s.raw(f'<line x1="{x}" y1="316" x2="{W-30}" y2="316" stroke="{PANEL_EDGE}" stroke-width="1"/>')
    items = ["LineGate-SLAM, UAV patrol in broiler houses", "multi-object tracking review", "SPM-01 piglet monitor"]
    parts = [f'<tspan class="mono" font-size="15" font-weight="600" fill="{ACCENT}">$</tspan>',
             f'<tspan class="mono" font-size="15" font-weight="600" fill="{INK}" dx="6">now</tspan>']
    for i, it in enumerate(items):
        parts.append(f'<tspan font-size="15" fill="{INK}" dx="{18 if i == 0 else 10}">{esc(it)}</tspan>')
        if i < len(items) - 1:
            parts.append(f'<tspan font-size="15" fill="{FAINT}" dx="10">·</tspan>')
    parts.append(f'<tspan class="mono" font-size="15" fill="{ACCENT}" dx="8">█'
                 f'<animate attributeName="fill-opacity" values="1;1;0;0" dur="1.1s" repeatCount="indefinite"/></tspan>')
    s.raw(f'<text x="{x}" y="347" class="sans">{"".join(parts)}</text>')
    return s


if __name__ == "__main__":
    svg = hero()
    path = OUT / "hero.svg"
    path.write_text(svg.render(), encoding="utf-8")
    print(f"  {path.relative_to(ROOT)}  {path.stat().st_size/1024:.1f} KB")
