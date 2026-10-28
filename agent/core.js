// Sculpt Studio core: voxel SDF + colour labels, brushes, surface-nets meshing, printable export.
// Plain JS, no dependencies, so it runs in the browser and in Node for tests.
(function (root) {
  "use strict";

  function Sculpt(N) {
    this.N = N;                       // samples per axis
    this.h = 2 / (N - 1);             // voxel size in world units (grid spans -1..1)
    this.f = new Float32Array(N * N * N);   // field: negative inside
    this.c = new Uint8Array(N * N * N);     // colour label per sample
    this.clamp = 0.25;
    this.f.fill(this.clamp);
    this.undo = []; this.redo = [];
  }
  const P = Sculpt.prototype;
  P.idx = function (i, j, k) { return i + this.N * (j + this.N * k); };
  P.pos = function (i) { return -1 + i * this.h; };

  P.snapshot = function () {
    this.undo.push([this.f.slice(), this.c.slice()]);
    if (this.undo.length > 12) this.undo.shift();
    this.redo.length = 0;
  };
  P.doUndo = function () {
    if (!this.undo.length) return false;
    this.redo.push([this.f.slice(), this.c.slice()]);
    const [f, c] = this.undo.pop(); this.f.set(f); this.c.set(c); return true;
  };
  P.doRedo = function () {
    if (!this.redo.length) return false;
    this.undo.push([this.f.slice(), this.c.slice()]);
    const [f, c] = this.redo.pop(); this.f.set(f); this.c.set(c); return true;
  };

  // ---------- starting shapes (original, generic) ----------
  P.reset = function (kind, color) {
    const N = this.N, cl = this.clamp;
    for (let k = 0; k < N; k++) for (let j = 0; j < N; j++) for (let i = 0; i < N; i++) {
      const x = this.pos(i), y = this.pos(j), z = this.pos(k);
      let d;
      if (kind === "egg") {
        const yy = y + 0.05, sy = yy > 0 ? 0.62 : 0.5;
        d = (Math.hypot(x / 0.42, yy / sy, z / 0.42) - 1) * 0.42;
      } else if (kind === "pebble") {
        d = (Math.hypot(x / 0.6, (y + 0.25) / 0.3, z / 0.5) - 1) * 0.3;
      } else if (kind === "block") {
        const qx = Math.abs(x) - 0.32, qy = Math.abs(y + 0.1) - 0.32, qz = Math.abs(z) - 0.32;
        const out = Math.hypot(Math.max(qx, 0), Math.max(qy, 0), Math.max(qz, 0));
        d = out + Math.min(Math.max(qx, qy, qz), 0) - 0.06;
      } else {
        d = Math.hypot(x, y + 0.05, z) - 0.45;
      }
      const b = (i === 0 || j === 0 || k === 0 || i === N - 1 || j === N - 1 || k === N - 1);
      const id = this.idx(i, j, k);
      this.f[id] = b ? cl : Math.max(-cl, Math.min(cl, d));
      this.c[id] = color;
    }
    this.undo.length = 0; this.redo.length = 0;
  };

  function smin(a, b, k) { const h = Math.max(k - Math.abs(a - b), 0) / k; return Math.min(a, b) - h * h * k * 0.25; }
  function smax(a, b, k) { return -smin(-a, -b, k); }

  // ---------- brushes ----------
  // tool: add | carve | smooth | paint ; p = [x,y,z] world ; r radius ; color label ; strength 0..1
  P.dab = function (tool, p, r, color, strength) {
    const N = this.N, h = this.h, cl = this.clamp;
    const R = r + 2 * h;
    const i0 = Math.max(1, Math.floor((p[0] - R + 1) / h)), i1 = Math.min(N - 2, Math.ceil((p[0] + R + 1) / h));
    const j0 = Math.max(1, Math.floor((p[1] - R + 1) / h)), j1 = Math.min(N - 2, Math.ceil((p[1] + R + 1) / h));
    const k0 = Math.max(1, Math.floor((p[2] - R + 1) / h)), k1 = Math.min(N - 2, Math.ceil((p[2] + R + 1) / h));
    const f = this.f, c = this.c;
    if (tool === "smooth") {
      const src = f.slice();
      for (let k = k0; k <= k1; k++) for (let j = j0; j <= j1; j++) for (let i = i0; i <= i1; i++) {
        const x = this.pos(i) - p[0], y = this.pos(j) - p[1], z = this.pos(k) - p[2];
        const d = Math.hypot(x, y, z); if (d > r) continue;
        const w = strength * (1 - d / r);
        const id = this.idx(i, j, k), s = N, s2 = N * N;
        const avg = (src[id - 1] + src[id + 1] + src[id - s] + src[id + s] + src[id - s2] + src[id + s2]) / 6;
        f[id] = src[id] + w * (avg - src[id]);
      }
      return;
    }
    const k = Math.max(r * 0.35, 1.5 * h);
    for (let kk = k0; kk <= k1; kk++) for (let j = j0; j <= j1; j++) for (let i = i0; i <= i1; i++) {
      const x = this.pos(i) - p[0], y = this.pos(j) - p[1], z = this.pos(kk) - p[2];
      const d = Math.hypot(x, y, z);
      const id = this.idx(i, j, kk);
      const s = d - r;
      if (tool === "add") {
        const nv = smin(f[id], s, k);
        f[id] = Math.max(-cl, f[id] + strength * (nv - f[id]));
        if (s < h && f[id] < h) c[id] = color;
      } else if (tool === "carve") {
        const nv = smax(f[id], -s, k);
        f[id] = Math.min(cl, f[id] + strength * (nv - f[id]));
      } else if (tool === "paint") {
        if (d <= r && f[id] > -3.5 * h) c[id] = color;
      }
    }
  };

  // ---------- surface nets ----------
  // returns {pos: Float32Array, col: Uint8Array (labels per vertex), idx: Uint32Array}
  P.mesh = function (field, labels) {
    field = field || this.f; labels = labels || this.c;
    const N = this.N, h = this.h, M = N - 1;
    const vid = new Int32Array(M * M * M).fill(-1);
    const pos = [], col = [];
    const cornerOff = [];
    for (let c = 0; c < 8; c++) cornerOff.push([(c & 1), (c >> 1) & 1, (c >> 2) & 1]);
    const edges = [[0, 1], [2, 3], [4, 5], [6, 7], [0, 2], [1, 3], [4, 6], [5, 7], [0, 4], [1, 5], [2, 6], [3, 7]];
    const v = new Float32Array(8);
    for (let k = 0; k < M; k++) for (let j = 0; j < M; j++) for (let i = 0; i < M; i++) {
      let mask = 0;
      for (let c = 0; c < 8; c++) {
        const o = cornerOff[c];
        v[c] = field[this.idx(i + o[0], j + o[1], k + o[2])];
        if (v[c] < 0) mask |= 1 << c;
      }
      if (mask === 0 || mask === 255) continue;
      let sx = 0, sy = 0, sz = 0, n = 0;
      for (const [a, b] of edges) {
        if ((v[a] < 0) === (v[b] < 0)) continue;
        const t = v[a] / (v[a] - v[b]);
        const oa = cornerOff[a], ob = cornerOff[b];
        sx += oa[0] + t * (ob[0] - oa[0]); sy += oa[1] + t * (ob[1] - oa[1]); sz += oa[2] + t * (ob[2] - oa[2]); n++;
      }
      vid[i + M * (j + M * k)] = pos.length / 3;
      pos.push(-1 + (i + sx / n) * h, -1 + (j + sy / n) * h, -1 + (k + sz / n) * h);
      // colour: the inside corner closest to the surface
      let best = -1, bv = -1e9;
      for (let c = 0; c < 8; c++) if (v[c] < 0 && v[c] > bv) { bv = v[c]; best = c; }
      const o = cornerOff[best];
      col.push(labels[this.idx(i + o[0], j + o[1], k + o[2])]);
    }
    const idx = [];
    const cell = (i, j, k) => vid[i + M * (j + M * k)];
    // for each grid edge with a sign change, connect the 4 cells around it
    for (let k = 1; k < M; k++) for (let j = 1; j < M; j++) for (let i = 0; i < M; i++) {     // x edges
      const a = field[this.idx(i, j, k)] < 0, b = field[this.idx(i + 1, j, k)] < 0;
      if (a === b) continue;
      quad(cell(i, j - 1, k - 1), cell(i, j, k - 1), cell(i, j, k), cell(i, j - 1, k), a);
    }
    for (let k = 1; k < M; k++) for (let j = 0; j < M; j++) for (let i = 1; i < M; i++) {     // y edges
      const a = field[this.idx(i, j, k)] < 0, b = field[this.idx(i, j + 1, k)] < 0;
      if (a === b) continue;
      quad(cell(i - 1, j, k - 1), cell(i - 1, j, k), cell(i, j, k), cell(i, j, k - 1), a);
    }
    for (let k = 0; k < M; k++) for (let j = 1; j < M; j++) for (let i = 1; i < M; i++) {     // z edges
      const a = field[this.idx(i, j, k)] < 0, b = field[this.idx(i, j, k + 1)] < 0;
      if (a === b) continue;
      quad(cell(i - 1, j - 1, k), cell(i, j - 1, k), cell(i, j, k), cell(i - 1, j, k), a);
    }
    function quad(q0, q1, q2, q3, flip) {
      if (flip) idx.push(q0, q1, q2, q0, q2, q3); else idx.push(q0, q2, q1, q0, q3, q2);
    }
    return { pos: new Float32Array(pos), col: new Uint8Array(col), idx: new Uint32Array(idx) };
  };

  // ---------- marching tetrahedra (export): always closed and edge-manifold ----------
  P.meshTet = function (field) {
    const N = this.N, h = this.h, M = N - 1;
    // keep every sample a little away from zero so no crossing lands on a grid point:
    // vertices then never share a position, which keeps the STL closed after slicers weld by position
    const eps = 0.03 * h;
    field = Float32Array.from(field, v => (v < 0 ? Math.min(v, -eps) : Math.max(v, eps)));
    const cornerOff = []; for (let c = 0; c < 8; c++) cornerOff.push([(c & 1), (c >> 1) & 1, (c >> 2) & 1]);
    // Kuhn split of the cube along the 0-7 diagonal: consistent across neighbouring cubes
    const tets = [[0, 1, 3, 7], [0, 3, 2, 7], [0, 2, 6, 7], [0, 6, 4, 7], [0, 4, 5, 7], [0, 5, 1, 7]];
    const pos = [], idx = [], vmap = new Map();
    const ids = new Int32Array(8), val = new Float64Array(8);
    const self = this;
    function vert(a, b) {          // a, b are sample ids, val via field
      const key = a < b ? a * 4294967296 + b : b * 4294967296 + a;
      let v = vmap.get(key);
      if (v !== undefined) return v;
      const fa = field[a], fb = field[b], t = fa / (fa - fb);
      const ai = a % N, aj = Math.floor(a / N) % N, ak = Math.floor(a / (N * N));
      const bi = b % N, bj = Math.floor(b / N) % N, bk = Math.floor(b / (N * N));
      v = pos.length / 3;
      pos.push(-1 + (ai + t * (bi - ai)) * h, -1 + (aj + t * (bj - aj)) * h, -1 + (ak + t * (bk - ak)) * h);
      vmap.set(key, v); return v;
    }
    function P3(id) { return [-1 + (id % N) * h, -1 + (Math.floor(id / N) % N) * h, -1 + Math.floor(id / (N * N)) * h]; }
    function tri(p, q, r, inId, outId) {
      // orient so the normal points from inside to outside
      const A = pos.slice(3 * p, 3 * p + 3), B = pos.slice(3 * q, 3 * q + 3), C = pos.slice(3 * r, 3 * r + 3);
      const ux = B[0] - A[0], uy = B[1] - A[1], uz = B[2] - A[2], vx = C[0] - A[0], vy = C[1] - A[1], vz = C[2] - A[2];
      const nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx;
      const pi = P3(inId), po = P3(outId);
      const d = nx * (po[0] - pi[0]) + ny * (po[1] - pi[1]) + nz * (po[2] - pi[2]);
      if (d >= 0) idx.push(p, q, r); else idx.push(p, r, q);
    }
    for (let k = 0; k < M; k++) for (let j = 0; j < M; j++) for (let i = 0; i < M; i++) {
      let any = 0, all = 1;
      for (let c = 0; c < 8; c++) {
        const o = cornerOff[c]; ids[c] = self.idx(i + o[0], j + o[1], k + o[2]);
        let f = field[ids[c]]; if (f === 0) f = 1e-7; val[c] = f;
        if (f < 0) any = 1; else all = 0;
      }
      if (!any || all) continue;
      for (const T of tets) {
        const ins = [], outs = [];
        for (const c of T) (val[c] < 0 ? ins : outs).push(ids[c]);
        if (ins.length === 0 || ins.length === 4) continue;
        if (ins.length === 1) {
          tri(vert(ins[0], outs[0]), vert(ins[0], outs[1]), vert(ins[0], outs[2]), ins[0], outs[0]);
        } else if (ins.length === 3) {
          tri(vert(outs[0], ins[0]), vert(outs[0], ins[1]), vert(outs[0], ins[2]), ins[0], outs[0]);
        } else {
          const a = vert(ins[0], outs[0]), b = vert(ins[0], outs[1]), c = vert(ins[1], outs[1]), d = vert(ins[1], outs[0]);
          tri(a, b, c, ins[0], outs[0]); tri(a, c, d, ins[0], outs[0]);
        }
      }
    }
    return { pos: new Float32Array(pos), idx: new Uint32Array(idx) };
  };

  // ---------- printable export ----------
  // opts: {heightMM, baseFrac, thicken}
  P.printField = function (opts) {
    const N = this.N, h = this.h;
    const f = this.f.slice();
    if (opts.thicken) for (let n = 0; n < f.length; n++) f[n] -= opts.thicken * h;
    // a light blur removes one-voxel pinches (saddles) that would make non-manifold edges
    const passes = opts.relax == null ? 1 : opts.relax;
    for (let p = 0; p < passes; p++) { const b = blur3(f, N); f.set(b); }
    // find vertical extent (y is up)
    let ymin = 1e9, ymax = -1e9;
    for (let k = 0; k < N; k++) for (let j = 0; j < N; j++) for (let i = 0; i < N; i++) {
      if (f[this.idx(i, j, k)] < 0) { const y = this.pos(j); if (y < ymin) ymin = y; if (y > ymax) ymax = y; }
    }
    if (ymin > ymax) return null;
    const cut = ymin + (ymax - ymin) * (opts.baseFrac || 0.06);
    for (let k = 0; k < N; k++) for (let j = 0; j < N; j++) for (let i = 0; i < N; i++) {
      const id = this.idx(i, j, k);
      f[id] = Math.max(f[id], cut - this.pos(j));
      if (i === 0 || j === 0 || k === 0 || i === N - 1 || j === N - 1 || k === N - 1) f[id] = this.clamp;
    }
    return { f, cut, top: ymax };
  };

  // closed print mesh: relax the field a little more until every edge has exactly two faces
  P.printable = function (opts) {
    const pf = this.printField(opts);
    if (!pf) return null;
    const m = this.meshTet(pf.f);
    return { pf, mesh: m, check: Sculpt.check(m.idx) };
  };

  // world (y-up) -> print (z-up, mm, sitting on z=0, centred)
  // centre: [cx, cz] in world units; pass the body's centre to every colour part so they stay aligned
  P.toPrint = function (m, cut, top, heightMM, centre) {
    const s = heightMM / Math.max(top - cut, 1e-6);
    const out = new Float32Array(m.pos.length);
    let cx = 0, cz = 0, n = m.pos.length / 3;
    if (centre) { cx = centre[0]; cz = centre[1]; }
    else { for (let q = 0; q < n; q++) { cx += m.pos[3 * q]; cz += m.pos[3 * q + 2]; } cx /= n || 1; cz /= n || 1; }
    for (let q = 0; q < n; q++) {
      const x = m.pos[3 * q], y = m.pos[3 * q + 1], z = m.pos[3 * q + 2];
      out[3 * q] = (x - cx) * s; out[3 * q + 1] = -(z - cz) * s; out[3 * q + 2] = (y - cut) * s;
    }
    return { pos: out, idx: m.idx, scale: s, centre: [cx, cz] };
  };

  // one closed mesh per colour label, for multi-material 3MF
  P.colourParts = function (pf) {
    const N = this.N, h = this.h, used = new Set();
    for (let n = 0; n < pf.f.length; n++) if (pf.f[n] < 0) used.add(this.c[n]);
    // smoothed indicator per colour; each colour's region is where its indicator beats every other one.
    // The regions tile the solid exactly (shared interfaces, no gaps), so no colour can leave a hole.
    const labs = [...used], n3 = pf.f.length, bls = [];
    for (const lab of labs) {
      const ind = new Float32Array(n3);
      for (let n = 0; n < n3; n++) ind[n] = this.c[n] === lab ? 1 : 0;
      bls.push(blur3(ind, N));
    }
    const parts = [];
    for (let li = 0; li < labs.length; li++) {
      const lab = labs[li], bl = bls[li];
      const g = new Float32Array(n3);
      for (let n = 0; n < n3; n++) {
        let other = 0; for (let lj = 0; lj < labs.length; lj++) if (lj !== li && bls[lj][n] > other) other = bls[lj][n];
        g[n] = Math.max(pf.f[n], (other - bl[n]) * 2 * h);
      }
      for (let k = 0; k < N; k++) for (let j = 0; j < N; j++) for (let i = 0; i < N; i++)
        if (i === 0 || j === 0 || k === 0 || i === N - 1 || j === N - 1 || k === N - 1) g[this.idx(i, j, k)] = this.clamp;
      const m = this.meshTet(g);
      if (m.idx.length) parts.push({ label: lab, mesh: m });
    }
    return parts;
  };
  function blur3(a, N) {
    let src = a, dst = new Float32Array(a.length);
    for (let axis = 0; axis < 3; axis++) {
      const st = axis === 0 ? 1 : axis === 1 ? N : N * N;
      for (let n = 0; n < a.length; n++) {
        const l = n - st >= 0 ? src[n - st] : src[n], r = n + st < a.length ? src[n + st] : src[n];
        dst[n] = 0.25 * l + 0.5 * src[n] + 0.25 * r;
      }
      const t = src; src = dst; dst = t === a ? new Float32Array(a.length) : t;
    }
    return src;
  }

  // ---------- mesh checks and writers ----------
  Sculpt.check = function (idx, nv) {
    const map = new Map();
    for (let t = 0; t < idx.length; t += 3) for (let e = 0; e < 3; e++) {
      const a = idx[t + e], b = idx[t + (e + 1) % 3];
      const key = a < b ? a * 4294967296 + b : b * 4294967296 + a;
      map.set(key, (map.get(key) || 0) + 1);
    }
    let bad = 0; for (const v of map.values()) if (v !== 2) bad++;
    return { triangles: idx.length / 3, badEdges: bad, watertight: bad === 0 };
  };
  Sculpt.volume = function (pos, idx) {
    let v = 0;
    for (let t = 0; t < idx.length; t += 3) {
      const a = idx[t] * 3, b = idx[t + 1] * 3, c = idx[t + 2] * 3;
      v += pos[a] * (pos[b + 1] * pos[c + 2] - pos[b + 2] * pos[c + 1])
         - pos[a + 1] * (pos[b] * pos[c + 2] - pos[b + 2] * pos[c])
         + pos[a + 2] * (pos[b] * pos[c + 1] - pos[b + 1] * pos[c]);
    }
    return v / 6;
  };
  Sculpt.stl = function (pos, idx, name) {
    const nt = idx.length / 3, buf = new ArrayBuffer(84 + nt * 50), dv = new DataView(buf);
    const hdr = (name || "sculpt").slice(0, 79);
    for (let i = 0; i < hdr.length; i++) dv.setUint8(i, hdr.charCodeAt(i) & 127);
    dv.setUint32(80, nt, true);
    let o = 84;
    for (let t = 0; t < nt; t++) {
      const a = idx[3 * t] * 3, b = idx[3 * t + 1] * 3, c = idx[3 * t + 2] * 3;
      const ux = pos[b] - pos[a], uy = pos[b + 1] - pos[a + 1], uz = pos[b + 2] - pos[a + 2];
      const vx = pos[c] - pos[a], vy = pos[c + 1] - pos[a + 1], vz = pos[c + 2] - pos[a + 2];
      let nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx;
      const L = Math.hypot(nx, ny, nz) || 1; nx /= L; ny /= L; nz /= L;
      for (const val of [nx, ny, nz]) { dv.setFloat32(o, val, true); o += 4; }
      for (const p of [a, b, c]) for (let e = 0; e < 3; e++) { dv.setFloat32(o, pos[p + e], true); o += 4; }
      dv.setUint16(o, 0, true); o += 2;
    }
    return new Uint8Array(buf);
  };
  Sculpt.model3mf = function (parts) {   // parts: [{name, hex, pos, idx}]
    const mats = parts.map(p => `<base name="${p.name}" displaycolor="${p.hex.toUpperCase()}FF"/>`).join("");
    let objs = "", items = "";
    parts.forEach((p, n) => {
      const vs = [], ts = [];
      for (let q = 0; q < p.pos.length; q += 3) vs.push(`<vertex x="${p.pos[q].toFixed(3)}" y="${p.pos[q + 1].toFixed(3)}" z="${p.pos[q + 2].toFixed(3)}"/>`);
      for (let q = 0; q < p.idx.length; q += 3) ts.push(`<triangle v1="${p.idx[q]}" v2="${p.idx[q + 1]}" v3="${p.idx[q + 2]}"/>`);
      objs += `<object id="${n + 2}" name="${p.name}" type="model" pid="1" pindex="${n}"><mesh><vertices>${vs.join("")}</vertices><triangles>${ts.join("")}</triangles></mesh></object>`;
      items += `<item objectid="${n + 2}"/>`;
    });
    return `<?xml version="1.0" encoding="UTF-8"?><model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"><resources><basematerials id="1">${mats}</basematerials>${objs}</resources><build>${items}</build></model>`;
  };

  // minimal zip (store, no compression) — enough for STL/3MF delivery
  const CRC = (() => { const t = new Uint32Array(256); for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; } return t; })();
  function crc32(u8) { let c = 0xFFFFFFFF; for (let i = 0; i < u8.length; i++) c = CRC[(c ^ u8[i]) & 255] ^ (c >>> 8); return (c ^ 0xFFFFFFFF) >>> 0; }
  const enc = s => new TextEncoder().encode(s);
  Sculpt.zip = function (files) {   // files: [{name, data: Uint8Array}]
    const chunks = [], central = []; let off = 0;
    for (const f of files) {
      const nm = enc(f.name), crc = crc32(f.data), sz = f.data.length;
      const lh = new DataView(new ArrayBuffer(30));
      lh.setUint32(0, 0x04034b50, true); lh.setUint16(4, 20, true); lh.setUint16(8, 0, true);
      lh.setUint32(14, crc, true); lh.setUint32(18, sz, true); lh.setUint32(22, sz, true); lh.setUint16(26, nm.length, true);
      chunks.push(new Uint8Array(lh.buffer), nm, f.data);
      const ch = new DataView(new ArrayBuffer(46));
      ch.setUint32(0, 0x02014b50, true); ch.setUint16(4, 20, true); ch.setUint16(6, 20, true);
      ch.setUint32(16, crc, true); ch.setUint32(20, sz, true); ch.setUint32(24, sz, true); ch.setUint16(28, nm.length, true);
      ch.setUint32(42, off, true);
      central.push(new Uint8Array(ch.buffer), nm);
      off += 30 + nm.length + sz;
    }
    const cdSize = central.reduce((a, b) => a + b.length, 0);
    const end = new DataView(new ArrayBuffer(22));
    end.setUint32(0, 0x06054b50, true); end.setUint16(8, files.length, true); end.setUint16(10, files.length, true);
    end.setUint32(12, cdSize, true); end.setUint32(16, off, true);
    const all = [...chunks, ...central, new Uint8Array(end.buffer)];
    const total = all.reduce((a, b) => a + b.length, 0), out = new Uint8Array(total);
    let p = 0; for (const a of all) { out.set(a, p); p += a.length; }
    return out;
  };
  Sculpt.package3mf = function (modelXml) {
    const ct = '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>';
    const rels = '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>';
    return Sculpt.zip([{ name: "[Content_Types].xml", data: enc(ct) }, { name: "_rels/.rels", data: enc(rels) }, { name: "3D/3dmodel.model", data: enc(modelXml) }]);
  };

  root.Sculpt = Sculpt;
  if (typeof module !== "undefined") module.exports = Sculpt;
})(typeof window !== "undefined" ? window : globalThis);
