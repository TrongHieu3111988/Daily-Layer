"""Search pages for Daily Layer: one crawlable page per toy, meta tags on every page, sitemap + robots.

usage: python3 agent/build_seo.py [public_dir]      (default: public, run from the repo root)

Run it as the LAST step before every push (after make_cf.py / build_shop.py / build_games.py),
because those rewrite the pages this script adds tags to. Safe to run any number of times:
it rewrites toys/ and the files between <!--seo--> markers, nothing else.
"""
import html, json, pathlib, re, sys, datetime

SITE = "https://dailylayer.funny3dprint.workers.dev"
PUB = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "public")
TODAY = datetime.date.today().isoformat()
E = lambda s: html.escape(str(s), quote=True)

LINES = {"figure": "Cute figures", "print-in-place": "Moving toys", "functional": "Handy things", "decor": "Decor"}
GAMES = {  # path: (name, description) - keep in step with the `games` words in site_src/shop.html
    "games/layers": ("Magic Printer", "A real 3D toy is cut into layers like a 3D printer makes it. Tap them from the bottom up and the little printer builds it! A free browser game for kids."),
    "games/shadow": ("Whose Shadow?", "A real 3D toy turns slowly in the dark. Guess whose shadow it is and the lights come on! A free browser game for kids."),
    "games/hide": ("Hide and Seek", "Our real 3D toys are hiding in a bedroom. Spin the room and find them all! A free 3D browser game for kids."),
    "games/bowl": ("Toy Bowling", "Our 3D-printable toys stand in as pins. Swipe the ball and knock them down! A free browser game for kids."),
    "games/stack": ("Stack the Drop", "Pile today's toys into a tower before it wobbles over. A free one-tap physics game for kids, on phone or computer."),
    "games/spot": ("Spot the Oops", "Be a print detective: find what went wrong with each 3D print and learn why. A free educational game for kids."),
    "games/shelf": ("Shelf Life", "Spot the pattern on the toy shelf and find who comes next. A free Montessori-style logic game for young kids."),
    "doodle": ("Doodle Puff", "Kids draw anything and it puffs up into a squishy 3D toy you can download as a colour 3MF or STL and print at home."),
    "sculpt": ("Sculpt Studio", "Squish, pinch and paint digital clay in your browser, then download a print-ready STL or colour 3MF. Free, no sign-up."),
}
HOME_DESC = ("Free games where kids draw and sculpt their own toys, plus a new 3D-printable toy every morning. "
             "Cute figures, moving toys and handy prints as STL and 3MF files.")
CSS = """
.crumbs{font-size:14px;color:var(--muted);margin:0 0 10px}.crumbs a{color:var(--muted)}
.hero{display:grid;gap:22px}@media (min-width:720px){.hero{grid-template-columns:1fr 1fr;align-items:start}}
.hero img{width:100%;aspect-ratio:1;object-fit:cover;border-radius:18px;background:var(--sky);display:block}
.price{font-family:var(--f-display);font-weight:800;font-size:28px;margin:6px 0 14px}
.cta{display:inline-block;background:var(--accent);color:#fff;font-family:var(--f-display);font-weight:800;font-size:18px;padding:12px 20px;border-radius:16px;text-decoration:none;margin:0 8px 8px 0}
.cta.ghost{background:transparent;color:var(--ink);border:2px solid var(--line)}
dl.specs{display:grid;grid-template-columns:auto 1fr;gap:6px 16px;margin:18px 0}dl.specs dt{color:var(--muted)}dl.specs dd{margin:0}
.tags{display:flex;gap:6px;flex-wrap:wrap;margin:10px 0 0;padding:0;list-style:none}.tags li{background:var(--sky);border-radius:99px;padding:2px 10px;font-size:13.5px;margin:0}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:14px;margin-top:12px}
.card{display:block;text-decoration:none;color:var(--ink);background:var(--paper);border:1px solid var(--line);border-radius:16px;overflow:hidden}
.card img{width:100%;aspect-ratio:1;object-fit:cover;display:block;background:var(--sky)}.card span{display:block;padding:8px 10px;font-weight:700;font-size:14.5px;line-height:1.3}
.card small{display:block;padding:0 10px 10px;color:var(--muted)}
"""


