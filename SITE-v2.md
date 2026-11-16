# Site v2: the brain up front

Since 16 November 2026 the site has three tabs:

- `index.html#brain`: the 3D brain (19 regions, 49 connections). Click a region for what it does and what it connects to.
- `index.html#simulation`: a separate JS brain that keeps living in the browser. You give him stimuli and watch them travel through the brain. Presets crow, human and pigeon, plus separate knobs.
- `world.html`: the old homepage, unchanged apart from the tabs at the top. `/#world` (the old link to the expanded world) forwards to `world.html#world`.

## Files

| file | what |
|---|---|
| `index.html` | the new homepage: tabs brain and simulation, three.js r128 as a plain script tag |
| `brein.js` | the simulation brain and the 3D view: regions (`REG`), connections (`EDGES`), places, actions, character knobs, stimuli |
| `world.html` | used to be `index.html`, now a subpage. Still uses `site.js`, `site.css`, `world.js` and the rest |
| `supabase/sim.sql` | table `sim_log`: visitors can only add rows, not read them. Limit 20 per browser per hour |

## How the simulation keeps data

- His state (needs, learned values, fear, aversion, habits, character) stays in that browser's localStorage. Open the page again and he carries on. Page closed = his brain stands still.
- The log goes to `sim_log` in batches, at most every 5 minutes (each event holds his needs and the activation of every region). If the table does not exist yet, everything still works without it.
- Every visitor gets their own Grimsby in the simulation. It is separate from the real Grimsby in `drive/`.

## Note

- The simulation brain (`brein.js`) and the real brain (`drive/`) are two separate things. The plan is to move what works in the simulation over to `drive/` later.
