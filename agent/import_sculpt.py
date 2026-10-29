"""Package animals sculpted with the Sculpt Studio engine into shop products (same layout as build.py output).
usage: python import_sculpt.py <sculpted_dir> <out_dir> <slug>:<name>:<title>:<price> ...
"""
import sys, os, json, zipfile, struct
import numpy as np
from forge import check, write_3mf, render, write_stl
from build import write_webmesh_fc, hex2rgb
from paint import read_paint, relax, cut, write_obj, write_3mf_painted, hexcol

def taubin(v, f, iters=12, lam=0.5, mu=-0.53):
    """Volume-preserving smoothing: removes the voxel stair pattern without shrinking the figure."""
    import scipy.sparse as sp
    n = len(v)
    e = np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]])
    e = np.concatenate([e, e[:, ::-1]])
    A = sp.coo_matrix((np.ones(len(e)), (e[:, 0], e[:, 1])), shape=(n, n)).tocsr()
    A.data[:] = 1.0
    deg = np.asarray(A.sum(1)).ravel(); deg[deg == 0] = 1
    v = v.astype(np.float64)
    for _ in range(iters):
        for k in (lam, mu):
            v = v + k * (A @ v / deg[:, None] - v)
    return v.astype(np.float32)

def read_stl(p):
    b = open(p, "rb").read(); n = struct.unpack("<I", b[80:84])[0]
    rec = np.frombuffer(b[84:84 + n * 50], dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    tri = rec["v"].reshape(-1, 3)
    uq, inv = np.unique(tri, axis=0, return_inverse=True)
    return uq.astype(np.float32), inv.reshape(-1, 3).astype(np.int64)

BLURB = {
    "chick": "Round little chick with a tuft, rosy cheeks and orange feet. Sculpted in Sculpt Studio and split by colour for AMS.",
    "bunny": "Soft bunny with tall ears, pink nose and a fluffy tail. One solid piece, colour-split 3MF included.",
    "bear": "Chubby bear cub with a tan muzzle and belly. Prints as one piece with no loose parts.",
    "penguin": "Little penguin with a white tummy, orange beak and feet. Colour-split for multi-material printers.",
    "fox": "Fox cub with a fluffy white-tipped tail, dark ear tips and a tiny smile. Sculpted at high resolution in Sculpt Studio.",
    "frog": "Grinning frog with big glossy eyes, rosy cheeks and a pale belly. One solid piece, colour-split 3MF included.",
    "axolotl": "Smiling axolotl with feathery gills and a curled tail. Prints as one piece with no loose parts.",
    "gingerbread": "Chubby gingerbread buddy with white icing trim, gumdrop buttons and a knitted scarf. One solid piece, colour-split for AMS.",
    "kitten": "Tabby kitten with pink ears, a white muzzle and its tail wrapped round its paws. Colour-split for AMS.",
}

def main():
    src, out = sys.argv[1], sys.argv[2]
    for spec in sys.argv[3:]:
        slug, name, title, price = spec.split(":")
        meta = json.load(open(os.path.join(src, name, "meta.json")))
        hex2name = {p["hex"].upper(): p["colour"] for p in meta["parts"]}
        d = os.path.join(out, slug); os.makedirs(d, exist_ok=True)
        # print body + colour shares from the sculpt; smooth the clay, then cut colours along their contours
        bv, bf, bsh, cols = read_paint(os.path.join(src, name, "body_paint.bin"))
        bv = taubin(bv, bf); bv[:, 2] -= bv[:, 2].min()
        names = [hex2name.get(hexcol(c), "colour%d" % i) for i, c in enumerate(cols)]
        # near-identical colours (eye ink on a black penguin) share one filament
        merge = np.arange(len(cols)); order = np.argsort(-np.bincount(bsh.argmax(1), minlength=len(cols))); kept = []
        for i in order:     # bigger colour areas first, so the body colour keeps its name
            for j in kept:
                if np.abs(cols[i].astype(int) - cols[j].astype(int)).sum() < 40: merge[i] = j; break
            else: kept.append(i)
        keepc = np.unique(merge); remap = {c: k for k, c in enumerate(keepc)}
        cmap = np.array([remap[merge[i]] for i in range(len(cols))])
        names = [names[c] for c in keepc]; pcols = cols[keepc]
        pv, pf, plab = cut(bv, bf, relax(bsh, bf, 10)); plab = cmap[plab]
        rep_body = check(bv, bf); rep_paint = check(pv, pf)
        # colour-split parts (one solid per colour) for slicers without painting
        parts = []
        for p in meta["parts"]:
            v, f = read_stl(os.path.join(src, name, f"part_{p['colour']}.stl"))
            v = taubin(v, f)
            parts.append((p["colour"], v, f, p["hex"]))
        reps = {c: check(v, f) for c, v, f, _ in parts}
        ok = rep_body["watertight"] and rep_paint["watertight"] and all(r["watertight"] for r in reps.values())
        write_3mf(os.path.join(d, f"{slug}_parts.3mf"), parts)
        write_3mf_painted(os.path.join(d, f"{slug}_painted.3mf"), pv, pf, plab, pcols, names, title)
        mtl = write_obj(os.path.join(d, f"{slug}_painted.obj"), pv, pf, plab, pcols, names)
        write_stl(os.path.join(d, f"{slug}.stl"), bv, bf, slug)
        zp = os.path.join(d, f"{slug}_files.zip")
        with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for fn in (f"{slug}.stl", f"{slug}_painted.obj", os.path.basename(mtl), f"{slug}_painted.3mf", f"{slug}_parts.3mf"):
                z.write(os.path.join(d, fn), fn)
            z.writestr("README.txt", f"""{title}

Which file to open:
- {slug}_painted.obj (+ .mtl): one solid piece with the colours painted on. Bambu Studio: drag it in, the import window
  matches each colour to a filament automatically (change any match in its drop-down), click OK. Keep the .mtl next to the .obj.
- {slug}_painted.3mf: the same painted piece as a 3MF (per-triangle colours, 3MF standard). Bambu Studio 2.5+ offers to import its colours.
- {slug}_parts.3mf: one solid per colour. Load as one object with multiple parts, then pick a filament for each part (PrusaSlicer, Orca, older Bambu Studio).
- {slug}.stl: single colour.

Colours: {", ".join(names)}.
Print: 0.12-0.16 mm layers, 3 walls, 10-15% infill, no supports for the body; tree supports only if your slicer flags the chin.

Safety: for ages 3+, adult supervision. Prints come out as one solid piece. Not for mouthing or chewing.

License: personal use. Commercial sale of prints requires a Pro Seller membership.
""")
        # web preview: seamless surface, colours cut along their contours, one colour per triangle (crisp borders)
        wv, wf, wsh, _ = read_paint(os.path.join(src, name, "preview.bin"))
        wv = taubin(wv, wf, iters=10)
        wv2, wf2, wlab = cut(wv, wf, relax(wsh, wf, 4))
        write_webmesh_fc(os.path.join(d, "preview_fc.bin"), wv2, wf2, cols[wlab])
        render([(wv2, wf2, cols[wlab], "face")], os.path.join(d, "cover.jpg"), size=720, elev=12, azim=-20)
        web = [dict(file=None, color="#" + p["hex"].lstrip("#"), name=p["colour"]) for p in meta["parts"]]
        entry = dict(slug=slug, title=title, price=float(price), blurb=BLURB[name], tags=["figure", "cute", "animal", "kids", "multicolor"],
                     line="figure", print_hint="Sculpted in Sculpt Studio. Painted OBJ/3MF (Bambu Studio maps the colours to your filaments on import), colour-split 3MF and single-colour STL; 0.12-0.16 mm layers.",
                     parts=[dict(name="body", **rep_body)], colour_parts=[dict(name=c, **reps[c]) for c, *_ in parts],
                     watertight=ok, smooth=True, web=web, preview="preview_fc.bin", preview_face=True,
                     download=f"{slug}_files.zip", cover="cover.jpg", build_seconds=0)
        json.dump(entry, open(os.path.join(d, "entry.json"), "w"), indent=1)
        print(slug, "OK" if ok else "NOT WATERTIGHT", rep_body["triangles"], "painted", rep_paint["triangles"], rep_paint["watertight"], rep_body["size_mm"], round(os.path.getsize(zp) / 1e6, 1), "MB")

if __name__ == "__main__":
    main()
