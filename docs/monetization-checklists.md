# Monetization research — accountant & vendor checklists

Two action checklists distilled from the 2026-08-19 research pass on ZA
tax/registration and auth/payment options (spanning both **lang-pages** and the
**pit** September push). This is decision-support captured so it isn't buried in a
chat transcript — **not** financial, legal, or tax advice. Confirm anything
consequential with a real accountant / SARS / CIPC / the vendor directly. Pricing
and country-eligibility numbers move often; every figure is *"verify current."*

Access date for all figures below: **2026-08-19**.

Full payments/auth write-up (source): the published playbook artifact
`auth-payments-playbook.md` — <https://claude.ai/code/artifact/93e6e011-7678-47d1-b567-459e61fe90bc>.

The through-line of both reports: **keep the backend at zero as long as possible;
a merchant-of-record is the lever that lets you sell without a backend *or* a VAT
registration.** Ship paid content as a license-gated downloadable zip; add real
accounts only when a feature needs server-side state (cross-device sync, live
content, analytics), not merely to gate content.

---

## Checklist 1 — Questions to ask an accountant (ZA sole proprietor, digital sales)

Context the research already established (confirm, don't assume):

- A **sole proprietor needs no CIPC registration** — business income flows into the
  personal SARS return (ITR12). A brand-name CIPC registration is optional, not
  required.
- Non-salary income makes you a **provisional taxpayer** (IRP6): ~2 estimated
  payments/year + the final return; keep records **5 years**.
- The **compulsory VAT threshold was raised R1m → R2.3m** taxable supplies/12 months
  (effective **1 Apr 2026**; voluntary R50k → R120k). Flagged for re-verification —
  SA's 2025 VAT reversals show these numbers can move. Well below it = no VAT
  charging, no VAT201s, that whole layer stays off.
- A **merchant-of-record** (Paddle / Lemon Squeezy) remits *buyer-side* VAT/sales-tax
  worldwide, but that does **not** touch your ZA **income** tax — the payout is still
  taxable ZA income.

Questions that genuinely need a professional (the research couldn't settle these):

1. **VAT threshold & MoR revenue** — does revenue collected through a merchant-of-record
   count toward the R2.3m ZA VAT-registration threshold, and if so at **gross or net**?
   (The single most important open question — it determines when, if ever, VAT compliance
   kicks in.)
2. **MoR income is still taxable** — confirm MoR payouts are declared as ZA income on the
   ITR12 even though consumption tax was remitted abroad, and how to evidence that split.
3. **Provisional tax mechanics** — activating IRP6 on eFiling, the two-payment schedule,
   how to base estimates to avoid under-estimation penalties, and interaction with any
   salaried/PAYE income you also earn.
4. **Foreign-currency income** — how to declare USD MoR/PayPal payouts on the ITR12: which
   exchange rate/date, and whether PayPal/Payoneer fees are deductible against the gross.
5. **Deductions for a sole prop** — home-office apportionment, equipment, software/hosting
   (EC2), domain, and what substantiation SARS expects.
6. **Record-keeping** — exact records to retain for the 5-year window for digital-goods
   sales routed through third-party storefronts (order records, payout statements, MoR
   tax reports).
7. **Sole prop → Pty Ltd trigger** — at what revenue / liability / co-founder point does
   incorporating (flat 27% company tax + 20% dividends tax on drawings, plus annual
   returns) become worth the double-tax and overhead? For a learning site / math tool the
   liability exposure is low, so the default is **defer**.
8. **Brand-name CIPC registration** — any practical upside (banking, trademarks) to
   registering a trading name vs staying a bare sole prop?

Bottom line for the September push (per the report): **operate as a sole prop, use a
merchant-of-record for any international sales, set up clean bookkeeping from day one, and
the only new tax mechanic to actually learn is provisional tax.** VAT and incorporation are
"later, when revenue justifies it" problems.

---

## Checklist 2 — Vendor / payment-provider verification (before routing real money)

Everything here is flagged in the research as needing **direct confirmation** before real
revenue flows — ZA seller-eligibility on the country lists was ambiguous, and pricing
changes.

**Merchant-of-record (international sales — recommended path):**

- [ ] **Lemon Squeezy** — the recommended MoR bet. **Open a support ticket to confirm ZA
      *seller* eligibility** before the first real sale (five-minute email, cheap
      insurance). Verify the **PayPal-to-ZA-bank / wire payout** actually lands (this is the
      same rail confirmed working for Gumroad's ZA creators). Fee: flat **5% + $0.50**,
      twice-monthly payout. 🟡
- [ ] **Paddle** — get a **written yes** that South Africa is a supported *seller* (not just
      buyer) country; the official supported-countries doc did **not** clearly confirm SA in
      this pass. Do not build around Paddle until confirmed. 🔴
- [ ] **Polar.sh** — confirm **ZA is included** in the ~120 Stripe-Connect-Express payout
      countries (not confirmed in this pass). Newer/smaller ecosystem. 🔴
- [ ] **Gumroad** — the fastest "will anyone pay for this zip" test rail: confirmed for ZA
      creators via **PayPal/Payoneer**, ~10% flat, zero setup. Higher fee, but lowest
      friction for a first willingness-to-pay test. 🟡

**ZA-native gateways (ZA-only card/EFT sales — no worldwide-VAT handling):**

- [ ] **Paystack South Africa** — recommended ZA-native pick (Stripe-owned). Confirm current
      **2.9% + R1**, free settlements, ZA-bank settlement. Cleanest documented API of the
      set. 🟢
- [ ] **Payfast** — fallback if you specifically want its mature native recurring
      billing/tokenisation. Budget for **R8.70 per payout** and **R250 per dispute** (weekly
      payouts ≈ R450/yr in payout fees alone). 🟢/🟡
- [ ] **Yoco** — consider only if you also sell **in person** (POS + online in one
      dashboard). 🟡
- [ ] **Ozow** — cheapest for **EFT-heavy** ZA buyers (1.5% EFT); less of a full billing
      platform. 🟢

**Do NOT use:**

- [ ] **Stripe (direct)** — **not usable by a ZA-registered seller** (no native ZAR payout,
      no ZAR Stripe Connect). Reachable only indirectly via Paystack or a foreign legal
      entity. Most Stripe advice online silently assumes a US/EU/UK seller — don't build
      around it. 🟢

**Licensing / entitlement (keeps the zip model backend-free):**

- [ ] **Lemon Squeezy License API** — `validate` / `activate` / `deactivate` (rate-limited
      60 req/min) auto-issues a key on purchase with zero backend code. Confirm it covers
      per-device activation limits you need. 🟢
- [ ] **Keygen** — only if LS's built-in keys aren't enough: fair-source, free-to-self-host
      Community Edition or metered Keygen Cloud. Still a key-check, not a login system. 🟢
- [ ] **Subscriptions caveat** — a subscription license needs to "phone home" periodically to
      confirm it's still active, which quietly reintroduces a server call. One-off purchases
      stay purest-no-backend; recurring billing edges you toward a minimal backend (Supabase)
      eventually.

**Auth (defer until a feature needs server-side state):**

- [ ] **Supabase Auth** — the pick *when* you need accounts, because it bundles the Postgres
      you'd need anyway for entitlements/progress. Free 50k MAU. Don't wire it up just to gate
      content — the license-gated zip replaces accounts-for-entitlement. 🟢
- [ ] **Self-hosting any IdP** (Keycloak/Ory/Authentik/Authelia) — explicitly **against** the
      avoid-attack-surface goal; a new always-on service to patch on the public box. Skip
      unless a managed free tier is genuinely insufficient.

---

## Bookmarks to verify against

**Official (ZA tax/registration — the authoritative sources):**

- SARS — Provisional Tax (IRP6): registration, payment dates, penalties
- SARS — VAT registration thresholds & digital/electronic-services rules (re-verify the
  R2.3m / R120k figures and the 1 Apr 2026 effective date)
- SARS — ITR12 (personal income tax return, where sole-prop income is declared)
- CIPC — company registration & name reservation (only if incorporating / registering a
  trading name)

**Vendor docs (pricing + ZA eligibility — all "verify current"):**

- Lemon Squeezy — pricing, payout countries, and the License API
  (`docs.lemonsqueezy.com/api/license-api`)
- Paddle — supported countries/locales (`developer.paddle.com/concepts/sell/supported-countries-locales`)
- Polar.sh — payout-country coverage
- Paystack South Africa — fees & settlement terms
- Payfast — fee schedule (incl. payout & dispute fees)
