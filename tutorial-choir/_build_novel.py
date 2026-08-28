#!/usr/bin/env python3
"""Build the web novel.html for sean-makes-stuff/books/tutorial-choir/.

Reads chapter text + beat manifests from scriptorium, writes a web-styled
novel.html with .jpg paths, embedded full-audiobook player + per-chapter players,
and Sean Makes Stuff CSS conventions adapted to the Mezieres BD-watercolor look."""
import json
import re
from pathlib import Path
from html import escape

SRC = Path("/Users/seansp/git/scriptorium/tutorial-choir")
DST = Path("/Users/seansp/git/sean-makes-stuff/books/tutorial-choir")
TITLE = "The Console Conjurers"
SUBTITLE = "a short illustrated tutorial on setting up the agentic-AI workstation"
AUTHOR = "by Sean Spratt"

CHAPTER_TITLES = {
    1: "The Empty Console",
    2: "Homebrew, the Foundation",
    3: "The Claude in Your Terminal",
    4: "The Choir Materializes",
    5: "The Spellbook — Adding a Skill",
    6: "The Drawing Hack",
    7: "Cooking the Game — PROCESS.md",
    8: "Press Play",
}

POS_MAP = {"opening": 0.02, "early": 0.18, "midchapter": 0.40,
           "turning": 0.55, "climax": 0.78, "closing": 0.96}


def load_chapter(n):
    nn = f"{n:02d}"
    body = (SRC / f"chapters/{nn}/chosen.md").read_text()
    body = re.sub(r"^#\s*[^\n]+\n+", "", body, count=1).strip()
    # Read beats.json directly so screenshot/terminal beats are picked up too
    raw_beats = json.loads((SRC / f"chapters/{nn}/images/beats.json").read_text())["beats"]
    beats = []
    wc_idx = 0
    for b in raw_beats:
        kind = b.get("type", "watercolor")
        if kind == "watercolor":
            wc_idx += 1
            wc_file = f"beat_{wc_idx:02d}.jpeg"
            wc_path = SRC / f"chapters/{nn}/images/_candidates/{wc_file}"
            if not wc_path.exists() or wc_path.stat().st_size == 0:
                continue
            beats.append({
                "type": "watercolor",
                "file": wc_file,
                "scene_name": b.get("scene_name", ""),
                "position": b.get("page_position", "midchapter"),
            })
        elif kind == "screenshot":
            beats.append({
                "type": "screenshot",
                "file": b.get("file", ""),
                "scene_name": b.get("scene_name", ""),
                "position": b.get("page_position", "midchapter"),
                "alt": b.get("alt", ""),
                "caption": b.get("caption", ""),
            })
        elif kind == "terminal":
            beats.append({
                "type": "terminal",
                "text": b.get("text", ""),
                "scene_name": b.get("scene_name", ""),
                "position": b.get("page_position", "midchapter"),
                "caption": b.get("caption", ""),
            })
    return {"n": n, "title": CHAPTER_TITLES[n], "raw": body, "beats": beats}


def split_paragraphs(body):
    """Split body into a list of paragraphs and code-fence blocks."""
    parts = []
    buf = []
    in_code = False
    for line in body.splitlines():
        if line.strip().startswith("```"):
            if not in_code:
                if buf:
                    parts.append("\n".join(buf).strip())
                    buf = []
                buf.append(line)
                in_code = True
            else:
                buf.append(line)
                parts.append("\n".join(buf))
                buf = []
                in_code = False
            continue
        if in_code:
            buf.append(line)
            continue
        if line.strip() == "":
            if buf:
                parts.append("\n".join(buf).strip())
                buf = []
        else:
            buf.append(line)
    if buf:
        parts.append("\n".join(buf).strip())
    return [p for p in parts if p]


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
    if p.startswith("```"):
        lines = p.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        code = "\n".join(lines)
        return f'<pre><code>{escape(code)}</code></pre>'
    h = escape(p)
    h = re.sub(r"\*([^*\n]+)\*", r"<em>\1</em>", h)
    h = re.sub(r"`([^`]+)`", r"<code>\1</code>", h)
    return f"<p>{h}</p>"


