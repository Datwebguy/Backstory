# Demo video script (3 minutes maximum)

Target: under 3:00. Record at 1440x900 or larger, browser zoom around
110% so text is readable after compression.

Before recording:

- Sign in at https://backstory.fly.dev/app so the OAuth redirect is not
  part of the take.
- Use a fresh Google account, or run a demo scenario first and then
  press "+ new chat", so the memory drawer starts clean.
- Have the repository open in a second tab.

---

## 0:00 to 0:20 — the problem

**On screen:** the landing page at https://backstory.fly.dev/

> "Most assistants forget. Ask about something you said last month and
> it is gone, because the conversation was stored as text and then
> truncated away. Backstory stores what you said as facts in a graph,
> so it can still answer weeks later, and tell you when a fact changed."

Scroll once so the five stage pipeline is visible: extract, resolve,
version, retrieve, abstain.

---

## 0:20 to 1:00 — a fact that changes (the core claim)

**On screen:** `/app`, click the "Changed plans" scenario.

Let the seeded messages play: works at Company A in February, left in
May, joined Company B in June.

Then the question runs: *Where do I work now?*

> "Three statements across four months, and the second one contradicts
> the first. Backstory answers Company B, and it does not silently
> discard the earlier answer."

Click "Based on N memories" to open the memory drawer.

> "This is the history. Company A is kept and marked superseded,
> Company B is current. That lineage is a SUPERSEDES edge in HydraDB,
> not a timestamp sort."

---

## 1:00 to 1:30 — knowing when it does not know

**On screen:** "+ new chat", then the "Knows when it does not know"
scenario.

> "Memory that guesses is worse than memory that admits a gap. Here the
> history mentions a ten and a twenty gallon tank. The question asks
> about a thirty gallon tank."

Let the abstention answer render.

> "It refuses, because the asked-for constraint is not in the graph.
> That is a gate in the engine, not the model being cautious."

---

## 1:30 to 2:10 — it is really per user, and really live

**On screen:** type into the composer directly.

Type: `my name is Eben`, then `what is my name?`

> "This is live, not a scripted demo. Every account gets its own graph,
> so nobody sees anyone else's facts, and the demo scenarios are kept
> in a separate sandbox so they never pollute your real memory."

Open the memory drawer to show the single stored fact.

---

## 2:10 to 2:45 — how HydraDB is actually used

**On screen:** switch to the repository, `docs/ARCHITECTURE.md`, then
`src/backstory/hydra/schema.py`.

> "HydraDB is the source of truth, not a cache. Facts, entities,
> sessions, and the SUPERSEDES and CONTRADICTS edges between them all
> live in the graph. Answers come from graph traversal from seed
> entities, not from nearest neighbour text search. The SQLite sidecar
> only mints integer ids and holds a rebuildable index; it is not
> allowed to answer a question."

If time allows, show the smoke output: 10 of 10 HydraDB capability
checks passing.

---

## 2:45 to 3:00 — close

> "Backstory. Tell it once, come back later, it still knows what
> changed, and it says so when it does not know. It is live at
> backstory dot fly dot dev, and the code is on GitHub."

**On screen:** the landing page footer, then the repository URL.

---

## Things to say only if they are true at record time

- Do not claim a LongMemEval score. The official judge has not been run.
- BEAM results, if quoted, are "judged against BEAM's rubrics", not an
  official BEAM score.
- Do not claim to beat any baseline. The measured 12 question slice
  showed parity with naive and session retrieval baselines.
