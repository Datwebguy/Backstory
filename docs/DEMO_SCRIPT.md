# Demo video script

Three minutes maximum, and the rules say content past that may not be
reviewed. Aim to land at 2:50.

Hack Hydra asks the video to cover four things by name. This script is
built around them, in this order, so none is left to chance:

1. the problem you are trying to solve
2. what you actually built
3. a demo of the project working
4. how you used the HydraDB repo and why it matters

---

## Before you record

1. Sign in at <https://backstory.fly.dev/app> first, so the Google
   redirect is not part of the take.
2. Press **+ new chat**. That clears the screen only. Anything already
   remembered stays remembered, so the drawer will not surprise you.
3. Second tab on the repository, scrolled to `docs/ARCHITECTURE.md`.
4. Third tab, optional but better: a terminal that has already run
   `python -m backstory.tools.smoke_hydradb`, so the 10 of 10 result is
   on screen without dead air.

Settings: 1440x900 or larger, browser zoom about 110%, chat text is
small after compression. Demo scenarios write to a separate sandbox
account, so running them on camera does not pollute what you show
later. Do not narrate the Google sign in page.

---

## 0:00 to 0:20 — the problem, and what this is

Both required elements one and two. Say the name and the shape of the
thing early; a judge watching many entries should know what they are
looking at inside ten seconds.

**On screen:** <https://backstory.fly.dev/>, drifting conversation cards
visible.

> "Assistants forget. Ask about something you said last month and it is
> gone, because the conversation was stored as text and then truncated
> away."

> "This is Backstory, a memory layer for conversational agents, built
> for Track 03. It stores what you say as versioned facts in a HydraDB
> graph, so it can answer weeks later, tell you when something changed,
> and say plainly when it does not know."

> "Every exchange on this page is real output from the running engine."

---

## 0:20 to 0:55 — demo one, a fact that changed

Element three starts here. This is the core claim; do not rush it.

**On screen:** `/app`, click **Changed plans**.

Seeded: at Company A in February, left in May, joined Company B in
June. Then, *Where do I work now?*

> "Three statements across four months, and the later ones contradict
> the first. It answers Company B."

Click **based on N memories**.

> "And here is the part that matters. Company A was not overwritten. It
> is still on record, marked superseded, with the date it stopped being
> true. That is a SUPERSEDES edge in the graph, not a sort by
> timestamp."

---

## 0:55 to 1:20 — demo two, knowing when it does not know

**On screen:** **+ new chat**, then **Knows when it does not know**.

Memory holds a 16 GB staging instance and a 32 GB production instance.
The question asks about a 64 GB instance.

> "Memory that guesses is worse than memory that admits a gap. There are
> related facts here, two sized instances, so a similarity search would
> happily answer from the nearest one."

> "It refuses, because the specific thing asked about is not in the
> graph. That is a gate in the engine, not the model being polite."

---

## 1:20 to 1:45 — demo three, why and not just what

**On screen:** **+ new chat**, then **Decision history**.

MongoDB planned in January, Postgres preferred in March, a consistency
requirement in April, standardised in June. Then, *Why did we choose
Postgres?*

> "This is the question a transcript cannot answer. The reason is spread
> across four conversations, and the deciding fact, the consistency
> requirement, never mentions Postgres at all."

> "It reconstructs the decision by following what replaced what, and
> pulls in the requirement behind the switch."

---

## 1:45 to 2:05 — that it is a product, not a script

Covers product completeness and usability, which is a judging criterion
on its own.

**On screen:** type into the composer directly, do not use a button.

Type `my name is Eben`, then `my birthday is March 12`, then ask
`what is my birthdate?`

> "This is live, and it answers birthdate from a fact stored as
> birthday."

Tap the theme toggle once while talking.

> "It is deployed, every account signs in with Google and gets its own
> isolated graph, and it works on a phone and in dark mode."

---

## 2:05 to 2:40 — how HydraDB is used, and why it matters

