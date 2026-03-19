# OncoGuide Research Agent -- Specification v6

> **Citeste `vision.md` inainte de orice altceva.**
> Fiecare decizie din acest spec trebuie sa raspunda la: "Ajuta asta pacientul?"

---

## 1. Scopul spec-ului

Acest document defineste logica completa a research agent-ului OncoGuide: cum genereaza ghiduri cuprinzatoare pentru orice subtip molecular de cancer, pornind de la un singur input (diagnosticul), prin prisma calatoriei pacientului.

Spec-ul va fi dat unui agent de implementare. Agentul trebuie sa pastreze si sa reutilizeze din implementarea curenta (v5): cod functional, skills existente (`.claude/skills/`), decizii din `decisions/log.yaml`, structura proiectului si pattern-urile editoriale.

---

## 2. Principiul fundamental

**Informatia nu este un scop in sine. Este un instrument de supravietuire cu cat mai putine complicatii.**

Algoritmul porneste de la intrebarile pe care un pacient le are EFECTIV, in ordinea in care le are:
1. Ce trebuie sa EVIT ca sa nu sabotez tratamentul?
2. Ce pot FACE activ ca sa ajut tratamentul sa functioneze cat mai bine?
3. Cum RECUNOSC cat mai rapid problemele si progresia?
4. Ce OPTIUNI am daca tratamentul actual nu mai merge?
5. Ce apare NOU in lume care ma poate ajuta?

Aceasta ordine este sacra. Ghidul trebuie sa reflecte aceste prioritati, nu o structura academica.

---

## 3. Input si output

**Input:** Un diagnostic precis de subtip molecular (ex: "RET fusion-positive lung adenocarcinoma (NSCLC)")
Definit ca topic in `topics/registry.yaml`.

**Output:** Un ghid master de 30-200KB in format markdown, cu citari catre surse verificabile, care acopera intregul lifecycle al pacientului cu acel diagnostic.

---

## 4. Cadrul lifecycle -- cele 9 intrebari (Q1-Q9)

Fiecare ghid se construieste raspunzand la 9 seturi de intrebari. Primele 8 sunt SPECIFICE diagnosticului. Q9 este TRANSVERSAL (acelasi pentru orice cancer).

### Intrebari specifice diagnosticului

**Q1 -- CONFIRMAREA DIAGNOSTICULUI**
Ce teste confirma diagnosticul definitiv? Ce inseamna staging-ul? Ce subtipuri moleculare exista si de ce conteaza pentru tratament?

**Q2 -- TRATAMENTUL STANDARD**
Ce tratamente sunt aprobate per stadiu si linie? Care este cea mai buna optiune acum? Ce spun ESMO si NCCN (si care sunt diferentele)? Imunoterapia este relevanta? Comparatii head-to-head daca exista mai multe optiuni.

**Q3 -- CUM TRAIESTI CU TRATAMENTUL** (cel mai mare volum de queries)
Per FIECARE drug aprobat:
- Cum se ia corect (doza, timing, mancare, pH, PPI)
- TOATE efectele secundare cu procente reale (%, grad)
- Profilul metabolic CYP: ce enzime, ce interactiuni concrete
- Interactiuni specifice: alimente, suplimente, OTC, alte medicamente
- Ce monitorizare trebuie: teste, frecventa, de ce
- Managementul fiecarui efect secundar major
- Semne de alarma -- cand mergi la urgente (checklist printabil)
- Nutritie, exercitii, oboseala in timpul tratamentului
- Acces si cost: per tara -- ordonanta prezidentiala (RO), ATU (FR), Hartefallprogramm (DE), compassionate use (EMA), cross-border healthcare directive EU, patient assistance programs

**Q4 -- METASTAZE COMUNE**
Care sunt cele mai frecvente site-uri de metastaza pentru acest cancer?
Per FIECARE site comun (top 3-5):
- Cat de frecvent (% pacienti)
- Cum se detecteaza
- Tratament standard (sistemic + local)
- Optiuni locale: SBRT, chirurgie, ablatie
- Terapie suportiva specifica site-ului (denosumab ptr os, etc.)

**Q5 -- CAND NU MAI MERGE (REZISTENTA SI PROGRESIE)**
Cum si cand se dezvolta rezistenta? Mecanisme specifice PE NUME (mutatii on-target, bypass pathways). Plan B, C, D concret -- fiecare optiune cu date. Re-biopsie: cand, ce cauti. Treatment beyond progression. Combinatii care depasesc rezistenta.

**Q6 -- CE VINE (PIPELINE)**
Per FIECARE drug in dezvoltare -- PE NUME: faza, mecanism, targeteza rezistenta? timeline realist.
Modalitati noi aplicabile (ADC, PROTAC, CAR-T, TIL, bispecifice, mRNA vaccines).
Trialuri clinice care recruteaza ACUM -- NCT, faza, eligibilitate, locatii.

**Q7 -- CE SA NU FACI (GRESELI)**
Ce interactiuni sunt periculoase? Ce suplimente/naturiste sunt contraindicate? Ce mituri circula? Ce greseli fac pacientii frecvent si de ce sunt periculoase? Format: GRESEALA -- DE CE E PERICULOASA -- CE SA FACI IN SCHIMB.

**Q8 -- NU ESTI SINGUR (COMUNITATE)**
Comunitati de pacienti specifice diagnosticului. Experienta reala a altor pacienti. Suport caregiver. Organizatii si resurse.

### Intrebari transversale (aceleasi ptr orice cancer)

**Q9 -- ACCES GEOGRAPHIC**
Diferente de acces la medicamente per tara/regiune. Mecanisme legale de acces (pe tara). Romania si Europa prioritar. Tehnologii de diagnostic disponibile per regiune.

**Nota:** Nu exista Q10, Q11 separate. Continutul lor a fost absorbit astfel:
- Liquid biopsy, ctDNA, MRD -> integrat in Q3 (monitorizare sub tratament) si Q5 (detectare rezistenta)
- Conferinte, inovatii, terapii tumor-agnostic -> integrat in Q6 (pipeline) doar daca au relevanta directa ptr diagnostic
- Conform P1 din vision.md: "informatia serveste supravietuirea, nu curiozitatea" -- conferintele si AI-ul oncologic nu sunt sectiuni de sine statatoare

---

## 5. Pipeline-ul -- faze, gate-uri si failover

### Principii de cost si rezilienta

- **Checkpoint dupa fiecare faza**: starea se salveaza in DB. Daca pipeline-ul pica, se reia din ultima faza completa, nu de la inceput.
- **Sanity check inainte de faze costisitoare**: inainte de discovery (Sonnet) si guide generation, se verifica: avem date suficiente? s-a ajuns la threshold-ul minim? Daca nu, se opreste cu raport de eroare, nu se cheltuiesc tokeni degeaba.
- **Budget cap**: max $5 per run. CostTracker (existent) verifica dupa fiecare API call.
- **Failover la enrichment**: daca un batch call esueaza, se reprocesseaza individual. Daca tot esueaza, se sare finding-ul cu log.
- **Failover la search**: daca un backend e down (rate limit, timeout), se logheaza eroarea si se continua cu celelalte. Finding-urile lipsa pot fi recuperate la re-run.
- **Guide generation per sectiune**: daca generarea unei sectiuni esueaza, celelalte nu sunt afectate. Se poate re-genera doar sectiunea esuata.
- **Checkpoint format**: Fiecare faza completa scrie un row in tabela `pipeline_state`: `topic_id, phase (0-8), status (complete/failed/partial), output_ref (path sau JSON blob), cost_usd, timestamp`. La re-run, `run_research.py` citeste ultima faza cu status=complete si reia de la faza urmatoare.
- **Budget prioritization**: Daca bugetul se apropie de cap ($5), prioritatea de alocare: 1) Validation Sonnet (siguranta pacientului), 2) Sectiuni critice Sonnet (3, 5, 8, 10), 3) Discovery Sonnet. Restul degradeaza la Haiku. CostTracker raporteaza `has_budget(reserve_usd=1.0)` inainte de faze costisitoare.

### Observabilitate si developer experience

**Logging structurat:**
- Fiecare faza logheaza: `[PHASE N] {phase_name} | START/END/ERROR | {detalii}`
- Nivel INFO ptr flow normal, WARNING ptr degradari graceful, ERROR ptr esecuri
- Fiecare API call logheaza: model, tokens (in/out), cost, duration_ms, status
- La sfarsitul fiecarei faze: summary line cu: findings_count, cost_so_far, duration
- Logurile se scriu in `logs/research.log` (existent) + stdout ptr CLI

**Progress reporting:**
- Operatiile care dureaza > 30 secunde afiseaza progress bar sau status updates in CLI:
  - Search: `[Search] 45/130 queries | 312 findings | $0.00 | 2m12s`
  - Enrichment: `[Enrich] 180/312 findings | batch 36/63 | $0.08 | 1m45s`
  - Discovery: `[Discovery] Round 2/5 | Q1:9.0 Q2:8.5 Q3:7.2 Q4:8.0 ... | $0.45`
  - Guide generation: `[Guide] Section 5/16 | "EFECTE SECUNDARE" (Sonnet) | $1.20`
  - Validation: `[Validate] Round 1/2 | Score: 8.1/10 | 2 issues | $1.80`
- Format: `[Module] progress_indicator | key_metric | cost_running | elapsed_time`
- Se actualizeaza in-place (carriage return) ptr terminals care suporta, fallback la newline

**Pipeline dashboard (post-run):**
- La sfarsitul fiecarui run (research sau monitor), se printeaza un summary:
```
=== PIPELINE SUMMARY ===
Topic:    lung-ret-fusion
Mode:     research
Duration: 14m32s
Cost:     $2.35 / $5.00 budget

Phase 0 (Pre-search):    32s    $0.02   50 findings
Phase 1 (Discovery):     4m12s  $0.45   converged round 4
Phase 2 (Query gen):     18s    $0.05   127 queries
Phase 3 (Search+Enrich): 5m44s  $0.38   289 findings (412 raw, 289 relevant)
Phase 4 (Gap analysis):  1m05s  $0.08   +34 findings round 2
Phase 5 (Cross-verify):  22s    $0.03   12 verified, 2 contradicted, 5 unverified
Phase 6 (Guide gen):     2m18s  $0.82   16 sections, 142KB
Phase 7 (Validation):    1m41s  $0.52   score 8.7/10, 0 safety concerns PASS
Phase 8 (Review+Skills): 2s     $0.00   checklist generated

Findings: 323 total (289 R1 + 34 R2)
Guide:    142KB, 16/16 sections, all >= 8.5
Alerts:   0 safety, 0 critical
Status:   guide_ready
```

**Health check la startup:**
- Inainte de orice run, se verifica:
  - API keys prezente si valide (Anthropic: HEAD request, Serper: test query)
  - DB accesibila si schema corecta (tabele prezente)
  - Topic exista in registry.yaml
  - Disk space suficient (min 100MB)
  - Daca e re-run: identifica ultima faza completa din `pipeline_state`
- Daca health check esueaza: mesaj clar cu CE lipseste si CUM se rezolva, apoi exit(1)

**Error context:**
- Fiecare eroare logheaza: ce se incerca, cu ce input, de ce a esuat, ce se poate face
- Exemplu bun: `[ERROR] Enrichment batch 12 failed: API rate limit (429). Retrying in 30s. Findings 56-60 will be processed individually if batch retry fails.`
- Exemplu rau: `[ERROR] API call failed`

**Idempotenta:**
- Rularea aceleiasi faze de doua ori este safe (dedup prin content_hash, checkpoint status check)
- `--force-phase N` flag ptr a forta re-executia unei faze specifice (ignora checkpoint-ul pt acea faza)

### Testabilitate

**Dry-run mode** (existent, se pastreaza):
- `--dry-run` afiseaza queries-urile generate fara sa le execute
- Se extinde: `--dry-run` acum arata si lifecycle stage mapping si minimum query coverage

**Mock mode** (nou):
- `--mock` ruleaza pipeline-ul complet dar cu raspunsuri AI fixe (din fixtures)
- Util ptr testarea flow-ului fara cost API
- Fixtures salvate in `tests/fixtures/` per topic
- Dupa un run real reusit, se pot salva raspunsurile ca fixtures: `--save-fixtures`

**Test isolation:**
- Fiecare modul are teste unitare independente (existent: 32 teste)
- Se adauga: integration test end-to-end cu mock mode
- Se adauga: smoke test ptr fiecare backend (verifica ca API-urile raspund)

### Guide versioning si rollback

- Ghidul master se salveaza cu timestamp: `data/guides/{topic_id}.md` (current) + `data/guides/{topic_id}_{timestamp}.md` (backup inainte de fiecare modificare)
- Monitoring mode creeaza backup automat inainte de patching
- Rollback: `--rollback --topic "lung-ret-fusion"` restaureaza ultima versiune din backup
- Max 10 versiuni backup (rotatie, identic cu DB backups)

