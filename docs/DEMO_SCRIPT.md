# Backstory — demo video script

**Hard limit:** 3:00. Speak this as a person, not a spec. Land at **2:50**.

Hack Hydra’s video must cover four things:

1. The problem you are trying to solve
2. What you actually built
3. A demo of the project working
4. How you used the HydraDB repository, and why it matters

Judges also listen for: technical execution, graph-native use of HydraDB, a real product, honest results, and an original idea. This script hits those without dumping jargon.

Pace: about 140 words a minute. The spoken track is ~390 words.

---

## Before you record

1. Sign in at https://backstory.fly.dev/app. Do not film Google sign-in.
2. Click **+ new chat**.
3. Browser 1440×900 or larger, zoom about 110%.
4. Second tab: https://github.com/Datwebguy/Backstory (README visible).
5. Optional third tab: `docs/ARCHITECTURE.md`.
6. One theme. Leave it.

If a demo card answers wrong, skip that line and keep going. Do not explain a miss on camera.

---

## Shot list

### 0:00–0:22 — Who is speaking, and what this is

**Screen:** https://backstory.fly.dev/

**Say:**

> Hello. I built Backstory. I’m Datwebguy on GitHub, Datweb3guy on X.

> This is a Track 03 project: Memory and Context Retrieval. Backstory is a memory layer for conversational agents. You tell it something once. Weeks later it still knows. If a fact changed, it can tell you what it used to be. If it never heard the thing you asked, it says so, instead of guessing.

Hold the landing for a beat after your name. Then go on.

---

### 0:22–0:42 — The problem the track is asking for

**Screen:** still the landing, then cut to `/app` as you finish.

**Say:**

> Most assistants store a chat as a pile of text. When the window fills, last month is gone. Even when the text is still there, the system cannot tell current from old. “I work at Company A” and “I work at Company B” look like two similar sentences. Track 03 is about memory that lasts across sessions, updates when life changes, and does not invent an answer.

---

### 0:42–1:12 — Demo: a fact that changed

**Screen:** `/app`. Click **Changed plans**. Wait for Company B. Open **on record** / **based on N memories** if it appears.

**Say:**

> Watch this. Three conversations, four months. In February, work is Company A. In May, that job ends. In June, Company B.

> Ask where I work now, and it says Company B. Open the evidence and Company A is still there, dated, marked as replaced. HydraDB did not overwrite the old fact. It linked the new one to the old one. That is how a graph remembers change. A search over chat logs cannot do that cleanly.

---

### 1:12–1:32 — Demo: it knows when it does not know

**Screen:** **+ new chat**, then **Knows when it does not know**. Wait for the refuse.

**Say:**

> Memory has a 16 gigabyte staging box and a 32 gigabyte production box. The question asks about 64 gigabytes. That size was never said.

> Related facts are sitting right there. A similarity search would answer from the nearest size. Backstory refuses. Guessing from a neighbour is the failure mode this track cares about. The refuse is a rule in the engine, not the model being polite.

If it answers with a number, do not narrate. Go to the next card.

---

### 1:32–1:52 — Demo: a decision across sessions

**Screen:** **+ new chat**, then **Decision history**.

**Say:**

> Four conversations. First a plan for MongoDB. Then a switch to Postgres. Then a requirement: we need strong consistency for billing. Then a standard: we standardised on Postgres.

> The requirement never names Postgres. The answer still uses it, because the graph kept the whole chain, not only the last sentence. That is original for this track: why, not only what.

Skip **Remembered across conversations**. Three working demos leave time for HydraDB.

---

### 1:52–2:42 — How we used HydraDB, what we learned, why it matters

**Screen:** GitHub README, then `docs/ARCHITECTURE.md` if you have the tab.

**Say:**

> HydraDB is not a cache in front of something else. We run the public open-source image, the graph-node process, locally in Docker and in production on Fly. Bolt on 7687, HTTP on 8443, admin on 9090. We did not use Hydra Cloud.

> People, sessions, messages, facts, and entities are nodes. When a fact replaces another, that is an edge. When two facts cannot both be true, that is another edge. Answers are a walk from those nodes, not “find similar text.”

> A small SQLite file only mints integer ids. It is not allowed to answer.

