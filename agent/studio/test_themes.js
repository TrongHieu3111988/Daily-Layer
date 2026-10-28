// builds every theme from a fake "child drawing": traced outline in ink, filled body, some stripes and dots
const D = require(__dirname + "/doodle_core.js"), TH = require(__dirname + "/doodle_themes.js");
const W = 512, out = {};
for (const t of TH.THEMES) {
  const { guide, keep } = TH.masks(t, W), lab = new Uint8Array(W * W);
  const dIn = D.edt(Uint8Array.from(guide, v => 1 - v), W, W);
  for (let p = 0; p < W * W; p++) if (guide[p] && !(keep && keep[p])) {
    const x = p % W, y = (p - x) / W;
    lab[p] = dIn[p] < 7 ? 1 : (Math.floor(y / 40) % 3 === 0 ? 2 : (Math.hypot((x % 50) - 25, (y % 50) - 25) < 9 ? 7 : 4));
  }
  const t0 = Date.now(), score = D.themeMatch(lab, W, W, guide, keep, 10);
  const r = D.buildTheme(lab, new Float32Array(W * W), W, W, { sizeMM: 80, fillLabel: 10, theme: TH.spec(t, W) });
  console.log(t.id, "match", score.toFixed(2), "tris", r.idx.length / 3, r.check.watertight ? "closed" : "OPEN " + r.check.badEdges, "size", r.size.map(v => v.toFixed(1)).join("x"), "base", r.base, "cols", r.used.join(","), (Date.now() - t0) + "ms");
  if (process.argv[2]) { const fs = require("fs"), d = process.argv[2] + "/th_"; fs.writeFileSync(d + t.id + ".pos", Buffer.from(r.pos.buffer)); fs.writeFileSync(d + t.id + ".idx", Buffer.from(r.idx.buffer)); fs.writeFileSync(d + t.id + ".lab", Buffer.from(r.faceLab.buffer)); }
}

