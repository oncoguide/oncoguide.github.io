# Prompt pentru agentul de implementare

## Context

Esti un senior software engineer care implementeaza un research pipeline pentru OncoGuide -- o platforma de informatie oncologica pentru pacienti cu cancer.

Exista deja o implementare functionala (v5) cu: 5 search backends (Serper, PubMed, ClinicalTrials.gov, openFDA, CIViC), discovery loop Sonnet, enrichment Haiku, guide generation, validation. Ai ghidul RET Fusion generat (171KB, 15 sectiuni, 500 findings). Pipeline-ul functioneaza end-to-end.

Trebuie sa evoluezi la v6 conform SPEC.md -- lifecycle-based discovery, 16 sectiuni, 6-layer validation, monitoring mode, seed data, auto-learning.

## Ordinea de citire (OBLIGATORIE)

Citeste in aceasta ordine EXACTA inainte de orice cod:

```
1. vision.md (root)                        -- DE CE existam (prioritati, principii)
2. agents/research/SPEC.md                 -- CE construim (spec complet, 1750+ linii)
3. CLAUDE.md (root)                        -- CUM functioneaza proiectul
4. .claude/skills/oncologist.md            -- learnings medicale existente (22 puncte)
5. .claude/skills/patient-advocate.md      -- learnings experienta pacient
6. decisions/log.yaml                      -- decizii validate (30 entries)
7. agents/research/run_research.py         -- entry point existent
8. agents/research/modules/                -- codul existent care trebuie pastrat/modificat
```

## Reguli absolute

- **Fiecare decizie tehnica trebuie sa raspunda la: "Ajuta asta pacientul?"**
- **NU ghici.** Daca SPEC.md nu specifica ceva, intreaba INAINTE de a implementa.
- **PASTREAZA** codul existent care functioneaza (searchers, cost_tracker, utils, skill_improver). Nu rescrie ce nu e necesar.
- **PASTREAZA** learnings-urile din `.claude/skills/oncologist.md` si `patient-advocate.md` -- sunt construite din experienta reala.
- **PASTREAZA** deciziile din `decisions/log.yaml` -- sunt decizii validate.
- **Foloseste** `python3` (nu `python`) -- macOS, Python 3.13.
- **Nu comite** `config.json` -- contine API keys reale.
- **Ruleaza testele existente** (32 teste) dupa fiecare modificare semnificativa.

## Ce trebuie sa faci

### Pas 0: Creeaza un plan de implementare

Inainte de a scrie cod, creeaza un plan detaliat in `agents/research/PLAN_V6.md`:

1. Citeste SPEC.md integral (toate 11 sectiuni + 20 subsectiuni din sectiunea 10)
2. Citeste codul existent (run_research.py, fiecare modul din modules/)
3. Identifica: ce se pastreaza neatins, ce se modifica, ce se creeaza nou
4. Creeaza planul cu:
   - Fiecare task concret (fisier + ce se schimba)
   - Ordinea de implementare (respecta SPEC.md Sectiunea 9)
   - Dependente intre task-uri
   - Estimare cost API ptr teste ($)
   - Milestone-uri cu verificari (vezi mai jos)
5. Prezinta planul userului ptr aprobare INAINTE de a scrie cod

### Milestone-uri obligatorii

**M1: Seed data + DB migration**
- Implementeaza tabelele noi din SPEC.md 10.10
- Implementeaza --seed (SPEC.md 10.11): importa 3454 findings din CNA + onco-blog DB
- Implementeaza --reclassify: batch Haiku lifecycle_stage classification
- Verificare: `SELECT lifecycle_stage, COUNT(*) FROM findings GROUP BY lifecycle_stage` arata distributie pe Q1-Q9
- Cost: ~$0.30 (reclassify)

**M2: Discovery restructurat**
- Modifica discovery.py: tool schemas Q1-Q8 (SPEC.md 10.3)
- Modifica advocate: scoring per Q1-Q8
- Verificare: --dry-run pe lung-ret-fusion produce output structurat per Q1-Q8
- Cost: ~$0.50 (Sonnet discovery)

**M3: Query generation + Search**
- Modifica keyword_extractor.py: queries per lifecycle stage cu minime (SPEC.md Faza 2)
- Modifica pre_search.py: template queries lifecycle
- Verificare: --dry-run arata >= 100 queries cu lifecycle_stage tags, fiecare Q1-Q8 atinge minimul
- Cost: $0 (dry-run)

