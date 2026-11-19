# Gebouwen met karakter (15-11-2026)

Gekozen: optie 1. Claude Code bouwt elk landmark zelf in three.js-code, in de stijl van de bouwdoos. Geen AI-3D-modellen, geen importscript, geen texturen (AI-3D via Tripo en Hunyuan3D liep vast op betaalmuur en een kapotte demo).

Noah maakt per landmark een voorbeeldplaatje (Tripo Generate Image) en zet het in `world/models/ref/<naam>.png`. `station-rodenrijs.png` is de stijlreferentie voor allemaal: creme muren, eva-blauwe daken, speelgoedgevoel.

## Zo bouw je een landmark (Claude Code, Opus)

- Bekijk het plaatje en bouw het na met dezelfde bouwdoos-onderdelen als de huizen, plus wat er nodig is (overkapping, toren, wieken, pui, luifel, terras). Geen kopie op detailniveau: herkenbaar silhouet en de 3-4 dingen die het karakter geven.
- Ware grootte uit de tabel hieronder, origin onderaan in het midden, voorkant naar +z.
- Kleuren alleen uit de huisstijl, MeshToonMaterial zoals de rest. Rood alleen voor zijn huidige plek.
- Botsvlak als 2D-footprint, net als de huizen.
- Molens: de wieken draaien langzaam. Fonteinen: een simpel waterstraaltje.
- Namen en borden (Albert Heijn, Jumbo, McDonald's, De Turk, Bibliotheek, station Rodenrijs) als bord/tekst in code.
- Ontbreekt een plaatje, bouw dan iets passends op basis van de beschrijving in de tabel, en zeg dat erbij.
- Begin met het station en laat het in `world/viewer.html` naast het plaatje zien. Pas na Noah's ok de rest.

## Bouwdoos-huizen

Meer karakter zonder AI: per huis via de seed variatie in dakvorm (zadeldak, trapgevel, mansarde, plat met dakrand), gevelbreedte, aantal verdiepingen, erker, dakkapel, luifel, voortuintje met heg of schutting, fiets tegen de gevel, gordijnen in de ramen, een kat op een vensterbank (1 in de 20). Laat 12 voorbeelden naast elkaar zien.

## Bestandsnamen en maten

| plaatje (ref/) | wat | hoogte (m) |
|---|---|---|
| station-rodenrijs.png | metrostation, perron met overkapping | 8 |
| albert-heijn.png | supermarkt | 7 |
| jumbo.png | supermarkt | 6 |
| mcdonalds.png | fastfood | 6 |
| de-turk.png | eethuis met terras | 7 |
| bibliotheek.png | bibliotheek | 10 |
| dorpskerk.png | oude dorpskerk met toren | 28 |
| de-bron.png | moderne kerk | 15 |
| molen-de-hichte.png | windmolen | 22 |
| molen-de-valk.png | windmolen | 20 |
| ondermolen.png | gedenksteen | 2 |
| fontein.png | fontein (2x gebruikt) | 2 |
| vis.png | beeld van een vis op sokkel | 3 |
| huis-a.glb t/m huis-d.png | optioneel: rijtjeshuizen als extra variatie | 9 |
