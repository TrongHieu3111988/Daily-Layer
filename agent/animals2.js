// Sculpt original cute animals with the Sculpt Studio v2 engine (same brushes as the app) and export print files.
// usage: node animals2.js <outdir> [name ...]
const S1 = require("./core.js");
const S2 = require("./core2.js");
const fs = require("fs"), path = require("path");

const COL = { orange: "#F28C3A", white: "#FBFBF8", ink: "#24283A", pink: "#F7A1B5", cream: "#F4E9D4",
              green: "#7CC56B", lime: "#D9F0B5", rose: "#F7A9C4", magenta: "#E0609A", grey: "#A9AFBF", slate: "#7C8396", brown: "#7A4E33" };
const NAMES = Object.keys(COL), L = n => NAMES.indexOf(n);
const BASE = { fox: "orange", frog: "green", axolotl: "rose", kitten: "grey" };

function kit(s) {
  const k = {
    blob: (p, r, col) => s.brush({ tool: "blob", p, r, color: L(col) }),
    line: (a, b, r0, r1, col, n = 14) => {
      const at = t => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
      for (let i = 0; i <= n; i++) { const t = i / n; k.blob(at(t), r0 + (r1 - r0) * t, col); }
      // sweep the Smooth brush along the chain, as a sculptor would, so the blobs read as one form
      for (let pass = 0; pass < 3; pass++) for (let i = 0; i <= n; i++) { const t = i / n, rr = r0 + (r1 - r0) * t; s.brush({ tool: "smooth", p: at(t), r: rr * 1.5, s: 0.6 }); }
    },
    mirror: fn => { fn(1); fn(-1); },
    // find the surface by casting a ray towards the model, like a finger touching the screen
    hit: (x, y, from = [0, 0, 1]) => s.raycast([x + from[0] * 2, y + from[1] * 2, from[2] * 2], [-from[0], -from[1], -from[2]].map((v, _, a) => v / Math.hypot(...a))),
    stroke: (tool, pts, r, sPow, opts = {}) => {
      for (const [x, y] of pts) { const h = k.hit(x, y, opts.from); if (h) s.brush({ tool, p: h.p, n: h.n, r, s: sPow, invert: !!opts.invert, color: L(opts.color || "ink") }); }
    },
    arc: (cx, cy, rx, ry, a0, a1, n = 16) => { const out = []; for (let i = 0; i <= n; i++) { const a = a0 + (a1 - a0) * i / n; out.push([cx + rx * Math.cos(a), cy + ry * Math.sin(a)]); } return out; },
    eye: (x, y, z, r) => { k.blob([x, y, z], r, "ink"); k.blob([x + 0.3 * r * Math.sign(x || 1), y + 0.35 * r, z + 0.72 * r], r * 0.36, "white"); },
    smoothAll: (passes, region = [[0, 0, 0], 1.2]) => { for (let i = 0; i < passes; i++) s.brush({ tool: "smooth", p: region[0], r: region[1], s: 0.35 }); },
    paint: (p, r, col) => s.brush({ tool: "paint", p, r, s: 1, color: L(col) }),
  };
  return k;
}

