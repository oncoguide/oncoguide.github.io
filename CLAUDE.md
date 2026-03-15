# OncoGuide — Agent Instructions

## Project Overview

Multilingual oncology education blog. Hugo + PaperMod theme + GitHub Pages.
URL: https://oncoguide.github.io
Primary authoring language: Romanian. 6 languages total (en, ro, it, fr, de, es).
Author is anonymous — a cancer patient writing for other patients.

## Key Files

- `prompt/PLAN.md` — Implementation plan with progress checkboxes (gitignored, local only). READ THIS FIRST every session.
- `prompt/research/` — Research findings for articles (gitignored, local only). READ relevant research files BEFORE writing any article content.
- `decisions/log.yaml` — Decision capture log. Update after significant interactions.
- `hugo.yaml` — Central Hugo configuration (languages, menus, params).
- `.github/workflows/deploy.yml` — GitHub Actions CI/CD.

## Research Directory (prompt/research/)

This directory contains research findings, medical data, and source references used to write articles.
It is gitignored (local only) to keep the public repo clean.

**Agent rule:** Before writing or translating any article, ALWAYS check `prompt/research/` for relevant
research files. These contain verified data, statistics, sources, and conclusions that MUST inform
the article content. Do NOT invent medical data — use what is documented in research files.

Current research files:
- `diagnostic-pathway.md` — Complete diagnostic protocol: molecular testing by cancer type, timelines, tumor board data
- `anadolu-experience.md` — Real patient experience at Anadolu Medical Center vs Romania (anonymized, for comparative examples)
- `content-strategy.md` — Editorial decisions: "avoid worst mistakes" philosophy, red flags pattern, patient advocacy tone

## Content Conventions

- **Disclaimer:** Every article MUST include `{{</* disclaimer */>}}{{</* /disclaimer */>}}` shortcode at the end (paired tags required).
- **Action box:** Every article MUST include `{{</* action-box */>}}...{{</* /action-box */>}}` shortcode with concrete next steps.
- **Callout:** Use `{{</* callout type="tip|important|warning" */>}}...{{</* /callout */>}}` for highlighted info boxes.
- **translationKey:** MUST be identical across all 6 language versions of the same content.
- **Tone:** Warm, empathic, from a patient who has been through it. NOT clinical/cold.
- **Medical terms:** Explain immediately upon first use, in plain language.
- **Paragraphs:** Max 4 lines. Short, scannable.
- **Anonymity:** NEVER reference specific personal details about the author. Numele real al autorului NU apare nicaieri — nici in cod, nici in continut, nici in git commits, nici pe GitHub.
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
- `archetypes/cancer-type-guide.md` — Cancer type master guide with full section structure

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
archetypes/                      — Hugo archetypes (article.md, cancer-type-guide.md)
assets/css/extended/             — Custom CSS (custom.css, print.css)
layouts/shortcodes/              — Custom shortcodes (disclaimer, action-box, callout)
layouts/partials/                — extend_head.html, extend_footer.html
i18n/                            — Custom i18n strings (en, ro, it, fr, de, es)
static/                          — robots.txt, llms.txt, favicon.svg, images
.github/workflows/               — GitHub Actions deploy workflow (deploy.yml)
decisions/                       — Decision capture log (log.yaml)
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
- The author's personal email must NEVER appear in any committed file
- Only the anonymous iCloud relay email may appear in content
- Use **GitHub Secrets** (`${{ secrets.X }}`) for any sensitive values needed in CI/CD
- Use **environment variables** for any sensitive values needed at build time
- If a value is sensitive, use a placeholder in code and document how to set the env var
- Check `.gitignore` covers sensitive patterns before first push
- The `.claude/` folder is gitignored — agent memory may contain personal data

## Research Agent (planificat)

Onco-blog va avea un research agent integrat, similar ca pattern cu proiectul separat `cancer-news-agent`.

### Arhitectura

- **Research agent** — cauta informatii ptr un topic specific, genereaza master guide per topic
  - Comanda: `python3 agents/research/run_research.py --topic "topic-id"`
  - Output: master guide markdown in `data/guides/{topic-id}.md`
- **Update agent** — acelasi agent cu flag diferit, scan lunar ptr topicuri publicate
  - Comanda: `python3 agents/research/run_research.py --update-all --since 30d`
  - Semnaleaza ce articole trebuie actualizate

### Structura planificata

```
agents/
  research/
    run_research.py        — CLI entry point (--topic X | --update-all)
    modules/               — Serper, PubMed, enrichment, DB (adaptate din cancer-news-agent)
    config.json            — API keys (gitignored)
data/
  research.db              — SQLite (gitignored)
  guides/                  — Master guide markdown per topic (gitignored)
  backups/                 — DB backups
topics/
  registry.yaml            — Lista topicuri: id, status, search queries, content_file
```

### Reguli

- Codul este copiat si adaptat din cancer-news-agent — fara dependinte intre proiecte
- Research DB in `data/research.db`, gitignored
- Master guides in `data/guides/`, gitignored
- Topic registry in `topics/registry.yaml`, comis in git
- Workflow: decidem topic → research agent → master guide → scriem articol → publish
- Update agent ruleaza lunar, compara cu ce e publicat

### Relatie cu cancer-news-agent

- cancer-news-agent = monitorizare medicala personala (proiect separat, independent)
- onco-blog research agent = research ptr articole educative publice
- Cod partajat prin copiere, NU prin import/dependinta
- cancer-news-agent NU se modifica niciodata din onco-blog

## Claude Skills

Skills specializate in `.claude/skills/`:

### Agenti de lucru
- `/research` — Run research agent for a specific topic, generating a master guide from Serper + PubMed data
- `/monthly-review` — Run monthly content review to identify published articles needing updates based on new medical data
- `/new-topic` — Add a new topic to the registry and prepare directory structure for research and content
- `/publish` — Run pre-publication checklist for an article -- SEO, disclaimers, translations, shortcodes, internal links

### Expertiza (persona + action checklist)
- `/frontend` — Review frontend code for responsive design, accessibility (WCAG AA), performance, and dark mode compatibility
- `/ux` — Review user experience -- navigation clarity, information architecture, mobile usability, content scanability
- `/oncologist` — Review medical accuracy, terminology, protocols, and source quality of oncology articles
- `/patient-advocate` — Review articles from a patient perspective -- accessible language, empathy, actionable steps, no condescension
- `/seo` — Review SEO -- keywords, meta descriptions, structured data, internal linking, multilingual SEO consistency

## Session Start Checklist

1. Read `prompt/PLAN.md` — find the first unchecked `[ ]` subfase
2. Read `decisions/log.yaml` — understand prior context
3. Read this file (`CLAUDE.md`) — refresh conventions
4. If writing content: read relevant files from `prompt/research/`
5. Continue implementation from where the last session left off