> What we learned from the repo: Hydra’s OpenCypher is a real subset. No IS NULL. No undirected matches. Writes have to follow their UNWIND rules exactly. We learned that by hitting the live parser, not by assuming Neo4j. We also learned Hydra is built for object storage, not a long-lived local disk, so the deployed graph sits on Tigris, Fly’s S3 store.

> If you swapped Hydra for a vector database, you would lose current versus history as a first-class thing. That is why the database is the product.

---

### 2:42–2:55 — Close

**Screen:** landing page.

**Say:**

> Backstory is live at backstory.fly.dev. Source is github.com/Datwebguy/Backstory. Thank you.

Stop. Two seconds of silence. End.

---

## Teleprompter (read this)

Hello. I built Backstory. I’m Datwebguy on GitHub, Datweb3guy on X.

This is a Track 03 project: Memory and Context Retrieval. Backstory is a memory layer for conversational agents. You tell it something once. Weeks later it still knows. If a fact changed, it can tell you what it used to be. If it never heard the thing you asked, it says so, instead of guessing.

Most assistants store a chat as a pile of text. When the window fills, last month is gone. Even when the text is still there, the system cannot tell current from old. “I work at Company A” and “I work at Company B” look like two similar sentences. Track 03 is about memory that lasts across sessions, updates when life changes, and does not invent an answer.

Watch this. Three conversations, four months. In February, work is Company A. In May, that job ends. In June, Company B.

Ask where I work now, and it says Company B. Open the evidence and Company A is still there, dated, marked as replaced. HydraDB did not overwrite the old fact. It linked the new one to the old one. That is how a graph remembers change. A search over chat logs cannot do that cleanly.

Memory has a 16 gigabyte staging box and a 32 gigabyte production box. The question asks about 64 gigabytes. That size was never said.

Related facts are sitting right there. A similarity search would answer from the nearest size. Backstory refuses. Guessing from a neighbour is the failure mode this track cares about. The refuse is a rule in the engine, not the model being polite.

Four conversations. First a plan for MongoDB. Then a switch to Postgres. Then a requirement: we need strong consistency for billing. Then a standard: we standardised on Postgres.

The requirement never names Postgres. The answer still uses it, because the graph kept the whole chain, not only the last sentence. That is original for this track: why, not only what.

HydraDB is not a cache in front of something else. We run the public open-source image, the graph-node process, locally in Docker and in production on Fly. Bolt on 7687, HTTP on 8443, admin on 9090. We did not use Hydra Cloud.

People, sessions, messages, facts, and entities are nodes. When a fact replaces another, that is an edge. When two facts cannot both be true, that is another edge. Answers are a walk from those nodes, not “find similar text.”

A small SQLite file only mints integer ids. It is not allowed to answer.

What we learned from the repo: Hydra’s OpenCypher is a real subset. No IS NULL. No undirected matches. Writes have to follow their UNWIND rules exactly. We learned that by hitting the live parser, not by assuming Neo4j. We also learned Hydra is built for object storage, not a long-lived local disk, so the deployed graph sits on Tigris, Fly’s S3 store.

If you swapped Hydra for a vector database, you would lose current versus history as a first-class thing. That is why the database is the product.

Backstory is live at backstory.fly.dev. Source is github.com/Datwebguy/Backstory. Thank you.

---

## Coverage (for you, not for the camera)

| What they asked | Where it lives |
|---|---|
| Who built it | 0:00 |
| The problem | 0:22 |
| What you built, by name and track | 0:08 |
| Demo working | 0:42–1:52 |
| HydraDB repo, tools, ports, OSS not Cloud | 1:52 |
| What you learned from their software | 2:15 |
| Why a graph, not a vector store | 2:32 |
| Live product + GitHub | 2:42 |

Do not say LongMemEval scores, 500 questions, or “we beat RAG.” Show the product. If a form field asks for a number later, use the validation doc, not this video.

---

## After the take

- Export 1080p, 16:9, under 3:00.
- Upload unlisted YouTube (or equivalent).
- Submit the form the same day: repo, https://backstory.fly.dev/, video.
- Deadline: **20 August 2026, 11:59 PM PT.**
