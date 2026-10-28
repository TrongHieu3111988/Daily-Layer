/* ---------- Daily Layer 3D kit: loads the shop's real figures as light game toys (inlined into module scripts) ---------- */
const ASSETS = window.ASSETS || "/";
async function fetchBytes(url) {
  const res = await fetch(url); if (!res.ok) throw new Error("fetch " + res.status + " " + url);
  if (!url.endsWith(".txt")) return new Uint8Array(await res.arrayBuffer());
  const bin = atob((await res.text()).trim()), out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}
async function loadToyList() { const r = await fetch(ASSETS + "toys.json"); if (!r.ok) throw new Error("toys"); return r.json(); }
const geoCache = new Map();
// a toy is 1 unit tall, standing on y = 0, centred on x/z, one colour per triangle
async function toyGeometry(t) {
  if (geoCache.has(t.slug)) return geoCache.get(t.slug);
  const p = (async () => {
    const gz = await fetchBytes(ASSETS + t.game);
    const buf = await new Response(new Blob([gz]).stream().pipeThrough(new DecompressionStream("gzip"))).arrayBuffer();
    const dv = new DataView(buf), nv = dv.getUint32(0, true), nf = dv.getUint32(4, true);
    const lo = [0, 1, 2].map(i => dv.getFloat32(8 + 4 * i, true)), hi = [0, 1, 2].map(i => dv.getFloat32(20 + 4 * i, true));
    const q = new Uint16Array(buf.slice(32, 32 + nv * 6)), pos = new Float32Array(nv * 3);
    for (let i = 0; i < nv; i++) for (let k = 0; k < 3; k++) pos[3 * i + k] = lo[k] + q[3 * i + k] / 65535 * (hi[k] - lo[k]);
    const fo = 32 + nv * 6, idx = new Uint32Array(buf.slice(fo, fo + nf * 12)), rgb = new Uint8Array(buf, fo + nf * 12, nf * 3);
    const g = new THREE.BufferGeometry(); g.setAttribute("position", new THREE.BufferAttribute(pos, 3)); g.setIndex(new THREE.BufferAttribute(idx, 1));
    g.computeVertexNormals();
    const ng = g.toNonIndexed(), col = new Float32Array(nf * 9), c = new THREE.Color();
    for (let f = 0; f < nf; f++) { c.setRGB(rgb[3 * f] / 255, rgb[3 * f + 1] / 255, rgb[3 * f + 2] / 255, THREE.SRGBColorSpace); for (let k = 0; k < 3; k++) col.set([c.r, c.g, c.b], 9 * f + 3 * k); }
    ng.setAttribute("color", new THREE.BufferAttribute(col, 3)); ng.computeBoundingBox(); g.dispose();
    return ng;
  })();
  geoCache.set(t.slug, p); return p;
}
const toyMat = () => new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.55, metalness: 0 });
async function toyMesh(t) { const m = new THREE.Mesh(await toyGeometry(t), toyMat()); m.castShadow = true; m.receiveShadow = true; m.userData.toy = t; return m; }
// the child's collection is kept on this device only
const collection = {
  get() { return K.store.get("dl-collection", {}); },
  add(slug) { const c = collection.get(); c[slug] = (c[slug] || 0) + 1; K.store.set("dl-collection", c); return c[slug]; }
};
const shopLink = slug => (window.SHOP_URL || "/") + "#m-" + slug;
const assetURL = p => ASSETS + p;
