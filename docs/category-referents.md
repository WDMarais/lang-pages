# Category referents & directional grading — design memo

**Status: design only, not implemented.** Captures how *superordinate* referents
(a meaning that subsumes more specific ones — `person` over `woman`/`child`) should
be represented, graded, and sourced, so their instance images don't collide with the
subordinate glyphs that also depict them. Motivated by the 人 referent-image batch
(man / two children / a senior / a woman): every candidate image for 人 is *also* a
valid instance of 女, 子, or 老 — a **class** of problem, not five bad picks.

Companion docs: [content-graph-schema.md](content-graph-schema.md) (`referent` node,
`denotes` edge), [deck-design.md](deck-design.md) (interference A/B), the
referent-sourcing [image-sourcing-brief.md](image-sourcing-brief.md).

## The problem: there is no photo of "a generic human"

人 means *person / human being*. Every real human is some age and some sex, so any
single photograph of a person is unavoidably also an instance of a **subordinate**
glyph that we teach in its own right (女 woman, 子 child, 老 old). Show one such photo
alone as "the referent of 人" and it actively teaches the wrong binding — a lone woman
portrait reads as 女, not 人.

This is not fixed by finding a "better, more neutral" image. It is fixed by changing
what the referent **is** (§Representation) and how its cards are **graded** (§Grading).

## A third kind of interference — C: hierarchy / hyponymy

`deck-design.md` splits interference into **A — leakage** (treat by spreading apart)
and **B — confusable competition** (treat by juxtaposing). The 人/女 collision is
neither: the referents genuinely *overlap by subsumption* (woman ⊑ person), by design,
permanently. Add:

| | **A — leakage** | **B — confusable** | **C — hierarchy / hyponymy** |
|---|---|---|---|
| what | answer primed in working memory | two items compete in durable memory | one referent **subsumes** another (is-a) |
| example | "red rose" → "what colour?" | 己 / 已 / 巳 | person ⊃ woman ⊃ … ; animal ⊃ dog |
| harms | the measurement (fake success) | the learning (real confusion) | miscredits a *wrong* answer, or over-narrows a category |
| treatment | separate / wash out | juxtapose + contrast | **directional grading + category montage** (this doc) |

C is not a scheduling problem (A) or a co-teach problem (B). It is a **grading +
representation** problem, owned here.

## The is-a lattice

Referents form a taxonomy: a directed **`isa`** edge from a referent to the referent
that subsumes it (hyponym → hypernym).

```
r:woman ──isa──▶ r:person ◀──isa── r:child
r:man   ──isa──▶ r:person
r:puppy ──isa──▶ r:dog ──isa──▶ r:animal
```

- `isa` is a *taxonomic* referent↔referent edge — the parked WordNet-style backbone in
  content-graph-schema.md, narrowed to the hyponymy subset (it carries grading
  semantics, so it is its own kind, not generic `assoc`).
- **Not** the property/graded axis. `red`, `big`, `hot` are *properties things have*,
  not categories they *are* — a separate parked axis. `isa` is strictly "X **is a**
  kind of Y."
