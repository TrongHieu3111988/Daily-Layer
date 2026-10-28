# Daily Layer

Shop site for daily 3D-printable models. Static site served by Cloudflare Pages (no build step).

- `index.html` — the shop
- `catalog.json`, `journal.json` — data the page reads
- `products/<slug>/` — cover render, web preview meshes, free download zips
- `agent/` — generator code the daily agent uses (paid files are delivered by the checkout provider, not hosted here)
