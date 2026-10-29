"""Game-ready toys: a light copy of every figure (about 8k triangles, colour per triangle) for the 3D games.
usage: python3 gen/game_assets.py site repo/public [games_dir]
- reads each figure's preview from site/products/<slug>/ (base64 .txt files of the artifact)
- writes site/products/<slug>/game.bin.txt (artifact) and repo/public/products/<slug>/game.bin (website)
- writes toys.json next to catalog.json in both places, with each toy's body colour, a front-view icon.png sticker,
  its Vietnamese name and its 2D look, so every game (2D and 3D) picks up a new model by itself
- with games_dir: also copies the toys (and covers) into games_dir/assets/ for the game artifacts
"""
import sys, os, json, gzip, struct, base64, shutil
import numpy as np


def read_webmesh(raw, face_rgb):
    raw = gzip.decompress(raw)
    nv, nf = struct.unpack("<II", raw[:8]); lo = np.frombuffer(raw, "<f4", 3, 8); hi = np.frombuffer(raw, "<f4", 3, 20)
    q = np.frombuffer(raw, "<u2", nv * 3, 32).reshape(-1, 3).astype(np.float64)
    v = lo + q / 65535.0 * (hi - lo)
    fo = 32 + nv * 6
    f = np.frombuffer(raw, "<u4", nf * 3, fo).reshape(-1, 3).astype(np.int64)
    rgb = np.frombuffer(raw, np.uint8, nf * 3, fo + nf * 12).reshape(-1, 3) if face_rgb else None
    return v, f, rgb


def cluster(v, f, rgb, target=12000):
    """Vertex-clustering simplification: snap vertices to a grid, merge, drop collapsed triangles."""
    lo, hi = v.min(0), v.max(0); size = (hi - lo).max()
    cells = 110
    while True:
        cell = size / cells
        key = np.floor((v - lo) / cell).astype(np.int64)
        uq, inv = np.unique(key, axis=0, return_inverse=True); inv = inv.reshape(-1)
        nv = np.zeros((len(uq), 3)); cnt = np.zeros(len(uq))
        np.add.at(nv, inv, v); np.add.at(cnt, inv, 1); nv /= cnt[:, None]
        nf = inv[f]
        ok = (nf[:, 0] != nf[:, 1]) & (nf[:, 1] != nf[:, 2]) & (nf[:, 0] != nf[:, 2])
        nf, ncol = nf[ok], rgb[ok]
        srt = np.sort(nf, axis=1); _, first = np.unique(srt, axis=0, return_index=True); first.sort()
        nf, ncol = nf[first], ncol[first]
        if len(nf) <= target or cells <= 30: return nv, nf, ncol
        cells = int(cells * 0.85)


def write_game_mesh(v, f, rgb):
    lo, hi = v.min(0), v.max(0)
    q = np.round((v - lo) / np.maximum(hi - lo, 1e-6) * 65535).astype("<u2")
    raw = struct.pack("<II", len(v), len(f)) + np.asarray(lo, "<f4").tobytes() + np.asarray(hi, "<f4").tobytes() + q.tobytes() + f.astype("<u4").tobytes() + np.asarray(rgb, np.uint8).tobytes()
    return gzip.compress(raw, 9)


def hexrgb(h): return [int(h[i:i + 2], 16) for i in (1, 3, 5)]


# --- what every game needs to show a toy without loading it in 3D: a body colour, a picture, a Vietnamese name, a 2D look ---
VI = {"sculpt-gingerbread": "Bánh Gừng", "sculpt-penguin": "Chim Cánh Cụt", "sculpt-kitten": "Mèo Mướp", "sculpt-frog": "Ếch Cười", "sculpt-fox": "Cáo Con",
      "sculpt-chick": "Gà Con", "sculpt-bunny": "Thỏ Tròn", "sculpt-bear": "Gấu Con", "sculpt-axolotl": "Kỳ Giông", "chibi-whale-4part": "Cá Voi"}
LOOK = {"penguin": "penguin", "kitten": "kitten", "cat": "kitten", "frog": "frog", "fox": "fox", "chick": "chick", "bunny": "bunny", "rabbit": "bunny",
        "bear": "bear", "axolotl": "axolotl", "whale": "whale"}   # 2D games paint these animals' ears, beaks and patches on their blocks


