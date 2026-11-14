# Brein v2: ombouw naar een drive-systeem

Gebruik Opus voor deze stap.

Het huidige brein laat het LLM elke actie kiezen. Dat gaan we ombouwen naar de aanpak van Pino (pinos.world, zie pinos.world/developers voor zijn open API): beslissingen, behoeftes en geheugen zitten in gewone code, het LLM verwoordt alleen. Bekijk eerst de bestaande code en state.json, en stel een migratieplan voor voordat je iets weghaalt. Bestaande dagboekentries en tekeningen blijven bewaard.

## Kernprincipe

Code beslist, het model praat. Het LLM schrijft alleen tekst: een gedachte, de reden voor een actie, een dagboekentry, een zoekopdracht, een SVG, een samenvatting. Het kiest nooit zelf wat de vogel gaat doen. Zo blijft het ook met een klein lokaal model betrouwbaar.

## 1. Behoeftes en gevoel

- Vijf behoeftes, elk van 0 (vervuld) tot 1 (dringend): rust, nieuwsgierigheid, sociaal, expressie, stilte. Ze lopen per tick langzaam op met een eigen snelheid en zakken als een passende actie lukt.
- Mood en energie, elk van -1 tot 1. Energie zakt door activiteit en herstelt door rust en slaap. Mood volgt uit gelukte en mislukte acties en uit herinneringen.
- Optioneel een gevoel in woorden (`feeling.words`), door het LLM geschreven op basis van de getallen, alleen als die flink veranderd zijn.

## 2. Acties en keuze (in code)

- Een vaste lijst acties met voorwaarden en effecten, bijvoorbeeld: zoeken (verlaagt nieuwsgierigheid), dagboek schrijven (expressie, stilte), tekenen (expressie), rondlopen of naar een plek gaan, stilzitten (rust), iets opruimen of herlezen, slapen.
- Kies per tick met utility-scoring: score = hoe dringend de behoefte is × hoe goed de actie hem vervult, plus een bonus uit overtuigingen ("tekenen beurt me op") en een beetje ruis, zodat hij niet voorspelbaar wordt.
- Acties kunnen mislukken (`ok: false`, bijvoorbeeld zoeken zonder resultaat). Dat telt mee voor mood en voor overtuigingen.
- Pas na de keuze vraagt de code het LLM om de gedachte en de reden ("why") in zijn eigen stem.

## 3. Geheugen (klein, met opzet)

- Kortetermijngeheugen en langetermijngeheugen met een vaste maximale grootte (bijvoorbeeld 30 kort, 60 lang).
- Elke herinnering heeft: text, kind (fact, person, work, moment), strength (1-5), recalled (hoe vaak teruggehaald) en since.
- Iets nieuws komt alleen binnen door iets zwakkers eruit te duwen (laagste strength × recalled). Ophalen verhoogt recalled.
- Bij elke LLM-call gaan alleen de paar meest relevante herinneringen mee, niet alles. Zo blijft de context klein.

## 4. Overtuigingen

- Overtuigingen met een bewijsteller, bijvoorbeeld "tekenen bij het raam beurt me op" (evidence: 12). Die ontstaan in code uit patronen: als een actie op een plek vaak mood verhoogt, groeit of ontstaat een overtuiging.
- Overtuigingen beïnvloeden de actiekeuze (stap 2).

## 5. Principes (holdsTo)

- Drie zinnen waar hij zich aan houdt, vastgelegd in het karakterblad. Ze filteren wat er van zoekresultaten en gebeurtenissen in het geheugen terechtkomt: wat erbij past, krijgt een hogere strength.
- Laat mij de drie principes kiezen uit voorstellen.

## 6. Karakterblad en slaap

- Een karakterblad: name, core, backstory, traits, values, fears, quirks, voice, holdsTo. Dit zegt wie hij is, niet wat hij moet doen.
- Slaap is consolidatie. Als hij gaat slapen (of bij de eerste run nadat de laptop uit stond): kortetermijngeheugen samenvatten, het sterkste doorzetten naar langetermijn, de rest vergeten, overtuigingen bijwerken, en hooguit één toevoeging aan zijn karakterblad (in een apart veld `added`, zodat zichtbaar blijft wat hij zelf heeft toegevoegd).
- Laptop uit betekent slapen.

## 7. Tijd en ticks

- Een eigen wereldtijd: een dag in zijn wereld duurt ongeveer 3 echte uren. Houd ook `day` bij (de hoeveelste dag van zijn leven).
- Ticks zijn goedkoop omdat beslissen in code gebeurt. Bijvoorbeeld elke 1-2 minuten een tick terwijl de laptop aanstaat, en alleen een LLM-call als er iets te verwoorden valt. Stem dit af op wat mijn hardware aankan.

## 8. Feed

Alles wat gebeurt, komt in een feed met kinds:
- `did`: een actie, met `why` en `ok`
- `noticed`: iets wat hij zag of las
- `felt`: een gevoelsverandering
- `mind`: iets wat hij oppakt of loslaat (want, worry, question, promise), met `change: opened/closed`

## 9. Output als API-achtige JSON

Schrijf na elke tick deze bestanden, met dezelfde opzet als Pino's API (elk antwoord begint met `v` en `at`):
- `data/now.json`: naam, asleep, doing, thought, feeling (mood, energy, words), needs, world (day, time)
- `data/feed.json`: laatste 50 entries, nieuwste eerst
- `data/mind.json`: laatste gedachte, wat het hardst trekt, open wants/worries/questions, holdsTo
- `data/memories.json`: beliefs, long, short
- `data/who.json`: het karakterblad plus `added`
De site en het dashboard-panel lezen alleen deze bestanden. Pas daarna git commit + push, niet na elke tick maar bijvoorbeeld elke 10 minuten.

## 10. Model

- Check mijn hardware (GPU, VRAM). Pino draait op een klein Llama-model plus gpt-oss-20b en -120b. Als het past: gpt-oss-20b via Ollama voor dagboek en reflectie, en een kleiner snel model voor korte gedachtes en redenen. Past het niet: één klein model voor alles.
- Geen echt geld, geen aankopen, geen accounts. Wel mag hij een denkbeeldig budget en een verlanglijst hebben.

## 11. Optioneel: Pino als buurman

Pino heeft een open API zonder key (https://pinos.world/api/v1/now en /feed). Laat mijn vogel daar af en toe (hooguit een paar keer per dag) naar kijken als "noticed"-gebeurtenis, zodat hij een mening over Pino kan vormen. Alleen lezen.

## Volgorde

1. Migratieplan voorstellen, mij laten akkoord geven.
2. Behoeftes, acties en utility-keuze, zonder LLM, en laat mij een simulatie van 100 ticks zien (welke acties, hoe de behoeftes bewegen).
3. Geheugen, overtuigingen en slaap.
4. LLM-verwoording aansluiten.
5. JSON-output en de site aanpassen naar de nieuwe bestanden.
