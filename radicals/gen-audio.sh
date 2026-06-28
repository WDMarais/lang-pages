#!/usr/bin/env bash
# Generate TTS clips for the radicals (components & characters) module.
# CN voice: zh-CN-Xiaoxiao · JP voice: ja-JP-Nanami
# Run: bash radicals/gen-audio.sh   (requires: uv tool install edge-tts)
set -e
OUT="$(dirname "$0")/audio"
mkdir -p "$OUT"

CN_VOICE="zh-CN-XiaoxiaoNeural"
JP_VOICE="ja-JP-NanamiNeural"

# slug : CN-name : CN-example : JP-name(kana) : JP-example(kana)
ROWS=(
  "ba:八:分:ハチ:わける"
  "er:二:元:ニ:ゲン"
  "lid:亠:六:なべぶた:ロク"
  "da:大:天:ダイ:テン"
  "ren:人:今:ひと:いま"
  "ru:入:全:はいる:ゼン"
  "li:力:男:ちから:おとこ"
  "bao:勹:包:つつみがまえ:つつむ"
  "kou:口:名:くち:メイ"
  "nv:女:好:おんな:すき"
  "qi:七:切:なな:きる"
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
