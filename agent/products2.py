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

# ---------- Christmas cookie cutter set (functional, 2026-11-01) ----------
# Printed upside down: the 2 mm pusher flange lies on the bed, the wall rises 14 mm and thins to a cutting edge. No overhangs, no supports.
CC_H, CC_FL, CC_FW = 14.0, 2.0, 5.0

def _smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b * (1 - h) + a * h - k * h * (1 - h)

def cc_gingerbread(p):
    d = circ2(p, (0, 27), 10.5)
    d = _smin(d, ell2(p, (0, 7), 14, 17), 5)
    for s in (1, -1):
        d = _smin(d, cap2(p, (s * 9, 15), (s * 28, 24), 5.2), 4)
        d = _smin(d, cap2(p, (s * 8, -8), (s * 13, -30), 6.2), 4)
    return d

def cc_tree(p):
    tiers = [((0, 40), (-18, 14), (18, 14)), ((0, 26), (-27, -4), (27, -4)), ((0, 8), (-35, -26), (35, -26))]
    d = np.inf
    for a, b, c in tiers: d = np.minimum(d, poly2(p, np.array([a, b, c], float)) - 2.5)
    return np.minimum(d, rrect2(p, (0, -31), (6, 7), 1.5))

def cc_star(p):
    return star2(p, 43, 19, 5) - 3.0

def _cc_sdf(shape):
    def f(p):
        d = shape(p); z = p[..., 2]
        w = np.where(z < 11.0, 1.5, 1.5 - 0.7 * (z - 11.0) / 3.0)      # wall 1.5 mm, thinning to 0.8 mm at the cutting edge
        wall = np.maximum(d, -(d + w))
        flange = np.maximum(d - CC_FW, -(d + 1.5))
        return np.minimum(extrude(wall, p, 0, CC_H), extrude(flange, p, 0, CC_FL))
    return f

def xmas_cutters(step=0.32):
    designs = [("gingerbread", cc_gingerbread, (-36, -38), (36, 38), "#C98B4A", (-48, 0)),
               ("tree", cc_tree, (-39, -41), (39, 44), "#2F7D4F", (48, 0)),
               ("star", cc_star, (-46, -44), (46, 46), "#E9B949", (0, -95))]
    parts = []
    for n, fn, lo, hi, col, (ox, oy) in designs:
        m = CC_FW + 2
        v, f = mesh(_cc_sdf(fn), (lo[0] - m, lo[1] - m, 0), (hi[0] + m, hi[1] + m, CC_H), step)
        v = v.copy(); v[:, 0] += ox; v[:, 1] += oy + 45
        parts.append((n, v, f, col))
    return dict(parts=parts, print_parts=parts, meta=dict(view=(52, -35), line="functional",
        print_hint="Print as shown, flange down on the bed: no supports, no brim. 0.2 mm layers, 3 walls, 100% of the wall is solid. Each cutter is 14 mm tall with a 2 mm pusher flange; flip it over to cut. For dough and play dough: hand wash in lukewarm water, keep it off the dishwasher. PLA is not guaranteed food safe, so for real cookies use a food-safe filament or press through baking paper. Not a toy for children under 3."))

CATALOG2["xmas-cookie-cutters-3"] = (xmas_cutters, dict(title="Christmas Cookie Cutter Set (3 shapes)", title_vi="Bộ 3 Khuôn Bánh Giáng Sinh", price=0.0,
    blurb="Gingerbread friend, Christmas tree and star cutters with a wide pusher flange, a thin cutting edge and a flat print bed. No supports. Free for the holidays.",
    tags=["christmas", "cookie-cutter", "gingerbread", "baking", "play-dough", "holiday", "free"]))

# ---------- Animal Friends tree ornaments (decor, 2026-11-09) ----------
# Four flat 3 mm plaques (fox, penguin, bear, owl) with a built-in hang hole and raised 1.2 mm colour details
# (light and dark layers sit 0.6 mm into the plaque so they fuse when printed). Flat on the bed, no supports.
OR_T, OR_D0, OR_D1 = 3.0, 2.4, 3.6

