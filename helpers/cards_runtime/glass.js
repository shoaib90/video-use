// Glass-card runtime for HyperFrames. Draws ONE card from window.CARD, a spec that
// helpers/cards.py has already fully resolved: every time is window-local seconds, every
// length is in 1080-high stage units, scroll offsets and heights are precomputed. Nothing
// here decides anything — it only draws, so the logic stays testable in Python.
//
// window.HF_MODE = "overlay" draws the card; "mask" draws only its silhouette (opaque white),
// which ffmpeg uses to cut the frosted backdrop. Both modes run the SAME geometry and the same
// container tweens, so the blur can never drift off the card.
(function () {
  const C = window.CARD;
  const MODE = window.HF_MODE || "overlay";
  const ICONS = {
    clock: '<path d="M12 3a9 9 0 1 1 0 18 9 9 0 0 1 0-18zm0 2a7 7 0 1 0 0 14 7 7 0 0 0 0-14zm-1 2.5h2v4.1l3 1.8-1 1.7-4-2.4z"/>',
    drop: '<path d="M12 3c3.2 4 5.5 7.1 5.5 10.2A5.5 5.5 0 0 1 6.5 13.2C6.5 10.1 8.8 7 12 3z"/>',
    bolt: '<path d="M13.2 2.8 5.8 13.2h5.1l-1.1 8 7.4-10.4h-5.1z"/>',
    scale: '<path d="M5 7.5h14a1.5 1.5 0 0 1 1.5 1.5l-1 9.5a1.5 1.5 0 0 1-1.5 1.3H6a1.5 1.5 0 0 1-1.5-1.3L3.5 9A1.5 1.5 0 0 1 5 7.5zm7 3.2a3 3 0 0 0-3 3h1.4a1.6 1.6 0 0 1 2.3-1.4l-1.2 1.4h1.9l1.2-1.6a3 3 0 0 0-2.6-1.4z"/>',
    list: '<path d="M4 6h2v2H4zm4 0h12v2H8zm-4 5h2v2H4zm4 0h12v2H8zm-4 5h2v2H4zm4 0h12v2H8z"/>',
    star: '<path d="m12 3 2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1-4.4-4.3 6.1-.9z"/>',
  };
  const LOOP = '<path d="M7 7h9.2l-2-2L15.6 3.6 20 8l-4.4 4.4-1.4-1.4 2-2H7a3 3 0 0 0-3 3v1H2v-1a5 5 0 0 1 5-5zm15 6v1a5 5 0 0 1-5 5H7.8l2 2-1.4 1.4L4 18l4.4-4.4 1.4 1.4-2 2H17a3 3 0 0 0 3-3v-1z"/>';
  const tri = (up) => `<svg class="tri" viewBox="0 0 10 10"><path d="${up ? "M5 1.5 9.2 8.5H.8z" : "M5 8.5 .8 1.5h8.4z"}"/></svg>`;
  const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const icon = (name) => (name && ICONS[name] ? `<span class="icon"><svg viewBox="0 0 24 24">${ICONS[name]}</svg></span>` : "");

  document.body.className = MODE;
  const stage = document.createElement("div");
  stage.className = "stage";
  stage.style.cssText = `width:${C.stage.w}px;height:${C.stage.h}px;transform:scale(${C.stage.scale});`;
  document.getElementById("root").appendChild(stage);

  // The holder carries the card's position and its static `scale` (box.k); the card inside
  // keeps its own tweened transform. Same structure in both modes, so the mask matches.
  const holder = document.createElement("div");
  holder.className = "holder";
  holder.style.cssText = `left:${C.box.x}px;top:${C.box.y}px;width:${C.box.w}px;` +
    `transform:scale(${C.box.k || 1});transform-origin:${C.box.side} top;`;
  stage.appendChild(holder);
  const card = document.createElement("div");
  card.className = `card ${C.kind}`;
  card.id = "card";
  card.style.cssText = `left:0px;top:0px;width:${C.box.w}px;height:${C.box.h0}px;` +
    `transform-origin:${C.kind === "stamp" ? "center center" : `${C.box.side} top`};`;
  holder.appendChild(card);

  const FULL = C.kind === "deck" || C.kind === "annotate";
  if (FULL) card.classList.add("full");
  // keyline has no glass (text over footage, like the reference), so its mask is EMPTY
  if (MODE === "mask") {
    card.innerHTML = C.kind === "keyline" ? "" : '<div class="shell"></div>';
  } else if (C.kind === "keyline") {
    const K = C.keyline;
    // characters wrapped per WORD so a line never breaks inside a word while typing
    const typed = K.text.split(" ").map((w) =>
      `<span class="w">${[...w].map((ch) => `<span class="c">${esc(ch)}</span>`).join("")}</span>`).join(" ");
    card.innerHTML = `
      <div class="kl-scrim"></div>
      <div class="kl" style="bottom:${1080 - K.bottom}px;max-width:${K.max_w}px">
        <div class="kl-bar" id="klbar"></div>
        <div class="kl-text" style="font-size:${K.font}px">${typed}</div>
        ${K.sub ? `<div class="kl-sub" id="klsub" style="font-size:${K.sub_font}px">${esc(K.sub)}</div>` : ""}
      </div>`;
  } else if (C.kind === "deck") {
    const D = C.deck;
    const cards = D.cards.map((c) => `
      <div class="dc" id="dc${c.k}" style="left:${c.x}px;top:${c.y}px;width:${D.w}px;height:${D.h}px">
        <div class="dc-shell"></div><div class="dc-glow" id="dg${c.k}"></div>
        <div class="dc-label">${esc(c.label)}</div>
        <div class="dc-mark">${c.icon && ICONS[c.icon] ? `<svg viewBox="0 0 24 24">${ICONS[c.icon]}</svg>` : `<span>${c.k + 1}</span>`}</div>
        <div class="dc-title">${esc(c.title)}</div>
      </div>`).join("");
    card.innerHTML = `<div class="ff-bg"></div><div class="deck-row" id="drow">${cards}</div>`;
  } else if (C.kind === "annotate") {
    const A = C.annotate, I = A.image;
    const lines = A.marks.map((m, k) => (m.type === "callout"
      ? `<line id="ln${k}" x1="${m.line[0]}" y1="${m.line[1]}" x2="${m.line[2]}" y2="${m.line[3]}" />` : "")).join("");
    const marks = A.marks.map((m, k) => {
      const box = `left:${m.x}px;top:${m.y}px;width:${m.w}px;height:${m.h}px`;
      if (m.type === "highlight") return `<div class="mk-hl" id="mk${k}" style="${box}"></div>`;
      let html = `<div class="mk-box${m.type === "callout" ? " thin" : ""}" id="mk${k}" style="${box}"></div>`;
      if (m.type === "callout") {
        const [, , x2, y2] = m.line;
        const pos = m.side === "right" ? `left:${x2 + 14}px;top:${y2 - 22}px`
          : m.side === "left" ? `right:${C.stage.w - x2 + 14}px;top:${y2 - 22}px;text-align:right`
          : m.side === "top" ? `left:${x2 - 300}px;width:600px;top:${y2 - 52}px;text-align:center`
          : `left:${x2 - 300}px;width:600px;top:${y2 + 8}px;text-align:center`;
        html += `<div class="mk-label" id="lb${k}" style="${pos}">${esc(m.label)}</div>`;
      }
      return html;
    }).join("");
    card.innerHTML = `
      <div class="ff-bg"></div>
      <div class="an" id="an">
        ${A.title ? `<div class="an-title">${esc(A.title)}</div>` : ""}
        <img class="an-img" src="${I.src}" style="left:${I.x}px;top:${I.y}px;width:${I.w}px;height:${I.h}px" />
        <svg class="an-lines" data-layout-allow-overlap viewBox="0 0 ${C.stage.w} 1080" style="width:${C.stage.w}px;height:1080px">${lines}</svg>
        <div class="an-marks" data-layout-allow-overlap>${marks}</div>
        ${A.caption ? `<div class="an-cap" style="top:${I.y + I.h + 28}px">${esc(A.caption)}</div>` : ""}
      </div>`;
  } else if (C.kind === "stamp") {
    const P = C.stamp;
    card.innerHTML = `
      <div class="shell"></div>
      <div class="content"><span class="stamp-text${P.accent ? " accent" : ""}" id="stext"
        style="font-size:${P.font}px;letter-spacing:${P.track}em">${esc(P.text)}</span></div>`;
  } else if (C.kind === "list") {
    const L = C.list;
    const rows = L.rows.map((r, k) => `
      <div class="row" id="r${k}" style="top:${r.top}px;height:${r.h}px">
        ${L.time_col ? `<span class="time">${esc(r.time || "")}</span>` : ""}
        <span class="dot" id="d${k}" style="left:${L.dot_x}px"></span>${k < L.rows.length - 1 ? `<span class="spine" id="sp${k}" style="left:${L.dot_x + 6}px;height:${r.h}px"></span>` : ""}
        <span class="what" style="left:${L.text_x}px">${esc(r.text)}</span>
        ${r.chips.length ? `<span class="chips" style="left:${L.text_x}px">${r.chips.map((c, j) => `<span class="chip" id="c${k}_${j}">${esc(c.text)}</span>`).join("")}</span>` : ""}
      </div>`).join("");
    const F = L.footer;
    card.innerHTML = `
      <div class="shell"></div>
      <div class="content">
        <div class="head">${icon(C.icon)}<span class="label">${esc(C.label)}</span>${L.tag ? `<span class="tag" id="tag">${esc(L.tag.text)}</span>` : ""}</div>
        <div class="view" style="top:${L.view.top}px;height:${L.view.h}px"><div class="list" id="list">${rows}</div></div>
        ${F ? `<div class="foot" id="foot"><span class="loop"><svg viewBox="0 0 24 24">${LOOP}</svg></span>
          <span class="rep">${esc(F.text)}</span>${F.value ? `<span class="years" id="fval">${esc(F.value)}</span>` : ""}</div>` : ""}
      </div>`;
  } else {
    const S = C.stat;
    const vals = S.steps.map((s, k) => `<div class="val${s.accent ? " accent" : ""}" id="v${k}">${esc(s.value)}${s.unit ? `<span class="unit">${esc(s.unit)}</span>` : ""}</div>`).join("");
    const tags = S.steps.map((s, k) => (s.tag ? `<span id="t${k}">${esc(s.tag)}</span>` : "")).join("");
    const subs = S.steps.map((s, k) => (s.sub ? `<div class="sub${s.sub_dir ? "" : " muted"}" id="s${k}">${s.sub_dir ? tri(s.sub_dir === "up") : ""}<span>${esc(s.sub)}</span></div>` : "")).join("");
    card.innerHTML = `
      <div class="shell"></div>
      <div class="content">
        <div class="row1">${icon(C.icon)}<span class="label">${esc(C.label)}</span><span class="tag">${tags}</span></div>
        <div class="valwrap" data-layout-allow-overlap>${vals}</div>
        <div class="subwrap" data-layout-allow-overlap>${subs}</div>
      </div>`;
  }

  const tl = gsap.timeline({ paused: true });
  const side = C.box.side === "left" ? -1 : C.box.side === "right" ? 1 : 0;
  // Curve for opacity, spring for transforms (motion.py: alpha must never overshoot).
  if (C.kind === "keyline" || FULL) {
    // Opacity only on the container: a full-frame mask that scaled would show the frosted
    // backdrop's edge. Motion lives on the inner elements (overlay pass only).
    tl.fromTo("#card", { opacity: 0 }, { opacity: 1, duration: FULL ? 0.45 : 0.25, ease: "power2.out" }, C.in);
    tl.fromTo("#card", { opacity: 1 }, { opacity: 0, duration: C.exit_dur, ease: "power2.in", immediateRender: false }, C.exit);
  } else if (C.kind === "stamp") {
    // A stamp lands ON its word: quick, a small press-in, no slide. Shared by both passes.
    tl.fromTo("#card", { opacity: 0 }, { opacity: 1, duration: 0.22, ease: "power2.out" }, C.in);
    tl.fromTo("#card", { scale: 1.14, y: -6 }, { scale: 1, y: 0, duration: 0.45, ease: "back.out(2.0)" }, C.in);
    tl.fromTo("#card", { opacity: 1 }, { opacity: 0, duration: 0.35, ease: "power2.in", immediateRender: false }, C.exit);
    tl.to("#card", { scale: 0.96, duration: 0.35, ease: "power2.in" }, C.exit);
  } else {
    tl.fromTo("#card", { opacity: 0 }, { opacity: 1, duration: 0.45, ease: "power2.out" }, C.in);
    tl.fromTo("#card", { x: 70 * side, scale: 0.93 }, { x: 0, scale: 1, duration: 0.85, ease: "back.out(1.4)" }, C.in);
    // Container height: shared by both passes, so the frosted backdrop grows with the card.
    for (const [t, h] of C.heights) tl.to("#card", { height: h, duration: 0.5, ease: "power3.out" }, t);
    tl.fromTo("#card", { opacity: 1 }, { opacity: 0, duration: C.exit_dur, ease: "power2.in", immediateRender: false }, C.exit);
    tl.to("#card", { x: 40 * side, scale: 0.96, duration: C.exit_dur, ease: "power2.in" }, C.exit);
  }

  if (MODE !== "mask" && C.kind === "list") {
    const L = C.list;
    const head = "#card .head";
    tl.fromTo(head, { opacity: 0, y: 10 }, { opacity: 1, y: 0, duration: 0.5, ease: "power3.out" }, C.in + 0.12);
    for (const s of L.scrolls) {
      tl.to("#list", { y: -s.offset, duration: 0.6, ease: "power3.inOut" }, s.t);
      for (const j of s.fade) tl.to(`#r${j}`, { opacity: 0, duration: 0.4, ease: "power2.in" }, s.t);
    }
    L.rows.forEach((r, k) => {
      tl.fromTo(`#r${k}`, { opacity: 0, x: -16 }, { opacity: 1, x: 0, duration: 0.5, ease: "power3.out" }, r.t);
      tl.fromTo(`#d${k}`, { scale: 0 }, { scale: 1, duration: 0.45, ease: "back.out(2.2)" }, r.t);
      // accent marks NOW: a dot is born accent (CSS) and goes muted when the next step lands
      if (k > 0) tl.to(`#d${k - 1}`, { backgroundColor: C.colors.dot_done, duration: 0.35, ease: "power2.out" }, r.t);
      // The spine below row k points at row k+1, so it grows down WITH row k+1. Shown with its
      // own row, it hung below the card, which only grows to the rows landed so far.
      if (k > 0) tl.fromTo(`#sp${k - 1}`, { scaleY: 0 }, { scaleY: 1, duration: 0.45, ease: "power3.out" }, r.t);
      r.chips.forEach((c, j) => tl.fromTo(`#c${k}_${j}`, { opacity: 0, y: 6, scale: 0.9 }, { opacity: 1, y: 0, scale: 1, duration: 0.45, ease: "back.out(1.6)" }, c.t));
    });
    if (L.tag) tl.fromTo("#tag", { opacity: 0 }, { opacity: 1, duration: 0.4, ease: "power2.out" }, L.tag.t);
    if (L.footer) {
      tl.fromTo("#foot", { opacity: 0, y: 10 }, { opacity: 1, y: 0, duration: 0.5, ease: "power3.out" }, L.footer.t);
      if (L.footer.value) tl.fromTo("#fval", { opacity: 0, y: 14 }, { opacity: 1, y: 0, duration: 0.6, ease: "expo.out" }, L.footer.value_t);
    }
  }
  if (MODE !== "mask" && C.kind === "stat") {
    const S = C.stat;
    tl.fromTo("#card .row1", { opacity: 0, y: 10 }, { opacity: 1, y: 0, duration: 0.5, ease: "power3.out" }, C.in + 0.12);
    S.steps.forEach((s, k) => {
      // Value flip: the previous value leaves upward, this one arrives from below on its word.
      if (k > 0) {
        tl.to(`#v${k - 1}`, { opacity: 0, y: -34, duration: 0.35, ease: "power2.in" }, s.t - 0.3);
        if (S.steps[k - 1].tag) tl.to(`#t${k - 1}`, { opacity: 0, duration: 0.3, ease: "power2.inOut" }, s.t - 0.15);
        if (S.steps[k - 1].sub) tl.to(`#s${k - 1}`, { opacity: 0, duration: 0.3, ease: "power2.inOut" }, s.t - 0.15);
      }
      tl.fromTo(`#v${k}`, { opacity: 0, y: 34 }, { opacity: 1, y: 0, duration: 0.6, ease: "expo.out" }, s.t);
      if (s.tag) tl.fromTo(`#t${k}`, { opacity: 0 }, { opacity: 1, duration: 0.35, ease: "power2.out" }, s.t + 0.15);
      if (s.sub) tl.fromTo(`#s${k}`, { opacity: 0, y: 8 }, { opacity: 1, y: 0, duration: 0.5, ease: "power3.out" }, s.sub_t);
    });
  }
  if (MODE !== "mask" && C.kind === "keyline") {
    const K = C.keyline;
    tl.fromTo("#klbar", { scaleY: 0 }, { scaleY: 1, duration: 0.45, ease: "power3.out" }, C.in);
    const chars = document.querySelectorAll(".kl-text .c");
    tl.fromTo(chars, { opacity: 0 }, { opacity: 1, duration: 0.06, ease: "none",
      stagger: K.type_dur / Math.max(1, chars.length) }, C.in + 0.05);
    if (K.sub) tl.fromTo("#klsub", { opacity: 0, y: 8 }, { opacity: 1, y: 0, duration: 0.5, ease: "power3.out" }, K.sub_t);
    tl.to(".kl", { x: -24, duration: C.exit_dur, ease: "power2.in" }, C.exit);
  }
  if (MODE !== "mask" && C.kind === "deck") {
    const D = C.deck;
    // state -> look. Opacity on a curve, scale on a spring (motion.py: alpha never overshoots).
    const LOOK = { done: { opacity: 0.34, scale: 0.88 }, next: { opacity: 0.6, scale: 0.88 }, lit: { opacity: 1, scale: 1 } };
    tl.fromTo("#drow", { scale: 0.94, y: 18 }, { scale: 1, y: 0, duration: 0.8, ease: "back.out(1.3)" }, C.in);
    for (const c of D.cards) {
      tl.set(`#dc${c.k}`, LOOK[c.before], 0);
      tl.set(`#dg${c.k}`, { opacity: c.before === "lit" ? 1 : 0 }, 0);
      if (c.before !== c.after) {
        tl.to(`#dc${c.k}`, { opacity: LOOK[c.after].opacity, duration: 0.45, ease: "power2.inOut" }, D.t_light);
        tl.to(`#dc${c.k}`, { scale: LOOK[c.after].scale, duration: 0.7, ease: c.after === "lit" ? "back.out(1.8)" : "power3.out" }, D.t_light);
        tl.to(`#dg${c.k}`, { opacity: c.after === "lit" ? 1 : 0, duration: 0.5, ease: "power2.inOut" }, D.t_light);
      }
    }
  }
  if (MODE !== "mask" && C.kind === "annotate") {
    const A = C.annotate;
    tl.fromTo("#an", { scale: 0.96, y: 14 }, { scale: 1, y: 0, duration: 0.8, ease: "back.out(1.2)" }, C.in);
    A.marks.forEach((m, k) => {
      if (m.type === "highlight") {
        tl.fromTo(`#mk${k}`, { scaleX: 0 }, { scaleX: 1, duration: 0.4, ease: "power2.out" }, m.t);
      } else {
        tl.fromTo(`#mk${k}`, { opacity: 0 }, { opacity: 1, duration: 0.3, ease: "power2.out" }, m.t);
        tl.fromTo(`#mk${k}`, { scale: 1.12 }, { scale: 1, duration: 0.55, ease: "back.out(2)" }, m.t);
      }
      if (m.type === "callout") {
        const ln = document.getElementById(`ln${k}`);
        const len = Math.hypot(m.line[2] - m.line[0], m.line[3] - m.line[1]);
        ln.style.strokeDasharray = `${len}`;
        tl.fromTo(ln, { strokeDashoffset: len }, { strokeDashoffset: 0, duration: 0.4, ease: "power2.out" }, m.t + 0.15);
        tl.fromTo(`#lb${k}`, { opacity: 0, y: 6 }, { opacity: 1, y: 0, duration: 0.4, ease: "power3.out" }, m.t + 0.4);
      }
    });
  }
  window.__timelines["main"] = tl;
  tl.seek(0);
})();
