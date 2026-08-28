#!/usr/bin/env bash
# Compress all PNGs from scriptorium → JPG and copy audio for web delivery.
set -uo pipefail
SRC=/Users/seansp/git/scriptorium/cant-have-nice-things
DST=/Users/seansp/git/sean-makes-stuff/books/cant-have-nice-things

# Cover
sips -s format jpeg -s formatOptions 85 "$SRC/storyboard/chosen/cover.png" --out "$DST/storyboard/cover.jpg" >/dev/null

# Character portraits
for f in "$SRC/characters/"*/portrait.png; do
  name=$(basename "$(dirname "$f")")
  sips -s format jpeg -s formatOptions 85 "$f" --out "$DST/characters/$name.jpg" >/dev/null
done

# Chapter beat illustrations
for n in 01 02 03 04 05 06 07 08 09; do
  mkdir -p "$DST/illustrations/ch$n"
  for f in "$SRC/chapters/$n/images/_candidates/"beat_*.png; do
    base=$(basename "$f" .png)
    sips -s format jpeg -s formatOptions 85 "$f" --out "$DST/illustrations/ch$n/$base.jpg" >/dev/null &
  done
done
wait

# Audio (already mp3, just copy)
cp "$SRC/audiobook.mp3" "$DST/audio/audiobook.mp3"
cp "$SRC/audio/chapters/"chapter_*.mp3 "$DST/audio/"

# Manifests + meta
cp "$SRC/audio/_beats_manifest.json" "$DST/" 2>/dev/null || true
for n in 01 02 03 04 05 06 07 08 09; do
  cp "$SRC/chapters/$n/images/_beats_manifest.json" "$DST/illustrations/ch$n/_manifest.json"
  cp "$SRC/chapters/$n/chosen.md" "$DST/chapters/ch$n.md"
done
cp "$SRC/audio/_voice_map.json" "$DST/audio/voice_map.json"
cp "$SRC/audio/_manifest.json" "$DST/audio/segments_manifest.json"

# Sizes
echo "=== compressed asset sizes ==="
du -sh "$DST/audio" "$DST/illustrations" "$DST/storyboard" "$DST/characters" "$DST/chapters"
echo "=== total ==="
du -sh "$DST"
