"""Product recipes. Each returns dict(parts=[(name, v, f, hex)], meta={...})."""
import numpy as np
from forge import *
from revolve import revolve, const

def seg_slab(p, a, b, halfx, halft, r=1.5):
    """Flat slab spanning segment a->b in the YZ plane, width 2*halfx in X, thickness 2*halft."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = b - a; L = np.linalg.norm(d); u = d / L; n = np.array([-u[1], u[0]])
    q = p[..., 1:] - a
    t = q @ u - L / 2; s = q @ n
    loc = np.stack([p[..., 0], t, s], -1)
    return box(loc, np.zeros(3), (halfx, L / 2, halft), r)

# ---------------- functional ----------------
def desk_bin(step=0.55):
    W, D, H, wall, floor, div = 120, 62, 44, 2.0, 1.8, 1.6
    cw = (W - 2 * wall - 2 * div) / 3
    def f(p):
        outer = box(p, np.array([0, 0, H / 2]), (W / 2, D / 2, H / 2), 4.0)
        cells = [box(p, np.array([-W / 2 + wall + cw / 2 + i * (cw + div), 0, floor + H / 2 + 5]),
                     (cw / 2, D / 2 - wall, H / 2 + 5), 3.0) for i in range(3)]
        # label notch on the front wall
        label = box(p, np.array([0, -D / 2, H - 6]), (24, 0.6, 4), 0.4)
        # stacking lip: shallow recess under the base
        recess = box(p, np.array([0, 0, -1.0]), (W / 2 - 3.2, D / 2 - 3.2, 1.6), 2.0)
        return diff(outer, *cells, label, recess)
    v, fc = mesh(f, (-W/2, -D/2, 0), (W/2, D/2, H), step)
    return dict(parts=[("bin", drop_to_bed(v), fc, "#E9E4D8")],
                meta=dict(line="functional", print_hint="0.2 mm layer, 3 walls, 10% infill, no supports"))

def phone_stand(step=0.5):
    def f(p):
        base = box(p, np.array([0, 4, 2.5]), (38, 34, 2.5), 2.0)
        back = seg_slab(p, (-14, 2), (22, 80), 34, 2.6, 1.6)          # leaning back plate
        leg = seg_slab(p, (36, 3), (21.5, 77), 30, 2.4, 1.6)           # rear A-frame leg
        lip = box(p, np.array([0, -24, 9]), (38, 3, 9), 1.5)          # front lip
        ledge = box(p, np.array([0, -18.5, 3.5]), (38, 6, 3.5), 1.0)  # floor between lip and plate
        shape = union(base, back, leg, lip, ledge)
        slot = box(p, np.array([0, -22, 12]), (7, 12, 14), 2.0)       # charging cable slot
        window = seg_slab(p, (2, 30), (14, 56), 16, 6, 6)              # material-saving window
        return diff(shape, slot, window)
    v, fc = mesh(f, (-38, -27, 0), (38, 38, 82), step)
    return dict(parts=[("stand", drop_to_bed(v), fc, "#2F3A3F")],
                meta=dict(line="functional", print_hint="0.2 mm layer, 4 walls, 15% gyroid, prints flat, no supports"))

# ---------------- print-in-place ----------------
def gyro_rings(n=5, hub_r=6.0, w=5.0, gap=0.6, h=5.0, a=1.6):
    parts = []
    cols = ["#F2A65A", "#EF6F6C", "#5B8E7D", "#4A6FA5", "#2E3047"]
    r_in = hub_r
    for i in range(n):
        groove = i > 0
        ridge = i < n - 1
        ro = r_in + w
        prof = []
        ri_mid = r_in + (a if groove else 0)
        ro_mid = ro + (a if ridge else 0)
        prof = [(const(r_in), -h), (const(ro), -h), (const(ro_mid), 0.0), (const(ro), h),
                (const(r_in), h), (const(ri_mid), 0.0)]
        prof = [(fn, z + h) for fn, z in prof]
        v, f = revolve(prof, 192)
        parts.append((f"ring{i+1}", v, f, cols[i % len(cols)]))
        r_in = ro + gap
    return dict(parts=parts, meta=dict(line="print-in-place",
                print_hint="Print as one plate, 0.16 mm layer, no supports, 0.6 mm clearance; twist gently to free rings"))

# ---------------- decor ----------------
def twist_vase(H=150, petals=6, twist=np.pi * 0.75, wall=2.0, floor=2.2, nz=90):
    def R(z):
        t = z / H
        return 34 + 16 * np.sin(np.pi * (0.15 + 0.75 * t)) - 10 * t
    outer = lambda th, z: R(z) * (1 + 0.10 * np.cos(petals * (th + twist * z / H)))
    inner = lambda th, z: outer(th, z) - wall
    zs = np.linspace(0, H, nz)
    prof = [(None, 0.0)] + [(outer, z) for z in zs] + [(inner, H)] + \
           [(inner, z) for z in zs[::-1] if z > floor + 0.5] + [(inner, floor), (None, floor)]
    v, f = revolve(prof, 288)
    return dict(parts=[("vase", v, f, "#C9B79C")],
                meta=dict(line="decor", print_hint="Works as solid model or in Vase mode (spiral); PLA silk looks great"))

def rib_planter(H=95, wall=2.4, floor=3.0, hole=5.0, ribs=24, nz=60):
    def R(z):
        t = z / H
        return 48 + 10 * t ** 0.8
    outer = lambda th, z: R(z) * (1 + 0.035 * np.abs(np.cos(ribs / 2 * th)) ** 0.6)
    inner = lambda th, z: np.full_like(th, R(z) - wall - 1.2)
    zs = np.linspace(0, H, nz)
    prof = [(const(hole), 0.0)] + [(outer, z) for z in zs] + [(inner, H)] + \
           [(inner, z) for z in zs[::-1] if z > floor + 0.5] + [(inner, floor), (const(hole), floor)]
    v, f = revolve(prof, 288)
    # matching drip saucer
    sp = [(None, 0.0), (const(58), 0.0), (const(60), 3.0), (const(61), 9.0), (const(59), 9.0),
          (const(57.5), 2.0), (None, 2.0)]
    sv, sf = revolve(sp, 288)
    sv = sv.copy(); sv[:, 0] += 135
    return dict(parts=[("planter", v, f, "#D9CBB8"), ("saucer", sv, sf, "#B9A88F")],
                meta=dict(line="decor", print_hint="0.2 mm layer, 3 walls; drainage hole included; saucer prints separately"))

# ---------------- multi-colour figure ----------------
EYE = np.array([-26.0, 15.5, 22.0])
def _eye_frame(side):
    c = EYE * np.array([1, side, 1])
    g = np.array([(c[0] + 5) / 900, c[1] / 484, (c[2] - 20) / 361]); n = g / np.linalg.norm(g)
    return c, n

def whale(step=0.42, cut=9.0):
    """Chibi whale in 3 colours: blue body, cream belly, black button eyes. Pegs + holes for assembly."""
    def shape(p):
        body = ellipsoid(p, np.array([-5, 0, 20]), (30, 22, 19))
        stalk = ellipsoid(p, np.array([24, 0, 24]), (15, 9, 9))
        fluke = ellipsoid(p, np.array([37, 0, 32]), (6, 16, 3.2))
        fins = union(ellipsoid(p, np.array([-6, 21, 16.5]), (9, 6, 2.6)),
                     ellipsoid(p, np.array([-6, -21, 16.5]), (9, 6, 2.6)))
        s = sunion(sunion(sunion(body, stalk, 7), fluke, 4), fins, 3)
        return np.maximum(s, 3.0 - p[..., 2])  # flat bottom at z=3
    pegs = [(-14.0, 0.0), (8.0, 0.0)]
    zc = 3.0 + cut
    def belly(p):
        b = np.maximum(shape(p), p[..., 2] - zc)
        pg = union(*[cyl_z(p, np.array([x, y, 0]), 2.5, zc - 1, zc + 4.0) for x, y in pegs])
        return union(b, pg)
    def top(p):
        t = np.maximum(shape(p), zc - p[..., 2])
        holes = [cyl_z(p, np.array([x, y, 0]), 2.75, zc - 1, zc + 4.6) for x, y in pegs]
        for side in (1, -1):
            c, n = _eye_frame(side)
            holes.append(cyl_axis(p, c + n * 3, c - n * 4.8, 1.45))
        return diff(t, *holes)
    lo, hi = (-37, -24, 2), (44, 24, 43)
    bv, bf = mesh(belly, lo, (44, 24, zc + 5), step)
    tv, tf = mesh(top, (-37, -24, zc - 1), hi, step)
    def eye_local(p):
        dome = inter(sphere(p, np.array([0, 0, -1.2]), 3.6), -p[..., 2], p[..., 2] - 2.0)
        dome = np.maximum(sphere(p, np.array([0, 0, -1.2]), 3.6), np.maximum(-p[..., 2], p[..., 2] - 2.0))
        pin = cyl_z(p, np.zeros(3), 1.2, -4.0, 0.3)
        return union(dome, pin)
    ev, ef = mesh(eye_local, (-4, -4, -4), (4, 4, 2.2), 0.18)
    # assembled preview: place eyes on the body (local +z -> surface normal)
    def place(v, side):
        c, n = _eye_frame(side)
        z = n; x = np.cross([0, 0, 1], z); x /= np.linalg.norm(x); y = np.cross(z, x)
        return (v @ np.stack([x, y, z])) + c - n * 0.6
    assembled = [("belly", bv, bf, "#F3EAD7"), ("body", tv, tf, "#4F8FC0"),
                 ("eye_l", place(ev, 1).astype(np.float32), ef, "#1D1F24"),
                 ("eye_r", place(ev, -1).astype(np.float32), ef, "#1D1F24")]
    # print layout: body flipped (cut face down), belly flat, two eyes pin-up (flat face down)
    tv_p = tv.copy(); tv_p[:, 2] = -tv_p[:, 2]; tv_p = drop_to_bed(tv_p); tv_p[:, 1] += 0
    tf_p = tf[:, ::-1]
    bv_p = drop_to_bed(bv); bv_p[:, 1] += 55
    ev_p = ev.copy(); ev_p[:, 2] = -ev_p[:, 2]; ev_p = drop_to_bed(ev_p); ef_p = ef[:, ::-1]
    e1 = ev_p.copy(); e1[:, 0] += 60; e2 = ev_p.copy(); e2[:, 0] += 60; e2[:, 1] += 12
    printplate = [("body", tv_p, tf_p, "#4F8FC0"), ("belly", bv_p, bf, "#F3EAD7"),
                  ("eye_l", e1, ef_p, "#1D1F24"), ("eye_r", e2, ef_p, "#1D1F24")]
    return dict(parts=assembled, print_parts=printplate,
                meta=dict(view=(18, 50), line="figure", print_hint="3 colours, 4 parts; press-fit pegs (0.25 mm clearance); 0.12 mm layer for the body, no supports with body printed cut-side down"))

CATALOG = {
    "desk-bin-3cell": (desk_bin, dict(title="Tri-Cell Desk Bin", price=1.99,
        blurb="Three-compartment organizer with a label notch and a stacking recess. Fits pens, bits, SD cards and clutter.",
        tags=["organizer", "desk", "office"])),
    "phone-stand-aframe": (phone_stand, dict(title="A-Frame Phone Stand", price=1.49,
        blurb="Stable A-frame stand with a charging-cable slot. Holds phones and small tablets in portrait or landscape.",
        tags=["phone", "desk", "gift"])),
    "gyro-rings-5": (gyro_rings, dict(title="Gyro Rings Fidget", price=0.0,
        blurb="Five interlocking rings that print as one piece and spin freely. No assembly, no supports.",
        tags=["fidget", "print-in-place", "toy"])),
    "twist-vase-petal": (twist_vase, dict(title="Petal Twist Vase", price=2.49,
        blurb="Six-petal vase with a slow twist. Prints solid or in spiral vase mode for a seamless finish.",
        tags=["vase", "home", "vase-mode"])),
    "rib-planter-saucer": (rib_planter, dict(title="Ribbed Planter + Saucer", price=1.99,
        blurb="Soft-ribbed planter with drainage hole and a matching drip saucer.",
        tags=["planter", "garden", "home"])),
    "chibi-whale-4part": (whale, dict(title="Chibi Whale (multi-colour)", price=3.99,
        blurb="Cute whale split by colour into body, belly and button eyes. Press-fit pegs, ready for AMS or manual swaps.",
        tags=["figure", "multicolor", "cute"])),
}
