#!/usr/bin/env bash
# Generate TTS audio clips for xi-zhuang vocab cards.
# Run from anywhere: bash xi-zhuang/gen-audio.sh
# Requires: uv tool install edge-tts

set -e
OUT="$(dirname "$0")/audio"

declare -A TEXT=(
  ["lao-ban-niang"]="老板娘，我的西装你们做好了吗？"
  ["cai-feng"]="他找裁缝照着照片做了一件旗袍。"
  ["xi-zhuang"]="这套西装挺合身的，颜色也很适合你。"
  ["ming-pai"]="这件西装是名牌的，当然贵。"
  ["jian-bang"]="可是我觉得肩膀这里有点紧，袖子也有点长。"
  ["xiu-zi"]="袖子我可以改短，肩膀这里放大的话，我担心没有现在合身。"
  ["yao"]="裤子长短正好，可是腰这里有点肥。"
  ["ku-zi"]="裤子长短正好，可是腰这里有点肥。"
  ["sou-suo"]="我上网搜索了一下儿，发现了一个很大的布料市场。"
  ["fa-xian"]="我还是发现了一点儿小问题：肩膀那里有点儿紧。"
  ["liang-chi-cun"]="来，我给你量量尺寸。"
  ["gai"]="没问题，这个也可以改小。"
  ["yao-qiu"]="都可以照我的要求改小或者放大。"
  ["man-yi"]="我对那个料子也很满意。"
  ["yang-zi"]="你看，照这个样子做，可以吗？"
  ["kuan-shi"]="这件裙子的款式很显身材。"
)

VOICES=(
  "xiaoxiao:zh-CN-XiaoxiaoNeural"
  "xiaoyi:zh-CN-XiaoyiNeural"
  "yunyang:zh-CN-YunyangNeural"
  "yunxi:zh-CN-YunxiNeural"
)

total=0; skipped=0; generated=0
for slug in "${!TEXT[@]}"; do
  for entry in "${VOICES[@]}"; do
    vslug="${entry%%:*}"
    vname="${entry##*:}"
    out="$OUT/${slug}-${vslug}.mp3"
    total=$((total+1))
    if [ -f "$out" ]; then
      echo "skip  $out"
      skipped=$((skipped+1))
      continue
    fi
    echo "gen   $out"
    edge-tts --voice "$vname" --text "${TEXT[$slug]}" --write-media "$out"
    generated=$((generated+1))
  done
done

echo "done  ($generated generated, $skipped skipped, $total total)"