def page(title, desc, path, body, image=None, ld=None, og_type="website"):
    url = f"{SITE}/{path}"
    img = f"{SITE}/{image}" if image else f"{SITE}/icons/icon-512.png"
    lds = "".join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>\n' for x in (ld or []))
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title>
<meta name="description" content="{E(desc)}">
<link rel="canonical" href="{url}">
<meta property="og:site_name" content="Daily Layer"><meta property="og:type" content="{og_type}">
<meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}">
<meta property="og:url" content="{url}"><meta property="og:image" content="{img}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/icons/icon-192.png" type="image/png">
<link rel="stylesheet" href="/legal.css"><link rel="stylesheet" href="/toys/toys.css">
{lds}</head>
<body>
<div class="wrap" style="max-width:980px">
  <div class="top"><a class="home" href="/">← Daily Layer</a><nav class="legal"><a href="/toys/">All toys</a><a href="/#play">Games</a></nav></div>
{body}
  <footer><a href="/terms/">Terms</a> · <a href="/refund/">Refunds</a> · <a href="/privacy/">Privacy</a> · <a href="/contact/">Contact</a></footer>
</div>
</body>
</html>
"""


def price_text(p):
    return "Free" if not p.get("price") else f"${p['price']:.2f}"


def card(p):
    return (f'<a class="card" href="/toys/{p["slug"]}/"><img src="/{E(p["cover"])}" alt="{E(p["title"])}, 3D printable" loading="lazy" width="300" height="300">'
            f'<span>{E(p["title"])}</span><small>{price_text(p)} · {E(LINES.get(p.get("line"), "Toy"))}</small></a>')


def toy_page(p, products):
    parts = p.get("parts") or []
    pieces = len(parts) or 1
    size = ""
    if parts and parts[0].get("size_mm"):
        dims = [max(pt["size_mm"][i] for pt in parts if pt.get("size_mm")) for i in range(3)]
        size = " × ".join(f"{d:.0f}" for d in dims) + " mm (largest part)"
    line = LINES.get(p.get("line"), "Toy")
    free = not p.get("price")
    title = f"{p['title']} – {'free ' if free else ''}3D printable {line.lower().rstrip('s')} (STL, 3MF) | Daily Layer"
    desc = f"{p['blurb']} {'Free download' if free else price_text(p) + ' one-time, or included with Maker Club'}. Print-checked STL/3MF files."
    tags = [t for t in p.get("tags", []) if isinstance(t, str)]
    related = [q for q in products if q["slug"] != p["slug"] and q.get("line") == p.get("line")][:4]
    related += [q for q in products if q["slug"] != p["slug"] and q not in related][: 4 - len(related)]
    ld = [{
        "@context": "https://schema.org", "@type": "Product", "name": p["title"], "description": p["blurb"],
        "image": f"{SITE}/{p['cover']}", "sku": p["slug"], "category": f"3D printable files > {line}",
        "brand": {"@type": "Brand", "name": "Daily Layer"},
        "offers": {"@type": "Offer", "price": f"{p.get('price') or 0:.2f}", "priceCurrency": "USD",
                   "availability": "https://schema.org/InStock", "url": f"{SITE}/toys/{p['slug']}/",
                   "itemCondition": "https://schema.org/NewCondition"},
    }, {
        "@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Daily Layer", "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": "Toys", "item": SITE + "/toys/"},
            {"@type": "ListItem", "position": 3, "name": p["title"], "item": f"{SITE}/toys/{p['slug']}/"}]}]
    cta = "Download free" if free else f"Buy {price_text(p)}"
    body = f"""  <article style="margin-top:14px">
    <p class="crumbs"><a href="/">Home</a> › <a href="/toys/">Toys</a> › {E(line)}</p>
    <div class="hero">
      <img src="/{E(p['cover'])}" alt="{E(p['title'])} 3D printed toy" width="600" height="600">
      <div>
        <h1>{E(p['title'])}</h1>
        <p class="price">{price_text(p)}</p>
        <p>{E(p['blurb'])}</p>
        <a class="cta" href="/#m-{E(p['slug'])}">{cta}</a><a class="cta ghost" href="/#m-{E(p['slug'])}">Spin it in 3D</a>
        <dl class="specs">
          <dt>Type</dt><dd>{E(line)}</dd>
          <dt>Pieces</dt><dd>{pieces}</dd>
          {f'<dt>Size</dt><dd>{size}</dd>' if size else ''}
          <dt>Files</dt><dd>STL + 3MF, print-checked (closed, 0 open edges)</dd>
          <dt>Added</dt><dd>{E(p.get('dropped', ''))}</dd>
        </dl>
      </div>
    </div>
    <h2>Print tips</h2>
    <p>{E(p.get('print_hint', 'Standard PLA settings, 0.2 mm layers.'))}</p>
    <p>Printed toys can have small parts and are not for children under 3. An adult should check each print before play.</p>
    {('<ul class="tags">' + ''.join(f'<li>{E(t)}</li>' for t in tags) + '</ul>') if tags else ''}
    <h2>Play with it</h2>
    <p>This toy also shows up in our free browser games — <a href="/games/hide/">Hide and Seek</a>, <a href="/games/bowl/">Toy Bowling</a> and <a href="/games/stack/">Stack the Drop</a>. Kids can also <a href="/sculpt/">sculpt</a> or <a href="/doodle/">draw</a> their own toy and print it.</p>
    <h2>More toys</h2>
    <div class="grid">{''.join(card(q) for q in related)}</div>
  </article>
