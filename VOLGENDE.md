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

## H. Grimsby verandert zijn wereld (15-11-2026)

Hij moet de wereld om zich heen kunnen veranderen, en die veranderingen blijven staan en zijn zichtbaar voor iedereen. Bouw dit na EILAND fase 1 en WERELD stap 3 (het heeft de 3D-wereld en de Supabase-tabellen nodig), voor of samen met WERELD stap 4.

Kernregel blijft: code beslist, het model praat. Het model kiest nooit coordinaten of geometrie. Het mag alleen een naam, titel of korte tekst verzinnen.

Nieuwe acties (in actions, met behoeftes zoals de rest):
- `carry`: een voorwerp oppakken (iets van een bezoeker, een gevonden ding zoals een flessendop, een takje, een patatje) en ergens anders neerleggen. Wat hij draagt staat in now.json.
- `nest`: zijn nest uitbreiden met wat hij verzameld heeft. Het nest groeit zichtbaar: elk voorwerp krijgt een plekje in of rond het nest. Expressie en rust.
- `mural`: een van zijn eigen tekeningen (uit TEKENEN) ophangen als poster of muurtekening op een gevel, hek of muur bij de plek waar hij is. Expressie.
- `stash`: eten of glimmende dingen verstoppen op een vaste plek (kraaien doen dit echt). Hij onthoudt waar, en kan het vergeten (vergeetcurve uit BREIN-v3).
- `plant`: een zaadje of pit laten vallen. Over een paar wereld-dagen wordt het een plantje, later een struik. Langzaam, zodat het iets betekent.
- `arrange`: dingen in een patroon leggen (een rijtje dopjes, een cirkel van takjes). Het model geeft het een naam ("monument voor de verloren friet").

Hoe het in code werkt:
- Een vaste catalogus van voorwerpen en aanpassingen (`world/catalog.json`), elk met een 3D-model uit de bouwdoos. Geen vrije geometrie van het model.
- Code kiest de plek: in een straal rond zijn huidige plek, op een geldig punt (niet in een gebouw, niet midden op straat waar bezoekers lopen, niet in zee). Murals alleen op vooraf aangewezen "hangplekken" op gevels.
- Supabase-tabel `world_changes`: id, character_id, kind, item, x, z, params (json), title, created_at, removed_at. Brein schrijft (service key), iedereen leest. Site laadt ze bij het starten en volgt nieuwe via Realtime.
- Plafond tegen rommel: max aantal voorwerpen per plek en voor het hele dorp. Is het vol, dan haalt hij eerst iets weg of "vergeet" de code het oudste niet-gekoesterde ding (removed_at). Planten en het nest tellen niet mee.
- Elke verandering is een gebeurtenis in feed.json (`did` met `why`) en een herinnering. Overtuigingen mogen erover gaan ("mijn dopjesrij bij de AH maakt me rustig").
- Bezoekers (blok G) kunnen zijn veranderingen zien en er briefjes bij leggen. Ze kunnen zijn dingen niet zelf weghalen of verplaatsen. Hij kan dat wel met hun spullen.

Wat hij (nog) niet kan: gebouwen neerzetten of slopen, wegen of kustlijn veranderen, bosvakken openen. Dat blijft mijn werk.

Check in de sim: na 5 wereld-dagen een lijstje van wat hij veranderd heeft en waar, en of het plafond werkt (geen 400 dopjes bij de Jumbo).

## I. Een tweede karakter dat praat en bouwt (15-11-2026)

Pas na blok H. Wie het karakter is (soort, naam, karakter) vult Noah nog in onderaan dit blok. Begin niet voordat dat er staat.

Basis:
- Zelfde brein als Grimsby (alles werkt al per `character_id`), eigen state, eigen behoeftes, eigen principes en karakterblad, eigen data-map (bv. `data/<id>/`) en eigen rijen in Supabase. Grimsby's bestaande data en API blijven exact zoals ze zijn.
- Een eigen huis/plek op het eiland, eigen geliefde en gehate plekken. Hij is geen kopie van Grimsby: andere gewichten op de behoeftes, en een eigen behoefte die bij bouwen hoort (bv. `maken`).

Praten met Grimsby:
- Code beslist wanneer: alleen als ze op dezelfde plek zijn (of vlakbij) en de sociaal-behoefte van minstens een van de twee hoog genoeg is. Geen eindeloze chats.
- Een gesprek is kort: max 3 beurten per karakter, elke beurt 1 LLM-call die alleen het werkgeheugen van de spreker plus de vorige zinnen krijgt.
- Elk karakter heeft een relatiemodel van de ander (vertrouwen, sympathie), net als bij bezoekers in blok G, met predictiefout. Ze mogen het oneens zijn, elkaar irriteren, elkaar ontlopen. Geen spiegels.
- Ze kunnen elkaar beinvloeden via dezelfde routes als blok G (plekken, onderwerpen, meningen), met hetzelfde plafond.
- Gesprekken komen in beide feeds en als herinnering bij allebei. Op de site: een tekstballonnetje boven ze in de 3D-wereld, en het gesprek terug te lezen.

