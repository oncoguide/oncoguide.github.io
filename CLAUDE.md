# OncoGuide — Agent Instructions

## Project Overview

Multilingual oncology education blog. Hugo + PaperMod theme + GitHub Pages.
URL: https://oncoguide.github.io
Primary authoring language: Romanian. 6 languages total (en, ro, it, fr, de, es).
Author is anonymous — a cancer patient writing for other patients.

Content is **hand-curated**. (An AI research pipeline lived in `agents/research/` until June 2026;
it produced the first guides and was then retired — see `decisions/log.yaml` id 72. If you ever need
it, it is recoverable from git history.)

The blog is operated by **Asociația OncoGuide**, a registered Romanian non-profit. Its legal,
founder, and financing documents live in `.private/` (gitignored — NEVER commit; contains personal data).

## Key Files

- `VISION.md` — Project vision and operating principles. READ THIS FIRST every session. Every decision must serve the patient.
- `CLAUDE.md` — This file: conventions, structure, skills.
- `decisions/log.yaml` — Decision capture log. Append after significant interactions.
- `DONATIONS.md` — Donate page architecture + review-gated implementation plan (source of truth for the donation flows).
- `hugo.yaml` — Central Hugo configuration (languages, menus, params).
- `.github/workflows/deploy.yml` — GitHub Actions CI/CD.
- `prompt/research/` — Local research notes / source material that inform article content (gitignored, local only). Check for relevant files BEFORE writing article content. Do NOT invent medical data.
- `.private/` — Association legal/admin/financing docs (gitignored, local only, personal data).

## Content Conventions

- **Disclaimer:** Every article MUST include `{{</* disclaimer */>}}{{</* /disclaimer */>}}` shortcode at the end (paired tags required).
- **Action box:** Every article MUST include `{{</* action-box */>}}...{{</* /action-box */>}}` shortcode with concrete next steps.
- **Callout:** Use `{{</* callout type="tip|important|warning" */>}}...{{</* /callout */>}}` for highlighted info boxes.
- **translationKey:** MUST be identical across all 6 language versions of the same content.
- **Tone:** Warm, empathic, from a patient who has been through it. NOT clinical/cold.
- **Medical terms:** Explain immediately upon first use, in plain language.
- **Paragraphs:** Max 4 lines. Short, scannable.
- **Anonymity:** NEVER reference specific personal details about the author. Numele real al autorului NU apare nicaieri — nici in cod, nici in continut, nici in git commits, nici pe GitHub. Founders' real names live ONLY in `.private/` (gitignored).
- **No commercial content:** No ads, no affiliate links, no product endorsements.
- **No special symbols:** NO emojis, NO typographic quotes, NO em-dashes. Use standard quotes (""), double hyphens (--), and bold text (**NU:**) instead.

## Shortcodes Reference

| Shortcode | Purpose | Usage |
|-----------|---------|-------|
| `disclaimer` | Medical disclaimer (i18n-aware) | `{{</* disclaimer */>}}{{</* /disclaimer */>}}` — paired tags required |
| `action-box` | Green "What to do now" box | `{{</* action-box */>}}1. Step one\n2. Step two{{</* /action-box */>}}` |
| `callout` | Info/warning/tip highlight | `{{</* callout type="tip" */>}}Content{{</* /callout */>}}` |

## Archetypes

- `archetypes/article.md` — Standard article template with all required fields
- `archetypes/default.md` — Hugo default archetype

## Content Architecture

**Published content types:**
- `guide` — Standalone articles (e.g., complete diagnosis guide)
- `subtype` — Patient Master Guide per molecular subtype (e.g., lung-ret-fusion, breast-her2)

**Why no generic "cancer type guide"?** Patients search for their specific diagnosis (e.g., "RET fusion lung cancer"), not generic overviews. A generic "lung cancer guide" would be too broad to be actionable. Each molecular subtype has completely different treatment, prognosis, and side effects.

## Static Pages (non-article)

| Page | translationKey | Layout | Notes |
|------|---------------|--------|-------|
| About | `about` | `page` | Mission, anonymity, how to contribute |
| Contact | `contact` | `page` | Email contact (Formspree form to be added later) |
| Archives | `archives` | `archives` | PaperMod auto-generated archive listing |
| Search | `search` | `search` | Fuse.js via PaperMod, JSON output required |

## SEO Checklist (per article)

- [ ] Title H1 contains primary keyword
- [ ] Meta `description` 140–160 chars, actionable, includes keyword
- [ ] Min 2 internal links to related articles
- [ ] Min 2 external links to authoritative sources (PubMed, ESMO, clinicaltrials.gov)
- [ ] Images with descriptive `alt` text (if any)
- [ ] `translationKey` identical in all 6 languages
- [ ] "What to do now" action section present at end
- [ ] Disclaimer shortcode present at end

## File Structure

