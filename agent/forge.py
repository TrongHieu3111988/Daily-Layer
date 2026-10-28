"""Forge: tiny implicit-geometry kit for printable models.
Shapes are functions f(x,y,z) -> value, negative inside (mm units).
mesh() runs marching cubes on a padded grid so every shell is closed.
"""
import numpy as np, struct, zipfile, io, json
from skimage.measure import marching_cubes

# ---------- primitives ----------
def box(p, c, half, r=0.0):
    q = np.abs(p - c) - (np.asarray(half) - r)
    out = np.linalg.norm(np.maximum(q, 0), axis=-1)
    inside = np.minimum(q.max(axis=-1), 0)
    return out + inside - r

def sphere(p, c, r):
    return np.linalg.norm(p - c, axis=-1) - r

def ellipsoid(p, c, rad):
    rad = np.asarray(rad, float)
    k0 = np.linalg.norm((p - c) / rad, axis=-1)
    k1 = np.linalg.norm((p - c) / rad**2, axis=-1)
    return k0 * (k0 - 1.0) / np.maximum(k1, 1e-9)

def cyl_z(p, c, r, h0, h1):
    d = np.linalg.norm(p[..., :2] - c[:2], axis=-1) - r
    dz = np.maximum(h0 - p[..., 2], p[..., 2] - h1)
    return np.maximum(d, dz)

def cyl_axis(p, a, b, r):
    a, b = np.asarray(a, float), np.asarray(b, float)
    ba = b - a; L = np.linalg.norm(ba); u = ba / L
    pa = p - a
    t = pa @ u
    radial = np.linalg.norm(pa - t[..., None] * u, axis=-1) - r
    axial = np.maximum(-t, t - L)
    return np.maximum(radial, axial)

def union(*fs): return np.minimum.reduce(fs)
def inter(*fs): return np.maximum.reduce(fs)
def diff(a, *bs): return np.maximum(a, -np.minimum.reduce(bs)) if bs else a
def sunion(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b * (1 - h) + a * h - k * h * (1 - h)

# ---------- grid & meshing ----------
def grid(lo, hi, step):
    lo = np.asarray(lo, float) - 2 * step; hi = np.asarray(hi, float) + 2 * step
    axes = [np.arange(lo[i], hi[i] + step, step) for i in range(3)]
    X, Y, Z = np.meshgrid(*axes, indexing="ij")
    return np.stack([X, Y, Z], -1), lo, step

def mesh(fn, lo, hi, step):
    P, origin, s = grid(lo, hi, step)
    vol = fn(P).astype(np.float32)
    vol[0, :, :] = vol[-1, :, :] = vol[:, 0, :] = vol[:, -1, :] = vol[:, :, 0] = vol[:, :, -1] = 1.0
    v, f, _, _ = marching_cubes(vol, level=1e-4, spacing=(s, s, s))  # tiny offset: exact zeros on grid planes make non-manifold edges
    v = v + origin
    if signed_volume(v, f) < 0: f = f[:, ::-1]
    return v.astype(np.float32), f.astype(np.int64)

def signed_volume(v, f):
    a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    return float(np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6.0)

def check(v, f):
    e = np.sort(np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]), axis=1)
    _, cnt = np.unique(e, axis=0, return_counts=True)
    shells = count_shells(f, len(v))
    ext = v.max(0) - v.min(0)
    return {"triangles": int(len(f)), "watertight": bool((cnt == 2).all()),
            "bad_edges": int((cnt != 2).sum()), "shells": shells,
            "volume_cm3": round(signed_volume(v, f) / 1000, 2),
            "size_mm": [round(float(x), 1) for x in ext],
            "min_z": round(float(v[:, 2].min()), 2)}

def count_shells(f, n):
    parent = np.arange(n)
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for a, b, c in f:
        ra, rb, rc = find(a), find(b), find(c)
        parent[rb] = ra; parent[find(rc)] = ra
    used = np.unique(f)
    return len({find(i) for i in used})

def drop_to_bed(v):
    v = v.copy(); v[:, 2] -= v[:, 2].min(); return v

