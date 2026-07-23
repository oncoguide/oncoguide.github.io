---
title: "TEP-TDM au sixième mois"
date: 2026-07-22
draft: false
description: "Résultat du suivi à six mois : tumeur stable, ganglions encore un peu actifs, une hausse métabolique sous le seuil et la décision de faire une SBRT sur la tumeur principale."
tags: ["TEP-TDM", "suivi", "SBRT", "radiothérapie stéréotaxique", "cancer du poumon", "RET", "stade IV", "SUV", "PERCIST", "CyberKnife", "MR-Linac"]
categories: ["Blog"]
translationKey: "blog-month-6-results"
weight: 30
author: "OncoGuide"
ShowToc: false
TocOpen: false
---

**En bref :** J'ai fait le TEP-TDM de contrôle à six mois de traitement. La grande nouvelle est bonne : aucune nouvelle lésion, nulle part. Mais la tumeur principale apparaît un peu plus intense qu'en avril, et les ganglions qui avaient rétréci restent encore, à l'échelle du millimètre, un peu actifs. Cet article parle de ce que montrent vraiment les chiffres, de la raison pour laquelle la comparaison entre deux examens n'a pas été aussi propre que je l'avais prévu -- alors même que j'ai utilisé le même appareil -- et de la décision que j'ai prise : une radiothérapie stéréotaxique sur la tumeur du poumon, le plus vite possible.

---

## Où j'en étais avant l'examen

Depuis février, je prends un comprimé ciblé pour la fusion RET de ma tumeur. ([L'histoire depuis le début est ici](/fr/blog/mon-histoire/), et sur ma façon de penser la stratégie j'ai écrit [ici](/fr/blog/standard-of-care-et-medecine-personnalisee/).)

La réponse a été profonde. Au contrôle des trois mois, la tumeur du poumon avait presque complètement baissé en activité métabolique, la lésion de la colonne -- traitée au début par radiothérapie -- s'était calmée, et la métastase du bassin avait disparu.

L'examen des six mois était donc la première vraie vérification de la question : est-ce que ça tient ?

## Ce qu'a montré l'examen

Le plus important d'abord, parce que c'est ce qui compte le plus : **aucune nouvelle lésion, nulle part**. Cerveau, cou, abdomen, bassin, foie, rate, surrénales, pancréas -- tout est propre. L'IRM cérébrale faite séparément, une semaine avant, est ressortie propre pour la troisième fois consécutive.

Le reste est plus nuancé, et c'est justement pour ça que ça mérite d'être raconté honnêtement.

**La tumeur principale du poumon** a la même taille qu'en avril, autour de 16 mm. Mais le radiologue la décrit comme "plus évidente sur le plan métabolique qu'à l'examen précédent". En chiffres : la valeur SUV (une mesure de la quantité de sucre radioactif que consomme le tissu, donc un indicateur indirect d'activité) est passée de 2.0 en avril à 3.2 en juillet. Pour situer, au diagnostic elle était de 19.2.

**Les ganglions** du médiastin font moins de 10 mm et sont décrits comme "similaires, avec par endroits une régression" par rapport à avril, avec une valeur de 5. Leur trajectoire, du début jusqu'à maintenant, ressemble à ça : 13.7, puis 8.3, maintenant 5. C'est exactement ce que je disais au début : officiellement en régression, millimétriques -- mais la conclusion du compte rendu continue de les appeler hypermétaboliques. Ils ne se sont pas éteints complètement. Il reste de l'activité, et elle est aujourd'hui la plus élevée parmi les lésions qui me restent.

**La lésion de la colonne**, traitée au début, est stable. Et une zone de condensation apparue en avril à la base du poumon gauche, dont on ne savait pas si c'était une inflammation ou autre chose, **a disparu** du compte rendu actuel. C'est en fait la nouvelle qui a débloqué la décision ci-dessous.

{{< callout type="tip" >}}
Si tu lis un compte rendu de TEP-TDM : la valeur SUV, ce n'est pas "la taille du cancer". C'est la quantité de glucose que ce tissu consomme au moment de l'examen. L'inflammation en consomme aussi. La cicatrisation en consomme aussi. C'est pour ça qu'un chiffre isolé, sans contexte et sans comparaison correcte, dit moins qu'il n'en a l'air.
{{< /callout >}}

## J'ai utilisé le même appareil. Et la comparaison n'est quand même pas sortie propre.

Voici la partie que je tiens vraiment à laisser écrite, parce que c'est la leçon la plus utile que j'ai apprise ce mois-ci.