### Data hygiene

- **Link rot detection**: la fiecare monitoring run, se verifica random 10% din URL-urile existente. Cele moarte se marcheaza `link_alive=false` in DB. Ghidul nu citeaza surse moarte.
- **Retracted papers**: daca un finding din PubMed este retras (detectat prin re-search), se marcheaza si se sterge din ghid la urmatoarea regenerare.
- **Guide size cap**: daca ghidul depaseste 250KB dupa monitoring patches, se triggereaza auto o regenerare completa (research mode) la urmatorul run.
- **DB cleanup**: findings cu relevance < 3 si mai vechi de 6 luni se arhiveaza (muta in `findings_archive` table). Nu se sterg -- pot fi restaurate.

### FAZA 0: Pre-search (zero AI cost ptr template-uri + Haiku ptr complement)

**Scop:** Grounding -- aduce date REALE din lumea exterioara inainte de discovery, ca sa nu se bazeze oncologistul exclusiv pe cunostintele parametrice.

**Input:** Diagnosticul din registry.yaml
**Output:** Top 50 findings formatate ca text context

**Logica:**
1. Genereaza ~20 template queries (zero AI, identice ptr orice cancer -- parametrizate cu {diagnosis}):
   - "{diagnosis} treatment guidelines {year}"
   - "{diagnosis} approved drugs first-line"
   - "{diagnosis} resistance mechanisms mutations"
   - "{diagnosis} side effects toxicity incidence"
   - "{diagnosis} brain metastases treatment"
   - "{diagnosis} bone metastases treatment"
   - "{diagnosis} clinical trials recruiting"
   - "{diagnosis} survival outcomes PFS OS"
   - "{diagnosis} drug interactions CYP metabolism"
   - "{diagnosis} ESMO NCCN guidelines"
   - "{diagnosis} patient experience community"
   - "{diagnosis} new drug pipeline development"
   - "{diagnosis} emergency symptoms when to go ER"
   - "{diagnosis} molecular testing diagnosis confirmation"
   - "{diagnosis} European access reimbursement"
   - (+ query-uri pe openFDA, CIViC, ClinicalTrials.gov)

2. Genereaza ~20 complement queries cu Haiku: focusate pe ENTITATI NUMITE (drug names, trial names, mutation names) -- ce template-urile nu pot sti

3. Executa pe toate 5 backend-urile (Serper, PubMed, ClinicalTrials.gov, openFDA, CIViC)
4. Enrichment rapid cu Haiku (relevance + authority)
5. Returneza top 50 findings ca text

**Failover:** Daca un backend e down, se continua cu celelalte. Daca Haiku complement esueaza, se folosesc doar template-urile.

**Checkpoint:** Pre-search context salvat in DB (run_type="pre_search"). Nu se repeta daca exista deja.

**GATE 0:** Min 20 findings obtinute. Daca < 20, se logheaza warning dar se continua (diagnosticul poate fi ultra-rar).

---

### FAZA 1: Discovery -- Expert Knowledge Extraction (Sonnet)

**Scop:** Extrage cunostintele unui oncolog expert, STRUCTURAT pe cele 8 intrebari lifecycle.

**Schimbarea majora fata de v5:** Nu mai e free-form. Oncologistul TREBUIE sa raspunda la Q1-Q8, nu la un "knowledge map" generic.

**Input:** Diagnostic + pre-search context (top 50 findings)
**Output:** Raspunsuri structurate per Q1-Q8, cu entitati numite

**Logica:**
1. Oncologistul primeste cadrul Q1-Q8 si pre-search context
2. Foloseste tool use pt a returna raspunsuri structurate per intrebare:
   - Q1: teste moleculare, staging, subtipuri
   - Q2: drugs aprobate [{name, brand, status_fda, status_ema, line, trials}], ghiduri
   - Q3: per drug [{name, dose, food, cyp_profile, side_effects[{name, percentage, grade}], monitoring[{test, frequency}]}]
   - Q4: metastasis_sites[{site, frequency_percent, detection, treatment, local_options, supportive}]
   - Q5: resistance_mechanisms[{type, name, median_time}], next_line_options[{drug, evidence}]
   - Q6: pipeline_drugs[{name, code, manufacturer, phase, mechanism, targets_resistance, trial_nct}]
   - Q7: mistakes[{mistake, why_dangerous, alternative}]
   - Q8: communities[{name, url, description}]

3. Advocate-ul evalueaza per intrebare (Q1-Q8), scor 1-10
4. Convergenta: TOATE Q1-Q8 >= 8.5/10 SAU max 5 runde

**Reguli OBLIGATORII ptr oncologist:**
- Q3: OBLIGATORIU profil CYP per drug + TOATE efectele cu %
- Q4: OBLIGATORIU top 3-5 site-uri de metastaza cu frecventa %
- Q5: OBLIGATORIU fiecare mutatie/mecanism PE NUME
- Q6: OBLIGATORIU fiecare drug in pipeline PE NUME + faza
- Q7: OBLIGATORIU fiecare interactiune periculoasa PE NUME

**Failover:** Daca Sonnet timeout, se re-incearca cu streaming (existent in utils.py api_call). Daca tot esueaza, se salveaza progresul partial si se reia la re-run.

**Checkpoint:** conversation + knowledge output salvate in DB.

**GATE 1:** Convergenta atinsa (toate Q >= 8.5) SAU max runde epuizate. Daca nu converge in 5 runde, se continua cu ce exista + log warning. Se verifica minim: Q2 are cel putin 1 drug, Q5 are cel putin 1 mecanism de rezistenta, Q6 are cel putin 1 pipeline drug.

**SANITY CHECK inainte de FAZA 2:** Se verifica ca output-ul discovery contine entitati numite suficiente: min 1 drug aprobat, min 1 trial, min 3 side effects cu %, min 1 metastasis site. Daca lipseste, se logheaza dar NU se opreste (pre-search-ul poate compensa).

---

### FAZA 2: Query Generation -- Keyword Extraction (Sonnet)

**Scop:** Transforma cunostintele din discovery in queries de cautare precise.

**Schimbarea majora:** Queries generate PER LIFECYCLE STAGE cu cerinte minime. Regula de aur: fiecare ENTITATE NUMITA din discovery trebuie sa aiba min 1 query dedicat.

**Input:** Discovery output structurat + cadrul Q1-Q8
**Output:** 100-170 queries taguite cu: lifecycle_stage, search_engine, language, priority

**Cerinte minime per stage:**

| Stage | Min queries | Logica |
|-------|-------------|--------|
| Q1 Diagnostic | 5 | per test molecular + staging |
| Q2 Tratament | 10 | per drug aprobat x per endpoint (efficacy, safety, comparison) |
| Q3 Cum traiesti | 20 | per drug: CYP, side effects, interactions, monitoring + nutritie, exercitii, urgente, acces |
| Q4 Metastaze | 8 | per site comun de metastaza |
| Q5 Rezistenta | 10 | per mecanism + per next-line drug |
| Q6 Pipeline | 12 | per named pipeline drug + per modality (ADC, PROTAC, etc.) |
| Q7 Greseli | 5 | interactiuni periculoase, mituri, erori frecvente |
| Q8 Comunitate | 4 | forumuri, povesti, caregiver, organizatii |
| Q9 Acces geographic | 5 | per tara/regiune, mecanisme legale de acces |

**Nota:** Q3 (Cum traiesti) include acum si queries ptr liquid biopsy/ctDNA relevante ptr monitorizare sub tratament. Q6 (Pipeline) include si highlights de conferinte/inovatii DOAR daca sunt direct relevante ptr diagnostic.

**Reguli per backend:**
- **Serper:** Limbaj natural, SPECIFIC (drug names, trial names). Include queries in min 6 limbi (en, de, fr, es, it, ro) ptr Q2+Q5.
- **PubMed:** MeSH terms + free-text hybrid. Max 100 chars.
- **ClinicalTrials.gov:** condition + intervention ptr fiecare drug aprobat si pipeline.
- **openFDA:** Per drug aprobat: adverse_events, label, enforcement.
- **CIViC:** Per gene: RESISTANCE + PREDICTIVE evidence.

**Query de acces per tara (Q3 + Q9):**
- "ordonanta prezidentiala Romania acces tratament oncologic"
- "ATU autorisation temporaire utilisation cancer France"
- "Hartefallprogramm cancer treatment access Germany"
- "compassionate use named patient program cancer Europe EMA"
- "cross-border healthcare directive cancer treatment EU"
- "NHS cancer drugs fund UK"
- "cancer treatment access Italy AIFA"

**Multilingual expansion:** Queries cheie din Q2, Q3, Q5 se traduc in min 12 limbi (en, es, de, fr, it, pt, nl, pl, ru, zh, ja, ko, ro, tr).

**Frontier discovery net (integrat in Q6):** "{cancer_type} new drug therapy breakthrough {year}" in 7+ limbi. Aceste queries fac parte din Q6 (Pipeline) -- nu sunt o categorie separata.

**Failover:** Daca Sonnet esueaza, se genereaza queries doar din template-uri (degraded mode). Se logheaza.

**Checkpoint:** Lista de queries salvata in DB (search_log pregatit).

**GATE 2:** Total queries >= 80. Fiecare Q1-Q8 atinge minimul. Daca nu, se logheaza warning dar se continua.

---

### FAZA 3: Search Round 1 + Enrichment (5 backends + Haiku)

**Scop:** Executia queries-urilor si clasificarea findings-urilor.

**Logica:** Identica cu v5 existenta:
1. Executa toate queries-urile pe cele 5 backends
2. Dedup: content_hash + URL
3. Enrichment cu Haiku batch (5 findings/batch): relevance 1-10, authority 1-5, title_english, summary_english
4. Stocheaza in DB findings relevante

**Schimbare:** Enrichment-ul primeste si lifecycle_stage tag-ul query-ului care a produs finding-ul. Asta ajuta la gap analysis.

**Failover:**
- Backend down: skip cu log, nu opreste pipeline-ul
- Enrichment batch fail: retry individual (existent)
- Rate limit: exponential backoff (existent in searcher modules)

**Checkpoint:** Findings salvate in DB cu run_id. search_log completat.

**GATE 3:** Min 100 findings relevante (relevant=true) total. Daca < 100, se logheaza warning. Daca < 20, se OPRESTE pipeline-ul cu eroare (diagnosticul e prea rar sau queries-urile sunt gresite).

---

### FAZA 4: Gap Analysis + Search Round 2 (Haiku)

**Scop:** Identifica lifecycle stages slab acoperite si genereaza queries tintite.

**Schimbare fata de v5:** Gap analysis se face PER LIFECYCLE STAGE, nu per sectiune abstracta.

**Threshold-uri per stage:**
| Stage | Min findings cu relevance >= 7 | Rationale |
|-------|--------------------------------|-----------|
| Q3 Cum traiesti | 20 | Cel mai important -- afecteaza viata zilnica |
| Q2 Tratament | 15 | Baza ghidului |
| Q5 Rezistenta | 10 | Plan B/C trebuie solid |
| Q4 Metastaze | 5 per site comun | Fiecare site trebuie acoperit |
| Q6 Pipeline | 8 | Optiuni viitoare |
| Q1 Diagnostic | 5 | Informatii de baza |
| Q7 Greseli | 5 | Alimenteaza Sect 3 (critica) -- nevoie de surse ptr fiecare greseala |
| Q8 Comunitate | 3 | Suport emotional |

**Logica:**
1. Mapeaza findings-urile existente pe Q1-Q8 (folosind lifecycle_stage tag + Haiku reclassification)
2. Identifica stages sub threshold
3. Genereaza 2-4 queries tintite per stage slab (Haiku)
4. Executa round 2 pe toate backend-urile
5. Enrichment round 2

**Failover:** Daca gap analysis Haiku esueaza, se sare direct la cross-verification cu findings-urile existente.

**Checkpoint:** Round 2 findings salvate cu acelasi run_id.

**GATE 4:** Nu e blocker -- se trece la faza urmatoare indiferent. Gap-urile ramase sunt notate in review checklist.

---

### FAZA 5: Cross-Verification (Haiku)

**Scop:** Compara afirmatiile din discovery cu datele reale din findings.

**Logica:** Identica cu v5. Compara claim-uri cantitative (%, luni, doze) cu findings authority >= 3. Clasifica: VERIFIED / CONTRADICTED / UNVERIFIED. Contradictiile prefera finding-ul cu authority mai mare.

**Output:** Raport formatat, feed-ul la guide generation.

**Failover:** Daca esueaza, se continua fara cross-verification (cu log warning). Ghidul se genereaza dar cu disclaimer in review.

