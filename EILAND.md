# Eiland: Grimsby woont op een verzonnen eiland dat stiekem Berkel is

Besloten op 15-11-2026. Dit vervangt de 3DBAG/OSM-aanpak uit VOLGENDE.md blok E (techniek) en de kaart uit WERELD.md stap 1. De stijl uit blok E (toon-shading, huisstijlkleuren, A Short Hike-gevoel) blijft gewoon staan.

Gebruik Opus. Eerst een plan, dan bouwen, dan mij laten kijken in de viewer voordat het op de site komt.

## Waarom

- Geen echte kaart van mijn dorp meer online waar vreemden rondlopen.
- Geen 3DBAG/OSM/RD/Draco-pijplijn meer. Het eiland wordt in code gebouwd.
- Het brein merkt er bijna niks van: plek-id's blijven hetzelfde.

## De vorm

Zie `world/eiland-schets.png` (door mij getekend):
- blauw: zee, rondom
- geel: strand, een ring om het hele eiland, aan de noordoostkant iets grilliger
- groen: bos, het grootste deel van het binnenland
- grijs: het dorp, aan de zuidkust, half op het strand. Hier staan alle plekken die we nu hebben.

Maat: ongeveer 1 pixel van de schets = 1 meter. Dus het eiland is ruwweg 750 x 400 m en het dorp ruwweg 220 x 80 m. Middelpunt (0, 0) is het midden van het eiland, x = oost, z = zuid. Het dorp ligt dan rond (0, +160).

Hoogte: een beetje glooiend, bos iets hoger dan het strand, dorp vlak. Geen bergen (het blijft Berkel).

## Wat we nu bouwen (fase 1)

Alleen het dorp is af. De rest bestaat wel, maar is nog leeg:
- Zee en strand rondom, het strand is helemaal beloopbaar.
- Het bos is voor nu een dichte rand bomen die je niet in kunt (botsvlak), met een beetje mist erachter. Later breiden we stukje bij beetje uit, dus maak het bos opgedeeld in vakken die we een voor een kunnen openen.
- Het dorp: compact, gezellig, huizen uit een bouwdoos in code (rijtjeshuisjes, een paar winkels met luifel, kerkjes, twee molens). Alles low-poly, geen texturen.

## Plekken

Houd precies de plekken uit `world/places.json` en hun `id`'s, `actions`, `feel`, `feel_for` en `food`. Alleen `x`, `z` en waar nodig `words` veranderen. Zet ze allemaal in het grijze dorp.

Wijzigingen:
- Metro Berkel Westpolder bestaat niet meer. Alleen Metro Rodenrijs blijft.
- `home` wordt het dak van station Rodenrijs (`words`: "on the roof of station Rodenrijs"). Id blijft `home`.
- `jumbo` en `de-turk` zeggen nu "by the station" in de zin van station Rodenrijs, prima zo.
- `poi` verwijst naar OSM en vervalt. Vervang het door een eigen id voor het 3D-object (bv. `"obj": "molen-de-valk"`).
- Het station: een perron met een spoor dat aan de ene kant het bos in loopt en aan de andere kant gewoon de zee in. Bezoekers spawnen op het perron.
- Valkenhof 41 zit er niet in, ook niet als decor.

Grove indeling in het dorp (mag je verbeteren, laat het me zien):
- West: station Rodenrijs met de Jumbo, De Turk, de fontein en het bankje erbij.
- Midden: het centrum met de Albert Heijn, Vis, de fontein, de bibliotheek, de Dorpskerk.
- Oost: de Bron, het plantsoen met bankje, de McDonald's.
- De twee molens (De Hichte en De Valk) aan de randen van het dorp, op het strand, zodat ze van ver te zien zijn.
- De Ondermolen-gedenksteen ergens tussen station en centrum.

## Brein

- Kleine migratie: alleen places.json krijgt nieuwe coordinaten. Reistijd/energie werkt op afstand, dus alles ligt nu dichter bij elkaar. Check in `drive.sim` of de reistijdkosten nog zinnig zijn en schaal ze zo nodig, zodat hij niet de hele dag heen en weer vliegt.
- Overtuigingen en herinneringen blijven staan (ze gaan over id's). Oude herinneringen die "Westpolder" noemen laat je staan, dat is zijn geschiedenis.
- 1 keer, bij de eerste tick na de verhuizing: een `noticed`-gebeurtenis dat hij wakker wordt en alles anders is: water overal, het station heet anders, de Jumbo is er nog steeds (helaas). De rest laat je aan hem over.

## Site

- `world.js`, `place.js`, `look.js` laden voortaan het eiland in plaats van `berkel.glb`. De export-API van `look.js` en `place.js` blijft hetzelfde, want het Dashboard-panel importeert ze.
- `build_world.py`, `berkel.glb`, `poi.json` en `world/cache/` verplaatsen naar `world/oud/` (niet weggooien, verwijderen mag in deze map toch niet).
- Bouw het eiland zoals jij het handigst vindt (in de browser bij het laden, of vooraf naar een .glb). Laadtijd onder de 5 seconden blijft de eis.
- Eerst in `world/viewer.html` aan mij laten zien.

## Later (niet nu)

- Bosvakken een voor een openen, met eigen plekken (de speeltuin met zijn nest, het voetbalveld, Het Baken, Cafe Het Centrum, De Windas als meertje met briefjes in het zand).
- Een tweede eilandje voor de kust waar hij naartoe kan vliegen.