Bouwen:
- Een catalogus van grotere bouwwerken (`world/builds.json`): bankje, vogelhuisje, steiger, schuurtje, brugje over een sloot, uitkijkpaal, bord met tekst. Elk met een 3D-model uit de bouwdoos, materialen en bouwtijd in ticks.
- Code kiest waar: alleen op vooraf aangewezen bouwplekken op het eiland (`world/plots.json`, Noah kan die later uitbreiden). Het model verzint alleen wat het wordt en hoe het heet.
- Bouwen duurt meerdere ticks en is zichtbaar in fases (fundering, half af, af). Kan mislukken (`ok: false`) en worstelt dan door of geeft op.
- Materialen: denkbeeldig, verzameld op plekken (takken in het bos, planken bij de AH-containers) of gekregen. Grimsby kan materialen brengen (zijn `carry`-actie uit H), en dat telt mee in hun relatie.
- Opslag in `world_changes` met kind `build`, character_id van de bouwer, en een `stage`. Plafond op aantal bouwwerken per plek en totaal. Bouwwerken kunnen vervallen als niemand ernaar omkijkt.
- Grenzen blijven: geen gebouwen op ware grootte (huizen, winkels), geen wegen, kust of bosvakken.

Performance:
- Twee karakters betekent ongeveer twee keer zoveel LLM-calls op de laptop, plus gesprekken. Meet in de sim hoeveel calls per uur het wordt en zeg het eerlijk als qwen3:8b het niet bijhoudt binnen een tick. Dan om de beurt laten ticken of de ticks van de bouwer langer maken.

Check in de sim: 5 wereld-dagen met allebei, hoeveel gesprekken, hoe de relatie loopt, wat er gebouwd is en waar.

### Wie is het? (door Noah in te vullen)
- Soort:
- Naam:
- Karakter in een paar zinnen:
- Waar woont hij/zij op het eiland:
- Hoe kijkt hij/zij tegen Grimsby aan bij de eerste ontmoeting:

## J. NPC's: bewoners zonder LLM (15-11-2026)

Naast de denkende karakters komen er NPC's die alleen in code bestaan. Nul LLM-calls, dus ze kosten de laptop vrijwel niks. Kan voor of na blok I.

- Elke NPC heeft een `character_id`, een soort, een naam, een dagritme (wereldtijd -> plek -> bezigheid) en een kleine statusmachine (bv. lopen, staan, zitten, slapen, vluchten).
- Praten: zinnen uit een vaste lijst per NPC (`world/npcs.json`), gekozen door de code op basis van situatie (tijd, weer, wie er is). Die lijst schrijven we een keer met de hand, of laat Claude Code er een voorstel voor doen dat ik goedkeur. Optioneel later: 1 LLM-call per nacht om de lijst van een NPC een beetje aan te vullen, als de laptop toch niks doet.
- Reageren: simpele regels in code. Een duif vlucht als Grimsby te dichtbij komt, de AH-medewerker duwt winkelwagens en zegt iets als een bezoeker langs loopt, enzovoort.
- Grimsby merkt ze op als `noticed`-gebeurtenissen en ze komen in zijn werkgeheugen en herinneringen, net als bezoekers. Zijn reactie kost alleen zijn normale tick. Hij kan er overtuigingen over vormen en een relatie mee opbouwen (zelfde relatiemodel als blok G en I, maar de NPC zelf onthoudt niks).
- NPC's draaien ook als de laptop uit is: hun ritme volgt de wereldtijd en kan dus ook gewoon in de browser van de bezoeker berekend worden. De wereld voelt dan nooit leeg.
- In de 3D-wereld: low-poly figuurtjes/dieren uit de bouwdoos, met een naamlabel zoals bezoekers maar in een andere kleur.

Eerste NPC's (voorstel):
- Derek, een duif bij de fontein in het centrum. Grimsby heeft hem zelf al verzonnen in zijn gedachtes, dus maak hem echt. Check eerst in log.json en memories.json wat Grimsby al over Derek denkt, zodat Derek daarbij past.
- Een AH-medewerker die winkelwagens terugzet.
- Een visser op het strand die altijd op dezelfde plek staat en nooit iets vangt.
- Een conducteur op het perron van station Rodenrijs (de trein komt nooit, hij blijft hopen).

Check: 1 wereld-dag in de sim met de NPC's erbij, laat zien hoe vaak Grimsby ze opmerkt en wat dat met zijn keuzes doet.

