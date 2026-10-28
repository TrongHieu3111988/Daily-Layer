"""Batch 2 recipes, chosen from market research (Oct 2026):
gridfinity starter (traffic), flat Christmas ornaments (seasonal), flexi koi (print-in-place), AirTag collar holder (pets)."""
import numpy as np
from forge import *

# ---------- 2D helpers (xy), extruded in z ----------
def cap2(p, a, b, r):
    pa = p[..., :2] - np.asarray(a, float); ba = np.asarray(b, float) - np.asarray(a, float)
    h = np.clip((pa @ ba) / (ba @ ba), 0, 1)
    return np.linalg.norm(pa - h[..., None] * ba, axis=-1) - r

def circ2(p, c, r): return np.linalg.norm(p[..., :2] - np.asarray(c, float), axis=-1) - r

def rrect2(p, c, half, r):
    q = np.abs(p[..., :2] - np.asarray(c, float)) - (np.asarray(half, float) - r)
    return np.linalg.norm(np.maximum(q, 0), axis=-1) + np.minimum(q.max(-1), 0) - r

def rot2(p, ang):
    c, s = np.cos(ang), np.sin(ang)
    x, y = p[..., 0], p[..., 1]
    return np.stack([c * x + s * y, -s * x + c * y, p[..., 2]], -1)

def star2(p, R, ri, n=5, rot=np.pi / 2):
    """Polygonal star as intersection-free polygon distance (sign via winding)."""
    ang = rot + np.arange(2 * n) * np.pi / n
    rad = np.where(np.arange(2 * n) % 2 == 0, R, ri)
    pts = np.stack([rad * np.cos(ang), rad * np.sin(ang)], 1)
    return poly2(p, pts)

def poly2(p, pts):
    x, y = p[..., 0], p[..., 1]
    d = np.full(x.shape, np.inf); inside = np.zeros(x.shape, bool)
    n = len(pts)
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        e = b - a; w = np.stack([x - a[0], y - a[1]], -1)
        h = np.clip((w @ e) / (e @ e), 0, 1)
        d = np.minimum(d, np.linalg.norm(w - h[..., None] * e, axis=-1))
        cond = ((a[1] <= y) & (b[1] > y)) | ((b[1] <= y) & (a[1] > y))
        xint = a[0] + (y - a[1]) * (b[0] - a[0]) / np.where(b[1] - a[1] == 0, 1e-9, b[1] - a[1])
        inside ^= cond & (x < xint)
    return np.where(inside, -d, d)

def ell2(p, c, a, b, ang=0.0):
    q = rot2(p - np.array([c[0], c[1], 0.0]), ang)
    k = np.hypot(q[..., 0] / a, q[..., 1] / b)
    return (k - 1.0) * min(a, b)

def extrude(d2, p, z0, z1):
    return np.maximum(d2, np.maximum(z0 - p[..., 2], p[..., 2] - z1))

# ---------- Gridfinity-compatible starter set ----------
def _gf_base_inset(z):
    return np.where(z < 0.8, 2.95 - z, np.where(z < 2.6, 2.15, np.where(z < 4.75, 2.15 - (z - 2.6), 0.0)))

def gf_bin(p, nx, ny, units, ox=0.0, oy=0.0):
    z = p[..., 2]
    W, D = 42 * nx - 0.5, 42 * ny - 0.5
    H = 7 * units
    body = extrude(rrect2(p, (ox, oy), (W / 2, D / 2), 3.75), p, 4.75, H)
    feet = []
    for i in range(nx):
        for j in range(ny):
            cx = ox - 21 * (nx - 1) + 42 * i; cy = oy - 21 * (ny - 1) + 42 * j
            ins = _gf_base_inset(np.clip(z, 0, 4.75))
            half = 20.75 - ins
            r = np.maximum(3.75 - ins, 0.8)
            q = np.abs(p[..., :2] - np.array([cx, cy])) - (half - r)[..., None]
            d2 = np.linalg.norm(np.maximum(q, 0), axis=-1) + np.minimum(q.max(-1), 0) - r
            feet.append(extrude(d2, p, 0, 4.76))
    shell = union(body, *feet)
    cav = extrude(rrect2(p, (ox, oy), (W / 2 - 1.2, D / 2 - 1.2), 2.55), p, 7.0, H + 1)
    return diff(shell, cav)

