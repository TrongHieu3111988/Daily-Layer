"""Package animals sculpted with the Sculpt Studio engine into shop products (same layout as build.py output).
usage: python import_sculpt.py <sculpted_dir> <out_dir> <slug>:<name>:<title>:<price> ...
"""
import sys, os, json, zipfile, struct
import numpy as np
from forge import check, write_3mf, render
from build import write_webmesh, hex2rgb

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
}

def main():
    src, out = sys.argv[1], sys.argv[2]
    for spec in sys.argv[3:]:
        slug, name, title, price = spec.split(":")
        meta = json.load(open(os.path.join(src, name, "meta.json")))
        d = os.path.join(out, slug); os.makedirs(d, exist_ok=True)
        bv, bf = read_stl(os.path.join(src, name, "body.stl"))
        parts = []
        for p in meta["parts"]:
            v, f = read_stl(os.path.join(src, name, f"part_{p['colour']}.stl"))
            parts.append((p["colour"], v, f, p["hex"]))
        rep_body = check(bv, bf)
        reps = {c: check(v, f) for c, v, f, _ in parts}
        ok = rep_body["watertight"] and all(r["watertight"] for r in reps.values())
        write_3mf(os.path.join(d, f"{slug}_colours.3mf"), parts)
        zp = os.path.join(d, f"{slug}_files.zip")
        with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            z.write(os.path.join(src, name, "body.stl"), f"{slug}.stl")
            z.write(os.path.join(d, f"{slug}_colours.3mf"), f"{slug}_colours.3mf")
            z.writestr("README.txt", f"{title}\n\n{slug}.stl: one solid piece for single-colour printing.\n{slug}_colours.3mf: one part per colour for AMS/MMU (load as one object with multiple parts).\n\nPrint: 0.12-0.16 mm layers, 3 walls, 10-15% infill, no supports for the body; tree supports only if your slicer flags the chin.\n\nSafety: for ages 3+, adult supervision. Prints come out as one solid piece. Not for mouthing or chewing.\n\nLicense: personal use. Commercial sale of prints requires a Pro Seller membership.\n")
        web = []
        for c, v, f, hx in parts:
            fn = f"web_{c}.bin"; write_webmesh(os.path.join(d, fn), v, f); web.append(dict(file=fn, color=hx, name=c))
        render([(v, f, hex2rgb(hx)) for c, v, f, hx in parts], os.path.join(d, "cover.jpg"), size=720, elev=12, azim=-20)
        entry = dict(slug=slug, title=title, price=float(price), blurb=BLURB[name], tags=["figure", "cute", "animal", "kids", "multicolor"],
                     line="figure", print_hint="Sculpted in Sculpt Studio. Single-colour STL plus colour-split 3MF; 0.12-0.16 mm layers, no supports for most printers.",
                     parts=[dict(name="body", **rep_body)], colour_parts=[dict(name=c, **reps[c]) for c, *_ in parts],
                     watertight=ok, web=web, download=f"{slug}_files.zip", cover="cover.jpg", build_seconds=0)
        json.dump(entry, open(os.path.join(d, "entry.json"), "w"), indent=1)
        print(slug, "OK" if ok else "NOT WATERTIGHT", rep_body["triangles"], rep_body["size_mm"], round(os.path.getsize(zp) / 1e6, 1), "MB")

if __name__ == "__main__":
    main()
