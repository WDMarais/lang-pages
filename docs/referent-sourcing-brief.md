# Gig brief — referent image sourcing & attribution (core process)

**What this is:** paid piecework finding clear, free-to-use images for lang-pages.
No programming or maths — the value is careful curation and getting the licensing
right. One "unit" of work = one *referent* (a meaning or a thing, e.g. `fire`,
`tree`, `Mount Fuji`, `to eat`) with **about 5** good images picked, verified, and
recorded — a small set the editor then picks the best from.

**This file is the process — it never changes.** *What* you source (the list of
referents) and *what a good image means for that subject* live in a separate
**subject sheet** you'll be given alongside this one (e.g.
[`subjects/kangxi-radicals.md`](subjects/kangxi-radicals.md)). The ask is always the
same shape: *"do this process, for the referents on that sheet."* Everything below
is subject-agnostic; wherever a judgement depends on the subject, this brief points
you at the sheet.

**You never touch code or data files.** You work entirely on one web page — the
*imagery linker*: search or paste in images, and it records the licence details for
you. Nothing to install, no terminal.

Companion docs: [authoring.md](authoring.md) (the wider ingest process — you don't
need it), [content-graph-schema.md](content-graph-schema.md).

---

## The one rule that matters most: licensing

The licence must let us **reuse the image freely — including commercially, and
modified** (we resize it and redistribute it). The familiar licences that qualify:

- **Public Domain (PD)** / **CC0**
- **CC BY** (attribution required)
- **CC BY-SA** (attribution required)

Those four cover almost everything you'll want; if you hit another licence, the test
is the same — *does it allow commercial use and modification?* If it doesn't say so
clearly, treat it as unusable.

**Reject anything that fails that test:** "all rights reserved", **NC** (non-commercial),
**ND** (no derivatives — blocks the resize we do), "free for personal use only", or an
unknown / blank licence. If you can't find a clear licence statement on the source page,
move on.

Every accepted image **must** have its attribution recorded exactly. A great image
with the wrong or missing credit is a *reject*, not a "fix later".

---

## Opening the tool

Everything happens on one web page — the **imagery linker** — that the editor will
send you a link to. No install, no terminal, nothing to set up: open the link in a
normal browser. First thing, type your name/handle in the **contributor** box; it rides
along so the editor knows whose work is whose. The page remembers it next time.

Your work saves automatically **in that browser** as you go, so you can close the tab
and come back. When you're done — or want to hand in progress — one **export** button
gives you a single file to send back. To hand in just part of it (say, today's
referents), open **export a selection**, hit *edited today* (or tick them by hand), and
export those. Each tile shows how many images the collection already holds, plus a
**+N** for the ones you've saved; it turns **green** once you have 5 complete images on
it. Switching browser or computer? Export, then **import a file** on the new one — it
merges into whatever is saved there, skipping images you already have. Import only
*adds* images, though: a card you edit or delete on one computer stays as it was on the
other. So if you work on more than one, **work on different referents on each** and send
an export from each — overlap is harmless, the editor skips images it already has.

---

## Workflow, per referent

1. **Pick the referent.** The page shows the worklist from your subject sheet — click
   the one you're working on (or type its slug). Its meaning seeds the search box.
   **Dim** tiles aren't asking for images right now: either not an image referent at
   all, or the editor has marked them *done* (enough images already) or *later* — skip
   those unless your sheet says otherwise. Tick **hide dim tiles** to see just the open ones.

2. **Get quick candidates from the built-in search.** Hit **search images**: a strip of
   free, safe-for-work candidates appears — via Openverse, which searches Flickr,
   Wikimedia Commons, museums and more. Only commercially-reusable licences are shown and
   mature content is excluded at the source. Click any one to drop it in as a card,
   pre-filled with its credit and licence. Ones already on that referent — or already in
   the collection — are greyed out. Treat these as a **starting point**, not the answer.
   *(If you add the same image twice, even under a different link, a yellow note says so.)*

3. **Do the real sourcing yourself** — this is where the value is; your own searches
   turn up better, more varied images than the default query. Good CC/PD sources:
   - **Wikimedia Commons** (commons.wikimedia.org) — browse the category, not just search; anything here the system can pull automatically.
   - **Openverse** (openverse.org) — searches CC images across many sites at once.
   - **Flickr** with the license filter set to Creative Commons.
   - PD collections (e.g. museum open-access, Wikimedia PD categories).

   *(Avoid Unsplash / Pexels / Pixabay for now — their images are "free" but under
   their own non-CC licenses that don't fit our attribution format. Stick to CC/PD.)*

   When you find a keeper, add it as a card — see the next section.

4. **Aim for about 5** good cards per referent, so the editor has strong ones to choose
   from. The panel on the right turns green when a card's licence details are complete;
   a red note says exactly what's still missing.

---

## Recording an image you found yourself

Click **+ image** to add a blank card, then fill it in:

- **source URL** — the image's **file / description page** (the page that shows the
  licence), *not* the raw image link. For Wikimedia that's the `.../wiki/File:…` page.
