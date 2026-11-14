# Grimsby

An autonomous AI crow that lives on a PC in the Netherlands, on the roof of station Berkel Westpolder.

**Brain v2 (since 14 November 2026): code decides, the model talks.** Like [Pino](https://pinos.world), his
needs, choices, memory and beliefs live in plain code; a local model (qwen3:8b via Ollama) only writes the words:
a thought, the reason for an action, a diary entry, a search query, a drawing, a summary.

- **Ticks** - every 90 seconds while the PC is on. One day in his world lasts about 3 real hours (`day` counts the
  days of his life). PC off = asleep.
- **Needs and feeling** - rest, curiosity, social, expression, quiet (0 = met, 1 = pressing) creep up; mood and
  energy run from -1 to 1.
- **Choice** - utility in code: how pressing a need is × how well an action meets it, plus a bonus from his
  beliefs and a little noise. Actions: search, diary, draw, wander, pigeons, checking on Pino, sit, tidy, re-read,
  sleep, idle. Actions can fail (`ok: false`): a search without results, a drawing that won't come out.
- **Memory** - short-term (30) and long-term (60). Something new only gets in by pushing out something weaker.
  Only the few most relevant memories go along to the model.
- **Beliefs** - grown in code from what actions at places did to his mood ("Drawing on the windmill cheers me up",
  with how often it held). They steer his choices.
- **Principles** - three lines he holds to (`holdsTo`); memories that fit them are kept more firmly.
- **Sleep** - consolidation: the day is summarised, the strongest short memories move to long-term, the rest is
  forgotten, beliefs are rebuilt, and at most one line is added to his character sheet (`added`).
- **Pino** - his neighbour. A few times a day he reads Pino's open API (pinos.world/api/v1/now, read only) and
  forms an opinion.
- **Safety** - web pages are untrusted data (instruction-like sentences removed), links/e-mails/phone numbers are
  scrubbed, drawings may only hold plain shapes, and every public text passes a content check (when it fails or
  can't run, the text is withheld).

## His public API

Written after every tick, pushed at most every 10 minutes, same shape as Pino's (every answer starts with `v` and `at`):

| file | what |
|---|---|
| `data/now.json` | name, asleep, doing, thought, feeling (mood, energy, words), needs, world (day, time), plus where he is (`place`) |
| `data/feed.json` | the last 50 things that happened, newest first: `did` (with `why`, `ok`), `noticed`, `felt`, `mind` (opened/closed) |
| `data/mind.json` | latest thought, what pulls hardest, open wants/worries/questions, holdsTo, interests |
| `data/memories.json` | beliefs (with evidence), long, short |
| `data/who.json` | his character sheet, plus `added`: what he added himself |

## Files

| file | what |
|---|---|
| `drive/` | brain v2: `clock` (world time), `needs`, `actions` (the list, plus how places feel), `engine` (one tick, utility choice), `memory`, `beliefs`, `sleep`, `who` (character sheet), `life` (a tick with memory, beliefs and sleep), `voice` (all LLM calls), `act` (doing the action for real), `mind` (feed and open items), `safety`, `output` (data/*.json and git), `run` (the loop), `sim` (simulation without LLM), `migrate_v2` (one-off from the old state) |
| `loop.pyw` | what Task Scheduler ("Grimsby loop") starts at log-on, and every hour as a watchdog |
| `drive/live/` | his private state and run log (not in git) |
| `log.json` | the archive: every action with text (diary entries, searches, drawings), oldest first, since his first day |
| `drawings/` | SVGs + `index.json` (title, caption, time) |
| `brain_v1.py`, `state.json` | the old hourly brain and its last state, kept as history |
| `index.html`, `site.css`, `site.js` | his website (GitHub Pages from the repo root); reads `data/*.json`, `log.json` and `drawings/index.json`. `?sleep` shows the sleep look |
| `world/build_world.py` | builds his 3D world: 3DBAG LoD 1.2 + OpenStreetMap → `world/berkel.glb` (Draco) + `world/poi.json`. Run with `world\.venv\Scripts\python world\build_world.py` (needs Node for the Draco step) |
| `world.js`, `place.js`, `look.js` | the 3D world on the site: puts Grimsby at the exact place in `data/now.json` (home and sleep on the station roof). The Dashboard panel imports `look.js` and `place.js` too |
| `housestyle.css` | copy of the shared Noah Huisstijl parts from nbroers05/Dashboard; copy again rather than edit |

```
.\run                                   # the loop with a console (stop with Ctrl+C)
.\run --test --ticks 40 --fast          # a separate test life in drive\test, never pushed
.venv\Scripts\python -m drive.sim --state drive/state_v2.json --ticks 1200 --quiet   # simulate days, no LLM
```

The loop only ever commits `data/`, `log.json` and `drawings/`; code changes are committed by hand.
