// Daily Layer app shell: the pages and the 3D library keep working offline once visited.
// Pages and the catalog: network first, cached copy when offline. Libraries, fonts, icons: cache first.
// Download zips are never cached.
const CACHE = "dl-v2";
const SHELL = ["/", "/doodle/", "/sculpt/", "/games/stack/", "/games/spot/", "/games/shelf/", "/manifest.webmanifest", "/icons/icon-192.png"];
self.addEventListener("install", e => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting())); });
self.addEventListener("activate", e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener("fetch", e => {
  const r = e.request, u = new URL(r.url);
  if (r.method !== "GET" || u.pathname.endsWith(".zip")) return;
  const lib = /cdn\.jsdelivr\.net|fonts\.(googleapis|gstatic)\.com/.test(u.host) || u.pathname.startsWith("/icons/");
  if (lib) { e.respondWith(caches.match(r).then(hit => hit || fetch(r).then(res => { const c = res.clone(); caches.open(CACHE).then(k => k.put(r, c)); return res; }))); return; }
  if (u.origin !== location.origin) return;
  e.respondWith(fetch(r).then(res => { if (res.ok) { const c = res.clone(); caches.open(CACHE).then(k => k.put(r, c)); } return res; }).catch(() => caches.match(r)));
});
