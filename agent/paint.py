"""Painted (per-triangle colour) meshes from Sculpt Studio colour shares.

The sculpt exporter writes, per mesh vertex, how strongly each colour owns that point (smooth field).
Here the triangles are cut exactly along the contour where two colours are equal, so every colour
border is a smooth line through the triangles instead of a zig-zag along triangle edges.
Cutting shares the new edge points between neighbouring triangles, so a watertight mesh stays watertight.
"""
import struct, zipfile
import numpy as np


def read_paint(path):
    raw = open(path, "rb").read()
    nv, nf, L = struct.unpack("<III", raw[:12]); o = 12
    pos = np.frombuffer(raw, "<f4", nv * 3, o).reshape(-1, 3).astype(np.float64); o += nv * 12
    idx = np.frombuffer(raw, "<u4", nf * 3, o).reshape(-1, 3).astype(np.int64); o += nf * 12
    sh = np.frombuffer(raw, "<f4", nv * L, o).reshape(-1, L).astype(np.float64); o += nv * L * 4
    cols = np.frombuffer(raw, np.uint8, L * 3, o).reshape(-1, 3).copy()
    return pos, idx, sh, cols


def relax(sh, f, iters):
    """Smooth the colour shares along the surface (borders follow soft curves, tiny specks vanish)."""
    import scipy.sparse as sp
    n = len(sh)
    e = np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]); e = np.concatenate([e, e[:, ::-1]])
    A = sp.coo_matrix((np.ones(len(e)), (e[:, 0], e[:, 1])), shape=(n, n)).tocsr(); A.data[:] = 1.0
    deg = np.asarray(A.sum(1)).ravel(); deg[deg == 0] = 1
    for _ in range(iters):
        sh = 0.5 * sh + 0.5 * (A @ sh) / deg[:, None]
    return sh


def cut(v, f, sh):
    """Split triangles along colour contours. Returns (v2, f2, label per triangle)."""
    w = sh.argmax(1)
    wf = w[f]
    same = (wf[:, 0] == wf[:, 1]) & (wf[:, 1] == wf[:, 2])
    out_f = [f[same]]; out_l = [wf[same, 0]]
    verts = [v]; nxt = len(v); emap = {}
    newv = []

    def edge_pt(p, q):
        nonlocal nxt
        a, b = (p, q) if p < q else (q, p)
        k = (a, b)
        if k in emap: return emap[k]
        wa, wb = w[a], w[b]
        da = sh[a, wa] - sh[a, wb]; db = sh[b, wa] - sh[b, wb]
        t = da / (da - db) if da - db > 1e-12 else 0.5
        t = min(max(t, 0.03), 0.97)
        newv.append(v[a] + t * (v[b] - v[a])); emap[k] = nxt; nxt += 1
        return emap[k]

    tris, labs = [], []
    for (a, b, c), (la, lb, lc) in zip(f[~same], wf[~same]):
        if la != lb and lb != lc and la != lc:          # three colours meet: fan around a centre point
            mab, mbc, mca = edge_pt(a, b), edge_pt(b, c), edge_pt(c, a)
            ctr = nxt; newv.append((newv[mab - len(v)] + newv[mbc - len(v)] + newv[mca - len(v)]) / 3); nxt += 1
            for i, mi, mo, l in ((a, mab, mca, la), (b, mbc, mab, lb), (c, mca, mbc, lc)):
                tris += [(i, mi, ctr), (i, ctr, mo)]; labs += [l, l]
            continue
        # two colours: rotate so the lone vertex comes first (keeps winding)
        if la == lb: i, j, k, li, lj = c, a, b, lc, la
        elif lb == lc: i, j, k, li, lj = a, b, c, la, lb
        else: i, j, k, li, lj = b, c, a, lb, lc
        mij, mik = edge_pt(i, j), edge_pt(i, k)
        tris += [(i, mij, mik), (mij, j, k), (mij, k, mik)]; labs += [li, lj, lj]
    if newv: verts.append(np.array(newv))
    if tris: out_f.append(np.array(tris, np.int64)); out_l.append(np.array(labs))
    return np.concatenate(verts), np.concatenate(out_f), np.concatenate(out_l)


def hexcol(c):
    return "#%02X%02X%02X" % tuple(int(x) for x in c)


def write_obj(path_obj, v, f, lab, cols, names):
    """OBJ + MTL, faces grouped by material. Bambu Studio maps each colour to a filament on import."""
    import os
    mtl = os.path.splitext(path_obj)[0] + ".mtl"
    with open(mtl, "w") as fh:
        for li, n in enumerate(names):
            r, g, b = (cols[li] / 255.0)
            fh.write(f"newmtl {n}\nKd {r:.4f} {g:.4f} {b:.4f}\nKa 0 0 0\nKs 0 0 0\nd 1\nillum 1\n\n")
    with open(path_obj, "w") as fh:
        fh.write(f"mtllib {os.path.basename(mtl)}\n")
        fh.write("".join(f"v {a:.3f} {b:.3f} {c:.3f}\n" for a, b, c in v))
        for li, n in enumerate(names):
            sel = f[lab == li] + 1
            if not len(sel): continue
            fh.write(f"usemtl {n}\n")
            fh.write("".join(f"f {a} {b} {c}\n" for a, b, c in sel))
    return mtl


def paint_code(s):
    """PrusaSlicer/Bambu triangle paint string for filament s (1-based), whole triangle."""
    return format(s << 2, "X") if s < 3 else format(s - 3, "X") + "C"


def write_3mf_painted(path, v, f, lab, cols, names, title):
    """One solid object, each triangle tagged with its colour.
    m:colorgroup + pid/p1 is what Bambu Studio / Orca import as colours (BambuStudio bbs_3mf.cpp reads m:colorgroup,
    not basematerials); slic3rpe:mmu_segmentation gives PrusaSlicer the same colours as filament painting."""
    cg = "".join(f'<m:color color="{hexcol(cols[i])}FF"/>' for i in range(len(names)))
    vs = "".join(f'<vertex x="{a:.3f}" y="{b:.3f}" z="{d:.3f}"/>' for a, b, d in v)
    ts = "".join(f'<triangle v1="{a}" v2="{b}" v3="{d}" pid="1" p1="{l}" slic3rpe:mmu_segmentation="{paint_code(int(l) + 1)}"/>' for (a, b, d), l in zip(f, lab))
    model = ('<?xml version="1.0" encoding="UTF-8"?><model unit="millimeter" xml:lang="en-US" '
             'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
             'xmlns:m="http://schemas.microsoft.com/3dmanufacturing/material/2015/02" '
             'xmlns:slic3rpe="http://schemas.slic3r.org/3mf/2017/06">'
             f'<metadata name="Title">{title}</metadata><resources><m:colorgroup id="1">{cg}</m:colorgroup>'
             f'<object id="2" name="{title}" type="model" pid="1" pindex="{int(np.bincount(lab).argmax())}"><mesh><vertices>{vs}</vertices><triangles>{ts}</triangles></mesh></object>'
             '</resources><build><item objectid="2"/></build></model>')
    ct = ('<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct); z.writestr("_rels/.rels", rels); z.writestr("3D/3dmodel.model", model)
