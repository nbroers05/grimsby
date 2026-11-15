# Volgende stappen (na BREIN-v2)

Lees dit pas als BREIN-v2 klaar is. Alles hieronder is na het begin van BREIN-v2 besloten. Doe het in deze volgorde, en laat mij na elk blok testen voordat je verdergaat. Check bij elk punt eerst wat er al gebouwd is, zodat je niks dubbel doet.

## A. BREIN-v2 stap 12: wereld als kaart

Deze stap is aan BREIN-v2.md toegevoegd nadat je eraan begon. Lees stap 12 in BREIN-v2.md en voer hem uit als dat nog niet gebeurd is: `world/places.json` met 8-12 plekken in Berkel en Rodenrijs, acties gekoppeld aan plekken, reistijd kost energie, het brein weet niks van de 3D.

## B. Brein-aanvullingen

> Status 14-11-2026: built, waiting for Noah's test (together with the E brain change: hunger + place-bound beliefs).
> B1 `drive/notes.py` + `voice.reply_note` (not wired to visitors yet: that is WERELD step 3), B2 `beliefs.py`
> (fact numbers in `state["facts"]`, `n` in memories.json), B3 `sleep.py` dreams -> log.json action `dream`,
> B4 `who.py` `version` + `changelog`. Eating places in places.json confirmed by Noah (AH centre, Jumbo by the
> station, McDonald's, Döner & Zo as De Turk).

1. Geen spiegel. Hij volgt bezoekers niet automatisch. Op basis van zijn behoeftes, principes (holdsTo) en stemming mag hij een briefje negeren, weigeren, verkeerd begrijpen of het oneens zijn. Leg dat vast in de code die bepaalt of en hoe hij reageert, en in de prompt voor antwoorden: geen "wat leuk dat je dat zegt"-antwoorden, geen verwachte beleefdheid. Hij is geen assistent.
2. Feiten. Elke overtuiging krijgt een volgnummer op het moment dat hij ontstaat ("feit 14"). Als een actie mislukt (`ok: false`) en daar een overtuiging uit volgt, eindigt die met een droge afsluiter in zijn eigen woorden, in de trant van "dat doe ik niet nog eens". Sla het nummer op in memories.json.
3. Dromen. Tijdens de slaap-consolidatie maakt hij 1 droom: een korte, rommelige mix van 3-5 willekeurige herinneringen uit kort en lang geheugen, door elkaar gehusseld. 1 LLM-call per nacht. Komt in het dagboek als soort `droom`.
4. Versies. Elke nacht dat het karakterblad verandert (het `added`-veld), telt een versienummer op. Sla per versie op wat er veranderd is (`who.json`: `version` en `changelog[]`).

## C. Site-aanpassingen

Zie de mockups in `mockup/`. Nieuw sinds de eerste versie:

1. `mockup/World.dc.html`: het uitgevouwen wereldscherm. Main.dc.html heeft nu een knop "uitvouwen" in de titelbalk van wereld.exe en een knop "Loop rond in zijn wereld". Uitgevouwen is de wereld volledig scherm met als HUD: behoeftes linksboven (de dringendste in rood), een wegklikbaar nu-kaartje midden boven, klok + wereldtijd + minikaart + knop "inklappen" rechtsboven, bezoekers linksonder, besturingshint onderin, rode knop "Laat iets achter" rechtsonder met een venster (naam, voorwerp kiezen, briefje max 280 tekens). Inklappen gaat terug naar de gewone site.
2. Nieuwe tab "feiten" in dagboek.exe: zijn overtuigingen als genummerde feiten, nieuwste bovenaan, met de bewijsteller klein erbij.
3. Dromen tonen in de dagboek-tab, herkenbaar als droom (bijvoorbeeld cursief of met een eigen label).
4. In de over-tab: "versie N van hem" met wat er die nacht veranderd is.

## D. WERELD.md

Daarna WERELD.md, stap 1 t/m 4 (lopen, Supabase live, iets achterlaten, andere bezoekers). Lees eerst blok E hieronder: daar staat hoe de wereld zelf gebouwd en ontworpen wordt. Aanvullingen op WERELD.md:

1. Briefjes in het zand. Een briefje van een bezoeker verschijnt in de wereld als tekst op de grond, op de plek waar het is neergelegd (bij voorkeur aan de waterkant). Zijn antwoord verschijnt er bij een volgende tick naast, ook als tekst op de grond. Andere bezoekers kunnen beide lezen. Daarnaast blijft het antwoord ook zichtbaar voor de schrijver bij een volgend bezoek.
2. Geen inhoudsfilter op wat bezoekers schrijven. Wel: max 280 tekens, rate limit per bezoeker, en tekst van bezoekers start nooit zelf een actie of tool (zie WERELD.md stap 3).

## E. Wereldontwerp (hoort bij WERELD.md stap 1, lees dit eerst)

### Techniek
- Gebouwen: 3DBAG (3dbag.nl), LoD 1.2, tiles voor Berkel en Rodenrijs. Wegen, water/sloten, parken, kassen: OpenStreetMap (Overpass API).
- Omrekenen van RD (EPSG:28992) naar lokale meters rond een vast middelpunt. Gebruik hetzelfde middelpunt in world/places.json.
- Preprocessing als Python-script: output 1 geoptimaliseerde .glb (geometrie samengevoegd per type, Draco-compressie) + botsvlakken (2D-plattegronden) als JSON.
- Laadtijd onder 5 seconden op mijn laptop. Begin met een gebied dat alle plekken hieronder bevat, rest in mist.
- Laat mij de .glb eerst in een simpele viewer checken.

### Stijl
- Low-poly geometrie, platte vlakken, geen texturen.
- MeshToonMaterial met 3 lichtstappen en een zachte gradientMap. Geen harde zwarte schaduwen.
- Kleuren uit de Noah Huisstijl: woningen paper #efe9dc / paper-raised #f8f4ea, water en lucht sky #8cc0e8, daken en schaduwkant zacht eva #1b2a8c, kassen half-transparant met sky-tint. Rood #d7261e voor 1 ding per scene: zijn huidige plek.
- Dunne outline in ink #16130f op gebouwranden als aan/uit-instelling.
- Licht volgt de huisstijl-standen: Digital Future (ochtend), Poster (middag), Titelkaart (avond, alleen lantaarns en ramen geven licht).
- Gevoel: A Short Hike, Pino's wereld. Knus, een beetje speelgoed.

### Plekken (world/places.json)
Zoek de echte locaties op via OSM/Nominatim en laat mij de coordinaten checken voordat je bouwt. Bestaat een plek niet of vind je hem niet: vraag het mij, niet gokken.

| Plek | Wat hij er doet | Wat er staat |
|---|---|---|
| Speeltuin bij zijn nest | slapen, stilte, rust | zijn nest in een boom, hier slaapt hij |
| Albert Heijn | eten, mensen kijken (sociaal) | winkelwagens, een bankje bij de ingang |
| Jumbo | eten | hij vindt de AH beter, en dat mag hij laten merken |
| McDonald's | eten | een vuilnisbak met patat, uiteraard |
| De Turk | eten | terras |
| Cafe Het Centrum | zoeken op internet, sociaal | een tafeltje aan het raam (zoals Pino's cafe) |
| Metro Rodenrijs | rondkijken, nieuwsgierigheid | perron; hier komen bezoekers binnen |
| Metro Berkel Westpolder | rondkijken, nieuwsgierigheid | perron; vliegen tussen de twee stations is zijn "treinreis" |
| Basisschool Het Baken | tekenen, leren | schoolplein; zijn tekeningen hangen hier aan het hek |
| Voetbalveld | rondlopen, energie kwijtraken | doel, middenstip |
| Windas (zwembad / water) | stilte, dagboek | waterkant; hier liggen de briefjes in het zand |

Overige plekken die ik noemde (Daansshop, kapper Cuts and More, tandarts Meijer, Casa Cadenza, Anytime Fitness) komen erin als herkenbaar decor zonder actie. Valkenhof 41 is mijn huis: geen label, geen actie.

### Brein-aanpassing
De helft van de plekken gaat over eten. Voeg een zesde behoefte toe: honger (zoals Pino's fullness), die je bevredigt bij de eetplekken. Overtuigingen mogen plekgebonden zijn ("de McDonald's is beter dan de Jumbo", evidence: 9).

### De kraai in 3D
- Low-poly kraai, gemaakt in code (geen Blender nodig voor v1), zwart met eva-glans, ogen in paper.
- Procedurele animaties: hoppen (lopen), vliegen in een boog tussen plekken, zitten, slapen (kop onder vleugel), tekenen (pikken naar de grond), schrikken bij fluiten.
- Boven hem een klein label met naam en wat hij doet, zoals in de mockup.

### Bezoekers
- Bezoekers zien elkaar als klein low-poly figuurtje in eva met hun naam erboven.
- Je begint op het perron van Metro Rodenrijs, met de kraai ergens in beeld als hij wakker is.

## Model

Opus voor A, B en WERELD stap 1-2. Sonnet mag voor C en WERELD stap 3-4.

## F. Update 15-11-2026: eiland

De wereld wordt een verzonnen eiland dat stiekem Berkel is. Zie EILAND.md. Daarmee vervalt in blok E het deel "Techniek" (3DBAG, OSM, RD-omrekening) en de plekkentabel. "Stijl", "De kraai in 3D" en "Bezoekers" blijven gelden. Bezoekers spawnen op het perron van station Rodenrijs op het eiland. WERELD.md stap 2 t/m 4 blijven zoals ze zijn.

## G. Invloed van bezoekers (15-11-2026)

> Status 15-11-2026: routes built in `drive/influence.py` with WERELD step 3; sim `python -m drive.sim_influence`.
> A plain opinion from a trusted visitor (0.8) moves his meals at the Jumbo 23% -> 43%, a distrusted one (-0.5)
> 23% -> 13%; "you should..." is mostly refused and then pushes him slightly the other way. At a stranger's trust
> (0.3) little shows: trust only learns in BREIN-v3 phase 3 (block 5), and the sheet line needs |trust| >= 0.35.

Bezoekers moeten hem echt kunnen beinvloeden. Niet als bevel, maar zoals mensen elkaar beinvloeden: hij hoort het, weegt het af en doet er iets mee, of juist niet. Bouw dit mee met WERELD.md stap 3 en BREIN-v3.md fase 3 (punt 8, model van bezoekers).

Hoe het werkt (allemaal in code, het model praat alleen):
- Plekken en acties. De code herkent in een briefje plek-namen en acties uit een vaste lijst (places.json en actions). Dat wordt een "suggestie" in zijn werkgeheugen, met saillantie = vertrouwen in die bezoeker x sociaal-behoefte, en geeft een bonus voor die actie@plek in de utility. Is het vertrouwen negatief, dan wordt het een straf: dan gaat hij er expres niet heen. Geen spiegel (blok B1) blijft gelden.
- Onderwerpen. Een briefje kan een interesse of open vraag planten ("weet jij waarom duiven knikken?"). De code zet het onderwerp in zijn wants/questions. Later kan hij er zelf over zoeken: de zoekopdracht schrijft het model in zijn eigen woorden en die gaat door safety. De tekst van de bezoeker wordt nooit letterlijk een zoekopdracht.
- Meningen over plekken. "De Jumbo is beter" telt als zwak bewijs voor zijn plekgebonden overtuigingen (ongeveer 0.3 van een eigen ervaring, gewogen met vertrouwen). Op termijn wint zijn eigen ervaring altijd.
- Spullen. Een achtergelaten voorwerp kan hij meenemen naar zijn nest. Het wordt een herinnering en kan zijn stemming en interesses kleuren.
- Karakterblad. Bezoekers kunnen er niet zelf iets op zetten, maar herhaalde invloed van dezelfde bezoeker kan in de slaap-consolidatie een regel opleveren ("ik luister meestal naar Sanne", of juist het omgekeerde).
- Plafond. Per bezoeker per wereld-dag een maximum aan invloed (bonus en bewijs), zodat een persoon hem niet helemaal kan overnemen. Getallen als constanten bovenaan, en laat in de sim met de drie nepbezoekers zien dat het werkt.

Wat niet mag: tekst van een bezoeker start nooit direct een tool. Dus geen web-zoekopdracht met hun letterlijke tekst, geen URL openen, geen bestand schrijven, geen code. Invloed loopt alleen via de routes hierboven.