def render_chapter(ch, is_first):
    n = ch["n"]
    nn = f"{n:02d}"
    paragraphs = split_paragraphs(ch["raw"])
    insertions = interleave(paragraphs, ch["beats"])
    out = [f'<section id="ch-{nn}" class="chapter{" chapter--first" if is_first else ""}">']
    out.append(f'  <div class="ch-head"><div class="ch-num">Step {n}</div><h2 class="ch-title">{escape(ch["title"])}</h2></div>')
    out.append(f'''  <div class="audio-chapter">
    <div class="audio-chapter__icon">🎧</div>
    <div class="audio-chapter__label">Listen · Step {n}</div>
    <audio controls preload="none" src="audio/chapter_{nn}.mp3"></audio>
  </div>''')
    out.append('  <div class="narrative">')
    for i, para in enumerate(paragraphs):
        out.append(f"    {render_paragraph(para)}")
        if i in insertions:
            for b in insertions[i]:
                kind = b.get("type", "watercolor")
                if kind == "screenshot":
                    cap = b.get("caption", "")
                    out.append(
                        f'    <figure class="screenshot-figure">'
                        f'<div class="screenshot-frame"><img src="screenshots/{escape(b["file"])}" alt="{escape(b.get("alt", b.get("scene_name", "")))}" loading="lazy" /></div>'
                        f'<figcaption><strong>{escape(b.get("scene_name", ""))}</strong>'
                        f'{(" — " + escape(cap)) if cap else ""}</figcaption>'
                        f'</figure>'
                    )
                elif kind == "terminal":
                    cap = b.get("caption", "")
                    out.append(
                        f'    <figure class="terminal-figure">'
                        f'<div class="terminal-frame">'
                        f'<div class="terminal-dots"><span></span><span></span><span></span></div>'
                        f'<pre>{escape(b.get("text", ""))}</pre>'
                        f'</div>'
                        f'<figcaption><strong>{escape(b.get("scene_name", ""))}</strong>'
                        f'{(" — " + escape(cap)) if cap else ""}</figcaption>'
                        f'</figure>'
                    )
                else:
                    fname = b["file"].replace(".jpeg", ".jpg").replace(".png", ".jpg")
                    out.append(
                        f'    <figure class="beat-figure">'
                        f'<img src="illustrations/ch{nn}/{escape(fname)}" alt="{escape(b.get("scene_name",""))}" loading="lazy" />'
                        f'<figcaption>{escape(b.get("scene_name", ""))}</figcaption>'
                        f'</figure>'
                    )
    out.append('  </div>')
    out.append('</section>')
    return "\n".join(out)


chapters = [load_chapter(n) for n in range(1, 9)]
total_words = sum(len(c["raw"].split()) for c in chapters)
total_beats = sum(len(c["beats"]) for c in chapters)


