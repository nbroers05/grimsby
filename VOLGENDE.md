# Volgende stappen (na BREIN-v2)

Lees dit pas als BREIN-v2 klaar is. Alles hieronder is na het begin van BREIN-v2 besloten. Doe het in deze volgorde, en laat mij na elk blok testen voordat je verdergaat. Check bij elk punt eerst wat er al gebouwd is, zodat je niks dubbel doet.

## A. BREIN-v2 stap 12: wereld als kaart

Deze stap is aan BREIN-v2.md toegevoegd nadat je eraan begon. Lees stap 12 in BREIN-v2.md en voer hem uit als dat nog niet gebeurd is: `world/places.json` met 8-12 plekken in Berkel en Rodenrijs, acties gekoppeld aan plekken, reistijd kost energie, het brein weet niks van de 3D.

## B. Brein-aanvullingen

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

Daarna WERELD.md, stap 1 t/m 4 (lopen, Supabase live, iets achterlaten, andere bezoekers). Aanvullingen daarop:

1. Briefjes in het zand. Een briefje van een bezoeker verschijnt in de wereld als tekst op de grond, op de plek waar het is neergelegd (bij voorkeur aan de waterkant). Zijn antwoord verschijnt er bij een volgende tick naast, ook als tekst op de grond. Andere bezoekers kunnen beide lezen. Daarnaast blijft het antwoord ook zichtbaar voor de schrijver bij een volgend bezoek.
2. Geen inhoudsfilter op wat bezoekers schrijven. Wel: max 280 tekens, rate limit per bezoeker, en tekst van bezoekers start nooit zelf een actie of tool (zie WERELD.md stap 3).

## Model

Opus voor A, B en WERELD stap 1-2. Sonnet mag voor C en WERELD stap 3-4.
