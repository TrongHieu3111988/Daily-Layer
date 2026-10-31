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

# ---------- Rainbow Wiggle Snake (print-in-place, 2026-10-30) ----------
# 13 segments joined by 12 captured bicone pins: every overhang is 45 degrees, nothing bridges, 0.55 mm clearance all round.
SNK_J = [24.0 + 14.0 * k for k in range(12)]           # joint centres along x (head at x ~ 0, tail toward +x)
SNK_TIP = SNK_J[-1] + 28.0
SNK_H, SNK_ZC, SNK_W = 10.0, 4.5, 6.0                  # height, top of the straight walls, body half-width
SNK_CLR, SNK_WRAP = 0.55, 6.0
SNK_PIN = np.array([(0, 0), (2.0, 0), (3.8, 1.8), (3.8, 7.2), (2.0, 9.0), (0, 9.0)], float)
SNK_RAINBOW = ["#E8453C", "#F28C28", "#F6C833", "#4CB963", "#3B8FD9", "#8C5BD6"]

def _snk_w(x):
    head = 9.6 * np.sqrt(np.clip(1 - ((x - 9.0) / 12.5) ** 2, 0, 1))
    tail = np.where(x > SNK_J[-1] + 7.0, SNK_W - (SNK_W - 1.4) * np.clip((x - SNK_J[-1] - 7.0) / (SNK_TIP - SNK_J[-1] - 7.0), 0, 1) ** 1.3, SNK_W)
    body = np.where(x > 13.0, tail, 0.0)
    return np.maximum(head, body)

def _snk_h(x):
    t = np.clip((x - SNK_J[-1] - 7.0) / (SNK_TIP - SNK_J[-1] - 7.0), 0, 1)
    return SNK_H - 5.0 * t ** 1.5 + 1.0 * np.exp(-((x - 9.0) / 7.0) ** 2)   # a little taller head, low pointed tail

def _snk_body(p, x0, x1):
    x, y, z = p[..., 0], p[..., 1], p[..., 2]
    w = np.maximum(_snk_w(x), 1e-3); h = _snk_h(x); zc = np.minimum(SNK_ZC, h * 0.45)
    side = np.abs(y) - w
    k = np.hypot(y / w, np.maximum(z - zc, 0) / np.maximum(h - zc, 1e-3))
    dome = (k - 1.0) * np.minimum(w, h - zc)
    d = np.where(z > zc, dome, side)
    return np.maximum(np.maximum(d, -z), np.maximum(x0 - x, x - x1))

def _snk_rz(p, jx):
    r = np.hypot(p[..., 0] - jx, p[..., 1])
    return np.stack([r, p[..., 2], np.zeros_like(r)], -1)

def _snk_pin(p, jx): return poly2(_snk_rz(p, jx), SNK_PIN)

def _snk_seg(p, i):
    n = len(SNK_J)
    x0 = SNK_J[i - 1] if i > 0 else -4.0
    x1 = SNK_J[i] if i < n else SNK_TIP + 1.0
    s = _snk_body(p, x0, min(x1, SNK_TIP + 1.0))
    if i < n:                                            # rear: a disc that wraps the next segment's pin
        jx = x1
        wrap = np.maximum(_snk_body(p, jx - SNK_WRAP, jx + SNK_WRAP), circ2(p, (jx, 0), SNK_WRAP))
        s = np.minimum(s, wrap)
        cav = np.minimum(_snk_pin(p, jx) - SNK_CLR, circ2(p, (jx, 0), 2.0 + SNK_CLR))  # open top and bottom over the pin
        ang = np.arctan2(p[..., 1], p[..., 0] - jx)
        slot = np.abs(ang) - np.radians(50)
        s = diff(s, cav, slot)
    if i > 0:                                            # front: concave face, pin and neck
        jx = x0
        s = diff(s, circ2(p, (jx, 0), SNK_WRAP + SNK_CLR))
        pin = np.maximum(_snk_pin(p, jx), _snk_body(p, jx - 5, jx + 5))
        neck = np.maximum(extrude(rrect2(p, (jx + 3.8, 0), (3.8, 1.6), 0.5), p, 2.4, 6.6), _snk_body(p, jx, jx + 9))
        s = union(s, pin, neck)
    if i == 0:                                           # face: round eyes with pupils, two nostrils
        for sd in (1, -1):
            ey = sd * 4.9; zt = float(_snk_top(7.0, 4.9))
            s = union(s, sphere(p, np.array([7.0, ey, zt - 1.0]), 3.0))
            s = diff(s, sphere(p, np.array([5.6, sd * 5.3, zt + 2.0]), 1.35))
            s = diff(s, sphere(p, np.array([0.6, sd * 2.3, float(_snk_top(0.6, 2.3)) + 0.35]), 0.85))
    return s