**Checkpoint:** Cross-verification report salvat.

---

### FAZA 6: Guide Generation (Haiku + Sonnet ptr sectiuni critice)

**Scop:** Genereaza ghidul master in format markdown.

**Schimbare majora:** Sectiunile ghidului sunt derivate din lifecycle, nu din categorii abstracte.

### Template-ul ghidului (OBLIGATORIU -- toate sectiunile in aceasta ordine)

```
# {Diagnostic} -- Ghid Complet pentru Pacienti

**Generat:** {data}
**Findings analizate:** {numar}
**Surse principale:** {top 5 domenii}
**Ultima actualizare:** {data}

---

## INAINTE DE TOATE

Daca tocmai ai aflat diagnosticul, e normal sa fii coplesit.
Nu trebuie sa citesti tot acum. Iata ce ai nevoie sa stii IMEDIAT:

**Ce ai:** {1-2 propozitii -- ce este boala, in termeni simpli}
**Exista tratament:** {Da/Nu + ce tratament, concret}
**Cat de serios este:** {Prognostic REAL cu numere -- nu vag, nu fals optimist}
**Ce faci ACUM:** Citeste Sectiunea 3 (ce sa eviti) si Sectiunea 4 (cum iei tratamentul).
Restul vine cand esti gata. Ai timp. Informatia nu dispare.

---

## 1. CE AI -- INTELEGEREA DIAGNOSTICULUI TAU [Q1]
Ce inseamna exact acest diagnostic. Cum se confirma (teste moleculare).
Ce inseamna staging-ul. Subtipuri si de ce conteaza.
Prognostic REAL cu numere, nu vague.

## 2. CEL MAI BUN TRATAMENT ACUM [Q2]
Ce e aprobat. Care e prima linie. ESMO vs NCCN.
Tabel: tratament | linie | ORR% | PFS luni | OS luni | sursa
Imunoterapia: cand da, cand nu.
Head-to-head daca exista.
Cand datele sunt contradictorii: prezinta range-ul cu sursele.
  Ex: "PFS 22-25 luni (LIBRETTO-431: 24.8 [[Finding N](URL)]; real-world: 22.0 [[Finding M](URL)])"
  NU ascunde contradictia -- pacientul merita sa stie.

## 3. CE SA NU FACI -- GRESELI CARE TE POT COSTA [Q7]  <<< PRIORITATE INALTA
FORMAT OBLIGATORIU per greseala:
  GRESEALA: {ce fac pacientii gresit}
  DE CE E PERICULOS: {consecinta concreta}
  CE SA FACI IN SCHIMB: {alternativa corecta}
Include: interactiuni periculoase, suplimente contraindicate,
mituri, oprirea tratamentului, ignorarea semnelor.

## 4. CUM SA IAI TRATAMENTUL CORECT [Q3 - dozare]
Per drug aprobat:
  Doza, timing, cu/fara mancare, interactiune pH/PPI/lactate.
  Tabel: situatie | ce faci | de ce conteaza

## 5. EFECTE SECUNDARE -- PROBABILITATI REALE [Q3 - side effects]  <<< CRITICAL (Sonnet)
Per drug aprobat:
  Tabel: efect | frecventa % | grad | ce faci
  Include efecte sub-raportate (hiperglicemie, QTc, gust alterat)
  Management practic per efect major.

## 6. INTERACTIUNI MEDICAMENTE SI ALIMENTE [Q3 - interactions]
Tabel: medicament/aliment | efect | actiune
"NICIODATA cu X", "ia cu 2h inainte de Y"
Suplimente, OTC, remedii naturale.
CYP profil explicat pe inteles.

## 7. CE MONITORIZARE TREBUIE [Q3 - monitoring]
Tabel: test | frecventa | de ce | ce urmaresti
Ce sa ceri daca medicul nu propune.
ECG, ficat, glicemie, tiroidia, tensiune, creatinina.
Include: liquid biopsy / ctDNA daca sunt relevante ptr monitorizarea
raspunsului si detectarea precoce a progresiei la acest diagnostic.

## 8. CAND MERGI LA URGENTE -- ACUM [Q3 - emergency]  <<< CRITICAL (Sonnet)
Checklist PRINTABIL. Format checkbox:
  - [ ] Simptom -> Actiune imediata
Bold, clar, fara ambiguitate.
"Printeaza aceasta pagina si pune-o pe frigider."

## 9. UNDE SE RASPANDESTE SI CE FACI [Q4]
Per fiecare site comun de metastaza:
  Frecventa (% pacienti). Cum se detecteaza.
  Tratament standard. Optiuni locale (SBRT, chirurgie, ablatie).
  Terapie suportiva specifica.
Daca discovery-ul determina ca un cancer NU metastazeaza frecvent
(ex: early-stage cu cura chirurgicala), aceasta sectiune se marcheaza:
  "Nu se aplica frecvent pentru acest diagnostic. Discuta cu oncologul daca apar simptome noi."

## 10. CAND TRATAMENTUL NU MAI MERGE [Q5]  <<< CRITICAL (Sonnet)
Cum se dezvolta rezistenta. Cat de repede (mediana).
Mecanisme SPECIFICE pe NUME.
Plan B, C, D -- CONCRET cu date.
Re-biopsie: cand, ce cauti.
"Ai nevoie de plan INAINTE sa ai nevoie de el."
Daca nu exista rezistenta (ex: chirurgie curativa), se marcheaza:
  "Tratamentul pentru acest diagnostic este de obicei definitiv. Monitorizarea dupa tratament este descrisa in Sectiunea 7."

## 11. CE VINE -- PIPELINE SI TRIALURI [Q6]
Per drug in dezvoltare:
  Tabel: drug | faza | mecanism | timeline | targeteaza rezistenta?
Trialuri clinice ACTIVE cu NCT, locatii, eligibilitate.
Speranta realista, nu hype.
Include terapii tumor-agnostic daca sunt relevante (ex: aprobari basket trial).

## 12. VIATA DE ZI CU ZI [Q3 - daily life]
Nutritie (specific, evidence-based). Exercitii fizice.
Oboseala -- managementul ei. Munca, calatorii, relatii.
Suport psihologic. Sexualitate si fertilitate.
Timeline realist: Saptamana 1-2, Luna 1-3, Luna 3-12, Anul 1-2.

## 13. ACCES LA TRATAMENT [Q3 - access + Q9]
Per tara europeana majora: cum obtii tratamentul.
Ordonanta prezidentiala (Romania). ATU (Franta).
Hartefallprogramm (Germania). NHS Cancer Drugs Fund (UK).
Compassionate use (EMA). Cross-border healthcare directive.
Programe de asistenta financiara (Eli Lilly, etc.)

## 14. NU ESTI SINGUR [Q8]
Comunitati de pacienti specifice diagnosticului (cu link-uri).
Experienta reala a altor pacienti.
Suport caregiver.
Organizatii si resurse.

## 15. CE SA INTREBI MEDICUL [din Q1-Q8]
Intrebari concrete per etapa:
  La diagnostic: {5 intrebari}
  La inceputul tratamentului: {5 intrebari}
  La progresie: {5 intrebari}
Context ptr fiecare (de ce conteaza).

## 16. GHIDURI INTERNATIONALE [Q2 - guidelines detail]
ESMO vs NCCN -- diferente explicite.
EMA approvals vs FDA.
Disponibilitate per tara.
```

**Total: 16 sectiuni** (nu 18). Fostele sectiuni 16 (Instrumente monitorizare) si 17 (Peisaj larg) au fost absorbite: liquid biopsy in Sectiunea 7, conferinte/inovatii in Sectiunea 11 doar daca sunt relevante direct. Conform P1 din vision.md: informatia serveste supravietuirea, nu curiozitatea.

### Sectiuni optionale
Daca discovery-ul (Faza 1) determina ca un lifecycle stage nu se aplica pentru un diagnostic (ex: nu exista rezistenta la chirurgie curativa, nu sunt metastaze frecvente), sectiunea se marcheaza cu explicatie scurta in loc sa fie omisa. Pacientul trebuie sa stie DE CE nu se aplica, nu doar sa constate ca lipseste.

### Sectiuni CRITICE (folosesc Sonnet):
- Sectiunea 3: Greseli (informatie gresita aici = pacient se pune in pericol)
- Sectiunea 5: Efecte secundare (greseli = pacient nepregatiit)
- Sectiunea 8: Urgente (semne de alarma gresite = pericol direct)
- Sectiunea 10: Rezistenta (Plan B lipsa = pacient fara optiuni)

### Sectiunea 3 (Greseli) se valideaza cu prioritate MAXIMA de advocate. Daca exista o singura informatie incorecta in aceasta sectiune, ghidul PICA integral validarea. Motivul: un pacient care evita gresit ceva inofensiv pierde calitate a vietii; un pacient care NU evita ceva periculos isi risca viata.

**Generare:**
1. Pass 1 (Haiku): Plan -- mapeaza findings pe 16 sectiuni
2. Pass 2 (per sectiune): Genereaza fiecare sectiune independent
   - Sectiuni critice: Sonnet
   - Restul: Haiku
3. Asamblare in ghid complet

**Failover:** Daca o sectiune esueaza, se re-incearca o data. Daca tot esueaza, se genereaza placeholder: "[Sectiunea {N} nu a putut fi generata -- necesita re-run]". Celelalte sectiuni NU sunt afectate.

**Checkpoint:** Fiecare sectiune generata se salveaza individual. La re-run se regenereaza doar sectiunile lipsa/esuate.

**GATE 6:** Ghidul generat are min 10KB. Toate 16 sectiunile sunt prezente (chiar daca unele sunt placeholder sau marcate "nu se aplica"). Sectiunea "INAINTE DE TOATE" (executive summary) este prezenta si raspunde la cele 4 intrebari imediate.

---

### FAZA 7: Validare (multi-layer, multi-round)

**Scop:** Verifica ghidul din 6 perspective: acuratete medicala, completitudine, siguranta, claritate, calitate redactionala, experienta pacientului.

Validarea ruleaza ca o serie de LAYER-uri. Fiecare layer produce issues. Issues-urile se rezolva prin auto-corectie (patches), apoi se re-ruleaza layer-urile care au picat. Max 2 runde complete.

#### Layer 1: Structural QA (zero AI cost -- programatic)

Verificari automate pe textul markdown al ghidului. NU consuma tokeni API.

```
CHECK                           | REGULA                                  | FAIL =
────────────────────────────────|─────────────────────────────────────────|────────
Sectiuni prezente               | Toate 16 sectiunile + INAINTE DE TOATE  | BLOCK
Sectiuni min length             | Critice (3,5,8,10): >= 500 words        | BLOCK
                                | Restul: >= 200 words                    |
                                | INAINTE DE TOATE: 100-250 words         |
Sectiuni max length             | Nicio sectiune > 3000 words             | WARN
Tabel obligatoriu               | Sect 2: tabel tratament|linie|ORR|PFS   | BLOCK
                                | Sect 5: tabel efect|%|grad|actiune      |
                                | Sect 6: tabel medicament|efect|actiune   |
                                | Sect 7: tabel test|frecventa|de ce       |
                                | Sect 11: tabel drug|faza|mecanism        |
Format checkbox                 | Sect 8: contine "- [ ]" (min 5)        | BLOCK
Citari                          | Fiecare sectiune are min 1 citare       | WARN
                                | Format: [[Finding N](URL)]              |
                                | Nicio citare cu URL gol sau placeholder  |
Paragrafe                       | Niciun paragraf > 5 randuri             | WARN
                                | (se calculeaza split pe "\n\n")          |
Headings                        | Sectiunile folosesc ## ptr titlu        | WARN
                                | Sub-sectiunile folosesc ###             |
                                | Nu exista #### sau mai profund           |
Formatare interzisa             | Nu contine emojis                       | BLOCK
                                | Nu contine tipographic quotes (curly)    |
                                | Nu contine em-dash (—)                   |
Deduplicare intra-document      | Nicio propozitie identica (>15 words)   | WARN
                                | apare in 2+ sectiuni diferite            |
URL-uri unice                   | Niciun URL citat in >3 sectiuni diferite| WARN
```

**BLOCK** = pipeline-ul nu trece la Layer 2 pana nu se rezolva (auto-fix sau re-generare sectiune).
**WARN** = se noteaza in review checklist, nu blocheaza.

**Auto-fix ptr BLOCK structural:**
- Sectiune lipsa -> se re-genereaza doar acea sectiune (Faza 6 per-section)
- Sectiune prea scurta -> se re-genereaza cu prompt care cere min N words
- Tabel lipsa -> se re-genereaza sectiunea cu prompt explicit: "TREBUIE sa contina tabel cu coloanele: ..."
- Emojis / curly quotes / em-dash -> find/replace automat (programatic, zero cost)