def _or_shapes(kind):
    """returns (outline sdf, hole centre, light sdf, dark sdf, body colour)"""
    if kind == "fox":
        def body(p):
            d = ell2(p, (0, 0), 24, 18)
            for s in (1, -1): d = _smin(d, poly2(p, np.array([(s * 9, 11), (s * 24, 8), (s * 21, 29)], float)) - 1.5, 3)
            return _smin(d, circ2(p, (0, 21), 6.5), 3)
        light = lambda p: np.minimum(ell2(p, (0, -8), 13, 9), ell2(p, (0, -3), 5, 7))
        dark = lambda p: np.minimum.reduce([circ2(p, (0, -12), 3.0), circ2(p, (-9, 3), 2.3), circ2(p, (9, 3), 2.3)])
        return body, (0, 21.5), light, dark, "#E07B39"
    if kind == "penguin":
        def body(p):
            d = _smin(ell2(p, (0, -4), 20, 28), circ2(p, (0, 22), 13), 7)
            for s in (1, -1): d = np.minimum(d, ell2(p, (s * 10, -31), 9, 4.5))
            return _smin(d, circ2(p, (0, 36), 6.5), 3)
        light = lambda p: np.minimum(ell2(p, (0, -7), 12, 19), ell2(p, (0, 22), 8, 7))
        dark = lambda p: np.minimum.reduce([circ2(p, (-4.5, 23), 2.0), circ2(p, (4.5, 23), 2.0), poly2(p, np.array([(-3.5, 17), (3.5, 17), (0, 12)], float)) - 0.8])
        return body, (0, 36.5), light, dark, "#34507A"
    if kind == "bear":
        def body(p):
            d = circ2(p, (0, 0), 21)
            for s in (1, -1): d = _smin(d, circ2(p, (s * 16, 16), 7.5), 2)
            return _smin(d, circ2(p, (0, 21), 6.5), 3)
        light = lambda p: np.minimum(ell2(p, (0, -7), 11, 8.5), np.minimum(circ2(p, (-16, 16), 3.8), circ2(p, (16, 16), 3.8)))
        dark = lambda p: np.minimum.reduce([circ2(p, (0, -4), 3.2), circ2(p, (-8, 5), 2.3), circ2(p, (8, 5), 2.3)])
        return body, (0, 21.5), light, dark, "#9B6A43"
    def body(p):   # owl
        d = _smin(ell2(p, (0, -2), 21, 27), circ2(p, (0, 14), 17), 8)
        for s in (1, -1): d = _smin(d, poly2(p, np.array([(s * 8, 26), (s * 20, 24), (s * 18, 38)], float)) - 1.5, 3)
        return _smin(d, circ2(p, (0, 31), 6.0), 3)
    light = lambda p: np.minimum.reduce([circ2(p, (-8.5, 12), 8.2), circ2(p, (8.5, 12), 8.2), ell2(p, (0, -12), 11, 11)])
    dark = lambda p: np.minimum.reduce([circ2(p, (-8.5, 12), 3.8), circ2(p, (8.5, 12), 3.8), poly2(p, np.array([(-3, 6), (3, 6), (0, -1)], float)) - 0.8])
    return body, (0, 31.5), light, dark, "#7B5B3A"

