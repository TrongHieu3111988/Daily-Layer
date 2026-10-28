// Sculpt original cute animals with the Sculpt Studio engine (same brushes as the app), then export print files.
// usage: node animals.js <outdir> [name ...]
const S = require("./core.js");
const fs = require("fs"), path = require("path");

const COL = { cream: "#F4E9D4", yellow: "#FFD24C", orange: "#FF9B3D", pink: "#F7A1B5", ink: "#24283A", white: "#FBFBF8",
              brown: "#A86B45", tan: "#E2C29B", black: "#2E3140", sky: "#7CC3F0", green: "#7AC77F" };
const NAMES = Object.keys(COL);
const L = n => NAMES.indexOf(n);

function Studio(N, base) { const s = new S(N); s.f.fill(s.clamp); s.c.fill(L(base)); return s; }
function ball(s, p, r, col, k) { s.dab("add", p, r, L(col), 1); }
function line(s, a, b, r0, r1, col, steps) {
  steps = steps || 12;
  for (let i = 0; i <= steps; i++) {
    const t = i / steps;
    s.dab("add", [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t], r0 + (r1 - r0) * t, L(col), 1);
  }
}
function paint(s, p, r, col) { s.dab("paint", p, r, L(col), 1); }
function mirror(fn) { fn(1); fn(-1); }
function eye(s, x, y, z, r) {               // glossy dot eye: ink ball with a tiny white highlight
  ball(s, [x, y, z], r, "ink");
  ball(s, [x + 0.25 * r * Math.sign(x || 1), y + 0.35 * r, z + 0.7 * r], r * 0.28, "white");
}

const BASE = { chick: "yellow", bunny: "cream", bear: "brown", penguin: "black" };
const ANIMALS = {
  chick(s) {
    ball(s, [0, -0.28, 0], 0.42, "yellow");                 // body
    ball(s, [0, 0.12, 0.02], 0.34, "yellow");               // head
    mirror(sx => line(s, [0.36 * sx, -0.25, 0.0], [0.44 * sx, -0.3, -0.08], 0.12, 0.07, "yellow", 8)); // wings
    line(s, [0, 0.42, 0.0], [0.04, 0.52, -0.04], 0.06, 0.03, "yellow", 6);   // tuft
    line(s, [-0.04, 0.44, 0.02], [-0.1, 0.5, 0.0], 0.05, 0.025, "yellow", 6);
    line(s, [0, 0.07, 0.3], [0, 0.04, 0.42], 0.075, 0.03, "orange", 8);      // beak
    mirror(sx => eye(s, 0.13 * sx, 0.17, 0.29, 0.045));
    mirror(sx => paint(s, [0.22 * sx, 0.04, 0.26], 0.06, "pink"));          // cheeks
    mirror(sx => line(s, [0.12 * sx, -0.66, 0.22], [0.16 * sx, -0.68, 0.34], 0.06, 0.045, "orange", 6)); // feet
  },
  bunny(s) {
    ball(s, [0, -0.32, 0], 0.4, "cream");
    ball(s, [0, 0.06, 0.03], 0.32, "cream");
    mirror(sx => {
      line(s, [0.12 * sx, 0.3, -0.02], [0.2 * sx, 0.72, -0.08], 0.09, 0.075, "cream", 16);   // ears
      for (let t = 0.15; t <= 0.85; t += 0.1)                                                // inner ear
        paint(s, [0.12 * sx + 0.08 * sx * t, 0.3 + 0.42 * t, -0.02 - 0.06 * t + 0.07], 0.045, "pink");
    });
    mirror(sx => eye(s, 0.12 * sx, 0.1, 0.29, 0.042));
    ball(s, [0, 0.0, 0.33], 0.035, "pink");                                                    // nose
    mirror(sx => paint(s, [0.2 * sx, -0.02, 0.26], 0.055, "pink"));
    mirror(sx => line(s, [0.18 * sx, -0.62, 0.2], [0.2 * sx, -0.64, 0.3], 0.09, 0.08, "cream", 6)); // feet
    ball(s, [0, -0.35, -0.4], 0.11, "white");                                                   // tail
    paint(s, [0, -0.3, 0.36], 0.18, "white");                                                    // belly
  },
  bear(s) {
    ball(s, [0, -0.3, 0], 0.42, "brown");
    ball(s, [0, 0.12, 0.02], 0.34, "brown");
    mirror(sx => { ball(s, [0.27 * sx, 0.38, -0.02], 0.11, "brown"); paint(s, [0.28 * sx, 0.39, 0.08], 0.06, "tan"); }); // ears
    ball(s, [0, 0.04, 0.27], 0.13, "tan");                                                      // muzzle
    ball(s, [0, 0.1, 0.39], 0.045, "ink");                                                      // nose
    mirror(sx => eye(s, 0.13 * sx, 0.2, 0.28, 0.04));
    paint(s, [0, -0.32, 0.38], 0.22, "tan");                                                    // belly
    mirror(sx => line(s, [0.3 * sx, -0.22, 0.12], [0.24 * sx, -0.36, 0.3], 0.1, 0.085, "brown", 8));  // arms
    mirror(sx => { line(s, [0.18 * sx, -0.62, 0.15], [0.2 * sx, -0.64, 0.32], 0.11, 0.1, "brown", 6); paint(s, [0.2 * sx, -0.62, 0.42], 0.06, "tan"); });
  },
  penguin(s) {
    for (let y = -0.4; y <= 0.15; y += 0.05) ball(s, [0, y, 0], 0.38 - Math.abs(y + 0.15) * 0.25, "black"); // egg body
    ball(s, [0, 0.18, 0.02], 0.3, "black");
    for (let y = -0.55; y <= 0.15; y += 0.06) paint(s, [0, y, 0.36], 0.24, "white");            // belly + face
    paint(s, [0, 0.2, 0.3], 0.18, "white");
    mirror(sx => line(s, [0.33 * sx, -0.05, 0], [0.42 * sx, -0.38, 0.02], 0.08, 0.05, "black", 10)); // flippers
    line(s, [0, 0.13, 0.3], [0, 0.11, 0.42], 0.06, 0.025, "orange", 8);                         // beak
    mirror(sx => eye(s, 0.115 * sx, 0.25, 0.335, 0.05));
    mirror(sx => paint(s, [0.19 * sx, 0.1, 0.26], 0.05, "pink"));
    mirror(sx => line(s, [0.12 * sx, -0.66, 0.15], [0.16 * sx, -0.68, 0.3], 0.07, 0.055, "orange", 6)); // feet
  },
};

