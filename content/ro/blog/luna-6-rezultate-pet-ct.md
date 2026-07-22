---
title: "PET-CT la luna 6"
date: 2026-07-22
draft: false
description: "Rezultatul monitorizarii la sase luni: tumora stabila, ganglioni inca usor activi, o crestere metabolica sub prag si decizia de a face SBRT pe tumora principala."
tags: ["PET-CT", "monitorizare", "SBRT", "radioterapie stereotactica", "cancer pulmonar", "RET", "stadiul IV", "SUV", "PERCIST", "CyberKnife", "MR-Linac"]
categories: ["Blog"]
translationKey: "blog-month-6-results"
weight: 30
author: "OncoGuide"
ShowToc: false
TocOpen: false
---

**Pe scurt:** Am făcut PET-CT-ul de control la șase luni de tratament. Vestea mare e bună: nicio leziune nouă, nicăieri. Dar tumora principală apare puțin mai intensă decât în aprilie, iar ganglionii care se micșoraseră sunt încă, milimetric, un pic activi. Articolul ăsta e despre ce arată de fapt cifrele, despre de ce comparația între două scanări nu a ieșit atât de curată pe cât plănuisem -- deși am folosit același aparat -- și despre decizia pe care am luat-o: radioterapie stereotactică pe tumora din plămân, cât mai repede.

---

## Unde eram înainte de scanare

Iau din februarie o pastilă țintită pentru fuziunea RET din tumora mea. ([Povestea de la început e aici](/ro/blog/povestea-mea/), iar despre cum gândesc strategia am scris [aici](/ro/blog/standard-of-care-vs-medicina-personalizata/).)

Răspunsul a fost profund. La controlul de la trei luni, tumora din plămân scăzuse ca activitate metabolică aproape complet, leziunea de la coloană -- tratată la început cu radioterapie -- se liniștise, iar metastaza de la bazin dispăruse.

Scanarea de la șase luni era, deci, prima verificare reală a întrebării: ține?

## Ce a arătat scanarea

Cel mai important lucru întâi, pentru că el contează cel mai mult: **nicio leziune nouă, nicăieri**. Creier, gât, abdomen, bazin, ficat, splină, suprarenale, pancreas -- toate curate. RMN-ul cerebral făcut separat, cu o săptămână înainte, a ieșit curat pentru a treia oară consecutiv.

Restul e mai nuanțat, și tocmai de aceea merită povestit onest.

**Tumora principală din plămân** are aceeași dimensiune ca în aprilie, în jur de 16 mm. Dar radiologul o descrie ca fiind "mai evidentă metabolic decât la studiul anterior". În cifre: valoarea SUV (o măsură a cât de mult zahăr radioactiv consumă țesutul, adică un indicator indirect de activitate) a urcat de la 2.0 în aprilie la 3.2 în iulie. Pentru context, la diagnostic era 19.2.

**Ganglionii** din mediastin au sub 10 mm și sunt descriși ca "similari, cu regresie pe alocuri" față de aprilie, cu o valoare de 5. Traiectoria lor, de la început până acum, arată așa: 13.7, apoi 8.3, acum 5. Adică exact ce spuneam la început: oficial regresați, milimetrici -- dar concluzia raportului îi numește în continuare hipermetabolici. Nu s-au stins complet. A rămas activitate, iar ea e acum cea mai ridicată dintre leziunile care mi-au mai rămas.

**Leziunea de la coloană**, tratată la început, e stabilă. Iar o zonă de condensare apărută în aprilie la baza plămânului stâng, despre care nu se știa dacă e inflamație sau altceva, **a dispărut** din raportul de acum. Asta a fost, de fapt, vestea care a deblocat decizia de mai jos.

{{< callout type="tip" >}}
Dacă citești un raport PET-CT: valoarea SUV nu e "cât de mare e cancerul". E cât de multă glucoză consumă acel țesut în momentul scanării. Inflamația consumă și ea. Vindecarea consumă și ea. De asta un număr singur, fără context și fără comparație corectă, spune mai puțin decât pare.
{{< /callout >}}

## Am folosit același aparat. Și tot n-a ieșit o comparație curată.

Aici e partea pe care chiar vreau să o las scrisă, pentru că e cea mai utilă lecție pe care am învățat-o luna asta.

