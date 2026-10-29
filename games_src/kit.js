/* Daily Layer game kit: words, sound, confetti and the "toy friends" every game draws. */
(function () {
  "use strict";
  const K = {};
  const store = {
    get(k, d) { try { const v = localStorage.getItem(k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }
  };
  K.store = store;
  K.CALM = matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---------- words ---------- */
  // English first; Vietnamese on Vietnamese devices, or whatever was last picked in the shop or any game (one shared setting)
  K.lang = (() => { let v = ""; try { v = (localStorage.getItem("dl-lang") || "").replace(/"/g, ""); } catch (e) {} return v === "vi" || v === "en" ? v : /^vi/i.test(navigator.language || "") ? "vi" : "en"; })();
  K.words = { en: {}, vi: {} };
  K.t = (k, ...a) => { const v = K.words[K.lang][k] ?? K.words.en[k] ?? k; return typeof v === "function" ? v(...a) : v; };
  K.applyWords = () => {
    document.documentElement.lang = K.lang;
    document.querySelectorAll("[data-t]").forEach(el => { el.textContent = K.t(el.dataset.t); });
    document.querySelectorAll("[data-t-label]").forEach(el => { el.setAttribute("aria-label", K.t(el.dataset.tLabel)); });
    const b = document.getElementById("langBtn"); if (b) b.textContent = K.lang === "vi" ? "EN" : "VI";
    K.onLang && K.onLang();
  };
  K.toggleLang = () => { K.lang = K.lang === "vi" ? "en" : "vi"; store.set("dl-lang", K.lang); K.applyWords(); };

  /* ---------- sound: tiny synth blips, only after the child has touched the screen ---------- */
  let ac = null; K.muted = store.get("dl-muted", false);
  function ctx() { if (K.muted) return null; if (!ac) { try { ac = new (window.AudioContext || window.webkitAudioContext)(); } catch (e) { return null; } } if (ac.state === "suspended") ac.resume(); return ac; }
  function tone(f0, f1, dur, type = "sine", vol = 0.18, delay = 0) {
    const a = ctx(); if (!a) return;
    const t0 = a.currentTime + delay, o = a.createOscillator(), g = a.createGain();
    o.type = type; o.frequency.setValueAtTime(f0, t0); o.frequency.exponentialRampToValueAtTime(Math.max(30, f1), t0 + dur);
    g.gain.setValueAtTime(0.0001, t0); g.gain.exponentialRampToValueAtTime(vol, t0 + 0.015); g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
    o.connect(g).connect(a.destination); o.start(t0); o.stop(t0 + dur + 0.02);
  }
  K.sfx = {
    pop: () => tone(520, 880, 0.12, "triangle", 0.16),
    thud: () => tone(180, 90, 0.14, "sine", 0.22),
    boing: () => { tone(300, 120, 0.25, "square", 0.06); tone(150, 260, 0.2, "sine", 0.12, 0.05); },
    chime: () => { [660, 880, 1320].forEach((f, i) => tone(f, f * 1.01, 0.22, "triangle", 0.12, i * 0.07)); },
    tada: () => { [523, 659, 784, 1046].forEach((f, i) => tone(f, f, 0.3, "triangle", 0.14, i * 0.09)); },
    tick: () => tone(1200, 900, 0.04, "square", 0.04)
  };
  K.setMuted = m => { K.muted = m; store.set("dl-muted", m); const b = document.getElementById("soundBtn"); if (b) b.innerHTML = m ? K.ICON.mute : K.ICON.sound; };

  /* ---------- confetti ---------- */
  let cc = null, cg = null, bits = [], craf = 0;
  const CONF = ["#FF6B57", "#FFC93C", "#3FBF7F", "#5DB8FF", "#8C6BF2", "#FF8FB8"];
  K.confetti = (x, y, n = 60) => {
    if (K.CALM) return;
    if (!cc) { cc = document.createElement("canvas"); cc.id = "confetti"; document.body.appendChild(cc); cg = cc.getContext("2d"); }
    const d = Math.min(devicePixelRatio || 1, 2); cc.width = innerWidth * d; cc.height = innerHeight * d;
    x = x ?? innerWidth / 2; y = y ?? innerHeight / 3;
    for (let i = 0; i < n; i++) { const a = Math.random() * Math.PI * 2, s = 4 + Math.random() * 7;
      bits.push({ x, y, vx: Math.cos(a) * s, vy: Math.sin(a) * s - 5, r: Math.random() * 6, vr: (Math.random() - .5) * .4, w: 6 + Math.random() * 6, h: 4 + Math.random() * 4, c: CONF[i % CONF.length], life: 0 }); }
    if (!craf) craf = requestAnimationFrame(step);
    function step() {
      const d = cc.width / innerWidth; cg.clearRect(0, 0, cc.width, cc.height);
      for (let i = bits.length - 1; i >= 0; i--) { const b = bits[i]; b.life++; b.vy += 0.25; b.vx *= 0.99; b.x += b.vx; b.y += b.vy; b.r += b.vr;
        if (b.y > innerHeight + 20 || b.life > 240) { bits.splice(i, 1); continue; }
        cg.save(); cg.translate(b.x * d, b.y * d); cg.rotate(b.r); cg.fillStyle = b.c; cg.fillRect(-b.w * d / 2, -b.h * d / 2, b.w * d, b.h * d); cg.restore(); }
      craf = bits.length ? requestAnimationFrame(step) : 0;
    }
  };

  /* ---------- toy friends: our own little characters, drawn with canvas ---------- */
  K.COLS = { coral: "#FF6B57", sun: "#FFC93C", grass: "#3FBF7F", sky: "#5DB8FF", grape: "#8C6BF2", pink: "#FF8FB8", orange: "#FF9B3D", mint: "#7FE0C2" };
  K.INK = "#1B2547";
  function shapePath(g, shape, w, h) {
    g.beginPath();
    const r = Math.min(w, h) * 0.22;
    if (shape === "ball") { g.ellipse(0, 0, w / 2, h / 2, 0, 0, Math.PI * 2); }
    else if (shape === "tri") { g.moveTo(0, -h / 2); g.lineTo(w / 2, h / 2); g.lineTo(-w / 2, h / 2); g.closePath(); }
    else if (shape === "dome") { g.moveTo(-w / 2, h / 2); g.lineTo(-w / 2, 0); g.ellipse(0, 0, w / 2, h / 2, 0, Math.PI, 0); g.lineTo(w / 2, h / 2); g.closePath(); }
    else if (shape === "star") { for (let k = 0; k < 10; k++) { const a = -Math.PI / 2 + k * Math.PI / 5, rr = k % 2 ? 0.42 : 1; g.lineTo(Math.cos(a) * w / 2 * rr, Math.sin(a) * h / 2 * rr * 1.05 + h * 0.04); } g.closePath(); }
    else if (shape === "heart") { const s = w / 2; g.moveTo(0, h * 0.42); g.bezierCurveTo(-s * 1.4, -h * 0.05, -s * 0.55, -h * 0.62, 0, -h * 0.2); g.bezierCurveTo(s * 0.55, -h * 0.62, s * 1.4, -h * 0.05, 0, h * 0.42); }
    else { g.roundRect ? g.roundRect(-w / 2, -h / 2, w, h, r) : g.rect(-w / 2, -h / 2, w, h); }
  }
  K.shapePath = shapePath;
  /* Each block colour belongs to one of the shop's animals, so a colour still means the same friend in every puzzle.
     The block keeps its shape (the physics and the puzzles use it); the animal is painted on: ears, patches, nose, beak. */
  K.ANIMALS = {
    fox: { ears: "point", tip: "#1B2547", inner: "#FFE3D6", muzzle: "#FFFFFF", nose: true },
    chick: { tuft: true, belly: "#FFE58A", beak: "#FF9B3D" },
    frog: { bumps: true, belly: "#BFF0C9", wide: true },
    whale: { spout: true, belly: "#D6EEFF", lines: true },
    penguin: { mask: "#FFFFFF", beak: "#FFB13D" },
    axolotl: { gills: "#E0457B", spots: "#FF6FA0" },
    kitten: { ears: "point", inner: "#FFC4D6", stripes: "rgba(27,37,71,.32)", nose: "#FF8FB8", whiskers: true },
    bear: { ears: "round", inner: "#E8C9A0", muzzle: "#E8C9A0", nose: true },
    bunny: { ears: "long", inner: "#FFC4D6", nose: "#FF8FB8", whiskers: true }
  };
  K.ANIMAL_OF = { "#ff6b57": "fox", "#ffc93c": "chick", "#3fbf7f": "frog", "#5db8ff": "whale", "#8c6bf2": "penguin", "#ff8fb8": "axolotl",
    "#ff9b3d": "kitten", "#b8834f": "bear", "#f4effa": "bunny", "#7fe0c2": "frog" };
  // y of the top edge of a shape at x (for ears and bumps); null where there is no flat-ish top
  function topAt(shape, w, h, x) {
    const u = Math.min(1, Math.abs(x) / (w / 2));
    if (shape === "ball" || shape === "dome") return -(h / 2) * Math.sqrt(1 - u * u);
    if (shape === "tri") return -h / 2 + h * u;
    if (shape === "star" || shape === "heart") return null;
    return -h / 2;
  }
  function blob(g, x, y, rx, ry, rot, fill, lw) { g.beginPath(); g.ellipse(x, y, rx, ry, rot || 0, 0, Math.PI * 2); g.fillStyle = fill; g.fill(); if (lw) { g.lineWidth = lw; g.strokeStyle = K.INK; g.stroke(); } }
  // behind the body: ears, gills, bumps, tuft, spout
  function animalBack(g, a, o, w, h, s, lw, colour) {
    const sh = o.shape, tri = sh === "tri", ex = tri ? w * 0.15 : Math.min(w * 0.3, w / 2 - s * 0.14), ear = s * (tri ? 0.18 : 0.22);
    const T = x => topAt(sh, w, h, x);
    if (a.ears && T(ex) !== null) for (const sx of [-1, 1]) {
      const x = sx * ex, y = T(x) + ear * 0.25;
      g.save(); g.translate(x, y); g.rotate(sx * (tri ? 0.75 : a.ears === "long" ? 0.12 : 0.28));
      if (a.ears === "point") {
        g.beginPath(); g.moveTo(-ear * 0.62, ear * 0.3); g.lineTo(0, -ear * 1.05); g.lineTo(ear * 0.62, ear * 0.3); g.closePath(); g.fillStyle = colour; g.fill(); g.lineWidth = lw; g.strokeStyle = K.INK; g.lineJoin = "round"; g.stroke();
        g.beginPath(); g.moveTo(-ear * 0.3, ear * 0.15); g.lineTo(0, -ear * 0.6); g.lineTo(ear * 0.3, ear * 0.15); g.closePath(); g.fillStyle = a.inner; g.fill();
        if (a.tip) { g.save(); g.beginPath(); g.moveTo(-ear * 0.62, ear * 0.3); g.lineTo(0, -ear * 1.05); g.lineTo(ear * 0.62, ear * 0.3); g.closePath(); g.clip(); g.fillStyle = a.tip; g.fillRect(-ear, -ear * 1.2, ear * 2, ear * 0.55); g.restore(); }
      } else if (a.ears === "round") { blob(g, 0, -ear * 0.2, ear * 0.55, ear * 0.55, 0, colour, lw); blob(g, 0, -ear * 0.2, ear * 0.28, ear * 0.28, 0, a.inner); }
      else { blob(g, 0, -ear * 1.0, ear * 0.42, ear * 1.25, 0, colour, lw); blob(g, 0, -ear * 0.95, ear * 0.2, ear * 0.85, 0, a.inner); }
      g.restore();
    }
    if (a.gills) for (const sx of [-1, 1]) {
      const bx = sx * (sh === "tri" ? w * 0.3 : w / 2), by = sh === "tri" ? h * 0.12 : -h * 0.12;
      for (let k = -1; k <= 1; k++) { g.save(); g.translate(bx, by + k * s * 0.13); g.rotate(sx * (Math.PI / 2 + k * 0.5) - Math.PI / 2 * sx + sx * 0.0); blob(g, sx * s * 0.11, 0, s * 0.13, s * 0.055, k * 0.45 * sx, a.gills, lw * 0.8); g.restore(); }
    }
    if (a.tuft && T(0) !== null) { g.lineWidth = lw; g.strokeStyle = K.INK; g.lineCap = "round"; const y = T(0);
      for (const k of [-1, 0, 1]) { g.beginPath(); g.moveTo(k * s * 0.05, y + 1); g.quadraticCurveTo(k * s * 0.12, y - s * 0.12, k * s * 0.09 + s * 0.04, y - s * 0.17); g.stroke(); } }
    if (a.spout && T(0) !== null) { const y = T(0) - s * 0.05; g.lineWidth = lw * 0.9; g.strokeStyle = K.INK; g.fillStyle = "#BDE6FF";
      for (const sx of [-1, 1]) { g.beginPath(); g.moveTo(0, y); g.quadraticCurveTo(sx * s * 0.05, y - s * 0.2, sx * s * 0.17, y - s * 0.17); g.stroke(); }
      for (const sx of [-1, 0, 1]) blob(g, sx * s * 0.19, y - s * (sx ? 0.15 : 0.26), s * 0.045, s * 0.055, 0, "#BDE6FF", lw * 0.6); }
  }
  // inside the body (clipped): patches, belly, stripes
  function animalPatches(g, a, o, w, h, s, fy, ey, ex) {
    if (a.belly) blob(g, 0, h / 2, w * (a.wide ? 0.42 : 0.34), h * 0.4, 0, a.belly);
    if (a.lines) { g.strokeStyle = "rgba(27,37,71,.18)"; g.lineWidth = Math.max(1, s * 0.025); for (const k of [-1, 0, 1]) { g.beginPath(); g.moveTo(k * w * 0.12, h * 0.2); g.lineTo(k * w * 0.12, h / 2); g.stroke(); } }
    if (a.mask) { blob(g, -ex * 0.95, ey + s * 0.02, s * 0.2, s * 0.22, 0, a.mask); blob(g, ex * 0.95, ey + s * 0.02, s * 0.2, s * 0.22, 0, a.mask); blob(g, 0, ey + s * 0.16, s * 0.24, s * 0.16, 0, a.mask); blob(g, 0, h / 2, w * 0.32, h * 0.36, 0, a.mask); }
    if (a.muzzle) blob(g, 0, ey + s * 0.13, s * 0.21, s * 0.13, 0, a.muzzle);
    if (a.stripes) { g.strokeStyle = a.stripes; g.lineWidth = Math.max(1.5, s * 0.05); g.lineCap = "round"; const y = ey - s * 0.2;
      for (const k of [-1, 0, 1]) { g.beginPath(); g.moveTo(k * s * 0.1, y - s * 0.06 + Math.abs(k) * s * 0.03); g.lineTo(k * s * 0.1, y + s * 0.04); g.stroke(); }
      for (const sx of [-1, 1]) for (const k of [0, 1]) { g.beginPath(); g.moveTo(sx * w / 2, ey + k * s * 0.12); g.lineTo(sx * (w / 2 - s * 0.12), ey + k * s * 0.12 + s * 0.02); g.stroke(); } }
    if (a.spots) for (const [x, y, r] of [[-0.3, -0.25, 0.05], [0.32, -0.18, 0.04], [0.25, 0.3, 0.05], [-0.28, 0.28, 0.035]]) blob(g, x * w, y * h + fy, s * r, s * r, 0, a.spots);
  }
  /* ---------- the toy library: every model the shop has made (toys.json), so games grow with the shop ----------
     Each toy brings its body colour, a front-view sticker (icon.png), its Vietnamese name and, for known animals, a 2D look.
     After K.library() resolves, K.TOYS[slug] is set and a slug can be passed anywhere a colour goes. */
  K.TOYS = {};
  K.library = (timeout = 5000) => K._lib || (K._lib = new Promise(res => {
    const base = window.ASSETS || "/", done = list => res(list), timer = setTimeout(() => done([]), timeout);
    fetch(base + "toys.json").then(r => r.ok ? r.json() : { toys: [] }).then(async j => {
      const list = await Promise.all((j.toys || []).map(t => new Promise(r2 => {
        const toy = { ...t, img: null }; K.TOYS[t.slug] = toy;
        if (!t.icon) return r2(toy);
        const im = new Image(); im.onload = () => { toy.img = im; r2(toy); }; im.onerror = () => r2(toy); im.src = base + t.icon;
      })));
      clearTimeout(timer); done(list);
    }).catch(() => { clearTimeout(timer); done([]); });
  }));
  K.toyName = t => (K.lang === "vi" && t.title_vi ? t.title_vi : (t.title || "").replace(/\s*\(.*\)\s*/, ""));
  // draw a friend centred at (0,0); opts: shape, colour (or a toy slug from the library), w, h, mood ("happy" | "wow" | "sleepy" | "sad"), lw, animal (defaults from the colour)
  K.friend = (g, o) => {
    const toy = o.toy || K.TOYS[o.colour];
    const { shape = "square", w = 60, h = 60, mood = "happy" } = o, colour = toy ? toy.colour : (o.colour || "#FFC93C"), lw = o.lw ?? Math.max(2, Math.min(w, h) * 0.07);
    const name = toy ? toy.look : o.animal === undefined ? K.ANIMAL_OF[String(colour).toLowerCase()] : o.animal, a = name ? K.ANIMALS[name] : null;
    if (toy && !a && toy.img) return stickerFriend(g, toy, shape, colour, w, h, lw);
    const s = Math.min(w, h), fy = shape === "tri" ? h * 0.18 : shape === "dome" ? h * 0.08 : 0, ex = s * 0.17, ey = fy - s * 0.04, er = Math.max(1.6, s * 0.065);
    g.save();
    if (a) animalBack(g, a, o, w, h, s, lw, colour);
    shapePath(g, shape, w, h); g.fillStyle = colour; g.fill();
    // soft highlight, animal patches and a little shade, all inside the shape
    g.save(); shapePath(g, shape, w, h); g.clip();
    if (a) animalPatches(g, a, o, w, h, s, fy, ey, ex);
    g.fillStyle = "rgba(255,255,255,.28)"; g.beginPath(); g.ellipse(-w * 0.22, -h * 0.28, w * 0.28, h * 0.16, -0.5, 0, Math.PI * 2); g.fill();
    g.fillStyle = "rgba(0,0,0,.08)"; g.fillRect(-w, h * 0.22, w * 2, h); g.restore();
    shapePath(g, shape, w, h); g.lineWidth = lw; g.strokeStyle = K.INK; g.lineJoin = "round"; g.stroke();
    // frog eyes sit on bumps on top of the head
    let eY = ey; const T0 = topAt(shape, w, h, ex);
    if (a && a.bumps && T0 !== null && shape !== "tri") { eY = T0 + s * 0.02; for (const sx of [-1, 1]) blob(g, sx * ex, eY, s * 0.15, s * 0.14, 0, colour, lw);
      g.save(); g.beginPath(); g.rect(-w, T0 + lw / 2, w * 2, h); g.clip(); for (const sx of [-1, 1]) blob(g, sx * ex, eY, s * 0.15 - lw / 2, s * 0.14 - lw / 2, 0, colour); g.restore();
      for (const sx of [-1, 1]) blob(g, sx * ex, eY - s * 0.01, s * 0.1, s * 0.1, 0, "#FFFFFF"); }
    // face
    g.fillStyle = K.INK; g.strokeStyle = K.INK; g.lineCap = "round"; g.lineWidth = Math.max(1.5, s * 0.05);
    if (mood === "sleepy") { for (const sx of [-1, 1]) { g.beginPath(); g.arc(sx * ex, eY, er, 0.1 * Math.PI, 0.9 * Math.PI); g.stroke(); } }
    else for (const sx of [-1, 1]) { g.beginPath(); g.ellipse(sx * ex, eY, er, er * (mood === "wow" ? 1.35 : 1.15), 0, 0, Math.PI * 2); g.fill();
      g.fillStyle = "#fff"; g.beginPath(); g.arc(sx * ex - er * 0.3, eY - er * 0.35, er * 0.38, 0, Math.PI * 2); g.fill(); g.fillStyle = K.INK; }
    g.fillStyle = "rgba(255,120,150,.55)";
    for (const sx of [-1, 1]) { g.beginPath(); g.ellipse(sx * ex * 1.75, ey + s * 0.1, s * 0.07, s * 0.045, 0, 0, Math.PI * 2); g.fill(); }
    let my = ey + s * 0.07;
    if (a && a.beak) { my = ey + s * 0.16; g.beginPath(); g.moveTo(-s * 0.075, ey + s * 0.05); g.lineTo(s * 0.075, ey + s * 0.05); g.lineTo(0, ey + s * 0.14); g.closePath(); g.fillStyle = a.beak; g.fill(); g.lineWidth = Math.max(1.2, s * 0.03); g.stroke(); g.lineWidth = Math.max(1.5, s * 0.05); }
    if (a && a.nose) { my = ey + s * 0.1; blob(g, 0, ey + s * 0.065, s * 0.045, s * 0.032, 0, a.nose === true ? K.INK : a.nose); }
    if (a && a.whiskers) { g.lineWidth = Math.max(1, s * 0.022); for (const sx of [-1, 1]) for (const k of [-1, 1]) { g.beginPath(); g.moveTo(sx * s * 0.13, ey + s * 0.11); g.lineTo(sx * s * 0.3, ey + s * 0.11 + k * s * 0.04); g.stroke(); } g.lineWidth = Math.max(1.5, s * 0.05); }
    g.fillStyle = K.INK; g.beginPath();
    const mr = a && a.wide ? s * 0.15 : s * 0.09;
    if (mood === "wow") { g.ellipse(0, my + s * 0.08, s * 0.05, s * 0.065, 0, 0, Math.PI * 2); g.fill(); }
    else if (mood === "sad") { g.arc(0, my + s * 0.15, s * 0.08, 1.15 * Math.PI, 1.85 * Math.PI); g.stroke(); }
    else { g.arc(0, my - (a && a.wide ? s * 0.06 : 0), mr, 0.15 * Math.PI, 0.85 * Math.PI); g.stroke(); }
    g.restore();
  };
  // a toy without a painted 2D look (a new model) wears its own picture on the block
  function stickerFriend(g, toy, shape, colour, w, h, lw) {
    g.save();
    shapePath(g, shape, w, h); g.fillStyle = colour; g.fill();
    g.save(); shapePath(g, shape, w, h); g.clip();
    g.fillStyle = "rgba(255,255,255,.55)"; g.beginPath(); g.ellipse(0, shape === "tri" ? h * 0.18 : 0, Math.min(w, h) * 0.44, Math.min(w, h) * 0.44, 0, 0, Math.PI * 2); g.fill();
    const s = Math.min(w, h) * (shape === "tri" ? 0.62 : 0.86), cy = shape === "tri" ? h * 0.16 : shape === "dome" ? h * 0.06 : 0;
    g.drawImage(toy.img, -s / 2, cy - s / 2, s, s);
    g.fillStyle = "rgba(0,0,0,.08)"; g.fillRect(-w, h * 0.3, w * 2, h); g.restore();
    shapePath(g, shape, w, h); g.lineWidth = lw; g.strokeStyle = K.INK; g.lineJoin = "round"; g.stroke();
    g.restore();
  }
  K.star = (g, x, y, r, fill = "#FFC93C") => {
    g.save(); g.beginPath();
    for (let k = 0; k < 10; k++) { const a = -Math.PI / 2 + k * Math.PI / 5, rr = k % 2 ? r * 0.45 : r; g.lineTo(x + Math.cos(a) * rr, y + Math.sin(a) * rr); }
    g.closePath(); g.fillStyle = fill; g.fill(); g.lineWidth = Math.max(2, r * 0.18); g.strokeStyle = K.INK; g.lineJoin = "round"; g.stroke(); g.restore();
  };
  K.starSVG = on => `<svg viewBox="0 0 40 40" aria-hidden="true"><path d="M20 3l5 10.3 11.3 1.5-8.3 7.8 2.1 11.2L20 28.3 9.9 33.8 12 22.6 3.7 14.8 15 13.3z" fill="${on ? "#FFC93C" : "rgba(127,140,180,.25)"}" stroke="#1B2547" stroke-width="3" stroke-linejoin="round"/></svg>`;

  /* ---------- canvas helper: crisp at any pixel density ---------- */
  K.fit = (canvas, onSize) => {
    const ro = new ResizeObserver(() => { const r = canvas.getBoundingClientRect(), d = Math.min(devicePixelRatio || 1, 2.5);
      if (!r.width) return; canvas.width = Math.round(r.width * d); canvas.height = Math.round(r.height * d); onSize && onSize(r.width, r.height, d); });
    ro.observe(canvas);
  };

  K.ICON = {
    back: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M15 5l-7 7 7 7"/></svg>',
    sound: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 9h4l5-4v14l-5-4H4z" fill="currentColor" fill-opacity=".2"/><path d="M16.5 9a4 4 0 010 6M19 6.5a7.5 7.5 0 010 11"/></svg>',
    mute: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 9h4l5-4v14l-5-4H4z" fill="currentColor" fill-opacity=".2"/><path d="M17 9l5 6M22 9l-5 6"/></svg>',
    star: '<svg viewBox="0 0 24 24"><path d="M12 2.5l2.9 6 6.6.9-4.8 4.6 1.2 6.5L12 17.4l-5.9 3.1 1.2-6.5L2.5 9.4l6.6-.9z" fill="#fff" stroke="#1B2547" stroke-width="2" stroke-linejoin="round"/></svg>',
    replay: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M4 12a8 8 0 108-8H8"/><path d="M8 1L5 4l3 3"/></svg>',
    play: '<svg viewBox="0 0 24 24"><path d="M7 4.5v15l12.5-7.5z" fill="currentColor"/></svg>'
  };
  // shared bar wiring: back link, sound, language
  K.initBar = () => {
    const back = document.getElementById("back"); if (back) { back.innerHTML = K.ICON.back; back.href = window.SHOP_URL || "/"; }
    const s = document.getElementById("soundBtn"); if (s) { s.innerHTML = K.muted ? K.ICON.mute : K.ICON.sound; s.onclick = () => { K.setMuted(!K.muted); if (!K.muted) K.sfx.pop(); }; }
    const l = document.getElementById("langBtn"); if (l) l.onclick = K.toggleLang;
  };
  window.K = K;
})();