#### Layer 1b: Section brief adherence (Haiku, ~$0.02)

Verifica ca FIECARE sectiune livreaza ce promite. Problema reala: AI-ul genereaza text care "suna bine" dar deviaza de la scopul sectiunii -- Sectiunea 3 ("Ce sa nu faci") devine sfaturi generice in loc de greseli concrete; Sectiunea 8 ("Urgente") devine lista de side effects in loc de checklist printabil.

**Haiku primeste fiecare sectiune + brief-ul ei din template si raporteaza:**

```json
{
  "section_adherence": [
    {"section": 3, "score": 6, "pass": false,
     "brief": "GRESELI: format GRESEALA/DE CE/ALTERNATIVA",
     "issue": "Section contains general advice ('eat healthy', 'exercise') instead of specific mistakes. Only 2 of 8 items use the MISTAKE/WHY/ALTERNATIVE format.",
     "fix": "Regenerate with explicit instruction: each item MUST follow format: GRESEALA: {ce fac gresit} / DE CE: {consecinta} / IN SCHIMB: {alternativa}"},
    {"section": 8, "score": 9, "pass": true,
     "brief": "URGENTE: checklist printabil cu checkbox",
     "issue": null, "fix": null},
    {"section": 12, "score": 5, "pass": false,
     "brief": "VIATA DE ZI CU ZI: nutritie, exercitii, oboseala, munca, calatorii",
     "issue": "Section covers only nutrition and exercise. Missing: work/travel restrictions, psychological support, sexuality/fertility, realistic timeline (week 1-2, month 1-3, etc.)",
     "fix": "Regenerate with all subtopics listed explicitly in prompt"}
  ]
}
```

**Section briefs** (ce trebuie sa contina fiecare sectiune -- referinta ptr Haiku):

```
Sect  1: Diagnostic explicat pe inteles + teste + staging + prognostic cu numere
Sect  2: Tabel comparativ tratamente cu ORR/PFS/OS + ghiduri ESMO/NCCN
Sect  3: Min 8 greseli in format GRESEALA/DE CE E PERICULOS/CE SA FACI IN SCHIMB
Sect  4: Per drug: doza, timing, mancare, pH, PPI -- tabel practic
Sect  5: Per drug: tabel side effects cu frecventa %, grad, actiune
Sect  6: Tabel interactiuni (medicamente, alimente, suplimente) cu actiune
Sect  7: Tabel monitorizare (test, frecventa, de ce) + liquid biopsy daca relevant
Sect  8: Min 5 checkbox-uri PRINTABILE: simptom -> actiune imediata
Sect  9: Per site metastaza: frecventa %, tratament, optiuni locale
Sect 10: Mecanisme rezistenta PE NUME + Plan B/C/D CONCRET + re-biopsie
Sect 11: Tabel pipeline drugs (drug, faza, mecanism, timeline) + trialuri active NCT
Sect 12: Nutritie + exercitii + oboseala + munca + calatorii + psihologic + fertilitate + timeline realist
Sect 13: Per tara: mecanisme legale de acces (ordonanta, ATU, etc.) + asistenta financiara
Sect 14: Comunitati SPECIFICE diagnosticului cu link-uri + povesti pacienti + suport caregiver
Sect 15: Min 5 intrebari per etapa (diagnostic, tratament, progresie) cu context
Sect 16: Diferente ESMO/NCCN explicite + disponibilitate per tara
```

**Scoring:** Fiecare sectiune primeste scor 1-10 pe aderenta la brief.
- **>= 8**: PASS
- **6-7**: WARN -- se noteaza in checklist, nu blocheaza
- **< 6**: BLOCK -- sectiunea se REGENEREAZA cu prompt-ul care include brief-ul ca instructiune explicita

**Auto-fix:** Regenerarea include brief-ul ca cerinta in system prompt: "Aceasta sectiune TREBUIE sa contina: {brief}. Formatul OBLIGATORIU este: {format}."

**Cost:** ~$0.02 (un singur Haiku call cu toate 16 sectiunile).

#### Layer 2: Language & Tone check (Haiku)

Verifica ca ghidul respecta regulile de ton din Sectiunea 6b a spec-ului.

**Haiku primeste ghidul complet + regulile de ton si raporteaza:**

```json
{
  "language_issues": [
    {"find": "text non-English", "replace": "English version", "language": "ro"}
  ],
  "tone_issues": [
    {"section": 5, "issue": "Uses passive voice: 'treatment should be administered'",
     "suggestion": "Change to direct: 'Take your medication...'"},
    {"section": 1, "issue": "Paragraph too clinical: 'adenocarcinoma histology confirmed via...'",
     "suggestion": "Simplify: 'Your biopsy confirmed a type of lung cancer called adenocarcinoma'"}
  ],
  "clarity_issues": [
    {"section": 10, "issue": "Term 'solvent front mutation' used without explanation",
     "suggestion": "Add: '(a specific change in the drug target that prevents the drug from binding)'"},
    {"section": 6, "issue": "CYP3A4 mentioned 8 times without re-explaining",
     "suggestion": "Explain at first use, then use 'liver enzyme (CYP3A4)' for next 2, then just 'CYP3A4'"}
  ],
  "jargon_unexplained": ["PFS", "ORR", "BBB", "MET amplification"]
}
```

**Reguli de ton verificate:**
- Adresare directa ("tu", "tratamentul tau") -- nu "pacientul", nu pasiv
- Termeni medicali explicati la prima utilizare in paranteze
- Niciun paragraf > 4 randuri
- Bold pe cifre cheie si avertismente
- Ton cald dar onest -- nu "prognostic favorabil" ci numere reale
- Nicio propozitie condescendenta ("nu va faceti griji", "totul va fi bine")

**Auto-fix:** language_issues -> find/replace direct. tone_issues + clarity_issues -> patch-uri sugerate, aplicate automat daca sunt find/replace clar. jargon_unexplained -> se adauga explicatii la prima aparitie.

#### Layer 3: Consistency check (Haiku)

Verifica ca informatiile din ghid NU se contrazic intre sectiuni.

**Haiku primeste ghidul complet si raporteaza:**

```json
{
  "contradictions": [
    {"sections": [2, 10], "issue": "Section 2 says PFS=24.8 months, Section 10 says 'resistance develops around 22 months'",
     "resolution": "Use consistent number with source: 'median PFS 24.8 months (LIBRETTO-431)'"}
  ],
  "duplications": [
    {"sections": [4, 6], "issue": "PPI interaction described in both sections with slightly different wording",
     "resolution": "Keep detailed version in Section 6 (Interactions), reference it from Section 4: 'See Section 6 for PPI rules'"}
  ],
  "cross_references_missing": [
    {"from_section": 5, "to_section": 8, "issue": "Side effect 'severe hepatotoxicity' mentioned but not linked to Emergency section"}
  ]
}
```

**Reguli:**
- Niciun numar (%, luni, doze) nu apare cu valori diferite in sectiuni diferite
- Daca aceeasi informatie e relevanta in 2+ sectiuni: versiune detaliata in sectiunea principala + referinta scurta ("Vezi Sectiunea N") in celelalte
- Efecte secundare severe din Sectiunea 5 TREBUIE sa aiba corespondent in Sectiunea 8 (Urgente)
- Drugs din Sectiunea 10 (Plan B) TREBUIE sa apara si in Sectiunea 11 (Pipeline) daca sunt inca in trial

**Auto-fix:** Contradictions -> se corecteaza in sectiunea cu authority mai mic. Duplications -> se inlocuieste cu referinta. Cross-references -> se adauga.

#### Layer 4: Medical review (Sonnet) -- existent, pastrat

**Oncologist review:**
- Acuratete factuala: numere (ORR%, PFS, frecvente side effects) corecte per knowledge map si findings
- Completitudine: drugs, trials, side effects lipsa?
- Siguranta: poate vreo afirmatie duce la decizii daunatoare?
- Output: overall (ACCURATE/NEEDS CORRECTION/POTENTIALLY HARMFUL), accuracy_issues, safety_concerns

#### Layer 5: Patient experience review (Sonnet) -- existent, extins

**Advocate review** cu scoring extins. Primeste ghidul complet si evalueaza:

**Per sectiune (1-10):**
- **Relevanta:** Informatia ajuta pacientul sa ia decizii mai bune? (P1 din vision.md)
- **Claritate:** Un pacient fara background medical intelege ce citeste?
- **Actionabilitate:** Pacientul stie CE SA FACA dupa ce citeste? (nu doar ce exista)
- **Completitudine:** Lipseste ceva ce un pacient ar VREA sa stie?

**Global (verificari suplimentare noi):**
- **First-read test:** Primele 500 cuvinte raspund la "Ce am? Exista tratament? Cat de serios? Ce fac ACUM?"
- **Scare test:** Ghidul sperie pacientul nejustificat? Sau il calmeaza fals?
- **Actionability test:** Fiecare sectiune se termina cu cel putin 1 actiune concreta (nu doar informatie)
- **Progression test:** Un pacient la progresie gaseste Plan B in max 30 secunde de scan?
- **Ce lipseste:** Missing keywords -> queries tintite ptr sectiunile slabe

**Threshold:** TOATE sectiunile >= 8.5 SI global tests PASS.

#### Ordinea layer-urilor si flow-ul

```
Layer 1  (Structural QA)          -- zero cost, fix automat
    |
    v  (trece daca 0 BLOCKs)
Layer 1b (Section brief adherence) -- Haiku, ~$0.02, regenereaza sectiuni < 6
    |
    v  (sectiuni regenerate daca needed)
Layer 2  (Language & Tone)         -- Haiku, ~$0.02
    |
    v  (patch-uri aplicate)
Layer 3  (Consistency)             -- Haiku, ~$0.02
    |
    v  (patch-uri aplicate)
Layer 4  (Medical review)          -- Sonnet, ~$0.15
    |
    v  (medical patches aplicate daca needed)
Layer 5  (Patient experience)      -- Sonnet, ~$0.15
    |
    v  (scor per sectiune)
    |
    +---> Daca TOATE PASS: GATE 7 TRECUT
    |
    +---> Daca issues: auto-corectie + re-run layer-urile care au picat
          (max 2 runde complete)
```

**Cost total validare:** ~$0.37 per runda (Layers 1-5). Max 2 runde = ~$0.74.

**Reguli speciale (pastrate):**
- Sectiunea 3 (Greseli): ORICE informatie incorecta = ghidul pica integral (severity CRITICAL)
- Sectiunea 5 (Side effects): Trebuie sa aiba tabel cu % -- fara tabel = pica (Layer 1 BLOCK)
- Sectiunea 8 (Urgente): Trebuie sa aiba format checkbox -- fara checkbox = pica (Layer 1 BLOCK)
- Sectiunea 10 (Rezistenta): Trebuie sa aiba min 1 Plan B concret -- fara = pica (Layer 5)

**Missing keywords (Layer 5):** Daca advocate-ul identifica lipsuri, se genereaza queries tintite, se cauta, se regenereaza DOAR sectiunile afectate (nu tot ghidul). Apoi se re-ruleaza Layer 1-5 pe sectiunile regenerate.

**Failover:** Daca Sonnet esueaza la Layer 4 sau 5, se salveaza ghidul cu disclaimer "[Nevalidat medical / de experienta pacient -- necesita review manual]". Layers 1-3 (structural, tone, consistency) sunt obligatorii si ruleaza chiar daca Sonnet nu e disponibil.

**Checkpoint:** Validation report salvat dupa fiecare layer. Ghid text salvat dupa fiecare runda de patches.

**GATE 7:**
- Layer 1: 0 BLOCKs
- Layer 2: 0 language issues ramase, 0 tone issues critice
- Layer 3: 0 contradictions
- Layer 4: overall = ACCURATE, 0 safety concerns
- Layer 5: TOATE sectiunile >= 8.5, global tests PASS
Daca nu trece dupa 2 runde: se genereaza review checklist cu TOATE problemele nerezolvate. Status: `guide_ready` (nu `validated`). Omul decide.

---

### FAZA 8: Human Review Checklist + Skill Self-Improvement

1. Genereaza checklist markdown cu: safety concerns, accuracy issues, cross-verification discrepancies, section scores, human review questions
2. Append learnings la skills (vezi sectiunea 5b mai jos)
3. Actualizeaza status in registry.yaml: researching -> guide_ready

---

## 5b. Skills -- definitii, utilizare, auto-invatare

### Inventar skills: ce pastram, ce modificam, ce eliminam

Exista 9 skills in `.claude/skills/`. Evaluare per skill:

| Skill | Linii | Scor actual | Decizie | Motiv |
|-------|-------|-------------|---------|-------|
| `/oncologist` | 164 | 8/10 | **MODIFICA** | Excelent pe fond. Trebuie adaptat ptr 16 sectiuni lifecycle + Q1-Q8. Learnings (22 puncte) se pastreaza integral. |
| `/patient-advocate` | 204 | 8/10 | **MODIFICA** | Cel mai bun skill. First-read test si patient journey checklist sunt exemplare. Trebuie adaptat ptr 16 sectiuni + section briefs. Learnings se pastreaza. |
| `/research` | 270 | 5/10 | **RESCRIE** | Descrie pipeline-ul v4, complet depasit de spec-ul v6. Trebuie rescris integral cu fazele 0-8, monitoring, seed, lifecycle. |
| `/monthly-review` | 38 | 4/10 | **ABSOARBE in /research** | Monitoring mode din spec inlocuieste aceasta functionalitate. Se documenteaza ca sub-sectiune in `/research`. Se sterge fisierul. |
| `/new-topic` | 47 | 5/10 | **EXTINDE** | Prea scurt. Trebuie sa ghideze definirea diagnosticului ptr lifecycle Q1-Q8, nu doar id/title/section. |
| `/publish` | 53 | 7/10 | **PASTREAZA** | Functional, clar. Minor: adauga verificare ca ghidul a trecut GATE 7 inainte de publicare. |
| `/frontend` | 44 | 7/10 | **PASTREAZA** | Nu e afectat de pipeline changes. Adecvat ptr review CSS/HTML. |
| `/ux` | 54 | 6/10 | **EXTINDE** | Bun ptr site Hugo. Lipseste: evaluare UX a ghidului generat (structura, scanability, progressive disclosure). |
| `/seo` | 57 | 7/10 | **PASTREAZA** | Functional, clar. Nu e afectat de pipeline changes. |

**Skills dupa modificari: 8 total** (monthly-review absorbit in research)

### Definitii detaliate per skill modificat

#### `/oncologist` -- Medical Accuracy Reviewer

**Cand se foloseste:**
- **In pipeline (automat):** Layer 4 al validarii (Faza 7). Oncologist review Sonnet. Learnings din skill sunt incluse in system prompt.
- **Manual:** `/oncologist data/guides/lung-ret-fusion.md` -- review complet al ghidului de un om

**Ce verifica (adaptat ptr lifecycle):**

Per lifecycle stage Q1-Q8, oncologistul verifica:
- **Q1:** Testele moleculare sunt CORECTE si COMPLETE? Staging-ul e explicat corect?
- **Q2:** Toate drug-urile aprobate listate? ORR/PFS/OS numere corecte vs trials? ESMO vs NCCN diferente corecte?
- **Q3:** Dozare corecta per drug? Side effects cu % corecte? CYP profil corect? Monitorizare conform ghiduri? Semne urgente complete?
- **Q4:** Site-urile de metastaza sunt cele mai frecvente? Frecventele (%) sunt corecte? Tratamentele sunt standard of care?
- **Q5:** Mecanismele de rezistenta sunt pe NUME si corecte? Plan B/C/D exista si este realist?
- **Q6:** Fiecare drug in pipeline e la faza corecta? NCT numbers sunt corecte?
- **Q7:** Greselile sunt REALE (nu inventate)? Consecintele sunt corecte? Alternativele sunt sigure?
- **Q8:** Comunitatile exista si URL-urile functioneaza?

**Output:** Severity per issue (CRITICAL/MAJOR/MINOR), overall verdict (ACCURATE/NEEDS CORRECTION/POTENTIALLY HARMFUL), safety concerns list.

**Learnings format:**
```
## Learnings
- [RET-NSCLC] Pralsetinib retras din UE (Oct 2024) -- verifica MEREU statusul EMA
- [RET-NSCLC] KIF5B-RET median OS 47.6 luni vs CCDC6-RET 37.2 luni -- diferenta semnificativa
- [GENERAL] PPI reduce absorbtia TKI pH-dependenti -- verifica MEREU interactiunea PPI per drug
```

Prefixul `[TOPIC]` sau `[GENERAL]` indica daca learning-ul e specific unui diagnostic sau aplicabil universal.

#### `/patient-advocate` -- Patient Experience Reviewer

**Cand se foloseste:**
- **In pipeline (automat):** Layer 5 al validarii (Faza 7). Advocate review Sonnet. Learnings din skill sunt incluse in system prompt.
- **Manual:** `/patient-advocate data/guides/lung-ret-fusion.md` -- review complet

**Ce verifica (adaptat ptr lifecycle):**

1. **First-read test** (primele 500 cuvinte):
   - "Ce am?" raspuns clar in primele 2 paragrafe?
   - "Exista tratament?" drug NUMIT in primele 500 cuvinte?
   - "Cat de serios?" prognostic REAL cu numere?
   - "Ce fac ACUM?" actiune concreta?

2. **Section brief adherence** (fiecare din 16 sectiuni):
   - Livreaza ce promite titlul?
   - Contine formatele obligatorii (tabele, checkboxuri)?
   - Se termina cu actiune concreta?

3. **Lifecycle completeness** (per Q1-Q8):
   - Un pacient gaseste raspuns la FIECARE intrebare din lifecycle?
   - Lipseste ceva ce un pacient ar VREA sa stie?

4. **Scare/hope calibration:**
   - Ghidul sperie nejustificat?
   - Ghidul da speranta falsa?
   - Numerele sunt prezentate IN CONTEXT (nu doar "mediana 24 luni" ci "asta inseamna ca jumatate din pacienti depasesc 24 luni")?

5. **Progression test:**
   - Un pacient la progresie gaseste Plan B in max 30 secunde de scan?
   - Sectiunile 10 si 11 sunt usor de gasit din cuprins?

6. **Caregiver test:**
   - Un partener/parinte/copil poate citi ghidul si intelege situatia?
   - Exista resurse specifice ptr caregiver?

**Output:** Scor per sectiune 1-10, global tests PASS/FAIL, missing keywords, priority issues (SAFETY > TREATMENT > ACCESS > QoL > TONE).

#### `/research` -- Pipeline Coordinator (RESCRIS)

**Cand se foloseste:**
- **Automat:** Orchestreaza pipeline-ul fazele 0-8 + monitoring + seed
- **Manual:** `/research lung-ret-fusion` sau `/research --monitor lung-ret-fusion`

**Continut (ce trebuie documentat in skill):**
- Pipeline v6: 9 faze (0-8) + monitoring (M0-M6) + seed
- Pre-run checklist: env, API keys, DB, topic, budget, checkpoint resume
- Lifecycle Q1-Q8 framework (referinta la SPEC.md sectiunea 4)
- Post-run report format (dashboard-ul din observabilitate)
- Troubleshooting: budget exceeded, non-convergence, validation failed, no findings, guide too small, API down
- CLI quick reference: --topic, --monitor, --monitor-all, --seed, --reclassify, --dry-run, --mock, --force-phase, --rollback, --list-alerts, --ack-alert, --save-fixtures

#### `/new-topic` -- Topic Planner (EXTINS)

**Cand se foloseste:** Manual, cand utilizatorul vrea sa adauge un diagnostic nou

**Ce trebuie definit ptr un topic nou:**
1. **Diagnosticul precis** (subtip molecular, nu generic): "EGFR exon 19 deletion NSCLC", nu "lung cancer"
2. **Verificare duplicat:** exista deja in registry?
3. **Lifecycle preview** (Haiku, ~$0.01): genereaza un preview rapid Q1-Q8 -- ce drugs, ce metastaze, ce rezistenta -- ptr a valida ca topic-ul e suficient de specific
4. **Registry entry** cu toate campurile
5. **Recomandare seed:** exista date in alte DB-uri ptr acest topic?
6. **Prioritizare:** unde se incadreaza fata de topic-urile existente?

#### `/ux` -- Guide & Site UX Reviewer (EXTINS)

**Cand se foloseste:** Manual, review UX al ghidului SAU al site-ului

**Extindere: evaluare UX ghid generat** (nu doar site Hugo):
- **Progressive disclosure:** Ghidul are "INAINTE DE TOATE" care orienteaza rapid?
- **Scanability:** Un pacient care cauta "ce sa nu fac cu grapefruit" gaseste in 10 secunde?
- **Information density:** Nicio sectiune nu e "wall of text"?
- **Cross-referencing:** Sectiunile isi refera una pe alta unde e relevant? ("Vezi Sectiunea 8 ptr semne de alarma")
- **Print-friendliness:** Sectiunea 8 (Urgente) este printabila ca pagina separata?

### Auto-invatare -- cum devin agentii mai buni

#### Mecanismul existent (se pastreaza si se imbunatateste)

`skill_improver.py` (existent) face append la `.claude/skills/oncologist.md` si `patient-advocate.md` dupa fiecare validation run. Asta functioneaza -- cele 22 learnings din RET fusion sunt valoroase.

**Probleme cu mecanismul actual:**
1. Learnings-urile se ACUMULEAZA fara limita -- dupa 50 topic-uri, sectiunea va avea 500+ linii
2. Learnings sunt identice intre oncologist si patient-advocate -- nu sunt diferentiate
3. Nu exista mecanism de PRUNING (stergere learnings gresite sau depasite)
4. Learnings nu sunt CATEGORIZATE (specific topic vs general)
5. Nu exista mecanism de SHARING intre topic-uri (ce s-a invatat la RET se aplica si la EGFR?)
6. Un agent nou (context fresh) nu stie CE SA CITEASCA INTAI

#### Mecanismul nou

**1. Learnings diferentiate per skill:**

`/oncologist` primeste learnings de tip MEDICAL:
```
## Learnings
### General (aplicabil la orice diagnostic)
- PPI reduce absorbtia TKI pH-dependenti -- verifica MEREU interactiunea PPI per drug
- Surse cu authority < 3 nu sunt suficiente ptr claims de eficacitate (ORR/PFS)
- Brain metastasis frequency trebuie MEREU verificata -- AI-ul tinde sa subestimeze

### Per topic
#### lung-ret-fusion
- Pralsetinib retras din UE (Oct 2024)
- KIF5B-RET vs CCDC6-RET survival difference semnificativa
- Immunotherapy nu functioneaza la RET+ (TMB scazut)
#### lung-egfr (dupa ce se cerceteaza)
- Osimertinib T790M second-line standard
- ...
```

`/patient-advocate` primeste learnings de tip EXPERIENTA PACIENT:
```
## Learnings
### General
- Pacientii vor sa stie "cat timp am?" in primele 30 secunde -- MEREU inclus in executive summary
- Sectiunea de fertilitate/sexualitate e MEREU trunchiata de AI -- monitorizare explicita
- Timeline realist (luna 1-3, luna 3-12) reduce anxietatea concret -- MEREU inclus

### Per topic
#### lung-ret-fusion
- Pacientii RET+ sunt frecvent never-smokers -- sectiunea demographics sa reflecte asta (reduce stigma)
- "Right to Try" legea americana trebuie mentionata ptr pipeline drugs
```

**2. Pruning automat:**

Dupa fiecare 5 runs ptr un topic, se ruleaza un PRUNING pass (Haiku, ~$0.01):
- Citeste toate learnings-urile
- Elimina: duplicate, learnings contrazise de date mai noi, learnings prea vagi ("be more specific")
- Marcheaza: learnings confirmate de 3+ runs -> promoveaza la "General"
- Output: learnings list curatata, log cu ce s-a sters si de ce

**3. Cross-topic sharing:**

Cand un learning e marcat `[GENERAL]`, se copiaza automat in skill-urile tuturor topic-urilor. Mecanism:
- La inceputul unui research run ptr un topic NOU, se citesc learnings `[GENERAL]` din TOATE topic-urile deja cercetate
- Se adauga in system prompt-ul oncologistului/advocate-ului ca "prior knowledge from other cancer types"
- Exemplu: "La RET+ am invatat ca PPI reduce absorbtia TKI pH-dependenti -- verifica daca se aplica si la EGFR"

**4. Rapid onboarding -- cum un agent fresh devine eficient**

Un agent nou (Claude in context nou) care primeste task pe OncoGuide trebuie sa fie productiv in <60 secunde. Mecanismul:

**Ordinea de citire (OBLIGATORIE, documentata in CLAUDE.md):**
```
1. vision.md           -- DE CE existam (30s)
2. SPEC.md sectiunea 2 -- principiul fundamental (10s)
3. SPEC.md sectiunea 4 -- lifecycle Q1-Q8 (60s)
4. CLAUDE.md           -- cum functioneaza proiectul (2min)
5. Skill-ul relevant   -- daca ruleaza pipeline: /research
                       -- daca revizuieste ghid: /oncologist + /patient-advocate
                       -- daca publica: /publish
6. Learnings-urile relevante din skill (sectiunea ## Learnings)
```