```
content/{en,ro,it,fr,de,es}/    — Content per language
  _index.md                      — Homepage content per language
  about.md                       — About page (translationKey: about)
  contact.md                     — Contact page (translationKey: contact)
  archives.md                    — Archives page (translationKey: archives)
  search.md                      — Search page (translationKey: search)
  diagnosis/                     — Diagnosis guides
  cancer-types/                  — Cancer type master guides
  treatment-access/              — Treatment access & patient rights
  imaging/                       — Imaging centers & guides
  clinical-trials/               — Clinical trials guides
archetypes/                      — Hugo archetypes (article.md, default.md)
assets/css/extended/             — Custom CSS (custom.css, print.css)
layouts/shortcodes/              — Custom shortcodes (disclaimer, action-box, callout)
layouts/partials/                — extend_head.html, extend_footer.html
i18n/                            — Custom i18n strings (en, ro, it, fr, de, es)
data/                            — Hugo data files (scanners.yaml, association.yaml, fiscal.yaml)
                                   NOTE: data/* is gitignored EXCEPT the 3 above (explicit !exceptions)
DONATIONS.md                     — Donate page architecture (review-gated; see Key Files)
package.json                     — Node tooling for donation scripts (pdf-lib devDependency)
static/donate/                   — Donation flow assets (vendored pdf-lib, ANAF templates, flow JS)
scripts/audit-contract-template.mjs — Anonymity audit (runs in pre-commit; name from .private/)
scripts/bridge-check.mjs         — Regression guard: donate data bridge in BUILT html (run after hugo)
scripts/fill-test.mjs            — ANAF AcroForm fill-test (re-run on any new ANAF form revision)
scripts/make-contract-template.mjs — Rebuilds sponsorship-contract-ro.pdf (reproducible; audit-gated)
static/                          — robots.txt, llms.txt, favicon.svg, images
scripts/                         — Helper scripts (staticrypt encryption, git hooks)
.github/workflows/               — GitHub Actions deploy workflow (deploy.yml)
hugo.yaml                        — Central config: languages, menus, params, homeInfoParams
```

## Translation Workflow

1. Write article in Romanian first
2. Translate to 5 other languages (en, it, fr, de, es)
3. Ensure `translationKey` is IDENTICAL in all 6 versions
4. Ensure all shortcodes are present in translations
5. Verify medical terminology uses standard terms in each language (not literal translations)
6. Preserve all internal links (adjust URL prefix per language)

## Decision Log

After any significant conversation with the user (design choices, content strategy, technical
decisions, learnings), append new entries to `decisions/log.yaml` following the existing format.

Categories: `technical`, `design`, `content`, `learning`, `process`

## Security Rules

- NEVER commit files containing: passwords, API keys, tokens, personal emails, private data
- ALWAYS grep staged files for sensitive patterns before every commit
- ALWAYS review `git diff` before committing
- The author's personal email and the founders' real names must NEVER appear in any committed file
- Only the anonymous iCloud relay email may appear in content
- Use **GitHub Secrets** (`${{ secrets.X }}`) for any sensitive values needed in CI/CD
- Use **environment variables** for any sensitive values needed at build time
- If a value is sensitive, use a placeholder in code and document how to set the env var
- Check `.gitignore` covers sensitive patterns before first push
- `.claude/` and `.private/` are gitignored — they may contain personal data
- A pre-commit hook (`scripts/hooks/pre-commit`) scans staged files for email addresses. Activated via `git config core.hooksPath scripts/hooks`.

## Claude Skills

Skills specializate in `.claude/skills/` (gitignored, local-only):

### Workflow
- `/publish` — Run pre-publication checklist for an article -- SEO, disclaimers, translations, shortcodes, internal links
- `/monthly-review` — Monthly freshness review of published medical guides (PubMed/ESMO/FDA/EMA/trials since last review, judgment-based triage, proposed updates). Editing principles: high bar (default no-change), integrate never patch, supersede never stack, full-article coherence pass after any edit, anti-noise circuit breaker (3 point edits -> full editorial pass). Backs the PUBLIC "roughly monthly review" promise on the donate pages -- keep cadence and copy in sync. State in `prompt/research/reviews/` (local)

### Expertiza (persona + action checklist)
- `/frontend` — Review frontend code for responsive design, accessibility (WCAG AA), performance, and dark mode compatibility
- `/ux` — Review user experience -- navigation clarity, information architecture, mobile usability, content scanability
- `/oncologist` — Review medical accuracy, terminology, protocols, and source quality of oncology articles
- `/patient-advocate` — Review articles from a patient perspective -- accessible language, empathy, actionable steps, no condescension
- `/seo` — Review SEO -- keywords, meta descriptions, structured data, internal linking, multilingual SEO consistency

## Dependency Map (keep in sync)

When modifying files in the left column, also update the files in the right column in the SAME commit.

| When you modify... | Also update... |
|---|---|
| Any skill in `.claude/skills/` | This file ("Claude Skills" section) |
| `hugo.yaml` (languages, menus) | This file ("File Structure") |
| `data/association.yaml` or `data/fiscal.yaml` | Review `static/donate/js/field-maps.js` + the donation flows (DONATIONS.md S13); if deadlines changed, also refresh the dated strings in `static/donate/js/i18n.js` and the RO donate pages |
| ANAF templates in `static/donate/templates/` | Re-run the fill-test (DONATIONS.md S7.3) and update DONATIONS.md App. A |

## Session Start Checklist

1. Read `VISION.md` — understand WHY before anything else. Every decision must serve the patient.
2. Read `CLAUDE.md` (this file) — refresh conventions.
3. Read `decisions/log.yaml` — understand prior context.
4. If writing content: read relevant files from `prompt/research/`.
5. If working on association admin/financing: read `.private/README.md` (fact-sheet) + `.private/finantare/`.