const ANIMALS = {
  fox(s, k) {
    k.blob([0, -0.32, 0], 0.38, "orange");                       // body
    k.blob([0, 0.08, 0.04], 0.33, "orange");                     // head
    k.mirror(sx => k.line([0.2 * sx, 0.06, 0.16], [0.36 * sx, 0.0, 0.08], 0.12, 0.05, "orange", 10));   // cheek fluff
    k.mirror(sx => k.line([0.17 * sx, 0.3, 0.0], [0.27 * sx, 0.6, -0.04], 0.12, 0.03, "orange", 16)); // ears
    k.mirror(sx => k.stroke("pinch", [[0.25 * sx, 0.55]], 0.08, 0.8, { from: [0, 0.2, 1] }));
    k.line([0, 0.0, 0.3], [0, -0.03, 0.42], 0.11, 0.06, "white", 10);      // muzzle
    // repaint the muzzle surface so carving the smile cannot expose orange underneath
    const muzzle = []; for (let x = -0.1; x <= 0.1001; x += 0.025) for (let y = -0.1; y <= 0.06; y += 0.025) muzzle.push([x, y]);
    k.stroke("paint", muzzle, 0.045, 1, { color: "white" });
    k.blob([0, 0.0, 0.47], 0.04, "ink");                          // nose
    k.mirror(sx => k.eye(0.13 * sx, 0.14, 0.32, 0.045));
    k.stroke("dam", k.arc(0, -0.08, 0.05, 0.03, Math.PI * 0.15, Math.PI * 0.85, 8), 0.02, 0.6);   // smile
    k.stroke("paint", muzzle.filter(([x, y]) => y < -0.02), 0.04, 1, { color: "white" });
    k.mirror(sx => { for (let t = 0; t <= 1; t += 0.2) k.paint([0.25 * sx, 0.55 - 0.18 * t, 0.06 - 0.04 * t], 0.06, "ink"); });  // dark ear tips
    k.mirror(sx => { for (let t = 0; t <= 1.01; t += 0.25) k.paint([0.14 * sx * (1 - t), 0.03 - 0.06 * t, 0.36], 0.08, "white"); });
    k.paint([0, -0.3, 0.36], 0.2, "white");                       // chest
    // big fluffy tail curling around the side
    k.line([0.22, -0.55, -0.25], [0.48, -0.45, 0.0], 0.13, 0.17, "orange", 12);
    k.line([0.48, -0.45, 0.0], [0.42, -0.42, 0.22], 0.17, 0.11, "orange", 10);
    for (let t = 0; t <= 1; t += 0.25) k.paint([0.42 + 0.02 * t, -0.42, 0.22 + 0.06 * t], 0.12, "white");
    k.mirror(sx => k.line([0.14 * sx, -0.64, 0.18], [0.17 * sx, -0.66, 0.3], 0.08, 0.07, "orange", 6));  // paws
    k.mirror(sx => k.paint([0.17 * sx, -0.63, 0.36], 0.08, "brown"));
  },
  frog(s, k) {
    k.blob([0, -0.38, 0], 0.4, "green");
    for (let y = -0.3; y <= 0.0; y += 0.05) k.blob([0, y, 0.02], 0.36 - (y + 0.3) * 0.25, "green");
    k.mirror(sx => { k.blob([0.17 * sx, 0.1, 0.12], 0.14, "green"); k.blob([0.17 * sx, 0.14, 0.23], 0.085, "white"); k.blob([0.18 * sx, 0.15, 0.3], 0.05, "ink"); k.blob([0.2 * sx, 0.18, 0.345], 0.016, "white"); });
    k.stroke("dam", k.arc(0, -0.08, 0.2, 0.09, Math.PI * 1.08, Math.PI * 1.92, 20), 0.025, 0.7);   // wide smile
    k.mirror(sx => k.paint([0.25 * sx, -0.08, 0.28], 0.06, "pink"));
    k.stroke("paint", [[0, -0.22], [0, -0.3], [0, -0.38], [0, -0.46], [0, -0.54], [0, -0.6], [-0.06, -0.4], [0.06, -0.4], [-0.06, -0.52], [0.06, -0.52]], 0.17, 1, { color: "lime" });   // belly
    k.mirror(sx => { k.line([0.3 * sx, -0.6, 0.12], [0.36 * sx, -0.66, 0.32], 0.1, 0.07, "green", 8); k.blob([0.36 * sx, -0.67, 0.36], 0.08, "green"); });   // feet
    k.mirror(sx => k.line([0.32 * sx, -0.25, 0.18], [0.18 * sx, -0.42, 0.36], 0.08, 0.06, "green", 10)); // arms
  },
  axolotl(s, k) {
    k.blob([0, -0.38, -0.05], 0.36, "rose");
    k.blob([0, -0.02, 0.05], 0.34, "rose");
    k.mirror(sx => {                                              // three feathery gills each side
      for (const [ang, len] of [[0.35, 0.3], [0.0, 0.33], [-0.35, 0.28]]) {
        const a = [0.28 * sx, 0.06, -0.02], b = [a[0] + sx * len * Math.cos(ang), a[1] + len * Math.sin(ang) + 0.06, -0.06];
        k.line(a, b, 0.06, 0.035, "magenta", 12);
      }
    });
    k.mirror(sx => k.eye(0.15 * sx, 0.04, 0.33, 0.045));
    k.stroke("dam", k.arc(0, -0.08, 0.09, 0.045, Math.PI * 1.12, Math.PI * 1.88, 14), 0.022, 0.65);
    k.mirror(sx => k.paint([0.24 * sx, -0.06, 0.28], 0.055, "magenta"));
    k.line([0, -0.3, -0.35], [0, -0.42, -0.62], 0.16, 0.06, "rose", 14);                        // tail
    k.line([0, -0.2, -0.32], [0, -0.32, -0.6], 0.03, 0.02, "magenta", 10);                       // tail fin ridge
    k.mirror(sx => k.line([0.24 * sx, -0.58, 0.12], [0.3 * sx, -0.66, 0.26], 0.07, 0.055, "rose", 6));
    for (let y = -0.62; y <= -0.25; y += 0.06) k.paint([0, y, 0.34], 0.16, "cream");
  },
  kitten(s, k) {
    k.blob([0, -0.34, 0], 0.37, "grey");
    k.blob([0, 0.08, 0.04], 0.34, "grey");
    k.mirror(sx => k.line([0.18 * sx, 0.3, 0.02], [0.27 * sx, 0.52, 0.0], 0.11, 0.03, "grey", 14));
    k.mirror(sx => k.stroke("pinch", [[0.26 * sx, 0.47]], 0.07, 0.7, { from: [0, 0.2, 1] }));
    k.mirror(sx => { for (let t = 0; t <= 1; t += 0.25) k.paint([0.2 * sx + 0.05 * sx * t, 0.34 + 0.12 * t, 0.12], 0.04, "pink"); });
    k.mirror(sx => k.blob([0.06 * sx, -0.02, 0.36], 0.065, "white"));                             // muzzle puffs
    k.blob([0, 0.04, 0.39], 0.03, "pink");                                                        // nose
    k.mirror(sx => k.eye(0.14 * sx, 0.13, 0.31, 0.05));
    k.stroke("dam", [[0, 0.02], [0, -0.03]], 0.018, 0.55);
    // tabby stripes on the forehead and back
    for (const dx of [-0.07, 0, 0.07]) k.stroke("paint", [[dx, 0.3], [dx * 1.1, 0.24]], 0.022, 1, { color: "slate", from: [0, 0.4, 1] });
    for (const y of [-0.15, -0.3, -0.45]) k.stroke("paint", k.arc(0, y, 0.3, 0.02, Math.PI * 0.75, Math.PI * 1.25, 10), 0.03, 1, { color: "slate", from: [0, 0, -1] });
    k.paint([0, -0.32, 0.36], 0.18, "white");
    k.mirror(sx => { k.line([0.15 * sx, -0.63, 0.16], [0.17 * sx, -0.65, 0.3], 0.085, 0.075, "grey", 6); k.paint([0.17 * sx, -0.63, 0.36], 0.08, "white"); });
    k.line([-0.25, -0.62, -0.2], [-0.45, -0.55, 0.05], 0.07, 0.06, "grey", 12);                   // tail wrapped to the front
    k.line([-0.45, -0.55, 0.05], [-0.33, -0.6, 0.26], 0.06, 0.055, "grey", 10);
  },
};

