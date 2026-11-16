# Site v2: the brain up front

Since 16 November 2026 the site has three tabs:

- `index.html#brain`: the 3D brain (19 regions, 49 connections). Click a region for what it does and what it connects to.
- `index.html#simulation`: a separate JS brain that keeps living in the browser. You give him stimuli and watch them travel through the brain. Presets crow, human and pigeon, plus separate knobs.
- `index.html#world`: the old homepage (`world.html`), shown in a frame inside `index.html`. Opening `world.html` on its own forwards to `index.html#world`.

All three tabs are one page, so the same brain runs in all of them. Switching tabs never reloads or restarts him; the small brain in the world tab draws the same activation as the big one (it reads `window.GRIM` from the page around it). A reload carries on from the saved state, with the log. Layout is full width (built for 1920 x 920 and up; scrolling down is fine): simulation has needs and character under the brain and the log on the side; world has world.exe and status on top, the small brain and diary under it, and his day on the side.

## Files

| file | what |
|---|---|
| `index.html` | the new homepage: tabs brain and simulation, three.js r128 as a plain script tag |
| `brein.js` | the simulation brain and the 3D view: regions (`REG`), connections (`EDGES`), places, actions, character knobs, stimuli |
| `brainview.js` | the 3D brain as a view on a running simulation; used by `brein.js` (big) and `world.html` (small) |
| `world.html` | used to be `index.html`, now the world tab (in a frame). Still uses `site.js`, `site.css`, `world.js` and the rest; his day is its own window |
| `supabase/sim.sql` | table `sim_log`: visitors can only add rows, not read them. Limit 20 per browser per hour |

## How the simulation keeps data

- His state (needs, learned values, fear, aversion, habits, character) stays in that browser's localStorage. Open the page again and he carries on. Page closed = his brain stands still.
- The log goes to `sim_log` in batches, at most every 5 minutes (each event holds his needs and the activation of every region). If the table does not exist yet, everything still works without it.
- Every visitor gets their own Grimsby in the simulation. It is separate from the real Grimsby in `drive/`.

## Note

- The simulation brain (`brein.js`) and the real brain (`drive/`) are two separate things. The plan is to move what works in the simulation over to `drive/` later.