def _snk_top(x, y):
    w = float(_snk_w(np.array(x))); h = float(_snk_h(np.array(x))); zc = min(SNK_ZC, h * 0.45)
    return zc + (h - zc) * np.sqrt(max(0.0, 1 - (y / w) ** 2))

def _snk_range(i):
    n = len(SNK_J)
    a = (SNK_J[i - 1] - 7.0) if i > 0 else -6.0
    b = (SNK_J[i] + 7.5) if i < n else SNK_TIP + 2.0
    return a, b

def _snk_sdf(segs):
    def f(P):
        sh = P.shape[:-1]; Q = P.reshape(-1, 3); out = np.full(len(Q), 50.0)
        for i in segs:
            a, b = _snk_range(i); m = (Q[:, 0] > a - 0.5) & (Q[:, 0] < b + 0.5)
            out[m] = np.minimum(out[m], _snk_seg(Q[m], i))
        return out.reshape(sh)
    return f

def rainbow_snake(step=0.28):
    n = len(SNK_J) + 1
    lo, hi = (-5.0, -11.0, 0.0), (SNK_TIP + 1.0, 11.0, SNK_H + 2.5)
    v, f = mesh(_snk_sdf(range(n)), lo, hi, step)
    groups = {}
    for i in range(n): groups.setdefault(min(5, i * 6 // n), []).append(i)
    names = ["red", "orange", "yellow", "green", "blue", "purple"]
    colour_parts = []
    for g, segs in groups.items():
        a, b = _snk_range(segs[0])[0], _snk_range(segs[-1])[1]
        gv, gf = mesh(_snk_sdf(segs), (max(lo[0], a - 1), lo[1], lo[2]), (min(hi[0], b + 1), hi[1], hi[2]), step)
        colour_parts.append((names[g], gv, gf, SNK_RAINBOW[g]))
    # shop preview: the same segments posed in a gentle S, the way it sits after a wiggle (the print file stays straight)
    ang = [0.0] + [np.radians(19) * np.sin(0.9 * k + 0.6) for k in range(1, n)]
    T = [np.eye(3)]
    posed = {}
    for i in range(n):
        if i > 0:
            jx = SNK_J[i - 1]; c, s_ = np.cos(ang[i]), np.sin(ang[i])
            R = np.array([[c, -s_, jx - c * jx], [s_, c, -s_ * jx], [0, 0, 1]])
            T.append(T[-1] @ R)
        a, b = _snk_range(i)
        sv, sf = mesh(_snk_sdf([i]), (a - 1, lo[1], lo[2]), (b + 1, hi[1], hi[2]), step)
        xy = np.c_[sv[:, :2], np.ones(len(sv))] @ T[i].T
        sv = np.c_[xy[:, :2], sv[:, 2]].astype(np.float32)
        g = min(5, i * 6 // n); pv, pf = posed.get(g, (np.zeros((0, 3), np.float32), np.zeros((0, 3), np.int64)))
        posed[g] = (np.concatenate([pv, sv]), np.concatenate([pf, sf + len(pv)]))
    allv = np.concatenate([pv for pv, _ in posed.values()]); ctr = (allv.max(0) + allv.min(0)) / 2
    preview = [(names[g], posed[g][0] - np.array([ctr[0], ctr[1], 0], np.float32), posed[g][1], SNK_RAINBOW[g]) for g in sorted(posed)]
    return dict(parts=preview, print_parts=[("snake", v, f, "#E8453C")], expect_shells=n, colour_3mf=colour_parts,
                meta=dict(view=(62, -75), line="print-in-place",
                          print_hint="Prints straight; the photos show it after a wiggle. Print-in-place, no supports, no assembly: 13 segments on 12 captured pins, 45-degree overhangs only, 0.55 mm clearance. 0.2 mm layers, 2 walls, PLA. One colour, a rainbow/silk-rainbow filament, or the included 3MF with each segment group pre-split for 6 AMS colours. Flex each joint gently after printing. Contains small parts: not for children under 3."))

CATALOG2["rainbow-wiggle-snake"] = (rainbow_snake, dict(title="Rainbow Wiggle Snake", title_vi="Rắn Cầu Vồng Uốn Éo", price=1.99,
    blurb="A 21 cm articulated snake that prints in one piece and slithers straight off the bed. 13 rainbow segments on captured pins, no supports, no assembly.",
    tags=["flexi", "print-in-place", "fidget", "snake", "rainbow", "stocking-stuffer"]))

# ---------- Wiggle Friends Christmas set (print-in-place, 2026-10-31) ----------
# Four 10 cm wiggle friends (reindeer, snowman, penguin, gingerbread) on the same captured bicone pins as the
# Rainbow Wiggle Snake (45-degree overhangs, 0.55 mm clearance). Each prints in one piece; a stocking-stuffer set.
WF_J = [22.0 + 14.0 * k for k in range(5)]           # joints along x; head at x ~ 0..20, tail toward +x
WF_TIP = WF_J[-1] + 19.0
WF_H, WF_ZC, WF_W, WF_RH, WF_HX = 10.0, 4.5, 6.0, 9.5, 9.0
WF_FRIENDS = [   # name, body colour, accent colours
    ("reindeer", "#A0683E", {"nose": "#D9443F", "antler": "#5A3A24"}),
    ("snowman", "#F4F4EF", {"carrot": "#F28C28", "coal": "#2B2E3A", "scarf": "#2F8A57"}),
    ("penguin", "#2E3140", {"face": "#F4F4EF", "beak": "#F2A93B"}),
    ("gingerbread", "#C27C43", {"icing": "#F7F4EC", "gumdrop": "#D9443F"}),
]
WF_Y = [-51.0, -17.0, 17.0, 51.0]

def _wf_w(x):
    head = WF_RH * np.sqrt(np.clip(1 - ((x - WF_HX) / WF_RH) ** 2, 0, 1))
    t = np.clip((x - WF_J[-1] - 6.0) / (WF_TIP - WF_J[-1] - 6.0), 0, 1)
    tail = np.where(x > WF_J[-1] + 6.0, WF_W - (WF_W - 2.2) * t ** 1.2, WF_W)
    return np.maximum(head, np.where(x > 13.0, tail, 0.0))

def _wf_h(x):
    t = np.clip((x - WF_J[-1] - 6.0) / (WF_TIP - WF_J[-1] - 6.0), 0, 1)
    return WF_H - 3.5 * t ** 1.5 + 2.0 * np.exp(-((x - WF_HX) / 7.0) ** 2)

def _wf_body(p, x0, x1):
    x, y, z = p[..., 0], p[..., 1], p[..., 2]
    w = np.maximum(_wf_w(x), 1e-3); h = _wf_h(x); zc = np.minimum(WF_ZC, h * 0.45)
    k = np.hypot(y / w, np.maximum(z - zc, 0) / np.maximum(h - zc, 1e-3))
    d = np.where(z > zc, (k - 1.0) * np.minimum(w, h - zc), np.abs(y) - w)
    return np.maximum(np.maximum(d, -z), np.maximum(x0 - x, x - x1))

def _wf_top(x, y):
    w = float(_wf_w(np.array(x))); h = float(_wf_h(np.array(x))); zc = min(WF_ZC, h * 0.45)
    return zc + (h - zc) * np.sqrt(max(0.0, 1 - (y / w) ** 2))

def _wf_pin(p, jx): return poly2(_snk_rz(p, jx), SNK_PIN)

def _wf_dot(p, x, y, r):     # a bump sitting on the body top (buttons, gumdrops); its lower half is buried
    return sphere(p, np.array([x, y, _wf_top(x, y) - 0.6 * r]), r)

def _wf_flat(d2, p, z1):     # flat feature on the bed: rounded top edge, no overhang
    return np.maximum(d2, np.maximum(-p[..., 2], p[..., 2] - z1))

def _wf_features(p, kind, i):
    """(extra solids to add, accent solids by colour) for segment i of a friend."""
    add, acc = [], {}
    def put(name, s): acc[name] = s if name not in acc else np.minimum(acc[name], s)
    if i == 0:
        if kind == "reindeer":
            for sd in (1, -1):
                ant = np.minimum.reduce([cap2(p, (11.0, sd * 7.0), (14.0, sd * 18.0), 1.7), cap2(p, (12.6, sd * 12.5), (5.5, sd * 15.5), 1.5),
                                         cap2(p, (13.7, sd * 16.5), (8.5, sd * 20.0), 1.4)])
                a = _wf_flat(ant, p, 3.4); add.append(a); put("antler", a)
            nose = np.minimum(cyl_z(p, np.array([-0.6, 0, 0]), 3.4, 0, 4.8), sphere(p, np.array([-0.6, 0, 4.8]), 3.4))
            add.append(nose); put("nose", np.minimum(nose, sphere(p, np.array([-0.6, 0, 4.8]), 3.6)))
        elif kind == "snowman":
            car = _wf_flat(poly2(p, np.array([(1.0, 3.0), (-10.0, 0.6), (-10.0, -0.6), (1.0, -3.0)])), p, 4.2)
            car = np.maximum(car, p[..., 2] - (4.4 - 0.35 * np.abs(p[..., 1]) - 0.05 * np.maximum(-p[..., 0], 0)))
            add.append(car); put("carrot", np.maximum(car, p[..., 0] + 0.4))
            for sd in (1, -1):    # coal smile under the carrot
                for k, (sx, sy) in enumerate([(3.4, 4.6), (2.1, 3.0), (1.6, 1.2)]):
                    put("coal", sphere(p, np.array([sx + 0.9, sd * sy, float(_wf_top(sx + 0.9, sy)) - 0.2]), 0.85))
        elif kind == "penguin":
            beak = _wf_flat(poly2(p, np.array([(1.5, 3.2), (-5.5, 0.0), (1.5, -3.2)])), p, 4.6)
            add.append(beak); put("beak", np.maximum(beak, p[..., 0] + 0.2))
            put("face", np.maximum(ell2(p, (4.6, 0.0), 5.4, 8.2), 5.5 - p[..., 2]))
        elif kind == "gingerbread":
            r = np.hypot(p[..., 0] - WF_HX, p[..., 1])
            band = np.maximum(np.abs(r - 7.4) - 0.75, 5.0 - p[..., 2])
            wave = np.abs(r - (7.4 + 0.6 * np.sin(8 * np.arctan2(p[..., 1], p[..., 0] - WF_HX)))) - 0.7
            put("icing", np.maximum(np.maximum(wave, 5.5 - p[..., 2]), p[..., 0] - 13.5))
    if i == 1:
        if kind == "penguin":
            for sd in (1, -1):
                fl = _wf_flat(poly2(p, np.array([(WF_J[0] + 7.0, sd * 5.0), (WF_J[0] + 12.0, sd * 5.0), (WF_J[0] + 12.5, sd * 11.0), (WF_J[0] + 9.0, sd * 10.0)])), p, 3.0)
                add.append(fl)
        if kind == "gingerbread":
            for sd in (1, -1):
                arm = _wf_flat(cap2(p, (WF_J[0] + 9.5, sd * 4.5), (WF_J[0] + 9.0, sd * 10.5), 2.2), p, 4.0)
                add.append(arm); put("icing", np.maximum(_wf_flat(np.abs(cap2(p, (WF_J[0] + 9.5, sd * 4.5), (WF_J[0] + 9.0, sd * 10.5), 2.2) + 0.0) - 0.5, p, 4.2), np.abs(p[..., 1]) - 8.6 * 1.0 + 0 * p[..., 0]))
        if kind == "snowman":   # knitted scarf band just behind the head
            jx = WF_J[0] + 4.6
            band = np.maximum(np.maximum(np.abs(p[..., 0] - jx) - 1.6, _wf_body(p, jx - 3, jx + 3) - 0.9), -p[..., 2])
            add.append(band); put("scarf", band)
    if 1 <= i <= 3:
        mx = (WF_J[i - 1] + WF_J[i]) / 2 + 2.5
        if kind == "snowman": d = _wf_dot(p, mx, 0.0, 1.6); add.append(d); put("coal", d)
        if kind == "gingerbread": d = _wf_dot(p, mx, 0.0, 1.9); add.append(d); put("gumdrop", d)
    return add, acc

def _wf_seg(p, kind, i):
    n = len(WF_J)
    x0 = WF_J[i - 1] if i > 0 else -4.0
    x1 = WF_J[i] if i < n else WF_TIP + 1.0
    s = _wf_body(p, x0, min(x1, WF_TIP + 1.0))
    add, _ = _wf_features(p, kind, i)
    if add: s = np.minimum(s, np.minimum.reduce(add))
    if i < n:
        jx = x1
        wrap = np.maximum(_wf_body(p, jx - SNK_WRAP, jx + SNK_WRAP), circ2(p, (jx, 0), SNK_WRAP))
        s = np.minimum(s, wrap)
        cav = np.minimum(_wf_pin(p, jx) - SNK_CLR, circ2(p, (jx, 0), 2.0 + SNK_CLR))
        slot = np.abs(np.arctan2(p[..., 1], p[..., 0] - jx)) - np.radians(50)
        s = diff(s, cav, slot)
    if i > 0:
        jx = x0
        s = diff(s, circ2(p, (jx, 0), SNK_WRAP + SNK_CLR))
        pin = np.maximum(_wf_pin(p, jx), _wf_body(p, jx - 5, jx + 5))
        neck = np.maximum(extrude(rrect2(p, (jx + 3.8, 0), (3.8, 1.6), 0.5), p, 2.4, 6.6), _wf_body(p, jx, jx + 9))
        s = union(s, pin, neck)
    if i == 0:   # eyes: raised domes with a pupil dimple, like the snake
        for sd in (1, -1):
            ex, ey = 8.2, sd * 4.2; zt = float(_wf_top(ex, abs(ey)))
            s = union(s, sphere(p, np.array([ex, ey, zt - 1.2]), 2.7))
            s = diff(s, sphere(p, np.array([ex - 1.1, sd * 4.5, zt + 1.9]), 1.25))
    return s

def _wf_range(i):
    n = len(WF_J)
    a = (WF_J[i - 1] - 7.0) if i > 0 else -12.0
    b = (WF_J[i] + 7.5) if i < n else WF_TIP + 2.0
    return a, b

def _wf_sdf(kind, segs, accent=None):
    def f(P):
        sh = P.shape[:-1]; Q = P.reshape(-1, 3); out = np.full(len(Q), 50.0)
        for i in segs:
            a, b = _wf_range(i); m = (Q[:, 0] > a - 0.5) & (Q[:, 0] < b + 0.5)
            if not m.any(): continue
            s = _wf_seg(Q[m], kind, i)
            if accent is not None:   # the accent colour region of this segment: inside the part and inside the accent solid
                _, acc = _wf_features(Q[m], kind, i)
                s = np.maximum(s, acc[accent]) if accent in acc else np.full(len(s), 50.0)
            out[m] = np.minimum(out[m], s)
        return out.reshape(sh)
    return f

def _wf_minus(kind, segs, accents):
    base = _wf_sdf(kind, segs)
    accs = [_wf_sdf(kind, segs, a) for a in accents]
    return lambda P: diff(base(P), *[a(P) for a in accs]) if accs else base(P)

def wiggle_friends(step=0.3):
    n = len(WF_J) + 1
    lo, hi = (-12.5, -22.0, 0.0), (WF_TIP + 1.0, 22.0, WF_H + 3.0)
    prints, colour_parts, preview = [], [], []
    def sh(v, y): v = v.copy(); v[:, 1] += y; return v
    for (kind, col, accs), y in zip(WF_FRIENDS, WF_Y):
        v, f = mesh(_wf_sdf(kind, range(n)), lo, hi, step)
        prints.append((kind, sh(v, y), f, col))
        names = list(accs)
        bv, bf = mesh(_wf_minus(kind, range(n), names), lo, hi, step)
        colour_parts.append((kind, sh(bv, y), bf, col)); preview.append((kind, sh(bv, y), bf, col))
        for a in names:
            av, af = mesh(_wf_sdf(kind, range(n), a), lo, hi, step)
            if len(af) == 0: continue
            colour_parts.append((f"{kind}_{a}", sh(av, y), af, accs[a])); preview.append((f"{kind}_{a}", sh(av, y), af, accs[a]))
    return dict(parts=preview, print_parts=prints, expect_shells=4 * n, colour_3mf=colour_parts, zip_3mf_only=True,
                meta=dict(view=(58, -62), line="print-in-place",
                          print_hint="Four 10 cm wiggle friends on one plate (or print one at a time). Print-in-place, no supports, no assembly: 6 segments each on 5 captured pins, 45-degree overhangs only, 0.55 mm clearance. 0.2 mm layers, 2 walls, PLA. One 3MF (opens in Bambu Studio, OrcaSlicer, PrusaSlicer and Cura) with the noses, antlers, beak, scarf and buttons pre-split for AMS colours; for a single-colour print, give every part the same filament. Flex each joint gently after printing. Contains small parts: not for children under 3."))

CATALOG2["wiggle-friends-xmas-4"] = (wiggle_friends, dict(title="Wiggle Friends Christmas Set (4 minis)", title_vi="Bộ 4 Bạn Uốn Éo Giáng Sinh", price=2.99,
    blurb="Four 10 cm articulated stocking stuffers that print in one piece each: a reindeer, a snowman, a penguin and a gingerbread friend. No supports, no assembly.",
    tags=["flexi", "print-in-place", "christmas", "stocking-stuffer", "reindeer", "snowman", "penguin", "gingerbread"]))
