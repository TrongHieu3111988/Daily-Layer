"""Assemble the shop site folder from built products.
usage: python assemble.py <out_dir> <site_dir> [--drop slug:YYYY-MM-DD ...] [--log "text" ...]
Keeps an existing catalog.json / journal.json in site_dir and merges into them.
"""
import sys, os, json, shutil, datetime

def main():
    out, site = sys.argv[1], sys.argv[2]
    args = sys.argv[3:]
    drops, logs = {}, []
    i = 0
    while i < len(args):
        if args[i] == "--drop": s, d = args[i + 1].split(":"); drops[s] = d; i += 2
        elif args[i] == "--log": logs.append(args[i + 1]); i += 2
        else: i += 1
    os.makedirs(site, exist_ok=True)
    cat_p, jr_p = os.path.join(site, "catalog.json"), os.path.join(site, "journal.json")
    cat = json.load(open(cat_p)) if os.path.exists(cat_p) else {"shop": "Daily Layer", "started": "2026-10-28", "products": [],
          "checkout": {"maker": "", "pro": "", "product_base": ""},
          "ledger": {"revenue_usd": 0.0, "orders": 0, "members": 0, "costs_usd": 0.0}}
    jr = json.load(open(jr_p)) if os.path.exists(jr_p) else {"entries": []}
    known = {p["slug"]: p for p in cat["products"]}
    for slug in sorted(os.listdir(out)):
        e_p = os.path.join(out, slug, "entry.json")
        if not os.path.exists(e_p) or (drops and slug not in drops and slug in known): continue
        e = json.load(open(e_p))
        if not e["watertight"]:
            print("skip (not watertight):", slug); continue
        dst = os.path.join(site, "products", slug); os.makedirs(dst, exist_ok=True)
        import base64
        shutil.copy2(os.path.join(out, slug, e["cover"]), os.path.join(dst, e["cover"]))
        # binaries ride as base64 text: the host serves .txt but not .zip/.bin
        for f in [e["download"]] + [w["file"] for w in e["web"] if w.get("file")] + ([e["preview"]] if e.get("preview") else []):
            open(os.path.join(dst, f + ".txt"), "w").write(base64.b64encode(open(os.path.join(out, slug, f), "rb").read()).decode())
        e["download"] += ".txt"
        for w in e["web"]:
            if w.get("file"): w["file"] += ".txt"
        base = f"products/{slug}/"
        e["cover"] = base + e["cover"]; e["download"] = base + e["download"]
        e["download_bytes"] = os.path.getsize(os.path.join(out, slug, os.path.basename(e["download"])[:-4]))
        for w in e["web"]:
            if w.get("file"): w["file"] = base + w["file"]
        if e.get("preview"): e["preview"] = base + e["preview"] + ".txt"
        e["dropped"] = drops.get(slug, known.get(slug, {}).get("dropped", cat["started"]))
        known[slug] = e
    cat["products"] = sorted(known.values(), key=lambda p: (p["dropped"], p["slug"]), reverse=True)
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7))).strftime("%Y-%m-%d %H:%M")
    for t in logs: jr["entries"].insert(0, {"at": now, "text": t})
    cat["updated"] = now
    cat.setdefault("featured", cat["products"][0]["slug"] if cat["products"] else "")
    json.dump(cat, open(cat_p, "w"), indent=1); json.dump(jr, open(jr_p, "w"), indent=1)
    print("products:", len(cat["products"]), "journal:", len(jr["entries"]))

if __name__ == "__main__":
    main()
