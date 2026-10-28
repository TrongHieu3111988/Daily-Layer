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
  K.lang = store.get("dl-lang", /^vi/i.test(navigator.language || "") ? "vi" : "en");
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
  // draw a friend centred at (0,0); opts: shape, colour, w, h, mood ("happy" | "wow" | "sleepy" | "sad"), lw
  K.friend = (g, o) => {
    const { shape = "square", colour = "#FFC93C", w = 60, h = 60, mood = "happy" } = o, lw = o.lw ?? Math.max(2, Math.min(w, h) * 0.07);
    g.save();
    shapePath(g, shape, w, h); g.fillStyle = colour; g.fill();
    // soft highlight
    g.save(); shapePath(g, shape, w, h); g.clip(); g.fillStyle = "rgba(255,255,255,.28)"; g.beginPath(); g.ellipse(-w * 0.22, -h * 0.28, w * 0.28, h * 0.16, -0.5, 0, Math.PI * 2); g.fill();
    g.fillStyle = "rgba(0,0,0,.08)"; g.fillRect(-w, h * 0.22, w * 2, h); g.restore();
    shapePath(g, shape, w, h); g.lineWidth = lw; g.strokeStyle = K.INK; g.lineJoin = "round"; g.stroke();
    // face
    const s = Math.min(w, h), fy = shape === "tri" ? h * 0.18 : shape === "dome" ? h * 0.08 : 0, ex = s * 0.17, ey = fy - s * 0.04, er = Math.max(1.6, s * 0.065);
    g.fillStyle = K.INK; g.strokeStyle = K.INK; g.lineCap = "round"; g.lineWidth = Math.max(1.5, s * 0.05);
    if (mood === "sleepy") { for (const sx of [-1, 1]) { g.beginPath(); g.arc(sx * ex, ey, er, 0.1 * Math.PI, 0.9 * Math.PI); g.stroke(); } }
    else for (const sx of [-1, 1]) { g.beginPath(); g.ellipse(sx * ex, ey, er, er * (mood === "wow" ? 1.35 : 1.15), 0, 0, Math.PI * 2); g.fill();
      g.fillStyle = "#fff"; g.beginPath(); g.arc(sx * ex - er * 0.3, ey - er * 0.35, er * 0.38, 0, Math.PI * 2); g.fill(); g.fillStyle = K.INK; }
    g.fillStyle = "rgba(255,120,150,.55)";
    for (const sx of [-1, 1]) { g.beginPath(); g.ellipse(sx * ex * 1.75, ey + s * 0.1, s * 0.07, s * 0.045, 0, 0, Math.PI * 2); g.fill(); }
    g.beginPath();
    if (mood === "wow") { g.fillStyle = K.INK; g.ellipse(0, ey + s * 0.15, s * 0.05, s * 0.065, 0, 0, Math.PI * 2); g.fill(); }
    else if (mood === "sad") { g.arc(0, ey + s * 0.22, s * 0.08, 1.15 * Math.PI, 1.85 * Math.PI); g.stroke(); }
    else { g.arc(0, ey + s * 0.07, s * 0.09, 0.15 * Math.PI, 0.85 * Math.PI); g.stroke(); }
    g.restore();
  };
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
