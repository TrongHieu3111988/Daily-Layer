// Records a game as a vertical 1080x1920 clip, frame by frame on a fake clock (smooth 30 fps whatever the machine speed).
// usage: node capture.js <game id> <out frames dir> [seconds cap]
// Each game has a small "director" below: what to tap and when. A new game adds its own director.
const { chromium } = require("playwright"); const { spawn } = require("child_process"); const fs = require("fs"), path = require("path");
const [gid, outDir] = process.argv.slice(2), FPS = 30, DT = 1000 / FPS;
const PUBLIC = process.env.PUBLIC || "/home/claude/repo/public", FONTS = path.join(__dirname, "fonts");
const FONT_CSS = `@font-face{font-family:"Baloo 2";font-weight:400 800;src:url(/__fonts/Baloo2.ttf)}@font-face{font-family:"Nunito";font-weight:200 1000;src:url(/__fonts/Nunito.ttf)}`;

const DIRECTORS = {
  // Hide and Seek: turn towards each hidden toy, tap it, then show the collection
  async hide(s) {
    await s.waitFor(() => window.__game && window.__game.hidden().length > 0);
    await s.page.evaluate(() => { window.__spot = k => {
        const G = __game, T = G.THREE, h = G.hidden()[k], p = h.mesh.position.clone(); p.y += h.mesh.scale.x * 0.45;
        let root = h.mesh; while (root.parent) root = root.parent; root.updateMatrixWorld(true);   // a fresh room has not been rendered yet
        const base = Math.atan2(-p.x, -p.z), ray = new T.Raycaster(), cam = G.cam, keep = cam.position.clone(), tg = G.controls.target, cands = [];
        for (let i = 0; i < 24; i++) for (const pol of [1.25, 1.05, 0.85]) for (const dist of [4.5, 3.5, 2.5]) {
          let da = i * Math.PI / 12; if (da > Math.PI) da -= 2 * Math.PI; cands.push({ da, pol, dist, cost: Math.abs(da) + (4.5 - dist) * 0.05 + Math.abs(pol - 1.05) * 0.2 }); }
        cands.sort((x, y) => x.cost - y.cost); let pick = null;
        for (const c of cands) {
          const a = base + c.da, r = Math.sin(c.pol) * c.dist, y = tg.y + Math.cos(c.pol) * c.dist;
          cam.position.set(Math.sin(a) * r, y, Math.cos(a) * r); cam.lookAt(tg); cam.updateMatrixWorld();
          const v = p.clone().project(cam); if (Math.abs(v.x) > 0.55 || v.y < -0.4 || v.y > 0.45) continue;   // clear of the panels and buttons
          ray.setFromCamera(new T.Vector2(v.x, v.y), cam);
          const hit = ray.intersectObjects([...G.solids(), h.mesh], false)[0];
          if (hit && hit.object === h.mesh) { pick = { a, r, y }; break; }
        }
        cam.position.copy(keep); cam.lookAt(tg); cam.updateMatrixWorld(); return pick; }; });
    for (let tries = 0; tries < 8; tries++) {
      for (let f = 0; f < 4; f++) { await s.page.clock.runFor(DT); await s.page.evaluate(() => __flushRAF()); }   // let the new room render once
      const ok = await s.page.evaluate(() => __game.hidden().every((_, k) => __spot(k)));
      if (ok) break; await s.page.evaluate(() => __game.newRoom()); await s.waitFor(() => __game.hidden().length > 0);
    }
    await s.hold(20); await s.tap("#startBtn"); await s.hold(15);
    const n = await s.page.evaluate(() => window.__game.hidden().length);
    for (let k = 0; k < n; k++) {
      const best = await s.page.evaluate(k => __spot(k), k);
      console.log("toy", k, best ? "visible" : "hidden everywhere"); if (!best) continue;
      const from = await s.page.evaluate(() => { const c = __game.cam.position; return { a: Math.atan2(c.x, c.z), r: Math.hypot(c.x, c.z), y: c.y }; });
      let d = best.a - from.a; while (d > Math.PI) d -= 2 * Math.PI; while (d < -Math.PI) d += 2 * Math.PI;
      for (let f = 1; f <= 36; f++) { const e = 0.5 - 0.5 * Math.cos(Math.PI * f / 36), a = from.a + d * e, r = from.r + (best.r - from.r) * e, y = from.y + (best.y - from.y) * e;
        await s.page.evaluate(([a, r, y]) => { __game.cam.position.set(Math.sin(a) * r, y, Math.cos(a) * r); __game.controls.update(); }, [a, r, y]); await s.frame(); }
      await s.hold(8);
      const pt = await s.page.evaluate(k => { const h = __game.hidden()[k], v = h.mesh.position.clone(); v.y += h.mesh.scale.x * 0.45; v.project(__game.cam); return [v.x, v.y]; }, k);
      const before = await s.page.evaluate(() => __game.found());
      await s.tapAt(pt); await s.frame();
      const got = await s.page.evaluate(() => __game.found()) > before; console.log("tap", k, pt.map(v => v.toFixed(2)).join(","), got); if (got) s.mark(await s.page.evaluate(() => __game.found() === __game.hidden().length) ? "allfound" : "found");
      await s.hold(32);
    }
    await s.hold(45);
  },
  // Toy Memory: one wrong guess (it just flips back), then every twin in rounds 1 and 2. CSS flips are stepped by hand so they follow the fake clock.
  async memory(s) {
    const fr = async () => { await s.page.evaluate(dt => { for (const a of document.getAnimations()) { if (a.playState === "finished") continue; a.pause(); const end = a.effect.getComputedTiming().endTime; a.currentTime = Math.min((a.currentTime || 0) + dt, end); if (a.currentTime >= end) a.finish(); } }, DT); await s.frame(); };
    const hold = async k => { for (let i = 0; i < k; i++) await fr(); };
    const click = async i => { await s.tap(`.cardx:nth-child(${i + 1})`); await hold(16); };
    await hold(20); await s.tap("#startBtn"); await hold(30);
    for (let r = 0; r < 2; r++) {
      const keys = await s.page.evaluate(() => cards.map(c => c.item.key)), n = keys.length;
      if (r === 0) { const b = keys.findIndex((v, k) => k && v !== keys[0]); await click(0); await click(b); await hold(36); }
      const done = new Set();
      for (let i = 0; i < n; i++) { if (done.has(i)) continue; const j = keys.findIndex((v, k) => k !== i && v === keys[i]);
        await click(i); await click(j); done.add(i); done.add(j); s.mark("match"); await hold(26); }
      if (r === 0) { s.mark("next"); await s.waitFor(() => cards.length === 8 && !cards.some(c => c.done), 200); await hold(30); }
    }
    s.mark("allfound"); await hold(60);
  },
  // Stack the Drop: drop friends when the crane is over the table
  async stack(s) {
    await s.hold(20); await s.tap("#startBtn"); await s.hold(20);
    for (let i = 0; i < 9; i++) { for (let t = 0; t < 60; t++) { const ok = await s.page.evaluate(() => Math.abs(Math.sin(window.__swing ?? 0)) < 0.12); if (ok && t > 18) break; await s.frame(); } await s.tapAt([0, -0.2]); await s.hold(28); }
    await s.hold(30);
  }
};

