---
title: "PET-CT en el mes 6"
date: 2026-07-22
draft: false
description: "El control de los seis meses: tumor estable, ganglios algo activos, un aumento metabólico por debajo del umbral y la decisión de hacer SBRT en el pulmón."
tags: ["PET-CT", "seguimiento", "SBRT", "radioterapia estereotáctica", "cáncer de pulmón", "RET", "estadio IV", "SUV", "PERCIST", "CyberKnife", "MR-Linac"]
categories: ["Blog"]
translationKey: "blog-month-6-results"
weight: 30
author: "OncoGuide"
ShowToc: false
TocOpen: false
---

**En resumen:** Me he hecho el PET-CT de control a los seis meses de tratamiento. La gran noticia es buena: ninguna lesión nueva, en ninguna parte. Pero el tumor principal aparece un poco más intenso que en abril, y los ganglios que se habían reducido siguen estando, milimétricamente, un poco activos. Este artículo va de lo que dicen en realidad las cifras, de por qué la comparación entre dos estudios no salió tan limpia como había planeado -- aunque usé el mismo equipo -- y de la decisión que he tomado: radioterapia estereotáctica sobre el tumor del pulmón, lo antes posible.

---

## Dónde estaba antes del estudio

Desde febrero tomo una pastilla dirigida para la fusión RET de mi tumor. ([La historia desde el principio está aquí](/es/blog/mi-historia/), y sobre cómo pienso la estrategia escribí [aquí](/es/blog/standard-of-care-y-medicina-personalizada/).)

La respuesta fue profunda. En el control de los tres meses, el tumor del pulmón había bajado en actividad metabólica casi por completo, la lesión de la columna -- tratada al principio con radioterapia -- se había calmado, y la metástasis de la pelvis había desaparecido.

El estudio de los seis meses era, por tanto, la primera comprobación real de la pregunta: ¿aguanta?

## Lo que mostró el estudio

Lo más importante primero, porque es lo que más cuenta: **ninguna lesión nueva, en ninguna parte**. Cerebro, cuello, abdomen, pelvis, hígado, bazo, suprarrenales, páncreas -- todo limpio. La resonancia magnética cerebral, hecha aparte una semana antes, salió limpia por tercera vez consecutiva.

El resto es más matizado, y precisamente por eso merece contarse con honestidad.

**El tumor principal del pulmón** tiene el mismo tamaño que en abril, alrededor de 16 mm. Pero el radiólogo lo describe como "metabólicamente más evidente que en el estudio anterior". En cifras: el valor SUV (una medida de cuánto azúcar radiactivo consume el tejido, es decir, un indicador indirecto de actividad) ha subido de 2.0 en abril a 3.2 en julio. Para contexto, en el diagnóstico era 19.2.

**Los ganglios** del mediastino miden menos de 10 mm y se describen como "similares, con regresión en algunos puntos" respecto a abril, con un valor de 5. Su trayectoria, desde el principio hasta ahora, es así: 13.7, después 8.3, ahora 5. Es decir, exactamente lo que decía al principio: oficialmente regresados, milimétricos -- pero la conclusión del informe los sigue llamando hipermetabólicos. No se han apagado del todo. Ha quedado actividad, y ahora es la más alta de las lesiones que me quedan.

**La lesión de la columna**, tratada al principio, está estable. Y una zona de condensación que apareció en abril en la base del pulmón izquierdo, de la que no se sabía si era inflamación u otra cosa, **ha desaparecido** del informe de ahora. Esa fue, en realidad, la noticia que desbloqueó la decisión de la que hablo más abajo.

{{< callout type="tip" >}}
Si lees un informe de PET-CT: el valor SUV no es "cuán grande es el cáncer". Es cuánta glucosa consume ese tejido en el momento del estudio. La inflamación también consume. La cicatrización también consume. Por eso un número solo, sin contexto y sin una comparación correcta, dice menos de lo que parece.
{{< /callout >}}

## Usé el mismo equipo. Y aun así no salió una comparación limpia.

Esta es la parte que de verdad quiero dejar escrita, porque es la lección más útil que he aprendido este mes.

