# Daily Layer — daily drop runbook

## Order of work (the owner's rule, 2026-10-29)
1. **Research first**: what can sell now and in the next 2–6 weeks (agent/RESEARCH.md + fresh searches with numbers).
2. **Then the print file**: build that model, checked and assembled.
3. **Then games that reuse the model library**: the library is `toys.json` (every figure the shop made, with its 3D game mesh, cover, icon sticker, body colour, Vietnamese name and 2D look, written by `gen/game_assets.py`). Every game, old and new, reads it at start, so a new model appears in every game by itself.
4. **Old games get every new model**: after a new figure, run `gen/game_assets.py`, then publish the new toy's assets to every game in `games/GAMES.json` with `library` set (2D games: `assets/toys.json` and `assets/products/<slug>/icon.png`; 3D games: also `game.bin.txt` and `cover.jpg`). The website needs nothing extra: `make_cf.py` copies the files.
5. **A new game never hard-codes toys**: it loads `toys.json` (`loadToyList()` in 3D, `K.library()` in 2D; names with `K.toyName(t)` / `t.title_vi`). Only if a new game truly needs a kind of model the library lacks (for example a train car or a board piece) is a new print model made for it, and that model goes through steps 1–2 like any other (sellable, checked, in the shop). Add the game to `games/GAMES.json`.
6. A new figure that is a known animal gets a 2D look automatically (LOOK map in `gen/game_assets.py`); add an entry or a `look2d` in its catalog record when you invent a new animal kind, and a `title_vi` for its Vietnamese name. Without a look, the 2D games show the toy's own icon on the block, which is fine.

Shop artifact: https://claude.ai/artifact/NWvKP3j5tXF8mCmxkDrE4A
The shop's generator code lives inside the artifact under `agent/` as `.txt` files (the host only serves text types).

## 1. Restore the workspace
- `Artifact` action `read` on the shop URL (no path) to get the page; the result names the saved file holding the full page. Copy it to `site/index.html`.
- `Artifact` action `read` with `paths`: `catalog.json`, `journal.json`, `agent/forge.py.txt`, `agent/revolve.py.txt`, `agent/products.py.txt`, `agent/products2.py.txt`, `agent/build.py.txt`, `agent/assemble.py.txt`, `agent/make_cf.py.txt`.
- Put `catalog.json` and `journal.json` in `site/`. Put the `.py.txt` files in `gen/` with the `.txt` dropped.
- Tools available in the cloud workspace without installs: numpy, scikit-image, scipy, Pillow. Package registries and Blender downloads are blocked, so build with `forge.py` (implicit shapes + marching cubes) and `revolve.py` (lathe profiles).

## Page source
- Both shop pages are generated from one source: `agent/shop_src.html.txt` (save as `site_src/shop.html`) and `agent/build_shop.py.txt` (save as `site_src/build_shop.py`). Run `python3 site_src/build_shop.py` from the workspace root after cloning the repo; it writes `site/index.html` (this artifact) and `repo/public/index.html` (the website). Never hand-edit either output.
- The daily drop does not need to touch the page: it reads `catalog.json` and `journal.json`.

