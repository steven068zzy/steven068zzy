#!/usr/bin/env python3
"""Generate the two SVGs for the profile README, light and dark.

Run from the repo root:  uv run --with fonttools tools/build.py

Text uses the viewer's system fonts (the same stack GitHub itself uses),
nothing is embedded. Widths are estimated with Helvetica for layout only.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets"
OUT.mkdir(exist_ok=True)

SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"

# layout-only metrics: Helvetica for sans, Menlo for mono; widths get a safety factor
_METRIC = {
    "sans": TTFont("/System/Library/Fonts/Helvetica.ttc", fontNumber=0),
    "mono": TTFont("/System/Library/Fonts/Menlo.ttc", fontNumber=0),
}
SAFETY = 1.08


def measure(text: str, face: str, size: float) -> float:
    f = _METRIC[face]
    cmap = f.getBestCmap()
    hmtx = f["hmtx"]
    upm = f["head"].unitsPerEm
    total = sum(hmtx[cmap.get(ord(c), cmap[ord("?")])][0] for c in text)
    return total * size / upm * SAFETY


@dataclass(frozen=True)
class Theme:
    name: str
    ink: str
    muted: str
    faint: str
    rule: str
    hairline: str
    canvas: str
    accent: str


THEMES = {
    "light": Theme("light", ink="#1F2328", muted="#656D76", faint="#8C959F",
                   rule="#D0D7DE", hairline="#E6EAEF", canvas="#FFFFFF", accent="#2F7D6B"),
    "dark": Theme("dark", ink="#E6EDF3", muted="#8B949E", faint="#6E7681",
                  rule="#30363D", hairline="#21262D", canvas="#0D1117", accent="#5DB39E"),
}


class SVG:
    def __init__(self, w: int, h: int, t: Theme, title: str):
        self.w, self.h, self.t, self.title = w, h, t, title
        self.parts: list[str] = []

    def text(self, x, y, s, face="sans", size=14, fill=None, weight=None, anchor="start"):
        fill = fill or self.t.ink
        attrs = [f'x="{x:.1f}"', f'y="{y:.1f}"', f'class="{face}"', f'font-size="{size}"', f'fill="{fill}"']
        if weight:
            attrs.append(f'font-weight="{weight}"')
        if anchor != "start":
            attrs.append(f'text-anchor="{anchor}"')
        right = x + measure(s, face, size) * (1.1 if weight else 1.0)
        if right > self.w - 2:
            print(f"  ! overflow: {s[:40]!r} ends at {right:.0f} > {self.w}")
        self.parts.append(f"<text {' '.join(attrs)}>{esc(s)}</text>")

    def raw(self, s: str):
        self.parts.append(s)

    def render(self) -> str:
        style = f".sans{{font-family:{SANS};}}.mono{{font-family:{MONO};}}"
        body = "\n".join(self.parts)
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
            f'viewBox="0 0 {self.w} {self.h}" role="img" aria-labelledby="t">\n'
            f'<title id="t">{esc(self.title)}</title>\n<style>{style}</style>\n{body}\n</svg>\n'
        )


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def write(name: str, svg: SVG):
    path = OUT / f"{name}-{svg.t.name}.svg"
    path.write_text(svg.render(), encoding="utf-8")
    print(f"  {path.relative_to(ROOT)}  {path.stat().st_size/1024:.1f} KB")


W = 900


def hero(t: Theme) -> SVG:
    H = 300
    s = SVG(W, H, t, "Ziyuan Zhao: robotics and computer vision for precision livestock farming. ziyuanzhao.org")
    x = 4

    # one <text> with tspans, so "Steven" follows the name whatever font the viewer has
    s.raw(f'<text x="{x-2}" y="112" class="sans">'
          f'<tspan font-size="58" font-weight="600" fill="{t.ink}">Ziyuan Zhao</tspan>'
          f'<tspan dx="14" font-size="26" fill="{t.muted}">Steven</tspan></text>')

    s.text(x, 162, "Robotics & computer vision", "sans", 22, t.ink)
    s.text(x, 192, "for precision livestock farming.", "sans", 22, t.ink)

    s.text(x, 234, "PhD researcher, Texas A&M  ·  Co-founder, Smart Swine", "sans", 15, t.muted)

    # the website, set as the one coloured line of text
    s.text(x, 276, "ziyuanzhao.org  →", "sans", 18, t.accent, weight=600)

    # --- right: broiler house plan with a patrolling drone
    hx, hy, hw, hh = 520, 34, 376, 232
    s.raw(f'<defs><pattern id="grid" width="16" height="16" patternUnits="userSpaceOnUse" x="{hx}" y="{hy}">'
          f'<path d="M16 0H0V16" fill="none" stroke="{t.hairline}" stroke-width="1"/></pattern></defs>')
    s.raw(f'<rect x="{hx}" y="{hy}" width="{hw}" height="{hh}" rx="4" fill="url(#grid)"/>')
    s.raw(f'<rect x="{hx}" y="{hy}" width="{hw}" height="{hh}" rx="4" fill="none" stroke="{t.rule}" stroke-width="1.2"/>')

    n_lines = 4
    pitch = hh / n_lines
    lane_y = []
    for i in range(n_lines):
        ly = hy + pitch * (i + 0.5)
        lane_y.append(ly)
        s.raw(f'<line x1="{hx+18}" y1="{ly:.1f}" x2="{hx+hw-18}" y2="{ly:.1f}" stroke="{t.muted}" stroke-width="1.6" stroke-linecap="round"/>')
        for px in range(int(hx + 34), int(hx + hw - 20), 34):
            s.raw(f'<circle cx="{px}" cy="{ly:.1f}" r="2.6" fill="{t.canvas}" stroke="{t.muted}" stroke-width="1.2"/>')
    for i in range(n_lines - 1):
        dy = (lane_y[i] + lane_y[i + 1]) / 2
        s.raw(f'<line x1="{hx+18}" y1="{dy:.1f}" x2="{hx+hw-18}" y2="{dy:.1f}" stroke="{t.faint}" stroke-width="1" stroke-dasharray="2 5" stroke-linecap="round"/>')

    gaps = [hy + 14] + [(lane_y[i] + lane_y[i + 1]) / 2 for i in range(n_lines - 1)] + [hy + hh - 14]
    ys = [gaps[0] + 2, gaps[1] - 9, gaps[2] + 9, gaps[3] - 9, gaps[4] - 2]
    xl, xr = hx + 30, hx + hw - 30
    d = f"M{xl},{ys[0]:.1f}"
    for i, yy in enumerate(ys):
        tx = xr if i % 2 == 0 else xl
        d += f" L{tx},{yy:.1f}"
        if i + 1 < len(ys):
            d += f" L{tx},{ys[i+1]:.1f}"
    s.raw(f'<path d="{d}" fill="none" stroke="{t.accent}" stroke-width="1.2" stroke-dasharray="1 6" stroke-linecap="round" opacity="0.9"/>')
    dur = "34s"
    s.raw(f'<g><circle r="9" fill="{t.accent}" opacity="0.18">'
          f'<animateMotion dur="{dur}" repeatCount="indefinite" path="{d}"/></circle>'
          f'<circle r="3.4" fill="{t.accent}">'
          f'<animateMotion dur="{dur}" repeatCount="indefinite" path="{d}"/></circle></g>')
    return s


def now(t: Theme) -> SVG:
    H = 44
    s = SVG(W, H, t, "Now: LineGate-SLAM, a multi-object-tracking review, SPM-01")
    items = [
        "LineGate-SLAM, UAV patrol in broiler houses",
        "multi-object tracking review",
        "SPM-01 piglet monitor",
    ]
    size = 15
    # single <text>: the browser flows the tspans, so widths never depend on our metrics
    parts = [f'<tspan class="mono" font-size="{size}" font-weight="600" fill="{t.accent}">$</tspan>',
             f'<tspan class="mono" font-size="{size}" font-weight="600" fill="{t.ink}" dx="6">now</tspan>']
    for i, it in enumerate(items):
        parts.append(f'<tspan font-size="{size}" fill="{t.ink}" dx="{18 if i == 0 else 10}">{esc(it)}</tspan>')
        if i < len(items) - 1:
            parts.append(f'<tspan font-size="{size}" fill="{t.faint}" dx="10">·</tspan>')
    parts.append(f'<tspan class="mono" font-size="{size}" fill="{t.accent}" dx="8">█'
                 f'<animate attributeName="fill-opacity" values="1;1;0;0" dur="1.1s" repeatCount="indefinite"/></tspan>')
    s.raw(f'<text x="4" y="28" class="sans">{"".join(parts)}</text>')
    est = measure("$ now " + "  ·  ".join(items) + " █", "sans", size) + 60
    if est > W - 2:
        print(f"  ! now line estimate {est:.0f} > {W}")
    return s


if __name__ == "__main__":
    for t in THEMES.values():
        print(f"[{t.name}]")
        write("hero", hero(t))
        write("now", now(t))
