#!/usr/bin/env python3
"""Build the web novel.html for sean-makes-stuff/books/maillard-crust-tutorial/.

Reads chapter text + beat manifests from scriptorium, writes a web-styled
novel.html with .jpg paths, embedded full-audiobook player + per-chapter players,
and Sean Makes Stuff CSS conventions."""
import json
import re
from pathlib import Path
from html import escape

SRC = Path("/Users/seansp/git/scriptorium/maillard-crust-tutorial")
DST = Path("/Users/seansp/git/sean-makes-stuff/books/maillard-crust-tutorial")
TITLE = "The Maillard Affair"
SUBTITLE = "a short illustrated tutorial on the perfect New York strip"
AUTHOR = "by Sean Spratt"

CHAPTER_TITLES = {
    1: "Cold Open", 2: "Reading the Steak", 3: "Salting Theory",
    4: "Pan & Heat", 5: "The Sear", 6: "Butter, Garlic, Thyme",
    7: "Probe & Rest", 8: "Slice & Settle",
}

POS_MAP = {"opening": 0.02, "early": 0.18, "midchapter": 0.40,
           "turning": 0.55, "climax": 0.78, "closing": 0.96}


def load_chapter(n):
    nn = f"{n:02d}"
    body = (SRC / f"chapters/{nn}/chosen.md").read_text()
    # Strip leading "# Chapter N — ..." heading
    body = re.sub(r"^#\s*[^\n]+\n+", "", body, count=1).strip()
    paragraphs = [p.strip() for p in re.split(r"\n\n+", body) if p.strip()]
    manifest = json.loads((SRC / f"chapters/{nn}/images/_beats_manifest.json").read_text())
    return {"n": n, "title": CHAPTER_TITLES[n], "paragraphs": paragraphs, "beats": manifest}


def interleave(paragraphs, beats):
    n_para = max(len(paragraphs), 1)
    placed = []
    for b in beats:
        pos = POS_MAP.get(b.get("position", "midchapter"), 0.5)
        t = max(0, min(n_para - 1, int(round(pos * (n_para - 1)))))
        placed.append([t, b])
    placed.sort(key=lambda x: x[0])
    used = set()
    final = {}
    for t, b in placed:
        while t in used and t < n_para - 1:
            t += 1
        used.add(t)
        final.setdefault(t, []).append(b)
    return final


def render_paragraph(p):
    h = escape(p)
    h = re.sub(r"\*([^*\n]+)\*", r"<em>\1</em>", h)
    return f"<p>{h}</p>"


def render_chapter(ch, is_first):
    n = ch["n"]
    nn = f"{n:02d}"
    insertions = interleave(ch["paragraphs"], ch["beats"])
    out = [f'<section id="ch-{nn}" class="chapter{" chapter--first" if is_first else ""}">']
    out.append(f'  <div class="ch-head"><div class="ch-num">Step {n}</div><h2 class="ch-title">{escape(ch["title"])}</h2></div>')
    out.append(f'''  <div class="audio-chapter">
    <div class="audio-chapter__icon">🎧</div>
    <div class="audio-chapter__label">Listen · Step {n}</div>
    <audio controls preload="none" src="audio/chapter_{nn}.mp3"></audio>
  </div>''')
    out.append('  <div class="narrative">')
    for i, para in enumerate(ch["paragraphs"]):
        out.append(f"    {render_paragraph(para)}")
        if i in insertions:
            for b in insertions[i]:
                fname = b["file"].replace(".jpeg", ".jpg").replace(".png", ".jpg")
                cap = b.get("scene_name", "")
                out.append(
                    f'    <figure class="beat-figure">'
                    f'<img src="illustrations/ch{nn}/{escape(fname)}" alt="{escape(b.get("scene_name",""))}" loading="lazy" />'
                    f'<figcaption>{escape(cap)}</figcaption>'
                    f'</figure>'
                )
    out.append('  </div>')
    out.append('</section>')
    return "\n".join(out)


chapters = [load_chapter(n) for n in range(1, 9)]
total_words = sum(sum(len(p.split()) for p in c["paragraphs"]) for c in chapters)
total_beats = sum(len(c["beats"]) for c in chapters)