def gf_baseplate(p, nx, ny, ox=0.0, oy=0.0, T=4.65):
    plate = extrude(rrect2(p, (ox, oy), (21 * nx, 21 * ny), 4.0), p, 0, T)
    d = T - p[..., 2]
    ins = np.where(d < 2.15, d, np.where(d < 3.95, 2.15, 2.15 + (d - 3.95)))
    pockets = []
    for i in range(nx):
        for j in range(ny):
            cx = ox - 21 * (nx - 1) + 42 * i; cy = oy - 21 * (ny - 1) + 42 * j
            half = 21 - ins; r = np.maximum(4.0 - ins, 0.8)
            q = np.abs(p[..., :2] - np.array([cx, cy])) - (half - r)[..., None]
            d2 = np.linalg.norm(np.maximum(q, 0), axis=-1) + np.minimum(q.max(-1), 0) - r
            pockets.append(extrude(d2, p, -1, T + 1))
    return diff(plate, *pockets)

def gridfinity_starter(step=0.42):
    parts = []
    v, f = mesh(lambda p: gf_baseplate(p, 3, 3), (-63, -63, 0), (63, 63, 4.65), step)
    parts.append(("baseplate_3x3", v, f, "#3A4750"))
    for name, nx, ny, u, ox, oy, col in [("bin_1x1", 1, 1, 3, -42, 42, "#F2B705"), ("bin_2x1", 2, 1, 3, 21, 42, "#0E7C6B"),
                                         ("bin_1x2", 1, 2, 3, -42, -21, "#E07A5F"), ("bin_2x2", 2, 2, 3, 21, -21, "#E9E4D8")]:
        hw, hd = 21 * nx, 21 * ny
        v, f = mesh(lambda p: gf_bin(p, nx, ny, u, ox, oy), (ox - hw, oy - hd, 0), (ox + hw, oy + hd, 7 * u), step)
        v = v.copy(); v[:, 2] += 4.65 + 0.35 - 4.75 + 0.0  # seat the bins in the plate for the preview
        parts.append((name, v, f, col))
    # print layout: everything flat on the bed, spread out
    pp = [(n, drop_to_bed(v), f, c) for n, v, f, c in parts]
    pp[0] = (pp[0][0], pp[0][1], pp[0][2], pp[0][3])
    offs = {"baseplate_3x3": (0, 0), "bin_1x1": (-42 - 90, 0), "bin_2x1": (150, 0), "bin_1x2": (-42 - 150, 0), "bin_2x2": (150, -90)}
    lay = []
    for n, v, f, c in pp:
        v = v.copy(); ctr = (v.max(0) + v.min(0)) / 2; v[:, 0] -= ctr[0]; v[:, 1] -= ctr[1]
        v[:, 0] += offs[n][0]; v[:, 1] += offs[n][1]; lay.append((n, v, f, c))
    return dict(parts=parts, print_parts=lay, meta=dict(view=(32, -50), line="functional",
                print_hint="Gridfinity-compatible (42 mm grid, 7 mm units), lite profile without stacking lip. 0.2 mm layer, 2 walls, no supports. Baseplate is open-bottom to save filament."))

# ---------- Flat Christmas ornaments ----------
T_ORN = 3.0
def _hanger(p, top_y):
    ring = np.maximum(circ2(p, (0, top_y + 3.2), 4.2), -circ2(p, (0, top_y + 3.2), 2.2))
    return ring

def orn_snowflake(p):
    R = 34; d = circ2(p, (0, 0), 7.5)
    for k in range(6):
        q = rot2(p, np.pi / 2 + k * np.pi / 3)
        d = np.minimum(d, cap2(q, (0, 0), (R, 0), 1.9))
        for t, L, w in ((0.42, 0.26, 1.6), (0.7, 0.17, 1.4)):
            for s in (1, -1):
                a = np.array([t * R, 0.0]); b = a + L * R * np.array([np.cos(s * np.pi / 4), np.sin(s * np.pi / 4)])
                d = np.minimum(d, cap2(q, a, b, w))
        d = np.minimum(d, circ2(q, (R, 0), 2.6))
    d = np.maximum(d, -star2(p, 4.2, 1.9, 6, np.pi / 2))
    return extrude(np.minimum(d, _hanger(p, R + 1.5)), p, 0, T_ORN)

def orn_star(p):
    outer = star2(p, 40, 17, 5)
    inner = star2(p, 31, 12.5, 5)
    rings = np.maximum(outer, -inner)
    core = np.maximum(star2(p, 19, 8, 5), -circ2(p, (0, 0), 3.2))
    d = np.minimum(rings, core)
    for k in range(5):
        q = rot2(p, np.pi / 2 + k * 2 * np.pi / 5)
        d = np.minimum(d, cap2(q, (17, 0), (31, 0), 1.4))
    return extrude(np.minimum(d, _hanger(p, 40.0 - 1.0)), p, 0, T_ORN)

