# Maps Module — Behavioral Spec

## Context

Interactive SVG map where clicking a region surfaces vocabulary anchored to
geographic referents. Pedagogical goal: provide a dignified adult frame for
N=1 vocabulary (directions, geographic terms, region names, cultural items)
that teaches through direct referents rather than L1→L2 translation. Follows
the xi-zhuang pattern: static HTML/CSS/JS + JSON cards + base.css renderer.
No backend; SRS state in localStorage.

---

## Subsystems

1. **Map interaction** — click/tap region, zoom, highlight
2. **Card pane** — factbox + cultural cards, CN-first, toggles
3. **Card schema** — enriched superset of xi-zhuang schema
4. **Discovery queue** — weighted random surfacing of lower cards
5. **Mobile layout** — single-column toggled view

---

## 1. Map Interaction

```
User opens maps page
  → Full SVG map of China rendered, all regions neutral colour
  → No card pane visible yet (or default/empty state on desktop)

User clicks/taps a region (e.g. 四川)
  → Region highlights (distinct fill/border)
  → Map zooms to bring clicked region to prominence
  → Card pane opens/populates for that region
  → Previously highlighted region returns to neutral

User clicks the currently-highlighted region again
  → No change (already selected) — not a toggle-off

User clicks empty map space (non-region)
  → Selection clears, map returns to default zoom
  → Card pane returns to empty/default state

User clicks a different region while one is already selected
  → Previous region deselects, new region highlights
  → Card pane replaces content with new region's cards

Map renders with all 34 administrative divisions clickable:
  23 provinces, 5 autonomous regions, 4 municipalities, 2 SARs
  → Each is a distinct SVG path with a slug identifier
```

---

## 2. Card Pane

### Factbox (always first, always visible for selected region)

```
User selects 四川
  → Factbox shows:
      四川省          ← hanzi, large
      Sìchuān Shěng  ← pinyin (hidden until 显示拼音 toggled)
      [definition sentence in Chinese]
      省 | 西南 | 面积 486,000 平方公里 | 人口 8,300万
      [English hidden by default, toggleable]

Factbox fields (typed, always present):
  admin_level: 省 / 自治区 / 直辖市 / 特别行政区
  location: cardinal direction in Chinese (西南 / 华北 / etc.)
  area: number + 平方公里
  population: number + 万/亿

Each factbox field is itself a vocabulary anchor:
  省, 自治区, 西南, 面积, 平方公里, 人口 encountered in
  real context on every region — not as isolated cards
```

### Cultural cards (below factbox)

```
User selects 四川
  → 5-10 cultural cards appear below factbox
  → First 3-5 ordered by salience (hardcoded per region)
  → Remaining cards randomised by discovery weight (see §4)
  → Cards follow enriched schema (see §3)

Example cards for 四川:
  熊猫  — image(s) of panda, panda sense audio, example sentences + TTS
  麻辣  — image of 火锅, example sentences
  成都  — image of city, example sentences
  峨眉山 — image, example sentences

Card is CN-first:
  Hanzi prominent, pinyin hidden (toggle), English hidden (toggle)
  Same 显示拼音 / 显示英文 controls as xi-zhuang

Card has spoken audio per example sentence (TTS or recorded)
Card may have sense audio at card level (non-speech: panda call,
  market noise, river sound)
Card may have multiple images at card level
```

### Controls

```
显示拼音 toggle → shows/hides pinyin on factbox + all cards
显示英文 toggle → shows/hides English on factbox + all cards
Both behave identically to xi-zhuang controls
```

---

## 3. Card Schema

Enriched superset of xi-zhuang. All xi-zhuang fields carry over unchanged.
New fields: `images`, `sense`, `links`.

```json
{
  "slug": "xiong-mao",
  "hanzi": "熊猫",
  "pinyin": "xióng māo",
  "meaning": "giant panda",
  "meaning_zh": "中国特有的黑白熊类动物",
  "theme": "t-red",
  "images": ["images/panda-eating.jpg", "images/panda-cub.jpg"],
  "sense": ["audio/panda-call.mp3"],
  "links": ["si-chuan", "zhu-zi", "hei-bai"],
  "examples": [
    {
      "zh": "四川的熊猫很有名。",
      "en": "Sichuan's pandas are famous.",
      "audio": { "TTS": "audio/xiong-mao-ex1.mp3" }
    }
  ],
  "note": "optional cultural note"
}
```

### Schema cases

