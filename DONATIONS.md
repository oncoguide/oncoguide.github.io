# OncoGuide Donations -- Architecture and Implementation Plan

Single source of truth for the public Donate / Doneaza page and its document-generation
flows. Written so a context-free agent (Claude Fable 5) can implement it without prior
conversation. Follow `CLAUDE.md` content conventions (no emojis, no em-dashes, no
typographic quotes; use double hyphens and standard quotes).

> Scope split: Sections 1-13 plus Appendix A are the ARCHITECTURE (reviewed by a fresh Fable
> agent, gate > 9.2/10). Section 14 is the TASK PLAN (each task reviewed by Gemini, gate
> > 9.1/10). Implementation is done by Claude and reviewed by a fresh Fable agent (gate
> > 9.3/10). All gates and scores are tracked in Section 0.

---

## 0. Status and Scorecard

| Stage | Reviewer | Gate | Score | Status | Date |
|-------|----------|------|-------|--------|------|
| Architecture v1 (S1-S13) | fresh Fable agent | > 9.2 | 7.6 | FAIL -- rebuilt as v2 | 2026-06-11 |
| Architecture v2 (S1-S13 + App. A) | fresh Fable agent | > 9.2 | 8.7 | FAIL -- revised as v3 | 2026-06-11 |
| Architecture v3 (S1-S13 + App. A, B) | fresh Fable agent | > 9.2 | 8.6 | FAIL -- revised as v4 | 2026-06-11 |
| Architecture v4 (S1-S13 + App. A, B) | fresh Fable agent | > 9.2 | 8.9 | FAIL -- revised as v5 | 2026-06-11 |
| Architecture v5 (S1-S13 + App. A, B) | fresh Fable agent | > 9.2 | 9.0 | FAIL -- revised as v6 | 2026-06-11 |
| Architecture v6 (S1-S13 + App. A, B) | fresh Fable agent | > 9.2 | **9.4** | **PASS** | 2026-06-11 |
| Task plan (S14, each task) | Gemini CLI | > 9.1 | T1:9.5 T2:9.2 T3:9.9 T4:10 T5:10 T6:9.8 T7:10 | **ALL PASS** | 2026-06-11 |
| Architecture v7 correction (S7 + App. A) | fresh Fable agent | > 9.2 | **9.4** | **PASS** -- T3 fill-test proved the ANAF beneficiary/entity sections have NO fillable fields; OncoGuide data pre-filled by positioned TEXT OVERLAY on the unchanged original (verified: 0/66 + 0/101 fields moved, coords match precompletate to the decimal, overlay text is pure ASCII). 4 non-blocking polish items (scara entry, 230 page-2 policy, 177 amount row, PAGE_H scope) noted. See D6. | 2026-06-11 |
| Implementation | fresh Fable agent | > 9.3 | T1+T2: 9.5 | T1+T2 PASS (4313d7f + 66093a2). T3 IN PROGRESS: pdf-lib vendored, ANAF originals downloaded + SHA-pinned, fill-test.mjs PASS, field-maps.js with verified fields + overlay coords done; generators (T4-T7) pending. | 2026-06-11 |

v1 -> v2 changelog (from the v1 review, score 7.6): rebased the document engine on the
**verified** fact that ANAF Forms 177 and 230 are plain AcroForms (no XFA, no validation
barcode); replaced the barcode-honesty subsystem with accurate per-form submission routes
(7.4); qualified the e-signature claim for the company contract (D3); pulled the verified field
inventory into Appendix A and defined the exact mapping method; defined non-Romanian visitor
behavior on the generator routes (5.1); added the "never flatten ANAF forms" rule, the
microenterprise guard, the contract-template anonymity audit, and lazy-loading.

v2 -> v3 changelog (from the v2 review, score 8.7): replaced the fragile `NeedAppearances`
prose with the exact pdf-lib private-API call plus a reload-assert test, and warned that a
byte-grep for the flag false-fails because pdf-lib writes object streams (7.3.5, App. A);
documented and classified the pushbutton (`/Btn` non-data) widgets so they are not mistaken for
options (7.3, App. A); made the privacy page all 6 languages to match the codebase pattern
(5.1, 12, 13); moved the dead 2026 F177 deadline to 2027 and made deadline logic show "window
closed this cycle" while `registru163_active` is false (9.2, 10); fixed the web3forms retention
figure and added a US-server disclosure (11, 12); turned the anonymity audit into a runnable
pre-commit script (12); added Appendix B (sponsorship-contract field schema); deferred the XFA
fallback to Section 16; added a mobile `mailto:` UX note (7.5).

v3 -> v4 changelog (from the v3 review, score 8.6): added the `.gitignore` exceptions for the
two `data/` files (build-breaker -- `data/*` is ignored) to Section 13 + T1; corrected the
Form 230 mirror to the exact 2 mirrored fields, not a full copy (7.3.4, App. A); made the
company tax-regime handling config-driven and flagged the disputed microenterprise-vs-Form-177
rule (current ANAF sources say microenterprises CAN use Form 177; the project's `.private/`
notes say they cannot -- to confirm with the accountant), while encoding the verified IMCA
exclusion and fixing the Form 107 description (8.1); broadened the anonymity audit to a
source-tree grep with a gitignored name source (12); fixed the consent-link to use Hugo's
language-aware ref (12); committed to the `donate/_index.md` -> `list.html` landing layout (13);
fixed the Section 4 diagram privacy-page regression (now all 6 languages).

v4 -> v5 changelog (from the v4 review, score 8.9; all three blockers were Hugo wiring): made
the custom layouts actually fire by mandating `type: donate-landing` / `type: donate-generator`
front matter and `layout: page` on stubs + privacy pages, with the Hugo lookup rule documented
(5.1); replaced the non-working "`ref` to a translationKey" consent-link mechanism with
language-scoped `site.GetPage "/donate-privacy"` (12); unified the privacy page name to
`donate-privacy` everywhere (was split with `donation-privacy`); mandated one canonical audit
name source (`REPRESENTATIVE_NAME` env var fed from a gitignored `.private/` file, exported by
the pre-commit hook) (12); added the ~90-day ANAF payout note to the 230 flow (8.2); marked 230
`TextField2[1]` as deliberately unused (App. A); documented why `updateFieldAppearances()` must
not replace the private-dict NeedAppearances approach (7.3.5).

v5 -> v6 changelog (from the v5 review, score 9.0; one blocker + 6 fix-items): resolved the
signed-230 contradiction by removing in-browser signing from ANAF forms entirely -- the
signature exists ONLY on the sponsorship contract; the 230 is printed and signed by hand (D3,
6.5, 7.4, 8.2, T5, S15); extended "never flatten" to the contract too (countersignature fields
must stay fillable) (7.1); deleted the unsupported ~30-day retention figure, keeping the
verified ~2-month log purge (12); flipped the microenterprise presumption to NOT eligible per
OUG 115/2023 (matching the `.private/` notes), with the accountant able to flip config, and made
the sub-path (a) tax-credit messaging regime-conditional (8.1); made the no-PII ping strictly
opt-in on the send-copy click, never automatic on generate (11, T4); extended the GDPR consent
to the company flow (12); reconciled 8.2 data entry with the 230's actual field capacity
(collect only mapped fields; no email field); hardened the audit script edge cases (unset env
var hard-fails, missing template skips with warning, npm pdf-lib devDependency) and widened the
grep to all donate assets (12); moved pdf-lib vendoring into T3 (fill-test needs it); noted the
UMD `PDFLib` global vs ESM import (7.3.5); allowed localized stub slugs via `slug:` (5.1).

Post-PASS polish (v6 review's 9 non-blocking items, applied after the 9.4 PASS, no semantic
changes to reviewed decisions): short fill-test markers respecting maxLength (7.3.2); audit
grep over full `git ls-files` (12); data-to-JS bridge via `jsonify` (5.1); `email:` added to
`association.yaml` with pre-commit allowlist note (9.1); `sponsor_semnatura` pinned to
pushbutton + `setImage` (App. B); consent checkbox placement aligned to step 5 (8.2); web3forms
~30-day submission retention noted (12); `package.json` added to the layout (13); audit script
moved to T1, generator layout to T4, accountant checklist (incl. the OUG 153/2020 deadline
question) to T6 (S14).

Post-T2 owner refinement (2026-06-11, decision D5): the five non-Romanian landing pages were
reduced to direct-donation-only (removed the "Romanian taxpayers: two options" section, the tax
status callout, and the generator links from en/it/fr/de/es `donate/_index.md`). The Romanian
landing is unchanged and still presents all three paths. This only removes content from non-RO
pages (strictly less surface, no new risk) and does not alter any reviewed S7-S13 engine or
generator decision. See D5 (Section 2) and Section 5.1.

v6 -> v7 correction (2026-06-11, decision D6; discovered during T3 implementation, PENDING a
fresh-Fable re-review of S7 + Appendix A): the T3 fill-test empirically proved that Appendix A's
provisional field meanings were wrong and, more importantly, that **the ANAF beneficiary/entity
sections have NO fillable AcroForm fields**. On Form 230 only `year` + donor `CNP` (+ their
page-2 mirrors) are fillable text fields; `TextField4[0/1]` are the tax-office "Nr.
inregistrare/Data" boxes and `TextField2[1]` is the proxy code (all left blank). On Form 177 the
company's own section I is fillable, but the beneficiary block (where OncoGuide goes) is not.
OncoGuide's CIF/denumire/IBAN (and the donor's name/address) therefore cannot be set via
`setText` -- they are pre-filled by a **positioned text overlay** on the unchanged original page,
exactly how the `.private` precompletate were produced (verified: identical 595.276x841.890 page
geometry, so overlay coordinates transfer). This honors the owner's hard rule (D6): use the
standard ANAF form, never change its fields/format, only add values -- in real fields where they
exist, as a text layer at the form's own positions where they do not. The verified field/checkbox
inventory and overlay coordinates are in Appendix A and `static/donate/js/field-maps.js`. This
changes the document engine (T4 must add overlay drawing) and the 230/177 generators (T5/T6
collect only what maps to a destination; the rest is hand-completed after printing).

---

## 1. Goal and Scope