def orn_tree(p):
    tiers = [((0, 38), (-17, 18), (17, 18)), ((0, 26), (-24, 2), (24, 2)), ((0, 12), (-31, -16), (31, -16))]
    d = np.inf
    for a, b, c in tiers:
        d = np.minimum(d, poly2(p, np.array([a, b, c], float)) - 1.0)
    d = np.minimum(d, rrect2(p, (0, -21), (5, 6), 1.2))
    holes = [circ2(p, c, r) for c, r in (((0, 28), 2.6), ((-8, 12), 2.4), ((9, 6), 2.4), ((-14, -6), 2.6), ((2, -4), 2.2), ((16, -10), 2.4), ((-4, -12), 2.0))]
    d = np.maximum(d, -np.minimum.reduce(holes))
    d = np.minimum(d, np.maximum(star2(p - np.array([0, 40.5, 0]), 6.5, 2.8, 5), -1e9))
    return extrude(np.minimum(d, _hanger(p, 45.5)), p, 0, T_ORN)

def orn_bauble(p):
    R = 32
    disc = circ2(p, (0, 0), R)
    lattice = np.inf
    for k in range(12):
        q = rot2(p, k * np.pi / 6)
        lattice = np.minimum(lattice, np.abs(circ2(q, (R * 0.55, 0), R * 0.55)) - 1.1)
    rim = np.abs(disc + 1.6) - 1.6
    d = np.minimum(np.maximum(lattice, disc), rim)
    d = np.minimum(d, circ2(p, (0, 0), 4.5))
    cap = rrect2(p, (0, R + 2.5), (6, 3.5), 1.0)
    d = np.minimum(d, cap)
    return extrude(np.minimum(d, _hanger(p, R + 6.0 - 1.0)), p, 0, T_ORN)

