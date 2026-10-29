// Tiny Worker in front of the static site. It only answers exact-path files that the
// static assets router would redirect (it turns /name.html into /name), such as
// search-engine verification files. Everything else is served from ./public as before.
const EXACT = {
  "/googlea402708d99025b1d.html": "google-site-verification: googlea402708d99025b1d.html",
};
export default {
  async fetch(request, env) {
    const body = EXACT[new URL(request.url).pathname];
    if (body !== undefined) return new Response(body, { headers: { "content-type": "text/html; charset=utf-8" } });
    return env.ASSETS.fetch(request);
  },
};