- A referent with ≥1 incoming `isa` edge is a **category referent** (derive the flag;
  don't hand-author it). Category-ness drives representation and grading below.

## Grading is directional (the core rule)

The is-a relation runs one way — *"a woman is a person"* is true; *"a person is a
woman"* is not — so the two card directions grade differently. This is exactly the
per-card front/back referent-set mechanism `deck-design.md` parks under
"Directionality"; here it has a concrete motivation.

### Forward — image → glyph — **subsumption-lenient**

Prompt is sense-data (an image). Accept the glyph that denotes the image's referent
**and any glyph that denotes an ancestor** up the `isa` chain. Reject siblings and
descendants.

> Woman photo (referent `r:woman`): accept **女** (own) and **人** (walk `isa` up to
> `r:person`). Reject **子** (sibling), reject **老**.

Rationale: naming something by a truthful supercategory is not an error. A learner who
sees a woman and answers "person" has understood, not failed.

### Backward — glyph → referent — **prototype-strict**

Prompt is a glyph. Expected answer is **that glyph's own canonical referent only** — no
walking the lattice, up or down.

> **女** → a *prototypical adult woman*. Reject a generic-person image, a child, a
> senior. **人** → its general representation (see §Representation), never a lone woman.

Rationale: the glyph *means* its own referent. 女 means woman, not "some human"; letting
it resolve to a person image would hollow out the very distinction 女 exists to carry.

**Why the asymmetry is safe (and not a discrimination leak):** the discrimination that
matters — keeping 人 from collapsing into 女 — is enforced entirely on the backward side
plus the category montage. Forward leniency only ever credits *truthful* over-general
answers, which is why it can be generous without eroding anything.

## Why leniency, not markedness — and the bias trap

A real objection to forward-leniency: by **Gricean Quantity**, choosing a *marked*
exemplar (a **puppy**, not a generic dog) implicates that the specificity is relevant,
so crediting "dog" under-reads it. Two reasons this does **not** loosen the rule — and
one reason it actively *confirms* it:

1. **The card is labeling, not message-reading.** Forward is a recognition task — *"here
   is an exemplar of a referent; name it."* That is truth-conditional: "dog" is *true*
   of a puppy, so it is correct, merely less specific. The implicature only arises under
   a different frame — reading a *deliberately chosen message* for intent ("why this
   image?") — which a referent exemplar is not. The phenomenon is real; it is not the
   one this card models.
2. **Leniency already credits the specific.** If `puppy` is itself a taught referent,
   its forward set is `{幼犬, 犬, 動物}` — the specific *and* every hypernym, all true.
   The rule never *requires* the general answer and never *penalizes* the specific; it
   only refuses to mark a true answer wrong.
3. **The bias trap makes leniency the safe choice.** The only way to honour the
   implicature is to *penalize the hypernym* when a specific was shown — which forces a
   **markedness ranking** (which subtype is "the marked one"). For *developmental*
   subtypes (puppy⊑dog) that ranking is benign. For **social** subtypes it is a bias
   vector: "woman = marked human" is precisely the androcentric default (man = person)
   — taxonomically woman and man are *both equally* subtypes of person, neither the
   default. Pure subsumption-leniency is **symmetric across siblings**, so the deck
   never has to declare a default human. That symmetry is free, and it is the reason not
   to build a markedness rule at all — which also spares us the fraught job of sorting
   "social" referents from "taxonomic" ones.

**The one legitimate strict-specific case, scoped out:** a lesson that genuinely drills
puppy-vs-adult-dog. Handle it as an explicit **contrast card** ("which is the puppy?",
both shown), *not* by penalizing "dog" on a bare recognition card. Discrimination opts
into specificity by testing a contrast, keeping the markedness judgment local to a
lesson that wants it — never in the base grader.

## Representation

- **Category referent → montage, never a single instance.** Render 人's anchor and its
  backward-direction target as a *diverse set* (man + woman + child + senior together)
  or a deliberately general form (mixed group, crowd, schematic silhouette). Across the
  set the only surviving invariant is human-ness; the age/sex specifics cancel. A
  montage's forward accepted-glyph set is just `{人}` — no single subordinate applies —
  so the montage also sidesteps the collision for the category's *own* card.
- **Subordinate referent → prototypical, central instance.** 女's image must read
  unambiguously as an *adult woman* — not a girl (→子), not strongly elderly (→老), not
  androgynous. Centrality is an acceptance criterion, not a nicety.
- An instance image that *also* fits a parent is **fine and expected** — the `isa`
  lattice handles acceptance. Don't avoid sourcing a woman photo for 女 just because a
  woman is also a person.

## Worked example — the 人 batch

| glyph | referent | role | sourcing verdict |
|---|---|---|---|
| 人 | person | **category** | 5 single portraits are all weak *sole* faces. Use as a **montage**, or reshoot the primary toward mixed-group / crowd / silhouette. The woman & child tiles double as instances of 女/子 — fine. |
| 女 | woman | subordinate | Needs its **own** prototypical-adult-woman image. The pack's *elderly woman* is a weak 女 prototype (reads 老); the Karen Padaung portrait is adult but culturally specific enough to distract. QC picks the most central. |
| 子 | child | subordinate | The two child photos serve; keep the most unambiguous. |

## Generalises past 人

Any taxonomic hierarchy: `animal ⊃ dog ⊃ puppy`, `tree ⊃ oak`, `vehicle ⊃ car`,
`bird ⊃ sparrow`. Whenever a language teaches both a category glyph/word and its
members, the category takes a montage and forward-lenient grading; the members take
prototypes and stay backward-strict. Language- and method-neutral — it lives at the
referent layer, not in CN.

## What's decided vs parked

**Decided (this memo):**
- Directional grading: forward = subsumption-lenient (accept self + hypernyms),
  backward = prototype-strict (own referent only).
- Category referents render as montage / general; subordinates as prototypical
  instances.
- Hierarchy is interference **type C**, owned here — a grading+representation problem,
  distinct from A (spacing) and B (co-teach).

**Parked (build when it bites, per bootstrap-over-monolith):**
- The `isa` referent→referent edge in the schema + derived `category` flag.
- The montage renderer.
- Per-card directional referent-sets in the grader (this unifies with the
  `deck-design.md` "Directionality" parked item — implement once, serves both).

**Feeds:** a category-vs-subordinate sourcing rule belongs in
`image-sourcing-brief.md`; the referent-QC viewer should surface a referent's `isa`
parents/children so a reviewer can judge montage-vs-prototype at review time.