(async () => {
  fs.mkdirSync(outDir, { recursive: true }); for (const f of fs.readdirSync(outDir)) fs.unlinkSync(path.join(outDir, f));
  const port = 8800 + Math.floor(Math.random() * 100), srv = spawn("python3", ["-m", "http.server", String(port)], { cwd: PUBLIC, stdio: "ignore" });
  await new Promise(r => setTimeout(r, 900));
  const b = await chromium.launch({ args: ["--use-gl=swiftshader", "--enable-webgl", "--ignore-gpu-blocklist"] });
  const ctx = await b.newContext({ viewport: { width: 432, height: 768 }, deviceScaleFactor: +(process.env.DPR || 1.25), locale: "en-US", serviceWorkers: "block", hasTouch: false });
  const page = await ctx.newPage(); const errs = []; page.on("pageerror", e => errs.push(e.message));
  await page.route("**/*", r => { const u = r.request().url();
    if (u.startsWith("https://cdn.jsdelivr.net/npm/three@0.160.0/")) return r.fulfill({ path: "/tmp/three-src/" + u.split("three@0.160.0/")[1], contentType: "text/javascript" });
    if (u.includes("cannon-es")) return r.fulfill({ path: "/tmp/cannon/dist/cannon-es.js", contentType: "text/javascript" });
    if (u.includes("matter")) return r.fulfill({ path: "/tmp/matter/build/matter.min.js", contentType: "text/javascript" });
    if (u.startsWith("https://fonts.googleapis.com/")) return r.fulfill({ body: FONT_CSS, contentType: "text/css" });
    if (u.includes("/__fonts/")) return r.fulfill({ path: path.join(FONTS, u.split("/__fonts/")[1]), contentType: "font/ttf" });
    return u.startsWith("http://localhost") ? r.continue() : r.abort(); });
  await page.clock.install();
  // one animation frame per video frame: the page's requestAnimationFrame callbacks run only when the recorder says so
  await page.addInitScript(() => { let q = []; window.requestAnimationFrame = cb => { q.push(cb); return q.length; }; window.cancelAnimationFrame = () => {};
    window.__flushRAF = () => { const run = q; q = []; const t = performance.now(); for (const cb of run) try { cb(t); } catch (e) { console.error(e); } }; });
  await page.goto(`http://localhost:${port}/games/${gid}/`, { waitUntil: "load" });
  let n = 0; const T0 = Date.now();
  const marks = [];
  const s = {
    page, mark(label) { marks.push([n, label]); },
    async frame() { await page.clock.runFor(DT); await page.evaluate(() => window.__flushRAF && window.__flushRAF()); await page.screenshot({ path: path.join(outDir, String(n++).padStart(5, "0") + ".jpg"), type: "jpeg", quality: 92 }); if (n % 30 === 0) console.log("frame", n, ((Date.now() - T0) / n / 1000).toFixed(2) + " s/frame"); },
    async hold(k) { for (let i = 0; i < k; i++) await s.frame(); },
    async waitFor(fn, max = 400) { for (let i = 0; i < max; i++) { if (await page.evaluate(fn).catch(() => false)) return; await page.clock.runFor(DT); await page.evaluate(() => window.__flushRAF && window.__flushRAF()); await page.waitForTimeout(40); } },
    async tap(sel) { const bb = await (await page.$(sel)).boundingBox(); await page.mouse.click(bb.x + bb.width / 2, bb.y + bb.height / 2); },
    async tapAt([x, y], sel = "canvas") { const bb = await (await page.$(sel)).boundingBox(); await page.mouse.click(bb.x + (x + 1) / 2 * bb.width, bb.y + (1 - y) / 2 * bb.height); }
  };
  await DIRECTORS[gid](s);
  fs.writeFileSync(path.join(outDir, "marks.json"), JSON.stringify(marks));
  console.log(gid, "frames", n, "marks", marks.length, "errors", errs);
  await b.close(); srv.kill();
})();
