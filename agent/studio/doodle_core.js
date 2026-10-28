// Doodle Puff core: turns a child's flat drawing into a puffy, print-ready 3D piece.
// Runs in the browser (window.Doodle) and in node (module.exports) so the shop agent can test it.
//
// Input: a label raster (0 = paper, 1..K = crayon colours) and a bump raster (mm of raised relief for
// crayon lines and sticker eyes), both W x H. Output: a closed mesh in millimetres (z up, flat back on z = 0)
// with one colour per triangle, plus STL / OBJ+MTL / 3MF writers.
(function (root) {
  "use strict";

  // ---------- raster helpers ----------
  // exact Euclidean distance transform (Felzenszwalb & Huttenlocher), distances in pixels to the nearest `feat` pixel
  function edt(feat, W, H) {
    const INF = 1e20, g = new Float64Array(W * H);
    for (let i = 0; i < W * H; i++) g[i] = feat[i] ? 0 : INF;
    const n = Math.max(W, H), f = new Float64Array(n), d = new Float64Array(n), v = new Int32Array(n), z = new Float64Array(n + 1);
    function pass(len) {
      let k = 0; v[0] = 0; z[0] = -INF; z[1] = INF;
      for (let q = 1; q < len; q++) {
        let s;
        while (true) { const p = v[k]; s = ((f[q] + q * q) - (f[p] + p * p)) / (2 * q - 2 * p); if (s <= z[k]) { k--; if (k < 0) { k = 0; break; } } else break; }
        k++; v[k] = q; z[k] = s; z[k + 1] = INF;
      }
      k = 0;
      for (let q = 0; q < len; q++) { while (z[k + 1] < q) k++; const p = v[k]; d[q] = (q - p) * (q - p) + f[p]; }
    }
    for (let x = 0; x < W; x++) { for (let y = 0; y < H; y++) f[y] = g[x + W * y]; pass(H); for (let y = 0; y < H; y++) g[x + W * y] = d[y]; }
    for (let y = 0; y < H; y++) { for (let x = 0; x < W; x++) f[x] = g[x + W * y]; pass(W); for (let x = 0; x < W; x++) g[x + W * y] = d[x]; }
    const out = new Float32Array(W * H); for (let i = 0; i < W * H; i++) out[i] = Math.sqrt(g[i]); return out;
  }
  function boxBlur(a, W, H, r, passes) {
    let src = Float32Array.from(a), tmp = new Float32Array(W * H);
    const win = 2 * r + 1;
    for (let p = 0; p < passes; p++) {
      for (let y = 0; y < H; y++) { let s = 0; const o = y * W;
        for (let x = -r; x <= r; x++) s += src[o + Math.min(W - 1, Math.max(0, x))];
        for (let x = 0; x < W; x++) { tmp[o + x] = s / win; s += src[o + Math.min(W - 1, x + r + 1)] - src[o + Math.max(0, x - r)]; } }
      for (let x = 0; x < W; x++) { let s = 0;
        for (let y = -r; y <= r; y++) s += tmp[x + W * Math.min(H - 1, Math.max(0, y))];
        for (let y = 0; y < H; y++) { src[x + W * y] = s / win; s += tmp[x + W * Math.min(H - 1, y + r + 1)] - tmp[x + W * Math.max(0, y - r)]; } }
    }
    return src;
  }
  function bilinear(a, W, H, x, y) {
    x = Math.min(Math.max(x, 0), W - 1.001); y = Math.min(Math.max(y, 0), H - 1.001);
    const i = Math.floor(x), j = Math.floor(y), u = x - i, v = y - j, o = i + W * j;
    return (a[o] * (1 - u) + a[o + 1] * u) * (1 - v) + (a[o + W] * (1 - u) + a[o + W + 1] * u) * v;
  }
  // connected regions of `mask` (8-neighbour); returns {comp: Int32Array, sizes: []}
  function components(mask, W, H) {
    const comp = new Int32Array(W * H).fill(-1), sizes = [], st = new Int32Array(W * H);
    for (let s = 0; s < W * H; s++) {
      if (!mask[s] || comp[s] >= 0) continue;
      const id = sizes.length; let top = 0, n = 0; st[top++] = s; comp[s] = id;
      while (top) {
        const p = st[--top]; n++; const x = p % W, y = (p - x) / W;
        for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
          const xx = x + dx, yy = y + dy; if (xx < 0 || yy < 0 || xx >= W || yy >= H) continue;
          const q = xx + W * yy; if (mask[q] && comp[q] < 0) { comp[q] = id; st[top++] = q; }
        }
      }
      sizes.push(n);
    }
    return { comp, sizes };
  }

  // ---------- the shape: what will be printed ----------
  // opts: fillLabel (colour for empty areas enclosed by lines), loop (keyring tab), sizeMM
  function shape(lab0, bump0, W, H, opts) {
    const lab = Uint8Array.from(lab0), bump = Float32Array.from(bump0);
    // paper enclosed by crayon lines becomes part of the piece, in the chosen body colour
    const seen = new Uint8Array(W * H), st = new Int32Array(W * H); let top = 0;
    const push = p => { if (!seen[p] && lab[p] === 0) { seen[p] = 1; st[top++] = p; } };
    for (let x = 0; x < W; x++) { push(x); push(x + W * (H - 1)); }
    for (let y = 0; y < H; y++) { push(W * y); push(W - 1 + W * y); }
    while (top) { const p = st[--top], x = p % W, y = (p - x) / W;
      if (x > 0) push(p - 1); if (x < W - 1) push(p + 1); if (y > 0) push(p - W); if (y < H - 1) push(p + W); }
    let filled = 0;
    for (let p = 0; p < W * H; p++) if (lab[p] === 0 && !seen[p]) { lab[p] = opts.fillLabel; filled++; }
    // one solid piece: keep the biggest connected drawing, report the rest
    let inside = new Uint8Array(W * H); for (let p = 0; p < W * H; p++) inside[p] = lab[p] > 0 ? 1 : 0;
    let { comp, sizes } = components(inside, W, H);
    if (!sizes.length) return null;
    let best = 0; sizes.forEach((s, i) => { if (s > sizes[best]) best = i; });
    const dropped = sizes.filter((s, i) => i !== best && s > 40).length;
    for (let p = 0; p < W * H; p++) if (inside[p] && comp[p] !== best) { inside[p] = 0; lab[p] = 0; bump[p] = 0; }
    // bounding box and scale
    let x0 = W, y0 = H, x1 = -1, y1 = -1;
    for (let p = 0; p < W * H; p++) if (inside[p]) { const x = p % W, y = (p - x) / W; if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
    let pxmm = opts.sizeMM / Math.max(x1 - x0 + 1, y1 - y0 + 1);
    // keyring tab: a ring above the highest point of the drawing
    if (opts.loop) {
      const ro = 4.2 / pxmm, ri = 2.1 / pxmm;
      // attach at the highest point (an ear tip, the top of a head...), sliding the ring down until it bites ~2 mm in
      let cx = x0, best = H;
      for (let x = x0; x <= x1; x++) for (let y = y0; y <= y1; y++) if (inside[x + W * y]) { if (y < best || (y === best && Math.abs(x - (x0 + x1) / 2) < Math.abs(cx - (x0 + x1) / 2))) { best = y; cx = x; } break; }
      const need = (2.0 / pxmm) * (2.4 / pxmm);
      let cy = best - ro;
      for (; cy < best + ro; cy += 0.5) {
        let ov = 0;
        for (let y = Math.floor(cy); y <= cy + ro; y++) for (let x = Math.floor(cx - ro); x <= cx + ro; x++) {
          if (x < 0 || y < 0 || x >= W || y >= H) continue; const r = Math.hypot(x - cx, y - cy);
          if (r <= ro && r >= ri && inside[x + W * y]) ov++;
        }
        if (ov >= need) break;
      }
      for (let y = Math.floor(cy - ro - 1); y <= cy + ro + 1; y++) for (let x = Math.floor(cx - ro - 1); x <= cx + ro + 1; x++) {
        if (x < 0 || y < 0 || x >= W || y >= H) continue;
        const r = Math.hypot(x - cx, y - cy), p = x + W * y;
        if (r <= ro && r >= ri && !inside[p]) { inside[p] = 1; lab[p] = opts.fillLabel; bump[p] = 0; }
        if (r < ri) { inside[p] = 0; lab[p] = 0; bump[p] = 0; }
      }
      y0 = Math.max(0, Math.floor(cy - ro - 1));
      pxmm = opts.sizeMM / Math.max(x1 - x0 + 1, y1 - y0 + 1);
    }
    return { lab, bump, inside, W, H, x0, y0, x1, y1, pxmm, dropped, filled };
  }

  // ---------- marching tetrahedra on a box grid: closed, edge-manifold ----------
  function meshTet(field, NX, NY, NZ, org, v) {
    const eps = 0.03 * v;
    const F = Float32Array.from(field, a => (a < 0 ? Math.min(a, -eps) : Math.max(a, eps)));
    const corner = []; for (let c = 0; c < 8; c++) corner.push([(c & 1), (c >> 1) & 1, (c >> 2) & 1]);
    const tets = [[0, 1, 3, 7], [0, 3, 2, 7], [0, 2, 6, 7], [0, 6, 4, 7], [0, 4, 5, 7], [0, 5, 1, 7]];
    const NT = NX * NY * NZ, pos = [], idx = [], vmap = new Map(), ids = new Int32Array(8);
    const P3 = id => { const i = id % NX, j = Math.floor(id / NX) % NY, k = Math.floor(id / (NX * NY)); return [org[0] + i * v, org[1] + j * v, org[2] + k * v]; };
    function vert(a, b) {
      const key = a < b ? a * NT + b : b * NT + a; let r = vmap.get(key);
      if (r !== undefined) return r;
      const t = F[a] / (F[a] - F[b]), A = P3(a), B = P3(b);
      r = pos.length / 3; pos.push(A[0] + t * (B[0] - A[0]), A[1] + t * (B[1] - A[1]), A[2] + t * (B[2] - A[2]));
      vmap.set(key, r); return r;
    }
    function tri(p, q, r, inId, outId) {
      const ux = pos[3 * q] - pos[3 * p], uy = pos[3 * q + 1] - pos[3 * p + 1], uz = pos[3 * q + 2] - pos[3 * p + 2];
      const vx = pos[3 * r] - pos[3 * p], vy = pos[3 * r + 1] - pos[3 * p + 1], vz = pos[3 * r + 2] - pos[3 * p + 2];
      const nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx;
      const a = P3(inId), b = P3(outId);
      if (nx * (b[0] - a[0]) + ny * (b[1] - a[1]) + nz * (b[2] - a[2]) >= 0) idx.push(p, q, r); else idx.push(p, r, q);
    }
    for (let k = 0; k < NZ - 1; k++) for (let j = 0; j < NY - 1; j++) for (let i = 0; i < NX - 1; i++) {
      let any = 0, all = 1;
      for (let c = 0; c < 8; c++) { const o = corner[c]; ids[c] = (i + o[0]) + NX * ((j + o[1]) + NY * (k + o[2])); if (F[ids[c]] < 0) any = 1; else all = 0; }
      if (!any || all) continue;
      for (const T of tets) {
        const ins = [], outs = [];
        for (const c of T) (F[ids[c]] < 0 ? ins : outs).push(ids[c]);
        if (ins.length === 0 || ins.length === 4) continue;
        if (ins.length === 1) tri(vert(ins[0], outs[0]), vert(ins[0], outs[1]), vert(ins[0], outs[2]), ins[0], outs[0]);
        else if (ins.length === 3) tri(vert(outs[0], ins[0]), vert(outs[0], ins[1]), vert(outs[0], ins[2]), ins[0], outs[0]);
        else { const a = vert(ins[0], outs[0]), b = vert(ins[0], outs[1]), c = vert(ins[1], outs[1]), d = vert(ins[1], outs[0]); tri(a, b, c, ins[0], outs[0]); tri(a, c, d, ins[0], outs[0]); }
      }
    }
    return { pos: new Float32Array(pos), idx: new Uint32Array(idx) };
  }
  function neighbours(idx, nv) {
    const sets = Array.from({ length: nv }, () => new Set());
    for (let t = 0; t < idx.length; t += 3) for (let e = 0; e < 3; e++) { const a = idx[t + e], b = idx[t + (e + 1) % 3]; sets[a].add(b); sets[b].add(a); }
    return sets.map(s => Int32Array.from(s));
  }
  // volume-preserving smoothing; the flat back stays flat
  function taubin(pos, nb, iters) {
    const nv = pos.length / 3, tmp = new Float32Array(pos.length);
    for (let it = 0; it < iters; it++) for (const k of [0.5, -0.53]) {
      for (let v = 0; v < nv; v++) {
        const n = nb[v]; if (!n.length || pos[3 * v + 2] < 0.02) { tmp[3 * v] = pos[3 * v]; tmp[3 * v + 1] = pos[3 * v + 1]; tmp[3 * v + 2] = pos[3 * v + 2]; continue; }
        let sx = 0, sy = 0, sz = 0; for (const u of n) { sx += pos[3 * u]; sy += pos[3 * u + 1]; sz += pos[3 * u + 2]; }
        tmp[3 * v] = pos[3 * v] + k * (sx / n.length - pos[3 * v]); tmp[3 * v + 1] = pos[3 * v + 1] + k * (sy / n.length - pos[3 * v + 1]); tmp[3 * v + 2] = Math.max(0, pos[3 * v + 2] + k * (sz / n.length - pos[3 * v + 2]));
      }
      pos.set(tmp);
    }
  }
  // split triangles exactly along the line where two colours meet (crisp, smooth borders; stays closed)
  function cutColours(pos, idx, sh, L) {
    const nv = pos.length / 3, w = new Int32Array(nv);
    for (let v = 0; v < nv; v++) { let b = 0; for (let l = 1; l < L; l++) if (sh[v * L + l] > sh[v * L + b]) b = l; w[v] = b; }
    const P = Array.from(pos), I = [], lab = [], emap = new Map();
    function edgePt(p, q) {
      const a = Math.min(p, q), b = Math.max(p, q), key = a * nv + b; let r = emap.get(key);
      if (r !== undefined) return r;
      const wa = w[a], wb = w[b], da = sh[a * L + wa] - sh[a * L + wb], db = sh[b * L + wa] - sh[b * L + wb];
      let t = da - db > 1e-9 ? da / (da - db) : 0.5; t = Math.min(0.97, Math.max(0.03, t));
      r = P.length / 3; P.push(P[3 * a] + t * (P[3 * b] - P[3 * a]), P[3 * a + 1] + t * (P[3 * b + 1] - P[3 * a + 1]), P[3 * a + 2] + t * (P[3 * b + 2] - P[3 * a + 2]));
      emap.set(key, r); return r;
    }
    for (let t = 0; t < idx.length; t += 3) {
      const a = idx[t], b = idx[t + 1], c = idx[t + 2], la = w[a], lb = w[b], lc = w[c];
      if (la === lb && lb === lc) { I.push(a, b, c); lab.push(la); continue; }
      if (la !== lb && lb !== lc && la !== lc) {
        const mab = edgePt(a, b), mbc = edgePt(b, c), mca = edgePt(c, a), ctr = P.length / 3;
        P.push((P[3 * mab] + P[3 * mbc] + P[3 * mca]) / 3, (P[3 * mab + 1] + P[3 * mbc + 1] + P[3 * mca + 1]) / 3, (P[3 * mab + 2] + P[3 * mbc + 2] + P[3 * mca + 2]) / 3);
        for (const [i, mi, mo, l] of [[a, mab, mca, la], [b, mbc, mab, lb], [c, mca, mbc, lc]]) { I.push(i, mi, ctr, i, ctr, mo); lab.push(l, l); }
        continue;
      }
      let i, j, k, li, lj;
      if (la === lb) { i = c; j = a; k = b; li = lc; lj = la; } else if (lb === lc) { i = a; j = b; k = c; li = la; lj = lb; } else { i = b; j = c; k = a; li = lb; lj = lc; }
      const mij = edgePt(i, j), mik = edgePt(i, k);
      I.push(i, mij, mik, mij, j, k, mij, k, mik); lab.push(li, lj, lj);
    }
    return { pos: new Float32Array(P), idx: new Uint32Array(I), lab: new Uint8Array(lab) };
  }
  function check(idx) {
    const m = new Map();
    for (let t = 0; t < idx.length; t += 3) for (let e = 0; e < 3; e++) { const a = idx[t + e], b = idx[t + (e + 1) % 3]; const k = a < b ? a * 4294967296 + b : b * 4294967296 + a; m.set(k, (m.get(k) || 0) + 1); }
    let bad = 0; for (const v of m.values()) if (v !== 2) bad++;
    return { triangles: idx.length / 3, badEdges: bad, watertight: bad === 0 };
  }

  // ---------- drawing -> puffy model ----------
  // opts: sizeMM (longest side), puff (extra mm of dome), edge (mm thickness at the outline), fillLabel, loop, quality (voxels across)
  function build(lab0, bump0, W, H, opts) {
    opts = Object.assign({ sizeMM: 80, puff: 5, edge: 2.4, fillLabel: 1, loop: false, quality: 200 }, opts);
    const S = shape(lab0, bump0, W, H, opts);
    if (!S) return null;
    const { lab, inside, pxmm } = S;
    // signed distance to the outline, in mm (positive inside)
    const dIn = edt(Uint8Array.from(inside, v => 1 - v), W, H), dOut = edt(inside, W, H);
    const sd = new Float32Array(W * H); let maxd = 0;
    for (let p = 0; p < W * H; p++) { sd[p] = (inside[p] ? dIn[p] - 0.5 : -(dOut[p] - 0.5)) * pxmm; if (sd[p] > maxd) maxd = sd[p]; }
    const bump = boxBlur(S.bump, W, H, Math.max(1, Math.round(0.35 / pxmm)), 2);
    let bmax = 0; for (let p = 0; p < W * H; p++) { if (!inside[p]) bump[p] = 0; if (bump[p] > bmax) bmax = bump[p]; }
    const R = Math.min(14, Math.max(3, 0.85 * maxd));
    const height = (x, y) => {   // top surface over pixel coords (x, y)
      const d = Math.max(0, bilinear(sd, W, H, x, y)), u = Math.min(d / R, 1);
      return opts.edge + opts.puff * Math.sqrt(Math.max(0, 1 - (1 - u) * (1 - u))) + bilinear(bump, W, H, x, y);
    };
    // voxel grid around the piece
    const wmm = (S.x1 - S.x0 + 1) * pxmm, hmm = (S.y1 - S.y0 + 1) * pxmm;
    const v = Math.min(0.6, Math.max(0.22, Math.max(wmm, hmm) / opts.quality));
    const zmax = opts.edge + opts.puff + bmax;
    const NX = Math.ceil(wmm / v) + 5, NY = Math.ceil(hmm / v) + 5, NZ = Math.ceil(zmax / v) + 5;
    const cx = (S.x0 + S.x1) / 2, cy = (S.y0 + S.y1) / 2;
    const org = [-(NX - 1) * v / 2, -(NY - 1) * v / 2, -2 * v];
    const toPx = (X, Y) => [cx + X / pxmm, cy - Y / pxmm];
    const field = new Float32Array(NX * NY * NZ);
    const col = new Float32Array(NZ);
    for (let j = 0; j < NY; j++) for (let i = 0; i < NX; i++) {
      const X = org[0] + i * v, Y = org[1] + j * v, [px, py] = toPx(X, Y);
      const s = bilinear(sd, W, H, px, py), top = height(px, py);
      for (let k = 0; k < NZ; k++) {
        const z = org[2] + k * v;
        let f = Math.max(-s, z - top, -z);
        if (i === 0 || j === 0 || k === 0 || i === NX - 1 || j === NY - 1 || k === NZ - 1) f = Math.max(f, v);
        field[i + NX * (j + NY * k)] = f;
      }
    }
    const m = meshTet(field, NX, NY, NZ, org, v);
    const nb = neighbours(m.idx, m.pos.length / 3);
    taubin(m.pos, nb, 4);
    // colour shares at each vertex from the drawing (smoothed so borders follow curves, not pixels)
    const used = [...new Set(Array.from(lab).filter(l => l > 0))].sort((a, b) => a - b), L = used.length;
    const insideBl = boxBlur(Float32Array.from(inside), W, H, 1, 3);
    const shareR = used.map(l => { const r = boxBlur(Float32Array.from(lab, x => (x === l ? 1 : 0)), W, H, 1, 3); for (let p = 0; p < W * H; p++) r[p] = insideBl[p] > 1e-4 ? r[p] / insideBl[p] : 0; return r; });
    // outside the drawing (walls at the outline) take the nearest colour inside
    const nearest = edtNearest(lab, W, H);
    const nvert = m.pos.length / 3, sh = new Float32Array(nvert * L);
    for (let q = 0; q < nvert; q++) {
      const [px, py] = toPx(m.pos[3 * q], m.pos[3 * q + 1]);
      let tot = 0; for (let l = 0; l < L; l++) { const s = bilinear(shareR[l], W, H, px, py); sh[q * L + l] = s; tot += s; }
      if (tot < 0.2) { const xi = Math.round(Math.min(W - 1, Math.max(0, px))), yi = Math.round(Math.min(H - 1, Math.max(0, py))); const l = used.indexOf(nearest[xi + W * yi]); if (l >= 0) sh[q * L + l] += 1; }
    }
    const cutM = cutColours(m.pos, m.idx, sh, L);
    const faceLab = Uint8Array.from(cutM.lab, l => used[l]);
    const chk = check(cutM.idx);
    // volume for the filament estimate
    let vol = 0; const p = cutM.pos, I = cutM.idx;
    for (let t = 0; t < I.length; t += 3) { const a = 3 * I[t], b = 3 * I[t + 1], c = 3 * I[t + 2];
      vol += p[a] * (p[b + 1] * p[c + 2] - p[b + 2] * p[c + 1]) - p[a + 1] * (p[b] * p[c + 2] - p[b + 2] * p[c]) + p[a + 2] * (p[b] * p[c + 1] - p[b + 1] * p[c]); }
    return { pos: cutM.pos, idx: cutM.idx, faceLab, used, check: chk, size: [wmm, hmm, zmax], volume: vol / 6, dropped: S.dropped, voxel: v };
  }
  // label of the nearest coloured pixel, for every pixel (multi-source breadth-first fill)
  function edtNearest(lab, W, H) {
    const out = Uint8Array.from(lab), q = new Int32Array(W * H); let h = 0, t = 0;
    for (let p = 0; p < W * H; p++) if (lab[p]) q[t++] = p;
    while (h < t) { const p = q[h++], x = p % W, l = out[p];
      for (const n of [x > 0 ? p - 1 : -1, x < W - 1 ? p + 1 : -1, p - W, p + W]) if (n >= 0 && n < W * H && !out[n]) { out[n] = l; q[t++] = n; } }
    return out;
  }

  // ---------- writers ----------
  const enc = s => new TextEncoder().encode(s);
  function stl(pos, idx, name) {
    const nt = idx.length / 3, buf = new ArrayBuffer(84 + nt * 50), dv = new DataView(buf);
    const hdr = (name || "doodle").slice(0, 79); for (let i = 0; i < hdr.length; i++) dv.setUint8(i, hdr.charCodeAt(i) & 127);
    dv.setUint32(80, nt, true); let o = 84;
    for (let t = 0; t < nt; t++) {
      const a = 3 * idx[3 * t], b = 3 * idx[3 * t + 1], c = 3 * idx[3 * t + 2];
      const ux = pos[b] - pos[a], uy = pos[b + 1] - pos[a + 1], uz = pos[b + 2] - pos[a + 2], vx = pos[c] - pos[a], vy = pos[c + 1] - pos[a + 1], vz = pos[c + 2] - pos[a + 2];
      let nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx; const Ln = Math.hypot(nx, ny, nz) || 1;
      for (const x of [nx / Ln, ny / Ln, nz / Ln]) { dv.setFloat32(o, x, true); o += 4; }
      for (const q of [a, b, c]) for (let e = 0; e < 3; e++) { dv.setFloat32(o, pos[q + e], true); o += 4; }
      o += 2;
    }
    return new Uint8Array(buf);
  }
  // OBJ + MTL with one material per colour: Bambu Studio maps each colour to a filament on import
  function obj(pos, idx, faceLab, palette, names, base) {
    const used = [...new Set(faceLab)].sort((a, b) => a - b);
    let mtl = ""; for (const l of used) { const c = parseInt(palette[l].slice(1), 16); mtl += `newmtl ${names[l]}\nKd ${((c >> 16 & 255) / 255).toFixed(4)} ${((c >> 8 & 255) / 255).toFixed(4)} ${((c & 255) / 255).toFixed(4)}\nKa 0 0 0\nKs 0 0 0\nd 1\nillum 1\n\n`; }
    const out = [`mtllib ${base}.mtl\n`];
    for (let q = 0; q < pos.length; q += 3) out.push(`v ${pos[q].toFixed(3)} ${pos[q + 1].toFixed(3)} ${pos[q + 2].toFixed(3)}\n`);
    for (const l of used) { out.push(`usemtl ${names[l]}\n`); for (let t = 0; t < faceLab.length; t++) if (faceLab[t] === l) out.push(`f ${idx[3 * t] + 1} ${idx[3 * t + 1] + 1} ${idx[3 * t + 2] + 1}\n`); }
    return { obj: enc(out.join("")), mtl: enc(mtl) };
  }
  // 3MF: one solid object, colour per triangle (3MF core basematerials)
  function model3mf(pos, idx, faceLab, palette, names, title) {
    const used = [...new Set(faceLab)].sort((a, b) => a - b), slot = new Map(used.map((l, i) => [l, i]));
    const mats = used.map(l => `<base name="${names[l]}" displaycolor="${palette[l].toUpperCase()}FF"/>`).join("");
    const vs = []; for (let q = 0; q < pos.length; q += 3) vs.push(`<vertex x="${pos[q].toFixed(3)}" y="${pos[q + 1].toFixed(3)}" z="${pos[q + 2].toFixed(3)}"/>`);
    const ts = []; for (let t = 0; t < faceLab.length; t++) ts.push(`<triangle v1="${idx[3 * t]}" v2="${idx[3 * t + 1]}" v3="${idx[3 * t + 2]}" pid="1" p1="${slot.get(faceLab[t])}"/>`);
    return `<?xml version="1.0" encoding="UTF-8"?><model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"><resources><basematerials id="1">${mats}</basematerials><object id="2" name="${title}" type="model" pid="1" pindex="0"><mesh><vertices>${vs.join("")}</vertices><triangles>${ts.join("")}</triangles></mesh></object></resources><build><item objectid="2"/></build></model>`;
  }

  const Doodle = { build, shape, edt, stl, obj, model3mf, check };
  root.Doodle = Doodle;
  if (typeof module !== "undefined") module.exports = Doodle;
})(typeof window !== "undefined" ? window : globalThis);