Add a Donate / Doneaza page to the OncoGuide blog (https://oncoguide.github.io), reachable
from the main menu like Contact, in all 6 languages. The page lets supporters of Asociatia
OncoGuide contribute through the three legal Romanian mechanisms, mirroring the user flow of
https://www.daruiesteviata.ro/sponsorizeaza and https://www.daruiesteviata.ro/formular-230,
adapted to a static site.

Three supported paths:

1. **Firme -- sponsorizare / redirectionare (the "20%" path).** A guided flow with a ceiling
   calculator, a sponsorship contract generated in the browser, and (for the redirection
   variant) a pre-filled ANAF Form 177.
2. **Persoane fizice -- redirectionare 3,5% (the "3.5%" path).** A guided flow that pre-fills
   the official ANAF Form 230.
3. **Donatie directa (universal).** Bank transfer to the association IBAN. Available in all
   languages and to non-Romanian supporters. No tax mechanism, no form.

Everything runs client-side. The site stays 100% on GitHub Pages. The generated documents are
the supporter's to keep and submit; the association receives copies only when supporters send
them, and those copies are the archived source of truth.

---

## 2. Confirmed Product Decisions

These four decisions were made by the project owner and are fixed for v1. Do not revisit them
during implementation without explicit instruction.

| # | Decision | Choice | Consequence |
|---|----------|--------|-------------|
| D1 | Backend model | **Static, no server.** All logic and PDF generation run in the supporter's browser. | Zero hosting cost, no PII held by us, stays on GitHub Pages. No centralized ANAF submission (that would require holding CNPs). |
| D2 | Source of truth | **Email to association -> archived in `.private/finantare/arhiva/` + a private Google Drive folder.** | `registru-donatii.md` is the manual index. No PII in git, ever. |
| D3 | Signature | **Simple electronic signature drawn/typed in the browser, embedded ONLY in the sponsorship contract (our document), as a convenience draft. ANAF forms are NEVER signed in the browser** -- the supporter signs the printed Form 230 by hand. | See the qualification below: for the company contract presented to ANAF, the intended legally robust route is print + wet signature (or qualified e-signature) by both parties. The in-browser signature does not by itself guarantee legal sufficiency for that path. |
| D4 | Anonymity | **Representative legal name appears only inside the generated contract PDF, never on the page or in git.** | The contract template leaves the association signature block blank for offline countersignature. Public association identifiers (name, CIF, IBAN, sediu) may appear -- they are public registry data and required on the documents. |
| D5 | Non-RO landing scope (added 2026-06-11) | **Non-Romanian landing pages show ONLY the direct-donation (bank transfer) path -- no 20% / 3.5% tax mechanisms, no links to the generators.** | The RO tax mechanisms apply only to Romanian taxpayers; other languages get a clean donation-only page (modeled on daruiesteviata.ro's general support page). Only the RO landing presents all three paths. See Section 5.1. |
| D6 | ANAF fill mechanism (added 2026-06-11) | **Use the standard ANAF PDFs unchanged; pre-fill values only. Where the form has a real AcroForm field (year, donor CNP on 230; the company's own section on 177), set it; where it has none (OncoGuide's beneficiary/entity block; donor name/address), add a positioned TEXT OVERLAY at the form's own position.** Never rename, move, resize, restyle, or flatten a field. | Verified in T3: the beneficiary/entity sections have no fillable fields. Overlay is exactly how the `.private` precompletate were made and keeps the official layout intact. See the v7 changelog, Section 7, and Appendix A. |

**D3 qualification (important).** Romanian law gives a simple electronic signature full effect
only under narrow conditions; for documents presented to authorities or third parties a
qualified signature is recommended. The company sponsorship contract redirecting profit tax is
exactly such a document. Therefore the in-browser signature is offered as a convenience for the
supporter's working copy, and the UX states plainly that, for ANAF purposes, the contract
should be printed and wet-signed (or qualified-signed) by both parties. Form 230 carries NO
in-browser signature: drawing a signature image onto the ANAF PDF would violate the fidelity
constraint (Section 3.2 / 7.2, values-only, no new drawing), and the paper route requires a
handwritten signature anyway -- the supporter prints the pre-filled 230 and signs by hand. ANAF
e-submission, where used, relies on the supporter's own SPV authentication, not on any
embedded signature.

---

## 3. Constraints and Principles

1. **Static host.** No server-side code. No database. No build-time secrets beyond the
   existing public web3forms key.
2. **ANAF form fidelity (hard constraint).** Official ANAF forms (177, 230) must remain the
   exact original ANAF PDF. We only set values on the existing named AcroForm fields. We never
   redraw, re-typeset, move, rename, resize, restyle, or flatten them. See Section 7 and
   Appendix A.
3. **No PII in git.** Supporter data (names, CNP, CUI, addresses) never enters the repository,
   not even a private one. It lives only in the browser and, if the supporter chooses, in the
   email they send and the association's private archive.
4. **No third-party PII transit by default.** The generated document travels from the
   supporter's own email client directly to the association inbox. The optional web3forms
   notification carries no personal data (see Section 11).
5. **No external runtime services.** Libraries are vendored in `static/`, not hot-linked from a
   CDN. Matches the existing GDPR-friendly privacy posture in `hugo.yaml` (no analytics, no
   external embeds) and works offline.
6. **Honesty over polish.** The UX must state plainly what each document is and how to submit
   it (Section 7.4). Never imply a generated PDF can be e-submitted as-is where that is untrue.
7. **Feature-flag the tax benefit.** The deductible mechanisms require OncoGuide to be in the
   ANAF Registrul entitatilor nonprofit (Form 163), which is not yet done. The build must be
   deployable now with only the direct-donation path live, and switch the tax paths on with a
   single config flag later. See Section 10.
8. **i18n-ready.** The landing page exists in all 6 languages. The two generator flows are
   Romanian-tax-specific; they ship in Romanian, and every other language serves a localized
   stub (Section 5.1) so no internal link is ever broken.
9. **Match the house style.** Minimalist, clean medical aesthetic; dark-mode compatible;
   WCAG AA; reuse existing shortcodes (`disclaimer`, `callout`, `action-box`) and CSS patterns.

---

## 4. System Overview

```
                 +-------------------------------------------------------+
                 |                  GitHub Pages (static)                |
                 |                                                       |
  Supporter ---> |  /donate/  (landing, 6 langs)                        |
   browser       |     |                                                 |
                 |     +--> /donate/firme/           (RO gen; stub x5)   |
                 |     +--> /donate/persoane-fizice/  (RO gen; stub x5)  |
                 |     +--> direct donation (IBAN, all langs)            |
                 |     +--> donate-privacy (privacy statement, all 6)   |
                 |                                                       |
                 |  Vendored JS, lazy-loaded on the generator pages:    |
                 |    pdf-lib (fill AcroForm + embed signature image)   |
                 |    signature canvas                                  |
                 |    flow controllers + field map + i18n strings       |
                 |                                                       |
                 |  Static assets: original ANAF PDFs, contract         |
                 |  template, data/association.yaml, data/fiscal.yaml   |
                 +-------------------------------------------------------+
                          |                                  |
            generated PDF (download)            optional no-PII ping
                          |                                  |
                          v                                  v
              Supporter keeps + emails          web3forms --> association inbox
              the copy to association                  (heads-up only)
                          |
                          v
       Association archives copy: .private/finantare/arhiva/{year}/
       + private Google Drive  ;  indexes it in registru-donatii.md
```

Components:

- **Content layer (Hugo).** Markdown pages + custom layouts that inject the generator UI and
  lazy-load the JS. Menu entry, i18n strings, data files.
- **Document engine (browser JS).** Loads a template PDF, sets values on its named AcroForm
  fields, embeds the signature image, triggers download. Pure client-side; no network call to
  generate.
- **Data layer (Hugo data files).** `data/association.yaml` (public identifiers, single source)
  and `data/fiscal.yaml` (deadlines, ceilings, feature flags).
- **Archival layer (manual + Drive).** Outside the repo. The association files received copies
  and updates `registru-donatii.md`.

---

## 5. Page and Content Architecture

### 5.1 Routes and pages

| Route | translationKey | Languages | Layout (front-matter key that selects it) | Purpose |
|-------|----------------|-----------|--------|---------|
| `/donate/` | `donate` | all 6 | `type: donate-landing` -> `layouts/donate-landing/list.html` | Choose a path; explain the 3 mechanisms; show IBAN. |
| `/donate/firme/` | `donate-companies` | RO = full generator; en/it/fr/de/es = localized stub | RO: `type: donate-generator` -> `layouts/donate-generator/single.html`; stubs: `layout: page` | Company sponsorship + Form 177 flow. |
| `/donate/persoane-fizice/` | `donate-individuals` | RO = full generator; en/it/fr/de/es = localized stub | RO: `type: donate-generator`; stubs: `layout: page` | Form 230 flow. |
| `/donate-privacy/` | `donate-privacy` | all 6 | `layout: page` | Privacy statement for the donation flows (Section 12). All 6 languages, one filename `donate-privacy.md` per language (URL may be localized via `slug:`; links resolve by logical path, Section 12). |

**Layout lookup (critical Hugo detail).** Hugo selects a layout from the page's section and
`type`/`layout`, NOT from the layout directory name. A section page `donate/_index.md` would
otherwise resolve to `layouts/donate/list.html` -> `layouts/_default/list.html`, never to
`layouts/donate-landing/`. Therefore the custom layouts fire ONLY because the front matter sets
`type:` explicitly: `type: donate-landing` on `donate/_index.md`, and `type: donate-generator`
on the Romanian `firme.md` / `persoane-fizice.md`. The 5 localized stubs and the privacy pages
set `layout: page` so they use PaperMod's standard page layout (same as `contact.md`). Stub
URLs may localize the Romanian slugs (`firme` -> `companies`, etc.) via `slug:` front matter;
internal links must then use `GetPage`/`relref` by logical path, never hard-coded slugs.

**Data-to-JS bridge.** The generator layout injects the Hugo data the JS needs as JSON:
`<script>window.oncoDonate = {{ dict "assoc" site.Data.association "fiscal" site.Data.fiscal | jsonify | safeJS }};</script>`
(or equivalent data attributes). The flow scripts read `window.oncoDonate`; they never fetch
YAML at runtime and never duplicate association data as JS literals.

The landing page exists in all 6 languages for menu consistency and SEO. **In non-Romanian
languages it presents ONLY the universal direct-donation path (bank transfer).** The Romanian
tax mechanisms (company sponsorship 20% / individual redirect 3.5%) are NOT shown or linked on
the non-RO landing pages -- those mechanisms apply only to Romanian taxpayers, and the owner
chose a clean donation-only page for other languages (D5, modeled on daruiesteviata.ro's
general "support us" page). Only the Romanian landing shows the three paths. The localized
generator stubs still exist (so the language switcher on the Romanian generator pages never
breaks), but they are not promoted from the non-RO landing.

**Non-Romanian visitor behavior on the generator routes (defined, not deferred).** Because
`hugo.yaml` uses `defaultContentLanguageInSubdir: true` and per-language `contentDir`, a missing
translation yields no page in that language tree and would break the localized landing links.
Therefore each generator route ships a **thin localized stub** in en/it/fr/de/es (same
`translationKey`, `layout: page`) that says, in that language, "this tax mechanism applies to
Romanian taxpayers" and links to the Romanian generator and to the universal direct-donation
option. The full interactive generator (with JS) renders only for the Romanian version. This
guarantees every internal link resolves and keeps `translationKey` consistent across languages.

### 5.2 Menu

Add a `donate` menu item to all 6 language menus in `hugo.yaml`, weight `28` (between
treatment at 18 / cancer-types at 20 and contact at 30). Names: `Doneaza` (ro), `Donate` (en),
`Dona` (it), `Faire un don` (fr), `Spenden` (de), `Donar` (es). Per the `CLAUDE.md` dependency
map, updating `hugo.yaml` menus requires updating the `CLAUDE.md` File Structure section in the
same commit.

### 5.3 Content per page

Each page is honest, warm, patient-author voice, follows content conventions, and ends with the
`disclaimer` shortcode. Landing page includes an `action-box`. The generator pages embed the
multi-step UI (Section 6) plus plain-language explanations of the mechanism, eligibility, the
deadline, and what to do with the generated document.

---

## 6. The Multi-Step Flow Pattern

Both generators use the same step machine, a multi-step pattern modeled on the daruiesteviata
flow (we do not assert a specific step count), driven by vanilla JS, no framework. Steps
render/hide `<section>` blocks; state lives in a single in-memory object; nothing is persisted.

Common steps:

1. **Intro / eligibility.** Who this is for, the deadline status, what they will get.
2. **Calculator** (companies only) or **eligibility confirm** (individuals).
3. **Data entry.** Fields per Section 8. Inline validation (required, CUI/CNP format, IBAN).
4. **Review.** Read-only summary of entered data.
5. **Sign / consent.** Companies flow only: canvas signature (draw) with a typed-name fallback,
   embedded in the sponsorship contract. Individuals flow: NO signature step (the ANAF 230 is
   never signed in the browser, per D3); this step holds only the consent checkboxes.
6. **Done.** Generate + download the PDF(s); show submission instructions and the optional
   "send us a copy" action.

Accessibility: keyboard navigable, focus management on step change, ARIA live region for
validation errors, labels bound to inputs.

---

## 7. Document Generation Engine

### 7.1 Library

Use **pdf-lib** (MIT, pure JS, browser-compatible). Capabilities used: load an existing PDF,
set values on named AcroForm text fields and checkboxes, embed a PNG (signature), set the
AcroForm `NeedAppearances` flag, and save to bytes for download. Vendored at
`static/donate/js/pdf-lib.min.js`; pinned version + SHA-256 recorded in Section 13.
Lazy-loaded: the engine loads only when the user reaches the generate step, not on page load
(mobile data consideration).

**Flatten rule: never flatten ANYTHING.** Never flatten the ANAF forms (flattening can alter
appearance across viewers and removes the supporter's ability to correct a value in their own
reader). Never flatten the sponsorship contract either: its blank `beneficiar_*` fields must
remain fillable for the association's offline countersignature (D4, Appendix B); flattening
would destroy them.

Signature capture (sponsorship contract ONLY -- never on ANAF forms, per D3): a small canvas
helper (`signature.js`, hand-rolled, ~80 lines, or a vendored MIT signature-pad -- if vendored,
pin it). Output: PNG data URL -> `embedPng` -> drawn into the contract's signature area.

### 7.2 Two document kinds, two strategies

- **Official ANAF forms (177, 230):** original PDF is sacred. Pre-fill values only, two
  mechanisms on the SAME unchanged page (D6, verified in T3): (1) `setText`/`check` on the real
  AcroForm fields that exist (Form 230: year, donor CNP + page-2 mirrors, the option/consent
  checkboxes; Form 177: the company's own section I + the "point 1 non-profit beneficiary"
  checkbox); (2) a positioned **text overlay** (`page.drawText`) for the values the form has no
  field for -- OncoGuide's beneficiary/entity block (CIF, denumire, IBAN, the 3,5% on 230) and,
  if collected, the donor's name/address. Overlay coordinates and field names are in
  `static/donate/js/field-maps.js` (Appendix A). No field is renamed, moved, resized, restyled,
  or flattened; the overlay only adds a text layer at the form's own positions -- identical to how
  the `.private` precompletate were produced. OncoGuide's constant data has no diacritics, so a
  standard Helvetica overlay renders it correctly.
- **Sponsorship contract (our document):** we own the template. Author it once as a fillable
  PDF (AcroForm) per language, bundle it, set fields + embed signature. The association
  signature block is a blank field, filled offline at countersignature (D4). This keeps the
  representative name out of the repo while still producing a complete, signable contract.

### 7.3 ANAF form fill procedure (verified)

The internal format of both forms is already characterized (see Appendix A, verified by
inspection): both are plain **AcroForms** with named fields, **no XFA**, **no NeedsRendering**,
and **no client-generated validation barcode**. pdf-lib fills them with `getField(name)` +
`setText` / `check`. The procedure:

1. **Bundle the blank originals** in `static/donate/templates/` (download once from anaf.ro):
   - Form 230: `https://static.anaf.ro/static/10/Anaf/formulare/230_OPANAF_103_2025.pdf`
   - Form 177: `https://static.anaf.ro/static/10/Anaf/formulare/177_A2_OPANAF_3562_2024.pdf`
   Record version + SHA-256. If ANAF publishes a newer revision, re-run the fill-test (below).
2. **Field name -> meaning map.** The field names are opaque (e.g.
   `form1[0].#subform[0].TextField2[0]`), so the map is produced once by a **fill-test**: set
   each text field to a SHORT unique marker (e.g. a zero-padded index like `01`, `02` --
   respecting each field's `maxLength`, since full field names exceed the 1/4/13-char limits and
   pdf-lib throws), save, open the PDF, and read off which visible box each marker landed in. Cross-check positions against the flattened pre-filled
   copies in `.private/finantare/formular-230-precompletat.pdf` and
   `formular-177-precompletat.pdf`, which visually show exactly where the association data sits.
   The resulting `name -> meaning` table is committed as `static/donate/js/field-maps.js`
   (field names only; no values, no PII). Appendix A lists the verified field inventory to start
   from.
3. **Respect `maxLength`.** Some fields are comb cells with a max length (e.g. CNP is one
   13-char field `TextField2[*]` on 230; the year field is 4 chars; on 177 `cif_nr[0]` is a
   single attribute character and `cif_nr[1]` the CIF). Validate and split input accordingly;
   never exceed `maxLength` (pdf-lib throws).
4. **Mirror fields (exact, verified).** Form 230's page 2 carries a PARTIAL mirror prefixed
   `1.`, not a full copy. Only two base fields are mirrored and must receive the same values:
   `TextField2[0]` (CNP) -> `1.form1[0].#subform[0].TextField2[0]`, and `TextField13[0]`
   (year / number-of-years) -> `1.form1[0].#subform[0].TextField13[0]`. The name fields
   (`TextField4[*]`) and `TextField2[1]` have NO mirror. Do not loop "copy every base field to a
   `1.` twin" -- the twin does not exist for most fields and pdf-lib will throw.
5. **Diacritics / appearances (exact recipe -- verified).** pdf-lib has no public
   `needAppearances()` method. After setting values, set the flag via the documented private
   path and skip pdf-lib's appearance generation so the viewer regenerates field appearances
   using the form's own embedded fonts (which cover Romanian diacritics):
   ```js
   // Browser (vendored UMD pdf-lib.min.js exposes the PDFLib global):
   const { PDFName, PDFBool } = PDFLib;
   // (In a Node test script with the npm package: import { PDFName, PDFBool } from 'pdf-lib')
   form.acroForm.dict.set(PDFName.of('NeedAppearances'), PDFBool.True);
   const bytes = await pdfDoc.save({ updateFieldAppearances: false });
   ```
   **Verification trap (verified):** do NOT assert the flag by byte-grepping the saved PDF.
   pdf-lib serializes into object streams, so a search for `NeedAppearances` -- and even for
   `/AcroForm` -- returns false on a correctly-flagged output. Assert instead by reloading:
   `(await PDFDocument.load(bytes)).getForm().acroForm.dict.has(PDFName.of('NeedAppearances'))`
   must be true. This private-dict approach is DELIBERATE: do not "simplify" it to pdf-lib's
   `form.updateFieldAppearances()`, which regenerates appearances with pdf-lib's own fonts and
   can drop Romanian diacritics; we want the viewer to regenerate appearances using the form's
   embedded fonts. Then the fill-test must visually confirm that values AND Romanian diacritics
   (s-comma, t-comma, a-breve, a-circumflex, i-circumflex) render in Adobe Reader, Chrome's PDF
   viewer, and macOS Preview. If any field renders blank or loses diacritics, fall back to
   setting that field via pdf-lib with an embedded Romanian-capable font (which generates an
   explicit appearance for just that field).
6. **Pushbutton (`/Btn`) widgets (verified).** pdf-lib reports many non-data pushbutton widgets
   that are NOT data-bearing options: 51 `PDFButton` on Form 230 and 73 on Form 177 (these are
   the visual cell/box widgets). The data-bearing options are the checkboxes only (8 on 230, 7
   on 177); pdf-lib finds zero radio groups. The fill-test must (a) confirm each `PDFButton` is a
   pushbutton with no on-state and leave it untouched, and (b) confirm every option the flows
   need to set (e.g. the 2-year redirection on Form 230) maps to one of the checkboxes. Never
   set a pushbutton.
7. **Never** add, remove, rename, move, resize, restyle, or flatten an ANAF field. Only values
   change.
8. **Association fields** (denumire, CIF, IBAN, sediu) are filled from `data/association.yaml`
   so they live in exactly one place. **Supporter fields** are filled from the form state.
9. **Future-proofing.** If a future ANAF revision ships an XFA form, see the deferred fallback
   in Section 16; the current versions are AcroForms and need none of it.

### 7.4 Submission routes (honesty rule, corrected)

The pre-filled ANAF PDFs are accurate, fillable AcroForms in the original ANAF layout. State
the real submission routes plainly; do not over- or under-promise:

- **Form 230 (individuals):** valid routes are (a) print -> sign -> submit on paper at the
  supporter's tax office or by registered mail; (b) upload through the supporter's own SPV
  account; (c) hand to an authorized intermediary. Our pre-filled 230 is directly usable for the
  paper route (print, sign by hand, submit), which the page presents as the simplest. The SPV
  route is offered for those who prefer it.
- **Form 177 (companies):** filed by the company's accountant through the company's own SPV by
  the 25 June deadline. Our pre-filled 177 is a faithful reference draft in the original layout;
  the page says so and does not imply we submit it.

### 7.5 Output and delivery

- Generate -> `pdfDoc.save()` -> `Blob` -> object URL -> auto-download with a clear filename,
  e.g. `Contract-Sponsorizare-OncoGuide-{companySlug}.pdf`, `Formular-230-OncoGuide-{nameSlug}.pdf`.
- Then show submission instructions and a "Trimite-ne o copie" action that opens the
  supporter's own mail client (`mailto:` to the association address, pre-filled subject/body,
  with a note to attach the just-downloaded file). This keeps PII off third-party servers. Keep
  the `mailto:` body short (under ~300 chars) because some mobile mail clients truncate long
  bodies; the on-page instructions carry the detail, and the body only reminds the supporter to
  attach the downloaded PDF.

---

## 8. The Document Flows in Detail

### 8.1 Companies -- sponsorship and Form 177 (the "20%" path)

First, **company tax-regime guard (config-driven, do not hard-code contested fiscal rules).**
Ask the company's regime: profit tax (impozit pe profit, 16%), microenterprise income tax
(impozit pe veniturile microintreprinderilor), or taxed at the IMCA minimum-turnover tax. The
flow reads eligibility, ceilings, and deadlines from `data/fiscal.yaml` (sourced from the
association's accountant-maintained `.private/finantare/` notes); it must not embed a hard-coded
"regime X cannot use Form 177" rule in JS, so the rule can be corrected by editing config.

Known facts to encode in config (each flagged for accountant confirmation at T6, because sources
conflict as of 2026-06):
- **Verified:** a company whose tax is established at the IMCA minimum-turnover-tax level cannot
  redirect via Form 177 (Art. 42 of the Tax Code does not apply at IMCA level). The flow blocks
  Form 177 for the IMCA case.
- **Presumed NO, confirm with accountant:** whether microenterprises may still use Form 177.
  Per OUG 115/2023, microenterprises lost the sponsorship tax credit and the Form 177
  redirection starting with fiscal 2024 -- which matches the project's `.private/finantare/`
  notes; the OPANAF 3562/2024 form retains micro fields, but these serve legacy windows. Default
  `data/fiscal.yaml` to microenterprises NOT eligible; the accountant can flip the config if a
  current exception applies. Until confirmed, the company generator stays gated by
  `registru163_active` (false) anyway, so nothing ships an unverified rule.
- Consequence for sub-path (a): the sponsorship tax credit is also regime-dependent --
  microenterprises get NO credit post-2024, so for them the page presents sponsorship honestly
  as a donation-equivalent (no fiscal benefit) unless the accountant confirms otherwise.
- **Form 107** is the informative declaration about sponsorships granted (filed with the annual
  return), NOT a redirection mechanism; do not present it as an alternative to Form 177.

Sub-paths chosen at step 1 (Form 177 sub-path offered only for regimes marked eligible in
`data/fiscal.yaml`):
- **(a) Sponsorizare in cursul anului:** company pays the amount to the IBAN now. Output:
  signed sponsorship contract. Available to any regime, but the tax-credit messaging is
  regime-conditional (see the config notes above: profit-tax companies get the credit;
  microenterprises post-2024 presumably do not).
- **(b) Redirectionare prin Form 177:** company redirects already-owed tax (profit tax, or
  microenterprise income tax if config marks it eligible; never at IMCA level). Output:
  sponsorship contract WITH the Article 5 clause that payment is made via Form 177, plus a
  pre-filled Form 177.

Calculator (step 2): inputs depend on regime. For profit-tax companies: `cifra de afaceri`,
`impozit pe profit`, `sponsorizari deja acordate in anul curent`, ceiling =
`min(0.0075 * cifra de afaceri, 0.20 * impozit pe profit)`. For microenterprises (if config
marks them eligible): the 20% applies to microenterprise income tax instead of profit tax; the
ceiling formula and label come from `data/fiscal.yaml` so the regime base is not hard-coded.
Available = `ceiling - sponsorizari deja acordate`. Show the recommended maximum amount.

Company data (step 3): denumire, CUI, nr. registrul comertului, sediu, reprezentant legal,
calitate (e.g. Administrator), banca, IBAN firma, suma. Supporter side only; association side
comes from `data/association.yaml`.

Generate (step 6): sponsorship contract PDF (supporter side filled, supporter signature
embedded, association block blank for countersignature); if sub-path (b), also the pre-filled
Form 177. Instructions per 7.4 and D3 (print + wet-sign the contract for ANAF; submit Form 177
via the company SPV by the `form177_next` deadline in `data/fiscal.yaml`). Send a copy to the
association.

### 8.2 Individuals -- Form 230 (the "3.5%" path)

Eligibility note (step 1): for employees and assimilated income; PFA / independent activity use
Declaratia Unica D212, not Form 230. Show the next deadline from `data/fiscal.yaml`.

Personal data (step 3) -- **collect only what the PDF can hold.** Appendix A shows the 230 has
just 5 base text fields (plus 2 mirrors), so the data-entry step collects EXACTLY the items the
T3 fill-test maps to a destination field (expected: nume, prenume, CNP, year/period), plus the
option checkboxes (2-year option) and the explicit consent checkbox for sending a copy. Any
form box with no fillable field (e.g. parts of the address grid, if the fill-test finds none)
is NOT collected in the UI -- the supporter completes those by hand after printing, and the
done-step instructions say exactly which ones. No email is collected (nothing in this
architecture sends confirmations). The 2-year option checkbox is set here (step 3); the GDPR
consent checkbox lives in step 5 (Section 6), immediately before the send-copy action it
authorizes.

Generate (step 6): the pre-filled original Form 230 PDF (association data from
`data/association.yaml`, supporter data from form state, base set plus the 2 mirror fields per
7.3.4; NO signature -- the supporter signs by hand after printing, per D3). Instructions per 7.4
(paper route primary), including the honest note that ANAF transfers the 3.5% within about 90
days of a valid submission. Send a copy to the association (optional).

CNP handling: stays in the browser. It only leaves the device if the supporter attaches the PDF
to their own email. We never store or transmit it ourselves.

### 8.3 Direct donation (universal)

No form. The landing page shows the association name, CIF, IBAN, BIC, and a short note that the
donation is not tax-deductible (the deductible routes are the two above). Available to everyone,
including non-Romanian supporters, in all languages.

---

## 9. Data Sources

### 9.1 `data/association.yaml` (public identifiers, single source)

Holds only public registry data, no representative name:

```yaml
name: "Asociatia OncoGuide"
legal_form: "Persoana juridica fara scop patrimonial (OG nr. 26/2000)"
cif: "54791907"
registry_no: "72 / 22.05.2026"
registry_court: "Judecatoria Sectorului 2 Bucuresti"
address: "Str. Fecioarei nr. 15, Corp C1, et. 1, ap. 1, Sector 2, Bucuresti, 020103"
iban: "RO91 RNCB 0280 1861 0767 0001"
bank: "Banca Comerciala Romana (BCR)"
bic: "RNCBROBU"
email: "nog.opt.3o@icloud.com"   # anonymous relay, already public in about.md; mailto target
registru163_no: ""   # filled after Form 163 approval; gates the tax paths (Section 10)
```

Note on the pre-commit email scan: the existing hook flags email addresses in staged files.
The relay address above is the one PERMITTED address (it is already public in `about.md` in all
6 languages); if the hook flags this YAML, extend the hook's allowlist for exactly this address
rather than weakening the scan.

The representative name is intentionally absent. The contract template carries a blank
representative field filled offline.

### 9.2 `data/fiscal.yaml` (deadlines, ceilings, flags)

```yaml
flags:
  registru163_active: true    # ON since 2026-06-12 (ANAF approval 11.06.2026; see Section 10)
deadlines:
  form230_next: "2027-05-25"  # next 3.5% filing window (2026 income)
  form177_next: "2026-06-25"  # NOW REACHABLE post-registration: F177 for 2025 profit tax
ceilings:
  sponsorship_turnover_pct: 0.0075   # 0.75% of turnover
  sponsorship_profit_tax_pct: 0.20   # 20% of profit tax
  individual_redirect_pct: 0.035     # 3.5%
```

---

## 10. Feature Flag and Fiscal Calendar Gating

> **STATUS UPDATE (2026-06-12): registration DONE.** ANAF approved the Registrul entitatilor
> nonprofit application on **11.06.2026** (decision on request INTERNT-1145502724-2026).
> `registru163_active` was flipped to `true` and `association.yaml registru163_no` filled on
> 2026-06-12. Consequence: the F177 window for 2025 profit tax (deadline **25.06.2026**) became
> reachable -- `fiscal.yaml form177_next` was moved to 2026-06-25. The gating mechanics below
> remain as designed (and as the kill switch if the registration ever lapses).

The deductible mechanisms require OncoGuide in the ANAF Registrul entitatilor nonprofit
(Form 163). At design time this was not yet done; gating kept the build honest.

Gating logic:

- `fiscal.yaml flags.registru163_active: false` -> the `/donate/firme/` and
  `/donate/persoane-fizice/` generators render in an explanatory "available after registration"
  state (the calculator and education are visible; the generate/sign actions are disabled with
  a clear note). The landing page shows only the direct-donation path as active.
- When Form 163 is approved: set `registru163_active: true`, fill
  `association.yaml registru163_no`, and the generators activate. No code change required.
- Deadline awareness: the generator pages read `deadlines` and show whether the current filing
  window is open, closed, or upcoming, with the next date. The 2025-income 230 window
  (25.05.2026) has already passed; the next is 2026 income, 25.05.2027. The F177 window for 2025
  profit tax (25.06.2026) is unreachable for a not-yet-registered NGO, so `form177_next` is set
  to 2027-06-25.
- **Coupled gating:** while `registru163_active` is false, the deadline banner must NOT present
  an actionable filing route. It shows "indisponibil in acest ciclu pana la inscrierea in
  Registrul entitatilor nonprofit" (window closed this cycle until Form 163 registration),
  never a live countdown. A live deadline appears only once the flag is true.

This makes the page deployable and useful today (direct donation), with the tax flows switching
on by config when the association is ready.

---

## 11. Source of Truth and Archival

- **Index:** `.private/finantare/registru-donatii.md` (already exists) records promised vs
  received amounts.
- **Documents:** signed copies that supporters email arrive in the association inbox; they are
  saved to `.private/finantare/arhiva/{year}/` locally AND mirrored to a private Google Drive
  folder (off-site backup, survives a lost laptop). All gitignored.
- **Optional no-PII notification (opt-in, never automatic):** the ping fires ONLY as part of
  the user-initiated "send us a copy" click, never automatically on generate -- an automatic
  POST would still transmit the supporter's IP to a US processor, against Principle 4. Payload:
  a minimal web3forms message with NO personal data -- only
  `{type: sponsorship|form230|donation, locale, timestamp}` (no name, no amount, to avoid weak
  re-identification when cross-referenced with an inbound email) -- so the association knows to
  expect a copy. The supporter is told this ping contains no personal data. The actual document
  never transits web3forms. web3forms deletes server logs periodically (about every 2 months per
  its FAQ) on US-based servers; acceptable here because the ping holds no personal data. The
  privacy page discloses this US connection.

Reuse the existing `web3formsKey` for the notification; it routes to the same association
relay address already used by the contact form.

---

## 12. Privacy, GDPR, and Anonymity

- **Data minimization.** We collect nothing server-side. Supporter PII (including CNP) lives in
  the browser and leaves only if the supporter emails their own copy.
- **Privacy statement page (deliverable, all 6 languages).** A `donate-privacy` page (all 6
  languages, Section 5.1) states: what data the forms process, that processing happens in the
  browser, what the optional copy-by-email and no-PII ping involve (including that the ping
  reaches web3forms' US-based servers, which may store the submission up to about 30 days with
  server logs purged about every 2 months, per its documentation),
  the association as recipient/controller for copies it receives, retention in the private
  archive, and contact for data requests. The GDPR consent checkbox in BOTH flows links to it.
- **Consent (both flows).** Before any "send a copy" action, BOTH generators show a short,
  plain GDPR notice with an explicit consent checkbox naming the association as recipient and
  the purpose -- the Form 230 flow because the copy carries the supporter's CNP, and the company
  flow because the contract carries the company representative's personal name.
  The notice links to the privacy page using a real, language-aware Hugo idiom -- NOT `ref` with
  a translationKey (Hugo `ref`/`relref` resolve by file path, not translationKey). Each language
  has `content/{lang}/donate-privacy.md`, and `site` is language-scoped, so the generator
  template resolves the current language's page with
  `{{ with site.GetPage "/donate-privacy" }}{{ .RelPermalink }}{{ end }}` (works even if the URL
  is localized via `slug:`, because `GetPage` resolves by the logical filename path). Never
  hard-code a slug.
- **No tracking.** No analytics, no third-party embeds; consistent with `hugo.yaml privacy`.
- **Anonymity (D4).** The representative's personal name is never in page content, JS, data
  files, or git. It appears only in the generated contract PDF, added offline at
  countersignature. **Template + source audit (required, runnable):** ship
  `scripts/audit-contract-template.mjs` (Node + pdf-lib). The representative name it checks
  against is read from ONE canonical, gitignored source: the `REPRESENTATIVE_NAME` environment
  variable, whose value is kept in a gitignored file under `.private/` (e.g.
  `.private/finantare/.audit-name`) and exported by the pre-commit hook. NEVER a literal in the
  script. The audit FAILS (non-zero exit) if: (a) any text field in
  `static/donate/templates/sponsorship-contract-*.pdf` has a non-empty default value; (b) the
  template contains `/JS` or `/JavaScript`; (c) the representative name appears in any field
  name, value, or XMP/metadata of the template; or (d) the name appears anywhere in the tracked
  source tree -- grep over the FULL `git ls-files` output (not a directory subset), which also
  covers `decisions/log.yaml`, `hugo.yaml`, `scripts/`, and root files; the binary ANAF
  templates may be excluded since (a)-(c) cover PDFs via the API. Edge cases
  (defined, not guessed): if `REPRESENTATIVE_NAME` is unset, the audit HARD-FAILS with a message
  pointing to `.private/finantare/.audit-name` (never silently skips); if the contract template
  does not exist yet (T1-T5 commits), checks (a)-(c) are skipped with a warning and check (d)
  still runs; the script uses the npm `pdf-lib` package via a `package.json` devDependency (the
  vendored UMD stays browser-only). Wire it into `scripts/hooks/pre-commit`.
  Assert via the pdf-lib field/metadata API, not by grepping serialized PDF bytes (7.3.5
  caveat). Public association identifiers (name,
  CIF, IBAN, registered office) may appear because they are public registry data and legally
  required on the documents; the registered-office street address appears in generated documents
  where required and is kept off the visible landing copy where it is not needed.

---

## 13. File and Directory Layout, Dependencies

```
content/en/donate/_index.md            # landing (and ro, it, fr, de, es)
content/ro/donate/firme.md             # company generator (RO, full)
content/ro/donate/persoane-fizice.md   # Form 230 generator (RO, full)
content/{en,it,fr,de,es}/donate/firme.md            # localized stubs (5.1)
content/{en,it,fr,de,es}/donate/persoane-fizice.md  # localized stubs (5.1)
content/{en,ro,it,fr,de,es}/donate-privacy.md       # privacy statement, all 6 langs (localized slug)

layouts/donate-landing/list.html       # landing layout (donate/_index.md is a section -> list.html)
layouts/donate-generator/single.html   # generator layout; lazy-loads the JS bundle

static/donate/templates/form-230-original.pdf          # blank ANAF original (App. A)
static/donate/templates/form-177-original.pdf          # blank ANAF original (App. A)
static/donate/templates/sponsorship-contract-ro.pdf    # our AcroForm template (RO; App. B)
scripts/audit-contract-template.mjs                    # anonymity audit, wired into pre-commit (S12)
static/donate/js/pdf-lib.min.js        # vendored, pinned (version + SHA-256)
static/donate/js/signature.js          # canvas signature helper
static/donate/js/field-maps.js         # ANAF field name -> meaning (names only; no PII)
static/donate/js/i18n.js               # JS UI strings per locale
static/donate/js/donate-companies.js   # company flow + fill 177 + contract
static/donate/js/donate-individuals.js # individual flow + fill 230
static/donate/js/donate-common.js      # step machine, validation, download, mailto, ping

data/association.yaml                   # public association identifiers (single source)
data/fiscal.yaml                        # deadlines, ceilings, feature flags
package.json                            # npm pdf-lib devDependency for Node scripts (audit, fill-test)

assets/css/extended/donate.css          # styles (dark-mode aware, WCAG AA)
i18n/{en,ro,it,fr,de,es}.yaml           # add donate UI strings (existing files)

hugo.yaml                               # add donate menu (6 langs)
CLAUDE.md                               # update File Structure + dependency map + content types
decisions/log.yaml                      # append decision entries
```

**Gitignore (build-breaker if missed).** `.gitignore` line 92 is `data/*` with a single
exception `!data/scanners.yaml`, so `data/association.yaml` and `data/fiscal.yaml` are ignored
and would never reach the GitHub Pages CI build (the IBAN, flags, ceilings, and deadlines would
render blank). T1 MUST add `!data/association.yaml` and `!data/fiscal.yaml` to `.gitignore` and
assert both files are tracked (`git ls-files data/`). These two files hold only public
association data and config -- no PII -- so committing them is safe and required.

Dependencies to vendor (no CDN): pdf-lib (pin exact version, store SHA-256). If a signature-pad
library is used instead of a hand-rolled canvas, vendor it too (MIT) and pin it.

`CLAUDE.md` dependency-map additions (must be kept in sync in the same commit):
- modify `hugo.yaml` menus -> update `CLAUDE.md` File Structure (already required)
- modify `data/association.yaml` or `data/fiscal.yaml` -> review `field-maps.js` and the flows
- replace an ANAF template (new ANAF revision) -> re-run the fill-test (7.3) and update App. A

---

## 14. Implementation Plan (Task Breakdown)

Each task is independently reviewable, has explicit acceptance criteria, and is ordered so a
context-free agent can execute top to bottom. Each task must pass Gemini review (> 9.1/10)
before it is considered ready; record the score in the task. Implementation of each task is
reviewed by a fresh Fable agent (> 9.3/10).

> The architecture passed its gate (9.4, Section 0). Each task below is fully specified:
> files, content requirements, validation rules, test steps, and acceptance criteria (AC).
> A task references architecture sections by number instead of repeating them; the referenced
> section is part of the task spec. Execute strictly in order T1 -> T7; each task leaves the
> site buildable and deployable. Run `hugo --gc --minify` after every task; a broken build
> fails the task. Per Section 18, each task needs Gemini > 9.1 before implementation, and each
> implementation needs fresh-Fable > 9.3.

### T1. Data + config foundation
Gemini score: 9.5 (PASS, 2026-06-11; noted defects fixed in-place) | Implementation Fable score: 9.5 (PASS, 2026-06-11, round 2 -- round 1 was 8.4 with 4 blocking fixes applied)

**Create:**
1. `data/association.yaml` -- exactly the Section 9.1 block (including `email:` and empty
   `registru163_no`). No representative name.
2. `data/fiscal.yaml` -- this complete, final content (Section 9.2 merged with eligibility):
   ```yaml
   flags:
     registru163_active: false   # master switch for the tax-benefit paths
     eligibility:
       form177_profit_tax: true
       form177_micro: false   # presumed NO per OUG 115/2023 (8.1) -- ACCOUNTANT: confirm
       form177_imca: false    # verified NO (Art. 42 not applicable at IMCA level)
   # ACCOUNTANT QUESTIONS (T6 go-live): (1) micro + F177 post-OUG 115/2023?
   # (2) does 25 June hold for fiscal 2026, or revert to 25 March 2027 (OUG 153/2020 lapse)?
   deadlines:
     form230_next: "2027-05-25"  # next 3.5% window (2026 income)
     form177_next: "2027-06-25"  # next F177 window; 2026-06-25 unreachable pre-registration
   ceilings:
     sponsorship_turnover_pct: 0.0075   # 0.75% of turnover
     sponsorship_profit_tax_pct: 0.20   # 20% of profit tax
     individual_redirect_pct: 0.035     # 3.5%
   ```
3. `package.json` -- `private: true`, devDependency `pdf-lib` (pin the exact version chosen in
   T3; placeholder `^1.17.1` until then), no other deps, scripts: `"audit": "node
   scripts/audit-contract-template.mjs"`.
4. `scripts/audit-contract-template.mjs` -- per Section 12: checks (a)-(d), name from
   `REPRESENTATIVE_NAME` env var (unset = hard fail, message points to
   `.private/finantare/.audit-name`), template-missing = skip (a)-(c) with warning, (d) greps
   full `git ls-files` output (skip binary `static/donate/templates/*.pdf`).
5. `.private/finantare/.audit-name` -- one line, the representative's name (NOT committed;
   `.private/` is already gitignored).

**Modify:**
6. `.gitignore` -- after line `!data/scanners.yaml`, add `!data/association.yaml` and
   `!data/fiscal.yaml`.
7. `scripts/hooks/pre-commit` -- append a block that (i) exports
   `REPRESENTATIVE_NAME="$(cat .private/finantare/.audit-name 2>/dev/null)"` and (ii) runs
   `node scripts/audit-contract-template.mjs` if `node` is available, failing the commit on
   non-zero exit; degrade with a warning (not a hard fail) if node is missing.
8. `hugo.yaml` -- add the `donate` menu item to all 6 language menus, weight 28, names per 5.2.
9. `CLAUDE.md` -- File Structure: add `DONATIONS.md`, `data/association.yaml`, `data/fiscal.yaml`,
   `package.json`, `static/donate/`, `scripts/audit-contract-template.mjs`; Dependency Map: add
   the three Section 13 rows; Key Files: add `DONATIONS.md` pointer.

**Validation rules:** YAML parses (`python3 -c "import yaml; yaml.safe_load(...)"`); no value in
either data file matches the representative name; `email:` is the public relay only.

**Test steps:** `hugo --gc --minify` clean; `git ls-files data/` lists scanners + the 2 new
files; `git check-ignore data/association.yaml` exits non-zero; menu renders in all 6 langs
(grep the donate URL in `public/{lang}/index.html`); `REPRESENTATIVE_NAME= node
scripts/audit-contract-template.mjs` fails; with the env var set it passes (template-missing
warning only); staged-file commit dry-run passes the hook.

**AC:** all test steps green; no PII anywhere in the diff; site deploys unchanged visually
(menu item appears but `/donate/` 404s until T2 -- acceptable on the feature branch, NOT
acceptable to merge to main until T2 lands; do T1+T2 in one PR).
### T2. Landing + privacy + stubs (same PR as T1)
Gemini score: 9.2 (PASS, 2026-06-11; noted defects fixed in-place) | Implementation Fable score: 9.5 (PASS, 2026-06-11, reviewed together with T1)

**Create:**
1. `content/{en,ro,it,fr,de,es}/donate/_index.md` -- front matter: `title` (localized),
   `translationKey: donate`, `type: donate-landing`, `description` (140-160 chars, keyword
   "doneaza"/"donate" per language); body: warm patient-author intro, the 3 paths (8.1, 8.2,
   8.3) explained in plain language, the direct-donation block (association name, CIF, IBAN,
   BIC from the data file -- rendered by the layout, not hard-coded in markdown), a
   `callout type="important"` that tax-benefit flows await Form 163 registration (10), links to
   the two generator pages and the privacy page, an `action-box` with concrete steps, and the
   `disclaimer` shortcode last. Non-RO versions lead with direct donation and state the tax
   mechanisms are for Romanian taxpayers (5.1).
2. `content/ro/donate/firme.md` + `content/ro/donate/persoane-fizice.md` -- front matter only
   for now (`type: donate-generator`, translationKeys per 5.1, `draft: false`); body =
   explanatory content per 5.3 with a visible "in pregatire" (in preparation) callout; the
   generator UI activates in T5/T6. This keeps T2 deployable without dead UI.
3. The 10 localized stubs `content/{en,it,fr,de,es}/donate/{firme,persoane-fizice}.md` --
   `layout: page`, same translationKeys, optional localized `slug:`; 5-10 lines per 5.1
   (mechanism is for Romanian taxpayers; link to the RO page via `relref` by logical path and
   to direct donation).
4. `content/{en,ro,it,fr,de,es}/donate-privacy.md` -- `layout: page`,
   `translationKey: donate-privacy`, optional localized `slug:`; content per Section 12
   (browser-only processing, optional copy-by-email, opt-in no-PII ping incl. web3forms US
   servers + ~30-day submission / ~2-month log retention, association as controller for
   received copies, archive retention, data-request contact = association email).
5. `layouts/donate-landing/list.html` -- extends PaperMod baseof; renders the page content,
   then the direct-donation data block from `site.Data.association` (name, CIF, IBAN with a
   copy-to-clipboard button, BIC, bank), then links to the generators. No JS beyond the
   clipboard one-liner.
6. `assets/css/extended/donate.css` -- landing + future generator styles: cards for the 3
   paths, the IBAN block, step indicators, form fields, signature canvas frame; CSS variables
   from PaperMod theme (`var(--primary)` etc.) for dark-mode compatibility; WCAG AA contrast;
   no fixed pixel fonts below 16px equivalent.

**Validation rules:** every page ends with the disclaimer shortcode in its PAIRED form
(`{{</* disclaimer */>}}{{</* /disclaimer */>}}` -- the paired form is a CLAUDE.md requirement;
a reviewer suggesting the unpaired form is wrong); translationKey
identical across the 6 versions of each page; no email address other than the public relay; no
emojis/em-dashes/typographic quotes; internal links via `relref`/`GetPage` only.

**Test steps:** `hugo --gc --minify` clean with zero `relref` errors; `/{lang}/donate/` renders
in all 6 langs; language switcher on every donate page resolves (check rendered HTML for all 6
alternates); both RO generator URLs and all 10 stubs render; privacy page linked from landing;
lighthouse or axe pass on `/ro/donate/` for contrast; dark-mode visual check.

**AC:** all test steps green; landing shows IBAN from `data/association.yaml` (change the YAML
locally -> rebuilt page changes); SEO checklist (CLAUDE.md) satisfied for the landing page in
all 6 languages; merged to main together with T1; live site shows the Doneaza menu working.
### T3. ANAF field map (no user-visible change; separate PR allowed)
Gemini score: 9.9 (PASS, 2026-06-11; noted defects fixed in-place) | Implementation Fable score: --

**Create:**
1. `static/donate/js/pdf-lib.min.js` -- vendored UMD build of the npm-pinned version; record
   version + SHA-256 in a comment at the top of `field-maps.js` AND in Section 13. Update
   `package.json` to the same exact version (remove the `^`).
2. `static/donate/templates/form-230-original.pdf` + `form-177-original.pdf` -- downloaded from
   the Section 7.3.1 URLs, byte-identical (record SHA-256 alongside).
3. `scripts/fill-test.mjs` -- Node script implementing 7.3.2: enumerate fields, set short
   indexed markers (respecting maxLength), set NeedAppearances per 7.3.5, save to
   `/tmp/filled-{form}.pdf`, then reload-assert the flag and print the field inventory with
   types and maxLengths. Also classifies every `PDFButton` (7.3.6) and fails if any has an
   on-state (i.e., is actually settable).
4. `static/donate/js/field-maps.js` -- the deliverable: for each form, an object mapping
   SEMANTIC keys to field names, e.g. `f230: { nume: '...TextField4[0]', prenume:
   '...TextField4[1]', cnp: '...TextField2[0]', cnpMirror: '1....TextField2[0]', anOption:
   '...TextField13[0]', anOptionMirror: '1....TextField13[0]', twoYearCheckbox: '...', ... }`,
   `f177: { anul, cifAttr, cif, denumire, adresa..., beneficiaryRows[], ... }`, plus a
   `manualAfterPrint` list per form naming the visible boxes with NO fillable field (8.2).
   Derived by opening the filled test PDFs and reading which box each marker landed in,
   cross-checked against the flattened `.private/finantare/formular-*-precompletat.pdf` copies.
   Field names only -- no values, no PII.

**Validation rules:** the semantic map covers every item the flows need (8.1: year, company
identifiers, beneficiary row for OncoGuide with amount; 8.2: nume, prenume, CNP + mirror,
year/period + mirror, 2-year checkbox); diacritics confirmed in 3 viewers per 7.3.5; zero
layout change confirmed by visual diff of filled vs blank.

**Test steps:** `node scripts/fill-test.mjs` exits 0 and prints the inventory matching
Appendix A counts; open both filled PDFs in Adobe Reader, Chrome, macOS Preview -- all markers
visible, diacritics correct (test string per 7.3.5), no box moved or restyled; SHA-256 of the
two templates matches the recorded values; `hugo` build still clean.

**AC:** `field-maps.js` complete per validation rules with the `manualAfterPrint` lists;
fill-test reproducible by re-running the script; Appendix A updated if any provisional meaning
changed; no pushbutton set anywhere.
### T4. Document engine + generator shell (no user-visible change until T5)
Gemini score: 10 (PASS on re-review after revision, 2026-06-11) | Implementation: DONE 2026-06-11 (commit pending push) -- engine verified end-to-end in Node (donate-common.js fillAnafForm fills 230 + 177 correctly incl. OncoGuide overlay + donor CNP/year + sustinere checkbox; validCNP/validCUI/validIBAN correct; NeedAppearances reload-asserted); build clean; generator page renders gate banner + hidden container + data bridge. Implements D6 overlay (page.drawText) in addition to setText. Fable implementation review >9.3 PENDING.

**Create:**
1. `layouts/donate-generator/single.html` -- renders the markdown body, then: the deadline/gate
   banner region (Section 10 logic from `site.Data.fiscal`: if `registru163_active` is false,
   "indisponibil in acest ciclu..." text and the generator sections render with actions
   disabled), the step `<section>` skeleton (Section 6), the data-to-JS bridge
   (`window.oncoDonate` per 5.1), and explicit dynamic script loading (NOT `defer` attributes):
   the layout ships only a tiny inline bootstrap that, on the first user interaction with the
   step-1 section (`click`/`focusin`, once), injects a `<script src=".../donate-common.js">`
   tag (plus the flow file and i18n.js); `pdf-lib.min.js` is injected the same way only when
   the user enters the generate step. Each injection sets a guard so scripts load exactly once.
2. `static/donate/js/donate-common.js` -- vanilla JS, no framework: step machine (show/hide
   sections, focus management, ARIA live region per Section 6), validators (required, CNP =
   13 digits + checksum, CUI format, IBAN mod-97, maxLength from field-maps), `downloadPdf
   (bytes, filename)` via Blob/objectURL (7.5), `buildMailto(subject, shortBody)` under 300
   chars (7.5), `sendPing(type, locale)` -- POST to web3forms with ONLY
   `{access_key, subject, type, locale, timestamp}` fired exclusively inside the send-copy
   click handler (11), and the GDPR consent gate (12: send-copy controls stay disabled until
   the consent checkbox is checked).
3. `static/donate/js/i18n.js` -- UI strings keyed per locale; RO complete now, other locales
   fall back to RO until the generators are localized (8.x flows are RO-first per 5.1).
4. `static/donate/js/signature.js` -- canvas draw capture (pointer events, works on touch),
   clear/undo, typed-name fallback rendered to canvas, `toPngDataUrl()`.

**Validation rules:** no PII in any committed file; no network call anywhere except `sendPing`;
all strings via i18n.js (no hard-coded UI text in logic files); CNP checksum implemented per
the standard algorithm (weights 279146358279, remainder 10 -> 1).

**Test steps:** a throwaway local HTML harness (not committed, or committed under
`scripts/dev/` and excluded from the site) that: loads the engine, fills the T3 sample values
into `form-230-original.pdf` in-browser, downloads it, and `setImage`-embeds a signature PNG
into a THROWAWAY test AcroForm (NOT the contract -- that is authored in T6); verify the ping
fires only on send-copy click (network tab), never on generate; keyboard-only walk through the
step machine; screen-reader labels announced.

**AC:** engine fills a 230 in-browser identical to the T3 Node result (same field values, flag
present on reload-assert); signature capture works with mouse and touch; consent gate blocks
send-copy until checked; build clean; nothing user-visible changed on the live site.
### T5. Form 230 generator (user-visible; gated)
Gemini score: 10 (PASS, 2026-06-11; noted defects fixed in-place) | Implementation Fable score: --

**Create:** `static/donate/js/donate-individuals.js` -- the 8.2 flow on top of donate-common:
step 1 eligibility + deadline from `fiscal.yaml` (D212 note for PFA); step 3 collects ONLY the
`field-maps.js` f230 semantic keys (8.2) + the 2-year checkbox; step 4 review; step 5 consent
checkboxes only (NO signature, D3); step 6 fills base + the 2 mirror fields (7.3.4), downloads
`Formular-230-OncoGuide-{nameSlug}.pdf`, shows the 7.4 routes (paper primary, ~90-day payout
note, the `manualAfterPrint` hand-completion list) and the consent-gated send-copy + ping
action.

**Modify:** `content/ro/donate/persoane-fizice.md` -- replace the "in pregatire" callout with
the full 5.3 content (mechanism, eligibility, deadline, what happens after); the page now
drives the live UI.

**Validation rules:** with `registru163_active: false` the generate/sign actions are disabled
and the banner explains why (10); CNP never appears in any URL, localStorage, or network
request; the generated PDF passes the T3 reload-assert and visual checks.

**Test steps:** end-to-end manual run on localhost with the flag flipped true locally: enter
test data (fictional CNP that passes checksum), generate, open in 3 viewers, verify values +
diacritics + zero layout change + NO signature on the PDF; verify mirror fields filled; flip
flag false -> actions disabled; axe/keyboard pass on the flow; `hugo` clean.

**AC:** correct pre-filled (base + mirror) 230 in original layout, NO signature on the ANAF
PDF (D3); gated by `registru163_active`; honest 7.4 instructions shown; consent gate enforced
before send-copy.
### T6. Company generator + contract template (user-visible; gated)
Gemini score: 9.8 (PASS, 2026-06-11; noted defects fixed in-place) | Implementation Fable score: --

**Create:**
1. `static/donate/templates/sponsorship-contract-ro.pdf` -- authored to the Appendix B field
   schema, fully programmatically: `scripts/make-contract-template.mjs` (committed; the
   template is reproducible by re-running it) uses Node + pdf-lib to build the PDF from
   scratch -- draws the contract text (clauses transcribed into a gitignored
   `.private/finantare/contract-text-ro.txt` from the existing
   `contract-sponsorizare-precompletat.pdf`, MINUS any representative name, with Article 5
   lit. a / lit. b as two checkbox options) with an embedded Romanian-capable font, and adds
   the named AcroForm fields from Appendix B at their positions. No GUI tool involved. The
   committed PDF contains the generic contract text (public legal boilerplate, association
   public data only -- safe in git); the source text file stays in `.private/` only as
   provenance. The audit script (T1) must pass on the result.
2. `static/donate/js/donate-companies.js` -- the 8.1 flow: step 1 regime question + sub-path
   choice (177 sub-path shown only for regimes eligible in `fiscal.yaml`); step 2 calculator
   (8.1 ceiling math, regime-conditional labels); step 3 company data (Appendix B sponsor_*
   keys); step 4 review; step 5 signature canvas -> `setImage` into `sponsor_semnatura` +
   consent; step 6 fill contract (+ Form 177 via field-maps when sub-path (b)), download(s),
   7.4 + D3 instructions (print + wet-sign for ANAF), consent-gated send-copy + ping.

**Modify:** `content/ro/donate/firme.md` -- full 5.3 content replacing the "in pregatire"
callout.

**Accountant checklist for go-live** (record answers as comments in `data/fiscal.yaml`):
(1) may microenterprises use Form 177 at all post-OUG 115/2023? (2) does the 25 June F177
deadline hold for fiscal 2026, or does it revert to 25 March 2027 when the OUG 153/2020 D101
extension lapses?

**Validation rules:** ceiling math exact per 8.1 (`min(0.0075 * CA, 0.20 * impozit)` minus
already-granted, floored at 0, RON formatting); no regime rule hard-coded in JS (all from
`fiscal.yaml`); contract association block fields stay empty; no flatten anywhere.

**Test steps:** unit-check the calculator against 3 hand-computed cases (incl. zero and
negative-available); end-to-end on localhost (flag true): both sub-paths, open contract in 3
viewers (signature visible, association block blank, no rep name anywhere -- check XMP too),
177 values land per field map; `REPRESENTATIVE_NAME=... node scripts/audit-contract-template.mjs`
passes including (a)-(c) now that the template exists; flag false -> disabled.

**AC:** correct ceiling math; Form 177 eligibility read from `data/fiscal.yaml` (IMCA blocked;
microenterprise rule accountant-confirmed before go-live); contract with blank association
block; audit passes; gated by flag.

### T7. Wire-up + final pass
Gemini score: 10 (PASS on re-review after revision, 2026-06-11) | Implementation Fable score: --

**Do:** add any missing UI strings to `i18n/{en,ro,it,fr,de,es}.yaml` (page-level strings; the
flow strings live in i18n.js); append the implementation decision entry to
`decisions/log.yaml`; sweep every Section 15 acceptance criterion, verify each against the
built site, and check off in this file every box whose evidence the agent can produce itself
(the review-score bookkeeping in Section 0 is NOT this task's job -- the human/orchestrator
records reviewer scores after each review, per Section 18); verify CLAUDE.md dependency-map
rows were honored in every T1-T6 commit.

**Test steps:** full `hugo --gc --minify` clean; manual end-to-end of both generators and the
landing in RO + EN; language switcher walk across all donate pages in all 6 langs; audit
script green; `git log --stat` review confirms no `.private/` path and no PII ever staged.

**AC:** every Section 15 box verified with reproducible evidence (command output or rendered
page) and checked off; both flows work end-to-end; site live and deployable with
`registru163_active: false`.

---

## 15. Acceptance Criteria (maps to the original request)

- [ ] Donate / Doneaza page in the main menu, like Contact, in all 6 languages.
- [ ] Two tax options present: firme (20%) and persoane fizice (3.5%), plus universal direct
      donation.
- [ ] Content and flow mirror daruiesteviata `/sponsorizeaza` and `/formular-230`, adapted to a
      static site (calculator, multi-step, generate in browser; in-browser signing on the
      sponsorship contract only -- never on ANAF forms).
- [ ] Sponsorship contract generated and electronically signed in the browser (with the D3
      print/wet-sign guidance for ANAF).
- [ ] ANAF forms kept in original ANAF layout; only values pre-filled; no field/format changes;
      never flattened.
- [ ] History preserved: archive flow + `registru-donatii.md` + private Drive; no PII in git.
- [ ] Honest submission routes (7.4); tax paths gated behind the Form 163 flag.
- [ ] Representative name only in the generated contract PDF (D4); template anonymity audit
      passes (no name in fields/JS/metadata).
- [ ] Form 177 eligibility is config-driven (IMCA blocked; microenterprise rule accountant-
      confirmed); no contested fiscal rule hard-coded in JS.
- [ ] `data/association.yaml` and `data/fiscal.yaml` are git-tracked (gitignore exceptions added).
- [ ] No broken internal links for non-Romanian visitors (localized stubs present); language
      switcher resolves on every donate page.
- [ ] Privacy statement page exists in all 6 languages and is linked from the consent step.
- [ ] All `/Btn` pushbutton widgets classified as non-data; needed options map to checkboxes.
- [ ] This document is the saved architecture in the repo root.

---

## 16. Non-Goals (v1) and Future Options

Non-goals now: server-side storage, accounts, online card payments, automatic / centralized
ANAF submission (the daruiesteviata "we submit your 230 for you" model).

Future option B (only if volume justifies it and after Form 163): a serverless backend
(e.g. Cloudflare Workers + private storage) that holds signed forms and submits a centralized
Form 230 borderou. This makes the association a personal-data controller (including CNP) with
full GDPR and security obligations; defer until clearly warranted.

Deferred XFA fallback (not needed today): the current Forms 177 and 230 are AcroForms, so pdf-lib
fills them directly. If a future ANAF revision ships an XFA "smart PDF" that pdf-lib cannot fill,
the fallback is to draw values as a text overlay at mapped coordinates on the static page and
not rely on form fields. Re-run the fill-test (7.3) on any ANAF template change to detect this.

---

## 17. Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Filled AcroForm appears blank in a viewer that ignores field values | Set `NeedAppearances=true`; fill-test in a mainstream viewer; for any non-rendering field, embed a Romanian-capable font via pdf-lib. |
| Romanian diacritics do not render in a field | Rely on the form's embedded fonts via NeedAppearances; fall back to pdf-lib embedded font for that field (7.3.5). |
| web3forms cannot attach files on the free tier | By design we never send the PDF through web3forms; the ping is no-PII; the document goes via the supporter's own email. |
| Representative name leaks into git via the contract template | Association block is a blank field; name added offline; T6 anonymity audit (fields + JS + XMP) before commit. |
| Tax paths go live before Form 163 | `registru163_active` defaults false; flows gated and explained. |
| CNP exposure | Stays in browser; never stored or transmitted by us; explicit consent before any copy is sent. |
| Wrong tax regime offered a Form 177 it cannot use | Eligibility is config-driven from `data/fiscal.yaml` (8.1); the IMCA case is blocked (verified); the disputed microenterprise rule is confirmed with the accountant before go-live, and flows stay gated until then. |
| Future ANAF revision ships an XFA form pdf-lib cannot fill | Deferred coordinate-overlay fallback (Section 16); re-run fill-test on any template change. |
| Acceptance test byte-greps for `NeedAppearances` and false-fails | Assert via pdf-lib reload API, never byte-grep (7.3.5, App. A). |
| Pushbutton widget mistaken for a data option | Fill-test classifies all `/Btn` as non-data; only checkboxes are set (7.3.6). |
| Non-RO visitor hits an empty generator route | Localized stubs for all 5 non-RO languages (5.1). |

---

## 18. Review and Acceptance Process (governance)

1. **Architecture (S1-S13 + Appendices A and B).** A fresh Fable agent reviews against a rubric
   of: correctness, feasibility on a static host, privacy/GDPR, anonymity, ANAF fidelity, i18n,
   simplicity and scalability, and completeness/non-ambiguity. Must score > 9.2/10. Iterate
   until it passes. Record score and date in Section 0.
2. **Task plan (S14).** Each fully expanded task is reviewed by the Gemini CLI against:
   clarity, non-ambiguity, correct acceptance criteria, and implementability by a context-free
   agent. Each must score > 9.1/10.
3. **Implementation.** Claude implements each task; a fresh Fable agent reviews the diff against
   the task's acceptance criteria and this architecture. Must score > 9.3/10.

Record every score in Section 0 and in the relevant task. Nothing is "done" until its gate is
met.

---

## Appendix A. Verified ANAF Form Facts and Field Inventory

Verified on 2026-06-11 by downloading the blank originals from anaf.ro and inspecting them with
pdf-lib. Re-run this inspection if ANAF publishes a new revision.

> **VERIFIED CORRECTION (T3, 2026-06-11) -- supersedes the provisional per-form tables further
> below.** The fill-test (`scripts/fill-test.mjs`) + per-checkbox test + `pdftotext` against the
> `.private` precompletate established the REAL field meanings. Several earlier provisional
> guesses were wrong (e.g. 230 `TextField4[*]` are the tax-office "Nr. inregistrare/Data" boxes,
> NOT the donor name; 177 `TextField3[0..9]` are the COMPANY's own address line, NOT a beneficiary
> table). The authoritative map is `static/donate/js/field-maps.js`. Summary:
>
> **Form 230 (OPANAF 103/2025) -- 7 text fields, 8 checkboxes, page H = 841.89.**
> Fillable text fields we use: `TextField13[0]` = **Anul (year)**, `TextField2[0]` = **donor CNP**
> (maxLen 13), plus their page-2 mirrors `1.form1[0].#subform[0].TextField13[0]` and
> `1.form1[0].#subform[0].TextField2[0]`. Left blank: `TextField4[0]` (Nr. inregistrare, organ
> fiscal), `TextField4[1]` (Data, organ fiscal), `TextField2[1]` (cod fiscal imputernicit, sect.
> III). Checkboxes: `#field[43]` = "2. Sustinerea unei entitati nonprofit" (**always check**;
> mirror `1...#field[11]`), `#field[46]` = "Optiune 2 ani" (optional; mirror `1...#field[14]`),
> `CheckBox1[0]` = data-sharing consent (optional; mirror `1...CheckBox1[0]`), `#field[40]` =
> "1. Bursa privata" (unused). NO fillable fields for the entity (OncoGuide) block or the donor's
> name/address -> overlay. Entity overlay (page 0, x, y = 841.89 - yMax): CIF (244.8, 396.99),
> denumire (180.5, 375.39), IBAN (102.2, 352.35), "3,5" (123.8, 330.27).
>
> **Form 177 (OPANAF 3562/2024) -- 21 text fields, 7 checkboxes.** The COMPANY's own section I is
> fillable: `TextField7[0]`=year, `cif_nr[0]`=RO attr char (maxLen 1), `cif_nr[1]`=company CIF,
> `TextField2[0]`=company name, `TextField8[0]`=judet, `TextField3[0..6]`=localitate/strada/numar/
> bloc/scara/ap/cod postal, `TextField3[7..9]`=telefon/fax/email, `TextField8[2..4]`=the three
> sums. Checkbox `#field[2]` = "1. Sponsorizare catre entitati ... fara scop lucrativ" (**always
> check**). The beneficiary (OncoGuide) block has NO fields -> overlay (page 0, x, y = 841.89 -
> yMax): denumire (120.96, 310.11), CIF (126.72, 286.11), strada (63.36, 263.55), numar
> (355.2, 263.55), bloc (411.84, 263.55), etaj (512.64, 263.55), ap (552.0, 263.55), localitate
> (71.04, 239.07), judet (351.36, 239.07), cod postal (510.24, 239.07), IBAN (250.56, 215.27).
> The beneficiary `Suma de redirectionat` (company's amount) overlays on the IBAN line; its x is
> finalized in T6. Overlay text values come from `data/association.yaml` (note: `address_parts`
> was added there for the 177 cell-split address).

**Common facts (both forms):** plain AcroForm; `/AcroForm` present; **no `/XFA`**; **no
`NeedsRendering`**; **no client-generated 2D validation barcode**. pdf-lib `setText` / `check`
work. Field names use LiveCycle-style hierarchical paths (`form1[0].#subform[0]....`).

**Pushbutton (`/Btn`) widgets:** Form 230 reports 51 `PDFButton` and Form 177 reports 73
`PDFButton` widgets (raw `/FT /Btn` counts: 59 and 80, the remainder being the checkboxes).
These pushbuttons are non-data visual-cell widgets; pdf-lib finds zero radio groups. Do not set
them. The only data-bearing options are the checkboxes (8 on 230, 7 on 177).

**NeedAppearances byte-grep trap (verified):** after a correct fill, pdf-lib serializes into
object streams, so searching the saved bytes for `NeedAppearances` -- or even for `/AcroForm` --
returns false. This is expected, not a defect. Assert the flag by reloading and calling
`getForm().acroForm.dict.has(PDFName.of('NeedAppearances'))` (7.3.5).

### Form 230 -- OPANAF 103/2025 (individuals, 3.5%) [PROVISIONAL -- superseded by the VERIFIED CORRECTION box above]
7 text fields, 8 checkboxes. Page 1 holds the 5 base text fields; page 2 carries a PARTIAL
mirror (prefix `1.`) of only 2 of them. The mirror pairs are exactly: `TextField2[0]` (CNP) ->
`1.form1[0].#subform[0].TextField2[0]`, and `TextField13[0]` ->
`1.form1[0].#subform[0].TextField13[0]`. There is no mirror for `TextField4[0]`,
`TextField4[1]`, or `TextField2[1]`.

| Field name | Type | maxLength | Provisional meaning (confirm in fill-test) |
|------------|------|-----------|--------------------------------------------|
| `form1[0].#subform[0].TextField4[0]` | text | -- | nume / prenume (confirm) |
| `form1[0].#subform[0].TextField4[1]` | text | -- | nume / prenume (confirm) |
| `form1[0].#subform[0].TextField2[0]` | text | 13 | CNP (13 digits) |
| `form1[0].#subform[0].TextField2[1]` | text | 13 | secondary code; NOT used by our flow (do not hunt for a meaning; leave empty) |
| `form1[0].#subform[0].TextField13[0]` | text | 4 | year / number-of-years (confirm) |
| `1.form1[0].#subform[0].TextField13[0]` | text | 4 | mirror of above |
| `1.form1[0].#subform[0].TextField2[0]` | text | 13 | mirror CNP |
| `...#field[40]`, `#field[43]`, `#field[46]`, `CheckBox1[0]` (+ `1.`-prefixed mirrors) | checkbox | -- | options incl. 2-year redirection (confirm) |

### Form 177 -- OPANAF 3562/2024 (companies, profit-tax redirection)
21 text fields, 7 checkboxes. Includes a beneficiary table (`TextField3[0..9]`, 10 rows) where
OncoGuide is listed as a beneficiary with an amount.

| Field name | Type | maxLength | Provisional meaning (confirm in fill-test) |
|------------|------|-----------|--------------------------------------------|
| `form1[0].#subform[0].TextField7[0]` | text | 4 | anul (year) |
| `form1[0].#subform[0].cif_nr[0]` | text | 1 | CIF attribute char (confirm) |
| `form1[0].#subform[0].cif_nr[1]` | text | 13 | company CIF |
| `form1[0].#subform[0].TextField2[0]` | text | -- | company name (confirm) |
| `form1[0].#subform[0].TextField8[0..4]` | text | -- | address / contact (confirm) |
| `form1[0].#subform[0].TextField3[0..9]` | text | -- | beneficiary table rows (name/CIF/amount cells) |
| `form1[0].#subform[4].TextField2[1..2]` | text | 13 | page-2 codes (confirm) |
| `CheckBox1[0..1]`, `#field[2]`, `#field[21]`, `subform[4] #field[66]`, `#field[99]`, `CheckBox1[2]` | checkbox | -- | options (confirm) |

The exact `name -> meaning` map is produced by the T3 fill-test and committed in
`field-maps.js`; the `.private/finantare/formular-*-precompletat.pdf` flattened copies are the
visual ground truth for the association-data positions.

---

## Appendix B. Sponsorship Contract Template Field Schema

The sponsorship contract is OUR document (not an ANAF form), authored once as a fillable
AcroForm PDF per language at `static/donate/templates/sponsorship-contract-{lang}.pdf` (RO
first). Base the legal text on `.private/finantare/contract-sponsorizare-precompletat.pdf`
(the vetted clauses, including Article 5 with the lit. a / lit. b payment choice), MINUS the
representative name (D4). Author it with these named fields so `donate-companies.js` can fill
them deterministically:

| Field name | Source | Notes |
|------------|--------|-------|
| `sponsor_denumire` | form state | company legal name |
| `sponsor_cui` | form state | company CUI |
| `sponsor_reg_com` | form state | nr. registrul comertului |
| `sponsor_sediu` | form state | company registered office |
| `sponsor_reprezentant` | form state | company legal representative |
| `sponsor_calitate` | form state | e.g. Administrator |
| `sponsor_banca` | form state | company bank |
| `sponsor_iban` | form state | company IBAN |
| `suma` | form state | sponsorship amount (RON) |
| `data_contract` | form state | contract date |
| `art5_varianta` | form state | checkbox: lit. a (direct payment) vs lit. b (via Form 177) |
| `beneficiar_denumire` | `association.yaml` | "Asociatia OncoGuide" |
| `beneficiar_cif` | `association.yaml` | 54791907 |
| `beneficiar_sediu` | `association.yaml` | registered office |
| `beneficiar_iban` | `association.yaml` | association IBAN |
| `beneficiar_reg163` | `association.yaml` | filled only when `registru163_no` is set |
| `sponsor_semnatura` | signature canvas | a pushbutton field used as an image placeholder: the flow calls pdf-lib `getButton('sponsor_semnatura').setImage(png)` (AcroForm has no native image field type; this is the standard pdf-lib mechanism, allowed here because the contract is OUR document) |
| `beneficiar_reprezentant` | LEFT BLANK | filled offline at countersignature (D4) -- no default value |
| `beneficiar_semnatura` | LEFT BLANK | association signs offline |

Anonymity rule for this template: `beneficiar_reprezentant` and `beneficiar_semnatura` have NO
default value and NO embedded name; `scripts/audit-contract-template.mjs` (Section 12) enforces
this before the template can be committed.