**Context bootstrap automat:**
La inceputul fiecarui run de pipeline, `run_research.py` genereaza un **context brief** de max 500 cuvinte care contine:
- Diagnosticul
- Cate findings exista in DB ptr acest topic
- Ultimul run (data, scor, issues nerezolvate)
- Top 5 learnings relevante (din skills)
- Alertele neacknowledged (daca exista)

Acest brief se injecteaza in system prompt-ul fiecarui agent (oncologist, advocate, keyword extractor) ca "Prior context -- ce s-a intamplat pana acum".

**5. Feedback loop explicit:**

Dupa fiecare run, pipeline-ul intreaba:
```
[LEARNING] Ce a mers bine si ce a mers prost in acest run?
```
Haiku analizeaza: validation report + issues gasite + patches aplicate + sectiuni regenerate si extrage 1-3 learnings NOI ptr fiecare skill. Se adauga automat.

**Daca omul corecteaza manual ghidul** (dupa human review), la urmatorul run pipeline-ul compara versiunea corectata cu versiunea generata si extrage learnings din diferente:
```
[LEARNING from human correction] Omul a schimbat "prognostic favorabil" in "mediana 47.6 luni"
-> Learning: NU folosi "prognostic favorabil" -- scrie MEREU numarul exact
```

---

## 6. Monitoring mode (rulare periodica)

**Scop:** Detecteaza schimbari si actualizeaza ghidul incremental, fara regenerare completa.

**Trigger:** `python run_research.py --monitor --topic "lung-ret-fusion" --since 7d`

**Logica simplificata (7 faze):**

**M0** -- Genereaza 30-50 queries din: diagnosticul din registry + entitati numite din ghidul existent (drugs, trials, mutations). Template-uri + Haiku complement. Cost: ~$0.02.

**M1** -- Executa pe 5 backend-uri, dedup vs DB existent. Cost: $0.

**M2** -- Enrichment Haiku batch. Cost: ~$0.05-0.15.

**M3** -- Change detection: Haiku analizeaza findings-urile noi si clasifica:
  - `safety` (label change, withdrawal, new adverse event) -> severity critical/major
  - `approval` (new drug approved for this diagnosis) -> severity major
  - `trial` (new trial recruiting) -> severity major
  - `resistance` (new mechanism or next-gen drug data) -> severity major
  - `guideline` (ESMO/NCCN update) -> severity major
  - `info` (new review, conference abstract) -> severity minor

**M4** -- Technology tracker: match findings noi la entitati urmarite din ghid. Genereaza update-uri datate. Auto-discovery: identifica entitati NOI care nu sunt in ghid.

**M5** -- Monitoring report markdown: alerts + new findings summary + technology updates + active trials.

**M6** -- Update ghid: adauga linii datate la sectiunile relevante (fara regenerare completa). Format: `**{data}**: {update text} [[Finding N](URL)]`

**Cost per run:** $0.15-0.30 per topic.

**Alert output:** CLI print cu severity coloring. Alertele sunt salvate in DB.

---

## 6b. Tonul ghidului -- cerinte obligatorii

Ghidul este scris de un **pacient informat care a trecut prin asta**, nu de un manual medical. Tonul trebuie sa respecte P6 din vision.md: "cald, direct, fara condescendenta".

**Reguli de ton:**
- **Adreseaza-te direct**: "tu", "tratamentul tau", nu "pacientul"
- **Recunoaste emotia fara sa te opresti la ea**: "E normal sa fii speriat cand citesti numere. Dar numerele astea sunt mai bune decat ai crede -- citeste mai departe."
- **Fii onest, nu optimist fals**: Numere reale, nu "prognostic favorabil". Daca mediana PFS e 24 luni, scrie 24 luni, nu "raspuns durabil".
- **Fii practic, nu teoretic**: "Pune pastila langa paharul de apa de dimineata" nu "se recomanda administrarea matinala"
- **Explica termenii la prima utilizare**: "PFS (progression-free survival -- cat timp trece pana cand boala se agraveaza)"
- **Paragrafe scurte**: Max 4 randuri. Daca depasesti, sparge in doua.
- **Bold ptr ce conteaza**: Cifrele cheie, avertismentele, actiunile.
- **Fara emojis, fara simboluri speciale**: Standard quotes (""), double hyphens (--), **bold** ptr emphasis. Conform D4 din content-strategy.md.
- **Tabele ptr comparatii**: Orice data comparativa (drugs, side effects, trials) in format tabel, nu proza.
- **Fiecare afirmatie cu numar = citare**: `[[Finding N](URL)]`. Fara numere neverificabile.

**Regula contradictiilor:**
Cand sursele ofera date diferite (ex: ORR 83% vs 85%), ghidul prezinta range-ul cu ambele surse:
"ORR 83-85% (LIBRETTO-001: 85% [[F12](url1)]; real-world Japan: 83% [[F45](url2)])"
NU se alege o singura valoare. Pacientul merita transparenta.

---

## 6c. Publication pipeline -- cum ajunge ghidul la pacient

Ghidul master (output Faza 6-7) este un document markdown intern. Calatoria pana la pacient:

```
Guide markdown (guide_ready)
  |
  v
Human review (citeste ghidul, verifica safety concerns din checklist)
  |
  v
Status: guide_ready -> drafting
  |
  v
Redactare articol Hugo in limba romana (content/ro/cancer-types/{slug}.md)
  - Adapteaza din guide markdown
  - Adauga shortcodes: {{< disclaimer >}}, {{< action-box >}}, {{< callout >}}
  - Respecta conventiile editoriale din CLAUDE.md
  |
  v
Traducere in 5 limbi (en, it, fr, de, es) cu translationKey identic
  |
  v
Publish checklist (/publish skill)
  |
  v
Git push -> GitHub Actions -> live pe oncoguide.github.io
  |
  v
Status: published
```

**Alertele de monitoring** ajung la pacient prin:
1. **Sectiunea "Ultima actualizare" din articolul Hugo** -- se actualizeaza la fiecare monitoring run cu schimbari relevante
2. **RSS feed** (Hugo genereaza automat) -- pacientii pot urmari update-uri
3. **Future (Faza 8 din PLAN.md):** Newsletter Buttondown -- push notifications

---

## 7. Ce se pastreaza din implementarea curenta

### Cod reutilizat integral:
- `modules/database.py` -- se extinde cu tabele noi (`pipeline_state`, `monitor_runs`, `alerts`, `tracked_technologies`), nu se rescrie
- `modules/searcher_serper.py`, `searcher_pubmed.py`, `searcher_clinicaltrials.py`, `searcher_openfda.py`, `searcher_civic.py` -- neschimbate
- `modules/enrichment.py` -- minor: primeste lifecycle_stage tag
- `modules/cost_tracker.py` -- neschimbat
- `modules/utils.py` -- neschimbat
- `modules/cross_verify.py` -- neschimbat
- `modules/skill_improver.py` -- neschimbat

### Cod modificat semnificativ:
- `modules/discovery.py` -- oncologistul raspunde la Q1-Q8 structurat (nu free-form knowledge map)
- `modules/keyword_extractor.py` -- queries generate per lifecycle stage cu cerinte minime
- `modules/guide_generator.py` -- 16 sectiuni lifecycle (template-ul din spec), GUIDE_SECTIONS redefinit
- `modules/gap_analyzer.py` -- gap analysis per lifecycle stage, nu per sectiune
- `modules/validation.py` -- 16 sectiuni, reguli speciale ptr sectiunile 3, 5, 8, 10
- `modules/pre_search.py` -- template-uri actualizate per lifecycle (Q1-Q9)
- `run_research.py` -- add --monitor mode

### Cod nou:
- `modules/monitor.py` -- orchestrator monitoring (M0-M6)
- `modules/monitor_queries.py` -- query generation ptr monitoring
- `modules/change_detector.py` -- clasificarea schimbarilor
- `modules/living_guide.py` -- technology tracking + guide patching

### Skills reutilizate:
- `.claude/skills/oncologist.md` -- se pastreaza cu learnings-urile existente
- `.claude/skills/patient-advocate.md` -- se pastreaza cu learnings-urile existente
- `.claude/skills/research.md` -- se actualizeaza cu monitoring mode
- `.claude/skills/publish.md`, `frontend.md`, `ux.md`, `seo.md` -- neschimbate

### Decizii pastreate:
- Toate deciziile din `decisions/log.yaml` raman valide
- Pattern editorial "Ce sa NU faci" devine Sectiunea 3 (promovata ca prioritate)
- Format: fara emojis, fara simboluri speciale, bold ptr emphasis
- Multilingual: Romanian first, apoi 5 limbi
- Hugo + PaperMod + GitHub Pages -- neschimbat

---

## 8. Metrici de succes

### Per ghid generat:
- Scor validare advocate >= 8.5 pe TOATE 16 sectiunile
- 0 safety concerns
- Min 200 findings relevante
- Cost < $5
- Toate 16 sectiunile prezente si non-triviale (>200 cuvinte fiecare, >500 ptr sectiuni critice)
- Sectiunea "INAINTE DE TOATE" raspunde la cele 4 intrebari imediate
- Nicio contradictie de date ascunsa -- toate range-urile prezentate cu ambele surse

### Per monitoring run:
- Toate alerts-urile detectate sunt actionate (verificate de om)
- Cost < $0.50 per topic
- Ghidul actualizat in < 5 minute

### Calitate ghid (perspectiva pacient):
- Un pacient nou diagnosticat gaseste raspuns la "Ce am?" in primele 500 cuvinte
- Un pacient in tratament gaseste "Ce sa nu fac" in Sectiunea 3
- Un pacient la progresie gaseste Plan B concret in Sectiunea 10
- Fiecare afirmatie cu numere are citare catre sursa
- Nicio informatie care poate duce la decizii daunatoare

---

## 9. Ordinea de implementare recomandata

1. **Template ghid (Sectiunea 6)** -- defineste output-ul final; tot restul il serveste
2. **Discovery restructurat (Faza 1)** -- Q1-Q8 structurat
3. **Query generation (Faza 2)** -- per lifecycle stage cu minime
4. **Pre-search actualizat (Faza 0)** -- template-uri noi
5. **Gap analysis (Faza 4)** -- per lifecycle stage
6. **Guide generation (Faza 6)** -- 16 sectiuni lifecycle + executive summary
7. **Validation (Faza 7)** -- reguli noi ptr sectiunile critice
8. **Monitoring mode (Sectiunea 6 spec)** -- dupa ce research mode functioneaza
9. **Integrare end-to-end** -- test pe lung-ret-fusion

---

## 10. Decizii de implementare -- ce NU trebuie ghicit

Aceasta sectiune elimina ambiguitatile din spec. Un agent de implementare trebuie sa gaseasca aici raspunsul la orice intrebare de tip "dar cum exact?".

### 10.1 Lifecycle stage vs guide section -- mapping-ul exact

Q1-Q9 sunt intrebari de research. Sectiunile 1-16 sunt output de ghid. Mapping-ul NU este 1:1.
Un finding tagat cu lifecycle_stage la search time poate ajunge in mai multe sectiuni.

```
Q1 (Diagnostic)        -> Sectiunea 1 (Ce ai)
Q2 (Tratament)         -> Sectiunea 2 (Cel mai bun tratament) + Sectiunea 16 (Ghiduri internationale)
Q3 (Cum traiesti)      -> Sectiunile 4, 5, 6, 7, 8, 12 (dozare, side effects, interactiuni, monitorizare, urgente, viata zilnica)
Q4 (Metastaze)         -> Sectiunea 9 (Unde se raspandeste)
Q5 (Rezistenta)        -> Sectiunea 10 (Cand nu mai merge)
Q6 (Pipeline)          -> Sectiunea 11 (Ce vine)
Q7 (Greseli)           -> Sectiunea 3 (Ce sa nu faci)
Q8 (Comunitate)        -> Sectiunea 14 (Nu esti singur)
Q9 (Acces geographic)  -> Sectiunea 13 (Acces la tratament)
Transversal            -> Sectiunea 15 (Ce sa intrebi medicul) -- derivat din TOATE Q1-Q8
```

**Cine face sub-clasificarea Q3?** Q3 produce findings despre side effects, interactiuni, dozare, monitorizare, urgente, nutritie. Clasificarea in sub-sectiuni se face in **Faza 6 Pass 1** (section planner, Haiku): "Acest finding despre CYP3A4 merge in Sectiunea 6 (Interactiuni), nu in Sectiunea 5 (Side effects)." Planner-ul primeste lista de 16 sectiuni cu descrierile lor si distribuie findings-urile.

### 10.2 Enrichment output schema

Enrichment-ul (Haiku) produce pentru fiecare finding:

```json
{
  "relevant": true,
  "lifecycle_stage": "Q3",
  "relevance_score": 9,
  "authority_score": 4,
  "title_english": "...",
  "summary_english": "..."
}
```

