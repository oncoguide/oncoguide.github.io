---
title: "Personalized cancer vaccines"
date: 2026-07-22
draft: false
description: "The types of therapeutic vaccine, what worked and what did not in trials, the real limits, and the centres I found -- plus how I decide what fits me."
tags: ["cancer vaccine", "immunotherapy", "personalized medicine", "neoantigens", "dendritic cells", "mRNA", "peptide vaccines", "lung cancer", "RET", "gene fusion"]
categories: ["Blog"]
translationKey: "blog-cancer-vaccines-landscape"
weight: 40
author: "OncoGuide"
ShowToc: false
TocOpen: false
---

**In short:** I have spent the last few months reading, asking questions and writing to centres that make therapeutic cancer vaccines. This article is the map I wish I had had at the start: what types of vaccine exist and how they differ, what worked and what did not work in trials, what the real limits are, what the ideal vaccine for my case would look like -- and the list of centres I found, sorted by how well they fit **my biology**. It is written both for patients and for doctors or oncology navigators running into this subject for the first time.

---

## Why I came back to this subject

Last time I [wrote](/en/blog/standard-of-care-vs-personalized-medicine/) that I was looking into vaccines, but that I was not starting any of them for now. That position has changed.

The reason is simple, and it has to do with [the month 6 result](/en/blog/pet-ct-at-month-6/): I have very little disease, the treatment is holding, and I feel well. Immunologically, this is the best possible moment for a vaccine -- not one to postpone.

A personalized vaccine takes, in any case, between six months and a year until it is ready. If you start it when you need it, you have started too late.

So I am now treating it as an active direction, in parallel with the pill (which does not stop) and with radiotherapy. What follows is what I found out.

## What a therapeutic vaccine actually is

A therapeutic cancer vaccine does not prevent cancer. It is not like the flu shot.

It tries to teach your immune system to recognize tumour cells as foreign and to attack them. The idea is more than a century old. The hard part has always been the same: **what exactly do you show the immune system?**

The target is called an antigen. If the target also appears on healthy cells, either you do not attack, or you attack the healthy ones too. If the target appears only on some cancer cells, you kill those and the rest grow. A good vaccine stands or falls on the choice of target.

Remember this sentence, because it is the conclusion of the whole article: **it is not the technology that decides, it is the target.**

## The types of vaccine, briefly

I came across six families. I put them here with what matters in practice: how they work, what material they ask of you and how long they take.

**1. Off-the-shelf vaccines, on shared antigens.** Fixed peptides or proteins, which target markers present in many patients with the same type of cancer. They need nothing from you -- no biopsy, no sequencing. They are ready-made and cheap. The downside: they do not look at your tumour at all.

**2. Dendritic cell vaccines.** Dendritic cells are the "teachers" of the immune system. They are collected from your blood, matured in the lab, "loaded" with the tumour antigen, then given back. There is a subtlety here that took me time to understand and that changes everything: **what you load them with matters.** There are three variants:
   - with **lysate from your own tumour** -- you need viable, fresh tumour tissue;
   - with **defined peptides** -- you only need the sequence, not fresh tissue;
   - with **mRNA** -- again, sequence.

   So "dendritic cell vaccine" does **not** automatically mean "I need fresh tissue". Only some variants do. That confusion cost me weeks.

**3. Personalized mRNA vaccines on neoantigens.** Your tumour and a normal sample are sequenced, the tumour's unique mutations (neoantigens) are looked for, they are encoded into mRNA and packaged into lipid nanoparticles. A few weeks of manufacturing once the analysis is done.

**4. Personalized peptide vaccines.** The same discovery logic, but the final product is a chemically synthesized peptide plus an adjuvant -- a substance that wakes up the immune system. If the target is a single one and is already known, you only need the sequence.

**5. Viral vector vaccines.** A modified virus, unable to replicate, carries the instructions for your neoantigens.

**6. Dendritic cells primed with an oncolytic virus.** A virus that selectively destroys tumour cells releases the antigen, which then loads the dendritic cells. The mechanism needs **tumour mass to destroy**.

{{< callout type="tip" >}}
The two questions that quickly separate what fits you from what does not:

**1. What material does it need?** Fresh-frozen tissue? An archival paraffin block? Only blood? Only a sequence on paper?
**2. Is the target yours, or is it a shared one?** An off-the-shelf vaccine and one built on your tumour's mutations are fundamentally different things, even if both are called a "vaccine".
{{< /callout >}}

## What has worked and what has not, so far

Honesty is needed here, otherwise the article becomes an advertisement.

**The sobering part: in lung cancer, off-the-shelf vaccines have failed, consistently.** Large phase III trials, with thousands of patients: MAGRIT (on the MAGE-A3 antigen), START (tecemotide, on MUC1), STOP (belagenpumatucel-L), TG4010. All were safe. All produced a measurable immune response. **None of them clearly prolonged life.**

That is not a detail. It is the dominant pattern of the field in lung cancer, and anyone selling you enthusiasm without mentioning it is not telling you everything.

**And there are two more failures that concern me directly, because they hit exactly at my idea.**

The first: a vaccine built on **a single** marker invites the tumour to lose that marker. It was tested seriously, in a phase III trial with 745 patients, on an antigen called EGFRvIII. It failed -- no survival benefit. And at relapse, the antigen was missing in almost six out of ten patients. Not because the vaccine did not work, but **because it did work**: it cleared the cells that carried the marker, and the ones that did not carry it were left.

The second is even closer to my case. In an analysis published in 2025, a lung cancer patient on a targeted pill received a vaccine built on his clonal driver -- exactly the structure I am thinking of. **He progressed.** The targeted clone disappeared, but an older clone, which did not carry the vaccine's target, expanded in its place. And the disease transformed and lost the vaccine's targets. All of this while a real immune response was being measured in the blood.

{{< callout type="warning" >}}
The lesson I take from this, and which changed my own plan: **a measurable immune response does not mean disease control.** You can see the lymphocytes working and the disease advance anyway, because you trained the defence against a single thing, and the tumour is a population, not an individual.

That is why the vaccine I am looking for is no longer "one peptide on the junction", but **several targets at once** -- the junction, plus at least one anticipated resistance mutation, plus a target that recruits the helper cells.
{{< /callout >}}

**The encouraging part comes from the vaccines built on the patient's own target.**

