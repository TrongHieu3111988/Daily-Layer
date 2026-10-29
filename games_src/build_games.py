"""Build every game page twice: an artifact copy (games/out/<id>_artifact.html) and the website copy (repo/public/games/<id>/index.html).
usage: python3 games/build_games.py  (from /home/claude)"""
import os, sys
KCSS = open("games/kit.css").read(); KJS = open("games/kit.js").read(); K3D = open("games/kit3d.js").read()
SHOP_ART = "https://claude.ai/artifact/NWvKP3j5tXF8mCmxkDrE4A"
ids = sys.argv[1:] or [f[:-5] for f in sorted(os.listdir("games")) if f.endswith(".html")]
for gid in ids:
    src = open(f"games/{gid}.html").read().replace("/*KITCSS*/", KCSS).replace("<script>/*KITJS*/</script>", "<script>\n" + KJS + "\n</script>").replace("/*KIT3D*/", K3D)
    art = src.replace("<!--HEAD-->\n", "").replace("<!--TAIL-->\n", "").replace("<script>\n" + KJS, f'<script>window.SHOP_URL = "{SHOP_ART}"; window.ASSETS = "assets/"; window.HOST = "artifact";</script>\n<script>\n' + KJS, 1)   # kit.js may start with a comment line
    open(f"games/out/{gid}_artifact.html", "w").write(art)
    title, rest = src.split("\n", 1)
    rest = rest.replace('<meta name="claude:viewport-fit-sides" content="cover">\n', "")
    rest = rest.replace("<!--HEAD-->\n", '<meta name="theme-color" content="#FFC93C">\n<link rel="manifest" href="/manifest.webmanifest">\n<link rel="icon" href="/icons/icon-192.png" type="image/png">\n<link rel="apple-touch-icon" href="/icons/apple-touch-icon.png">\n')
    rest = rest.replace("<!--TAIL-->\n", "")
    rest = rest.replace("*{box-sizing:border-box}", "body{margin:0}[hidden]{display:none!important}\n:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}\n*{box-sizing:border-box}", 1)
    rest = rest.replace('<div class="app">', '</head>\n<body>\n<div class="app">', 1)
    web = '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n' + title + "\n" + rest.rstrip() + "\n</body>\n</html>\n"
    os.makedirs(f"repo/public/games/{gid}", exist_ok=True)
    open(f"repo/public/games/{gid}/index.html", "w").write(web)
    print("built", gid)