def xmas_ornaments(step=0.22):
    designs = [("snowflake", orn_snowflake, (-38, -38), (38, 42), "#E8EEF2"), ("star", orn_star, (-41, -36), (41, 49), "#E9B949"),
               ("tree", orn_tree, (-34, -29), (34, 53), "#2F7D4F"), ("bauble", orn_bauble, (-34, -34), (34, 45), "#C8443A")]
    parts, lay = [], []
    for i, (n, fn, lo, hi, col) in enumerate(designs):
        v, f = mesh(fn, (lo[0], lo[1], 0), (hi[0], hi[1], T_ORN), step)
        ox, oy = (i % 2) * 92 - 46, (i // 2) * -100 + 50
        v = v.copy(); v[:, 0] += ox; v[:, 1] += oy
        parts.append((n, v, f, col)); lay.append((n, v, f, col))
    return dict(parts=parts, print_parts=lay, meta=dict(view=(80, 0), line="decor",
                print_hint="Flat, no supports, 3 mm thick. Swap filament at 2.4 mm for a two-tone face. PLA or silk PLA; hang with ribbon."))

# ---------- Flexi koi (print-in-place) ----------
KOI_H = 8.0
def koi_width(x):
    # half-width of the fish outline along x (head at x=0, tail toward +x)
    t = np.clip(x / 96.0, 0, 1)
    return 3.5 + 10.5 * np.sin(np.pi * np.clip(0.08 + 0.95 * t, 0, 1)) ** 0.8 * (1 - 0.55 * t)

def flexi_koi(step=0.22, clr=0.5):
    joints = [16.0, 28.0, 39.5, 50.5, 61.0, 71.5, 82.0]       # pin centres along x
    seg_edges = [-2.0] + joints + [102.0]
    zm0, zm1 = 2.6, KOI_H - 2.6                                  # boss band
    rb = 2.7                                                     # boss radius
    def body_slab(p, x0, x1):
        x, y, z = p[..., 0], p[..., 1], p[..., 2]
        w = koi_width(x)
        ny = np.abs(y) / np.maximum(w, 1e-3); nz = np.abs(z - KOI_H / 2) / (KOI_H / 2)
        sup = (ny ** 3 + nz ** 3) ** (1 / 3) - 1.0
        return np.maximum(sup * np.minimum(w, KOI_H / 2), np.maximum(x0 - x, x - x1))
    def seg(p, i):
        x = p[..., 0]
        x0 = seg_edges[i]; x1 = seg_edges[i + 1]
        # owns the joint at its rear (x1): wraps around the pin; front joint (x0) is a boss on a neck
        rear_r = rb + clr + 1.4
        lo = x0 + (rear_r + clr) if i > 0 else x0
        s = body_slab(p, lo, x1)
        if i < len(joints):
            jx = x1
            wrap = np.maximum(body_slab(p, x1 - 1, x1 + rear_r), circ2(p, (jx, 0), rear_r))
            s = np.minimum(s, wrap)
            cav = np.maximum(circ2(p, (jx, 0), rb + clr), np.maximum(zm0 - clr - p[..., 2], p[..., 2] - (zm1 + clr)))
            ang = np.arctan2(p[..., 1], p[..., 0] - jx)
            wedge = np.maximum(np.abs(ang) - np.radians(38), 1.0 - np.hypot(p[..., 0] - jx, p[..., 1]))
            slot = np.maximum(wedge, np.maximum(zm0 - clr - p[..., 2], p[..., 2] - (zm1 + clr)))
            s = diff(s, cav, slot)
        if i > 0:
            jx = x0
            # clear the previous segment's rounded rear
            s = diff(s, extrude(circ2(p, (jx, 0), rear_r + clr), p, -1, KOI_H + 1))
            boss = extrude(circ2(p, (jx, 0), rb), p, zm0, zm1)
            neck = extrude(rrect2(p, ((jx + lo) / 2 + 0.3, 0), ((lo - jx) / 2 + 0.3, 1.5), 0.4), p, zm0, zm1)
            s = union(s, boss, neck)
        if i == 0:   # head: rounded snout, eyes, fins
            s = np.maximum(s, ell2(p, (15.5, 0), 17.5, 14.0))
            for side in (1, -1):
                s = diff(s, sphere(p, np.array([6.0, side * 6.4, KOI_H - 0.9]), 1.9))
            fins = union(*[extrude(ell2(p, (12.5, side * 12.0), 7.0, 3.2, side * np.radians(-35)), p, 0.0, 2.2) for side in (1, -1)])
            s = union(s, fins)
        if i == len(joints):   # tail fan
            fan = extrude(np.maximum(np.maximum(circ2(p, (90, 0), 20), -circ2(p, (114, 0), 12.5)), 90 - p[..., 0]), p, 0, 2.4)
            s = union(s, fan)
        return s
    def koi(p):
        return np.minimum.reduce([seg(p, i) for i in range(len(joints) + 1)])
    v, f = mesh(koi, (-3, -22, 0), (111, 22, KOI_H), step)
    return dict(parts=[("fishbone", v, f, "#E6DFCC")], expect_shells=len(joints) + 1,
                meta=dict(view=(72, 15), line="print-in-place",
                          print_hint="Print-in-place, no supports, no assembly. 0.2 mm layer, 0.5 mm joint clearance; flex gently after printing. Looks great in silk orange/white or multi-colour layer swaps."))

# ---------- AirTag collar holder ----------
def airtag_holder(step=0.25, strap=25.5):
    def f(p):
        z = p[..., 2]
        puck = extrude(circ2(p, (0, 0), 19.2), p, 4.2, 15.0)
        chamfer = np.hypot(p[..., 0], p[..., 1]) - (19.2 - np.maximum(0, z - 12.0))
        puck = np.maximum(puck, chamfer)
        pocket = extrude(circ2(p, (0, 0), 16.15), p, 5.8, 14.0)
        window = extrude(circ2(p, (0, 0), 13.2), p, 13.0, 20)
        loops = []
        for y in (-11.0, 11.0):
            band = extrude(rrect2(p, (0, y), (strap / 2 + 3.0, 5.0), 2.0), p, 0, 4.6)
            loops.append(band)
        base = union(puck, *loops, extrude(circ2(p, (0, 0), 17.5), p, 0, 4.6))
        tunnel = extrude(rrect2(p, (0, 0), (strap / 2, 30), 0.8), p, 1.2, 4.0)
        return diff(base, pocket, window, tunnel)
    v, fc = mesh(f, (-20, -20, 0), (20, 20, 15.5), step)
    return dict(parts=[("holder", v, fc, "#D9534F")],
                meta=dict(view=(30, -35), line="functional",
                          print_hint="Print in TPU 95A so the AirTag snaps in through the front window. Fits collars up to 25 mm wide. 0.2 mm layer, 3 walls, no supports."))

CATALOG2 = {
    "gridfinity-starter-3x3": (gridfinity_starter, dict(title="Gridfinity Starter Set 3×3", price=0.0,
        blurb="Open-bottom 3×3 baseplate plus four bins (1×1, 2×1, 1×2, 2×2). Drops into any Gridfinity drawer system.",
        tags=["gridfinity", "organizer", "storage"])),
    "xmas-flat-ornaments-4": (xmas_ornaments, dict(title="Nordic Flat Ornaments (set of 4)", price=2.99,
        blurb="Snowflake, star, tree and lattice bauble. Flat prints with built-in hangers, ready for two-tone layer swaps.",
        tags=["christmas", "ornament", "holiday", "gift"])),
    "flexi-fishbone": (flexi_koi, dict(title="Flexi Fishbone", price=1.99,
        blurb="Eight-segment fish skeleton that prints in one piece and wiggles straight off the bed. No supports, no assembly. Great for Halloween.",
        tags=["flexi", "print-in-place", "fidget", "halloween"])),
    "airtag-collar-holder": (airtag_holder, dict(title="AirTag Collar Holder", price=1.49,
        blurb="Snap-in AirTag case that slides onto pet collars up to 25 mm wide. Print in TPU for a secure, soft fit.",
        tags=["pet", "airtag", "dog", "cat"])),
}