**lifecycle_stage** este NOU fata de v5. Inlocuieste topic_id-ul generic. Se foloseste la gap analysis (Faza 4) pentru a numara findings per stage.

**NU se clasifica in guide sections la enrichment.** Clasificarea in sectiuni (4, 5, 6, 7...) se face DOAR in Faza 6 Pass 1 (section planner). Motivul: enrichment-ul proceseaza sute de findings rapid -- nu are context suficient ptr a decide "side effect vs interaction". Section planner-ul vede TOATE findings-urile si decide holistic.

**DB storage:** Coloana `lifecycle_stage TEXT` se adauga la tabela `findings` (ALTER TABLE migration). Valorile: Q1, Q2, Q3, Q4, Q5, Q6, Q7, Q8, Q9. Findings-urile pre-existente (din v5) au lifecycle_stage = NULL.

### 10.3 Discovery tool schemas (exact)

Oncologistul raspunde folosind tool use cu acest schema:

```json
{
  "name": "submit_lifecycle_knowledge",
  "parameters": {
    "Q1_diagnostic": {
      "molecular_tests": [{"test": "NGS", "panel": "FoundationOne CDx", "turnaround_days": 14}],
      "staging": "TNM system, stage I-IV",
      "subtypes": [{"name": "KIF5B-RET", "frequency_percent": 70, "clinical_significance": "..."}]
    },
    "Q2_treatment": {
      "approved_drugs": [
        {"generic": "selpercatinib", "brand": "Retevmo", "manufacturer": "Eli Lilly",
         "status_fda": "approved", "status_ema": "approved", "line": "first-line",
         "approval_date": "2024-02", "withdrawn": false,
         "key_trials": ["LIBRETTO-431", "LIBRETTO-001"]}
      ],
      "guidelines": {"esmo": "...", "nccn": "...", "differences": "..."},
      "immunotherapy_role": "..."
    },
    "Q3_living": {
      "per_drug": [
        {"drug": "selpercatinib",
         "dosing": {"dose": "160mg BID", "weight_based": true, "food": "with food", "ppi_interaction": "-69% AUC if fasting"},
         "cyp_profile": {"inhibits": ["CYP3A4"], "substrates": [], "key_interactions": ["grapefruit", "St John's Wort"]},
         "side_effects": [{"name": "hepatotoxicity", "percentage": 59, "grade": "any"}, ...],
         "monitoring": [{"test": "LFT", "frequency": "monthly first 3 months", "why": "hepatotoxicity"}]}
      ],
      "emergency_signs": ["jaundice", "syncope", "dyspnea", "hemiparesis"],
      "nutrition": "...",
      "access": {"romania": "ordonanta prezidentiala", "france": "ATU", "germany": "Hartefallprogramm"}
    },
    "Q4_metastases": {
      "sites": [
        {"site": "brain", "frequency_percent": 25, "detection": "MRI",
         "systemic_treatment": "selpercatinib penetrates BBB",
         "local_options": ["SRS", "WBRT"], "supportive": "dexamethasone if symptomatic"}
      ]
    },
    "Q5_resistance": {
      "mechanisms": [
        {"type": "on-target", "name": "G810R", "frequency": "most common solvent front"},
        {"type": "bypass", "name": "MET amplification", "frequency": "10-15%"}
      ],
      "median_time_months": 24,
      "next_line": [{"drug": "EP0031", "evidence": "Phase II, active vs G810"}, ...]
    },
    "Q6_pipeline": {
      "drugs": [
        {"name": "EP0031", "code": "lunbotinib", "manufacturer": "Ellipses Pharma",
         "phase": "Phase II", "mechanism": "next-gen selective RET",
         "targets_resistance": true, "trial_nct": "NCT05443126"}
      ],
      "novel_modalities": [{"name": "RET PROTACs", "status": "preclinical"}, ...]
    },
    "Q7_mistakes": {
      "items": [
        {"mistake": "Taking grapefruit with selpercatinib",
         "why_dangerous": "CYP3A4 inhibition increases drug levels, toxicity risk",
         "alternative": "Avoid grapefruit entirely; use other citrus fruits"}
      ]
    },
    "Q8_community": {
      "resources": [
        {"name": "RETpositive.org", "url": "https://retpositive.org", "type": "patient community"}
      ]
    }
  }
}
```

Advocate-ul raspunde cu:

```json
{
  "name": "submit_lifecycle_evaluation",
  "parameters": {
    "scores": {
      "Q1": {"score": 9.0, "assessment": "Complete molecular testing, staging clear"},
      "Q2": {"score": 8.5, "assessment": "Both drugs covered, guidelines present"},
      ...
    },
    "all_satisfied": false,
    "questions": ["Q3 is missing monitoring frequency for thyroid function", "Q6 is missing BYS10"]
  }
}
```

### 10.4 "INAINTE DE TOATE" -- cum se genereaza

Sectiunea "INAINTE DE TOATE" (executive summary) se genereaza DUPA toate celelalte 16 sectiuni, nu inainte. Motivul: are nevoie de informatii din sectiunile 1-3 pentru a raspunde la cele 4 intrebari.

**Model:** Haiku (nu e safety-critical -- e un summary, nu informatie noua)
**Input:** Sectiunile 1, 2, 3 generate + diagnosticul
**Prompt:** "Esti un pacient care tocmai a aflat diagnosticul. Raspunde in MAX 200 cuvinte la: Ce am? Exista tratament? Cat de serios? Ce fac ACUM? Tonul: cald, direct, fara condescendenta. Include un mesaj de orientare emotionala (1 propozitie)."
**Validare:** Advocate-ul verifica ca cele 4 intrebari au raspuns concret (nu vag). Nu primeste scor separat -- e parte din evaluarea globala.

### 10.5 Validare esec -- ce se intampla exact

Cand validarea PICA (scor < 8.5 pe o sectiune SAU safety concern):

**Runda 1:**
1. Language check (Haiku) -- patch-uri find/replace
2. Medical corrections (Sonnet) -- patch-uri find/replace ptr accuracy issues
3. Daca sectiuni specifice au scor < 8.5 si advocate identifica missing keywords:
   a. Se genereaza 3-5 queries ptr keywords-urile lipsa
   b. Se executa search + enrichment DOAR ptr acele queries
   c. Se REGENEREAZA doar sectiunile afectate (nu tot ghidul)
4. Re-validare

**Runda 2 (identica cu runda 1, daca tot nu trece):**
- Dupa runda 2, daca tot nu trece:
  - Se salveaza ghidul AS IS
  - Se genereaza review checklist cu TOATE problemele nerezolvate
  - Status: `guide_ready` (nu `validated`)
  - Se logheaza: `[WARNING] Guide did not pass validation after 2 rounds. Score: X/10. Y safety concerns. Human review required.`
  - Pipeline-ul se OPRESTE (nu continua la publicare)

**Caz special -- Sectiunea 3 (Greseli) cu informatie gresita:**
- Daca oncologist review gaseste informatie factuala incorecta in Sectiunea 3 (ex: "grapefruit e OK cu selpercatinib"):
  - Severity: CRITICAL
  - Se REGENEREAZA Sectiunea 3 complet cu Sonnet (nu patch)
  - Se re-valideaza DOAR Sectiunea 3
  - Daca tot e gresita: ghidul pica integral, se logheaza, omul decide

### 10.6 Drugs multipe -- regula de prioritizare

Unele diagnostice au 10+ drugs aprobate. Regula:

**Deep dive complet (sectiuni 4-8):** Drugs de prima linie + a doua linie recomandate de ESMO/NCCN.
Daca sunt > 4 drugs in deep dive, oncologistul din discovery trebuie sa le prioritizeze explicit.

**Mentiune sumara:** Drugs de linii ulterioare, drugs retrase din piata (ex: pralsetinib in UE -- se mentioneaza ca RETRAS, nu se face deep dive pe dozare/efecte).

**Tabel comparativ:** Daca sunt 2-3 drugs de prima linie (ex: cancer cu mai multe optiuni echivalente), Sectiunea 2 contine tabel head-to-head obligatoriu.

### 10.7 Multilingual query selection

"Queries cheie din Q2, Q3, Q5 se traduc in min 12 limbi" -- concret:

**Se traduc (max 2 per stage per limba):**
- Q2: 1 query ptr drug principal + 1 ptr rezistenta/noua generatie
- Q3: 1 query ptr side effects drug principal
- Q5: 1 query ptr rezistenta

**NU se traduc:** Q1 (diagnostic -- termeni universali), Q7 (greseli -- prea specifice), Q8 (comunitate -- query-uri separate per limba, nu traduceri)

**Total multilingual:** ~4 queries x 12 limbi = ~48 queries multilingual adaugate la totalul din Q2.

### 10.8 Monitoring -- entity extraction si guide patching

**Entity extraction (la prima generare a ghidului):**
Dupa Faza 6 (guide generation), se ruleaza un Haiku call care extrage din ghidul generat:
```json
{
  "drugs_tracked": ["selpercatinib", "pralsetinib", "EP0031", "vepafestinib", ...],
  "mutations_tracked": ["G810R", "G810S", "V804L", "MET amplification", ...],
  "trials_tracked": ["LIBRETTO-431", "NCT05443126", ...],
  "metastasis_sites": ["brain", "bone", "liver", ...]
}
```
Se salveaza in tabela `tracked_technologies` (o inregistrare per entitate, cu aliases).

**Guide patching (la monitoring):**
1. Se identifica sectiunea relevanta din ghid prin mapping: drug -> sectiuni 2,4,5,6; mutation -> sectiunea 10; trial -> sectiunea 11
2. Se gaseste SFARSITUL sectiunii (prima linie care incepe cu `## ` urmatorul heading)
3. Se insereaza INAINTE de heading-ul urmator, cu format:
```
### Actualizari recente

**2026-03-18**: EP0031 Phase II results show 85% ORR in G810R-resistant patients [[Finding 2891](url)]
```
4. Daca subsectiunea "Actualizari recente" exista deja, se adauga la ea (append)

### 10.9 Alert classification -- logica de decizie

Change detector-ul (Haiku) primeste fiecare finding NOU si il clasifica folosind aceste reguli:

```
REGULI (in ordinea prioritatii):
1. Finding mentioneaza drug CURENT (din tracked) + "withdrawal" OR "recall" OR "contraindication" OR "black box"
   -> category: safety, severity: critical

2. Finding mentioneaza drug CURENT + "adverse event" OR "side effect" + authority >= 4
   -> category: safety, severity: major

3. Finding mentioneaza drug NOU aprobat ptr acest diagnostic + authority >= 3
   -> category: approval, severity: major

4. Finding de pe clinicaltrials.gov + status RECRUITING + conditia match diagnostic
   -> category: trial, severity: major

5. Finding mentioneaza mutatie NOUA de rezistenta (nu e in tracked) + authority >= 3
   -> category: resistance, severity: major

6. Finding mentioneaza "ESMO" OR "NCCN" + "guideline" OR "recommendation" + "update" OR year curent
   -> category: guideline, severity: major

7. Finding cu relevance >= 8 si authority >= 4 care nu se incadreaza in 1-6
   -> category: info, severity: minor

8. Orice altceva
   -> nu e alert, se stocheaza normal in DB
```

### 10.10 Database schema -- tabele noi (complet)

