# Brein v3: dichter bij een echt brein

Gebruik Opus. Werk per fase, en laat mij na elke fase de simulatie zien voordat je verdergaat.

Volgorde over alle plannen heen:

1. VOLGENDE.md blok B
2. VOLGENDE.md blok C
3. Dit bestand, fase 1 en 2
4. VOLGENDE.md blok D (WERELD.md, met blok E)
5. Dit bestand, fase 3 (heeft echte bezoekers uit WERELD stap 3-4 nodig)

Begin dus niet aan dit bestand voordat B en C klaar en getest zijn.

Elk onderdeel hieronder is een versimpelde versie van een mechanisme uit de cognitieve neurowetenschap. Het doel is niet dat hij "echt" denkt, maar dat zijn gedrag leert, verrast en minder in rondjes loopt. Als een onderdeel in de simulatie niks zichtbaars verandert, zeg dat dan eerlijk en laat het weg.

## Vaste regels

- Code beslist, het model praat. Alles hieronder is gewone Python in `drive/`. Er komen geen extra LLM-calls bij, behalve waar dat expliciet staat.
- Bestaande data blijft bewaard. Nieuwe velden voeg je toe, oude JSON-velden blijven werken (de site leest ze).
- Alle getallen als constanten bovenaan het bestand, zoals nu in `needs.py` en `engine.py`.
- Alles per `character_id`, zodat een tweede karakter later hetzelfde brein kan krijgen.
- Breid `drive/sim.py` uit zodat elke fase een eigen check heeft (zie onder elke fase). Draai 300 ticks, met een vaste seed.

## Fase 1: leren van verrassing