def get_audio_min():
    try:
        import subprocess
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(DST / "audio" / "audiobook.mp3")],
            capture_output=True, text=True,
        ).stdout.strip()
        return int(float(out) // 60) if out else 0
    except Exception:
        return 0


AUDIO_MIN = get_audio_min() or 40
AUDIO_SIZE_MB = (DST / "audio" / "audiobook.mp3").stat().st_size // (1024 * 1024) if (DST / "audio" / "audiobook.mp3").exists() else 0

toc_html = "\n".join(
    f'      <li><a href="#ch-{c["n"]:02d}"><span class="toc__num">{c["n"]}.</span> {escape(c["title"])}</a></li>'
    for c in chapters
)
chapters_html = "\n\n".join(render_chapter(c, i == 0) for i, c in enumerate(chapters))


CSS = """
:root {
  --paper: #f4eddd;
  --paper-border: #c4b489;
  --ink: #1d1d1f;
  --ink-soft: #6e6e73;
  --accent-rust: #b1593a;
  --accent-gold: #c69b3c;
  --slate: #3f6a82;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: var(--paper); font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", Helvetica, Arial, sans-serif; color: var(--ink); }
.book-nav {
  position: sticky; top: 0; z-index: 50;
  background: rgba(244,237,221,0.95); backdrop-filter: blur(4px);
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
.meet { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin: 32px 0 40px; }
.meet figure { margin: 0; text-align: center; }
.meet img { width: 100%; aspect-ratio: 1; object-fit: cover; border-radius: 12px; border: 1px solid var(--paper-border); background: var(--paper); }
.meet figcaption { margin-top: 10px; font-family: "Iowan Old Style", serif; }
.meet figcaption strong { display: block; font-size: 1rem; color: var(--ink); }
.meet figcaption em { display: block; color: var(--ink-soft); font-size: 0.86rem; margin-top: 4px; font-style: italic; }
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
.narrative code { font-family: "SF Mono", "Menlo", monospace; background: rgba(63,106,130,0.13); padding: 0.05em 0.32em; border-radius: 4px; color: var(--ink); font-size: 0.92em; }
.narrative pre { background: #1d1814; color: #f6e5c3; padding: 14px 18px; border-radius: 8px; overflow-x: auto; margin: 18px 0; font-family: "SF Mono", "Menlo", monospace; font-size: 0.84rem; line-height: 1.45; border: 1px solid #2b211a; }
.narrative pre code { background: transparent; padding: 0; color: inherit; font-size: inherit; }
.beat-figure { margin: 32px -20px; }
.beat-figure img { width: 100%; border-radius: 10px; border: 1px solid var(--paper-border); background: var(--paper); display: block; }
.beat-figure figcaption { margin-top: 8px; font-size: 0.85rem; font-style: italic; color: var(--ink-soft); text-align: center; font-family: "Iowan Old Style", serif; }
.screenshot-figure { margin: 32px -20px; text-align: center; }
.screenshot-frame { display: block; padding: 26px 4px 4px; background: linear-gradient(#ded2b5, #d4c8a8); border-radius: 12px 12px 8px 8px; border: 1px solid var(--paper-border); position: relative; box-shadow: 0 6px 22px rgba(40,28,18,0.14); }
.screenshot-frame::before { content: ""; position: absolute; top: 9px; left: 14px; width: 10px; height: 10px; border-radius: 50%; background: #d27d6b; box-shadow: 18px 0 0 #e3b56b, 36px 0 0 #95b67a; }
.screenshot-frame img { width: 100%; height: auto; display: block; border-radius: 4px; }
.screenshot-figure figcaption { margin-top: 10px; font-size: 0.88rem; font-style: italic; color: var(--ink-soft); text-align: center; font-family: "Iowan Old Style", serif; line-height: 1.5; padding: 0 18px; }
.screenshot-figure figcaption strong { color: var(--ink); font-style: normal; }
.terminal-figure { margin: 32px -20px; text-align: center; }
.terminal-frame { display: block; padding: 28px 18px 18px; background: #1d1814; border-radius: 12px 12px 8px 8px; border: 1px solid #2b211a; position: relative; text-align: left; box-shadow: 0 6px 22px rgba(40,28,18,0.18); }
.terminal-dots { position: absolute; top: 11px; left: 14px; display: flex; gap: 6px; }
.terminal-dots span { width: 11px; height: 11px; border-radius: 50%; display: inline-block; }
.terminal-dots span:nth-child(1) { background: #ff5f57; }
.terminal-dots span:nth-child(2) { background: #febc2e; }
.terminal-dots span:nth-child(3) { background: #28c840; }
.terminal-frame pre { background: transparent; color: #f6e5c3; font-family: "SF Mono", "Menlo", monospace; font-size: 0.84rem; line-height: 1.5; margin: 0; padding: 0; border: 0; overflow-x: auto; white-space: pre; }
.terminal-figure figcaption { margin-top: 10px; font-size: 0.88rem; font-style: italic; color: var(--ink-soft); text-align: center; font-family: "Iowan Old Style", serif; line-height: 1.5; padding: 0 18px; }
.terminal-figure figcaption strong { color: var(--ink); font-style: normal; }
.back-matter { margin-top: 96px; padding-top: 32px; border-top: 1px solid var(--paper-border); text-align: center; color: var(--ink-soft); font-family: "Iowan Old Style", serif; font-style: italic; font-size: 0.95rem; }
@media (max-width: 540px) {
  .meet { grid-template-columns: 1fr; }
  .cover__title { font-size: 2.2rem; }
}
"""

audio_label = f"🎧 Full audiobook · {AUDIO_MIN} min · 3 voices · 8 chapter markers"

html_doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{escape(TITLE)} — Sean Makes Stuff</title>
<meta name="description" content="A short illustrated technical tutorial in 8 steps — Mezieres-watercolor panels, {total_beats} hand-painted beats, a {AUDIO_MIN}-minute audiobook narrated by 3 distinct voices. Lor and Vex set up Claude Code, Choir, skills, the image-gen hack, and PROCESS.md for solo D&D.">
<style>{CSS}</style>
</head>
<body>
<nav class="book-nav">
  <span class="label">{escape(TITLE)} · {total_words:,} words · {total_beats} illustrations · {AUDIO_MIN} min audio</span>
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
    <div class="audio-hero__label">{audio_label}</div>
    <audio controls preload="none" src="audio/audiobook.mp3"></audio>
    <a class="audio-hero__download" href="audio/audiobook.mp3" download>⬇ Download MP3<small>~{AUDIO_SIZE_MB} MB · open in a podcast app to see chapters</small></a>
  </div>

  <section class="meet">
    <figure>
      <img src="characters/lor.jpg" alt="Lor" />
      <figcaption><strong>Lor</strong><em>the methodical one · reads the docs</em></figcaption>
    </figure>
    <figure>
      <img src="characters/vex.jpg" alt="Vex" />
      <figcaption><strong>Vex</strong><em>the chaotic enthusiast · types first</em></figcaption>
    </figure>
    <figure>
      <img src="characters/cricket.jpg" alt="Cricket" />
      <figcaption><strong>Cricket</strong><em>cat · supervisor</em></figcaption>
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
    <p>Process beats prompt. Anything with an HTTP endpoint can be a tool. Now go press play on something of your own.</p>
  </section>
</main>
</body>
</html>
"""

out = DST / "novel.html"
out.write_text(html_doc)
print(f"wrote {out} ({len(html_doc):,} bytes)")
print(f"  {total_words:,} words, {total_beats} beats, {len(chapters)} chapters")
