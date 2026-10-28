"""Build one or more products: print files, web preview meshes, render, and a manifest entry.
usage: python build.py <out_dir> [slug ...]
"""
import sys, os, json, time, inspect, zipfile
import numpy as np
from forge import check, write_stl, write_3mf, render
import struct, gzip

def write_webmesh(path, v, f):
    """gzip( u32 nv, u32 nf, f32 min[3], f32 max[3], u16 xyz*nv, u32 abc*nf ) -- quantized indexed mesh for the web viewer"""
    # weld duplicate vertices (STL-style meshes) before quantizing
    lo, hi = v.min(0), v.max(0)
    q = np.round((v - lo) / np.maximum(hi - lo, 1e-6) * 65535).astype(np.uint16)
    uq, inv = np.unique(q, axis=0, return_inverse=True)
    ff = inv.reshape(-1)[f].astype(np.uint32)
    raw = struct.pack('<II', len(uq), len(ff)) + np.asarray(lo, '<f4').tobytes() + np.asarray(hi, '<f4').tobytes() + uq.astype('<u2').tobytes() + ff.astype('<u4').tobytes()
    open(path, 'wb').write(gzip.compress(raw, 9))

from products import CATALOG

def hex2rgb(h): return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))

def build(slug, out):
    fn, info = CATALOG[slug]
    d = os.path.join(out, slug); os.makedirs(d, exist_ok=True)
    t0 = time.time()
    res = fn()
    pp = res.get("print_parts", res["parts"])
    reports = {}
    for name, v, f, c in pp:
        reports[name] = check(v, f)
        write_stl(os.path.join(d, f"{slug}_{name}.stl"), v, f, name)
    write_3mf(os.path.join(d, f"{slug}.3mf"), pp)
    with zipfile.ZipFile(os.path.join(d, f"{slug}_files.zip"), "w", zipfile.ZIP_DEFLATED) as z:
        for name, *_ in pp: z.write(os.path.join(d, f"{slug}_{name}.stl"), f"{slug}_{name}.stl")
        z.write(os.path.join(d, f"{slug}.3mf"), f"{slug}.3mf")
        z.writestr("README.txt", f"{info['title']}\n\nPrint tips: {res['meta']['print_hint']}\n\nLicense: personal use. Commercial sale of prints requires a Pro membership.\n")
    # lighter preview mesh for the web viewer and render
    if "step" in inspect.signature(fn).parameters:
        step = inspect.signature(fn).parameters["step"].default
        prev = fn(step=step * 1.6)
    else:
        prev = res
    web = []
    for name, v, f, c in prev["parts"]:
        fn_ = f"web_{name}.bin"; write_webmesh(os.path.join(d, fn_), v, f)
        web.append(dict(file=fn_, color=c, name=name))
    render([(v, f, hex2rgb(c)) for _, v, f, c in prev["parts"]], os.path.join(d, "cover.jpg"), size=720, **dict(zip(("elev","azim"), res["meta"].get("view",(28,-55)))))
    allok = all(r["watertight"] for r in reports.values())
    entry = dict(slug=slug, **info, line=res["meta"]["line"], print_hint=res["meta"]["print_hint"],
                 parts=[dict(name=k, **r) for k, r in reports.items()], watertight=allok,
                 web=web, download=f"{slug}_files.zip", cover="cover.jpg",
                 build_seconds=round(time.time() - t0, 1))
    json.dump(entry, open(os.path.join(d, "entry.json"), "w"), indent=1)
    return entry

if __name__ == "__main__":
    out = sys.argv[1]; slugs = sys.argv[2:] or list(CATALOG)
    for s in slugs:
        e = build(s, out)
        print(s, "OK" if e["watertight"] else "NOT WATERTIGHT", e["build_seconds"], "s",
              [(p["name"], p["triangles"], p["shells"], p["size_mm"], p["volume_cm3"]) for p in e["parts"]], flush=True)
