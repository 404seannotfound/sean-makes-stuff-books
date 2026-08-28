#!/usr/bin/env bash
# Copy fortune-cookie assets from scriptorium → sean-makes-stuff for web delivery.
# Source assets are already JPEG (genimg.sh writes .jpeg), so no PNG→JPG conversion needed.
set -uo pipefail
SRC=/Users/seansp/git/scriptorium/fortune-cookie
DST=/Users/seansp/git/sean-makes-stuff/books/fortune-cookie

mkdir -p "$DST"/{storyboard,characters,audio,illustrations,chapters}

# Cover
cp "$SRC/storyboard/chosen/cover.jpeg" "$DST/storyboard/cover.jpg"

# Character portraits (chosen ones)
for f in "$SRC/characters/"*/chosen.jpeg; do
  name=$(basename "$(dirname "$f")")
  cp "$f" "$DST/characters/$name.jpg"
done

# Chapter beat illustrations
for n in 01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18; do
  mkdir -p "$DST/illustrations/ch$n"
  for f in "$SRC/chapters/$n/images/_candidates/"beat_*.jpeg; do
    base=$(basename "$f" .jpeg)
    cp "$f" "$DST/illustrations/ch$n/$base.jpg"
  done
done

# Audio
cp "$SRC/audiobook.mp3" "$DST/audio/audiobook.mp3"
cp "$SRC/audio/chapters/"chapter_*.mp3 "$DST/audio/"

# Manifests + chapter text
for n in 01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18; do
  cp "$SRC/chapters/$n/images/_beats_manifest.json" "$DST/illustrations/ch$n/_manifest.json"
  cp "$SRC/chapters/$n/chosen.md" "$DST/chapters/ch$n.md"
done
cp "$SRC/audio/_voice_map.json" "$DST/audio/voice_map.json"
cp "$SRC/audio/_manifest.json" "$DST/audio/segments_manifest.json" 2>/dev/null || true

echo "=== asset sizes ==="
du -sh "$DST/audio" "$DST/illustrations" "$DST/storyboard" "$DST/characters" "$DST/chapters"
echo "=== total ==="
du -sh "$DST"
