# Deck design & scheduling

Why the content graph exists on the *consumer* side: how a typed graph drives
**deck composition and ordering**, not just per-card timing. Companion to
[content-graph-schema.md](content-graph-schema.md) (the fact model) — this doc is
the *scheduling policy* that reads it. Vocabulary: [glossary.md](glossary.md).

> Status: **design rationale — partly latent.** The *representation* (composes
> gates, association edges, denotes→referent) supports everything here; the
> graph→scheduler *wiring* is "deferred with cadence" (see the schema's open
> mapping question). This doc records the target so the wiring gets built toward
> it, and so effort lands on the coupling rather than commodity timing.
>
> Design stance (unchanged): **bootstrap, don't boil the ocean.** Ship the
> cheapest version, measure whether it bites, mechanize only what does. See memory
> `feedback-bootstrap-over-monolith`.

## The lever: deck composition, not per-card timing

There are two axes you can optimize a spaced-repetition system on:

| axis | what it tunes | who does it | ceiling |
|------|---------------|-------------|---------|
| **per-card timing** | *when* to show one fact next | FSRS / SM-2 — a solved commodity | pushing ~80% → ~85% of theoretical peak |
| **deck composition** | *which* facts sit near each other, and in what order | almost nobody — needs a graph | largely unclaimed |

The bet (memory `graph-schedules-you`): the unclaimed efficiency is in the second
axis. FSRS treats every fact as **independent** and optimizes each in isolation.
But cards are *not* independent — one card can **support** another (teach `red`,
then `red→rose` lands cheaper) or **sabotage** another (see *interference* below).
That structure *between* facts is exactly what a typed graph models and a linear
deck cannot. So: don't chase the last 5% of per-card timing; invest in
**fire-together / wire-together at the deck level**.

### Graph ordering is optional enrichment over a naive floor

This is additive, never a rewrite of FSRS:

- **Floor (always available):** once a card is *seen*, timing is naive/identical
  FSRS. A deck emits to Anki in naive order and works. No graph required to run.
- **Enrichment (opt-in per chain):** the graph re-orders and gates *around* that
  floor — hard `composes` prerequisites (you can't learn 好 before 女 and 子), soft
  `association` sequencing (co-teach a confusable set), and the interference
  spacing below. A learner (or a future consumer) opts a particular chain in.

So the graph layer sits *above* a working commodity engine. The novelty is that
**the graph schedules you** — ordering and unlock fall out of the prerequisite
structure, and the structure is *derived, not hand-drawn* — while the floor keeps
the system useful (and Anki-exportable) before any of that is wired.

## Two kinds of "interference" — opposite treatments

The word "interference" hides two phenomena that want **opposite** handling.
Conflating them is the trap.

| | **A — leakage / priming** | **B — confusable competition** |
|---|---|---|
| what | one card's answer is fresh in working memory when another tests it | two distinct items genuinely compete in durable memory |
| example | "this is a red rose" → "what colour is the rose?" | fire / ember · 己 / 已 / 巳 |
| timescale | seconds → hours (a session) | long-term |
| harms | the **measurement** — a fake success | the **learning** — real confusion |
| treatment | **separate / wash out** — don't test while the answer is primed | **juxtapose + contrast** — teach together against disambiguating cues |
| who owns it | this doc (spacing + the exposure stream) | already shipped: `association`/`confusable` co-teach, memory `confusable-pair-anchoring` |

The consequence that matters: a naive **"same keyword → spread apart"** rule is
correct for A and *actively wrong* for B — it would pull apart exactly the
confusable pairs the authored layer spent effort putting together. Any interference
mechanism must be **sign-aware**, and the graph already carries the sign:

- shared referent **on an `association` edge** (confusable/cognate) → *intentional*
  juxtaposition — keep together / co-schedule, never skip.
- shared referent with **no edge** (incidental collision) → *leakage* candidate —
  soft-spread within the near-term window.

### The cheap mechanism (build this first)

The mandate for A is **signal integrity, not pedagogy**: a primed recall feeds
FSRS a success the learner didn't earn, FSRS schedules the card too far out, and a
gap surfaces later. That is a much smaller job than "avoid all interference."

1. Take the near-term window (~200 cards from the today/tomorrow/day-after
   frontier).
2. Detect overlap by **referent**, not keyword — cards already resolve to referents
   via `denotes`; referent-overlap avoids the false positives ("red rose" vs "red
   herring") and false negatives (synonyms) of lexical matching.
3. For an incidental (no-edge) overlap, mark **"skip if possible"** — a *soft*
   spacing constraint, not a hard optimizer. Spread the pair apart in the queue.

Deliberately **not** built until observed to bite:

- **Directionality.** True leakage is specifically B's *answer* referent appearing
  in A's *prompt* — which needs per-card front/back "reveals vs. prompts" referent
  sets. Start undirected; add this only if fake successes are seen mis-scheduling
  something real.

## The exposure stream — the real fix, and a bridge

Beyond interference, this is the larger idea. Split study into two registers,
borrowing the reading-pedagogy distinction:

- **Intensive** — 20–60 active-recall cards/day (the deck).
- **Extensive** — ~2000 low-effort **exposures**/day (encounters, not tests).

The exposures do triple duty: they **wash out** priming (A) as intervening varied
material displaces "I saw 火 two cards ago"; they give **varied-context
re-encounters** that actually *help* discrimination (B); and they are the
**bridge from deck into use-at-volume** — the point of the whole system.

**The corpus loop.** The exposure stream *is the corpus* — and it is the same
enumerable corpus that *defined* the deck (memory `enumerable-referent-principle`).
Bible text, Python you read, sentences. The corpus that generates the deck also
services it as volume:

```
corpus ──decompose──▶ deck (intensive, tested)
   ▲                    │
   └──── exposures ◀─────┘   (extensive, washes + consolidates + bridges to use)
```

**Comprehensibility gate (i+1).** Exposures only wash and consolidate if they're
*parseable* — 2000 exposures of unreadable material is noise. So *which* exposures
to serve is gated by what's unlocked: pick exposures whose referents are mostly
taught. This routes back through the graph, but **softly** (a selection bias toward
comprehensible material), not as a hard lock.

## Calibration — when any of this matters

Leakage is worst for the **beginner with a small deck**: few cards, high referent
overlap, *and* no exposure stream yet (they can't read the corpus). It evaporates
for the advanced learner: a large deck interleaves collisions away and a real
exposure stream washes them out. So:

- ship the cheap sign-aware soft-spread for the early-deck case;
- lean on the exposure stream for everything after;
- don't build the directional reveals/prompts machinery until a fake success is
  observed mis-scheduling something real.

Effort here is **inversely proportional to learner level** — which is why "don't
worry about it too much" is right, but not *zero* at the start.

## Status & pointers

- **Built:** the fact model (`composes`/`denotes`/`variant`/`association`) —
  content-graph-schema.md; confusable co-teach (B) — memory
  `confusable-pair-anchoring`.
- **Wiring deferred:** graph→scheduler unlock/ordering — the schema's open mapping
  question; srs-tool consumes concepts by id (memories `srs-tool-data-model`,
  `srs-sequencing-working-model`). Naive in-degree-on-`composes` teach-order is the
  current floor.
- **Not built:** interference soft-spread, the exposure stream, the comprehensibility
  gate. Recorded here; sequence per the calibration above.

Related future-exploration in content-graph-schema.md: spreading-activation-unlock
and weighted `assoc` enrichment edges are the general form of the sign-aware
spacing described here.