def body_colour(v, f, rgb):
    """The colour covering most of the toy (eyes and tiny details ignored), as #RRGGBB."""
    a = np.linalg.norm(np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]]), axis=1)
    key = (rgb // 24).astype(np.int64) @ np.array([10000, 100, 1])
    uq, inv = np.unique(key, return_inverse=True); area = np.zeros(len(uq)); np.add.at(area, inv, a)
    best = np.argmax(area); m = inv == best
    c = (rgb[m] * a[m, None]).sum(0) / a[m].sum()
    return "#%02X%02X%02X" % tuple(int(round(x)) for x in c)


def render_icon(v, f, rgb, size=160):
    """Front view of the toy (it faces +z), soft-lit, on a transparent background: a sticker the 2D games can draw."""
    from PIL import Image
    S = size * 2
    lo, hi = v.min(0), v.max(0); span = max(hi[0] - lo[0], hi[1] - lo[1]) * 1.08
    cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
    P = np.stack([(v[:, 0] - cx) / span * S + S / 2, (cy - v[:, 1]) / span * S + S / 2, v[:, 2]], 1)
    n = np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]]); n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    L = np.array([-0.35, 0.55, 0.76]); L /= np.linalg.norm(L)
    shade = 0.5 + 0.5 * np.clip(n @ L, 0, 1) + 0.12 * np.clip(n[:, 2], 0, 1)
    col = np.clip(rgb * shade[:, None], 0, 255)
    zb = np.full((S, S), -1e9); img = np.zeros((S, S, 4), np.uint8)
    for t in np.argsort(P[f, 2].mean(1)):
        if n[t, 2] <= 0: continue
        a, b, c = P[f[t, 0]], P[f[t, 1]], P[f[t, 2]]
        x0, x1 = int(max(0, np.floor(min(a[0], b[0], c[0])))), int(min(S - 1, np.ceil(max(a[0], b[0], c[0]))))
        y0, y1 = int(max(0, np.floor(min(a[1], b[1], c[1])))), int(min(S - 1, np.ceil(max(a[1], b[1], c[1]))))
        if x1 < x0 or y1 < y0: continue
        X, Y = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(d) < 1e-9: continue
        w0 = ((b[1] - c[1]) * (X - c[0]) + (c[0] - b[0]) * (Y - c[1])) / d
        w1 = ((c[1] - a[1]) * (X - c[0]) + (a[0] - c[0]) * (Y - c[1])) / d
        w2 = 1 - w0 - w1
        ins = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
        z = w0 * a[2] + w1 * b[2] + w2 * c[2]
        sub = zb[y0:y1 + 1, x0:x1 + 1]; m = ins & (z > sub)
        sub[m] = z[m]; img[y0:y1 + 1, x0:x1 + 1][m] = [*col[t].astype(np.uint8), 255]
    im = Image.fromarray(img, "RGBA").resize((size, size), Image.LANCZOS)
    return im


def main():
    site, web = sys.argv[1], sys.argv[2]; gdir = sys.argv[3] if len(sys.argv) > 3 else None
    cat = json.load(open(os.path.join(site, "catalog.json")))
    toys = []
    for p in cat["products"]:
        if p["line"] != "figure": continue
        d = os.path.join(site, "products", p["slug"])
        b64 = lambda path: base64.b64decode(open(os.path.join(site, path)).read())
        if p.get("preview"):
            v, f, rgb = read_webmesh(b64(p["preview"]), True)
        else:   # older figures: one mesh per colour part
            vs, fs, cs, off = [], [], [], 0
            for w in p["web"]:
                if not w.get("file"): continue
                pv, pf, _ = read_webmesh(b64(w["file"]), False)
                vs.append(pv); fs.append(pf + off); cs.append(np.tile(hexrgb(w["color"]), (len(pf), 1))); off += len(pv)
            v, f, rgb = np.concatenate(vs), np.concatenate(fs), np.concatenate(cs).astype(np.uint8)
        # print space (z up, mm) -> game space (y up), centred on x/z, standing on y = 0, 1 unit tall
        v = v[:, [0, 2, 1]] * np.array([1, 1, -1])   # same turn as the shop viewer (a proper rotation, winding unchanged)
        v -= [(v[:, 0].max() + v[:, 0].min()) / 2, v[:, 1].min(), (v[:, 2].max() + v[:, 2].min()) / 2]
        hmm = v[:, 1].max(); v /= hmm
        gv, gf, gc = cluster(v, f, rgb)
        blob = write_game_mesh(gv, gf, gc)
        open(os.path.join(d, "game.bin.txt"), "w").write(base64.b64encode(blob).decode())
        wd = os.path.join(web, "products", p["slug"]); os.makedirs(wd, exist_ok=True)
        open(os.path.join(wd, "game.bin"), "wb").write(blob)
        icon = render_icon(gv, gf, gc.astype(np.float64)); ipath = f"products/{p['slug']}/icon.png"
        icon.save(os.path.join(d, "icon.png")); icon.save(os.path.join(wd, "icon.png"))
        look = next((LOOK[k] for k in LOOK if k in p["slug"]), p.get("look2d"))
        cover = p["cover"]
        toys.append(dict(slug=p["slug"], title=p["title"], title_vi=p.get("title_vi") or VI.get(p["slug"], p["title"]), price=p["price"], dropped=p["dropped"],
                         height_mm=round(float(hmm), 1), game=f"products/{p['slug']}/game.bin", cover=cover, icon=ipath,
                         colour=body_colour(gv, gf, gc.astype(np.float64)), look=look, featured=p["slug"] == cat.get("featured")))
        if gdir:
            ad = os.path.join(gdir, "assets", "products", p["slug"]); os.makedirs(ad, exist_ok=True)
            open(os.path.join(ad, "game.bin.txt"), "w").write(base64.b64encode(blob).decode())
            shutil.copy2(os.path.join(site, cover), os.path.join(ad, "cover.jpg"))
            icon.save(os.path.join(ad, "icon.png"))
        print(p["slug"], len(f), "->", len(gf), "tris", round(len(blob) / 1024), "KB")
    toys.sort(key=lambda t: t["dropped"], reverse=True)
    man = {"updated": cat.get("updated"), "featured": cat.get("featured"), "toys": toys}
    json.dump(man, open(os.path.join(site, "toys.json"), "w"), indent=1)
    json.dump(man, open(os.path.join(web, "toys.json"), "w"), indent=1)
    if gdir:
        art = {**man, "toys": [{**t, "game": t["game"] + ".txt"} for t in toys]}
        json.dump(art, open(os.path.join(gdir, "assets", "toys.json"), "w"), indent=1)
    print("toys:", len(toys))


if __name__ == "__main__":
    main()