toc_html = "\n".join(
    f'      <li><a href="#ch-{c["n"]:02d}"><span class="toc__num">{c["n"]}.</span> {escape(c["title"])}</a></li>'
    for c in chapters
)
chapters_html = "\n\n".join(render_chapter(c, i == 0) for i, c in enumerate(chapters))

CSS = """
:root {
  --paper: #f3ede0;
  --paper-border: #c4b489;
  --ink: #1d1d1f;
  --ink-soft: #6e6e73;
  --accent-rust: #8b2f1d;
  --accent-gold: #c69b3c;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: var(--paper); font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", Helvetica, Arial, sans-serif; color: var(--ink); }
.book-nav {
  position: sticky; top: 0; z-index: 50;
  background: rgba(243,237,224,0.95); backdrop-filter: blur(4px);
  border-bottom: 1px solid var(--paper-border);
  padding: 14px 24px;
  display: flex; align-items: center; gap: 16px;
  font-family: "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif;
  font-size: 0.92rem;
  color: var(--ink-soft);
}
.book-nav .label { flex: 1; font-style: italic; }
.book-nav a { color: var(--accent-rust); text-decoration: none; border-bottom: 1px solid transparent; }
.book-nav a:hover { border-bottom-color: var(--accent-rust); }
main.book { max-width: 760px; margin: 0 auto; padding: 16px 24px 96px; }
.cover { margin: 16px 0 32px; }
.cover__art { width: 100%; aspect-ratio: 1/1; background: var(--paper); border: 1px solid var(--paper-border); border-radius: 14px; overflow: hidden; }
.cover__art img { width: 100%; height: 100%; object-fit: contain; display: block; }
.cover__title { font-family: "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif; font-size: 3rem; line-height: 1.1; color: var(--ink); margin: 32px 0 8px; text-align: center; }
.cover__subtitle { font-family: "Iowan Old Style", serif; font-size: 1.05rem; color: var(--ink-soft); text-align: center; font-style: italic; }
.cover__author { font-family: "Iowan Old Style", serif; font-size: 1.05rem; color: var(--ink-soft); text-align: center; margin-top: 8px; }
.meet { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 32px 0 40px; }
.meet figure { margin: 0; text-align: center; }
.meet img { width: 100%; aspect-ratio: 1; object-fit: cover; border-radius: 12px; border: 1px solid var(--paper-border); background: var(--paper); }
.meet figcaption { margin-top: 10px; font-family: "Iowan Old Style", serif; }
.meet figcaption strong { display: block; font-size: 1.05rem; color: var(--ink); }
.meet figcaption em { display: block; color: var(--ink-soft); font-size: 0.9rem; margin-top: 4px; font-style: italic; }
.audio-hero { margin: 16px 0 32px; padding: 18px 20px; background: #fff; border: 1px solid var(--paper-border); border-radius: 10px; display: flex; align-items: center; gap: 18px; flex-wrap: wrap; font-family: "Iowan Old Style", serif; }
.audio-hero__label { font-style: italic; color: var(--ink-soft); font-size: 0.95rem; }
.audio-hero audio { flex: 1; min-width: 260px; }
.audio-hero__download { font-family: "Iowan Old Style", serif; font-size: 0.9rem; color: var(--accent-rust); text-decoration: none; padding: 8px 14px; border: 1px solid var(--paper-border); border-radius: 8px; background: var(--paper); white-space: nowrap; }
.audio-hero__download:hover { background: var(--accent-gold); color: var(--ink); border-color: var(--accent-gold); }
.audio-hero__download small { display: block; font-size: 0.72rem; font-style: italic; color: var(--ink-soft); margin-top: 2px; }
.audio-hero__download:hover small { color: var(--ink); }
.toc { margin: 32px 0 56px; padding: 24px 28px; background: #fff; border: 1px solid var(--paper-border); border-radius: 10px; }
.toc h2 { font-family: "Iowan Old Style", serif; font-size: 1.4rem; margin-bottom: 14px; }
.toc ol { list-style: none; font-family: "Iowan Old Style", serif; }
.toc li { padding: 6px 0; border-bottom: 1px dotted var(--paper-border); }
.toc li:last-child { border-bottom: 0; }
.toc a { color: var(--ink); text-decoration: none; display: block; }
.toc a:hover { color: var(--accent-rust); }
.toc__num { display: inline-block; width: 32px; color: var(--ink-soft); }
.chapter { margin-top: 64px; }
.chapter--first { margin-top: 24px; }
.ch-head { text-align: center; margin-bottom: 32px; }
.ch-num { font-family: "Iowan Old Style", serif; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.2em; color: var(--accent-rust); margin-bottom: 12px; }
.ch-title { font-family: "Iowan Old Style", serif; font-size: 2.2rem; color: var(--ink); }
.audio-chapter { margin: 0 -20px 24px; padding: 12px 16px; background: #fff; border: 1px solid var(--paper-border); border-radius: 8px; display: flex; align-items: center; gap: 14px; font-family: "Iowan Old Style", serif; }
.audio-chapter__icon { font-size: 1.3rem; }
.audio-chapter__label { font-style: italic; color: var(--ink-soft); font-size: 0.9rem; min-width: 120px; }
.audio-chapter audio { flex: 1; min-width: 200px; }
.narrative { font-family: "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif; font-size: 1.08rem; line-height: 1.74; }
.narrative p { margin: 0 0 1.05em; }
.narrative p:first-of-type::first-letter { font-family: "Iowan Old Style", serif; font-size: 3.4rem; float: left; line-height: 0.92; padding-right: 10px; padding-top: 4px; color: var(--accent-rust); }
.beat-figure { margin: 32px -20px; }
.beat-figure img { width: 100%; border-radius: 10px; border: 1px solid var(--paper-border); background: var(--paper); display: block; }
.beat-figure figcaption { margin-top: 8px; font-size: 0.85rem; font-style: italic; color: var(--ink-soft); text-align: center; font-family: "Iowan Old Style", serif; }
.back-matter { margin-top: 96px; padding-top: 32px; border-top: 1px solid var(--paper-border); text-align: center; color: var(--ink-soft); font-family: "Iowan Old Style", serif; font-style: italic; font-size: 0.95rem; }
@media (max-width: 540px) {
  .meet { grid-template-columns: 1fr; }
  .cover__title { font-size: 2.2rem; }
}
"""

