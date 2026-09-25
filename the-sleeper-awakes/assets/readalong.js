/* Read-along player for Scriptorium books.
 *
 * Each narrated chapter embeds <script type="application/json" id="ra-NN"> with
 * {audio, duration, paras: [[[startMs,endMs]|null per whitespace token] per <p data-p>]}.
 * Word + sentence highlighting uses the CSS Custom Highlight API (no DOM rewriting), with a
 * paragraph-level fallback. Tap any narrated word to hear from there. Your place (chapter,
 * time, and reading position when not listening) and your reading settings persist locally.
 * Pattern adapted from the Helios reader (HeliosNYC/ephemeral-one scripts/tts.js).
 */
(function () {
  'use strict';
  var KEY = 'sleeper-awakes:v1';
  var store = load();
  function load() { try { return JSON.parse(localStorage.getItem(KEY)) || {}; } catch (e) { return {}; } }
  function save() { try { localStorage.setItem(KEY, JSON.stringify(store)); } catch (e) {} }

  var HAS_HL = !!(window.CSS && CSS.highlights && window.Highlight);
  var hlWord = HAS_HL ? new Highlight() : null, hlSent = HAS_HL ? new Highlight() : null;
  if (HAS_HL) { CSS.highlights.set('ra-word', hlWord); CSS.highlights.set('ra-sent', hlSent); }

  var ROMAN = ['', 'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII', 'XIII', 'XIV', 'XV', 'XVI', 'XVII', 'XVIII', 'XIX', 'XX', 'XXI', 'XXII', 'XXIII', 'XXIV', 'XXV'];
  var chapters = {};               // n -> {data, section, words, sents}
  var order = [];
  document.querySelectorAll('script[id^="ra-"]').forEach(function (s) {
    var n = parseInt(s.id.slice(3), 10);
    chapters[n] = { data: JSON.parse(s.textContent), section: document.getElementById('ch-' + String(n).padStart(2, '0')) };
    order.push(n);
  });
  order.sort(function (a, b) { return a - b; });
  if (!order.length) return;

  var audio = new Audio(); audio.preload = 'none';
  var cur = null;                  // current chapter number
  var wi = -1, si = -1;            // current word / sentence index
  var raf = 0, userScrollAt = 0, autoScrolling = false;

  /* ---------- building word ranges for a chapter (lazily) ---------- */
  function build(n) {
    var c = chapters[n];
    if (c.words) return c;
    var words = [], sents = [], sentStart = 0;
    c.section.querySelectorAll('.prose p[data-p]').forEach(function (p) {
      var times = c.data.paras[+p.dataset.p] || [];
      var k = 0, walker = document.createTreeWalker(p, NodeFilter.SHOW_TEXT), node, m, re = /\S+/g;
      while ((node = walker.nextNode())) {
        re.lastIndex = 0;
        while ((m = re.exec(node.data))) {
          var t = times[k++];
          if (!t) continue;
          var r = document.createRange(); r.setStart(node, m.index); r.setEnd(node, m.index + m[0].length);
          words.push({ r: r, s: t[0] / 1000, e: t[1] / 1000, p: p, tok: m[0] });
        }
      }
    });
    for (var i = 0; i < words.length; i++) {
      words[i].sent = sents.length;
      var tok = words[i].tok, endsSent = /[.?!]["”’')]*$/.test(tok) && !/^(Mr|Mrs|Dr|St|Messrs)\.$/.test(tok);
      if (endsSent || i === words.length - 1 || words[i + 1].p !== words[i].p) {
        var r = document.createRange();
        r.setStart(words[sentStart].r.startContainer, words[sentStart].r.startOffset);
        r.setEnd(words[i].r.endContainer, words[i].r.endOffset);
        sents.push(r); sentStart = i + 1;
      }
    }
    c.words = words; c.sents = sents;
    return c;
  }

  function indexAt(words, t) {       // last word with start <= t
    var lo = 0, hi = words.length - 1, ans = -1;
    while (lo <= hi) { var mid = (lo + hi) >> 1; if (words[mid].s <= t) { ans = mid; lo = mid + 1; } else hi = mid - 1; }
    return ans;
  }

  /* ---------- highlight + follow ---------- */
  var activeP = null;
  function paint() {
    if (cur == null) return;
    var c = chapters[cur], t = audio.currentTime, i = indexAt(c.words, t);
    var mode = store.hl || 'both';
    if (i !== wi) {
      wi = i;
      var w = c.words[i];
      if (HAS_HL) {
        hlWord.clear(); hlSent.clear();
        if (w && mode !== 'off') {
          if (mode === 'both' || mode === 'word') hlWord.add(w.r);
          if (mode === 'both' || mode === 'sentence') hlSent.add(c.sents[w.sent]);
        }
      }
      if (w && w.p !== activeP) {
        if (activeP) activeP.classList.remove('ra-active');
        activeP = w.p; activeP.classList.add('ra-active');
      }
      if (w) follow(w);
    }
  }
  function follow(w) {
    if (store.follow === false || Date.now() - userScrollAt < 5000) return;
    var rect = w.r.getBoundingClientRect(), vh = window.innerHeight;
    if (rect.top < vh * 0.18 || rect.bottom > vh * 0.62) {
      autoScrolling = true;
      window.scrollBy({ top: rect.top - vh * 0.33, behavior: 'smooth' });
      setTimeout(function () { autoScrolling = false; }, 900);
    }
  }
  window.addEventListener('scroll', function () { if (!autoScrolling && !audio.paused) userScrollAt = Date.now(); }, { passive: true });
  function loop() { paint(); raf = requestAnimationFrame(loop); }

  /* ---------- transport ---------- */
  function playChapter(n, t, autoplay) {
    build(n);
    if (cur !== n) {
      cur = n; wi = -1;
      audio.src = chapters[n].data.audio;
      ui.title.textContent = 'Chapter ' + ROMAN[n];
      mediaMeta();
    }
    var go = function () {
      if (t != null) audio.currentTime = t;
      audio.playbackRate = store.rate || 1;
      if (autoplay !== false) audio.play().catch(function () {});
      paint();
    };
    if (audio.readyState >= 1) go(); else audio.addEventListener('loadedmetadata', go, { once: true });
    if (audio.preload === 'none') { audio.preload = 'auto'; audio.load(); }
    showBar();
  }
  audio.addEventListener('play', function () { ui.pp.textContent = '❚❚'; ui.pp.setAttribute('aria-label', 'Pause'); cancelAnimationFrame(raf); loop(); });
  audio.addEventListener('pause', function () { ui.pp.textContent = '▶'; ui.pp.setAttribute('aria-label', 'Play'); cancelAnimationFrame(raf); remember(); });
  audio.addEventListener('timeupdate', function () {
    ui.time.textContent = fmt(audio.currentTime) + ' / ' + fmt(audio.duration || chapters[cur].data.duration);
    if (!ui.seeking) ui.seek.value = audio.duration ? (audio.currentTime / audio.duration * 1000) : 0;
    if (Math.floor(audio.currentTime) % 3 === 0) remember();
  });
  audio.addEventListener('ended', function () {
    var next = order[order.indexOf(cur) + 1];
    if (next) { playChapter(next, 0); } else remember();
  });
  function remember() { if (cur != null) { store.ch = cur; store.t = Math.max(0, audio.currentTime - 2); save(); } }
  function fmt(s) { s = Math.max(0, s || 0) | 0; return (s / 60 | 0) + ':' + String(s % 60).padStart(2, '0'); }

  /* ---------- tap a word to listen from there ---------- */
  document.addEventListener('click', function (ev) {
    var p = ev.target.closest && ev.target.closest('.prose p[data-p]');
    if (!p || (window.getSelection && String(window.getSelection()).length)) return;
    var sec = p.closest('section.chapter'), n = sec && parseInt(sec.id.slice(3), 10);
    if (!chapters[n] || store.tap === false) return;
    var pos = document.caretPositionFromPoint ? document.caretPositionFromPoint(ev.clientX, ev.clientY)
            : document.caretRangeFromPoint ? document.caretRangeFromPoint(ev.clientX, ev.clientY) : null;
    if (!pos) return;
    var node = pos.offsetNode || pos.startContainer, off = pos.offset != null ? pos.offset : pos.startOffset;
    var c = build(n), best = null;
    for (var i = 0; i < c.words.length; i++) {
      var r = c.words[i].r;
      if (r.startContainer === node && r.startOffset <= off && off <= r.endOffset) { best = c.words[i]; break; }
    }
    if (!best) return;
    userScrollAt = 0;
    playChapter(n, Math.max(0, best.s - 0.05));
  });

  /* ---------- remember reading place even without audio ---------- */
  var posTimer = 0;
  window.addEventListener('scroll', function () {
    clearTimeout(posTimer);
    posTimer = setTimeout(function () {
      var ps = document.querySelectorAll('.prose p[data-p]'), vh = window.innerHeight;
      for (var i = 0; i < ps.length; i++) {
        var r = ps[i].getBoundingClientRect();
        if (r.bottom > vh * 0.2) { store.place = ps[i].closest('section').id + ':' + ps[i].dataset.p; save(); break; }
      }
    }, 400);
  }, { passive: true });

  /* ---------- media session (lock screen / headphones) ---------- */
  function mediaMeta() {
    if (!('mediaSession' in navigator)) return;
    var cover = document.querySelector('.cover img');
    navigator.mediaSession.metadata = new MediaMetadata({
      title: 'Chapter ' + ROMAN[cur] + ' · ' + (chapters[cur].section.querySelector('.ch-title') || {}).textContent,
      artist: 'H. G. Wells', album: 'The Sleeper Awakes',
      artwork: cover ? [{ src: cover.src, sizes: '832x1248', type: 'image/jpeg' }] : []
    });
    navigator.mediaSession.setActionHandler('play', function () { audio.play(); });
    navigator.mediaSession.setActionHandler('pause', function () { audio.pause(); });
    navigator.mediaSession.setActionHandler('seekbackward', function () { audio.currentTime -= 15; });
    navigator.mediaSession.setActionHandler('seekforward', function () { audio.currentTime += 15; });
  }

  /* ---------- UI ---------- */
  var ui = {};
  function el(tag, attrs, html) { var e = document.createElement(tag); for (var k in attrs) e.setAttribute(k, attrs[k]); if (html != null) e.innerHTML = html; return e; }
  var bar = el('div', { id: 'ra-bar', role: 'region', 'aria-label': 'Audiobook player', hidden: '' });
  bar.innerHTML =
    '<div class="ra-row">' +
    '<button class="ra-btn" data-a="back" aria-label="Back 15 seconds">↺15</button>' +
    '<button class="ra-btn ra-pp" data-a="pp" aria-label="Play">▶</button>' +
    '<button class="ra-btn" data-a="fwd" aria-label="Forward 15 seconds">15↻</button>' +
    '<div class="ra-mid"><div class="ra-title"></div><input class="ra-seek" type="range" min="0" max="1000" value="0" aria-label="Position in chapter"><div class="ra-time">0:00</div></div>' +
    '<select class="ra-rate" aria-label="Speed"><option value="0.8">0.8×</option><option value="0.9">0.9×</option><option value="1">1×</option><option value="1.15">1.15×</option><option value="1.3">1.3×</option><option value="1.5">1.5×</option></select>' +
    '<button class="ra-btn ra-aa" data-a="opts" aria-label="Reading options" aria-expanded="false">Aa</button>' +
    '</div>' +
    '<div class="ra-opts" hidden>' +
    '<label>Font <select data-o="font"><option value="serif">Book serif</option><option value="lexend">Lexend (easy-read)</option><option value="dyslexic">OpenDyslexic</option></select></label>' +
    '<label>Size <select data-o="size"><option value="1">Normal</option><option value="1.15">Large</option><option value="1.3">Larger</option></select></label>' +
    '<label>Spacing <select data-o="spacing"><option value="normal">Normal</option><option value="relaxed">Relaxed</option></select></label>' +
    '<label>Highlight <select data-o="hl"><option value="both">Word + sentence</option><option value="word">Word</option><option value="sentence">Sentence</option><option value="off">Off</option></select></label>' +
    '<label>Colour <select data-o="color"><option value="gold">Gold</option><option value="mint">Mint</option><option value="sky">Sky</option><option value="rose">Rose</option></select></label>' +
    '<label class="ra-check"><input type="checkbox" data-o="follow"> Follow along</label>' +
    '<label class="ra-check"><input type="checkbox" data-o="tap"> Tap a word to listen</label>' +
    '</div>';
  document.body.appendChild(bar);
  ui.pp = bar.querySelector('.ra-pp'); ui.title = bar.querySelector('.ra-title'); ui.time = bar.querySelector('.ra-time');
  ui.seek = bar.querySelector('.ra-seek'); ui.rate = bar.querySelector('.ra-rate'); ui.opts = bar.querySelector('.ra-opts');
  function showBar() { bar.hidden = false; document.body.classList.add('ra-has-bar'); }

  bar.addEventListener('click', function (e) {
    var a = e.target.getAttribute && e.target.getAttribute('data-a'); if (!a) return;
    if (a === 'pp') { if (cur == null) { var ok = store.ch && chapters[store.ch]; playChapter(ok ? store.ch : order[0], ok ? store.t : 0); } else if (audio.paused) audio.play(); else audio.pause(); }
    if (a === 'back') audio.currentTime = Math.max(0, audio.currentTime - 15);
    if (a === 'fwd') audio.currentTime = Math.min(audio.duration || 1e9, audio.currentTime + 15);
    if (a === 'opts') { ui.opts.hidden = !ui.opts.hidden; e.target.setAttribute('aria-expanded', String(!ui.opts.hidden)); }
  });
  ui.seek.addEventListener('input', function () { ui.seeking = true; if (audio.duration) audio.currentTime = ui.seek.value / 1000 * audio.duration; paint(); });
  ui.seek.addEventListener('change', function () { ui.seeking = false; userScrollAt = 0; });
  ui.rate.value = String(store.rate || 1);
  ui.rate.addEventListener('change', function () { store.rate = parseFloat(ui.rate.value); audio.playbackRate = store.rate; save(); });

  /* reading options */
  var defaults = { font: 'serif', size: '1', spacing: 'normal', hl: 'both', color: 'gold', follow: true, tap: true };
  function applyOpts() {
    var b = document.body;
    b.dataset.raFont = store.font || defaults.font;
    b.dataset.raSpacing = store.spacing || defaults.spacing;
    b.dataset.raColor = store.color || defaults.color;
    b.style.setProperty('--ra-scale', store.size || defaults.size);
    if (b.dataset.raFont === 'dyslexic' && !document.getElementById('ra-od')) {
      document.head.appendChild(el('link', { id: 'ra-od', rel: 'stylesheet', href: 'https://cdn.jsdelivr.net/npm/@fontsource/opendyslexic@5.3.0/index.css' }));
    }
    if (b.dataset.raFont === 'lexend' && !document.getElementById('ra-lx')) {
      document.head.appendChild(el('link', { id: 'ra-lx', rel: 'stylesheet', href: 'https://fonts.googleapis.com/css2?family=Lexend:wght@300;400&display=swap' }));
    }
    wi = -1; paint();
  }
  ui.opts.querySelectorAll('[data-o]').forEach(function (inp) {
    var k = inp.dataset.o, v = store[k] != null ? store[k] : defaults[k];
    if (inp.type === 'checkbox') inp.checked = v !== false; else inp.value = String(v);
    inp.addEventListener('change', function () {
      store[k] = inp.type === 'checkbox' ? inp.checked : inp.value; save(); applyOpts();
    });
  });
  applyOpts();

  /* per-chapter "listen" buttons + hero buttons */
  document.querySelectorAll('[data-ra-play]').forEach(function (b) {
    b.addEventListener('click', function () { userScrollAt = 0; playChapter(parseInt(b.dataset.raPlay, 10), 0); });
  });

  /* resume prompt */
  var resume = document.getElementById('ra-resume');
  if (resume) {
    var html = [];
    if (store.ch && chapters[store.ch] && store.t > 5)
      html.push('<button class="ra-pill" data-go="listen">▶ Keep listening — Chapter ' + ROMAN[store.ch] + ' at ' + fmt(store.t) + '</button>');
    if (store.place) {
      var parts = store.place.split(':'), sec = document.getElementById(parts[0]);
      if (sec && sec.querySelector('p[data-p="' + parts[1] + '"]'))
        html.push('<button class="ra-pill ra-pill--ghost" data-go="read">↧ Jump to where you were reading (Chapter ' + ROMAN[parseInt(parts[0].slice(3), 10)] + ')</button>');
    }
    if (html.length) {
      resume.innerHTML = html.join('');
      resume.hidden = false;
      resume.addEventListener('click', function (e) {
        var go = e.target.getAttribute('data-go');
        if (go === 'listen') { userScrollAt = 0; playChapter(store.ch, store.t); }
        if (go === 'read') {
          var parts = store.place.split(':');
          var p = document.getElementById(parts[0]).querySelector('p[data-p="' + parts[1] + '"]');
          p.scrollIntoView({ block: 'start' }); window.scrollBy(0, -80);
        }
      });
    }
  }
  if (store.ch && chapters[store.ch]) { showBar(); ui.title.textContent = 'Chapter ' + ROMAN[store.ch]; }
  document.addEventListener('keydown', function (e) {
    if (e.target.matches('input,select,textarea') || bar.hidden) return;
    if (e.code === 'Space' && cur != null) { e.preventDefault(); if (audio.paused) audio.play(); else audio.pause(); }
  });
})();
