---
title: "PET-CT at Month 6"
date: 2026-07-22
draft: false
description: "Six-month follow-up results: stable tumour, nodes still slightly active, a sub-threshold metabolic rise, and the decision to do SBRT on the main tumour."
tags: ["PET-CT", "monitoring", "SBRT", "stereotactic body radiotherapy", "lung cancer", "RET", "stage IV", "SUV", "PERCIST", "CyberKnife", "MR-Linac"]
categories: ["Blog"]
translationKey: "blog-month-6-results"
weight: 30
author: "OncoGuide"
ShowToc: false
TocOpen: false
---

**In short:** I had my six-month follow-up PET-CT. The big news is good: no new lesions, anywhere. But the main tumour looks a little more intense than in April, and the lymph nodes that had shrunk are still, at a millimetre scale, a little active. This article is about what the numbers actually show, about why the comparison between two scans did not come out as clean as I had planned -- even though I used the same machine -- and about the decision I made: stereotactic radiotherapy on the lung tumour, as soon as possible.

---

## Where I was before the scan

Since February I have been taking a targeted pill for the RET fusion in my tumour. ([The story from the beginning is here](/en/blog/my-story/), and I wrote about how I think about strategy [here](/en/blog/standard-of-care-vs-personalized-medicine/).)

The response was profound. At the three-month check, the lung tumour had dropped in metabolic activity almost completely, the spine lesion -- treated with radiotherapy at the start -- had quietened down, and the pelvic metastasis had disappeared.

So the six-month scan was the first real test of the question: does it hold?

## What the scan showed

The most important thing first, because it is what counts most: **no new lesions, anywhere**. Brain, neck, abdomen, pelvis, liver, spleen, adrenals, pancreas -- all clear. The brain MRI done separately, a week earlier, came back clear for the third time in a row.

The rest is more nuanced, and that is exactly why it deserves an honest telling.

**The main lung tumour** is the same size as in April, around 16 mm. But the radiologist describes it as "metabolically more evident than on the previous study". In numbers: the SUV (a measure of how much radioactive sugar the tissue consumes, that is, an indirect indicator of activity) went up from 2.0 in April to 3.2 in July. For context, at diagnosis it was 19.2.

**The lymph nodes** in the mediastinum are under 10 mm and are described as "similar, with regression in places" compared with April, at a value of 5. Their trajectory, from the beginning until now, looks like this: 13.7, then 8.3, now 5. Which is exactly what I said at the start: officially regressed, millimetre-sized -- but the conclusion of the report still calls them hypermetabolic. They have not gone out completely. Activity has remained, and it is now the highest of the lesions I have left.

**The spine lesion**, treated at the start, is stable. And an area of consolidation that appeared in April at the base of the left lung, about which nobody knew whether it was inflammation or something else, **has disappeared** from this report. That was, in fact, the news that unblocked the decision below.

{{< callout type="tip" >}}
If you are reading a PET-CT report: the SUV is not "how big the cancer is". It is how much glucose that tissue consumes at the moment of the scan. Inflammation consumes it too. Healing consumes it too. That is why a single number, without context and without a proper comparison, says less than it seems to.
{{< /callout >}}

## I used the same machine. And it still did not come out as a clean comparison.

This is the part I really want to leave written down, because it is the most useful lesson I learned this month.

I thought about comparability in advance. I insisted on having all the scans on the **same machine**, in the same centre, with the same protocol. I thought that was enough to be able to compare two numbers honestly.

It is not. I looked into the raw DICOM files -- the technical data the machine writes into every image -- and I found several differences between April and July. None of them is anybody's mistake. All of them together mean that the two numbers are not rigorously comparable.