In melanoma, a personalized mRNA vaccine combined with immunotherapy significantly reduced the risk of relapse after surgery, with the benefit maintained at a few years ([KEYNOTE-942](https://pubmed.ncbi.nlm.nih.gov/38246194/)). It is the best result in the whole class. But mind the context: melanoma has very many mutations, and the vaccine was given **together with** immunotherapy. Two things I do not have.

In resected pancreatic cancer, a personalized mRNA vaccine produced T cells that persisted for years in half of the patients -- and those patients did better.

And one result that interests me directly: a peptide vaccine built on **a single mutation of the KRAS gene** produced an immune response in the great majority of the patients treated and a drop in circulating tumour DNA in some of them, in a context with few mutations. That is exactly the demonstration I needed: **a single well-chosen target can be enough**, even when the tumour is "poor" in mutations.

{{< callout type="warning" >}}
A recap, because it is easy to lose: the platform (mRNA, peptide, dendritic cells) did not decide the results. **The target decided.** The vaccines on shared antigens failed one after another, whatever the technology. The ones built on something specific to that patient's tumour have started to show something.
{{< /callout >}}

## The real limits, in my case

Now the unpleasant part: most of these options do not fit me, and it is important that you understand why, because it may help you do your own triage.

**I have few mutations.** My tumour has a low tumour mutational burden. Classic personalized vaccines look for point mutations and build from them. In my case they find few, and most of them are too weakly represented to pass the technical thresholds. The raw material is thin.

**The tumour is immunologically "cold".** Low PD-L1, few mutations. And in RET fusion lung cancers, classic checkpoint immunotherapy works poorly -- response rates on the order of 6-17 per cent. That automatically rules out all the programmes that require, as a condition, a checkpoint inhibitor alongside the vaccine. Not because it would be dangerous, but because in my case it probably simply does not help.

**I have no fresh-frozen tissue, and nowhere to get it from.** I have never had surgery -- only a needle biopsy. And now, with such a deep response, I have no lesion worth biopsying. That closes off all the platforms that require fresh tissue.

**I only have paraffin blocks, in an unknown quantity.** Their quality is confirmed by the lab. **The quantity left, after the tests already done, has never been inventoried.** It is a distinction everyone confuses, myself included: "the tissue is good" and "I still have enough tissue" are two different things. I cannot promise any lab that I have enough material until someone counts.

**My HLA typing is incomplete.** HLA is a kind of immune fingerprint that decides which protein fragments can be shown to the defence system. Mine has only been determined at a coarse level, at two digits. The study that validates the target I am interested in works on a precise subtype, at four digits. Mine may be a different one -- and then the whole construction collapses.

{{< callout type="important" >}}
If you take a single practical idea from this article, take this one: **inventory your tissue and get your HLA typed at four digits early.** They are the cheapest tests in the whole chain, they are done once, and they decide whether the rest makes sense. I only discovered they were blocking after months of discussions with centres.
{{< /callout >}}

## What the ideal vaccine for me would look like

My tumour is defined by a fusion between two genes. The exact place where the two join -- the junction -- produces a sequence that **exists nowhere in the healthy body**.

It is the perfect target, in theory: it is specific to the tumour, it is present in practically every cancer cell, and it is kept even as the disease evolves, because it is the very engine of it. An ordinary vaccine, which looks for point mutations, would miss it completely.

So the ideal vaccine for me would have: the junction peptide as the main target, a few extra targets as a safety net, a strong adjuvant, and it would be given **alongside the targeted pill**, not instead of it.

Two construction details I found out late and that change a lot.

**The peptide has to be long, not short.** A short peptide, of eight to eleven "letters", sticks directly onto the surface of any cell and wakes up only the killer lymphocytes, without help -- and those get tired and can end up tolerating the target. A long peptide, of twenty-five to thirty-five letters, is too big to stick directly: it first has to be "chewed" by the dendritic cells, which then show it **both** to the killers **and** to the helper cells. The result is a stronger and more durable response. It is the school of Melief, at Leiden, who invented the concept.

**And it must not be a single target** -- for the reason told above. A vaccine on a single marker invites the tumour to lose that marker, and that has already happened, in real people, including in a case almost identical to mine. So: the junction as the anchor, plus a target that anticipates a known resistance mutation, plus one that recruits the helper cells.

There is one more step I would want done before any manufacturing: **confirmation that the junction really is displayed** naturally on the surface of the tumour cell, through direct analysis of the presented peptides. So far nobody has shown this for any RET junction.

**And here comes the asterisk I did not anticipate.**

Last time I wrote that the junction sequence can be read from the genetic tests I already have. That is true -- but it was not in the report. My report says which the two genes are, at a general level. **It does not say exactly where they join.**

The difference matters enormously: depending on the exact breakpoint, the left half of the peptide is an entirely different one. You cannot synthesize a peptide you cannot write down.

The good news: the lab that did the analysis used instruments that normally produce exactly those coordinates. **The data almost certainly exists already** -- it just did not make it into the clinical report. So I do not need a new test, I need a data request. I have sent it.

{{< callout type="warning" >}}
And a correction I owe my readers. In the previous article I wrote that checkpoint immunotherapy would be **risky** in my case, because of a genetic particularity (MDM2). I went back over the basis of that statement and **it does not hold up**: the evidence was thin, in a very small number of patients, not replicated. The real reason I avoid checkpoint immunotherapy is a different one, and a more mundane one: in RET fusion cancers it works poorly. It does not block a vaccine. I prefer to correct it rather than leave standing something that sounds convincing and is not.
{{< /callout >}}

There is one more thing I have to say about the study the whole idea leans on. In 2025 a paper was published showing that peptides built on this junction can be recognized by the immune system ([Castillo et al., 2025](https://pubmed.ncbi.nlm.nih.gov/41246330/)). It is encouraging. But it has four limits I am not allowed to hide:

1. it assumes a certain breakpoint -- mine is not yet known;
2. the demonstration was done on cells from healthy donors, with the peptide added artificially, not on a real tumour;
3. the validated HLA subtype is not confirmed in me;
4. when I ran the predictions myself on my own profile, the top-scoring peptide came out as **a different one** from the one validated in the paper.

There is nowhere in the literature the proof that such a junction is really displayed naturally on the surface of a tumour cell. It is a well-argued hypothesis, not a fact.

## Why Germany, and why the legislation matters

One thing I did not know at all: if you want a treatment built **specially for you**, outside a clinical trial, the question is not only who can manufacture it. It is where it is legal to give it to you.

In Europe, the only place where I found a mechanism that actually works in practice is **Germany**. The German medicines law allows a doctor to produce a preparation for a particular patient, without the full industrial authorization, under a formula called an "individual therapeutic trial". It is not a clinical trial: it has no mandatory ethics approval, no public registry. The liability is the doctor's.

There is also a second mechanism, European, not only German: the "hospital exemption", which allows a hospital to manufacture cell therapies for individual patients. On paper it exists across the whole Union. In practice, in other countries it is almost unused -- in Belgium, for example, it has been granted only once. Switzerland has no equivalent.

**And here is the paradox I did not anticipate.** German university hospitals **can** build personalized products -- some of them even have the best expertise in the world on exactly the type of vaccine I would need. But as a rule they offer it to you **only within a trial**. And a trial has fixed criteria: if your disease is not the one in the protocol, you do not get in, however well you fit biologically.

Which means that, in practice, the personalized product outside a trial comes rather from private clinics, for a fee -- not from the academic centre that invented it.

Outside Europe: **Japan** has its own law, from 2014, on the safety of regenerative medicine, which allows accredited clinics to legally offer autologous cell therapies to patients who pay. **Taiwan** has a similar framework, updated in 2024.

{{< callout type="important" >}}
A warning I keep repeating to myself: **a manufacturing licence is not proof of efficacy.** The fact that a clinic has the legal right to produce something says nothing about whether that something works. The same authorizations are held by serious academic centres and by commercial clinics alike. Check the mechanism and the evidence separately from the authorization.
{{< /callout >}}

## The centres I found

I want to be very clear about the criterion, because otherwise the list below can be read wrongly. **I am not splitting centres into good and bad. I am splitting them into fitting and not fitting for my biology.**

Every programme below is built seriously by serious people, and each one fits somebody. A tumour lysate vaccine is a reasonable choice for a patient who has just had surgery and has fresh tissue in abundance. For me, who do not have it, it is impossible to manufacture -- and that says nothing bad about it.

My filter has never been "it is paid for" or "it is not a clinical trial". If that had been the filter, the options I am pursuing now would have fallen too. **The filter is the mechanism fit.**

### Where the bottleneck actually is

This is the conclusion that changed how I search the most, and I wish I had had it from the start.

I started out asking "who can **manufacture** my vaccine". It is the wrong question. A long peptide built on my junction can be synthesized under pharmaceutical conditions, **directly from the sequence, without a single gram of tissue**, by almost a dozen specialized laboratories in Europe, Australia and the United States -- piCHEM in Austria, Mimotopes in Australia, Eurogentec in Belgium, Biosynth in the Netherlands and others. Synthesis is not the barrier. It is almost a commodity.

The barrier is who **formulates** the adjuvant, who **takes the liability** and who **administers** it -- as an individual treatment, without checkpoint immunotherapy bundled in. There is almost no place that does the whole chain end to end.

{{< callout type="important" >}}
If you are in my situation, look for **a willing doctor**, not another manufacturer. I lost weeks asking laboratories whether they could build something that, it turns out, almost all of them can build. The rare link is clinical, not chemical.
{{< /callout >}}

### Fitting for my profile

**CeCurio / CeGaT, Tübingen (Germany)** -- personalized peptide vaccine, derived from full sequencing of the tumour's exome **and transcriptome**. That last part matters: transcriptome analysis is what allows fusions to be detected, not just point mutations. From what I understood about their platform, a peptide built on a fusion junction can be included, provided it passes the usual filters for stability and for difference from the normal protein -- and they already have experience with peptides of this kind, which I have not found anywhere else. Nobody can promise in advance that a usable peptide will come out; that is only known after the analysis, and it seems scientifically honest to me for it to be said that way, not an evasion. Their constraint: they do not work with sequencing done elsewhere, they want their own data, so they need **tissue**.

What I have learned to ask for explicitly, in writing, from any supplier of this kind: (a) that they run fusion detection, not just the point mutation scan, and (b) that they include the peptide defined on my junction. A standard analysis, however well done, can walk right past exactly the thing that matters, because it was not asked to look for it.

**Dr. Morisaki's clinic, Fukuoka (Japan)** -- dendritic cell vaccine loaded with neoantigens, injected under ultrasound guidance directly into the lymph node. It accepts **tissue from paraffin blocks**, which for me is decisive. Fusion analysis is not part of their standard workflow -- as with most platforms, the search starts from point mutations -- but a junction can be assessed separately if the exact sequence is made available to them. That is exactly why the data request to the lab is on the critical path.

**ISEIKAI / meneki-clinic, Osaka (Japan)** -- dendritic cells again, but with a structural particularity I have not found anywhere else: **the peptides can be added individually**, as distinct line items. That is, a peptide built on my junction could go in separately, instead of the whole product having to be renegotiated. It is the only place where this lever seems to exist.

**Tübingen University Hospital, the academic team (Germany)** -- scientifically, the most experienced team in the world on vaccines built exactly on fusion junctions. They also have a real human precedent: a patient with another cancer also driven by a fusion, vaccinated on the junction, **without immunotherapy**, on top of his usual treatment, with no relapse at over twenty months. A single case, not a trial -- but exactly the structure I am looking for.

Their situation has a nuance I got wrong at first. They have **two** routes: a personalized one, which starts from direct analysis of the peptides displayed by the tumour and requires fresh-frozen tissue -- that one is closed to me. And one built **from sequence**, which requires no tissue at all. The problem with the second is not the material, but the catalogue: the junction they have built from so far is a different one from mine. So it is not a closed door, but a special request to be made.

### The builders in the United States

I discovered them late and I am sorry about it, because they change the calculation.

**The Gunaratne lab (University of Houston, with MD Anderson)** -- they are the ones who published exactly the KIF5B-RET junction science that my whole line of reasoning leans on. On paper it is the best fit in the world for my case: it targets exactly the junction, it is built from sequence, without checkpoint. The limit is brutally simple: their programme does not reach patients before 2027. For now, all I can do is exist on their list.

**Jaime Leandro Foundation, with Washington University (Saint Louis)** -- a non-profit foundation that coordinates, for each individual patient, a consortium: one lab does the genomic design, another synthesizes, and the patient's own treating doctor administers it through a US legal route for expanded access. **It accepts paraffin tissue, it is checkpoint-free, and it does not disqualify you if you are responding well to treatment** -- that is, it cuts exactly three of the barriers that block me elsewhere. The warning is the same as everywhere: their search also starts from the broad scan, so it could miss the junction if you do not explicitly ask for the defined peptide to be included.

**Houston Methodist, the RNA therapeutics programme (Cooke and Gollihar)** -- the only group I found that has **actually built** a personalized RNA vaccine for a single patient, as an act of compassion, and administered it. Without checkpoint, and it can encode the junction directly from sequence, so it does not even need my tissue. Availability for RET fusion lung cancer and the access conditions remain to be confirmed.

There is also a strategic move I am considering: at Johns Hopkins a trial is running that combines exactly a fusion peptide with a targeted pill, without checkpoint -- but for the ALK fusion. The natural question is whether they would extend it to a RET fusion. It costs nothing to ask.

**BNT116 (BioNTech)** -- an mRNA vaccine in clinical trials, which needs no tissue from you and can be combined with a targeted pill. The advantage: it is a real, open route. The limit: it targets **shared** antigens, not my junction. It is exactly the category I wrote about above as having failed repeatedly in lung cancer -- but it is open and accessible, which counts.

### Less fitting for me

I group them by the **reason** for the mismatch, not alphabetically. If you have a different diagnosis, chances are you will find yourself in one of the categories, even if the company names differ.

#### The ones that need tissue I do not have

**LANEX-DC (LDG Laboratories, Germany)** -- dendritic cells loaded with **lysate from your own tumour**. That is where the problem is, and it is purely mechanical: the lysate is made from viable tumour tissue. I only have formalin-fixed, paraffin-embedded tissue, which is not a functional source of lysate. The product simply **cannot be manufactured for me** -- and, on top of that, it does not look at the fusion that drives my disease. I have no doubt it is an option for patients in a different tissue situation.

**IOZK, Cologne (Germany)** -- here the dendritic cells are grown from your blood, but the antigen is produced **in the body**: an oncolytic virus plus targeted hyperthermia make the tumour cells die in a way the immune system notices. So the mechanism needs **tumour mass to work on**. In my case, precisely because the treatment has gone so well, I have almost nothing for it to work with. It is an approach designed for someone with visible disease -- I keep it as a reserve option if the situation changes.

**MIDRIXNEO, Ghent (Belgium)** -- dendritic cell vaccine loaded with neoantigen mRNA, a scientifically elegant construction. Three barriers: the trial is closed, it required fresh-frozen surgical tissue in large quantity, and RET fusions were explicitly excluded from the inclusion criteria.

#### The ones built on a target other than mine

**Moderna (United States)** -- two different products, unsuitable for different reasons. **mRNA-4157**, their personalized vaccine, is given in the lung programme **together with pembrolizumab** -- and checkpoint immunotherapy is the wrong backbone for my biology, with response rates on the order of 6-17 per cent in RET fusion cancers. **mRNA-4359** is, on the contrary, off-the-shelf: it encodes fragments of PD-L1 and IDO1, evasion mechanisms common to many tumours. It contains nothing from my fusion. They are the programmes with the most clinical experience in the class -- it is just that both are built around releasing the same immune brakes that, in my case, seem to matter little.

**ELI-002 (Elicio Therapeutics, United States)** -- here is an irony I prefer to point out myself. It is exactly the trial I cite above as being encouraging: the proof that **a single well-chosen target** can produce a durable immune response in a mutation-poor tumour. But ELI-002 is not personalized -- it is a **fixed** set of peptides built on mutations of the KRAS gene, and the confirmed driver in my case is a KIF5B::RET fusion. It validates my principle, but it is not my product.

#### The ones that look for point mutations, not junctions

**NeoVax (Dana-Farber, United States)** -- one of the most respected academic platforms for personalized peptide vaccines. Its method is to scan the tumour exome and build from the point mutations found there. It is excellent for mutation-rich tumours.

Mine has around four mutations per megabase, and the only strong target is a fusion junction -- exactly the kind of thing such a scan is not built to look for. Technically, the platform could synthesize my peptide if you gave it the sequence. It is just that this is not how it gets to the target, and that is a distinction that cost me a lot of time to understand.

### What makes a centre interesting for a case like mine

If you have a similar profile -- disease driven by a gene fusion, few mutations, low PD-L1, little disease and only archival tissue -- these are the questions that triaged my list most efficiently. You can use them as they are:

1. **Do you accept tissue from archived paraffin blocks, or do you require fresh-frozen tissue?** That one alone eliminates half the options.
2. **Does your analysis detect fusions, or only point mutations?** That is, do you also do the transcriptome, not just the exome?
3. **Can you include a peptide built on a fusion junction that I supply to you?**
4. **Does the product require a checkpoint inhibitor alongside it?** If so, in a fusion-driven cancer it is probably not for you.
5. **Do you require measurable disease?** A good response to treatment can disqualify you -- paradoxical, but real.
6. **What happens if the analysis finds nothing usable?** Do I get the data? Is there a stopping point before the expensive stage? Ask for the answer **in writing**, before any payment.
7. **Is the peptide long or short?** A peptide of twenty-five to thirty-five amino acids also recruits the helper cells; a short one does not.
8. **How many targets does the product have?** A single one invites the tumour to escape. Ask whether they can also include an anticipated resistance mutation.

And the two question-zeros, the ones I wish I had asked myself earlier: **how much tissue do I actually have left?** And, more important than all eight above: **who agrees to administer it to me?**

## We reason by analogy, because RET data does not exist

It has to be said plainly, because it is the foundation of the whole line of reasoning: **there is not a single RET fusion patient ever treated with such a vaccine.** Zero human data. Neither positive nor negative.

So everything I am doing is reasoning by analogy -- I learn from situations that biologically resemble mine. Concretely, I lean on three:

**The ALK fusion, in mice.** ALK is the close "cousin" of my case: also lung cancer, also driven by a fusion. A vaccine built on the fusion peptide, given together with the targeted pill, eradicated the tumours and prevented brain metastases in mice ([Mota et al., 2023](https://pubmed.ncbi.nlm.nih.gov/37430060/)). It is only an animal model -- but it is exactly the mechanism I would use. The idea has also reached a human clinical trial, [ARCHER](https://clinicaltrials.gov/study/NCT05950139), open to patients with ALK. Not to those with RET.

**One fusion, in one human being, in Germany.** In a rare liver cancer also driven by a fusion, a junction peptide vaccine was built and administered, without immunotherapy, exactly through the legal route described above ([published in 2022](https://pubmed.ncbi.nlm.nih.gov/36302754/)). It does not prove that it works at scale. It proves that **this thing can be built and given to a real human being** -- which, when I had started out, I did not know.

**KRAS, a single target, few mutations.** The trial mentioned above, which shows that a single well-chosen epitope can raise a durable immune response even in a mutation-poor tumour.

None of them is proof that my vaccine would work. Together they tell me only this much: the mechanism is plausible, the manufacturing route exists, and a single well-chosen target can be enough. The rest is hypothesis.

{{< callout type="warning" >}}
Hope without data stays a wish. I am writing this article as a map, not as a recommendation. If you are looking at the same options, look also at the part I do not like: most of the vaccines rigorously tested in lung cancer did not prolong life, and for my specific situation there is not a single patient treated before me.
{{< /callout >}}

## A resource I recommend again

I wrote about it [last time](/en/blog/standard-of-care-vs-personalized-medicine/) too, but here it is even more in place.

Sijbrandij Foundation -- created by Sid Sijbrandij, the co-founder of GitLab, after his own experience with cancer -- keeps a clean list of suppliers for exactly the things in this article: tissue preservation, molecular profiling, vaccines, cell therapies. And the part that seemed most valuable to me is that it offers you, free of charge, a thirty-minute conversation with someone from their team.

They do not make your decision and they do not replace your doctor. But through the patients who have passed through them they have seen solutions I could never have found on my own, and they can put you in touch with people they already work with. For someone stuck on exactly the link I wrote about above -- who agrees to administer -- it is the kind of conversation that can shorten months of searching.

{{< callout type="tip" >}}
Sijbrandij Foundation -- FCCT, free for patients: the supplier list and the 30-minute consultation. [sijbrandijfoundation.org/fcct#suppliers](https://sijbrandijfoundation.org/fcct#suppliers)
{{< /callout >}}

## Where I am now

I have paid nothing and I have signed nothing. I have three gates to pass, in this order:

1. **How much tissue I have left.** I am going to the lab in person, with the blocks, so that someone who has them in hand can count.
2. **HLA typing at four digits.** It tells me whether the target is real or only plausible on paper.
3. **The exact sequence of the junction.** The data request has been sent.

Only after these three does a conversation about money with anyone make sense.

It is a strange position: I have a very clear strategy and zero certainties. But I prefer that to buying something expensive that does not look at my tumour.

If you are a doctor, an oncology navigator or a patient and you have experience with any of these centres -- or with others I have not found -- [write to me](/en/contact/). I got here by asking people, and that is how I want to keep going.

---

{{< action-box >}}
1. **Inventory your tissue.** Ask the lab that ran your tests how many sections you have left and what percentage of tumour the block has now. "The tissue is good" and "I still have enough" are different things.
2. **Ask for HLA typing at four digits.** It is cheap, it is done once, and it decides whether a peptide target makes sense for you.
3. **If your tumour is driven by a fusion, ask for the report with the exact junction** -- the exons involved and the coordinates -- not just the names of the two genes. Usually the data already exists, it just does not make it into the clinical report.
4. **Ask any centre, before any payment, what material their product needs**: fresh tissue, paraffin, blood or just a sequence.
5. **Ask in writing what happens if the analysis finds nothing usable** -- what you get, where you can stop, what data stays yours.
6. **Do not confuse a manufacturing authorization with proof of efficacy**, and do not confuse a fast reply with a good fit.
{{< /action-box >}}

---

{{< disclaimer >}}{{< /disclaimer >}}