def animal_ornaments(step=0.5):
    kinds = [("fox", (-42, 38)), ("penguin", (42, 38)), ("bear", (-42, -42)), ("owl", (42, -42))]
    parts = []
    for k, (ox, oy) in kinds:
        body, hole, light, dark, col = _or_shapes(k)
        def plaque(p, body=body, hole=hole):
            d = body(p) ; d = np.maximum(d, -(circ2(p, hole, 2.3)))
            return extrude(d, p, 0, OR_T)
        def feat(fn, top, body=body):
            def f(p): return extrude(np.maximum(fn(p), body(p) + 1.2), p, OR_D0, top)
            return f
        lo, hi = (-30, -36, 0), (30, 46, OR_D1 + 0.6)
        for nm, fn, c in ((k, plaque, col), (k + "_light", feat(light, OR_D1), "#FFF4E2"), (k + "_dark", feat(dark, OR_D1 + 0.6), "#2B2E3A")):
            v, f = mesh(fn, lo, hi, step)
            v = v.copy(); v[:, 0] += ox; v[:, 1] += oy
            parts.append((nm, v, f, c))
    return dict(parts=parts, print_parts=parts, meta=dict(view=(52, -35), line="decor",
        print_hint="Print flat as shown, no supports, no brim. 0.2 mm layers, 3 walls. Four plaques of 3 mm with raised colour details: swap filament at layer 12 (2.4 mm) for the light and dark details, or print the plaque in one colour. Thread string or ribbon through the 4.6 mm hang hole. Decoration for the tree, not a toy for children under 3."))

CATALOG2["animal-ornaments-4"] = (animal_ornaments, dict(title="Animal Friends Tree Ornaments (4 pack)", title_vi="Bộ 4 Đồ Treo Cây Thông Hình Thú", price=1.99,
    blurb="Fox, penguin, bear and owl: four flat 3D-printed tree ornaments with raised colour details and a built-in hang hole. No supports, one colour swap.",
    tags=["christmas", "ornament", "fox", "penguin", "bear", "owl", "decor", "holiday", "gift"]))

# ---------- Dragon Egg with a baby dragon inside (figure, 2026-11-10) ----------
# Two egg halves (lip fit, 0.25 mm clearance) and a loose baby dragon that sits inside. Bottom half prints base-down,
# the top half prints rim-down (dome up), the dragon prints on its feet. No supports. Dragon is 4 cm tall: not for under 3.
EG_R, EG_H, EG_W = 30.0, 40.0, 2.4      # egg radius, half-height, wall
EG_FLAT = -33.0                          # flat foot of the egg
EG_LIP = 4.5

def _egg_out(p): return ellipsoid(p, np.zeros(3), (EG_R, EG_R, EG_H))
def _egg_in(p): return ellipsoid(p, np.zeros(3), (EG_R - EG_W, EG_R - EG_W, EG_H - EG_W))

def egg_bottom_sdf(p):
    z = p[..., 2]; rr = np.linalg.norm(p[..., :2], axis=-1)
    shell = np.maximum(_egg_out(p), z)                       # outer, cut at the seam z=0
    shell = np.maximum(shell, EG_FLAT - z)                   # flat foot
    cav = np.maximum(_egg_in(p), (EG_FLAT + EG_W) - z)
    cav = np.maximum(cav, np.where(z > -3.0, rr - 25.2, -1.0))   # inward shoulder below the seam
    cav = np.maximum(cav, z - 0.0)
    body = np.maximum(shell, -cav)
    tube = np.maximum(np.maximum(rr - 27.3, 25.2 - rr), np.maximum(-z, z - EG_LIP))
    return np.minimum(body, tube)

def egg_top_sdf(p):
    z = p[..., 2]; rr = np.linalg.norm(p[..., :2], axis=-1)
    shell = np.maximum(_egg_out(p), -z)
    cav = np.minimum(_egg_in(p), np.maximum(rr - 27.55, np.maximum(-z - 0.0, z - (EG_LIP + 0.3))))
    return np.maximum(shell, -cav)

