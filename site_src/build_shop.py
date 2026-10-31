"""Build both copies of the shop page from site_src/shop.html.
site/index.html          -> the claude.ai artifact (tools open as artifacts, files are base64 .txt)
repo/public/index.html   -> the public website on Cloudflare (real files, installable as an app)
usage: python3 site_src/build_shop.py  (run from /home/claude)"""
import os
src = open("site_src/shop.html").read()
ART = '<script>window.HOST = "artifact"; window.TOOLS = { doodle: "https://claude.ai/artifact/KE3s6dFJQW2m9saZy9Gam3", sculpt: "https://claude.ai/artifact/AuyWaB1MFswxLQc6Uzyces", stack: "https://claude.ai/artifact/5ELRqRw3UhEdrhw7jZgH1z", spot: "https://claude.ai/artifact/JbcssAnpkXChMTvtktXmkv", shelf: "https://claude.ai/artifact/HBKDhzdkkK5bUefDzYffwf", hide: "https://claude.ai/artifact/Q3idBaN6tiht1SzcC2wrVK", bowl: "https://claude.ai/artifact/8wVbSSvujjEp4qp44eUKoa", shadow: "https://claude.ai/artifact/A2WdpL6ztBRyJCbU2moABm", layers: "https://claude.ai/artifact/K7SEug6s3i7K8mHbqgXyoF", memory: "https://claude.ai/artifact/NjiQ1yupYs4tUvQXJ44b9h" };</script>\n'
art = src.replace("<!--HEAD-->\n", "").replace("<!--TAIL-->\n", "").replace("<script>\n/* ---------- words ---------- */", ART + "<script>\n/* ---------- words ---------- */", 1)
open("site/index.html", "w").write(art)

WEB_HEAD = """<meta name="description" content="A playground where kids draw and sculpt their own toys, and grown-ups print them at home on a 3D printer. A new printable toy every morning.">
<meta name="theme-color" content="#FFC93C">
<link rel="manifest" href="/manifest.webmanifest">
<link rel="icon" href="/icons/icon-192.png" type="image/png">
<link rel="apple-touch-icon" href="/icons/apple-touch-icon.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Daily Layer">
"""
WEB_TAIL = """<script>
if ("serviceWorker" in navigator) addEventListener("load", () => navigator.serviceWorker.register("/sw.js").catch(() => {}));
</script>
"""
title, rest = src.split("\n", 1)
rest = rest.replace('<meta name="claude:viewport-fit-sides" content="cover">\n', "")
rest = rest.replace("<!--HEAD-->\n", WEB_HEAD).replace("<!--TAIL-->\n", WEB_TAIL)
rest = rest.replace("<script>\n/* ---------- words ---------- */", '<script>window.HOST = "web";</script>\n<script>\n/* ---------- words ---------- */', 1)
rest = rest.replace("*{box-sizing:border-box}", "html{color-scheme:light dark}body{margin:0}img{max-width:100%}[hidden]{display:none!important}\n:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}\n*{box-sizing:border-box}", 1)
rest = rest.replace('<svg width="0" height="0" style="position:absolute" aria-hidden="true">', '</head>\n<body>\n<svg width="0" height="0" style="position:absolute" aria-hidden="true">', 1)
web = '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n' + title + "\n" + rest.rstrip() + "\n</body>\n</html>\n"
open("repo/public/index.html", "w").write(web)
print("built", len(art), len(web))