```sql
-- Starea pipeline-ului per topic (checkpoint/resume)
CREATE TABLE IF NOT EXISTS pipeline_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id TEXT NOT NULL,
    run_id INTEGER REFERENCES search_runs(id),
    phase INTEGER NOT NULL,          -- 0-8
    phase_name TEXT NOT NULL,         -- "pre_search", "discovery", etc.
    status TEXT NOT NULL,             -- "complete", "failed", "partial"
    output_ref TEXT,                  -- path la fisier output sau JSON blob
    cost_usd REAL DEFAULT 0,
    duration_seconds REAL DEFAULT 0,
    error_message TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_pipeline_state_topic ON pipeline_state(topic_id, phase);

-- Monitoring runs (separat de search_runs ptr claritate)
CREATE TABLE IF NOT EXISTS monitor_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date TEXT NOT NULL,
    topic_id TEXT NOT NULL,
    since_date TEXT,                  -- "--since 7d" resolved to date
    findings_scanned INTEGER DEFAULT 0,
    new_findings INTEGER DEFAULT 0,
    alerts_generated INTEGER DEFAULT 0,
    tech_updates INTEGER DEFAULT 0,
    new_techs_discovered INTEGER DEFAULT 0,
    cost_usd REAL DEFAULT 0,
    duration_seconds REAL DEFAULT 0
);

-- Alerte generate de monitoring
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    monitor_run_id INTEGER REFERENCES monitor_runs(id),
    topic_id TEXT NOT NULL,
    severity TEXT NOT NULL,           -- "critical", "major", "minor"
    category TEXT NOT NULL,           -- "safety", "approval", "trial", "resistance", "guideline", "info"
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    finding_ids TEXT,                 -- JSON array [123, 456]
    acknowledged INTEGER DEFAULT 0,
    acknowledged_at TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_alerts_topic ON alerts(topic_id, acknowledged);

-- Entitati urmarite per topic (populate dupa guide generation)
CREATE TABLE IF NOT EXISTS tracked_entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,        -- "drug", "mutation", "trial", "metastasis_site", "modality"
    canonical_name TEXT NOT NULL,
    aliases TEXT,                     -- JSON array ["Retevmo", "LOXO-292"]
    guide_sections TEXT,              -- JSON array [2, 4, 5, 6] -- in ce sectiuni apare
    last_updated TEXT,
    auto_discovered INTEGER DEFAULT 0,
    UNIQUE(topic_id, entity_type, canonical_name)
);

-- Arhiva findings vechi (data hygiene) -- schema identica cu findings
CREATE TABLE IF NOT EXISTS findings_archive (
    id INTEGER PRIMARY KEY,
    content_hash TEXT NOT NULL,
    topic_id TEXT NOT NULL,
    title_original TEXT,
    snippet_original TEXT,
    source_language TEXT,
    title_english TEXT,
    summary_english TEXT,
    relevance_score INTEGER,
    authority_score INTEGER DEFAULT 0,
    source_url TEXT,
    source_domain TEXT,
    source_platform TEXT,
    date_published TEXT,
    date_found TEXT,
    run_id INTEGER,
    lifecycle_stage TEXT,
    is_seeded INTEGER DEFAULT 0,
    seed_source TEXT,
    archived_at TEXT NOT NULL,
    archive_reason TEXT
);
```

**Migration:** Coloana noua pe findings:
```sql
ALTER TABLE findings ADD COLUMN lifecycle_stage TEXT;
-- Findings existente raman cu lifecycle_stage = NULL
```

### 10.11 Seed data -- importul din bazele de date existente

Pentru topic-ul `lung-ret-fusion` exista deja ~3454 findings unice in doua baze de date:

| Sursa | Findings | Overlap (URL) | Unique |
|-------|----------|---------------|--------|
| onco-blog `research.db` (topic: lung-ret-fusion) | 1037 | 260 | 777 |
| CNA `ret_findings_v3.db` | 2689 | 260 | 2417 |
| **Total unic combinat** | | | **3454** |

**Aceste date TREBUIE reutilizate.** Reprezinta luni de cautari si $10+ in API costs. A le ignora si a rula research de la zero ar fi risipa de resurse si timp.

**Comanda de import:** `python run_research.py --seed --topic "lung-ret-fusion"`

**Logica de seed (Faza -1, ruleaza O SINGURA DATA inainte de primul research run):**

1. **Import din onco-blog DB** (findings cu topic_id="lung-ret-fusion"):
   - Se copiaza direct: content_hash, title_original, snippet_original, source_language, title_english, summary_english, relevance_score, authority_score, source_url, source_domain, source_platform, date_published, date_found
   - lifecycle_stage = NULL (se reclasifica ulterior)
   - Se marcheaza: `is_seeded = 1, seed_source = "onco-blog"`
   - run_id = un search_run nou cu run_type = "seed_onco"

2. **Import din CNA DB** (toate findings-urile):
   - Mapping CNA section -> lifecycle_stage:
     ```
     my_treatment      -> Q2  (dar include si Q3 -- se reclasifica)
     resistance        -> Q5
     daily_life        -> Q3
     alerts_safety     -> Q3
     patient_community -> Q8
     research_pipeline -> Q6
     ```
   - Se copiaza: content_hash, title_original (din title_english daca lipseste), snippet_original, source_language, title_english, summary_english, source_url, source_domain, source_platform, date_published, date_found
   - relevance_score: se pastreaza (CNA si onco-blog folosesc aceeasi scala 1-10)
   - authority_score: CNA nu are acest camp -> se seteaza 0 (se recalculeaza la reclasificare)
   - Se marcheaza: `is_seeded = 1, seed_source = "cna"`
   - run_id = un search_run nou cu run_type = "seed_cna"
   - **Dedup:** Se verifica content_hash si source_url inainte de insert. Skip daca exista.

3. **Reclasificare (optional dar recomandat):** `python run_research.py --reclassify --topic "lung-ret-fusion"`
   - Ruleaza batch Haiku pe toate findings-urile cu lifecycle_stage = NULL sau cu authority_score = 0
   - Seteaza: lifecycle_stage (Q1-Q9) + authority_score (1-5) ptr cele care lipsesc
   - Cost: ~$0.30 ptr ~3500 findings (batch 5, Haiku)
   - Dupa reclasificare, gap analysis (Faza 4) poate identifica PRECIS ce lipseste per lifecycle stage

**De ce nu se reclasifica automat la seed?**
Seed-ul trebuie sa fie rapid si gratuit (zero API cost). Reclasificarea e optionala -- ghidul functioneaza si fara (section planner-ul distribuie findings pe baza continutului). Dar reclasificarea permite gap analysis precis si monitoring mai bun.

**Coloane noi pe findings (migration):**
```sql
ALTER TABLE findings ADD COLUMN lifecycle_stage TEXT;
ALTER TABLE findings ADD COLUMN is_seeded INTEGER DEFAULT 0;
ALTER TABLE findings ADD COLUMN seed_source TEXT;
```

**Nota:** Seed-ul se ruleaza O SINGURA DATA per topic. La re-run, `--seed` verifica daca exista deja un run cu run_type="seed_*" ptr acel topic si refuza sa re-importe (cu mesaj clar).

**Alte topic-uri:** Cand se va cerceta un topic NOU (ex: lung-egfr), NU exista seed data. Pipeline-ul porneste de la zero cu Faza 0 (pre-search). Seed-ul e relevant DOAR ptr topic-uri care au date istorice.

### 10.11b Existing data -- ce se intampla la deploy (fara seed)

Daca se alege sa NU se ruleze `--seed`:

1. **Findings existente din onco-blog raman in DB** dar nu au lifecycle_stage. Section planner le poate folosi la guide generation.
2. **Findings din CNA NU sunt disponibile** (sunt in alt DB). Se pierd ~2417 findings unice (inclusiv alerts_safety, daily_life, patient_community pe care onco-blog nu le are).
3. **Research run-ul va re-descoperi o parte** din ele prin search, dar nu pe toate.

**Recomandare:** Ruleaza `--seed` ptr lung-ret-fusion. Costul e zero (import) + $0.30 (reclasificare). Beneficiul: 3454 findings gata clasificate, pipeline-ul sare direct la Faza 4 (gap analysis) care identifica ce mai lipseste, in loc sa re-caute tot.

### 10.12 Model IDs exacte

```python
DISCOVERY_MODEL = "claude-sonnet-4-6"        # Sonnet ptr discovery + validation
CRITICAL_MODEL  = "claude-sonnet-4-6"        # Sonnet ptr sectiuni critice (3, 5, 8, 10)
DEFAULT_MODEL   = "claude-haiku-4-5-20251001" # Haiku ptr tot restul
```

Configurabile prin config.json (existent). Spec-ul NU dicteaza model IDs hardcoded -- se folosesc cele din config cu fallback la valorile de mai sus.

### 10.13 Concurrency

- **Research mode:** SECVENTIAL. O singura faza ruleaza la un moment dat. Motivul: fiecare faza depinde de output-ul precedentei.
- **Sectiuni guide (Faza 6 Pass 2):** Se pot genera IN PARALEL (max 4 concurrent, limitat de API rate). Fiecare sectiune e independenta.
- **Monitoring multiple topics:** Se pot rula SECVENTIAL prin `--monitor-all`. NU in paralel (risc de rate limit API + DB lock). Motivul: costul e mic ($0.20/topic), nu justifica complexitatea paralelismului.
- **Search queries (Faza 3):** Secventiale cu delay intre ele (existent: 3s Serper, 1s PubMed). NU in paralel -- API rate limits.

### 10.14 Content hash formula

```python
content_hash = SHA256(f"{topic_id}|{title.lower().strip()}|{url.lower().strip()}")
```

Identica cu formula existenta in onco-blog `utils.py`. La seed din CNA, se RECALCULEAZA hash-ul cu topic_id-ul onco-blog ("lung-ret-fusion"), nu cu cel CNA. Motivul: dedup-ul functioneaza per topic in onco-blog.

### 10.15 Section 15 (Ce sa intrebi medicul) -- model

Se genereaza cu **Haiku** (nu e safety-critical -- sunt intrebari sugerate, nu informatii medicale directe). Daca bugetul permite, se poate promova la Sonnet ca bonus.

### 10.16 Monitoring report template

Raportul de monitoring (`data/monitors/{topic_id}-{date}.md`) are aceasta structura:

```markdown
# Monitoring Report: {Diagnostic}
**Data:** {date}  **Since:** {since_date}  **Cost:** ${cost}

## Alerts
{per alert: severity badge + category + title + description + finding links}
{daca 0 alerts: "No alerts detected."}

## New Findings Summary
{count} new findings added ({per lifecycle stage: Q2: +5, Q3: +12, Q5: +3, ...})
Top 5 by relevance:
1. {title} (rel: {score}, auth: {auth}) -- {lifecycle_stage}
...

## Technology Tracker Updates
{per entity updated: "EP0031: Phase II results 85% ORR (was: Phase I ongoing)"}
{per entity newly discovered: "NEW: APS03118 (RET PROTAC, Phase I)"}

## Active Clinical Trials
{lista trials RECRUITING cu: NCT, phase, drug, locations, status}

## Guide Patches Applied
{lista sectiuni modificate cu ce s-a adaugat}
```

### 10.17 --monitor-all ordering

Topicurile se monitorizeaza in ordinea `priority` din `topics/registry.yaml` (0 = cea mai mare prioritate). La prioritate egala, se foloseste ordine alfabetica per topic_id. Doar topicurile cu status `guide_ready` sau `published` se monitorizeaza (nu `planned` sau `researching`).

### 10.18 Section 3 -- minimum greseli flexibil

Layer 1b cere "Min 8 greseli" ca default. Dar daca diagnosticul are mai putine greseli reale relevante:
- **Minimul absolut:** 4 greseli
- **Regula:** Toate greselile identificate in discovery Q7 + greselile descoperite in findings relevante. Daca totalul e < 4, se logheaza warning si se accepta (unele diagnostice au mai putine riscuri).
- Section brief-ul se actualizeaza: "Min {N} greseli" unde N = max(4, numar greseli din discovery Q7)

### 10.19 Q7 (Greseli) -- threshold actualizat

| Stage | Min queries | Min findings (relevance >= 7) |
|-------|-------------|-------------------------------|
| Q7 Greseli | **5** (nu 3) | **5** (nu 3) |

Motivul: Q7 alimenteaza Sectiunea 3 care e CRITICA. Cu 3 findings nu poti genera 4+ greseli cu surse. 5 queries pe interactiuni periculoase, mituri, erori frecvente sunt fezabile ptr orice diagnostic.

### 10.20 Section generation order (fost 10.14)

Sectiunile se genereaza in ordinea template-ului (1-16) cu o EXCEPTIE:
- **"INAINTE DE TOATE"** se genereaza ULTIMUL (dupa toate 16 sectiunile), deoarece e un summary.
- Sectiunile critice (3, 5, 8, 10) folosesc Sonnet; restul Haiku.
- Daca o sectiune esueaza, urmatoarele NU sunt blocate -- se continua.
- Se pot genera max 4 sectiuni Haiku in paralel (dar nu Sonnet -- prea scump sa ai 4 Sonnet calls simultane).

---

## 11. Glossar

- **Lifecycle stage**: Una din cele 9 intrebari (Q1-Q9) pe care pacientul le are
- **Named entity**: Un drug, mutatie, trial, site de metastaza sau organizatie mentionata pe NUME
- **Gate**: Punct de verificare obligatoriu intre faze. Daca nu trece, pipeline-ul se opreste sau degradeaza graceful.
- **Checkpoint**: Salvare stare in DB. Permite reluarea din punctul salvat la re-run.
- **Critical section**: Sectiune din ghid care foloseste Sonnet in loc de Haiku (3, 5, 8, 10).
- **Failover**: Mecanism de degradare gratiala cand o componenta esueaza.
- **Section brief**: Descrierea concisa a ce TREBUIE sa contina o sectiune (folosita de Layer 1b ptr validare aderenta).
- **Seed data**: Findings importate din baze de date externe (CNA, alte surse) ptr a evita re-search-ul de la zero.
- **Authority score**: 1-5, masoara calitatea sursei (5 = NEJM/Lancet/ESMO guideline).
