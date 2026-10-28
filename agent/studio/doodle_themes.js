// Doodle Puff themes: objects a child draws by tracing a dotted outline, then gets back as a round 3D object.
// Each theme is a side-view profile: r(y) = half width at row y (paper is 512 px), around a vertical axis.
// Runs in the browser (window.DoodleThemes) and in node (tests).
(function (root) {
  "use strict";
  const sq = v => Math.sqrt(Math.max(0, v));
  const circ = (y, cy, R) => sq(R * R - (y - cy) * (y - cy));
  const THEMES = [
    { id: "cup", vi: "Cái cốc", en: "Cup", tint: "#4FA8E8", mode: "left", axis: 228, hollow: true, y0: 150, y1: 440,
      r: y => 116 - (y - 150) * 0.04 - (y > 424 ? (y - 424) * (y - 424) * 0.09 : 0),
      // the handle: a C-shaped band on the right, with paper inside it that stays a hole
      parts: [() => { const p = [], cx = 340, cy = 292; for (let a = -1.25; a <= 1.2501; a += 0.05) p.push([cx + 96 * Math.cos(a), cy + 100 * Math.sin(a)]);
        p.push([326, cy + 100 * Math.sin(1.25)], [326, cy + 64 * Math.sin(1.2)]);
        for (let a = 1.2; a >= -1.2001; a -= 0.05) p.push([cx + 58 * Math.cos(a), cy + 64 * Math.sin(a)]);
        p.push([326, cy - 64 * Math.sin(1.2)], [326, cy - 100 * Math.sin(1.25)]); return p; }],
      keep: () => { const p = []; for (let a = -1.2; a <= 1.2001; a += 0.1) p.push([340 + 50 * Math.cos(a), 292 + 56 * Math.sin(a)]); p.push([346, 292 + 56 * Math.sin(1.2)], [346, 292 - 56 * Math.sin(1.2)]); return p; } },
    { id: "balloon", vi: "Bóng bay", en: "Balloon", tint: "#E8483B", mode: "sym", axis: 256, y0: 44, y1: 440,
      r: y => y <= 340 ? 122 * sq(1 - ((y - 195) / 150) ** 2) : y <= 358 ? Math.max(4.5, 15 - Math.abs(y - 348) * 0.8) : 4.5,
      c: y => y > 358 ? 256 + 13 * Math.sin((y - 358) / 15) : 256 },
    { id: "tree", vi: "Cái cây", en: "Tree", tint: "#5CBF6A", mode: "sym", axis: 256, y0: 48, y1: 440,
      r: y => Math.max(y <= 332 ? circ(y, 190, 142) * (1 + 0.07 * Math.sin((y - 48) / 284 * Math.PI * 6) ** 2) : 0, y >= 300 ? 30 + (y > 414 ? (y - 414) * 0.9 : 0) : 0) },
    { id: "pine", vi: "Cây thông", en: "Pine tree", tint: "#3F9C5A", mode: "sym", axis: 256, y0: 40, y1: 440,
      r: y => { let r = y >= 330 ? 28 : 0; [[40, 82], [118, 118], [205, 152]].forEach(([t, R]) => { if (y >= t && y <= t + 125) r = Math.max(r, 6 + (y - t) / 125 * (R - 6)); }); return r; } },
    { id: "icecream", vi: "Kem ốc quế", en: "Ice cream", tint: "#F7A1B5", mode: "sym", axis: 256, y0: 62, y1: 440,
      r: y => Math.max(y <= 285 ? circ(y, 178, 116) : 0, y >= 250 ? 104 * (440 - y) / 190 + 3 : 0) },
    { id: "mushroom", vi: "Cây nấm", en: "Mushroom", tint: "#E8483B", mode: "sym", axis: 256, y0: 92, y1: 440,
      r: y => Math.max(y <= 250 ? 176 * sq(1 - ((250 - y) / 158) ** 2) : y <= 266 ? 176 - (y - 250) * 7 : 0, y >= 250 ? 58 + (y > 404 ? (y - 404) * 0.5 : 0) : 0) },
    { id: "snowman", vi: "Người tuyết", en: "Snowman", tint: "#4FA8E8", mode: "sym", axis: 256, y0: 40, y1: 440,
      r: y => Math.max(circ(y, 92, 52), circ(y, 204, 74), y <= 440 ? circ(y, 350, 96) : 0, y >= 420 ? 64 : 0) },
    { id: "rocket", vi: "Tên lửa", en: "Rocket", tint: "#9B6BD6", mode: "sym", axis: 256, y0: 46, y1: 440,
      r: y => Math.max(y <= 175 ? 72 * sq(1 - ((175 - y) / 129) ** 2) : y <= 395 ? 72 : 72 - (y - 395) * 0.5, y >= 300 ? 72 + (y - 300) * 0.55 : 0) },
    { id: "vase", vi: "Lọ hoa", en: "Vase", tint: "#FF9B3D", mode: "sym", axis: 256, hollow: true, y0: 100, y1: 440,
      r: y => y <= 136 ? 78 - (y - 100) * 0.35 : 58 + 66 * Math.sin(Math.PI * Math.min(1, (y - 136) / 330)) ** 1.3 - (y > 428 ? (y - 428) * (y - 428) * 0.12 : 0) }
  ];
  // closed outline of the body (right side going down, left side coming back up)
  function body(t) {
    const R = [], Lf = [], c = t.c || (() => t.axis);
    for (let y = t.y0; y <= t.y1 + 0.001; y += 2) { const r = Math.max(t.r(y), 0.5), x = c(y); R.push([x + r, y]); Lf.push([x - r, y]); }
    return R.concat(Lf.reverse());
  }
  function outlines(t) { return [body(t)].concat((t.parts || []).map(f => f())); }
  // fill polygons into a W x W mask (even-odd per polygon, union over polygons)
  function rasterize(polys, W) {
    const m = new Uint8Array(W * W);
    for (const poly of polys) for (let y = 0; y < W; y++) {
      const yc = y + 0.5, xs = [];
      for (let i = 0; i < poly.length; i++) { const [ax, ay] = poly[i], [bx, by] = poly[(i + 1) % poly.length];
        if ((ay <= yc) !== (by <= yc)) xs.push(ax + (yc - ay) / (by - ay) * (bx - ax)); }
      xs.sort((a, b) => a - b);
      for (let k = 0; k + 1 < xs.length; k += 2) for (let x = Math.max(0, Math.ceil(xs[k] - 0.5)); x <= Math.min(W - 1, Math.floor(xs[k + 1] - 0.5)); x++) m[x + W * y] = 1;
    }
    return m;
  }
  function masks(t, W) {
    const s = W / 512, sc = ps => ps.map(([x, y]) => [x * s, y * s]);
    return { guide: rasterize(outlines(t).map(sc), W), keep: t.keep ? rasterize([sc(t.keep())], W) : null };
  }
  function spec(t, W) { const m = masks(t, W); return { id: t.id, mode: t.mode, axis: t.axis * W / 512, hollow: !!t.hollow, keep: m.keep }; }
  const api = { THEMES, outlines, rasterize, masks, spec, byId: id => THEMES.find(t => t.id === id) };
  root.DoodleThemes = api;
  if (typeof module !== "undefined") module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
