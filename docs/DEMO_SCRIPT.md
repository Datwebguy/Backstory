# Demo video script

Three minutes maximum. Aim for 2:55 so the upload is not rejected on a
rounding error.

## Before you record

Setup, in order:

1. Sign in at <https://backstory.fly.dev/app> first, so the Google
   redirect is not part of the take.
2. Press **+ new chat** so the transcript area is empty. This clears the
   screen only; anything already remembered stays remembered, which is
   worth knowing so you are not surprised by the drawer later.
3. Open a second tab on the repository, already scrolled to
   `docs/ARCHITECTURE.md`.
4. Optional but better: a third tab with the terminal showing
   `python -m backstory.tools.smoke_hydradb` already run, so the 10 of
   10 result is on screen without waiting for it.

Recording:

- 1440x900 or larger. Browser zoom about 110%, since chat text is small
  after compression.
- Demo scenarios write to a separate sandbox account, not to your own
  memory, so running them on camera does not pollute what you show
  later.
- Do not narrate the sign in screen. It is a Google page, and it says
  nothing about the product.

---

## 0:00 to 0:15 — the problem, on the landing page

**On screen:** <https://backstory.fly.dev/>, scrolled slowly to the
floating conversation cards.

> "Most assistants forget. Ask about something you said last month and
> it is gone, because the conversation was stored as text and then
> truncated away. Backstory stores what you said as facts in a graph."

Let one or two of the drifting cards be legible before moving on.

> "Every exchange on this page is real output from the running engine."

---

## 0:15 to 0:50 — a fact that changed

This is the core claim. Do not rush it.

**On screen:** `/app`, click **Changed plans**.

The seeded messages play: at Company A in February, left in May, joined
Company B in June. Then the question runs, *Where do I work now?*

> "Three statements across four months, and the later ones contradict
> the first. It answers Company B."

Click **based on N memories** to open the drawer.

> "And here is the part that matters. Company A was not overwritten. It
> is still on record, marked superseded, with the date it stopped being
> true. That lineage is a SUPERSEDES edge in HydraDB, not a sort by
> timestamp."

---

## 0:50 to 1:15 — knowing when it does not know

**On screen:** **+ new chat**, then **Knows when it does not know**.

The history mentions a 16 GB staging instance and a 32 GB production
instance. The question asks about a 64 GB instance.

> "Memory that guesses is worse than memory that admits a gap. There are
> related facts here, two sized instances, so a similarity search would
> happily answer from the nearest one."

Let the refusal render.

> "It refuses, because the specific thing asked about is not in the
> graph. That is a gate in the engine, not the model being polite."

---

## 1:15 to 1:45 — why, not just what

**On screen:** **+ new chat**, then **Decision history**.

MongoDB planned in January, Postgres preferred in March, a strong
consistency requirement in April, standardised on Postgres in June.
Then, *Why did we choose Postgres?*

> "This is the question a transcript cannot answer. The reason is spread
> across four conversations, and the deciding fact, the consistency
> requirement, never mentions Postgres at all."

Let the answer render.

> "It reconstructs the decision by following what replaced what, and
> pulls in the requirement behind the switch."

---

## 1:45 to 2:10 — live, and private per account

**On screen:** type into the composer directly. Do not use a scenario
button here; the point is that this is not canned.

Type `my name is Eben`, then `my birthday is March 12`, then ask
`what is my birthdate?`

> "This is live. And note it answers birthdate from a fact stored as
> birthday."

> "Every account has its own graph, enforced on the server, so nobody
> sees anyone else's memory."

---

## 2:10 to 2:40 — how HydraDB is actually used

**On screen:** the repository tab, `docs/ARCHITECTURE.md`, then
`src/backstory/hydra/schema.py`. If you prepared the terminal tab, show
the 10 of 10 smoke result here.

> "HydraDB is the source of truth, not a cache. Facts, entities,
> sessions, and the SUPERSEDES and CONTRADICTS edges between them all
> live in the graph, and answers come from traversal, not nearest
> neighbour text search. The SQLite sidecar only mints integer ids and
> holds a rebuildable index. It is not allowed to answer a question."

If you have a spare beat:

> "Every Cypher pattern here was validated against the running engine,
> including the ones it rejects."

---

## 2:40 to 2:55 — close on the footer

**On screen:** scroll to the landing page footer, where the supersede
chain draws itself.

> "One fact, three points in time. Two superseded, one current, all
> three still on record. Tell it once, come back later, and it still
> knows what changed. Backstory is live at backstory dot fly dot dev,
> and the code is on GitHub."

---

## Claims to avoid on camera

These are not pedantry. Each one is something the project cannot
currently back up, and a judge who checks will find that out.

- **No LongMemEval score.** The official `evaluate_qa.py` judge has
  never been run, because it requires an OpenAI key with credit. Say
  "we built the official evaluation path" if you must mention it, not
  "we scored X".
- **No BEAM result.** The adapter and runner exist and are in the repo,
  but no run was completed. If that changes before you record, quote it
  as "judged against BEAM's published rubrics", never as an official
  BEAM score.
- **Do not claim to beat a baseline.** The one measured slice, twelve
  questions scored by loose token overlap, showed parity with a naive
  graph ablation and with session retrieval. That is a diagnostic, not
  a result.
- **Do not call the storage bug ours or theirs loosely.** If it comes
  up: it is a confirmed upstream HydraDB issue, filed as
  hydra-db/hydradb#81, and the deployment works around it by using
  S3 compatible storage. That is a good story, told accurately.

## Things worth saying, because they are true

- Facts are versioned. Superseded values are kept with their dates.
- Abstention is a gate in the engine, demonstrable on a question whose
  neighbours exist in memory.
- Each account is isolated server side.
- HydraDB is the graph of record; the sidecar cannot answer questions.
- The engine works without an LLM, and degrades to that path
  automatically if the provider fails.