- **preview** — paste a direct image link here to see the picture on the spot (this is
  just for your eyes; it isn't saved). A direct-image source fills it in for you.
- **licence** — pick from the dropdown. It only lists the allowed ones (PD / CC0 /
  CC BY / CC BY-SA) and auto-fills the licence URL. If the image isn't under one of
  these, it's unusable — don't record it.
- **credit** — the author / uploader, **exactly** as the source page states it. Don't
  paraphrase; this is the bit that has to be precise. (Search-picked cards fill this in
  for you — still check it against the source page.)
- **title / notes** — optional, but a one-line note on what the image shows helps the
  editor match it.

The file name and today's date fill in automatically. That's it — you never save image
files or edit any data yourself; the editor pulls the actual files from the sources you
recorded.

---

## What makes a *good* referent image

**Always, whatever the subject:**

- **Clean / uncluttered** — single clear subject, ideally isolated or on a simple
  background. No text overlays, watermarks, collages, or busy scenes.
- **Neutral & safe** — no gore, nothing offensive, no obvious brand logos or
  identifiable private individuals as the subject.
- **Decent quality** — in focus, not tiny, not heavily compressed.
- **Correctly licensed and credited** (see the licensing rule above).

**How you judge "does it depict the meaning?" depends on the *type* of referent.**
Your subject sheet marks each referent's type (or says the whole subject is one
type). Here's what each type asks for:

1. **Object / being** — a concrete thing (`knife`, `dog`, `mountain`). *Around 5 clear,
   typical examples* of the same thing, so the editor has good ones to choose from. If a
   stranger couldn't name the meaning from an image alone, drop that one; skip odd or
   edge-case examples and keep the ones they'd name instantly.

2. **Broad / umbrella** — a meaning many different things fit under (`person` covers
   men, women, children; `animal` covers dogs, birds, fish). These want the *opposite*
   of an object: **show the variety, not one example.** Your ~5 images should genuinely
   differ (a mixed group, a range), and **avoid any single image that reads as a
   narrower meaning** — a lone woman photo under `person` looks like `woman`, which we
   teach separately. Lead with the most general-looking image (a mixed group beats any
   individual).

3. **Action (verb)** — `eat`, `run`, `see`. The image must show the **activity
   happening**, not the object involved. `eat` = a person eating, *not* a plate of
   food. Choose a shot where the action is unmistakably mid-motion and the actor is
   clearly doing it.

4. **Quality (colour / property)** — `red`, `big`, `dry`. The **property** has to be
   the obvious point, not the thing carrying it. Show it on a clear, neutral carrier
   (a red swatch or a plainly-red single object for `red`), and where you can, pick a
   carrier that isn't itself an important referent — so the learner reads the *quality*,
   not the object. For comparative qualities (`big`, `long`) a shot that implies the
   contrast reads best.

5. **Identity / named entity** — a specific named thing (`Mount Fuji`, a landmark, a
   named person). It must be **that exact one**. A generic lookalike is a **hard
   reject** — the opposite of the broad rule: here a "typical mountain" for `Mount Fuji`
   teaches a wrong fact. Confirm the file page actually names the right subject before
   accepting.

6. **Abstract / conventional** — `freedom`, `and`, `sound`, a grammatical particle.
   Often **no literal photo exists.** If there's a widely-understood convention or
   symbol for it, use that; otherwise **flag it as not image-suitable and move on** —
   don't force a misleading picture. Your subject sheet will tell you when to expect
   these and how it wants them handled.

Aim for **about 5** per referent, so the editor has room to pick the best — but 5
near-identical or mediocre shots don't help. Every one should be clean and clearly on
the meaning; for **broad** referents they should be genuinely *varied*. If you can only
honestly find 2 or 3 good ones, that's fine — quality beats hitting the number.

---

## Definition of done (per referent)

- About 5 image cards for the referent (a *varied set* for **broad** referents; fewer
  is fine if that's all you can honestly find), each showing green on the right.
- Search-picked cards: confirmed the auto-filled credit/licence looks right against the
  source page.
- Hand-added cards: source page URL, licence, and credit all filled in accurately.
- Every licence allows commercial reuse and modification (e.g. PD / CC0 / CC BY / CC BY-SA).
- The image clearly and unambiguously depicts the meaning, **judged by the referent's
  type** (see the type menu above — object vs broad vs action vs quality vs identity).
- **Abstract / not-suitable** referents: flagged as such (per your sheet's
  instruction), not forced with a misleading image.
- **Exported** — hit **export all** (or **export a selection**) and send back the file it
  produces. Re-sending a referent you've already handed in is fine — the editor's fold
  skips images it already has.

**Don't:** invent or guess a credit; use a non-free image "just this once"; add text
overlays or edit images; paraphrase a license string; force a picture onto a referent
that has no honest one.

---

## How the work is checked

The editor runs these — you don't need to:

1. `python3 data/fetch-referent-images.py <your-export>.json` — pulls the actual image
   files from the sources you recorded.
2. `python3 data/qc-viewer.py` — shows every candidate in a grid to keep the best and
   drop the rest, then folds the keepers in (`referents-from-qc.py`), taking your credit
   / licence strings **exactly** as you entered them (no rewording), and rejecting any
   non-free licence on the spot.
3. `python3 data/check-source.py` — confirms every referent resolves and is sound.
4. `python3 data/sourcing-status.py done <referent>` (or `later`) — dims that tile for
   everyone once it has enough, or when it should wait.

If something's off you'll get it back with a note — no problem, it's expected on the
first batch while we calibrate.

---

## Pay

- **Rate:** R20 per referent completed (a set of ~5 verified images + accurate recording).
- **Trial:** first small batch (≈5 referents) at full rate, so we can check the
  workflow fits and adjust anything before you do volume.
- Work at your own pace — there's no clock, just completed referents.

*(The subject sheet may set a different rate or trial size for a subject where the
sourcing is unusually hard — if so, its numbers win over these.)*
