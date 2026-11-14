# Wereld v1: lopen, live zien, iets achterlaten

Gebruik Opus voor stap 1 en 2, Sonnet mag voor de rest. Doe dit na BREIN-v2.

## Architectuur

- Site (GitHub Pages): three.js-wereld, first person lopen, botsingen, geluid. Alles in de browser van de bezoeker.
- Supabase (bestaand account, nieuw project of nieuw schema): live staat van de vogel, spullen en briefjes van bezoekers, wie er rondloopt. Realtime voor live updates.
- Brein (laptop): schrijft elke tick zijn staat naar Supabase in plaats van naar git, en haalt de inbox op. Git push alleen nog voor tekeningen en dagboek-archief.

Als de laptop uit is: bezoekers kunnen nog steeds rondlopen en dingen achterlaten bij zijn slaapplek. De vogel slaapt. Bij wakker worden verwerkt hij de stapel.

## Stap 1: lopen (alleen browser, geen backend)

- Gebied: een afgebakend stuk van een paar honderd meter rond het centrum van Berkel en Rodenrijs, rest in mist. Uitbreidbaar maken.
- Bediening zoals pinos.world: klikken om te kijken (pointer lock), W/S lopen, A/D draaien, E fluiten. Op touch: simpele joystick, laag prioriteit.
- Botsingen: 2D-plattegronden van de 3DBAG-gebouwen als botsvlakken, niet de 3D-meshes. Water uit OSM ook niet beloopbaar.
- Plekken uit world/places.json (zie BREIN-v2 stap 12) krijgen een zichtbaar herkenningspunt.
- De vogel staat op zijn positie uit now.json. Stijl: low-poly met toon-shading in de Noah Huisstijl.
- Geluid: voetstappen, wat vogelgeluid, een fluitje bij E. Vrije geluiden (CC0), vermeld de bron.

## Stap 2: live via Supabase

Tabellen (voorstel, mag je verbeteren):
- `bird_state`: 1 rij met de inhoud van now.json plus positie (x, z) en doel. Het brein update deze elke tick.
- `feed`: zoals feed.json.
- Site leest via Realtime, en laat de vogel vloeiend naar nieuwe posities lopen in plaats van te springen.
- Het brein gebruikt de service key (alleen lokaal, nooit in de site of repo). De site gebruikt alleen de anon key.
- RLS: iedereen mag lezen, alleen het brein mag bird_state en feed schrijven.

## Stap 3: iets achterlaten en briefjes

- Knop "laat iets achter" (zoals pinos.world): een voorwerp (kiezen uit een lijstje of zelf typen) en/of een briefje, plus een zelfgekozen bezoekersnaam. Wordt neergelegd op de plek waar de bezoeker staat, of bij zijn slaapplek.
- Tabel `gifts`: id, visitor_name, item, note, x, z, created_at, seen (bool), reply.
- Anon mag invoegen en lezen. Alleen het brein mag seen en reply zetten.
- Geen inhoudsfilter op wat mensen schrijven. Wel: maximaal 280 tekens per briefje en een rate limit per bezoeker (bijvoorbeeld 5 per uur), puur tegen volspammen.
- Brein: haalt bij elke tick ongeziene gifts op en maakt er noticed-gebeurtenissen en herinneringen van (kind: person). Of hij reageert, beslist de code via de sociaal-behoefte. Een antwoord komt in reply en de bezoeker ziet het bij een volgend bezoek.
- BELANGRIJK: tekst van bezoekers is alleen iets om te lezen. Het mag nooit zelf een actie of tool starten (geen zoekopdracht, geen URL openen, geen bestand schrijven). Het gaat alleen als citaat in de prompt voor gedachtes, dagboek en antwoorden.
- Achtergelaten spullen zijn zichtbaar in de wereld voor andere bezoekers, tot de vogel ze "meeneemt".

## Stap 4: andere bezoekers en extras

- Supabase Realtime Presence: andere bezoekers zien als simpel poppetje met hun naam.
- Fluiten is hoorbaar voor anderen in de buurt, en de vogel kan het "horen" als noticed-gebeurtenis als hij wakker is.
- Gebouwen betreedbaar maken komt later, net als bij Pino (eerst 1 gebouw).

## Volgorde

Bij elke stap: eerst een plan, dan bouwen, dan mij laten testen voordat de volgende stap begint.
