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


# ------------------------------------------------------------------ isometric scene
K = 0.84                      # world unit -> px
CX, SY = 0.866 * K, 0.5 * K   # 2:1-ish true isometric


class Iso:
    """Project world (x, y, z) onto the page; x runs right-down, y left-down, z up."""
    def __init__(self, ox, oy):
        self.ox, self.oy = ox, oy

    def p(self, x, y, z=0.0):
        return self.ox + (x - y) * CX, self.oy + (x + y) * SY - z * K

    def pts(self, seq):
        return " ".join(f"{px:.1f},{py:.1f}" for px, py in (self.p(*q) for q in seq))


def shade(hex_, f):
    """Lighten (f>1) or darken (f<1) a hex colour."""
    r, g, b = (int(hex_[i:i + 2], 16) for i in (1, 3, 5))
    r, g, b = (max(0, min(255, int(c * f))) for c in (r, g, b))
    return f"#{r:02X}{g:02X}{b:02X}"


def cuboid(s: SVG, iso: Iso, x, y, z, lx, ly, lz, color, stroke=None, sw=0.7, rx_top=None):
    """Solid box: top, right (x+lx) and left (y+ly) faces, lit from the upper left."""
    top = [(x, y, z + lz), (x + lx, y, z + lz), (x + lx, y + ly, z + lz), (x, y + ly, z + lz)]
    right = [(x + lx, y, z), (x + lx, y + ly, z), (x + lx, y + ly, z + lz), (x + lx, y, z + lz)]
    left = [(x, y + ly, z), (x + lx, y + ly, z), (x + lx, y + ly, z + lz), (x, y + ly, z + lz)]
    st = f' stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round"' if stroke else ""
    s.raw(f'<polygon points="{iso.pts(left)}" fill="{shade(color, 0.72)}"{st}/>')
    s.raw(f'<polygon points="{iso.pts(right)}" fill="{shade(color, 0.86)}"{st}/>')
    s.raw(f'<polygon points="{iso.pts(top)}" fill="{color}"{st}/>')


def wire_box(s: SVG, iso: Iso, x, y, z, lx, ly, lz, color, sw=1.1):
    """3-D detection box: back edges faint, front edges solid."""
    c = lambda i, j, k: (x + i * lx, y + j * ly, z + k * lz)
    edges = [((0,0,0),(1,0,0)),((1,0,0),(1,1,0)),((1,1,0),(0,1,0)),((0,1,0),(0,0,0)),
             ((0,0,1),(1,0,1)),((1,0,1),(1,1,1)),((1,1,1),(0,1,1)),((0,1,1),(0,0,1)),
             ((0,0,0),(0,0,1)),((1,0,0),(1,0,1)),((1,1,0),(1,1,1)),((0,1,0),(0,1,1))]
    for a, b in edges:
        back = (a[0] == 0 and b[0] == 0 and a[1] == 0 and b[1] == 0) or (a == (0,0,0) and b == (0,0,1)) \
               or ((a[0] + b[0] == 0) and a[2] == 0 and b[2] == 0) or ((a[1] + b[1] == 0) and a[2] == 0 and b[2] == 0)
        p1, p2 = iso.p(*c(*a)), iso.p(*c(*b))
        s.raw(f'<line x1="{p1[0]:.1f}" y1="{p1[1]:.1f}" x2="{p2[0]:.1f}" y2="{p2[1]:.1f}" stroke="{color}" '
              f'stroke-width="{sw}" opacity="{0.35 if back else 0.95}" stroke-linecap="round"/>')


def label(s: SVG, x, y, txt):
    w = 7 * len(txt) + 10
    s.raw(f'<rect x="{x:.1f}" y="{y-11:.1f}" width="{w}" height="{14}" rx="3" fill="{ACCENT}"/>')
    s.text(x + 5, y, txt, "mono", 10, PANEL, weight=600)


def floor_ellipse(s: SVG, iso: Iso, x, y, r, **kw):
    px, py = iso.p(x, y, 0)
    attrs = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in kw.items())
    s.raw(f'<ellipse cx="{px:.1f}" cy="{py:.1f}" rx="{r*1.22*K:.1f}" ry="{r*0.71*K:.1f}" {attrs}/>')