AUDIO_LABEL = "🎧 Full audiobook · 33 min · 3 voices · 8 chapter markers"

html_doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{escape(TITLE)} — Sean Makes Stuff</title>
<meta name="description" content="A short illustrated cooking tutorial in 8 steps with 66 hand-painted watercolor beats and a 33-minute audiobook narrated with 3 distinct voices.">
<style>{CSS}</style>
</head>
<body>
<nav class="book-nav">
  <span class="label">{escape(TITLE)} · {total_words:,} words · {total_beats} illustrations · 33 min audio</span>
  <a href="../../">Sean Makes Stuff</a>
</nav>
<main class="book">
  <section class="cover">
    <div class="cover__art"><img src="storyboard/cover.jpg" alt="Cover" /></div>
    <h1 class="cover__title">{escape(TITLE)}</h1>
    <p class="cover__subtitle">{escape(SUBTITLE)}</p>
    <p class="cover__author">{escape(AUTHOR)}</p>
  </section>

  <div class="audio-hero">
    <div class="audio-hero__label">{AUDIO_LABEL}</div>
    <audio controls preload="none" src="audio/audiobook.mp3"></audio>
    <a class="audio-hero__download" href="audio/audiobook.mp3" download>⬇ Download MP3<small>~16 MB · open in a podcast app to see chapters</small></a>
  </div>

  <section class="meet">
    <figure>
      <img src="characters/mara.jpg" alt="Mara" />
      <figcaption><strong>Mara</strong><em>the meticulous one · believes in reverse sear</em></figcaption>
    </figure>
    <figure>
      <img src="characters/theo.jpg" alt="Theo" />
      <figcaption><strong>Theo</strong><em>the enthusiastic one · believes in forward sear</em></figcaption>
    </figure>
  </section>

  <nav class="toc">
    <h2>The eight steps</h2>
    <ol>
{toc_html}
    </ol>
  </nav>

{chapters_html}

  <section class="back-matter">
    <p>Cook with someone you like. Lay everything out. Let the pan get hot. Don't poke it. Let it rest. Eat together.</p>
  </section>
</main>
</body>
</html>
"""

out = DST / "novel.html"
out.write_text(html_doc)
print(f"wrote {out} ({len(html_doc):,} bytes)")
print(f"  {total_words:,} words, {total_beats} beats, {len(chapters)} chapters")