> Status 15-11-2026: built in `drive/learn.py`, waiting for Noah's go. Check: `python -m drive.sim --ticks 300
> --seed 1 --start 2026-11-15T09:00:00+01:00 --quiet --check 1`. Habituation/novelty clearly changes behaviour
> (top-place share 32% -> 19% over 8 seeds); V steers mildly (AH 30% -> 36% of meals over 2000 ticks) and now
> drives the facts; Yerkes-Dodson changed nothing visible, so `YD_DEPTH = 0` (code kept). REPEAT/LATELY lowered,
> not removed.

### 1. Voorspelling en predictiefout (dopamine-achtig leren)
Nu tellen overtuigingen alleen de moodverandering per `action@place` op (`beliefs.py`). Vervang dat door echt leren:

- Per `action@place` een verwachte waarde `V` (begint op 0).
- Voor een actie start: sla `V` op als verwachting.
- Na afloop: `uitkomst = dmood + 0.5 * met` (wat de actie echt opleverde). Predictiefout `delta = uitkomst - V`. Update: `V += ALPHA * delta` met `ALPHA` rond 0.15.
- `beliefs.bonus()` gebruikt voortaan `V` in plaats van de opgetelde stats. Overtuigingen (en de genummerde feiten uit blok B) blijven de verwoording van `V`: een feit ontstaat als `V` duidelijk boven of onder zijn gemiddelde ligt en de bewijsteller hoog genoeg is.
- `delta` wordt opgeslagen bij de herinnering van die actie (`surprise`, intern veld, niet in de publieke JSON).

### 2. Gewenning en nieuwigheid
- Per prikkel (plek, interesse-onderwerp) een gewenningswaarde `h` van 0 tot 1. Elke keer dat hij iets meemaakt: `h += 0.2`. Per tick zakt `h` langzaam terug.
- Wat hij gewend is, levert minder op: de relief van een actie wordt vermenigvuldigd met `(1 - 0.5 * h)`.
- Een plek waar hij nog nooit (of lang niet) was, geeft een nieuwigheidsbonus op nieuwsgierigheid.
- Dit mag een deel van `REPEAT_PENALTY` en `LATELY_PENALTY` vervangen. Haal ze niet allebei helemaal weg voordat de sim laat zien dat gewenning het werk overneemt.

### 3. Emotie op twee assen
- Naast mood (valentie, -1 tot 1) komt `arousal` (0 tot 1). Omhoog door verrassing (`|delta|`), reizen, bezoekers en schrikken. Omlaag door stilzitten en slaap.
- Prestatie volgt een omgekeerde U (Yerkes-Dodson): de kans dat zoeken of tekenen lukt is het hoogst bij middelmatige arousal en zakt bij te laag of te hoog.
- Code kiest een emotielabel uit valentie x arousal (bv. tevreden, opgewonden, geprikkeld, futloos, kalm). Het model krijgt alleen het label, niet de getallen.

Check fase 1: laat per `action@place` zien hoe `V` over de ticks loopt, hoeveel verschillende plekken hij bezoekt (moet omhoog ten opzichte van nu), en een histogram van arousal. Hij moet niet blijven hangen op max arousal of op 0.

## Fase 2: geheugen en slaap

> Status 15-11-2026: built, waiting for Noah's go (phase 1 too: neither is committed). Check:
> `python -m drive.sim --ticks 900 --seed 1 --start 2026-11-15T09:00:00+01:00 --quiet --check 2`.
> 4: `drive/attend.py`; voice.context now gets only these items ("On your mind"), the general beliefs line is gone
> (a belief about the current action competes as an item); a note's own words never enter WM. Winner over 900
> ticks: memory, outcome, goal, need, seen all win regularly. 5: dreams weighted by |surprise| (visible: replayed
> memories mostly have |surprise| > 0.15), reconsolidation on every recall. Replay-learning V changed nothing
> visible (6 seeds x 1000 ticks), so `ALPHA_REPLAY = 0` (code kept). 6: forgetting curve in `memory.py`
> (`S_BASE = 1.0`; at 1.5 nothing faded in 5 nights); unrecalled day summaries go after ~5 world days, recalled or
> emotional ones reach S 10-30. Old memories get a curve that starts at the upgrade, so nothing is lost at once.

### 4. Werkgeheugen en aandacht
- Maximaal 4 dingen "in zijn hoofd": bijvoorbeeld de dringendste behoefte, zijn huidige doel, een opgehaalde herinnering en iets wat hij net zag (een briefje, een plek, een bezoeker).
- Ze strijden om een plek op saillantie: urgentie van de behoefte, `|delta|`, nieuwigheid, emotionele lading. Wat niet wint, valt eruit.
- Alleen deze 4 gaan naar het model als context. Zo blijft de prompt klein en klinkt hij alsof hij met iets bezig is.
- Het winnende item wordt `loudest` in `mind.json` (dat veld bestaat al).

### 5. Slaap als replay
- Blok B laat hem dromen met willekeurige herinneringen. Maak de keuze gewogen: herinneringen met de grootste verrassing worden vaker herbeleefd (zoals replay in de hippocampus).
- Tijdens die replay wordt `V` van die `action@place` nog een keer bijgewerkt, met een kleinere `ALPHA`. Hij leert dus ook in zijn slaap.
- De droom blijft 1 LLM-call per nacht en is de verwoording van precies die herbeleefde mix.
- Een herinnering die wordt opgehaald, schuift met zijn `feel` een klein stukje richting zijn huidige mood (reconsolidatie). Een slechte week kleurt dus oude herinneringen een beetje.

### 6. Vergeten volgens een curve
- Vervang de vaste `NIGHT_FADE` in `memory`/`sleep` door een vergeetcurve: `behoud = exp(-t / S)`, met `t` de tijd sinds hij er voor het laatst aan dacht.
- `S` (stabiliteit) groeit elke keer dat hij een herinnering ophaalt, en meer als er tijd tussen zat (spacing-effect).
- Emotionele herinneringen (`|feel|` hoog) beginnen met een hogere `S`.
- Onder een drempel valt een herinnering weg, ook als er nog plek is.

Check fase 2: laat zien welke herinneringen na 5 sim-nachten nog bestaan en waarom, en wat er in werkgeheugen zat bij 10 willekeurige ticks.

## Fase 3: vooruitdenken en anderen

### 7. Vooruitdenken (allostase)
- Bij het kiezen van een actie met reistijd rekent hij uit hoe zijn behoeftes eruitzien bij aankomst. Is honger of rust daar al boven `PRESSING`, dan krijgt die actie een straf en een eet- of rustactie een bonus.
- Eén stap vooruit is genoeg. Geen zoekboom.

### 8. Een model van bezoekers
- Per bezoeker (op naam) een klein profiel: vertrouwen (-1 tot 1), hoe zijn briefjes meestal voelden, wat hij meestal achterlaat.
- Een nieuw briefje wordt vergeleken met wat hij van die bezoeker verwacht. Ook hier een predictiefout: valt iemand mee of tegen, dan verschuift het vertrouwen.
- Vertrouwen bepaalt mee of hij reageert, negeert of weigert (sluit aan op blok B1, geen spiegel).

### 9. Metacognitie
- Elke overtuiging krijgt een zekerheid, uit de bewijsteller en hoe wisselend de uitkomsten waren.
- Het model krijgt een label mee: zeker, vermoeden of geen idee. Hij zegt dan "I know", "I suspect" of "no idea", en kan zich vergissen met veel zelfvertrouwen als de data dat zegt.

Check fase 3: een sim met drie nepbezoekers (een aardige, een vervelende, een wisselende) en laat zien hoe het vertrouwen per bezoeker loopt.

## Later, voor de site
Een tab "hersenscan" in dagboek.exe met de huidige `V`-waarden als kleine balkjes, het werkgeheugen en de emotie op de twee assen. Niet nu bouwen, alleen de data er alvast voor in `mind.json` zetten.