**M4: Guide generation (16 sectiuni)**
- Modifica guide_generator.py: 16 sectiuni + INAINTE DE TOATE (template din SPEC.md)
- Implementeaza section briefs (SPEC.md Layer 1b)
- Verificare: genereaza ghid pe lung-ret-fusion, toate 16 sectiuni prezente, INAINTE DE TOATE prezent
- Cost: ~$1.00 (Haiku + Sonnet ptr critice)

**M5: Validation (6 layers)**
- Implementeaza Layer 1 (structural QA, zero cost)
- Implementeaza Layer 1b (section brief adherence, Haiku)
- Implementeaza Layer 2 (language + tone, Haiku)
- Implementeaza Layer 3 (consistency, Haiku)
- Modifica Layer 4 (oncologist review, Sonnet) ptr Q1-Q8
- Modifica Layer 5 (advocate review, Sonnet) ptr 16 sectiuni + global tests
- Verificare: ruleaza validarea pe ghidul generat la M4, raporteaza scor per sectiune
- Cost: ~$0.74 (2 runde)

**M6: Generare ghid RET Fusion complet (end-to-end test)**
- Ruleaza pipeline-ul COMPLET pe lung-ret-fusion:
  `python3 run_research.py --topic "lung-ret-fusion"`
- Cu seed data deja importat (M1), pipeline-ul sare la gap analysis
- Verificare contra SPEC.md Sectiunea 8 (Metrici de succes):
  - [ ] Scor advocate >= 8.5 pe TOATE 16 sectiunile
  - [ ] 0 safety concerns
  - [ ] Min 200 findings relevante
  - [ ] Cost < $5
  - [ ] Toate 16 sectiunile prezente si non-triviale
  - [ ] INAINTE DE TOATE raspunde la cele 4 intrebari
  - [ ] Nicio contradictie de date ascunsa
- Output: ghid RET Fusion v6 in `data/guides/lung-ret-fusion.md`
- Compara cu ghidul v5 existent: ce e nou? ce e mai bun? ce lipseste?
- Cost: ~$2.50 total

**M7: Monitoring mode**
- Implementeaza modules/monitor.py (M0-M6 din SPEC.md)
- Implementeaza modules/monitor_queries.py
- Implementeaza modules/change_detector.py (reguli din 10.9)
- Implementeaza modules/living_guide.py (entity extraction + guide patching)
- Verificare: `python3 run_research.py --monitor --topic "lung-ret-fusion" --since 7d`
  - Genereaza monitoring report
  - Detecteaza cel putin 1 finding nou
  - Patching-ul ghidului functioneaza
- Cost: ~$0.30

**M8: Skills + Auto-learning**
- Modifica .claude/skills/oncologist.md ptr Q1-Q8, learnings diferentiate [MEDICAL]
- Modifica .claude/skills/patient-advocate.md ptr 16 sectiuni, learnings [EXPERIENTA]
- Rescrie .claude/skills/research.md ptr v6
- Sterge monthly-review.md (absorbit in research)
- Extinde new-topic.md si ux.md
- Implementeaza context bootstrap automat
- Implementeaza feedback loop (learning extraction din validation + human corrections)
- Verificare: dupa un run complet, learnings noi apar in skills cu prefix [TOPIC] sau [GENERAL]

**M9: Observabilitate + Polish**
- Implementeaza progress reporting (format din SPEC.md)
- Implementeaza pipeline dashboard (post-run summary)
- Implementeaza health check la startup
- Implementeaza --mock mode + --save-fixtures
- Implementeaza --rollback
- Ruleaza testele: existente (32) + noi
- Final consistency check: toate flag-urile CLI functioneaza

### Dupa implementare

1. Genereaza raport final: ce s-a implementat, ce merge, ce nu merge, ce ramane
2. Compara ghidul RET Fusion v6 cu v5: diferente concrete
3. Actualizeaza decisions/log.yaml cu deciziile luate in timpul implementarii
4. Ruleaza `/publish` skill checklist pe ghidul generat (dar NU publica -- omul decide)

## Ce NU trebuie sa faci

- NU modifica vision.md
- NU modifica hugo.yaml sau Hugo site structure
- NU publica nimic pe GitHub Pages
- NU rula git push
- NU sterge date din bazele de date existente
- NU depasi bugetul de $5 per research run
- NU implementa fara plan aprobat
