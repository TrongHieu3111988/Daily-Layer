"""Build the Cloudflare (static host) copy of the shop from the claude.ai site folder.
usage: python make_cf.py <site_dir> <repo_dir> <deliverables_dir> <zip_out>
- decodes base64 .txt binaries back to real files
- keeps download zips only for free models; paid zips go to deliverables (upload them to the checkout provider)
- keeps repo_dir/index.html (the standalone page) untouched
"""
import sys, os, json, base64, shutil, zipfile

site, repo, deliv, zip_out = sys.argv[1:5]
os.makedirs(deliv, exist_ok=True)
shutil.rmtree(os.path.join(repo, "products"), ignore_errors=True)
cat = json.load(open(os.path.join(site, "catalog.json")))
for p in cat["products"]:
    for w in p["web"]:
        src = os.path.join(site, w["file"]); w["file"] = w["file"][:-4] if w["file"].endswith(".txt") else w["file"]
        dst = os.path.join(repo, w["file"]); os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, "wb").write(base64.b64decode(open(src).read()))
    if p.get("preview"):
        src = os.path.join(site, p["preview"]); p["preview"] = p["preview"][:-4] if p["preview"].endswith(".txt") else p["preview"]
        open(os.path.join(repo, p["preview"]), "wb").write(base64.b64decode(open(src).read()))
    shutil.copy2(os.path.join(site, p["cover"]), os.path.join(repo, p["cover"]))
    zsrc = os.path.join(site, p["download"]); zname = p["download"][:-4] if p["download"].endswith(".txt") else p["download"]
    data = base64.b64decode(open(zsrc).read())
    if p["price"] > 0:
        open(os.path.join(deliv, os.path.basename(zname)), "wb").write(data); p["download"] = ""
    else:
        open(os.path.join(repo, zname), "wb").write(data); p["download"] = zname
json.dump(cat, open(os.path.join(repo, "catalog.json"), "w"), indent=1)
shutil.copy2(os.path.join(site, "journal.json"), os.path.join(repo, "journal.json"))
if os.path.exists(zip_out): os.remove(zip_out)
with zipfile.ZipFile(zip_out, "w", zipfile.ZIP_DEFLATED) as z:
    for root, _, files in os.walk(repo):
        for f in files:
            full = os.path.join(root, f); rel = os.path.relpath(full, repo)
            if rel.startswith((".git", "agent")) or rel == "README.md": continue
            z.write(full, rel)
print("models:", len(cat["products"]), "zip MB:", round(os.path.getsize(zip_out) / 1e6, 1))
