# Sensory Axes & 3D — Design Notes

## What we have

The scene component decomposes a vocabulary item into three orthogonal attributes:
**color × size × shape** — rendered as SVG, selectable via pickers, displayed as a compound phrase with pinyin.

The equation row (`[color pane] + [size pane] + [shape pane] = compound pane`) makes the decomposition explicit. The 找一找 recognition grid adds a retrieval task: 12 shapes, one highlighted, 11 greyed out.

---

## Sensory axes on the roadmap

| Axis | Status | Notes |
|---|---|---|
| Color | Done | 10 values, full hex palette |
| Size | Done | sm / md / lg |
| Shape | Done | 6 polygons |
| Opacity / transparency | Easy | CSS `opacity` or SVG `fill-opacity`; teaches 透明/半透明 |
| Material / surface | Medium | Three.js canvas-nested; glass, matte, gloss, dull |
| Sound | Medium | Web Audio API; discrete pitch/volume levels, harmonic vs dissonant |
| Texture / pattern | Harder | SVG `<pattern>` fill or Three.js texture maps |

Opacity is the cheapest win — one CSS property, new vocabulary axis, slots directly into the existing equation row.

Sound has no visual presence, so it attaches to the `pick()` config logic rather than the layout — play a tone when the selection changes, vary pitch by attribute value.

---

## 3D: when it earns its keep

The rule: **3D UI layout is only worth the cost when the spatial geometry is itself semantically meaningful** — i.e., when position encodes information that a flat layout cannot.

**Cases where 3D genuinely adds something:**

- **Geographic/spatial data** — a globe for map views is the canonical example. 2D projections distort; the sphere is the right shape for the data.
- **Orthogonal combinatorial space** — color × size × shape are genuinely three independent axes, so the 180 combinations form a real 3D grid. A navigable cube where movement along X/Y/Z changes color/size/shape would be semantically grounded: the spatial gesture *is* the attribute change, not a metaphor for it. The current selection is a point in that space.
- **Semantic proximity / embedding space** — if word-embedding distances drove layout, nearby shapes would cluster by meaning (菱形 near 正方形, 红 near 橙). Navigating the space would surface structural relationships. This requires an LLM or embedding backend and is a bigger project.
- **Memory palace navigation** — if spatial position is itself the mnemonic (you always go "left" for sound, "up" for character decomposition), the navigation path becomes part of the schema.

**Cases where 3D doesn't add anything:**

- **Cube-per-card** — a 6-sided cube with one fact per face is just a 6-node graph. The 3D geometry adds no information over a labeled adjacency list or a tabbed card. It looks interesting but spatializes data that isn't spatial.
- **3D for visual interest** — the browser page itself being a 3D scene adds rendering cost and navigation complexity without semantic payoff.

**Conclusion for this project:**

- Page layout stays flat. The equation row already makes attribute orthogonality legible without requiring 3D navigation.
- When materials/gloss arrive, Three.js renders into a `<canvas>` nested inside the existing `.scene-pane` — the layout frame (labels, pickers, equation row) stays as-is.
- Revisit 3D if: (a) we build the embedding-space navigation feature, or (b) we do a map/geographic vocabulary set where a globe is the natural container.

---

## The broader vocabulary-anchoring picture

The shape/color/size system is deliberately abstract — it works as a scaffold for the decomposition habit ("what are the attributes? what is the compound form?") but doesn't anchor to culturally specific referents. Two directions from here:

1. **Abstract → cultural**: use the attribute system as a feeder for real-world instantiation. "Ask your LLM for circles in a Chinese context" — drag in images of jade bi discs, the Temple of Heaven, coins. The shape becomes a retrieval cue for culturally grounded instances.

2. **Spatial relations page** (high-ROI next feature): two shapes positioned relative to each other, teaching 上面/下面/左边/右边/里面/外面. Same SVG rendering infrastructure, new vocabulary domain, interaction model already designed.

The system is most useful as a scaffold for *new cognitive equipment* — vocabulary domains that give the learner a new category, not more instances of a known one. Spatial prepositions, kinship terms, cooking verbs, hierarchical titles are all higher-ROI than more color/shape synonyms.
