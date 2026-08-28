#!/usr/bin/env python3
"""Tag the web 64-kbps audiobook.mp3 + per-chapter mp3s with ID3v2.3:
APIC + Title/Album/Artist/Composer/Genre/Year, CHAP×8 + CTOC re-imported
from the scriptorium-side master (re-encode drops them)."""

from pathlib import Path
from mutagen.mp3 import MP3
from mutagen.id3 import (APIC, CHAP, CTOC, CTOCFlags, TIT2, TIT3, TALB,
                          TPE1, TPE2, TCON, TYER, TCOM, COMM, TLAN, TRCK)

SRC = Path("/Users/seansp/git/scriptorium/tutorial-choir")
DST = Path("/Users/seansp/git/sean-makes-stuff/books/tutorial-choir")
TITLE = "The Console Conjurers"
SUBTITLE = "a short illustrated tutorial on setting up the agentic-AI workstation"
ARTIST = "Scriptorium"
COMPOSER = "Sean Spratt"
GENRE = "Audiobook"
YEAR = "2026"
COMMENT = "A short illustrated tutorial — Lor and Vex set up Claude Code, the Choir CLI, skills, the image-gen hack, and a PROCESS.md that runs a solo D&D game."

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

art_bytes = (DST / "storyboard" / "cover.jpg").read_bytes()
print(f"cover: {len(art_bytes):,} bytes")


def common_tags(id3, title_text, track_num=None, total_tracks=8):
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


master_path = DST / "audio" / "audiobook.mp3"
print(f"\ntagging {master_path.name} …")
mp3 = MP3(master_path)
if mp3.tags is None:
    mp3.add_tags()
id3 = mp3.tags
common_tags(id3, TITLE)

src_mp3 = MP3(SRC / "audiobook.mp3")
chap_keys = sorted([k for k in src_mp3.tags if k.startswith("CHAP")])
for k in chap_keys:
    src_chap = src_mp3.tags[k]
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
    print(f"  imported {len(src_ctoc.child_element_ids)} CHAP frames + CTOC from source")

mp3.save(v2_version=3)
print(f"  saved ({master_path.stat().st_size/1024/1024:.1f} MB)")

print("\nper-chapter mp3s:")
for n in range(1, 9):
    p = DST / "audio" / f"chapter_{n:02d}.mp3"
    if not p.exists():
        continue
    mp3 = MP3(p)
    if mp3.tags is None:
        mp3.add_tags()
    chapter_title = f"{n:02d}. {CHAPTER_TITLES[n]}"
    common_tags(mp3.tags, chapter_title, track_num=n, total_tracks=8)
    mp3.save(v2_version=3)
    print(f"  ch{n:02d} {CHAPTER_TITLES[n][:40]:40s} → tagged ({p.stat().st_size/1024:.0f} KB)")

print("\ndone.")
