# Tekenen v2: code tekent, het model bedenkt

> Status 15-11-2026: built and live (stap 1-4) in `drive/draw/`. Test sheet: `python -m drive.draw.test` (writes to
> `drive/test/tekenen/`, not in git, so not `drawings/test.html`: the loop publishes all of `drawings/`). No bigger
> model: the RTX 3070 has 8 GB and qwen3:8b already fills it. Learned symbols are crude; the retry keeps the least
> broken version, which is not the same as the most recognisable.

Gebruik Opus voor stap 1 en 2, Sonnet mag voor 3 en 4. Doe dit na blok B uit VOLGENDE.md. Het mag voor of na blok C, maar niet tegelijk met werk aan `voice.py`.

## Het probleem

Nu laat `voice.drawing()` qwen3:8b in één keer een complete SVG schrijven. Een klein model weet niet waar dingen op een canvas staan, dus komen er losse vormen uit zonder onderwerp (zie `drawings/2026-11-14-2002-the-rubber-band-s-dignity.svg`: een bruin vlak met lijnen, geen kraai, geen elastiekje). Een betere prompt lost dat niet op.

## Kernprincipe

Net als bij het brein: het model bedenkt wat er op de tekening staat, de code tekent het. Het model schrijft geen SVG-coördinaten meer, behalve voor kleine losse symbolen (stap 3).

## 1. Compositie als JSON (1 LLM-call)

Het model krijgt het onderwerp en geeft alleen een plan terug:

```json
{"title": "...", "caption": "...", "line": "...",
 "objects": [
   {"what": "crow", "where": "left", "size": "big", "pose": "proud"},
   {"what": "rubber band", "where": "center", "size": "small"},
   {"what": "sun", "where": "top right", "size": "small"}
 ],
 "mood": "suspicious"}
```

- Maximaal 5 objecten. `where` uit een vaste lijst (links, midden, rechts, boven, onder, en combinaties), `size` uit small/medium/big.
- Code zet dat om naar echte posities en schalen op een canvas van 200x200, met een grondlijn, zodat dingen niet in de lucht zweven als dat niet de bedoeling is.
- `mood` bepaalt kleine dingen in code: kleurtemperatuur, scheefheid, hoeveel krabbels in de achtergrond.

## 2. Een tekendoos met eigen stijl

Een map `drive/draw/` met getekende symbolen in code, elk een functie `teken(x, y, schaal, variatie) -> svg`:

- Begin met wat hij het vaakst tekent: kraai (een paar poses), fiets, wiel, flessendop, elastiekje, duif, zon, wolk, bankje, boom, huis, metro, theelepel. Kijk in `drawings/index.json` en zijn interesses voor wat er nog meer vaak terugkomt.
- Alles in één herkenbare stijl, zodat het als zijn werk voelt:
  - Inkt (#16130f) op papier (#efe9dc), met hooguit 2 accentkleuren uit de huisstijl (eva-blauw #1556cf, rood #de2f1f).
  - Lijnen met een lichte wiebel, zoals rough.js: elk lijnstuk een paar pixels ruis, dubbele streken bij contouren.
  - Arcering met schuine lijntjes in plaats van vlakke vullingen.
- Een kraai die tekent als een kleuter met een vaste hand is charmant. Willekeurige vormen zijn dat niet.

## 3. Woordenschat die groeit

Hier wordt hij echt beter met oefenen:

- Staat een object niet in de tekendoos, dan vraagt de code het model om alleen dat ene symbool, in een eigen vakje van 50x50, met maximaal 8 vormen. Dat is een tweede LLM-call, alleen als het nodig is.
- Het resultaat gaat door dezelfde wiebel- en kleurfilter, zodat het in stijl blijft.
- Is het geldig (`safety.clean_svg` laat het door, het past in zijn vakje en is niet leeg), dan wordt het opgeslagen in `drive/draw/learned/<naam>.json`, met een teller hoe vaak hij het heeft getekend.
- De volgende keer hergebruikt hij dat symbool. Na elke 5 keer mag hij het een keer opnieuw proberen, en houdt hij de versie die het minst kapot is (meer vormen binnen het vakje, geen overlap met de rand).
- Dit koppelt aan de vaardigheid uit de breinkaart (cerebellum): het aantal geleerde symbolen en hun tellers zijn zijn tekenvaardigheid. In de over-tab kan later staan: "kan 23 dingen tekenen".

## 4. Opruimen en tonen

- Oude tekeningen blijven zoals ze zijn. Dat is zijn vroege werk.
- `drawings/index.json` krijgt per tekening `version: 2` en de lijst objecten, zodat de site later kan laten zien wat erop hoort te staan.
- Draai 10 testtekeningen met onderwerpen uit zijn interesses, zet ze naast elkaar in `drawings/test.html` en laat ze mij zien voordat dit live gaat.

## Niet doen (nu)

- Geen groter model alleen voor tekenen, tenzij je videokaart het makkelijk aankan. Check dat eerst en zeg het me.
- Geen beeldmodel (Stable Diffusion en dergelijke). Dat is zwaar en het ziet er niet uit als zijn werk.
- Een vision-model dat zijn eigen tekening beoordeelt, kan later. Eerst kijken hoe ver stap 1 tot en met 3 komen.