function exportAnimal(name, outDir, N, heightMM) {
  const s = Studio(N, BASE[name]);
  ANIMALS[name](s);
  // gentle overall smoothing pass so blobs read as one soft figure
  const out = s.printable({ heightMM, baseFrac: 0.04, thicken: 0.3, relax: 0 });
  const body = s.toPrint(out.mesh, out.pf.cut, out.pf.top, heightMM);
  const parts = s.colourParts(out.pf, { web: true }).map(p => ({ label: p.label, ...s.toPrint(p.mesh, out.pf.cut, out.pf.top, heightMM, body.centre), check: S.check(p.mesh.idx),
                                                              web: s.toPrint(p.web, out.pf.cut, out.pf.top, heightMM, body.centre) }));
  const dir = path.join(outDir, name); fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, "body.stl"), S.stl(body.pos, body.idx, name));
  const meta = { name, body: out.check, parts: [] };
  for (const p of parts) {
    const cname = NAMES[p.label];
    fs.writeFileSync(path.join(dir, `part_${cname}.stl`), S.stl(p.pos, p.idx, cname));
    fs.writeFileSync(path.join(dir, `web_${cname}.stl`), S.stl(p.web.pos, p.web.idx, cname));
    meta.parts.push({ colour: cname, hex: COL[cname], check: p.check });
  }
  const pal = {}; NAMES.forEach((nm, i) => { pal[i] = COL[nm]; });
  const fld = s.colourField(out.pf, pal);
  const pv = s.previewMesh(out.pf, fld), pvp = s.toPrint(pv, out.pf.cut, out.pf.top, heightMM, body.centre);
  fs.writeFileSync(path.join(dir, "preview.bin"), S.paintBin(pvp.pos, pvp.idx, pv.shares, fld.cols, fld.L));
  fs.writeFileSync(path.join(dir, "body_paint.bin"), S.paintBin(body.pos, body.idx, s.sampleShares(fld, out.mesh.pos), fld.cols, fld.L));
  fs.writeFileSync(path.join(dir, "meta.json"), JSON.stringify(meta, null, 1));
  return meta;
}

if (require.main === module) {
  const outDir = process.argv[2], names = process.argv.slice(3).length ? process.argv.slice(3) : Object.keys(ANIMALS);
  for (const n of names) {
    const t0 = Date.now(); const m = exportAnimal(n, outDir, 160, 70);
    console.log(n, (Date.now() - t0) + "ms", "body", m.body.watertight, m.body.triangles, "parts", m.parts.map(p => p.colour + (p.check.watertight ? "" : "!")).join(","));
  }
}
module.exports = { ANIMALS, COL };
