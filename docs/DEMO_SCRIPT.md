# Backstory — demo video script

**Hard limit:** 3:00. Judges may ignore anything after that. Land at **2:45–2:50**.

Hack Hydra asks the video to cover four things, in this order:

1. The problem
2. What you built
3. The product working
4. How you used the HydraDB repo, and why that matters

This script hits all four. Do not add a fifth demo, a scoreboard, or a slide deck.

Spoken pace: about 140 words per minute. The lines below are about 380 words. If you run long, cut the live-typing beat first, not HydraDB.

---

## Setup (do this before you press record)

1. Sign in at https://backstory.fly.dev/app so Google OAuth is not in the take.
2. Click **+ new chat**. That clears the screen only. Memory stays.
3. Browser: 1440×900 or larger, zoom about 110%. Chat text dies in compression if it is smaller.
4. Second tab: https://github.com/Datwebguy/Backstory scrolled to `docs/ARCHITECTURE.md`.
5. Optional third tab: a terminal that already shows `SMOKE OK` from  
   `python -m backstory.tools.smoke_hydradb`.
6. Theme: light or dark, pick one and leave it. Do not narrate the toggle.
7. Do not open the sign-in page on camera.

Demo cards write into a `demo:` sandbox. They will not mix with your real account. If an old answer looks wrong, click **+ new chat** and run the card again on the deployed app.

---

## Shot list

### 0:00–0:18 — Problem, then the name

**Screen:** https://backstory.fly.dev/ (landing, conversation cards moving).

**Say:**

> Assistants forget. Last month’s conversation is a blob of text. When the window fills up, the fact is gone.

> This is Backstory. It is a memory layer for conversational agents, built for Track 03. What you say becomes versioned facts in a HydraDB graph. It can answer weeks later, say what changed, and refuse when the graph does not have the answer.

Hold the landing for one extra beat after the name. Do not rush into `/app`.

---

### 0:18–0:52 — A fact that changed

**Screen:** `/app`. Click **Changed plans**.

The thread seeds three dated lines, then asks *Where do I work now?*

Wait until the answer shows Company B. Then click **based on N memories**.

**Say:**

> February: Company A. May: left. June: Company B. Three conversations, four months. It answers Company B.

> Company A is still here. It is marked superseded, with the date it stopped being true. That is a SUPERSEDES edge in HydraDB. It is not “whichever sentence ranked highest.”

If the drawer is slow, keep talking over it. Do not apologize to the camera.

---

### 0:52–1:18 — It knows when it does not know

**Screen:** **+ new chat**, then **Knows when it does not know**.

Memory has a 16 GB staging instance and a 32 GB production instance. The question is *How many services run on the 64 GB instance?*

Wait for the refuse.

**Say:**

> Related facts exist. Two sized instances. A nearest-neighbor search would answer from the closest one.

> It refuses. Sixty-four gigabytes was never stated. That gate is in the engine. The model does not get to invent a no.

---

### 1:18–1:46 — Why, not only what

**Screen:** **+ new chat**, then **Decision history**.

Four dated lines, then *Why did we choose Postgres?*

**Say:**

> MongoDB in January. Postgres in March. A consistency requirement in April that never names the database. A standard in June.

> The reason is spread across four sessions. Backstory walks the SUPERSEDES chain and pulls the requirement that justified the switch. A transcript store cannot do that.

Skip **Remembered across conversations**. Three working demos is enough. A fourth will blow the HydraDB section.

---

### 1:46–2:02 — It is a product

**Screen:** **+ new chat**. Type, do not click a card.

Type: `my name is Eben`  
Then: `what is my name?`

**Say:**

> That was live, not a fixture. Every account signs in with Google and gets its own graph. The demo cards you just saw run in a separate sandbox.

If the name question is slow, cut after “I’ll keep that” and move on.

---

### 2:02–2:38 — How HydraDB is used, and why it matters

**Screen:** GitHub, `docs/ARCHITECTURE.md`, then a glance at `src/backstory/hydra/schema.py`. If you have it, cut to the 10 of 10 smoke result.

**Say:**

> HydraDB’s graph-node is the source of truth. Users, sessions, facts, entities, SUPERSEDES, CONTRADICTS: all nodes and edges. Answers are a traversal from seed entities, not a similarity search over chat logs.

> The SQLite sidecar only mints integer ids and holds a rebuildable index. It is not allowed to answer.