Required element four. Give it the time; it is also a judging criterion
and a repository requirement.

**On screen:** the repository, `docs/ARCHITECTURE.md`, then
`src/backstory/hydra/schema.py`. Show the 10 of 10 smoke result if you
prepared it.

> "HydraDB is the source of truth, not a cache. Users, sessions, facts,
> entities, and the SUPERSEDES and CONTRADICTS edges between them all
> live in the graph. Answers come from traversal out of seed entities,
> not nearest neighbour text search. The SQLite sidecar only mints ids
> and holds a rebuildable index; it is not allowed to answer anything."

Why it matters, in one line:

> "On a vector store, the superseded value and the current one look
> equally similar to a query. Current versus historical, what replaced
> what, and what contradicts what are edges, so a graph is what makes
> the answer and its history separable at all."

---

## 2:40 to 2:55 — close

**On screen:** the landing page footer, where the supersede chain draws.

> "One fact, three points in time. Two superseded, one current, all
> three still on record. Backstory is live at backstory dot fly dot dev,
> and the code is on GitHub."

---

## Coverage check before uploading

Required elements:

- [ ] the problem — 0:00
- [ ] what you built, by name — 0:10
- [ ] a demo of it working — 0:20 to 2:05, three scenarios plus live typing
- [ ] how HydraDB is used and why it matters — 2:05 to 2:40

Judging criteria, and where the video speaks to each:

- [ ] technical execution — the supersede lineage in the drawer, the
      abstention gate, the smoke result
- [ ] use of HydraDB and graph native approaches — 2:05 section, plus
      the vector store contrast
- [ ] product completeness and usability — deployed, signed in, per
      account, phone and dark mode, 1:45 section
- [ ] quality of results — real transcripts throughout, and no invented
      numbers
- [ ] originality — answering *why* across four sessions, and refusing
      when neighbours exist

---

## Claims to avoid on camera

Each of these is something the project cannot currently support, and a
judge who checks will find out.

- **No LongMemEval score.** The official `evaluate_qa.py` judge has
  never been run; it needs an OpenAI key with credit. You may say "we
  built the official evaluation path", never "we scored X".
- **No BEAM result.** The adapter and runner are in the repo, but no run
  completed. If that changes, quote it as "judged against BEAM's
  published rubrics", never as an official BEAM score.
- **Do not claim to beat a baseline.** The one measured slice, twelve
  questions scored by loose token overlap, showed parity with a naive
  graph ablation and with session retrieval. That is a diagnostic.
- **The storage bug is upstream, and say so precisely.** It is
  hydra-db/hydradb#81, confirmed and reproduced, and the deployment
  works around it with S3 compatible storage. Told accurately that is a
  strength, not an excuse.

## Safe to say, because it is true

- Facts are versioned; superseded values are kept with their dates.
- Abstention is an engine gate, shown on a question whose neighbours do
  exist in memory.
- Each account is isolated server side.
- HydraDB is the graph of record; the sidecar cannot answer questions.
- It runs without an LLM, and falls back to that path automatically if
  the provider fails.
- 19 engine tests, and 10 of 10 HydraDB capability checks, pass.

---

## Submission checklist (deadline 20 August 2026, 11:59 PM PT)

- [ ] Video, 3 minutes or less, uploaded to YouTube or similar. Unlisted
      is acceptable.
- [ ] Official Google Form submitted.
- [ ] Public repository: <https://github.com/Datwebguy/Backstory>

Repository requirements, all currently present:

- [x] complete source code
- [x] README with setup and run instructions
- [x] explanation of how HydraDB is used (README plus
      `docs/ARCHITECTURE.md`)
- [x] dependency and environment info (`pyproject.toml`, `.env.example`)
- [x] third party attribution (`NOTICE`)
- [x] open source license (`LICENSE`, MIT; HydraDB is AGPL 3.0 and runs
      as a separate service)
- [x] no commits before 12 August 2026 (first commit 14 August)
