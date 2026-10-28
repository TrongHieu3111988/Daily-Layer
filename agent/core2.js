// Sculpt Studio engine v2: chunked voxel field for high resolution, local remeshing,
// ZBrush-style brushes, mask channel, chunk-level undo, ray marching on the field.
// Export (printField/meshTet/colourParts/toPrint) is borrowed from core.js (window.Sculpt).
(function (root) {
  "use strict";
  const Base = root.Sculpt || (typeof require !== "undefined" ? require("./core.js") : null);
  const C = 16;                                 // samples per chunk edge

  function Sculpt2(N) { this.alloc(N); this.undo = []; this.redo = []; this.rec = null; }
  const P = Sculpt2.prototype;
  // borrow exporters and helpers from v1
  for (const k of ["printField", "meshTet", "colourParts", "toPrint", "printable", "idx", "pos"]) P[k] = Base.prototype[k];

  P.alloc = function (N) {
    this.N = N; this.h = 2 / (N - 1); this.clamp = 0.25;
    this.f = new Float32Array(N * N * N).fill(this.clamp);
    this.c = new Uint8Array(N * N * N);
    this.m = new Uint8Array(N * N * N);      // mask 0..255 (255 = fully protected)
    this.K = Math.ceil(N / C);               // chunks per axis (by sample index)
    this.dirty = new Set();
    this.markAll();
  };
  P.markAll = function () { for (let i = 0; i < this.K ** 3; i++) this.dirty.add(i); };
  P.chunkId = function (a, b, c) { return a + this.K * (b + this.K * c); };

  // ---------- starting shapes ----------
  P.reset = function (kind, color) {
    const N = this.N, cl = this.clamp;
    for (let k = 0; k < N; k++) for (let j = 0; j < N; j++) for (let i = 0; i < N; i++) {
      const x = -1 + i * this.h, y = -1 + j * this.h, z = -1 + k * this.h;
      let d;
      if (kind === "egg") { const yy = y + 0.05, sy = yy > 0 ? 0.62 : 0.5; d = (Math.hypot(x / 0.42, yy / sy, z / 0.42) - 1) * 0.42; }
      else if (kind === "pebble") d = (Math.hypot(x / 0.6, (y + 0.25) / 0.3, z / 0.5) - 1) * 0.3;
      else if (kind === "block") {
        const qx = Math.abs(x) - 0.32, qy = Math.abs(y + 0.1) - 0.32, qz = Math.abs(z) - 0.32;
        d = Math.hypot(Math.max(qx, 0), Math.max(qy, 0), Math.max(qz, 0)) + Math.min(Math.max(qx, qy, qz), 0) - 0.06;
      } else d = Math.hypot(x, y + 0.05, z) - 0.45;
      const id = i + N * (j + N * k);
      const b = i === 0 || j === 0 || k === 0 || i === N - 1 || j === N - 1 || k === N - 1;
      this.f[id] = b ? cl : Math.max(-cl, Math.min(cl, d));
      this.c[id] = color; this.m[id] = 0;
    }
    this.undo.length = 0; this.redo.length = 0; this.markAll();
  };

  // ---------- resolution (subdivide) ----------
  P.resample = function (N2) {
    const o = { N: this.N, f: this.f, c: this.c, m: this.m, h: this.h };
    this.alloc(N2);
    for (let k = 0; k < N2; k++) for (let j = 0; j < N2; j++) for (let i = 0; i < N2; i++) {
      const id = i + N2 * (j + N2 * k);
      if (i === 0 || j === 0 || k === 0 || i === N2 - 1 || j === N2 - 1 || k === N2 - 1) { this.f[id] = this.clamp; continue; }
      const gx = i * (o.N - 1) / (N2 - 1), gy = j * (o.N - 1) / (N2 - 1), gz = k * (o.N - 1) / (N2 - 1);
      this.f[id] = tri(o.f, o.N, gx, gy, gz);
      const ni = Math.round(gx) + o.N * (Math.round(gy) + o.N * Math.round(gz));
      this.c[id] = o.c[ni]; this.m[id] = o.m[ni];
    }
    this.undo.length = 0; this.redo.length = 0;
  };
  function tri(f, N, gx, gy, gz) {
    const i = Math.min(Math.max(Math.floor(gx), 0), N - 2), j = Math.min(Math.max(Math.floor(gy), 0), N - 2), k = Math.min(Math.max(Math.floor(gz), 0), N - 2);
    const u = gx - i, v = gy - j, w = gz - k, a = i + N * (j + N * k), s = N, s2 = N * N;
    const c00 = f[a] * (1 - u) + f[a + 1] * u, c10 = f[a + s] * (1 - u) + f[a + s + 1] * u;
    const c01 = f[a + s2] * (1 - u) + f[a + s2 + 1] * u, c11 = f[a + s2 + s] * (1 - u) + f[a + s2 + s + 1] * u;
    return (c00 * (1 - v) + c10 * v) * (1 - w) + (c01 * (1 - v) + c11 * v) * w;
  }
  P.sample = function (x, y, z) {
    const g = (this.N - 1) / 2;
    return tri(this.f, this.N, (x + 1) * g, (y + 1) * g, (z + 1) * g);
  };
  P.gradient = function (x, y, z) {
    const e = this.h * 0.75;
    const gx = this.sample(x + e, y, z) - this.sample(x - e, y, z);
    const gy = this.sample(x, y + e, z) - this.sample(x, y - e, z);
    const gz = this.sample(x, y, z + e) - this.sample(x, y, z - e);
    const L = Math.hypot(gx, gy, gz) || 1;
    return [gx / L, gy / L, gz / L];
  };

  // ray march: o, d (unit) in world; returns {p, n} or null
  P.raycast = function (o, d) {
    let t0 = 0, t1 = 1e9;
    for (let a = 0; a < 3; a++) {
      if (Math.abs(d[a]) < 1e-9) { if (o[a] < -1 || o[a] > 1) return null; continue; }
      let ta = (-1 - o[a]) / d[a], tb = (1 - o[a]) / d[a]; if (ta > tb) [ta, tb] = [tb, ta];
      t0 = Math.max(t0, ta); t1 = Math.min(t1, tb);
    }
    if (t0 > t1) return null;
    const step = this.h * 0.5;
    let t = t0 + this.h, prevT = t, prev = this.sample(o[0] + d[0] * t, o[1] + d[1] * t, o[2] + d[2] * t);
    for (t = t + step; t < t1; t += Math.max(step, Math.min(Math.abs(prev) * 0.7, this.h * 3))) {
      const v = this.sample(o[0] + d[0] * t, o[1] + d[1] * t, o[2] + d[2] * t);
      if (v < 0 && prev >= 0) {
        let lo = prevT, hi = t;
        for (let it = 0; it < 12; it++) { const mid = (lo + hi) / 2; const vm = this.sample(o[0] + d[0] * mid, o[1] + d[1] * mid, o[2] + d[2] * mid); if (vm < 0) hi = mid; else lo = mid; }
        const p = [o[0] + d[0] * hi, o[1] + d[1] * hi, o[2] + d[2] * hi];
        return { p, n: this.gradient(p[0], p[1], p[2]), t: hi };
      }
      prev = v; prevT = t;
    }
    return null;
  };

  // ---------- undo by chunk ----------
  P.beginStroke = function () { this.rec = new Map(); };
  P.endStroke = function () {
    if (this.rec && this.rec.size) { this.undo.push(this.rec); if (this.undo.length > 30) this.undo.shift(); this.redo.length = 0; }
    this.rec = null;
  };
  P.cancelStroke = function () {           // revert the stroke in progress
    if (!this.rec) return;
    this.swapRecord(this.rec); this.rec = null;
  };
  P.saveChunk = function (cid) {
    if (!this.rec || this.rec.has(cid)) return;
    const [ox, oy, oz] = this.chunkOrigin(cid), N = this.N;
    const ex = Math.min(C, N - ox), ey = Math.min(C, N - oy), ez = Math.min(C, N - oz), n = ex * ey * ez;
    const f = new Float32Array(n), c = new Uint8Array(n), m = new Uint8Array(n);
    let q = 0;
    for (let k = 0; k < ez; k++) for (let j = 0; j < ey; j++) { const base = ox + N * (oy + j + N * (oz + k)); for (let i = 0; i < ex; i++, q++) { f[q] = this.f[base + i]; c[q] = this.c[base + i]; m[q] = this.m[base + i]; } }
    this.rec.set(cid, { f, c, m });
  };
  P.chunkOrigin = function (cid) { const K = this.K; return [(cid % K) * C, (Math.floor(cid / K) % K) * C, Math.floor(cid / (K * K)) * C]; };
  P.swapRecord = function (rec) {
    const N = this.N;
    for (const [cid, d] of rec) {
      const [ox, oy, oz] = this.chunkOrigin(cid);
      const ex = Math.min(C, N - ox), ey = Math.min(C, N - oy), ez = Math.min(C, N - oz);
      let q = 0;
      for (let k = 0; k < ez; k++) for (let j = 0; j < ey; j++) {
        const base = ox + N * (oy + j + N * (oz + k));
        for (let i = 0; i < ex; i++, q++) {
          const id = base + i;
          let t = this.f[id]; this.f[id] = d.f[q]; d.f[q] = t;
          t = this.c[id]; this.c[id] = d.c[q]; d.c[q] = t;
          t = this.m[id]; this.m[id] = d.m[q]; d.m[q] = t;
        }
      }
      this.markSampleBox(ox, oy, oz, ox + ex - 1, oy + ey - 1, oz + ez - 1);
    }
  };
  P.doUndo = function () { const r = this.undo.pop(); if (!r) return false; this.swapRecord(r); this.redo.push(r); return true; };
  P.doRedo = function () { const r = this.redo.pop(); if (!r) return false; this.swapRecord(r); this.undo.push(r); return true; };

  // mark chunks whose cells touch samples in [i0..i1]
  P.markSampleBox = function (i0, j0, k0, i1, j1, k1) {
    const K = this.K;
    const a0 = Math.max(0, Math.floor((i0 - 1) / C)), a1 = Math.min(K - 1, Math.floor(i1 / C));
    const b0 = Math.max(0, Math.floor((j0 - 1) / C)), b1 = Math.min(K - 1, Math.floor(j1 / C));
    const c0 = Math.max(0, Math.floor((k0 - 1) / C)), c1 = Math.min(K - 1, Math.floor(k1 / C));
    for (let c = c0; c <= c1; c++) for (let b = b0; b <= b1; b++) for (let a = a0; a <= a1; a++) this.dirty.add(this.chunkId(a, b, c));
  };

  // ---------- brushes ----------
  const fall = t => { const u = 1 - t * t; return u * u; };        // smooth falloff, 1 at centre, 0 at edge
  // iterate samples within radius R of p; cb(id, x, y, z, w) where w = falloff
  P.region = function (p, R, cb) {
    const N = this.N, h = this.h;
    const i0 = Math.max(1, Math.floor((p[0] - R + 1) / h)), i1 = Math.min(N - 2, Math.ceil((p[0] + R + 1) / h));
    const j0 = Math.max(1, Math.floor((p[1] - R + 1) / h)), j1 = Math.min(N - 2, Math.ceil((p[1] + R + 1) / h));
    const k0 = Math.max(1, Math.floor((p[2] - R + 1) / h)), k1 = Math.min(N - 2, Math.ceil((p[2] + R + 1) / h));
    if (i0 > i1 || j0 > j1 || k0 > k1) return;
    if (this.rec) {
      const a0 = Math.floor(i0 / C), a1 = Math.floor(i1 / C), b0 = Math.floor(j0 / C), b1 = Math.floor(j1 / C), c0 = Math.floor(k0 / C), c1 = Math.floor(k1 / C);
      for (let c = c0; c <= c1; c++) for (let b = b0; b <= b1; b++) for (let a = a0; a <= a1; a++) this.saveChunk(this.chunkId(a, b, c));
    }
    for (let k = k0; k <= k1; k++) {
      const z = -1 + k * h, dz = z - p[2];
      for (let j = j0; j <= j1; j++) {
        const y = -1 + j * h, dy = y - p[1];
        let id = i0 + N * (j + N * k);
        for (let i = i0; i <= i1; i++, id++) {
          const x = -1 + i * h, dx = x - p[0];
          const d = Math.sqrt(dx * dx + dy * dy + dz * dz);
          if (d >= R) continue;
          cb(id, x, y, z, fall(d / R));
        }
      }
    }
    this.markSampleBox(i0, j0, k0, i1, j1, k1);
  };

  /* op: {tool, p, n, r, s (0..1), invert, color, viewDir}
     Field convention: negative inside. Moving the surface outward = lowering f. */
  P.brush = function (op) {
    const { tool, p, r } = op, n = op.n || [0, 1, 0], h = this.h, cl = this.clamp;
    const sgn = op.invert ? -1 : 1, s = op.s, f = this.f, mk = this.m;
    const keep = id => 1 - mk[id] / 255;
    const amt = s * r * 0.22;                       // per-dab displacement in world units
    if (tool === "standard") {                       // push along the hit normal
      const src = this.copyBox(p, r * 1.4);
      this.region(p, r, (id, x, y, z, w) => {
        const a = sgn * amt * w * keep(id);
        f[id] = clampv(src(x - n[0] * a, y - n[1] * a, z - n[2] * a), cl);
      });
    } else if (tool === "inflate") {                 // grow along the local surface normal
      this.region(p, r, (id, x, y, z, w) => { f[id] = clampv(f[id] - sgn * amt * 0.8 * w * keep(id), cl); });
    } else if (tool === "clay") {                    // flat-topped layers of clay
      const off = amt * 1.2, px = p[0] + n[0] * off * sgn, py = p[1] + n[1] * off * sgn, pz = p[2] + n[2] * off * sgn;
      this.region(p, r, (id, x, y, z, w) => {
        const plane = (x - px) * n[0] + (y - py) * n[1] + (z - pz) * n[2];
        const target = sgn > 0 ? Math.min(f[id], plane) : Math.max(f[id], -plane);
        f[id] = clampv(f[id] + (target - f[id]) * Math.min(1, w * 1.6) * s * keep(id), cl);
      });
    } else if (tool === "flatten") {                 // trim everything above a plane through the hit
      const px = p[0] - n[0] * amt * 0.3, py = p[1] - n[1] * amt * 0.3, pz = p[2] - n[2] * amt * 0.3;
      this.region(p, r, (id, x, y, z, w) => {
        const plane = (x - px) * n[0] + (y - py) * n[1] + (z - pz) * n[2];
        const target = Math.max(f[id], plane);
        f[id] = clampv(f[id] + (target - f[id]) * Math.min(1, w * 1.5) * s * keep(id), cl);
      });
    } else if (tool === "smooth") {
      const N = this.N, s1 = N, s2 = N * N;
      const tmp = [];
      this.region(p, r, (id, x, y, z, w) => {
        const avg = (f[id - 1] + f[id + 1] + f[id - s1] + f[id + s1] + f[id - s2] + f[id + s2]) / 6;
        tmp.push(id, f[id] + (avg - f[id]) * Math.min(1, w * (0.4 + s)) * keep(id));
      });
      for (let q = 0; q < tmp.length; q += 2) f[tmp[q]] = tmp[q + 1];
    } else if (tool === "pinch") {                   // pull material towards the brush centre line
      const src = this.copyBox(p, r * 1.3);
      this.region(p, r, (id, x, y, z, w) => {
        let dx = x - p[0], dy = y - p[1], dz = z - p[2];
        const dn = dx * n[0] + dy * n[1] + dz * n[2]; dx -= dn * n[0]; dy -= dn * n[1]; dz -= dn * n[2];
        const a = sgn * 0.35 * s * w * keep(id);
        f[id] = clampv(src(x + dx * a, y + dy * a, z + dz * a), cl);
      });
    } else if (tool === "dam") {                     // Dam Standard: carve a sharp crease and pinch it
      const rr = r * 0.6;
      this.region(p, rr, (id, x, y, z, w) => { f[id] = clampv(f[id] + sgn * amt * 0.9 * w * w * keep(id), cl); });
      this.brush({ tool: "pinch", p, n, r, s: s * 0.8, invert: op.invert });
    } else if (tool === "mask") {
      this.region(p, r, (id, x, y, z, w) => {
        if (f[id] > -3 * h) mk[id] = op.invert ? Math.max(0, mk[id] - 255 * w * s * 2) : Math.min(255, mk[id] + 255 * w * s * 2);
      });
    } else if (tool === "paint") {
      this.region(p, r, (id, x, y, z, w) => { if (f[id] > -3.5 * h && w > 0.15 && keep(id) > 0.5) this.c[id] = op.color; });
    } else if (tool === "blob") {                    // add a ball (used by Eyes)
      const k = Math.max(r * 0.35, 1.5 * h);
      this.region(p, r + 2 * h, (id, x, y, z) => {
        const d = Math.hypot(x - p[0], y - p[1], z - p[2]) - r;
        const hh = Math.max(k - Math.abs(f[id] - d), 0) / k;
        const nv = Math.min(f[id], d) - hh * hh * k * 0.25;
        f[id] = clampv(nv, cl);
        if (d < h) this.c[id] = op.color;
      });
    }
  };
  function clampv(v, cl) { return v < -cl ? -cl : v > cl ? cl : v; }

  // snapshot a box of the field, return a trilinear sampler over it (so brushes read pre-dab values)
  P.copyBox = function (p, R) {
    const N = this.N, h = this.h, g = (N - 1) / 2;
    const i0 = Math.max(0, Math.floor((p[0] - R + 1) / h) - 1), i1 = Math.min(N - 1, Math.ceil((p[0] + R + 1) / h) + 1);
    const j0 = Math.max(0, Math.floor((p[1] - R + 1) / h) - 1), j1 = Math.min(N - 1, Math.ceil((p[1] + R + 1) / h) + 1);
    const k0 = Math.max(0, Math.floor((p[2] - R + 1) / h) - 1), k1 = Math.min(N - 1, Math.ceil((p[2] + R + 1) / h) + 1);
    const W = i1 - i0 + 1, H = j1 - j0 + 1, D = k1 - k0 + 1, box = new Float32Array(W * H * D);
    for (let k = 0; k < D; k++) for (let j = 0; j < H; j++) { const b = i0 + N * (j0 + j + N * (k0 + k)); box.set(this.f.subarray(b, b + W), W * (j + H * k)); }
    const f = this.f, cl = this.clamp;
    return (x, y, z) => {
      const gx = (x + 1) * g - i0, gy = (y + 1) * g - j0, gz = (z + 1) * g - k0;
      if (gx < 0 || gy < 0 || gz < 0 || gx > W - 1 || gy > H - 1 || gz > D - 1) return this.sample(x, y, z);
      const i = Math.min(Math.floor(gx), W - 2), j = Math.min(Math.floor(gy), H - 2), k = Math.min(Math.floor(gz), D - 2);
      const u = gx - i, v = gy - j, w = gz - k, a = i + W * (j + H * k), s = W, s2 = W * H;
      const c00 = box[a] * (1 - u) + box[a + 1] * u, c10 = box[a + s] * (1 - u) + box[a + s + 1] * u;
      const c01 = box[a + s2] * (1 - u) + box[a + s2 + 1] * u, c11 = box[a + s2 + s] * (1 - u) + box[a + s2 + s + 1] * u;
      return (c00 * (1 - v) + c10 * v) * (1 - w) + (c01 * (1 - v) + c11 * v) * w;
    };
  };

  // Move: drag a region; uses the field as it was when the drag started
  // grabs: [{p, sx}] where sx = 1 or -1 (mirror the drag in x)
  P.moveBegin = function (grabs, r) { this.moveState = grabs.map(g => ({ p: g.p, sx: g.sx, r, src: this.copyBox(g.p, r * 2.6) })); };
  P.moveTo = function (delta) {
    if (!this.moveState) return;
    for (const st of this.moveState) this.moveOne(st, [delta[0] * st.sx, delta[1], delta[2]]);
  };
  P.moveOne = function (st, delta) {
    const { p, r, src } = st, f = this.f, mk = this.m, cl = this.clamp;
    const reach = r + Math.hypot(delta[0], delta[1], delta[2]);
    const c = [p[0] + delta[0] * 0.5, p[1] + delta[1] * 0.5, p[2] + delta[2] * 0.5];
    this.region(c, reach, (id, x, y, z) => {
      // weight by distance from the displaced grab point, sample the original field backwards
      const dx = x - p[0] - delta[0], dy = y - p[1] - delta[1], dz = z - p[2] - delta[2];
      const d = Math.sqrt(dx * dx + dy * dy + dz * dz) / r;
      const w = (d < 1 ? fall(d) : 0) * (1 - mk[id] / 255);
      f[id] = clampv(src(x - delta[0] * w, y - delta[1] * w, z - delta[2] * w), cl);
    });
  };
  P.moveEnd = function () { this.moveState = null; };

  P.clearMask = function () { this.beginStroke(); for (let cid = 0; cid < this.K ** 3; cid++) this.saveChunk(cid); this.m.fill(0); this.endStroke(); this.markAll(); };
  P.invertMask = function () { this.beginStroke(); for (let cid = 0; cid < this.K ** 3; cid++) this.saveChunk(cid); for (let i = 0; i < this.m.length; i++) this.m[i] = this.f[i] < 0.02 ? 255 - this.m[i] : 0; this.endStroke(); this.markAll(); };

  // ---------- chunk meshing (surface nets) with field-gradient normals ----------
  // returns {pos, nor, lab, msk, idx} for chunk cid
  P.meshChunk = function (cid) {
    const N = this.N, f = this.f, h = this.h, M = N - 1;
    const [ox, oy, oz] = this.chunkOrigin(cid);
    // cells owned: [ox, min(ox+C, M)); we also need cells at ox-1 for quads
    const x0 = Math.max(ox - 1, 0), y0 = Math.max(oy - 1, 0), z0 = Math.max(oz - 1, 0);
    const x1 = Math.min(ox + C, M), y1 = Math.min(oy + C, M), z1 = Math.min(oz + C, M);
    const W = x1 - x0, H = y1 - y0, D = z1 - z0;
    if (W <= 0 || H <= 0 || D <= 0) return null;
    const vid = new Int32Array(W * H * D).fill(-1);
    const pos = [], nor = [], lab = [], msk = [];
    const v = new Float32Array(8);
    const off = [0, 1, N, N + 1, N * N, N * N + 1, N * N + N, N * N + N + 1];
    const cx = [0, 1, 0, 1, 0, 1, 0, 1], cy = [0, 0, 1, 1, 0, 0, 1, 1], cz = [0, 0, 0, 0, 1, 1, 1, 1];
    const E = [[0, 1], [2, 3], [4, 5], [6, 7], [0, 2], [1, 3], [4, 6], [5, 7], [0, 4], [1, 5], [2, 6], [3, 7]];
    for (let k = z0; k < z1; k++) for (let j = y0; j < y1; j++) for (let i = x0; i < x1; i++) {
      const a = i + N * (j + N * k);
      let inside = 0;
      for (let q = 0; q < 8; q++) { v[q] = f[a + off[q]]; if (v[q] < 0) inside++; }
      if (inside === 0 || inside === 8) continue;
      let sx = 0, sy = 0, sz = 0, n = 0;
      for (let e = 0; e < 12; e++) {
        const A = E[e][0], B = E[e][1];
        if ((v[A] < 0) === (v[B] < 0)) continue;
        const t = v[A] / (v[A] - v[B]);
        sx += cx[A] + t * (cx[B] - cx[A]); sy += cy[A] + t * (cy[B] - cy[A]); sz += cz[A] + t * (cz[B] - cz[A]); n++;
      }
      const px = -1 + (i + sx / n) * h, py = -1 + (j + sy / n) * h, pz = -1 + (k + sz / n) * h;
      vid[(i - x0) + W * ((j - y0) + H * (k - z0))] = pos.length / 3;
      pos.push(px, py, pz);
      const g = this.gradient(px, py, pz); nor.push(g[0], g[1], g[2]);
      let best = 0, bv = -1e9; for (let q = 0; q < 8; q++) if (v[q] < 0 && v[q] > bv) { bv = v[q]; best = q; }
      lab.push(this.c[a + off[best]]);
      let mm = 0; for (let q = 0; q < 8; q++) mm = Math.max(mm, this.m[a + off[q]]);
      msk.push(mm);
    }
    const idx = [];
    const cell = (i, j, k) => (i < x0 || j < y0 || k < z0 || i >= x1 || j >= y1 || k >= z1) ? -1 : vid[(i - x0) + W * ((j - y0) + H * (k - z0))];
    const ex1 = Math.min(ox + C, M), ey1 = Math.min(oy + C, M), ez1 = Math.min(oz + C, M);
    const push = (q0, q1, q2, q3, flip) => {
      if (q0 < 0 || q1 < 0 || q2 < 0 || q3 < 0) return;
      if (flip) idx.push(q0, q1, q2, q0, q2, q3); else idx.push(q0, q2, q1, q0, q3, q2);
    };
    // edges owned by this chunk: start sample in [ox, ex1) x [oy, ey1) x [oz, ez1)
    for (let k = oz; k < ez1; k++) for (let j = oy; j < ey1; j++) for (let i = ox; i < ex1; i++) {
      const a = i + N * (j + N * k), inA = f[a] < 0;
      if (j >= 1 && k >= 1 && (f[a + 1] < 0) !== inA) push(cell(i, j - 1, k - 1), cell(i, j, k - 1), cell(i, j, k), cell(i, j - 1, k), inA);
      if (i >= 1 && k >= 1 && (f[a + N] < 0) !== inA) push(cell(i - 1, j, k - 1), cell(i - 1, j, k), cell(i, j, k), cell(i, j, k - 1), inA);
      if (i >= 1 && j >= 1 && (f[a + N * N] < 0) !== inA) push(cell(i - 1, j - 1, k), cell(i, j - 1, k), cell(i, j, k), cell(i - 1, j, k), inA);
    }
    return { pos: new Float32Array(pos), nor: new Float32Array(nor), lab: new Uint8Array(lab), msk: new Uint8Array(msk), idx: new Uint32Array(idx) };
  };

  // ---------- compact save (Int8 field + labels), for autosave ----------
  P.serialize = function () {
    const n = this.f.length, out = new Uint8Array(4 + 2 * n);
    new DataView(out.buffer).setUint32(0, this.N, true);
    for (let i = 0; i < n; i++) out[4 + i] = Math.max(-127, Math.min(127, Math.round(this.f[i] / this.clamp * 127))) & 255;
    out.set(this.c, 4 + n);
    return out;
  };
  P.deserialize = function (u8) {
    const N = new DataView(u8.buffer, u8.byteOffset).getUint32(0, true), n = N * N * N;
    if (u8.length !== 4 + 2 * n || N < 32 || N > 256) return false;
    this.alloc(N);
    for (let i = 0; i < n; i++) this.f[i] = ((u8[4 + i] << 24 >> 24) / 127) * this.clamp;
    this.c.set(u8.subarray(4 + n, 4 + 2 * n));
    return true;
  };

  root.Sculpt2 = Sculpt2;
  if (typeof module !== "undefined") module.exports = Sculpt2;
})(typeof window !== "undefined" ? window : globalThis);