- **The uptake time after injection.** In April I waited 99 minutes between the tracer injection and the scan. In July, 55 minutes. A tumour keeps taking up tracer for hours, so a shorter time **underestimates** the value. Which means this factor works against the observed rise, not in favour of it.
- **Respiratory motion correction.** In July a motion correction algorithm was applied that had not been applied in April. A lesion that moves with breathing appears "smeared" and diluted; when you correct for motion, you recover the signal and the value **goes up**, for the same biology.
- **The reconstruction software version** was updated between the two scans, including an additional scatter correction.
- **My weight** went up from 77 to 79 kg. SUV is normalized to body weight, so that alone mechanically adds about 2.6 per cent.
- **The amount of oral contrast** was roughly half of what it was in April. It does not affect the lung, but it does affect how well the structures in the abdomen separate.
- **EARL standardization** -- a procedure by which the lab additionally delivers a reconstruction calibrated to a European standard, precisely so that values are comparable over time -- I asked for it at booking. It was not delivered for either scan.

I reached a conclusion I did not know before: **the same machine does not automatically mean the same conditions.** Comparability is not a property of the machine, it is a procedure you have to ask for explicitly, in writing, every single time.

{{< callout type="important" >}}
What I ask for from now on, at every PET-CT booking, and what I would suggest you ask for in writing too:

1. The same uptake time after injection as at the previous scan (the standard tolerance is plus/minus 15 minutes).
2. The same corrections applied (motion, scatter) and the same reconstruction version, or at least an explicit mention of them in the report.
3. An additional standardized [EARL](https://earl.eanm.org/) reconstruction -- asked for at booking, because it cannot be done retroactively once the raw data have been deleted.
4. The same contrast protocol.
5. A fixed list of target lesions, reported with numerical values at every follow-up and compared with **all** the previous scans, not just the last one.
{{< /callout >}}

## So did it grow, or not?

The honest answer is: it went up a little, but the rise does not mean progression. And it is worth explaining why, because this is exactly the kind of nuance that frightens people for nothing.

There is a set of international criteria for deciding when a change on PET means progression, called [PERCIST](https://pubmed.ncbi.nlm.nih.gov/19403881/). To speak of metabolic progression you need a rise of at least 30 per cent **and**, at the same time, an absolute rise of at least 0.8 units. In my case, the rise was about 25 per cent and 0.32 units in absolute terms. It reaches neither threshold.

More than that: for a lesion this small, the normal variability between two repeated scans of the same unchanged tumour is on the order of 30-50 per cent. The observed rise fits comfortably inside the measurement noise.

And one more thing: at both time points, my lesion is below the threshold at which PERCIST considers a lesion measurable. Its values are below the liver level. In practice, the criteria were not even designed for a target this small.

But the most important argument comes from somewhere else. The PET has all the confounders above. **The CT component of the same scan has none of them** -- it does not depend on the uptake time, on motion correction or on the PET software version. And the CT says, April versus July: diameter 13.5 mm, unchanged. Solid component volume, slightly lower. Density, unchanged. (These measurements are my own, calculated at home from the raw images with AI tools -- they do not appear as such in the radiologist's report.)

So: **stable, not progression, with a sub-threshold metabolic change.** I am not saying "flat", because there is a small and real rise. And I am not saying "artefact", because the biggest factor -- the uptake time -- was working against it. I am saying exactly what it is: a lesion that is not growing, with a metabolic flicker I cannot certify.

{{< callout type="tip" >}}
One clarification I think is useful. The numbers above -- the solid component volume, the density, the comparisons between the two scans -- do not come from the report. I calculated them myself, at home, from the raw DICOM files, with AI tools.

This is not something reserved for specialists. The raw images are yours and you can ask for them on a USB stick or on a CD at every scan. In my case, the difference between "I read the report" and "I measured the same images myself" was the difference between panic and a calm decision.
{{< /callout >}}

## Read the report word by word

A little mishap worth telling, because I nearly published something else.

For a few days I was convinced that the report gave no numerical value at all for the lymph nodes. I had already built a small theory around that: that it was a reporting omission, that I should ask for an addendum.

I was wrong. The number was there. It sat inside a parenthesis, at the end of a four-line sentence that started with something else and finished over the page. I missed it, and then I built on top of that miss.

The lesson, for anyone keeping a long-term medical file: **read the report yourself, sentence by sentence, and pull the numbers out into a table of your own.** The values usually sit in parentheses at the end of a sentence, not in obvious places, and a single sentence can describe three different groups of lesions with three different values. And if something really is missing, a report **can be amended** -- you ask politely, it is free and it takes little time.

## The decision: radiotherapy on the lung tumour, now

Here I get to the action part.

The logic I follow is the one I wrote about last time: the fewest cancer cells I will ever have are the ones I have now, while the pill keeps the disease down. If there is a moment worth hitting what is left, that moment is now, not later.

The lung tumour is small, anatomically stable, but it has not disappeared. It is a good target for **SBRT** -- stereotactic body radiotherapy, that is, a high dose delivered very precisely, in few sessions, with very small margins around the target.

One thing unblocked the decision: the area of consolidation that appeared in April at the base of the left lung, about which nobody knew whether it was infection, treatment-related inflammation or disease, has disappeared. As long as it was there, any thoracic irradiation was on hold, because I did not want to irradiate without knowing what I was irradiating.

The simulation was done on 21 July, and treatment starts on Monday, 27 July, at Anadolu Medical Center in Istanbul, on a Varian Edge.

**What I do not know yet:** the exact dose, the number of sessions and the rule about the pill -- whether and for how many days it is stopped around the radiotherapy. The team is due to tell me. I asked for it in writing, because it is the kind of detail you do not want to be remembering from a conversation.

I have been through SBRT once before, in January, for the spine lesion: three sessions, on CyberKnife. The back pain that had brought me to the doctor went away. So I am not stepping onto unknown ground.

## Three machines under one roof

The part that genuinely impressed me was the conversation with the radiation oncologist. I did not know that a single centre could have three different stereotactic radiotherapy platforms, each with its own role. I am leaving them here because this is the kind of thing I would have liked to know earlier.

**CyberKnife.** An industrial robotic arm with a small linear accelerator mounted on the end, with no gantry. It can aim from over a thousand different positions. Its particularity is continuous respiratory tracking: it correlates the movement of the body surface with the internal position of the tumour, checks periodically with real-time X-rays, and **moves the beam after the tumour** throughout the session. You do not need to hold your breath. The cost: long sessions.

**MR-Linac (at Anadolu, a 1.5 tesla Elekta Unity, the first in Turkey, since October 2024).** A diagnostic MRI combined with a linear accelerator. During irradiation you see the tumour directly, as a continuous film, not through a surrogate. And you can redo the treatment plan at every session, adapting it to how the body looks that day. It is the right machine when the target sits up against soft organs that move and fill differently from one day to the next: pancreas, liver, pelvis, or a lymph node next to the oesophagus or the bowel. The cost: the longest sessions of all.

**Varian Edge.** A classic C-arm accelerator, configured specifically for radiosurgery and SBRT. It brings a precision package: continuous optical monitoring of the body surface, with automatic beam hold if you move outside tolerance; delivery gated to the phase of the breath; a cone-beam CT taken right before treatment, to verify position; a robotic couch that corrects on six axes, including rotations; a fine-leaf collimator, which cuts the dose off sharply around a small target; and high intensity beams, which considerably shorten the effective irradiation time.

The difference in philosophy, if you want to remember it simply: CyberKnife and MR-Linac **track** the target continuously, each in its own way. Edge **gates and verifies** -- it treats in the right phase of the breath and confirms the position with imaging, with much shorter sessions.

For my case, the team proposed the Edge. The "sub-millimetre" accuracy figure you see in any manufacturer's materials is a number obtained under test conditions, not a guarantee for a particular patient -- all three manufacturers display it. What matters is the concrete chain of motion control, on your lesion.

{{< callout type="tip" >}}
A good question to ask your radiotherapy team, wherever you are treated: **"Why this machine, for my lesion, and not the other one?"** The answer is usually dosimetric -- how much the surrounding organs receive -- and it is a conversation worth having, not one to assume.
{{< /callout >}}

What struck me as remarkable is that all three are in the same building, and access was quick. For a patient looking for this technology, the fact that you do not have to choose between centres, but that the right machine for you can be chosen inside the same centre, matters enormously.

## The question I am still weighing: radiotherapy and a possible vaccine

There is one single thing left for me to weigh, and it is only honest to say that it is not resolved.

In parallel with treatment, I am actively investigating a personalized vaccine built on the genetic particularity of my tumour. I am talking right now with several centres that do this sort of thing. (I write about that at length in [the next article](/en/blog/personalized-cancer-vaccines/).)

The question is whether irradiation helps or hinders such a vaccine. The arguments go in both directions:

**In favour.** Radiotherapy kills cells in a way that can release tumour antigens and can draw the immune system's attention -- a sort of in situ vaccination. There is an interesting technical detail: above a certain dose threshold per session, the cell activates a mechanism that destroys the DNA in the cytoplasm and **cancels out** the very immune signal you wanted ([Vanpouille-Box, 2017](https://pubmed.ncbi.nlm.nih.gov/28598415/)). In other words, several sessions at a moderate dose can preserve more immune effect than a single very large one.

**Against.** Radiotherapy also destroys lymphocytes -- exactly the cells a vaccine wants to train. And there is a large randomized trial in oligometastatic lung cancer, [NRG-LU002](https://clinicaltrials.gov/study/NCT03137771), which did not show a benefit for adding local radiotherapy to systemic treatment. That is a result I am not allowed to ignore just because it does not suit me.

To be fair in the other direction as well: that trial included unselected patients, not patients on a targeted pill like me. The trial that tested exactly the "targeted pill plus local radiotherapy" scenario -- SINDAS, in a different mutation from mine -- did show a benefit. The truth is probably somewhere in the middle: local radiotherapy is not a universal panacea, but the context in which you give it matters enormously.

One thing is clear and worth saying, because it is an easy confusion to make: **radiotherapy does not touch the tissue the vaccine would be built from.** That is the paraffin-embedded block from this year's biopsy, which I physically have with me. They are two completely separate things.

I put the direct question to one of the centres: whether it would be better for the cells to be collected before radiotherapy. I am waiting for the answer. The rule I have set myself in the meantime is simple: **I do not delay radiotherapy for a vaccine that has not yet passed its own thresholds.** The radiotherapy is decided, paid for, simulated, on a real target. The vaccine, for now, is not.

## What comes next in monitoring

From month 6 I move to an alternating rhythm, one scan every three months:

- **month 9** (October 2026) -- CT, this time **with intravenous contrast**;
- **month 12** (January 2027) -- PET-CT plus brain MRI;
- **month 15** -- CT; **month 18** -- PET-CT plus MRI. And so on.

A technical detail I only found out now and which is worth knowing: **the CT component of a PET-CT has no intravenous contrast** and never will, because its role is a different one -- attenuation correction. The bottle you drink beforehand is oral contrast, for the bowel, and the two syringes are the tracer and the flush. If you need a fine anatomical measurement, it comes from a **separate diagnostic CT, with intravenous contrast** -- not from the PET.

## Where I actually am

Six months. No new lesions. A tumour that is not growing, with a metabolic flicker I cannot certify. Some millimetre-sized lymph nodes that have not gone out completely. And a good window, in which I choose to act instead of waiting.

It is not a cure and I do not claim it is. It is a good position, and I am trying to use it well.

---

{{< action-box >}}
1. Ask for all follow-up scans to be done on the **same machine, in the same centre** -- that is the minimum condition, not the guarantee.
2. Ask **in writing, at booking**, for the same acquisition parameters as at the previous scan: uptake time after injection, corrections applied, reconstruction version, contrast protocol.
3. Ask for a **standardized EARL reconstruction** as an additional series. It cannot be done retroactively.
4. If a value is missing from the report, **ask for an addendum**. It is free, it takes little time, and it saves the chart you will be looking at two years from now.
5. Do not interpret a single SUV in isolation. Ask about the PERCIST thresholds, about the normal variability for a lesion of your size, and about what the CT component says.
6. If stereotactic radiotherapy is proposed to you, ask **why that machine for your lesion** -- and ask in writing for the dose, the number of sessions and the rule about the targeted pill.
{{< /action-box >}}

---

{{< disclaimer >}}{{< /disclaimer >}}