## 2. Research, then pick today's model
- Before designing, run 3–5 web searches for current demand: what is selling or trending for 3D-print files right now (Etsy STL listings and review counts, MakerWorld/Printables trending, search-trend data, upcoming holidays and seasons in the next 2–6 weeks). Prefer evidence with numbers over listicles.
- Choose the idea with the clearest demand signal that `forge.py`/`revolve.py` can build well. Seasonal items go first when their season is 2–6 weeks away (Halloween, Christmas, Valentine's, Easter, Mother's Day, back-to-school).
- Keep a rough balance across lines (functional, print-in-place, decor, figure) over each week, but demand evidence wins over rotation.
- Never repeat an existing slug or a near-duplicate idea. No trademarked characters, logos or brand names ("Gridfinity-compatible" is fine; the standard is open).
- Write the evidence in one sentence in the journal entry (source and number).
- Write a recipe function in `gen/products2.py` and register it in `CATALOG2` with title, price (0 for about one in five drops, otherwise 0.99–3.99 USD), a one-sentence blurb, and tags.
- Figures (cute animals, characters of our own invention): sculpt them with the Sculpt Studio engine, the same one the public app uses. Read `agent/sculpt_core.js.txt`, `agent/sculpt_core2.js.txt` and `agent/sculpt_animals2.js.txt` (save as `studio/core.js`, `studio/core2.js`, `studio/animals2.js`; v2 = 160-cubed clay with the app's ZBrush-style brushes), add a new function to `ANIMALS` and a base colour to `BASE`, run `node studio/animals2.js sculpted <name>`, then `python3 gen/import_sculpt.py sculpted out <slug>:<name>:<Title>:<price>` (copy `agent/import_sculpt.py.txt` and `agent/paint.py.txt` to `gen/` without the `.txt`, and add a blurb for the new name; it cuts the colour borders exactly and packs a painted OBJ/3MF that Bambu Studio maps to filaments on import). Kid-safe: one solid piece, no detachable parts, nothing under ~3 cm for toddlers.
- Design rules for FDM on a Bambu Lab P1S: flat base on the bed, overhangs ≤ 50°, walls ≥ 1.6 mm, print-in-place clearance 0.5–0.6 mm, press-fit clearance 0.2–0.3 mm, figures split by colour with pegs or pin holes, everything within 250 × 250 × 250 mm.

## 3. Build and check
- `cd gen && python3 build.py ../out <slug>`
- Every part must report `watertight: true`, `bad_edges: 0`, and one shell per part. Print-in-place designs set `expect_shells` in the recipe result and the build fails if any joint fused.
- Zips over ~11 MB will not fit the host's 16 MB text limit after base64; raise the mesh step slightly if needed.
- Open `out/<slug>/cover.jpg` with Read and judge it as a buyer would. Fix and rebuild if it looks wrong; at most three attempts.
- If it still fails after three attempts, publish nothing new except a journal entry that says what failed.

## 4. Assemble
- `python3 gen/assemble.py out site --drop <slug>:<YYYY-MM-DD> --log "<what was made, why, and what the checks said>"`
- Set `featured` in `site/catalog.json` to the new slug.

## 5. Publish (same URL)
- `Artifact` publish with `url` = the shop URL, `file_path` = `site/index.html`, `root` = `site`, and `files` listing ONLY: `catalog.json`, `journal.json`, `agent/products2.py.txt` (copy of the updated `gen/products2.py`), and the new `products/<slug>/...` files. Files left out stay as they are.
- Do not pass `capabilities` or `icon`.
- If the publish is refused for size, stop adding products and add a journal entry saying storage is full.

## 6. Push to GitHub (Cloudflare deploys from it)
- The public shop https://dailylayer.funny3dprint.workers.dev is served by Cloudflare from the GitHub repo `TrongHieu3111988/Daily-Layer`, branch `main`. Cloudflare cannot be reached from the workspace; GitHub can.
- Call the `add_repo` tool with owner `TrongHieu3111988`, repo `Daily-Layer`, access `push`, then `git clone --depth 1 https://github.com/TrongHieu3111988/Daily-Layer repo` (generous timeout).
- The deployed site lives in `repo/public/` (Cloudflare serves only that folder; `repo/agent/` holds code). Run `python3 gen/make_cf.py site repo/public deliverables /tmp/cf.zip` — rebuilds `repo/public/products`, `catalog.json`, `journal.json` from `site/` (paid zips go to `deliverables/`, never into the repo) and keeps `repo/public/index.html` and `repo/public/sculpt/` as they are.
- After pushing, confirm the build: `gh api repos/TrongHieu3111988/Daily-Layer/commits/<sha>/check-runs` until the "Workers Builds: dailylayer" run is `completed`; report `success` or `failure`.
- Copy `gen/*.py` into `repo/agent/`, then commit as "Daily drop <YYYY-MM-DD>: <title>" and `git push origin main`.
- If the push is refused, say so in the report; the claude.ai shop is still updated.

## 3D games: keep them stocked (every run that adds a figure)
- `gen/game_assets.py` makes a light game copy of every figure (about 10k triangles, colour per triangle) and `toys.json`. Run it right after step 4: `python3 gen/game_assets.py site /tmp/webtoys games` (copy `agent/game_assets.py.txt` to `gen/game_assets.py`). It writes `site/products/<slug>/game.bin.txt`, `site/toys.json` and `games/assets/...`; `make_cf.py` later copies them into the website.
- Publish `toys.json` and the new `products/<slug>/game.bin.txt` with the shop files in step 5.
- The two 3D game artifacts carry their own copy of the toys. Publish the new toy to both: `Artifact` publish with `url` = https://claude.ai/artifact/Q3idBaN6tiht1SzcC2wrVK (Hide and Seek), `file_path` = `games/out/hide_artifact.html`, `files` = `{"assets/toys.json": "games/assets/toys.json", "assets/products/<slug>/game.bin.txt": "games/assets/products/<slug>/game.bin.txt", "assets/products/<slug>/cover.jpg": "games/assets/products/<slug>/cover.jpg"}`; the same for https://claude.ai/artifact/8wVbSSvujjEp4qp44eUKoa (Toy Bowling) with `games/out/bowl_artifact.html`. Read each artifact first if the tool asks.

## 8. One new game every day
- Restore the game sources: `agent/games_kit.css.txt`, `agent/games_kit.js.txt`, `agent/games_kit3d.js.txt`, `agent/games_build_games.py.txt`, `agent/games_BACKLOG.md.txt` and every `agent/games_<id>.html.txt` (save them in `games/` without the `games_` prefix and `.txt`). Restore `agent/shop_src.html.txt` -> `site_src/shop.html` and `agent/build_shop.py.txt` -> `site_src/build_shop.py`.
- Take the first unchecked line of `games/BACKLOG.md`. Build it as one page `games/<id>.html` following the existing games (stack, spot, shelf for 2D; hide, bowl for 3D with the real toys): same bar (back, title, score, sound, language), intro card, end card with stars, `K.words.en` and `K.words.vi`, `K.sfx` sounds, `K.confetti`. Libraries only from the import map already used (three@0.160.0, cannon-es@0.20.0) or cdnjs.
- Rules: playable by a 4-year-old with one finger; no fail screens that scold; original drawings only (no known characters); no ads, no text input, no network calls except the page's own files and the pinned libraries; respect reduced motion.
- Test before shipping: clone `https://github.com/mrdoob/three.js` at tag r160 (sparse: build, examples/jsm) and `https://github.com/pmndrs/cannon-es` (dist) into /tmp, serve `repo/public` with `python3 -m http.server`, open the page in Playwright (Chromium with `--use-gl=swiftshader`), route the CDN URLs to the local copies, play it with scripted taps, and require zero page errors. Look at a phone-size screenshot (400×820) and fix what looks wrong; at most three rounds.
- Ship: `python3 games/build_games.py <id>`; publish `games/out/<id>_artifact.html` as a NEW artifact (3D games also pass `files` with `assets/toys.json` and every toy's `game.bin.txt` and `cover.jpg`, as in the section above); add its URL to `TOOLS` in `site_src/build_shop.py`; add the tile in `site_src/shop.html` (`GAMES` entry with `isNew: true` — remove `isNew` from older tiles — an `ART` drawing, and the name + one-line description in both `games` word lists; add the web path to the default `TOOLS`); run `python3 site_src/build_shop.py`; publish the shop artifact again (`site/index.html`) plus the updated `agent/` sources (games files, shop source, BACKLOG with the line checked); copy `games/*.html games/kit* games/build_games.py games/BACKLOG.md` into `repo/games_src/` and `site_src/*` into `repo/site_src/`; commit and push with the daily drop.
- If the game still fails its test after three rounds, ship nothing for games today and say so in the journal and the report.

## 7. Report
- Send the owner a short message in Vietnamese: the new model, its line and price, the demand evidence, the check result, today's new game (or why there is none), whether the GitHub push (Cloudflare) succeeded, and the links (shop, today's game on the website and its artifact): https://dailylayer.funny3dprint.workers.dev and https://claude.ai/artifact/NWvKP3j5tXF8mCmxkDrE4A

## Doodle Puff 3D objects (themes)
- `studio/doodle_themes.js` lists the objects a child can trace (cup, balloon, tree, pine, ice cream, mushroom, snowman, rocket, vase). Each is a side-view profile `r(y)` on the 512 px paper, plus optional parts (cup handle) and a `keep` hole.
- `Doodle.buildTheme` spins the child's own outline into a round object, wraps their colours around it, drops the outline crayon, hollows cups and vases, and adds a round foot when the bottom is thin.
- A new theme can join the daily drop: add it to the list, run `node agent/studio/test_themes.js` (every theme must say `closed`), rebuild with `python3 build_doodle.py`, try it in the page. Keep shapes that stand on their own and print as one piece. Cups and vases are toys or pen pots, never food containers.
