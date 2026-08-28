#!/usr/bin/env bash
# Copy maillard-crust-tutorial assets from scriptorium → sean-makes-stuff for web delivery.
# Source assets are already JPEG, so just copy (no PNG→JPG conversion needed).
# Audio re-encoded to 64 kbps mono 22050 Hz for smaller web delivery.

set -uo pipefail
SRC=/Users/seansp/git/scriptorium/maillard-crust-tutorial
DST=/Users/seansp/git/sean-makes-stuff/books/maillard-crust-tutorial

mkdir -p "$DST"/{storyboard,characters,audio,illustrations,chapters}

# Cover — PNG→JPG at q85 via sips (native macOS, cuts ~75%)
sips -s format jpeg -s formatOptions 85 "$SRC/storyboard/chosen/cover.jpeg" --out "$DST/storyboard/cover.jpg" >/dev/null

# Character portraits
for f in "$SRC/characters/"*/portrait.jpeg; do
  name=$(basename "$(dirname "$f")")
  sips -s format jpeg -s formatOptions 85 "$f" --out "$DST/characters/$name.jpg" >/dev/null
done

# Chapter beat illustrations
for n in 01 02 03 04 05 06 07 08; do
  mkdir -p "$DST/illustrations/ch$n"
  for f in "$SRC/chapters/$n/images/_candidates/"beat_*.jpeg; do
    base=$(basename "$f" .jpeg)
    sips -s format jpeg -s formatOptions 85 "$f" --out "$DST/illustrations/ch$n/$base.jpg" >/dev/null
  done
done

# Audio: re-encode to 64 kbps mono 22050 Hz for web. The re-encode drops tags
# (we'll re-apply them via _tag_audio.py).
echo "re-encoding audiobook for web (64 kbps mono 22050 Hz) …"
ffmpeg -y -i "$SRC/audiobook.mp3" -codec:a libmp3lame -b:a 64k -ar 22050 -ac 1 -f mp3 \
  "$DST/audio/audiobook.mp3" 2>&1 | tail -3

for n in 01 02 03 04 05 06 07 08; do
  ffmpeg -y -i "$SRC/audio/chapters/chapter_$n.mp3" -codec:a libmp3lame -b:a 64k -ar 22050 -ac 1 -f mp3 \
    "$DST/audio/chapter_$n.mp3" 2>&1 | tail -1
done

# Manifests + chapter text
for n in 01 02 03 04 05 06 07 08; do
  cp "$SRC/chapters/$n/images/_beats_manifest.json" "$DST/illustrations/ch$n/_manifest.json"
  cp "$SRC/chapters/$n/chosen.md" "$DST/chapters/ch$n.md"
done
cp "$SRC/audio/_voice_map.json" "$DST/audio/voice_map.json"
cp "$SRC/audio/_manifest.json" "$DST/audio/segments_manifest.json" 2>/dev/null || true

echo ""
echo "=== asset sizes ==="
du -sh "$DST/audio" "$DST/illustrations" "$DST/storyboard" "$DST/characters" "$DST/chapters"
echo "=== total ==="
du -sh "$DST"