"""
    return page(title, desc[:300], f"toys/{p['slug']}/", body, p["cover"], ld, "product")


def list_page(products):
    groups = {}
    for p in products: groups.setdefault(LINES.get(p.get("line"), "More toys"), []).append(p)
    secs = "".join(f'<h2>{E(g)}</h2><div class="grid">{"".join(card(p) for p in ps)}</div>' for g, ps in groups.items())
    nfree = sum(1 for p in products if not p.get("price"))
    body = f"""  <article style="margin-top:14px">
    <h1>3D printable toys</h1>
    <p>{len(products)} original designs made for home 3D printers — {nfree} free. Every file is print-checked and comes as STL and 3MF. A new toy is added every morning.</p>
    {secs}
  </article>
"""
    ld = [{"@context": "https://schema.org", "@type": "ItemList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "url": f"{SITE}/toys/{p['slug']}/", "name": p["title"]} for i, p in enumerate(products)]}]
    return page("3D printable toys for kids – STL & 3MF files, new every day | Daily Layer",
                f"Browse {len(products)} original 3D printable toys: cute figures, moving print-in-place toys and handy prints. STL and 3MF, {nfree} free.",
                "toys/", body, products[0]["cover"] if products else None, ld)


def tag_block(title, desc, path, image, extra_ld=None):
    url = f"{SITE}/{path}"
    out = [f'<meta name="description" content="{E(desc)}">', f'<link rel="canonical" href="{url}">',
           '<meta property="og:site_name" content="Daily Layer">', '<meta property="og:type" content="website">',
           f'<meta property="og:title" content="{E(title)}">', f'<meta property="og:description" content="{E(desc)}">',
           f'<meta property="og:url" content="{url}">', f'<meta property="og:image" content="{SITE}/{image}">',
           '<meta name="twitter:card" content="summary_large_image">']
    for x in extra_ld or []:
        out.append(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>')
    return "<!--seo-->\n" + "\n".join(out) + "\n<!--/seo-->"


def inject(file, block, title):
    s = file.read_text(encoding="utf-8")
    s = re.sub(r"<title>[^<]*</title>", f"<title>{E(title)}</title>", s, count=1)
    s = re.sub(r"<!--seo-->.*?<!--/seo-->\n?", "", s, flags=re.S)
    if 'name="description"' in s:  # page already has its own description: keep ours as the single source
        s = re.sub(r'<meta name="description" content="[^"]*">\n?', "", s)
    s = s.replace("</title>", "</title>\n" + block, 1)
    file.write_text(s, encoding="utf-8")


def main():
    cat = json.loads((PUB / "catalog.json").read_text(encoding="utf-8"))
    products = sorted(cat["products"], key=lambda p: p.get("dropped", ""), reverse=True)
    toys = PUB / "toys"; toys.mkdir(exist_ok=True)
    (toys / "toys.css").write_text(CSS.strip() + "\n", encoding="utf-8")
    keep = {p["slug"] for p in products}
    for d in toys.iterdir():  # drop pages of toys that left the catalog
        if d.is_dir() and d.name not in keep:
            for f in d.iterdir(): f.unlink()
            d.rmdir()
    for p in products:
        (toys / p["slug"]).mkdir(exist_ok=True)
        (toys / p["slug"] / "index.html").write_text(toy_page(p, products), encoding="utf-8")
    (toys / "index.html").write_text(list_page(products), encoding="utf-8")

    cover = products[0]["cover"] if products else "icons/icon-512.png"
    site_ld = [{"@context": "https://schema.org", "@type": "WebSite", "name": "Daily Layer", "url": SITE + "/"},
               {"@context": "https://schema.org", "@type": "Organization", "name": "Daily Layer", "url": SITE + "/",
                "logo": f"{SITE}/icons/icon-512.png", "email": "tronghieu3111988@gmail.com"}]
    home_t = "Daily Layer – free kids' games and 3D printable toys"
    inject(PUB / "index.html", tag_block(home_t, HOME_DESC, "", cover, site_ld), home_t)
    for path, (name, desc) in GAMES.items():
        f = PUB / path / "index.html"
        if f.exists():
            ld = [{"@context": "https://schema.org", "@type": "VideoGame", "name": name, "description": desc, "url": f"{SITE}/{path}/",
                   "genre": "Educational", "gamePlatform": "Web browser", "applicationCategory": "Game",
                   "audience": {"@type": "PeopleAudience", "suggestedMinAge": 3}, "isAccessibleForFree": True,
                   "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}}]
            t = {"sculpt": "Sculpt Studio – sculpt a 3D printable figure in your browser, free | Daily Layer",
                 "doodle": "Doodle Puff – turn a kid's drawing into a 3D printable toy, free | Daily Layer"}.get(path, f"{name} – free kids' game | Daily Layer")
            inject(f, tag_block(t, desc, f"{path}/", cover, ld), t)

    urls = [("", "daily", TODAY), ("toys/", "daily", TODAY)]
    urls += [(f"{p}/", "weekly", TODAY) for p in GAMES if (PUB / p / "index.html").exists()]
    urls += [(f"toys/{p['slug']}/", "monthly", p.get("dropped") or TODAY) for p in products]
    urls += [(f"{p}/", "yearly", None) for p in ("terms", "refund", "privacy", "contact") if (PUB / p).exists()]
    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u, freq, mod in urls:
        sm.append(f"  <url><loc>{SITE}/{u}</loc>" + (f"<lastmod>{mod}</lastmod>" if mod else "") + f"<changefreq>{freq}</changefreq></url>")
    sm.append("</urlset>")
    (PUB / "sitemap.xml").write_text("\n".join(sm) + "\n", encoding="utf-8")
    (PUB / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n", encoding="utf-8")
    print(f"seo: {len(products)} toy pages, {len(urls)} sitemap urls")


if __name__ == "__main__":
    main()