M-am gândit din timp la comparabilitate. Am insistat să fac toate scanările pe **același aparat**, în același centru, cu același protocol. Credeam că asta e suficient ca să pot compara cinstit două numere.

Nu e. M-am uitat în fișierele DICOM brute -- datele tehnice pe care aparatul le scrie în fiecare imagine -- și am găsit mai multe diferențe între aprilie și iulie. Niciuna nu e o greșeală a cuiva. Toate, împreună, fac ca cele două numere să nu fie riguros comparabile.

- **Timpul de așteptare după injectare.** În aprilie am stat 99 de minute între injectarea trasorului și scanare. În iulie, 55 de minute. Tumora continuă să acumuleze trasor ore întregi, așa că un timp mai scurt **subestimează** valoarea. Adică acest factor lucrează împotriva creșterii observate, nu în favoarea ei.
- **Corecția pentru mișcarea respiratorie.** În iulie a fost aplicat un algoritm de corecție a mișcării, care în aprilie nu fusese. O leziune care se mișcă odată cu respirația apare "întinsă" și diluată; când corectezi mișcarea, recuperezi semnalul și valoarea **crește**, la aceeași biologie.
- **Versiunea softului de reconstrucție** a fost actualizată între cele două scanări, incluzând și o corecție suplimentară de împrăștiere.
- **Greutatea mea** a crescut de la 77 la 79 kg. SUV se raportează la greutate, deci asta singură adaugă mecanic vreo 2.6 la sută.
- **Cantitatea de contrast oral** a fost aproximativ jumătate față de aprilie. Nu afectează plămânul, dar afectează cât de bine se separă structurile din abdomen.
- **Standardizarea EARL** -- o procedură prin care laboratorul livrează, în plus, o reconstrucție calibrată după un standard european, tocmai ca valorile să fie comparabile în timp -- am cerut-o la programare. Nu a fost livrată la niciuna dintre scanări.

Am ajuns la o concluzie pe care nu o știam: **același aparat nu înseamnă automat aceleași condiții.** Comparabilitatea nu e o proprietate a mașinii, e o procedură pe care trebuie s-o ceri explicit, în scris, de fiecare dată.

{{< callout type="important" >}}
Ce cer de acum înainte, la fiecare programare de PET-CT, și ce ți-aș sugera și ție să ceri în scris:

1. Aceeași durată de așteptare după injectare ca la scanarea anterioară (toleranța standard e de plus/minus 15 minute).
2. Aceleași corecții aplicate (mișcare, împrăștiere) și aceeași versiune de reconstrucție, sau cel puțin menționarea lor explicită în raport.
3. O reconstrucție standardizată [EARL](https://earl.eanm.org/) suplimentară -- cerută la programare, pentru că nu se poate face retroactiv după ce datele brute sunt șterse.
4. Același protocol de contrast.
5. O listă fixă de leziuni-țintă, raportate cu valori numerice la fiecare control și comparate cu **toate** scanările anterioare, nu doar cu ultima.
{{< /callout >}}

## Deci a crescut, sau nu?

Răspunsul cinstit e: a crescut puțin, dar creșterea nu înseamnă progresie. Și merită explicat de ce, pentru că e exact genul de nuanță care sperie inutil.

Există un set de criterii internaționale pentru a decide când o modificare pe PET înseamnă progresie, numit [PERCIST](https://pubmed.ncbi.nlm.nih.gov/19403881/). Ca să vorbim de progresie metabolică, e nevoie de o creștere de cel puțin 30 la sută **și**, simultan, de o creștere absolută de cel puțin 0.8 unități. La mine, creșterea a fost de circa 25 la sută și de 0.32 unități absolut. Nu atinge niciunul dintre praguri.

Mai mult: pentru o leziune atât de mică, variabilitatea normală între două scanări repetate ale aceleiași tumori nemodificate e de ordinul a 30-50 la sută. Creșterea observată intră confortabil în zgomotul de măsurare.

Și încă ceva: leziunea mea e, la ambele momente, sub pragul de la care PERCIST consideră o leziune măsurabilă. Valorile ei sunt sub nivelul ficatului. Practic, criteriile nici nu au fost concepute pentru o țintă atât de mică.

Dar cel mai important argument vine din altă parte. PET-ul are toate confuziile de mai sus. **Componenta CT a aceleiași scanări nu are niciuna** -- ea nu depinde de timpul de așteptare, de corecția de mișcare sau de versiunea softului PET. Iar CT-ul spune, aprilie față de iulie: diametru 13.5 mm, neschimbat. Volumul părții solide, ușor scăzut. Densitatea, neschimbată. (Măsurătorile astea sunt ale mele, calculate acasă din imaginile brute cu instrumente de AI -- nu apar ca atare în raportul radiologului.)

Deci: **stabil, nu progresie, cu o modificare metabolică sub prag.** Nu spun "plat", pentru că există o creștere mică și reală. Și nu spun "artefact", pentru că factorul cel mai mare -- timpul de așteptare -- lucra împotriva ei. Spun exact ce e: o leziune care nu crește, cu o pâlpâire metabolică pe care nu o pot certifica.

{{< callout type="tip" >}}
O precizare care cred că e utilă. Cifrele de mai sus -- volumul părții solide, densitatea, comparațiile între cele două scanări -- nu vin din raport. Le-am calculat singur, acasă, din fișierele DICOM brute, cu instrumente de AI.

Nu e ceva rezervat specialiștilor. Imaginile brute sunt ale tale și le poți cere pe un stick sau pe CD la fiecare scanare. În cazul meu, diferența dintre "am citit raportul" și "am măsurat eu aceleași imagini" a fost diferența dintre panică și o decizie liniștită.
{{< /callout >}}

## Citește raportul cuvânt cu cuvânt

O pățanie care merită spusă, pentru că era să public altceva.

Câteva zile am fost convins că raportul nu dă nicio valoare numerică pentru ganglioni. Îmi construisem deja o mică teorie în jurul asta: că e o omisiune de raportare, că ar trebui să cer o completare.

Greșeam. Numărul era acolo. Stătea într-o paranteză, la capătul unei fraze lungi de patru rânduri care începea cu altceva și se termina peste pagină. L-am ratat, apoi am construit peste ratarea aia.

Lecția, pentru oricine ține un dosar medical pe termen lung: **citește raportul singur, frază cu frază, și scoate numerele într-un tabel al tău.** Valorile stau, de obicei, în paranteze la capăt de propoziție, nu în locuri evidente, iar o singură frază poate descrie trei grupuri diferite de leziuni cu trei valori diferite. Iar dacă chiar lipsește ceva, un raport **se poate completa** -- se cere politicos, e gratuit și durează puțin.

## Decizia: radioterapie pe tumora din plămân, acum

Aici ajung la partea de acțiune.

Logica pe care o urmez e cea despre care am scris data trecută: cele mai puține celule canceroase pe care le voi avea vreodată sunt cele de acum, cât timp pastila ține boala jos. Dacă e un moment în care merită să lovești ce a mai rămas, acela e acum, nu mai târziu.

Tumora din plămân e mică, stabilă anatomic, dar nu a dispărut. E o țintă bună pentru **SBRT** -- radioterapie stereotactică, adică o doză mare livrată foarte precis, în puține ședințe, cu marje foarte mici în jurul țintei.

Un lucru a deblocat decizia: zona de condensare apărută în aprilie la baza plămânului stâng, despre care nu se știa dacă e infecție, inflamație de la tratament sau boală, a dispărut. Cât timp era acolo, orice iradiere toracică era pe pauză, pentru că nu voiam să iradiez fără să știu ce iradiez.

Simularea s-a făcut pe 21 iulie, iar tratamentul începe luni, 27 iulie, la Anadolu Medical Center din Istanbul, pe un aparat Varian Edge.

**Ce nu știu încă:** doza exactă, numărul de ședințe și regula privind pastila -- dacă și câte zile se oprește în jurul radioterapiei. Urmează să-mi fie comunicate de echipă. Am cerut-o în scris, pentru că e genul de detaliu pe care nu vrei să-l ții minte din vorbă.

Am mai trecut prin SBRT o dată, în ianuarie, pentru leziunea de la coloană: trei ședințe, pe CyberKnife. Durerea de spate care mă adusese la medic a dispărut. Deci nu intru pe teren necunoscut.

## Trei aparate sub același acoperiș

Partea care m-a impresionat sincer a fost discuția cu medicul radioterapeut. Nu știam că un singur centru poate avea trei platforme diferite de radioterapie stereotactică, fiecare cu rolul ei. Le las aici pentru că e genul de lucru pe care mi-ar fi plăcut să-l știu mai devreme.

**CyberKnife.** Un braț robotic industrial cu un mic accelerator liniar montat la capăt, fără gantry. Poate ținti din peste o mie de poziții diferite. Particularitatea lui e urmărirea respiratorie continuă: corelează mișcarea suprafeței corpului cu poziția internă a tumorii, verifică periodic prin radiografii în timp real, și **mișcă fasciculul după tumoră** pe tot parcursul ședinței. Nu ai nevoie să-ți ții respirația. Costul: ședințe lungi.

**MR-Linac (la Anadolu, un Elekta Unity de 1.5 tesla, primul din Turcia, din octombrie 2024).** Un RMN de diagnostic combinat cu un accelerator liniar. În timpul iradierii vezi tumora direct, în film continuu, nu prin surogat. Și poți reface planul de tratament la fiecare ședință, adaptându-l la cum arată corpul în ziua aceea. E aparatul potrivit când ținta stă lipită de organe moi care se mișcă și se umplu diferit de la o zi la alta: pancreas, ficat, bazin, sau un ganglion vecin cu esofagul ori intestinul. Costul: cele mai lungi ședințe dintre toate.

**Varian Edge.** Un accelerator clasic cu braț în C, configurat special pentru radiochirurgie și SBRT. Aduce un pachet de precizie: monitorizare optică continuă a suprafeței corpului, cu oprirea automată a fasciculului dacă te miști în afara toleranței; livrare sincronizată cu faza respirației; un CT conic făcut chiar înainte de tratament, pentru verificarea poziției; o masă robotică ce corectează pe șase axe, inclusiv rotațiile; un colimator cu lamele fine, care taie doza abrupt în jurul unei ținte mici; și fascicule de intensitate mare, care scurtează mult timpul efectiv de iradiere.

Diferența de filosofie, dacă vrei să o reții simplu: CyberKnife și MR-Linac **urmăresc** ținta continuu, fiecare în felul lui. Edge **sincronizează și verifică** -- tratează în faza corectă a respirației și confirmă poziția prin imagistică, cu ședințe mult mai scurte.

Pentru cazul meu, echipa a propus Edge. Precizarea de "sub un milimetru" pe care o vezi în materialele oricărui producător e o cifră obținută în condiții de test, nu o garanție pentru un pacient anume -- toți trei producătorii o afișează. Ce contează e lanțul concret de control al mișcării, pe leziunea ta.

{{< callout type="tip" >}}
O întrebare bună de pus echipei tale de radioterapie, indiferent unde te tratezi: **"De ce acest aparat, pentru leziunea mea, și nu celălalt?"** Răspunsul e de obicei dozimetric -- cât primesc organele din jur -- și e o discuție pe care merită să o ai, nu una pe care să o presupui.
{{< /callout >}}

Ce mi s-a părut remarcabil e că toate trei sunt în aceeași clădire, iar accesul a fost rapid. Pentru un pacient care caută tehnologia asta, faptul că nu trebuie să alegi între centre, ci se poate alege aparatul potrivit pentru tine în interiorul aceluiași centru, contează enorm.

## Întrebarea pe care încă o cântăresc: radioterapia și un eventual vaccin

Un singur lucru mai am de cântărit, și e cinstit să spun că nu e rezolvat.

În paralel cu tratamentul, investighez activ un vaccin personalizat construit pe particularitatea genetică a tumorii mele. Vorbesc chiar acum cu mai multe centre care fac așa ceva. (Despre asta scriu pe larg în [articolul următor](/ro/blog/vaccinuri-personalizate-ce-am-gasit/).)

Întrebarea e dacă iradierea ajută sau încurcă un asemenea vaccin. Argumentele merg în ambele direcții:

**În favoarea.** Radioterapia omoară celulele într-un mod care poate elibera antigene tumorale și poate atrage atenția sistemului imunitar -- un fel de vaccinare la fața locului. Există un detaliu tehnic interesant: peste un anumit prag de doză pe ședință, celula activează un mecanism care distruge ADN-ul din citoplasmă și **anulează** tocmai semnalul imunitar dorit ([Vanpouille-Box, 2017](https://pubmed.ncbi.nlm.nih.gov/28598415/)). Cu alte cuvinte, mai multe ședințe cu doză moderată pot păstra mai mult efect imunitar decât o singură ședință foarte mare.

**Împotriva.** Radioterapia distruge și limfocite -- exact celulele pe care un vaccin vrea să le antreneze. Și există un studiu randomizat mare în cancerul pulmonar oligometastatic, [NRG-LU002](https://clinicaltrials.gov/study/NCT03137771), care nu a arătat un beneficiu pentru adăugarea radioterapiei locale la tratamentul sistemic. E un rezultat pe care nu am voie să-l ignor doar pentru că nu-mi convine.

Ca să fiu corect și în cealaltă direcție: acel studiu a inclus pacienți neselectați, nu pacienți aflați pe o pastilă țintită ca mine. Studiul care a testat exact scenariul "pastilă țintită plus radioterapie locală" -- SINDAS, la altă mutație decât a mea -- a arătat beneficiu. Adevărul e probabil undeva la mijloc: radioterapia locală nu e un panaceu universal, dar contextul în care o dai contează enorm.

Un lucru e clar și merită spus, pentru că e o confuzie ușor de făcut: **radioterapia nu atinge țesutul din care s-ar construi vaccinul.** Acela e blocul de parafină din biopsia de anul acesta, pe care îl am fizic la mine. Sunt două lucruri complet separate.

Am pus întrebarea directă unuia dintre centre: dacă ar fi mai bine să se recolteze celulele înainte de radioterapie. Aștept răspunsul. Regula pe care mi-am impus-o între timp e simplă: **nu întârzii radioterapia pentru un vaccin care încă nu și-a trecut propriile praguri.** Radioterapia e decisă, plătită, simulată, pe o țintă reală. Vaccinul, deocamdată, nu e.

## Ce urmează la monitorizare

De la luna 6 trec pe un ritm alternant, o scanare la trei luni:

- **luna 9** (octombrie 2026) -- CT, de data asta **cu substanță de contrast intravenoasă**;
- **luna 12** (ianuarie 2027) -- PET-CT plus RMN cerebral;
- **luna 15** -- CT; **luna 18** -- PET-CT plus RMN. Și tot așa.

Un detaliu tehnic pe care l-am aflat abia acum și care merită știut: **componenta CT a unui PET-CT nu are contrast intravenos** și nu va avea niciodată, pentru că rolul ei e altul -- corectarea atenuării. Sticla pe care o bei înainte e contrast oral, pentru intestin, iar cele două seringi sunt trasorul și serul de spălare. Dacă ai nevoie de o măsurătoare anatomică fină, ea vine de la un **CT de diagnostic separat, cu contrast intravenos** -- nu de la PET.

## Unde sunt, de fapt

Șase luni. Nicio leziune nouă. O tumoră care nu crește, cu o pâlpâire metabolică pe care nu o pot certifica. Niște ganglioni milimetrici care nu s-au stins complet. Și o fereastră bună, în care aleg să acționez în loc să aștept.

Nu e vindecare și nu pretind că e. E o poziție bună, pe care încerc să o folosesc bine.

---

{{< action-box >}}
1. Cere ca toate scanările de control să se facă pe **același aparat, în același centru** -- e condiția minimă, nu garanția.
2. Cere **în scris, la programare**, aceiași parametri de achiziție ca la scanarea anterioară: timp de așteptare după injectare, corecții aplicate, versiune de reconstrucție, protocol de contrast.
3. Cere o **reconstrucție standardizată EARL** ca serie suplimentară. Nu se poate face retroactiv.
4. Dacă lipsește o valoare din raport, **cere o completare**. E gratuit, durează puțin, și îți salvează graficul de peste doi ani.
5. Nu interpreta o singură valoare SUV izolat. Întreabă de pragurile PERCIST, de variabilitatea normală pentru o leziune de dimensiunea ta, și ce spune componenta CT.
6. Dacă ți se propune radioterapie stereotactică, întreabă **de ce acel aparat pentru leziunea ta** -- și cere în scris doza, numărul de ședințe și regula privind pastila țintită.
{{< /action-box >}}

---

{{< disclaimer >}}{{< /disclaimer >}}