## K. Model per karakter, API met budget (15-11-2026)

Na blok H, voor blok I. Model instelbaar per `character_id` in `drive/voice.py`, providers ollama, anthropic en gemini. Grimsby naar claude-haiku-5-5, qwen3:8b als fallback bij een API-fout of als het maandbudget op is (constante, standaard 8 euro over alle karakters samen, harde grens 10). Keys alleen in .env. Log per call tokens en kosten in `drive/live/costs.jsonl`, en laat Noah na een dag het gemiddelde per dag en de schatting per maand zien voordat er meer karakters bij komen.

## Volgorde vanaf 15-11-2026 (avond)

Alles hierboven tot en met blok G, EILAND.md fase 1, TEKENEN.md en WERELD.md stap 1-4 is af. Wat nog komt, in deze volgorde, elk met plan -> ok -> bouwen -> testen -> go -> commit:

1. BREIN-v3.md fase 3
2. EILAND.md fase 1b (ware grootte) samen met GEBOUWEN.md (landmarks in code naar Noah's plaatjes, plus meer variatie in de bouwdoos-huizen). Staat los van het brein, mag ook eerder als de plaatjes er zijn.
3. Blok H: Grimsby verandert zijn wereld
4. Blok K: model per karakter, API met budget
5. Blok J: NPC's (begin met Derek)
6. Blok I: tweede karakter (pas als Noah de "Wie is het?"-velden heeft ingevuld)

Later, nog zonder plan: bosvakken openen, tweede eilandje, hersenscan-tab, Dashboard-panel, gebouwen betreedbaar.

## L. Lessen uit Pino (15-11-2026)

Bron: pinos.world/facts, /brain, /memories en een screenrecording van Noah. Check bij elk punt eerst wat er al is (geheugen met verdringen van de zwakste bestaat al in memory.py, werkgeheugen en bezoekersmodel staan in BREIN-v3). Bouw alleen wat ontbreekt. Hoort bij of na blok K.

Hoe Pino echt werkt, voor de duidelijkheid: code rekent elke seconde behoeftes en gevoelens uit en bepaalt welke acties er op tafel liggen en hoe ze uitpakken. Een model kiest daaruit 1-3 acties en zegt waarom. Van zijn 2.965 acties in 24 uur kwamen er ~950 van een model, de rest was autopilot, wachtrij of "niks nieuws, ga door". Onze regel "code beslist, model praat" mag dus iets opschuiven naar: code maakt het menu (top 3 uit de utility), het model mag kiezen, alleen als er iets gebeurt. Optioneel en achter een constante, standaard uit tot Noah het heeft getest.

1. Wachtrij. Als het model wordt aangeroepen, mag het 1-3 acties in een keer kiezen. De rest komt in `state["queue"]` en wordt zonder call uitgevoerd, tenzij er iets nieuws gebeurt (briefje, bezoeker, behoefte schiet door een drempel). Log per actie de bron: `model`, `queue`, `autopilot`, `carry_on`. Laat in de sim de verdeling zien.
2. Alleen calls als er iets gebeurt. Triggers: iemand praat tegen hem, er landt iets bij hem, een actie is klaar, of er zijn X wereld-minuten verstreken. Anders autopilot. Geen model bereikbaar = hij gaat door met wat hij deed.
3. Karakterblad met slot. Regels die Noah schreef staan op slot en kan hij nooit wijzigen. Zijn eigen regels (`added`) volgen vaste drempels: toevoegen bij een patroon van 6 nachten of 6 dagen op hetzelfde tijdstip, een angst toevoegen als een zorg 3 keer uitkwam, loslaten na 30 nachten zonder teken ervan. Elke wijziging in de changelog met het bewijs erbij (sluit aan op blok B4). Constanten bovenaan.
4. Gewoontes aan plek en tijd. Een terugkerend patroon "actie@plek rond tijdstip" kan een regel op het karakterblad worden ("'s avonds naar de McDonald's") en geeft dan een kleine utility-bonus op dat tijdstip.
5. Oefenniveau per activiteit (0-1, plus aantal keer). Stijgt met herhaling, zakt langzaam zonder. Beinvloedt de kans dat iets lukt (samen met de Yerkes-Dodson-curve uit BREIN-v3). Zichtbaar op de site.
6. Geheugen-check: Pino heeft twee delen (kort ~42, lang ~43) en een waarde per herinnering uit sterkte x hoe vaak teruggekomen x hoe lang geleden. Niks verdwijnt op een timer, wat terugkomt is weer veilig. Vergelijk met onze memory.py en meld de verschillen aan Noah voordat je iets verandert.
7. Wants met status. Zijn verlanglijst (denkbeeldig) als lijst met status: `open`, `bezig`, `gelukt`, `losgelaten`. Komt op de site in het dagboek.
8. Haiku-zuinig (bij blok K): het vaste deel van de prompt (karakterblad, regels, principes) altijd vooraan en ongewijzigd, zodat prompt caching werkt. Prompt altijd ver onder 100k tokens (daarboven wordt Haiku 5x duurder), dus nooit het hele geheugen meesturen.

Site-ideeen uit de recording (voor later, geen haast):
- "Nu"-kaartje bovenin: wat hij doet, een zin van hemzelf, en "veranderd: kreeg briefje van X".
- Zijn tas/nest als raster met per voorwerp waar het vandaan komt.
- Een "hoe hij werkt"-pagina met live getallen uit de feed (calls vandaag, dagen oud, verdeling model/autopilot).
- Dithering/halftone op materiaalniveau in three.js (Pino doet het in het materiaal, niet als post-processing) als optie naast de toon-shading.
- Klusjes voor bezoekers: hij vraagt iets (een foto van iets op het eiland, een woord, een tekening) en bezoekers kunnen dat inleveren. Beloning denkbeeldig.

## M. Groot idee: Grimsby maakt dingen voor buiten (15-11-2026)

Nog niet bouwen. Eerst een plan per onderdeel aan Noah laten zien. Volgorde: blog, dan eigen pagina's, dan video. Overal geldt blok G: tekst van een bezoeker wordt nooit letterlijk inhoud, zoekopdracht, URL of code.

1. Blog (makkelijkst, eerst). Eens per wereld-week kiest de code een onderwerp uit zijn sterkste herinneringen, wants of feiten van die week. Het model schrijft een post van 300-600 woorden in zijn stem. Komt als `data/blog/<datum>.json` en een blogpagina op de site. 1 call per week, eventueel Sonnet voor betere tekst. Geen namen van bezoekers zonder dat die het zelf in een briefje zetten.
2. Internet breder. Hij zoekt al (actie search + safety.py). Uitbreiding: hij mag een gevonden pagina echt lezen (eerst alleen Wikipedia en een korte allowlist), safety haalt instructie-achtige zinnen eruit, en wat hij leest wordt een `read`-herinnering. Max N pagina's per wereld-dag.
3. Eigen pagina's op de site. Pino heeft dit ook ("his websites"). Risico: model-HTML live op Noah's site. Dus: alleen in een eigen map (`site/grimsby-made/`), getoond in een iframe met `sandbox` zonder `allow-scripts` en een strenge CSP, geen externe bronnen, max grootte per pagina, een validator die script-tags, event-handlers, forms en externe URL's eruit gooit. V1 = alleen HTML+CSS. Noah krijgt per nieuwe pagina eerst een melding en kan hem uitzetten.
4. Video's (reels/tiktoks, moeilijkst). V1: hij maakt alleen clips in een map, Noah post zelf. Clip = opname uit de 3D-wereld (headless browser die een stukje van zijn dag rendert) of zijn tekeningen, plus tekst-overlay met zijn gedachte, in elkaar gezet met ffmpeg. Caption schrijft het model. Automatisch posten pas later, en check dan eerst wat TikTok en Instagram nu eisen voor posten via hun API (app-review, zakelijk account) en hun regels voor AI-content en geautomatiseerde accounts. Meet eerst hoeveel tijd en CPU een clip op de laptop kost.

## N. Grimsby van de daken af (15-11-2026, klein, mag meteen tussendoor)

Probleem: `perch()` in place.js zoekt tot 60 m rond een plek naar het eerste dak (y > 2) en kiest dat altijd. Alleen bench/fountain/artwork landen op de grond. Daardoor zit hij bijna altijd op een dak en kunnen bezoekers (die niet vliegen) niet bij hem komen. Bezoekers laten vliegen doen we niet.

Fix:
1. Standaard landt hij op de grond: het dichtstbijzijnde punt rond de plek dat `island.walkable` is (zelfde 2D-plattegrond als de bezoekers), een paar meter voor de ingang, niet midden in een deur of op het perronrand.
2. Dak alleen als het past: slapen (zijn dak op station Rodenrijs blijft zijn huis), en een kleine kans bij rondkijken/stilte (constante, bv. 0.15). Na schrikken (fluiten, bezoeker te dichtbij) mag hij kort naar een dak of tak vluchten en komt daarna weer naar beneden.
3. Komt een bezoeker binnen ~15 m terwijl hij op een dak zit en hij is niet bang/slaapt niet, dan hopt hij naar beneden (alleen visueel, geen LLM-call).
4. Tussen plekken blijft hij in een boog vliegen, maar landen = grond.
5. De cadeautjes op zijn dak (`onRoof` in world.js) blijven waar ze zijn.

Check: loop een wereld-dag in de viewer of sim en tel hoe vaak hij op een dak vs op de grond zit. Doel: overdag grotendeels grond.