Pensé en la comparabilidad con antelación. Insistí en hacer todos los estudios en el **mismo equipo**, en el mismo centro, con el mismo protocolo. Creía que eso bastaba para poder comparar honestamente dos números.

No basta. Miré los archivos DICOM en bruto -- los datos técnicos que el equipo escribe en cada imagen -- y encontré varias diferencias entre abril y julio. Ninguna es un error de nadie. Todas juntas hacen que los dos números no sean rigurosamente comparables.

- **El tiempo de espera tras la inyección.** En abril pasaron 99 minutos entre la inyección del trazador y el estudio. En julio, 55 minutos. El tumor sigue acumulando trazador durante horas, así que un tiempo más corto **subestima** el valor. Es decir, este factor trabaja en contra del aumento observado, no a favor.
- **La corrección del movimiento respiratorio.** En julio se aplicó un algoritmo de corrección del movimiento que en abril no se había aplicado. Una lesión que se mueve con la respiración aparece "estirada" y diluida; cuando corriges el movimiento, recuperas la señal y el valor **sube**, con la misma biología.
- **La versión del software de reconstrucción** se actualizó entre los dos estudios, e incluía además una corrección adicional de dispersión.
- **Mi peso** subió de 77 a 79 kg. El SUV se normaliza por el peso, así que solo eso ya añade mecánicamente un 2.6 por ciento.
- **La cantidad de contraste oral** fue aproximadamente la mitad que en abril. No afecta al pulmón, pero sí a lo bien que se separan las estructuras del abdomen.
- **La estandarización EARL** -- un procedimiento por el cual el laboratorio entrega, además, una reconstrucción calibrada según un estándar europeo, precisamente para que los valores sean comparables en el tiempo -- la pedí al reservar la cita. No se entregó en ninguno de los dos estudios.

He llegado a una conclusión que no conocía: **el mismo equipo no significa automáticamente las mismas condiciones.** La comparabilidad no es una propiedad de la máquina, es un procedimiento que hay que pedir de forma explícita, por escrito, cada vez.

{{< callout type="important" >}}
Lo que pido de ahora en adelante, en cada cita de PET-CT, y lo que te sugeriría pedir a ti también por escrito:

1. El mismo tiempo de espera tras la inyección que en el estudio anterior (la tolerancia estándar es de más/menos 15 minutos).
2. Las mismas correcciones aplicadas (movimiento, dispersión) y la misma versión de reconstrucción, o al menos que se mencionen de forma explícita en el informe.
3. Una reconstrucción estandarizada [EARL](https://earl.eanm.org/) adicional -- pedida al reservar la cita, porque no se puede hacer de forma retroactiva una vez que los datos en bruto se han borrado.
4. El mismo protocolo de contraste.
5. Una lista fija de lesiones diana, informadas con valores numéricos en cada control y comparadas con **todos** los estudios anteriores, no solo con el último.
{{< /callout >}}

## ¿Entonces ha crecido o no?

La respuesta honesta es: ha subido un poco, pero esa subida no significa progresión. Y merece la pena explicar por qué, porque es exactamente el tipo de matiz que asusta sin necesidad.

Existe un conjunto de criterios internacionales para decidir cuándo un cambio en el PET significa progresión, llamado [PERCIST](https://pubmed.ncbi.nlm.nih.gov/19403881/). Para hablar de progresión metabólica hace falta un aumento de al menos el 30 por ciento **y**, a la vez, un aumento absoluto de al menos 0.8 unidades. En mi caso, el aumento fue de alrededor del 25 por ciento y de 0.32 unidades en términos absolutos. No alcanza ninguno de los dos umbrales.

Más aún: para una lesión tan pequeña, la variabilidad normal entre dos estudios repetidos del mismo tumor sin cambios es del orden del 30-50 por ciento. El aumento observado entra cómodamente dentro del ruido de medición.

Y algo más: mi lesión está, en ambos momentos, por debajo del umbral a partir del cual PERCIST considera que una lesión es medible. Sus valores están por debajo del nivel del hígado. En la práctica, los criterios ni siquiera fueron concebidos para una diana tan pequeña.

Pero el argumento más importante viene de otro lado. El PET tiene todas las confusiones de arriba. **El componente CT del mismo estudio no tiene ninguna** -- no depende del tiempo de espera, de la corrección del movimiento ni de la versión del software del PET. Y el CT dice, abril frente a julio: diámetro 13.5 mm, sin cambios. El volumen de la parte sólida, ligeramente menor. La densidad, sin cambios. (Estas mediciones son mías, calculadas en casa a partir de las imágenes en bruto con herramientas de IA -- no aparecen como tales en el informe del radiólogo.)

Así que: **estable, no progresión, con un cambio metabólico por debajo del umbral.** No digo "plano", porque hay un aumento pequeño y real. Y no digo "artefacto", porque el factor más grande -- el tiempo de espera -- trabajaba en su contra. Digo exactamente lo que es: una lesión que no crece, con un parpadeo metabólico que no puedo certificar.

{{< callout type="tip" >}}
Una aclaración que creo que es útil. Las cifras de arriba -- el volumen de la parte sólida, la densidad, las comparaciones entre los dos estudios -- no vienen del informe. Las calculé yo mismo, en casa, a partir de los archivos DICOM en bruto, con herramientas de IA.

No es algo reservado a los especialistas. Las imágenes en bruto son tuyas y puedes pedirlas en un pendrive o en un CD en cada estudio. En mi caso, la diferencia entre "he leído el informe" y "he medido yo mismo esas mismas imágenes" fue la diferencia entre el pánico y una decisión tranquila.
{{< /callout >}}

## Lee el informe palabra por palabra

Un percance que merece contarse, porque estuve a punto de publicar otra cosa.

Durante unos días estuve convencido de que el informe no daba ningún valor numérico para los ganglios. Ya me había construido una pequeña teoría alrededor de eso: que era una omisión del informe, que debería pedir una ampliación.

Me equivocaba. El número estaba ahí. Estaba entre paréntesis, al final de una frase de cuatro líneas que empezaba con otra cosa y terminaba en la página siguiente. Se me pasó, y luego construí encima de ese despiste.

La lección, para cualquiera que lleve un historial médico a largo plazo: **lee el informe tú mismo, frase por frase, y saca los números a una tabla propia.** Los valores suelen estar entre paréntesis al final de una frase, no en sitios evidentes, y una sola frase puede describir tres grupos distintos de lesiones con tres valores distintos. Y si de verdad falta algo, un informe **se puede ampliar** -- se pide con educación, es gratis y tarda poco.

## La decisión: radioterapia sobre el tumor del pulmón, ahora

Aquí llego a la parte de la acción.

La lógica que sigo es la que escribí la vez pasada: el menor número de células cancerosas que voy a tener jamás es el de ahora, mientras la pastilla mantiene la enfermedad a raya. Si hay un momento en el que merece la pena golpear lo que ha quedado, ese momento es ahora, no más tarde.

El tumor del pulmón es pequeño, anatómicamente estable, pero no ha desaparecido. Es una buena diana para la **SBRT** -- radioterapia estereotáctica corporal, es decir, una dosis alta administrada con mucha precisión, en pocas sesiones, con márgenes muy pequeños alrededor de la diana.

Una cosa desbloqueó la decisión: la zona de condensación que apareció en abril en la base del pulmón izquierdo, de la que no se sabía si era infección, inflamación por el tratamiento o enfermedad, ha desaparecido. Mientras estuvo ahí, cualquier irradiación torácica estaba en pausa, porque no quería irradiar sin saber qué estoy irradiando.

La simulación se hizo el 21 de julio, y el tratamiento empieza el lunes 27 de julio, en el Anadolu Medical Center de Estambul, en un equipo Varian Edge.

**Lo que aún no sé:** la dosis exacta, el número de sesiones y la regla sobre la pastilla -- si se para y cuántos días alrededor de la radioterapia. El equipo me lo va a comunicar. Lo he pedido por escrito, porque es el tipo de detalle que no quieres recordar de oídas.

Ya pasé por la SBRT una vez, en enero, para la lesión de la columna: tres sesiones, en CyberKnife. El dolor de espalda que me había llevado al médico desapareció. Así que no entro en terreno desconocido.

## Tres equipos bajo el mismo techo

La parte que sinceramente me impresionó fue la conversación con el oncólogo radioterápico. No sabía que un solo centro puede tener tres plataformas distintas de radioterapia estereotáctica, cada una con su papel. Las dejo aquí porque es el tipo de cosa que me habría gustado saber antes.

**CyberKnife.** Un brazo robótico industrial con un pequeño acelerador lineal montado en el extremo, sin gantry. Puede apuntar desde más de mil posiciones distintas. Su particularidad es el seguimiento respiratorio continuo: correlaciona el movimiento de la superficie del cuerpo con la posición interna del tumor, comprueba periódicamente con radiografías en tiempo real, y **mueve el haz siguiendo al tumor** durante toda la sesión. No necesitas aguantar la respiración. El coste: sesiones largas.

**MR-Linac (en Anadolu, un Elekta Unity de 1.5 teslas, el primero de Turquía, desde octubre de 2024).** Una resonancia magnética de diagnóstico combinada con un acelerador lineal. Durante la irradiación ves el tumor directamente, en película continua, no a través de un sustituto. Y puedes rehacer el plan de tratamiento en cada sesión, adaptándolo a cómo está el cuerpo ese día. Es el equipo adecuado cuando la diana está pegada a órganos blandos que se mueven y se llenan de forma distinta de un día para otro: páncreas, hígado, pelvis, o un ganglio vecino al esófago o al intestino. El coste: las sesiones más largas de todas.

**Varian Edge.** Un acelerador clásico con brazo en C, configurado especialmente para radiocirugía y SBRT. Trae un paquete de precisión: monitorización óptica continua de la superficie del cuerpo, con parada automática del haz si te mueves fuera de la tolerancia; administración sincronizada con la fase de la respiración; un CT de haz cónico hecho justo antes del tratamiento, para verificar la posición; una mesa robótica que corrige en seis ejes, incluidas las rotaciones; un colimador de láminas finas, que corta la dosis de forma abrupta alrededor de una diana pequeña; y haces de intensidad alta, que acortan mucho el tiempo efectivo de irradiación.

La diferencia de filosofía, si quieres quedarte con lo simple: CyberKnife y MR-Linac **siguen** la diana de forma continua, cada uno a su manera. Edge **sincroniza y verifica** -- trata en la fase correcta de la respiración y confirma la posición con imagen, con sesiones mucho más cortas.

Para mi caso, el equipo propuso el Edge. La precisión de "menos de un milímetro" que ves en los materiales de cualquier fabricante es una cifra obtenida en condiciones de prueba, no una garantía para un paciente concreto -- los tres fabricantes la muestran. Lo que cuenta es la cadena concreta de control del movimiento, sobre tu lesión.

{{< callout type="tip" >}}
Una buena pregunta para hacerle a tu equipo de radioterapia, te trates donde te trates: **"¿Por qué este equipo, para mi lesión, y no el otro?"** La respuesta suele ser dosimétrica -- cuánto reciben los órganos de alrededor -- y es una conversación que merece la pena tener, no una que debas dar por supuesta.
{{< /callout >}}

Lo que me pareció notable es que los tres están en el mismo edificio, y que el acceso fue rápido. Para un paciente que busca esta tecnología, el hecho de no tener que elegir entre centros, sino de poder elegir el equipo adecuado para ti dentro del mismo centro, cuenta enormemente.

## La pregunta que aún estoy sopesando: la radioterapia y una posible vacuna

Me queda una sola cosa por sopesar, y es honesto decir que no está resuelta.

En paralelo al tratamiento, estoy investigando activamente una vacuna personalizada construida sobre la particularidad genética de mi tumor. Ahora mismo estoy hablando con varios centros que hacen algo así. (De eso escribo con detalle en [el artículo siguiente](/es/blog/vacunas-personalizadas-contra-el-cancer/).)

La pregunta es si la irradiación ayuda o estorba a una vacuna así. Los argumentos van en las dos direcciones:

**A favor.** La radioterapia mata las células de una forma que puede liberar antígenos tumorales y puede atraer la atención del sistema inmunitario -- una especie de vacunación in situ. Hay un detalle técnico interesante: por encima de cierto umbral de dosis por sesión, la célula activa un mecanismo que destruye el ADN del citoplasma y **anula** justo la señal inmunitaria que se busca ([Vanpouille-Box, 2017](https://pubmed.ncbi.nlm.nih.gov/28598415/)). Dicho de otro modo, varias sesiones con dosis moderada pueden conservar más efecto inmunitario que una sola sesión muy grande.

**En contra.** La radioterapia también destruye linfocitos -- justo las células que una vacuna quiere entrenar. Y existe un ensayo aleatorizado grande en cáncer de pulmón oligometastásico, [NRG-LU002](https://clinicaltrials.gov/study/NCT03137771), que no mostró beneficio al añadir radioterapia local al tratamiento sistémico. Es un resultado que no me está permitido ignorar solo porque no me conviene.

Para ser justo también en la otra dirección: ese ensayo incluyó pacientes no seleccionados, no pacientes en una pastilla dirigida como yo. El ensayo que probó exactamente el escenario "pastilla dirigida más radioterapia local" -- SINDAS, en otra mutación distinta de la mía -- sí mostró beneficio. La verdad está probablemente en algún punto intermedio: la radioterapia local no es una panacea universal, pero el contexto en el que la das cuenta enormemente.

Una cosa está clara y merece decirse, porque es una confusión fácil de cometer: **la radioterapia no toca el tejido con el que se construiría la vacuna.** Ese es el bloque de parafina de la biopsia de este año, que tengo físicamente conmigo. Son dos cosas completamente separadas.

Le he hecho la pregunta directa a uno de los centros: si sería mejor extraer las células antes de la radioterapia. Espero la respuesta. La regla que me he impuesto mientras tanto es sencilla: **no retraso la radioterapia por una vacuna que todavía no ha superado sus propios umbrales.** La radioterapia está decidida, pagada, simulada, sobre una diana real. La vacuna, por ahora, no.

## Qué viene en el seguimiento

A partir del mes 6 paso a un ritmo alterno, un estudio cada tres meses:

- **mes 9** (octubre de 2026) -- CT, esta vez **con contraste intravenoso**;
- **mes 12** (enero de 2027) -- PET-CT más resonancia magnética cerebral;
- **mes 15** -- CT; **mes 18** -- PET-CT más resonancia. Y así sucesivamente.

Un detalle técnico que he sabido apenas ahora y que merece la pena conocer: **el componente CT de un PET-CT no lleva contraste intravenoso** y nunca lo va a llevar, porque su papel es otro -- la corrección de la atenuación. La botella que bebes antes es contraste oral, para el intestino, y las dos jeringas son el trazador y el suero de lavado. Si necesitas una medición anatómica fina, esa viene de un **CT diagnóstico aparte, con contraste intravenoso** -- no del PET.

## Dónde estoy, en realidad

Seis meses. Ninguna lesión nueva. Un tumor que no crece, con un parpadeo metabólico que no puedo certificar. Unos ganglios milimétricos que no se han apagado del todo. Y una buena ventana, en la que elijo actuar en lugar de esperar.

No es curación y no pretendo que lo sea. Es una buena posición, que intento usar bien.

---

{{< action-box >}}
1. Pide que todos los estudios de control se hagan en el **mismo equipo, en el mismo centro** -- es la condición mínima, no la garantía.
2. Pide **por escrito, al reservar la cita**, los mismos parámetros de adquisición que en el estudio anterior: tiempo de espera tras la inyección, correcciones aplicadas, versión de reconstrucción, protocolo de contraste.
3. Pide una **reconstrucción estandarizada EARL** como serie adicional. No se puede hacer de forma retroactiva.
4. Si falta un valor en el informe, **pide una ampliación**. Es gratis, tarda poco, y te salva el gráfico de dentro de dos años.
5. No interpretes un solo valor SUV de forma aislada. Pregunta por los umbrales PERCIST, por la variabilidad normal para una lesión del tamaño de la tuya, y por lo que dice el componente CT.
6. Si te proponen radioterapia estereotáctica, pregunta **por qué ese equipo para tu lesión** -- y pide por escrito la dosis, el número de sesiones y la regla sobre la pastilla dirigida.
{{< /action-box >}}

---

{{< disclaimer >}}{{< /disclaimer >}}