> We used the public HydraDB image, the documented Docker ports, and the Cypher the OSS parser actually accepts. No Hydra Cloud.

> On a vector store, the old employer and the new one look equally similar to “where do I work.” Current versus historical is an edge. That is why the graph is the product, not a cache in front of one.

---

### 2:38–2:50 — Close

**Screen:** landing page again. If the footer shows the supersede chain, leave it visible.

**Say:**

> One fact, three points in time. Two superseded, one current, all three still on record.

> Backstory is live at backstory.fly.dev. The code is on GitHub.

Stop talking. Hold two seconds. End.

---

## Teleprompter (read this if you only want the spoken track)

Assistants forget. Last month’s conversation is a blob of text. When the window fills up, the fact is gone.

This is Backstory. It is a memory layer for conversational agents, built for Track 03. What you say becomes versioned facts in a HydraDB graph. It can answer weeks later, say what changed, and refuse when the graph does not have the answer.

February: Company A. May: left. June: Company B. Three conversations, four months. It answers Company B.

Company A is still here. It is marked superseded, with the date it stopped being true. That is a SUPERSEDES edge in HydraDB. It is not “whichever sentence ranked highest.”

Related facts exist. Two sized instances. A nearest-neighbor search would answer from the closest one.

It refuses. Sixty-four gigabytes was never stated. That gate is in the engine. The model does not get to invent a no.

MongoDB in January. Postgres in March. A consistency requirement in April that never names the database. A standard in June.

The reason is spread across four sessions. Backstory walks the SUPERSEDES chain and pulls the requirement that justified the switch. A transcript store cannot do that.

That was live, not a fixture. Every account signs in with Google and gets its own graph. The demo cards you just saw run in a separate sandbox.

HydraDB’s graph-node is the source of truth. Users, sessions, facts, entities, SUPERSEDES, CONTRADICTS: all nodes and edges. Answers are a traversal from seed entities, not a similarity search over chat logs.

The SQLite sidecar only mints integer ids and holds a rebuildable index. It is not allowed to answer.

We used the public HydraDB image, the documented Docker ports, and the Cypher the OSS parser actually accepts. No Hydra Cloud.

On a vector store, the old employer and the new one look equally similar to “where do I work.” Current versus historical is an edge. That is why the graph is the product, not a cache in front of one.

One fact, three points in time. Two superseded, one current, all three still on record.

Backstory is live at backstory.fly.dev. The code is on GitHub.

---

## Coverage

| Required | Where |
|---|---|
| The problem | 0:00 |
| What you built, by name | 0:08 |
| Demo working | 0:18–2:02 |
| HydraDB how and why | 2:02–2:38 |

Judging, mapped to a shot:

- Technical execution: superseded Company A in the drawer; 64 GB refuse; smoke 10/10 if you show it
- Graph-native HydraDB: SUPERSEDES / traversal / sidecar cannot answer
- Product: signed-in `/app`, live type-in, isolated accounts
- Results: real engine output, no mocked bubbles
- Originality: why-across-sessions, and refuse when neighbors exist

---

## Do not say on camera

- Do not say you aced LongMemEval-S, or that you ran the 500-question / 115k set.
- Do not say you beat RAG, mem0, or any baseline as a leaderboard result.
- Do not say you have an official LME-V2 or official BEAM number.
- Do not say Hydra Cloud.
- Do not say the sidecar answers questions.
- Do not mention hydradb#81 unless a judge asks later. It is not a video beat.

If a judge later asks for a number, the true line is: official `evaluate_qa.py gpt-4o` on a **12-question oracle slice**, **9/12**, abstention **2/2**. That is not an S-500 score. Do not put it in this video unless you have ten spare seconds at 2:35 and you say the full caveat. Prefer the product.

---

## Safe to say

- Facts are versioned. Superseded values stay, with dates.
- Abstention is an engine gate. Neighbors can exist and it still refuses.
- Each Google account has its own graph. Demo cards use a sandbox.
- HydraDB graph-node is the record. The sidecar cannot answer.
- Public image, OSS Cypher subset, no Hydra Cloud.
- Live at backstory.fly.dev. Code at github.com/Datwebguy/Backstory.

---

## After the take

- Export 1080p, 16:9, under 3:00.
- Upload unlisted YouTube (or equivalent).
- Submit the official form the same day: repo, https://backstory.fly.dev/, video.
- Deadline: 20 August 2026, 11:59 PM PT.