def _dragon_sdf(P):
    P = P * np.array([1.0, -1.0, 1.0])   # the dragon looks toward -y (toward the viewer)
    x, y, z = P[..., 0], P[..., 1], P[..., 2]
    ax = np.abs(x)
    d = ellipsoid(P, np.array([0, 0, 13.0]), (10.5, 9.5, 13.0))                      # body
    d = sunion(d, ellipsoid(P, np.array([0, 3.0, 27.0]), (7.5, 7.0, 6.5)), 4)       # neck
    d = sunion(d, ellipsoid(P, np.array([0, 5.5, 33.0]), (8.8, 8.8, 7.8)), 3)        # head
    d = sunion(d, ellipsoid(P, np.array([0, 13.5, 31.0]), (5.2, 6.0, 4.0)), 2.5)     # snout
    for s in (1, -1):
        d = sunion(d, ellipsoid(P, np.array([s * 7.0, 7.0, 4.0]), (4.6, 6.5, 4.0)), 3)    # front feet
        d = sunion(d, ellipsoid(P, np.array([s * 8.5, -3.0, 4.0]), (4.6, 6.0, 4.0)), 3)   # back feet
        d = np.minimum(d, cyl_axis(P, (s * 5.0, 6.0, 38.0), (s * 8.0, 0.5, 46.0), 1.7))   # horns
    wing = np.array([(3, 12), (21, 34), (16, 25), (21, 21), (14, 17), (17, 11)], float)   # bat wing outline in (|x|, z)
    wd = poly2(np.stack([ax, z, np.zeros_like(z)], -1), wing)
    d = np.minimum(d, np.maximum(wd - 1.2, np.abs(y + 7.8) - 1.2))
    for i, (cy, cz, r) in enumerate([(-8.5, 12, 2.6), (-9.0, 18, 2.4), (-8.0, 24, 2.2)]):
        d = sunion(d, ellipsoid(P, np.array([0, cy, cz]), (1.6, r, r)), 2)       # back ridge
    tail = [(0, -9, 5, 5.0), (3, -15, 4, 4.2), (9, -19, 3.6, 3.5), (16, -19, 3, 2.7), (21, -15, 2.5, 2.0), (23, -10, 2.2, 1.5)]
    for (tx, ty, tz, r) in tail:
        d = np.minimum(d, sphere(P, np.array([tx, ty, tz]), r))
    for a, b in zip(tail[:-1], tail[1:]):
        d = np.minimum(d, cyl_axis(P, a[:3], b[:3], b[3]))
    for s in (1, -1):   # eye pits
        d = np.maximum(d, -sphere(P, np.array([s * 5.2, 11.0, 35.5]), 1.5))
    return np.maximum(d, -z)

def dragon_egg(step=0.8, egg_step=1.3):
    def part(fn, lo, hi, ox, oy, st):
        v, f = mesh(fn, lo, hi, st)
        v = v.copy(); v[:, 0] += ox; v[:, 1] += oy
        return v, f
    parts = []
    v, f = part(egg_bottom_sdf, (-31, -31, -34), (31, 31, EG_LIP + 1), -36, 20, egg_step); parts.append(("egg_bottom", drop_to_bed(v), f, "#6A4FA3"))
    v, f = part(egg_top_sdf, (-31, -31, -1), (31, 31, 41), 36, 20, egg_step); parts.append(("egg_top", drop_to_bed(v), f, "#4F9FA3"))
    v, f = part(_dragon_sdf, (-28, -24, -1), (14, 22, 48), 0, -42, step); parts.append(("baby_dragon", drop_to_bed(v), f, "#E0643A"))
    return dict(parts=parts, print_parts=parts, meta=dict(view=(34, -25), line="figure",
        print_hint="No supports. Bottom half base-down, top half rim-down with the dome up, dragon on its feet; 0.2 mm layers, 3 walls, 15% infill. The two halves click together over a 0.25 mm lip: a dab of glue is optional. The dragon is about 4.7 cm tall and sits loose inside. Contains small parts: not for children under 3."))

CATALOG2["dragon-egg-baby-dragon"] = (dragon_egg, dict(title="Dragon Egg with Baby Dragon Inside", title_vi="Trứng Rồng Có Rồng Con Bên Trong", price=2.99,
    blurb="A two-part dragon egg that clicks shut around a loose 4.7 cm baby dragon. Prints without supports. Great Christmas stocking surprise.",
    tags=["dragon", "dragon-egg", "surprise", "christmas", "stocking-stuffer", "fantasy", "figure", "gift"]))
