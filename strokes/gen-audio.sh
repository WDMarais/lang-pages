#!/usr/bin/env bash
# Generate TTS clips for the strokes/radicals module.
# CN voice: zh-CN-Xiaoxiao · JP voice: ja-JP-Nanami
# Run: bash strokes/gen-audio.sh   (requires: uv tool install edge-tts)
set -e
OUT="$(dirname "$0")/audio"
mkdir -p "$OUT"

CN_VOICE="zh-CN-XiaoxiaoNeural"
JP_VOICE="ja-JP-NanamiNeural"

# slug : CN-name : CN-example : JP-name(kana) : JP-example(kana)
ROWS=(
  "heng:横:三:よこかく:ニ"
  "shu:竖:十:たてかく:ジュウ"
  "pie:撇:人:ひだりばらい:ひと"
  "na:捺:八:みぎばらい:ハチ"
  "dian:点:犬:テン:いぬ"
  "ti:提:打:はね:うつ"
  "zhe:折:口:おれ:くち"
  "shugou:竖钩:小:はねぼう:ちいさい"
)

gen() { # voice text outfile
  if [ -f "$3" ]; then echo "skip  $3"; return; fi
  echo "gen   $3"
  edge-tts --voice "$1" --text "$2" --write-media "$3"
}

for row in "${ROWS[@]}"; do
  IFS=':' read -r slug cnName cnEx jpName jpEx <<< "$row"
  gen "$CN_VOICE" "$cnName" "$OUT/cn-${slug}.mp3"
  gen "$CN_VOICE" "$cnEx"   "$OUT/cn-${slug}-ex.mp3"
  gen "$JP_VOICE" "$jpName" "$OUT/jp-${slug}.mp3"
  gen "$JP_VOICE" "$jpEx"   "$OUT/jp-${slug}-ex.mp3"
done
echo "done"
