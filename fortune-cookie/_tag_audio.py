#!/usr/bin/env python3
"""
Tag the published 64-kbps web audiobook.mp3 + per-chapter mp3s with full ID3v2.3:
  - APIC cover artwork
  - Title / Album / Artist / Composer / Genre / Year
  - For audiobook.mp3: CHAP × 18 + CTOC (re-imported from source if absent)
  - For chapter_NN.mp3: TRCK track number + chapter-specific title

Run AFTER _copy_assets.sh (and after the audiobook has been re-encoded for web).
"""
import json, re, sys
from pathlib import Path
from mutagen.mp3 import MP3
from mutagen.id3 import (ID3, APIC, CHAP, CTOC, CTOCFlags, TIT2, TIT3, TALB,
                          TPE1, TPE2, TCON, TYER, TCOM, COMM, TLAN, TRCK)

SRC  = Path("/Users/seansp/git/scriptorium/fortune-cookie")
DST  = Path("/Users/seansp/git/sean-makes-stuff/books/fortune-cookie")
TITLE = "The Empty Jar"
SUBTITLE = "a fortune-cookie novel"
ARTIST = "Scriptorium"
COMPOSER = "Sean Spratt"
GENRE = "Audiobook"
YEAR = "2026"
COMMENT = "An illustrated middle-grade novel — 18 chapters, 143 Inksmoke illustrations, narrated with 10 voices."

art_bytes = (DST / "storyboard" / "cover.jpg").read_bytes()
print(f"cover: {len(art_bytes):,} bytes")

# Pull source chapter list for titles
titles = {}
for n in range(1, 19):
    text = (SRC / f"chapters/{n:02d}/chosen.md").read_text()
    m = re.search(r"^title:\s*(.+)$", text, re.MULTILINE)
    titles[n] = m.group(1).strip() if m else f"Chapter {n}"

def common_tags(id3, title_text, track_num=None, total_tracks=18):
    id3.setall("TIT2", [TIT2(encoding=3, text=title_text)])
    id3.setall("TIT3", [TIT3(encoding=3, text=SUBTITLE)])
    id3.setall("TALB", [TALB(encoding=3, text=TITLE)])
    id3.setall("TPE1", [TPE1(encoding=3, text=ARTIST)])
    id3.setall("TPE2", [TPE2(encoding=3, text=ARTIST)])
    id3.setall("TCOM", [TCOM(encoding=3, text=COMPOSER)])
    id3.setall("TCON", [TCON(encoding=3, text=GENRE)])
    id3.setall("TYER", [TYER(encoding=3, text=YEAR)])
    id3.setall("TLAN", [TLAN(encoding=3, text="eng")])
    id3.delall("COMM")
    id3.add(COMM(encoding=3, lang="eng", desc="", text=COMMENT))
    id3.delall("APIC")
    id3.add(APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover (front)", data=art_bytes))
    if track_num is not None:
        id3.setall("TRCK", [TRCK(encoding=3, text=f"{track_num}/{total_tracks}")])

# --- Tag the master web audiobook ---
master_path = DST / "audio" / "audiobook.mp3"
print(f"\ntagging {master_path.name} ...")
mp3 = MP3(master_path)
if mp3.tags is None: mp3.add_tags()
id3 = mp3.tags
common_tags(id3, TITLE)

# Restore CHAP + CTOC from the scriptorium source's tag set (source has them; re-encode dropped them)
src_mp3 = MP3(SRC / "audiobook.mp3")
chap_keys = sorted([k for k in src_mp3.tags if k.startswith("CHAP")])
for k in chap_keys:
    src_chap = src_mp3.tags[k]
    # Copy CHAP wholesale
    id3.add(CHAP(
        element_id=src_chap.element_id,
        start_time=src_chap.start_time,
        end_time=src_chap.end_time,
        start_offset=src_chap.start_offset,
        end_offset=src_chap.end_offset,
        sub_frames=src_chap.sub_frames,
    ))
src_ctoc_key = next((k for k in src_mp3.tags if k.startswith("CTOC")), None)
if src_ctoc_key:
    src_ctoc = src_mp3.tags[src_ctoc_key]
    new_ctoc = CTOC(
        element_id=src_ctoc.element_id,
        flags=CTOCFlags.TOP_LEVEL | CTOCFlags.ORDERED,
        child_element_ids=list(src_ctoc.child_element_ids),
    )
    new_ctoc.sub_frames["TIT2"] = TIT2(encoding=3, text="Chapters")
    id3.add(new_ctoc)
    print(f"  imported {len(src_ctoc.child_element_ids)} CHAP frames + CTOC from scriptorium source")

mp3.save(v2_version=3)
print(f"  saved ({master_path.stat().st_size/1024/1024:.1f} MB)")

# --- Tag each per-chapter mp3 ---
print("\nper-chapter mp3s:")
for n in range(1, 19):
    p = DST / "audio" / f"chapter_{n:02d}.mp3"
    if not p.exists(): continue
    mp3 = MP3(p)
    if mp3.tags is None: mp3.add_tags()
    chapter_title = f"{n:02d}. {titles[n]}"
    common_tags(mp3.tags, chapter_title, track_num=n, total_tracks=18)
    mp3.save(v2_version=3)
    print(f"  ch{n:02d} {titles[n][:40]:40s} → tagged ({p.stat().st_size/1024:.0f} KB)")

print("\ndone.")
