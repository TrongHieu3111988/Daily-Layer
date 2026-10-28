"""Clean parametric meshes by revolving a closed (r, z) profile around Z.
Each profile point is (rfun, z) where rfun(theta, z) -> radius array; rfun None means a pole on the axis.
Profile must be ordered so the material lies on the left when walking it (CCW in r-z plane).
"""
import numpy as np

def revolve(profile, nth=256):
    th = np.linspace(0, 2 * np.pi, nth, endpoint=False)
    verts, rows = [], []
    for rf, z in profile:
        if rf is None:
            rows.append(("pole", len(verts))); verts.append([0.0, 0.0, z])
        else:
            r = np.broadcast_to(rf(th, z), th.shape)
            start = len(verts)
            verts.extend(np.stack([r * np.cos(th), r * np.sin(th), np.full(nth, z)], 1).tolist())
            rows.append(("ring", start))
    faces = []
    n = len(rows)
    closed = rows[0][0] == "ring" and rows[-1][0] == "ring"
    pairs = [(i, i + 1) for i in range(n - 1)] + ([(n - 1, 0)] if closed else [])
    j = np.arange(nth); j1 = (j + 1) % nth
    for a, b in pairs:
        ka, sa = rows[a]; kb, sb = rows[b]
        if ka == "ring" and kb == "ring":
            A, A1, B, B1 = sa + j, sa + j1, sb + j, sb + j1
            faces.append(np.stack([A, B, A1], 1)); faces.append(np.stack([A1, B, B1], 1))
        elif ka == "pole":
            B, B1 = sb + j, sb + j1
            faces.append(np.stack([np.full(nth, sa), B, B1], 1))
        else:
            A, A1 = sa + j, sa + j1
            faces.append(np.stack([A, np.full(nth, sb), A1], 1))
    v = np.asarray(verts, np.float32); f = np.concatenate(faces).astype(np.int64)
    from forge import signed_volume
    if signed_volume(v, f) < 0: f = f[:, ::-1]
    return v, f

def const(r):
    return lambda th, z: np.full_like(th, r, dtype=float)