J'avais pensé à la comparabilité à l'avance. J'ai insisté pour faire tous les examens sur le **même appareil**, dans le même centre, avec le même protocole. Je croyais que ça suffisait pour pouvoir comparer honnêtement deux chiffres.

Ça ne suffit pas. J'ai regardé dans les fichiers DICOM bruts -- les données techniques que l'appareil inscrit dans chaque image -- et j'ai trouvé plusieurs différences entre avril et juillet. Aucune n'est l'erreur de quelqu'un. Toutes ensemble, elles font que les deux chiffres ne sont pas rigoureusement comparables.

- **Le temps d'attente après l'injection.** En avril, j'ai attendu 99 minutes entre l'injection du traceur et l'acquisition. En juillet, 55 minutes. La tumeur continue d'accumuler le traceur pendant des heures, donc un temps plus court **sous-estime** la valeur. Autrement dit, ce facteur joue contre la hausse observée, pas en sa faveur.
- **La correction du mouvement respiratoire.** En juillet, un algorithme de correction du mouvement a été appliqué, ce qui n'avait pas été le cas en avril. Une lésion qui bouge avec la respiration apparaît "étalée" et diluée ; quand on corrige le mouvement, on récupère le signal et la valeur **augmente**, à biologie identique.
- **La version du logiciel de reconstruction** a été mise à jour entre les deux examens, avec en plus une correction supplémentaire du rayonnement diffusé.
- **Mon poids** est passé de 77 à 79 kg. Le SUV est rapporté au poids, donc cela seul ajoute mécaniquement environ 2.6 pour cent.
- **La quantité de produit de contraste oral** a été à peu près la moitié de celle d'avril. Cela n'affecte pas le poumon, mais cela affecte la façon dont les structures de l'abdomen se distinguent les unes des autres.
- **La standardisation EARL** -- une procédure par laquelle un service peut fournir, en plus, une reconstruction calibrée selon un standard européen, justement pour que les valeurs soient comparables dans le temps. Aucun des deux examens n'a inclus une telle reconstruction standardisée.

J'en suis arrivé à une conclusion que je ne connaissais pas : **le même appareil ne veut pas automatiquement dire les mêmes conditions.** La comparabilité n'est pas une propriété de la machine, c'est une procédure qu'il faut demander explicitement, par écrit, à chaque fois.

{{< callout type="important" >}}
Ce que je demande désormais à chaque prise de rendez-vous de TEP-TDM, et que je te suggérerais de demander aussi par écrit :

