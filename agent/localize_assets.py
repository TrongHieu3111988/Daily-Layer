"""Self-host third-party assets so visitors' IP addresses are not sent to Google or a CDN.
Run LAST (after build_seo.py, before committing):  python3 agent/localize_assets.py public
Idempotent. Rewrites Google Fonts links and jsDelivr/cdnjs library URLs in every .html under <dir>
to the copies in <dir>/vendor/. Never adds a new external host: it fails if any remains."""
import re, sys, pathlib
root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "public")
FONT_LINK = re.compile(r'<link[^>]+href="https://fonts\.(?:googleapis|gstatic)\.com[^"]*"[^>]*>\s*')
SUBS = [
    ("https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js", "/vendor/three/build/three.module.js"),
    ("https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/", "/vendor/three/examples/jsm/"),
    ("https://cdn.jsdelivr.net/npm/cannon-es@0.20.0/dist/cannon-es.js", "/vendor/cannon-es/cannon-es.js"),
    ("https://cdnjs.cloudflare.com/ajax/libs/matter-js/0.19.0/matter.min.js", "/vendor/matter/matter.min.js"),
]
BAD = re.compile(r'https?://(?:fonts\.(?:googleapis|gstatic)\.com|cdn\.jsdelivr\.net|cdnjs\.cloudflare\.com|unpkg\.com)')
changed = bad = 0
for p in sorted(root.rglob("*.html")):
    if "vendor" in p.parts: continue
    s = o = p.read_text(encoding="utf-8")
    if FONT_LINK.search(s):
        first = True
        def rep(m):
            global first
            if "css2" in m.group(0) and first:
                first = False
                return '<link rel="stylesheet" href="/vendor/fonts/fonts.css">\n'
            return ""
        s = FONT_LINK.sub(rep, s)
        if "/vendor/fonts/fonts.css" not in s:
            s = s.replace("</head>", '<link rel="stylesheet" href="/vendor/fonts/fonts.css">\n</head>', 1)
    for a, b in SUBS: s = s.replace(a, b)
    if s != o: p.write_text(s, encoding="utf-8"); changed += 1
    if BAD.search(s): bad += 1; print("STILL EXTERNAL:", p, BAD.search(s).group(0))
print(f"localized {changed} page(s)"); sys.exit(1 if bad else 0)