# ---------- writers ----------
def write_stl(path, v, f, name="forge"):
    tri = v[f]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    rec = np.zeros(len(f), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    rec["n"] = n; rec["v"] = tri
    with open(path, "wb") as fh:
        fh.write(name.encode()[:80].ljust(80, b" "))
        fh.write(struct.pack("<I", len(f)))
        fh.write(rec.tobytes())

def write_3mf(path, parts):
    """parts: list of (name, v, f, hexcolor). One build item per part, colors as basematerials."""
    mats = "".join(f'<base name="{n}" displaycolor="{c}FF"/>' for n, _, _, c in parts)
    objs, items = [], []
    for i, (n, v, f, c) in enumerate(parts):
        vs = "".join(f'<vertex x="{a:.3f}" y="{b:.3f}" z="{d:.3f}"/>' for a, b, d in v)
        ts = "".join(f'<triangle v1="{a}" v2="{b}" v3="{d}"/>' for a, b, d in f)
        oid = i + 2
        objs.append(f'<object id="{oid}" name="{n}" type="model" pid="1" pindex="{i}"><mesh><vertices>{vs}</vertices><triangles>{ts}</triangles></mesh></object>')
        items.append(f'<item objectid="{oid}"/>')
    model = ('<?xml version="1.0" encoding="UTF-8"?><model unit="millimeter" xml:lang="en-US" '
             'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"><resources>'
             f'<basematerials id="1">{mats}</basematerials>{"".join(objs)}</resources><build>{"".join(items)}</build></model>')
    ct = ('<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct); z.writestr("_rels/.rels", rels); z.writestr("3D/3dmodel.model", model)

# ---------- preview render (numpy z-buffer) ----------
def render(parts, path, size=900, bg=(226, 229, 226), elev=28, azim=-55):
    """parts: list of (v, f, rgb tuple 0-255). Simple flat-shaded rasterizer with soft key+fill light."""
    from PIL import Image
    allv = np.concatenate([p[0] for p in parts])
    ctr = (allv.max(0) + allv.min(0)) / 2
    e, a = np.radians(elev), np.radians(azim)
    Rz = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    Rx = np.array([[1, 0, 0], [0, np.cos(e), -np.sin(e)], [0, np.sin(e), np.cos(e)]])
    # camera looks along -y in view space; map world -> view (x right, y depth, z up)
    M = Rx @ Rz
    proj = [(((v - ctr) @ M.T), f, col) for v, f, col in parts]
    pts = np.concatenate([p[0] for p in proj])
    span = max(np.ptp(pts[:, 0]), np.ptp(pts[:, 2])) * 1.18
    S = size; ss = 2; W = S * ss
    zbuf = np.full((W, W), np.inf, np.float32); img = np.zeros((W, W, 3), np.float32)
    mask = np.zeros((W, W), bool)
    L1 = np.array([-0.45, -0.7, 0.55]); L1 /= np.linalg.norm(L1)
    L2 = np.array([0.6, -0.4, 0.2]); L2 /= np.linalg.norm(L2)
    for v, f, col in proj:
        tri = v[f]
        n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        # smooth (per-vertex) shading so the render shows the true surface, not the triangulation
        vn = np.zeros_like(v)
        for k in range(3): np.add.at(vn, f[:, k], n)
        vn /= np.maximum(np.linalg.norm(vn, axis=1, keepdims=True), 1e-12)
        n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
        keep = n[:, 1] < 0  # facing camera (camera at -y)
        tri, n, fk = tri[keep], n[keep], f[keep]
        def shade_of(nn):
            return 0.32 + 0.58 * np.clip(nn @ L1, 0, 1) + 0.18 * np.clip(nn @ L2, 0, 1) + 0.12 * np.clip(1 - np.abs(nn[:, 1]), 0, 1) ** 2
        vshade = shade_of(vn)
        cvert = np.clip(vshade[:, None] * (np.asarray(col) / 255.0)[None, :], 0, 1)
        c = cvert[fk]   # (T, 3 corners, rgb)
        sx = (tri[..., 0] / span + 0.5) * W
        sy = (0.5 - tri[..., 2] / span) * W
        depth = tri[..., 1].mean(1)
        order = np.argsort(-depth)
        for i in order:  # painter-ish with zbuffer per bbox
            xs, ys = sx[i], sy[i]
            x0, x1 = int(max(xs.min(), 0)), int(min(xs.max() + 1, W))
            y0, y1 = int(max(ys.min(), 0)), int(min(ys.max() + 1, W))
            if x1 <= x0 or y1 <= y0: continue
            gx, gy = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(y0, y1) + 0.5)
            (ax, bx, cx), (ay, by, cy) = xs, ys
            den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
            if abs(den) < 1e-9: continue
            w0 = ((by - cy) * (gx - cx) + (cx - bx) * (gy - cy)) / den
            w1 = ((cy - ay) * (gx - cx) + (ax - cx) * (gy - cy)) / den
            w2 = 1 - w0 - w1
            ins = (w0 >= -1e-4) & (w1 >= -1e-4) & (w2 >= -1e-4)
            if not ins.any(): continue
            d = w0 * tri[i, 0, 1] + w1 * tri[i, 1, 1] + w2 * tri[i, 2, 1]
            zb = zbuf[y0:y1, x0:x1]
            upd = ins & (d < zb)
            zb[upd] = d[upd]
            pix = w0[..., None] * c[i, 0] + w1[..., None] * c[i, 1] + w2[..., None] * c[i, 2]
            img[y0:y1, x0:x1][upd] = pix[upd]
            mask[y0:y1, x0:x1] |= upd
    out = np.empty((W, W, 3), np.float32); out[:] = np.asarray(bg) / 255.0
    # soft ground shadow
    yy, xx = np.mgrid[0:W, 0:W]
    lowest = np.where(mask.any(1))[0]
    if len(lowest):
        gy = lowest.max(); cols = np.where(mask.any(0))[0]
        cx, rx = (cols.min() + cols.max()) / 2, (cols.max() - cols.min()) / 2
        sh = np.exp(-(((xx - cx) / (rx * 0.95)) ** 2 + ((yy - gy) / (W * 0.035)) ** 2) * 2.2)
        out *= (1 - 0.22 * sh[..., None])
    out[mask] = img[mask]
    im = Image.fromarray((out * 255).astype(np.uint8)).resize((S, S), Image.LANCZOS)
    im.save(path, quality=90)