function exportAnimal(name, outDir, N, heightMM) {
  const s = new S2(N);
  s.f.fill(s.clamp); s.c.fill(L(BASE[name]));
  const k = kit(s);
  ANIMALS[name](s, k);
  const out = s.printable({ heightMM, baseFrac: 0.04, thicken: 0.4, relax: 0 });
  const body = s.toPrint(out.mesh, out.pf.cut, out.pf.top, heightMM);
  const raw = s.colourParts(out.pf, { web: true });
  const parts = raw.map(p => ({ label: p.label, ...s.toPrint(p.mesh, out.pf.cut, out.pf.top, heightMM, body.centre), check: S1.check(p.mesh.idx),
                                web: s.toPrint(p.web, out.pf.cut, out.pf.top, heightMM, body.centre) }));
  const dir = path.join(outDir, name); fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, "body.stl"), S1.stl(body.pos, body.idx, name));
  const meta = { name, resolution: N, body: out.check, parts: [] };
  for (const p of parts) {
    const cname = NAMES[p.label];
    fs.writeFileSync(path.join(dir, `part_${cname}.stl`), S1.stl(p.pos, p.idx, cname));
    fs.writeFileSync(path.join(dir, `web_${cname}.stl`), S1.stl(p.web.pos, p.web.idx, cname));
    meta.parts.push({ colour: cname, hex: COL[cname], check: p.check });
  }
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