def bird3d(s: SVG, iso: Iso, x, y, facing=1, sc=1.0):
    """White broiler sprite standing at world (x, y). facing=1 looks screen-right."""
    px, py = iso.p(x, y, 0)
    s.raw(f'<ellipse cx="{px+2:.1f}" cy="{py:.1f}" rx="{14*sc:.1f}" ry="{5.5*sc:.1f}" fill="#000" opacity="0.45" filter="url(#blur2)"/>')
    s.raw(f'<g transform="translate({px:.1f},{py:.1f}) scale({facing*sc},{sc})">')
    # legs and feet
    for lx in (-1, 5):
        s.raw(f'<path d="M{lx},-6 L{lx+1},-0.5 M{lx-2.5},-0.5 L{lx+1},-0.5 L{lx+3.5},-0.5" fill="none" stroke="#E0A030" stroke-width="1.3" stroke-linecap="round"/>')
    # tail fan
    s.raw('<path d="M-9,-14 L-18,-23 L-20,-18 L-21,-13 L-19,-9 L-9,-9 Z" fill="#CBD3DB" stroke="#AEB8C2" stroke-width="0.6"/>')
    s.raw('<path d="M-11,-12 L-19,-19 M-11,-11 L-20,-14 M-11,-10 L-19,-10" fill="none" stroke="#AEB8C2" stroke-width="0.5" opacity="0.8"/>')
    # body with lit back
    s.raw('<ellipse cx="0" cy="-11" rx="13" ry="8.5" transform="rotate(8 0 -11)" fill="url(#birdside)" stroke="#AEB8C2" stroke-width="0.7"/>')
    # folded wing
    s.raw('<path d="M-6,-13 C-2,-18 7,-17 10,-12 C6,-9 -1,-8 -6,-13 Z" fill="#D7DEE5" stroke="#B9C2CC" stroke-width="0.6"/>')
    # neck and head
    s.raw('<path d="M8,-16 C10,-20 12,-23 14,-24 L17,-22 C16,-19 13,-15 11,-13 Z" fill="#E9EEF2" stroke="#AEB8C2" stroke-width="0.5"/>')
    s.raw('<circle cx="16" cy="-24" r="4.6" fill="url(#birdside)" stroke="#AEB8C2" stroke-width="0.7"/>')
    s.raw('<path d="M13,-28 L14.5,-30.5 L16,-28.5 L17.5,-31 L19,-28.5" fill="#C9473C" stroke="#C9473C" stroke-width="1.2" stroke-linejoin="round"/>')
    s.raw('<circle cx="17.6" cy="-25" r="0.9" fill="#1F2328"/>')
    s.raw('<path d="M20.2,-25.5 L25,-24 L20.2,-22.6 Z" fill="#E0A030"/>')
    s.raw('<path d="M18.5,-21.5 L19,-19.5" stroke="#C9473C" stroke-width="1.4" stroke-linecap="round"/>')  # wattle
    s.raw('</g>')


