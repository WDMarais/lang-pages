# Gig brief — referent image sourcing & attribution

**What this is:** paid piecework finding clear, free-to-use images for lang-pages.
No programming or maths — the value is careful curation and getting the licensing
right. One "unit" of work = one *referent* (a meaning, e.g. `fire`, `tree`, `water`)
with 1–2 good images picked, verified, and recorded.

**You never touch JSON.** Images the fetch script pulls are recorded for you
automatically; images you find yourself get written as a simple fill-in-the-blanks
text block (details below).

Companion docs: [authoring.md](authoring.md) (the wider ingest process — you don't
need it), [content-graph-schema.md](content-graph-schema.md).

---

## The one rule that matters most: licensing

Only these licenses are acceptable, because we redistribute the image:

- **Public Domain (PD)** / **CC0**
- **CC BY** (attribution required)
- **CC BY-SA** (attribution required)

**Anything else — reject it.** No "all rights reserved", no NC (non-commercial),
no ND, no "free for personal use only", no unknown/blank license. If you can't find
a clear license statement on the source page, treat it as unusable and move on.

Every accepted image **must** have its attribution recorded exactly. A great image
with the wrong or missing credit is a *reject*, not a "fix later".

---

## One-time setup

The fetch script talks to Wikimedia, which asks for a real contact address. Set it
once per terminal session (use whatever email you're comfortable with):

```bash
export WIKIMEDIA_CONTACT="you@example.com"
```

---

## Workflow, per referent

1. **Get candidates from Wikimedia** using the script:

   ```bash
   python3 data/fetch-referent.py <slug> "<search query>" -n 2
   # e.g.
   python3 data/fetch-referent.py tree "tree isolated white background" -n 2
   ```

   This pulls thumbnails into `shared/referents/`, keeps only free-licensed ones,
   and **records them for you** — no typing needed.

2. **Look at what came back.** If one is clearly good — sharp, obvious, well-licensed
   — you're basically done. Just glance at the Wikimedia file page to confirm the
   credit and license look right.

3. **If nothing good came back, search deeper yourself** (this is where the real
   value is). Good CC/PD sources:
   - **Openverse** (openverse.org) — searches CC images across many sites at once; **start here** for a deeper hunt.
   - **Wikimedia Commons** (commons.wikimedia.org) — browse the category, not just search.
   - **Flickr** with the license filter set to Creative Commons.
   - PD collections (e.g. museum open-access, Wikimedia PD categories).

   *(Avoid Unsplash / Pexels / Pixabay for now — their images are "free" but under
   their own non-CC licenses that don't fit our attribution format. Stick to CC/PD.)*

   When you find a keeper: **download it into `shared/referents/`** with a sensible
   filename (`<slug>-NN.jpg`), then **record it as a text block** — see next section.

---

## Recording a hand-found image (the fill-in block)

For images you found yourself, open **`data/referents-inbox.toml`** and add one
block per image. It's just labelled lines — copy the template, fill in the values,
keep the quotes:

```toml
[[image]]
slug    = "tree"          # the meaning, lowercase, one word (fire, water, tree...)
label   = "tree"          # how it reads on the card (usually same as slug)
file    = "tree-03.jpg"   # the filename you saved into shared/referents/
credit  = "Jane Doe"      # author, exactly as the source page states
license = "CC BY-SA 4.0"  # must be PD / CC0 / CC BY / CC BY-SA — nothing else
source  = "https://commons.wikimedia.org/wiki/File:..."   # the file PAGE url
```

- Add as many `[[image]]` blocks as you like — one per image.
- `source` is the **file page URL** (the page that shows the license), not the raw
  image link.
- Type the `credit` and `license` **exactly** as the source states them. Don't
  paraphrase — this is the bit that has to be precise.

That's it. Wynand converts the inbox into the site's data himself; you never edit
the JSON.

---

## What makes a *good* referent image

You're picking the image a learner will glance at to grasp the meaning. Aim for:

- **Unambiguous** — a photo of `fire` should obviously be fire, not "a campsite that
  happens to have a fire". If a stranger couldn't name the meaning from the image
  alone, skip it.
- **Clean / uncluttered** — single clear subject, ideally isolated or on a simple
  background. No text overlays, watermarks, collages, or busy scenes.
- **Neutral & safe** — no gore, nothing offensive, no obvious brand logos or
  identifiable private individuals as the subject.
- **Decent quality** — in focus, not tiny, not heavily compressed.

1 excellent image beats 2 mediocre ones. Only add a 2nd if it genuinely helps —
**except for broad meanings** (next section), where a small varied set is the point.

---

## Broad meanings vs specific meanings

A few referents are **broad** — an umbrella that many different things fit under.
`person` covers men, women, children and the elderly; `animal` covers dogs, birds,
fish; `tree` (trees-in-general) covers oak, pine, palm. Most referents are **specific**
— `woman`, `puppy`, `oak` — one particular kind.

These two want *opposite* sourcing. **When a referent is broad, its line in the task
list will say so (e.g. "broad — variety").** If it isn't marked, treat it as specific.

**Broad meaning → show the variety, not one example.**
- Pick images that read as the *general idea*: a mixed group, a crowd, or a clear
  range — for `person`, a handful of different people (mixed ages and sexes), not one
  portrait.
- This is the one case where **3–5 images that differ from each other** is better than
  one. Make them genuinely varied; five near-identical shots don't help.
- **Avoid a single image that reads as a narrower meaning.** A lone woman photo under
  `person` looks like `woman`, not `person` — and we teach `woman` separately, so it
  sends the wrong signal. If you only have one slot, choose the most general-looking
  image (a mixed group beats any single individual).

**Specific meaning → one clear, typical, central example.**
- `woman` = plainly an **adult woman** — not a girl (that's `child`), not one that reads
  mainly as elderly (that's `old`). `puppy` = obviously a *young* dog.
- Skip edge cases and unusual examples. Pick the one a stranger would name instantly.
- It's completely fine if your specific image also happens to fit a broader meaning — a
  photo of a woman is of course also a person. You don't need to avoid that; just make
  sure it's a *clear* woman.

Why it matters: a learner has to tell these meanings apart. A broad meaning shown as one
narrow example, or a specific meaning shown with an off-centre example, quietly teaches
the wrong word.

---

## Definition of done (per referent)

- 1–2 images saved in `shared/referents/`.
- Script-fetched images: confirmed the auto-recorded credit/license looks right.
- Hand-found images: a complete `[[image]]` block in `data/referents-inbox.toml`
  (all six lines filled).
- Every license is one of PD / CC0 / CC BY / CC BY-SA.
- The image clearly and unambiguously depicts the meaning.
- **Broad meaning** (marked in the list): a *varied set* showing the general idea, no
  single image that reads as a narrower meaning. **Specific meaning:** one clear,
  central, typical example.

**Don't:** invent or guess a credit; use a non-free image "just this once"; add text
overlays or edit images; paraphrase a license string.

---

## How the work is checked

Wynand runs two things — you don't need to:

1. `python3 data/referents-from-toml.py` — folds your inbox blocks into the site data
   **exactly as you typed them** (no LLM, no rewording), and rejects any non-free
   license or incomplete block on the spot.
2. `python3 data/check-source.py` — confirms every referent resolves and is sound.

If something's off you'll get it back with a note — no problem, it's expected on the
first batch while we calibrate.

---

## Pay

- **Rate:** R20 per referent completed (1–2 verified images + accurate recording).
- **Trial:** first small batch (≈5 referents) at full rate, so we can check the
  workflow fits and adjust anything before you do volume.
- Work at your own pace — there's no clock, just completed referents.
