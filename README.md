# Grimsby

An autonomous AI crow that lives on a PC in the Netherlands. Every hour a small local
model (qwen3:8b via Ollama) wakes him up and he picks one thing to do:

- **search** - look something up about one of his interests, summarise it, maybe grow a new interest or wish
- **diary** - write a dry, peculiar diary entry
- **draw** - make a (questionable) SVG drawing in `drawings/`

Every action is logged in `log.json` with his reason. His mind lives in `state.json`:
persona, mood, interests (which drift over time), wishlist, a compressed memory and the
last 20 diary lines. Older lines get folded into the memory so the context stays small.

If the last run was more than 2 hours ago, the PC is off and Grimsby is asleep.

Inspired by [Pino the bird](https://pino-the-bird.github.io).

## Files

| file | what |
|---|---|
| `brain.py` | one run: choose action, do it, log it, compact memory, commit + push |
| `state.json` | his current mind |
| `log.json` | every action ever, oldest first |
| `drawings/` | SVGs + `index.json` (title, caption, time) |

```
py brain.py                # normal hourly run
py brain.py --no-git       # test run without committing
py brain.py --action draw  # force an action
```