```
Card with no images
  → image slot absent from rendered card — no broken img tag

Card with no sense audio
  → no sense audio player rendered

Card with no links
  → links field absent or empty array — no adjacency section rendered

Card with multiple images
  → rendered as a small gallery or horizontally scrollable strip

Card with multiple examples
  → each example has its own TTS audio button, same as xi-zhuang

links field contains slugs of adjacent cards
  → each slug is a directed association traversable in either direction
  → each link is a potential SRS card edge (given one end, produce other)
  → cross-card: 熊猫 → 四川 means 熊猫 card links to 四川 region card

SRS card derived from rich card:
  [image of panda] → hanzi         (image → term)
  [hanzi 熊猫]     → pinyin        (term → pronunciation)
  [sense audio]    → hanzi         (sound → term)
  [example + gap]  → fill 熊猫     (context → term)
  [熊猫]           → 四川 (link)   (term → association)
  Each is a single directed edge; rich card is the source of truth
```

### Factbox schema (region-level, separate from vocab cards)

```json
{
  "slug": "si-chuan",
  "hanzi": "四川",
  "hanzi_full": "四川省",
  "pinyin": "Sìchuān",
  "pinyin_full": "Sìchuān Shěng",
  "admin_level": "省",
  "location": "西南",
  "area_km2": 486000,
  "population_wan": 8300,
  "definition_zh": "四川是中国西南部的一个省，以熊猫和麻辣著名。",
  "definition_en": "Sichuan is a province in southwest China, known for pandas and spicy food.",
  "cards": ["xiong-mao", "ma-la", "cheng-du", "e-mei-shan"]
}
```

---

## 4. Discovery Queue

```
Lower cultural cards (below top 3-5 hardcoded) surface in weighted random order.

Weight is inversely proportional to interaction count per card slug:
  never seen      → highest weight (surfaces most often)
  seen (scrolled past, rendered) → medium weight
  interacted with (clicked, expanded, audio played) → lower weight
  explicitly dismissed → lowest weight

Interaction counts stored in localStorage keyed by slug.

User opens 四川 card pane, scrolls past 5th card
  → cards 6-10 rendered in weighted-random order
  → slugs for rendered cards have their seen-count incremented

User plays audio on 熊猫 card
  → 熊猫's interaction count incremented
  → next time 四川 pane opens, 熊猫 appears slightly lower in random order

User closes and reopens the page
  → localStorage counts persist, ordering remains weighted

User has seen all cards for a region many times
  → weights converge toward uniform — all cards roughly equally likely
  → no card is permanently suppressed

Discovery queue is per-card-slug, not per-region:
  熊猫 seen in 四川 pane counts toward its weight everywhere
```

---

## 5. Mobile Layout

```
Mobile (≤ 620px): single-column toggled view — map mode OR card mode

Default state on mobile
  → Map mode: full-width SVG map, no card pane

User taps a region on mobile
  → Switches to card mode: map hidden, card pane fills screen
  → Back button / header returns to map mode
  → Selected region remains highlighted (visible when returning to map)

User taps back from card mode
  → Returns to map mode, selected region still highlighted
  → Tapping a different region switches card mode to that region

Desktop (> 620px): split view
  → Map left, card pane right, both visible simultaneously
  → No toggle needed
```

---

## Known deferred / out of scope

- Sub-region zoom (clicking into a province to see cities) — deferred
- SRS scheduling (SM-2 intervals, due dates) — deferred; discovery queue
  is the precursor
- Cross-device sync — deferred; localStorage only for now
- Import/export of card data or SRS state — deferred
- Radicals module — separate, not grafted onto map
- Non-China maps — out of scope for this module

---

## Technology Recommendation

**No new technology needed.** The maps module is a strict extension of the
xi-zhuang pattern: static HTML + CSS + vanilla JS + JSON data files.

Specific constraints that drove this:

- **Card schema is a superset of xi-zhuang** — the existing renderer
  (`renderCard`) needs minor extension (images array, sense audio, links),
  not a rewrite. New fields degrade gracefully if absent.
- **Discovery queue is localStorage** — interaction counts keyed by slug,
  read on pane open, written on scroll/interaction events. No library needed.
- **Map SVG** — source a CC-licensed China provinces SVG (Wikimedia Commons),
  add `onclick="selectRegion(slug)"` per path. No mapping library (Leaflet,
  D3) required at this complexity level; vanilla SVG manipulation suffices.
- **Mobile toggle** — CSS class swap (`body.map-mode` / `body.card-mode`) +
  one JS toggle function. Same pattern as xi-zhuang's pinyin/English toggles.
- **TTS audio** — use Web Speech API (`speechSynthesis`) for example sentences
  where recorded audio is absent; falls back gracefully to no audio button.

The only decision worth revisiting if scope grows: if sub-region zoom arrives,
D3's zoom behaviour on SVGs is significantly easier than rolling it manually.
Hold that decision until sub-regions are actually in scope.