def drone3d(s: SVG, iso: Iso, x, y, z):
    """Quadcopter hovering at world (x, y, z), nose toward +y (screen left-down)."""
    cx, cy = iso.p(x, y, z)
    arm = 15
    motors = [(x + arm, y + arm), (x - arm, y + arm), (x - arm, y - arm), (x + arm, y - arm)]
    # arms
    for mx, my in motors:
        ax, ay = iso.p(mx, my, z)
        s.raw(f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{ax:.1f}" y2="{ay:.1f}" stroke="#C9D1D9" stroke-width="5.5" stroke-linecap="round"/>')
        s.raw(f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{ax:.1f}" y2="{ay:.1f}" stroke="#6E7681" stroke-width="1.4" stroke-linecap="round"/>')
    # body box and gimbal under the nose
    cuboid(s, iso, x - 8, y - 10, z - 3, 16, 20, 7, "#E6EDF3", stroke="#8B949E", sw=0.6)
    gx, gy = iso.p(x, y + 10, z - 6)
    s.raw(f'<circle cx="{gx:.1f}" cy="{gy:.1f}" r="5.2" fill="#30363D" stroke="#C9D1D9" stroke-width="1.1"/>')
    s.raw(f'<circle cx="{gx:.1f}" cy="{gy:.1f}" r="2.4" fill="{ACCENT}"/>')
    tx, ty = iso.p(x, y - 10, z + 4)
    s.raw(f'<circle cx="{tx:.1f}" cy="{ty:.1f}" r="1.5" fill="#D9534F"/>')
    # motors and prop discs
    for i, (mx, my) in enumerate(motors):
        ax, ay = iso.p(mx, my, z + 1)
        s.raw(f'<rect x="{ax-3.5:.1f}" y="{ay-2.5:.1f}" width="7" height="6" rx="1.8" fill="#30363D" stroke="#C9D1D9" stroke-width="0.9"/>')
        px, py = iso.p(mx, my, z + 5)
        s.raw(f'<ellipse cx="{px:.1f}" cy="{py:.1f}" rx="15" ry="7.5" fill="#FFFFFF" opacity="0.08"/>')
        s.raw(f'<ellipse cx="{px:.1f}" cy="{py:.1f}" rx="15" ry="7.5" fill="none" stroke="#C9D1D9" stroke-width="0.6" opacity="0.5"/>')
        s.raw(f'<ellipse cx="{px:.1f}" cy="{py:.1f}" rx="14" ry="2" fill="#E6EDF3" opacity="0.9" transform="rotate({[20, 110, 65, 150][i]} {px:.1f} {py:.1f})"/>')
        s.raw(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="1.6" fill="#C9D1D9"/>')


def ugv3d(s: SVG, iso: Iso, x, y, arm):
    """Tracked robot, 44 x 30 x 14 world units, parked with its nose toward +x.
    arm = ((base), (elbow), (wrist), (tip)) in world coordinates."""
    L, Wd, H = 44, 30, 14
    # shadow + tracks + chassis + deck
    floor_ellipse(s, iso, x + L / 2 + 4, y + Wd / 2 + 6, 26, fill="#000", opacity="0.4", filter="url(#blur2)")
    for ty in (y - 1, y + Wd - 7):
        cuboid(s, iso, x - 2, ty, 0, L + 4, 8, 8, "#2B3139", stroke="#484F58", sw=0.6)
        # tread marks on the visible long face (y + 8)
        for tx in range(int(x + 1), int(x + L + 1), 4):
            a, b = iso.p(tx, ty + 8, 1), iso.p(tx, ty + 8, 7)
            s.raw(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="#484F58" stroke-width="1"/>')
    cuboid(s, iso, x, y + 4, 5, L, Wd - 8, H - 4, "#AEB7C2", stroke="#6E7681", sw=0.6)
    cuboid(s, iso, x + 4, y + 7, H + 1, L - 14, Wd - 14, 2, "#8B949E")
    # lidar puck at the front
    lx, ly = x + L - 8, y + Wd / 2
    cuboid(s, iso, lx - 4, ly - 4, H + 1, 8, 8, 6, "#30363D", stroke="#C9D1D9", sw=0.8)
    tpx, tpy = iso.p(lx, ly, H + 7)
    s.raw(f'<ellipse cx="{tpx:.1f}" cy="{tpy:.1f}" rx="4.8" ry="2.4" fill="#484F58" stroke="#C9D1D9" stroke-width="0.8"/>')
    hx, hy = iso.p(x + L, y + Wd / 2, 9)
    s.raw(f'<circle cx="{hx:.1f}" cy="{hy:.1f}" r="1.5" fill="{ACCENT}"/>')
    # arm
    base, elbow, wrist, tip = arm
    pb, pe, pw, pt = (iso.p(*q) for q in (base, elbow, wrist, tip))
    bx, by = iso.p(base[0], base[1], base[2] - 3)
    s.raw(f'<ellipse cx="{bx:.1f}" cy="{by:.1f}" rx="7" ry="3.5" fill="#30363D" stroke="#C9D1D9" stroke-width="1"/>')
    d = f"M{pb[0]:.1f},{pb[1]:.1f} L{pe[0]:.1f},{pe[1]:.1f} L{pw[0]:.1f},{pw[1]:.1f}"
    s.raw(f'<path d="{d}" fill="none" stroke="#6E7681" stroke-width="8.5" stroke-linecap="round" stroke-linejoin="round"/>')
    s.raw(f'<path d="{d}" fill="none" stroke="#E6EDF3" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>')
    s.raw(f'<path d="{d}" fill="none" stroke="#FFFFFF" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" opacity="0.7" transform="translate(-1,-1.4)"/>')
    for (jx, jy), r in ((pb, 5.2), (pe, 4.6), (pw, 4)):
        s.raw(f'<circle cx="{jx:.1f}" cy="{jy:.1f}" r="{r}" fill="#30363D" stroke="#C9D1D9" stroke-width="1.2"/>')
        s.raw(f'<circle cx="{jx:.1f}" cy="{jy:.1f}" r="{r*0.38:.1f}" fill="#C9D1D9"/>')
    # gripper: short link to the tip, then two fingers
    s.raw(f'<line x1="{pw[0]:.1f}" y1="{pw[1]:.1f}" x2="{pt[0]:.1f}" y2="{pt[1]:.1f}" stroke="#C9D1D9" stroke-width="3.2" stroke-linecap="round"/>')
    ux, uy = pt[0] - pw[0], pt[1] - pw[1]
    n = math.hypot(ux, uy) or 1
    ux, uy = ux / n, uy / n
    nx, ny = -uy, ux
    s.raw(f'<line x1="{pt[0]-nx*5:.1f}" y1="{pt[1]-ny*5:.1f}" x2="{pt[0]+nx*5:.1f}" y2="{pt[1]+ny*5:.1f}" stroke="#C9D1D9" stroke-width="2.6" stroke-linecap="round"/>')
    for sgn in (-1, 1):
        fx, fy = pt[0] + nx * 4.2 * sgn, pt[1] + ny * 4.2 * sgn
        s.raw(f'<line x1="{fx:.1f}" y1="{fy:.1f}" x2="{fx+ux*7:.1f}" y2="{fy+uy*7:.1f}" stroke="#C9D1D9" stroke-width="2.2" stroke-linecap="round"/>')


def scene(s: SVG, x, y, w, h):
    """Isometric broiler-house floor: feeder line, birds, a hovering drone whose camera
    footprint holds the detections, and a ground robot inspecting a feeder pan."""
    FW, FD = 300, 200                 # floor size in world units
    iso = Iso(x + w / 2 + (FD - FW) * CX / 2 + 4, y + 56)
    s.raw(f'<defs><filter id="blur" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="5"/></filter>'
          f'<filter id="blur2" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="2"/></filter>'
          f'<radialGradient id="birdside" cx="0.38" cy="0.32" r="0.75"><stop offset="0" stop-color="#F7F9FB"/>'
          f'<stop offset="1" stop-color="#BFC8D1"/></radialGradient>'
          f'<radialGradient id="glow" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="{ACCENT}" stop-opacity="0.26"/>'
          f'<stop offset="1" stop-color="{ACCENT}" stop-opacity="0"/></radialGradient></defs>')

    # floor slab with thickness
    T = 10
    s.raw(f'<polygon points="{iso.pts([(0, FD, 0), (FW, FD, 0), (FW, FD, -T), (0, FD, -T)])}" fill="#0B0F14" stroke="{FLOOR_EDGE}" stroke-width="0.8"/>')
    s.raw(f'<polygon points="{iso.pts([(FW, 0, 0), (FW, FD, 0), (FW, FD, -T), (FW, 0, -T)])}" fill="#10151C" stroke="{FLOOR_EDGE}" stroke-width="0.8"/>')
    s.raw(f'<polygon points="{iso.pts([(0, 0, 0), (FW, 0, 0), (FW, FD, 0), (0, FD, 0)])}" fill="{FLOOR}" stroke="{FLOOR_EDGE}" stroke-width="0.8"/>')
    for gx in range(25, FW, 25):
        s.raw(f'<polyline points="{iso.pts([(gx, 0, 0), (gx, FD, 0)])}" fill="none" stroke="{GRID}" stroke-width="0.8"/>')
    for gy in range(25, FD, 25):
        s.raw(f'<polyline points="{iso.pts([(0, gy, 0), (FW, gy, 0)])}" fill="none" stroke="{GRID}" stroke-width="0.8"/>')

    # camera footprint on the floor, with its glow
    fp = [(95, 50), (225, 50), (225, 140), (95, 140)]
    s.raw(f'<polygon points="{iso.pts([(a, b, 0) for a, b in fp])}" fill="url(#glow)"/>')
    s.raw(f'<polygon points="{iso.pts([(a, b, 0) for a, b in fp])}" fill="none" stroke="{ACCENT}" stroke-width="1" stroke-dasharray="4 5" opacity="0.85"/>')

    # tracks on the floor (where two birds came from)
    for pts in ([(60, 122), (84, 126), (108, 119), (130, 112)], [(242, 136), (226, 122), (205, 110)]):
        s.raw(f'<polyline points="{iso.pts([(a, b, 0) for a, b in pts])}" fill="none" stroke="{ACCENT}" stroke-width="1.2" stroke-dasharray="3 4" opacity="0.7"/>')
        for a, b in pts[:-1]:
            floor_ellipse(s, iso, a, b, 1.6, fill=ACCENT, opacity="0.7")

    # drone shadow + camera frustum (drawn behind everything that stands on the floor)
    DX, DY, DZ = 160, 30, 80
    floor_ellipse(s, iso, DX + 6, DY + 8, 18, fill="#000", opacity="0.45", filter="url(#blur)")
    cam = iso.p(DX, DY + 10, DZ - 6)
    for a, b in fp:
        q = iso.p(a, b, 0)
        s.raw(f'<line x1="{cam[0]:.1f}" y1="{cam[1]:.1f}" x2="{q[0]:.1f}" y2="{q[1]:.1f}" stroke="{ACCENT}" stroke-width="0.8" opacity="0.28"/>')

    # drinker line at the back (pipe at height, nipples)
    a, b = iso.p(8, 20, 20), iso.p(FW - 8, 20, 20)
    s.raw(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="{LINE}" stroke-width="1.6" stroke-linecap="round"/>')
    for wx in range(30, FW - 10, 22):
        a, b = iso.p(wx, 20, 20), iso.p(wx, 20, 15)
        s.raw(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="{LINE}" stroke-width="1.2"/>')

    # objects, painted back to front
    items = []
    FY = 128                                   # feeder line depth
    for px_ in range(35, FW - 20, 50):          # pans with drop tubes, pipe segments between them
        items.append((px_ + FY, "pan", px_))
    items.append((0, "pipe", None))
    birds = [  # (x, y, facing, scale, detected)
        (50, 50, 1, 0.9, False), (110, 70, -1, 0.95, True), (165, 75, 1, 0.95, True),
        (205, 110, -1, 0.95, True), (130, 112, 1, 0.95, True), (280, 80, -1, 0.9, False),
        (255, 30, 1, 0.85, False), (150, 170, -1, 0.95, False), (232, 172, 1, 0.95, False),
        (282, 150, -1, 0.9, False), (112, 178, 1, 0.9, False), (268, 192, -1, 0.9, False),
    ]
    for bx, by, f, sc, det in birds:
        items.append((bx + by, "bird", (bx, by, f, sc, det)))
    items.append((36 + 150 + 30, "ugv", None))
    items.sort(key=lambda t: t[0])

    for depth, kind, payload in items:
        if kind == "pipe":
            a, b = iso.p(8, FY, 18), iso.p(FW - 8, FY, 18)
            s.raw(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="{LINE}" stroke-width="2.4" stroke-linecap="round"/>')
        elif kind == "pan":
            px_ = payload
            a, b = iso.p(px_, FY, 18), iso.p(px_, FY, 5)
            s.raw(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="{LINE}" stroke-width="1.6"/>')
            floor_ellipse(s, iso, px_, FY, 7, fill="#2B3139", stroke=LINE, stroke_width="1.2")
            floor_ellipse(s, iso, px_, FY, 3, fill=LINE)
        elif kind == "bird":
            bx, by, f, sc, det = payload
            bird3d(s, iso, bx, by, f, sc)
            if det:
                wire_box(s, iso, bx - 14, by - 9, 0, 30, 18, 24, ACCENT)
        elif kind == "ugv":
            ugv3d(s, iso, 36, 150, arm=((46, 162, 14), (58, 152, 46), (78, 138, 34), (85, 131, 10)))

    # labels on two detections: one above its box, one to the right of its box
    ax, ay = iso.p(110, 61, 24)
    label(s, ax - 44, ay - 16, "broiler 0.97")
    bx_, by_ = iso.p(221, 101, 24)
    label(s, bx_ + 6, by_ + 4, "broiler 0.94")

    drone3d(s, iso, DX, DY, DZ)


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

    scene(s, 470, 16, 410, 290)

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