1. Le même temps d'attente après l'injection qu'à l'examen précédent (la tolérance standard est de plus ou moins 15 minutes).
2. Les mêmes corrections appliquées (mouvement, rayonnement diffusé) et la même version de reconstruction, ou au moins leur mention explicite dans le compte rendu.
3. Une reconstruction standardisée [EARL](https://earl.eanm.org/) supplémentaire -- demandée à la prise de rendez-vous, parce qu'on ne peut pas la faire rétroactivement une fois les données brutes effacées.
4. Le même protocole de produit de contraste.
5. Une liste fixe de lésions cibles, rapportées avec des valeurs numériques à chaque contrôle et comparées à **tous** les examens précédents, pas seulement au dernier.
{{< /callout >}}

## Alors, est-ce que ça a augmenté, ou pas ?

La réponse honnête est : ça a un peu augmenté, mais cette hausse ne veut pas dire progression. Et ça vaut la peine d'expliquer pourquoi, parce que c'est exactement le genre de nuance qui fait peur inutilement.

Il existe un ensemble de critères internationaux pour décider quand une modification sur la TEP signifie une progression, appelé [PERCIST](https://pubmed.ncbi.nlm.nih.gov/19403881/). Pour parler de progression métabolique, il faut une hausse d'au moins 30 pour cent **et**, en même temps, une hausse absolue d'au moins 0.8 unité. Chez moi, la hausse a été d'environ 25 pour cent et de 0.32 unité en absolu. Elle n'atteint aucun des deux seuils.

Plus encore : pour une lésion aussi petite, la variabilité normale entre deux examens répétés de la même tumeur inchangée est de l'ordre de 30 à 50 pour cent. La hausse observée entre confortablement dans le bruit de mesure.

Et encore une chose : ma lésion est, aux deux moments, sous le seuil à partir duquel PERCIST considère une lésion comme mesurable. Ses valeurs sont sous le niveau du foie. En pratique, les critères n'ont même pas été conçus pour une cible aussi petite.

Mais l'argument le plus important vient d'ailleurs. La TEP a toutes les sources de confusion ci-dessus. **La composante TDM du même examen n'en a aucune** -- elle ne dépend ni du temps d'attente, ni de la correction du mouvement, ni de la version du logiciel TEP. Et la TDM dit, avril contre juillet : diamètre 13.5 mm, inchangé. Le volume de la partie solide, légèrement en baisse. La densité, inchangée. (Ces mesures sont les miennes, calculées à la maison à partir des images brutes avec des outils d'IA -- elles n'apparaissent pas telles quelles dans le compte rendu du radiologue.)

Donc : **stable, pas de progression, avec une modification métabolique sous le seuil.** Je ne dis pas "plat", parce qu'il y a une hausse petite et réelle. Et je ne dis pas "artefact", parce que le facteur le plus important -- le temps d'attente -- jouait contre elle. Je dis exactement ce que c'est : une lésion qui n'augmente pas, avec un frémissement métabolique que je ne peux pas certifier.

{{< callout type="tip" >}}
Une précision qui me semble utile. Les chiffres ci-dessus -- le volume de la partie solide, la densité, les comparaisons entre les deux examens -- ne viennent pas du compte rendu. Je les ai calculés moi-même, à la maison, à partir des fichiers DICOM bruts, avec des outils d'IA.

Ce n'est pas réservé aux spécialistes. Les images brutes t'appartiennent et tu peux les demander sur une clé USB ou sur un CD à chaque examen. Dans mon cas, la différence entre "j'ai lu le compte rendu" et "j'ai mesuré moi-même les mêmes images" a été la différence entre la panique et une décision sereine.
{{< /callout >}}

## Lis le compte rendu mot à mot

Une mésaventure qui mérite d'être racontée, parce que j'ai failli publier autre chose.

Pendant quelques jours, j'ai été convaincu que le compte rendu ne donnait aucune valeur numérique pour les ganglions. Je m'étais déjà construit une petite théorie autour de ça : que c'était une omission de rédaction, qu'il fallait que je demande un complément.

Je me trompais. Le chiffre était là. Il se trouvait dans une parenthèse, au bout d'une phrase longue de quatre lignes qui commençait par autre chose et se terminait à la page suivante. Je l'ai raté, puis j'ai construit par-dessus ce ratage.

La leçon, pour quiconque tient un dossier médical sur le long terme : **lis le compte rendu toi-même, phrase par phrase, et sors les chiffres dans un tableau à toi.** Les valeurs se trouvent d'habitude entre parenthèses en fin de phrase, pas à des endroits évidents, et une seule phrase peut décrire trois groupes de lésions différents avec trois valeurs différentes. Et s'il manque vraiment quelque chose, un compte rendu **peut être complété** -- ça se demande poliment, c'est gratuit et ça prend peu de temps.

## La décision : radiothérapie sur la tumeur du poumon, maintenant

J'arrive ici à la partie action.

La logique que je suis est celle dont j'ai parlé la dernière fois : le plus petit nombre de cellules cancéreuses que j'aurai jamais, c'est celui de maintenant, tant que le comprimé maintient la maladie en bas. S'il y a un moment où ça vaut la peine de frapper ce qui reste, c'est maintenant, pas plus tard.

La tumeur du poumon est petite, stable sur le plan anatomique, mais elle n'a pas disparu. C'est une bonne cible pour la **SBRT** -- la radiothérapie stéréotaxique, c'est-à-dire une forte dose délivrée très précisément, en peu de séances, avec des marges très petites autour de la cible.

Une chose a débloqué la décision : la zone de condensation apparue en avril à la base du poumon gauche, dont on ne savait pas si c'était une infection, une inflammation liée au traitement ou la maladie, a disparu. Tant qu'elle était là, toute irradiation thoracique était en pause, parce que je ne voulais pas irradier sans savoir ce que j'irradie.

La simulation a été faite le 21 juillet, et le traitement commence lundi 27 juillet, à l'Anadolu Medical Center d'Istanbul, sur un appareil Varian Edge.

**Ce que je ne sais pas encore :** la dose exacte, le nombre de séances et la règle concernant le comprimé -- si et combien de jours on l'arrête autour de la radiothérapie. L'équipe doit me le communiquer. Je l'ai demandé par écrit, parce que c'est le genre de détail qu'on ne veut pas retenir de mémoire.

J'ai déjà vécu une SBRT une fois, en janvier, pour la lésion de la colonne : trois séances, sur CyberKnife. La douleur dans le dos qui m'avait amené chez le médecin a disparu. Donc je n'entre pas en terrain inconnu.

## Trois appareils sous le même toit

La partie qui m'a sincèrement impressionné a été la discussion avec le radiothérapeute. Je ne savais pas qu'un seul centre pouvait avoir trois plateformes différentes de radiothérapie stéréotaxique, chacune avec son rôle. Je les laisse ici parce que c'est le genre de chose que j'aurais aimé savoir plus tôt.

**CyberKnife.** Un bras robotisé industriel avec un petit accélérateur linéaire monté au bout, sans statif. Il peut viser depuis plus de mille positions différentes. Sa particularité, c'est le suivi respiratoire continu : il met en relation le mouvement de la surface du corps avec la position interne de la tumeur, vérifie périodiquement par des radiographies en temps réel, et **déplace le faisceau en suivant la tumeur** pendant toute la séance. Tu n'as pas besoin de bloquer ta respiration. Le prix à payer : des séances longues.

**MR-Linac (à Anadolu, un Elekta Unity de 1.5 tesla, le premier de Turquie, depuis octobre 2024).** Une IRM de diagnostic combinée à un accélérateur linéaire. Pendant l'irradiation, tu vois la tumeur directement, en film continu, pas à travers un substitut. Et tu peux refaire le plan de traitement à chaque séance, en l'adaptant à ce à quoi le corps ressemble ce jour-là. C'est l'appareil qu'il faut quand la cible est collée à des organes mous qui bougent et se remplissent différemment d'un jour à l'autre : pancréas, foie, bassin, ou un ganglion voisin de l'œsophage ou de l'intestin. Le prix à payer : les séances les plus longues de toutes.

**Varian Edge.** Un accélérateur classique à bras en C, configuré spécialement pour la radiochirurgie et la SBRT. Il apporte un ensemble de dispositifs de précision : une surveillance optique continue de la surface du corps, avec arrêt automatique du faisceau si tu bouges au-delà de la tolérance ; une délivrance synchronisée avec la phase respiratoire ; un scanner à faisceau conique fait juste avant le traitement, pour vérifier la position ; une table robotisée qui corrige sur six axes, rotations comprises ; un collimateur à lames fines, qui coupe la dose de façon abrupte autour d'une petite cible ; et des faisceaux de forte intensité, qui raccourcissent beaucoup le temps effectif d'irradiation.

La différence de philosophie, si tu veux la retenir simplement : le CyberKnife et le MR-Linac **suivent** la cible en continu, chacun à sa manière. L'Edge **synchronise et vérifie** -- il traite dans la bonne phase respiratoire et confirme la position par l'imagerie, avec des séances beaucoup plus courtes.

Pour mon cas, l'équipe a proposé l'Edge. La précision "sous le millimètre" que tu vois dans les documents de n'importe quel fabricant est un chiffre obtenu en conditions de test, pas une garantie pour un patient donné -- les trois fabricants l'affichent. Ce qui compte, c'est la chaîne concrète de contrôle du mouvement, sur ta lésion.

{{< callout type="tip" >}}
Une bonne question à poser à ton équipe de radiothérapie, où que tu te fasses traiter : **"Pourquoi cet appareil-là, pour ma lésion, et pas l'autre ?"** La réponse est en général dosimétrique -- ce que reçoivent les organes autour -- et c'est une discussion qui mérite d'avoir lieu, pas une chose à supposer.
{{< /callout >}}

Ce qui m'a paru remarquable, c'est que les trois sont dans le même bâtiment, et que l'accès a été rapide. Pour un patient qui cherche cette technologie, le fait de ne pas devoir choisir entre des centres, mais de pouvoir choisir l'appareil qui te convient à l'intérieur du même centre, compte énormément.

## La question que je pèse encore : la radiothérapie et un éventuel vaccin

Il me reste une seule chose à peser, et il est honnête de dire qu'elle n'est pas réglée.

En parallèle du traitement, j'explore activement un vaccin personnalisé construit sur la particularité génétique de ma tumeur. Je suis en train de parler avec plusieurs centres qui font ce genre de chose. (J'en parle en détail dans [l'article suivant](/fr/blog/vaccins-personnalises-contre-le-cancer/).)

La question est de savoir si l'irradiation aide ou gêne un tel vaccin. Les arguments vont dans les deux sens :

**Pour.** La radiothérapie tue les cellules d'une façon qui peut libérer des antigènes tumoraux et attirer l'attention du système immunitaire -- une sorte de vaccination sur place. Il y a un détail technique intéressant : au-delà d'un certain seuil de dose par séance, la cellule active un mécanisme qui détruit l'ADN présent dans le cytoplasme et **annule** précisément le signal immunitaire recherché ([Vanpouille-Box, 2017](https://pubmed.ncbi.nlm.nih.gov/28598415/)). Autrement dit, plusieurs séances à dose modérée peuvent préserver plus d'effet immunitaire qu'une seule séance très forte.

**Contre.** La radiothérapie détruit aussi des lymphocytes -- exactement les cellules qu'un vaccin cherche à entraîner. Et il existe un grand essai randomisé dans le cancer du poumon oligométastatique, [NRG-LU002](https://clinicaltrials.gov/study/NCT03137771), qui n'a pas montré de bénéfice à ajouter la radiothérapie locale au traitement systémique. C'est un résultat que je n'ai pas le droit d'ignorer juste parce qu'il ne m'arrange pas.

Pour être juste dans l'autre sens aussi : cet essai a inclus des patients non sélectionnés, pas des patients sous comprimé ciblé comme moi. L'essai qui a testé exactement le scénario "comprimé ciblé plus radiothérapie locale" -- SINDAS, sur une autre mutation que la mienne -- a montré un bénéfice. La vérité est probablement quelque part au milieu : la radiothérapie locale n'est pas une panacée universelle, mais le contexte dans lequel tu la donnes compte énormément.

Une chose est claire et mérite d'être dite, parce que c'est une confusion facile à faire : **la radiothérapie ne touche pas le tissu à partir duquel le vaccin serait construit.** Celui-ci, c'est le bloc de paraffine de la biopsie de cette année, que j'ai physiquement chez moi. Ce sont deux choses complètement séparées.

J'ai posé la question directement à l'un des centres : s'il vaudrait mieux prélever les cellules avant la radiothérapie. J'attends la réponse. La règle que je me suis imposée entre-temps est simple : **je ne retarde pas la radiothérapie pour un vaccin qui n'a pas encore franchi ses propres seuils.** La radiothérapie est décidée, payée, simulée, sur une cible réelle. Le vaccin, pour l'instant, non.

## La suite du suivi

À partir du sixième mois, je passe à un rythme alterné, un examen tous les trois mois :

- **mois 9** (octobre 2026) -- TDM, cette fois **avec produit de contraste intraveineux** ;
- **mois 12** (janvier 2027) -- TEP-TDM plus IRM cérébrale ;
- **mois 15** -- TDM ; **mois 18** -- TEP-TDM plus IRM. Et ainsi de suite.

Un détail technique que je n'ai appris que maintenant et qui mérite d'être connu : **la composante TDM d'un TEP-TDM n'a pas de produit de contraste intraveineux** et n'en aura jamais, parce que son rôle est autre -- la correction d'atténuation. La bouteille que tu bois avant, c'est du produit de contraste oral, pour l'intestin, et les deux seringues sont le traceur et le sérum de rinçage. Si tu as besoin d'une mesure anatomique fine, elle vient d'une **TDM de diagnostic séparée, avec produit de contraste intraveineux** -- pas de la TEP.

## Où j'en suis, en fait

Six mois. Aucune nouvelle lésion. Une tumeur qui n'augmente pas, avec un frémissement métabolique que je ne peux pas certifier. Des ganglions millimétriques qui ne se sont pas éteints complètement. Et une bonne fenêtre, dans laquelle je choisis d'agir au lieu d'attendre.

Ce n'est pas une guérison et je ne prétends pas que ça en soit une. C'est une bonne position, que j'essaie de bien utiliser.

---

{{< action-box >}}
1. Demande que tous les examens de contrôle soient faits sur le **même appareil, dans le même centre** -- c'est la condition minimale, pas la garantie.
2. Demande **par écrit, à la prise de rendez-vous**, les mêmes paramètres d'acquisition qu'à l'examen précédent : temps d'attente après l'injection, corrections appliquées, version de reconstruction, protocole de produit de contraste.
3. Demande une **reconstruction standardisée EARL** comme série supplémentaire. Ça ne peut pas être fait rétroactivement.
4. S'il manque une valeur dans le compte rendu, **demande un complément**. C'est gratuit, ça prend peu de temps, et ça sauve ton graphique dans deux ans.
5. N'interprète pas une valeur SUV isolée. Demande les seuils PERCIST, la variabilité normale pour une lésion de la taille de la tienne, et ce que dit la composante TDM.
6. Si on te propose une radiothérapie stéréotaxique, demande **pourquoi cet appareil-là pour ta lésion** -- et demande par écrit la dose, le nombre de séances et la règle concernant le comprimé ciblé.
{{< /action-box >}}

---

{{< disclaimer >}}{{< /disclaimer >}}
