# Backstory — demo video script

**Hard limit:** 3:00. Land at **2:40**. Do not go over.

Cover only what Hack Hydra asked for:

1. The problem
2. What you built
3. The product working
4. How you used HydraDB, and why it matters

Do not mention benchmarks, scores, baselines, RAG, mem0, BEAM, LongMemEval, tests, or bugs. Do not type into the chat on camera. Do not use your name. If a card does not show the answer you expect, skip the line and go to the next card. Do not explain a miss.

---

## Before record

1. Sign in at https://backstory.fly.dev/app. Do not film the Google page.
2. Click **+ new chat**.
3. Browser about 1440×900, zoom 110%.
4. One extra tab: https://github.com/Datwebguy/Backstory
5. Pick light or dark and leave it.

---

## Shot list

### 0:00–0:18 — Problem and name

**Screen:** https://backstory.fly.dev/

**Say:**

> Assistants forget. A conversation is stored as text, then cut when the window fills.

> This is Backstory, a memory layer for conversational agents, built for Track 03. What you say is stored as versioned facts in HydraDB, so it can answer later, show what changed, and say when it does not know.

---

### 0:18–0:52 — A fact that changed

**Screen:** `/app`. Click **Changed plans**. Wait for the answer. Open **based on N memories** if it appears.

**Say:**

> Work was Company A, then a leave, then Company B, across three conversations.

> It answers with the current employer. The earlier job is still in the graph, marked as replaced, with a date. That replacement is a SUPERSEDES edge in HydraDB.

If the drawer does not open, do not comment. Continue.

---

### 0:52–1:16 — When it does not know

**Screen:** **+ new chat**, then **Knows when it does not know**. Wait for the reply.

**Say:**

> Memory has two instance sizes. The question asks about a third size that was never stated.

> It does not guess from the nearby facts. It says it does not have enough information.

If it answers with a number, do not narrate. Go to the next card.

---

### 1:16–1:44 — A decision across sessions

**Screen:** **+ new chat**, then **Decision history**.

**Say:**

> Four conversations: a first database, a change of plan, a consistency requirement, then a standard.

> The requirement never names the database. The answer still uses it, because the graph keeps the history of the decision, not only the last sentence.

Do not run **Remembered across conversations**.

---

### 1:44–2:28 — How HydraDB is used

**Screen:** the GitHub repository. Stay on the README or `docs/ARCHITECTURE.md`. Do not scroll hunting for files.

**Say:**

> HydraDB graph-node is the source of truth. Users, sessions, facts, and entities are nodes. SUPERSEDES and CONTRADICTS are edges.

> Retrieval is a walk from those entities. A small sidecar only allocates ids. It does not answer questions.

> We run the public HydraDB image. We use the Cypher that the open-source parser accepts. We do not use Hydra Cloud.

> Current versus historical is stored as an edge, so both can exist without one deleting the other.

---

### 2:28–2:40 — Close

**Screen:** https://backstory.fly.dev/

**Say:**

> Backstory is live at backstory.fly.dev. The code is on GitHub.

Stop. Hold two seconds. End.

---

## Teleprompter

Assistants forget. A conversation is stored as text, then cut when the window fills.

This is Backstory, a memory layer for conversational agents, built for Track 03. What you say is stored as versioned facts in HydraDB, so it can answer later, show what changed, and say when it does not know.

Work was Company A, then a leave, then Company B, across three conversations.

It answers with the current employer. The earlier job is still in the graph, marked as replaced, with a date. That replacement is a SUPERSEDES edge in HydraDB.

Memory has two instance sizes. The question asks about a third size that was never stated.

It does not guess from the nearby facts. It says it does not have enough information.

Four conversations: a first database, a change of plan, a consistency requirement, then a standard.

The requirement never names the database. The answer still uses it, because the graph keeps the history of the decision, not only the last sentence.

HydraDB graph-node is the source of truth. Users, sessions, facts, and entities are nodes. SUPERSEDES and CONTRADICTS are edges.

Retrieval is a walk from those entities. A small sidecar only allocates ids. It does not answer questions.

We run the public HydraDB image. We use the Cypher that the open-source parser accepts. We do not use Hydra Cloud.

Current versus historical is stored as an edge, so both can exist without one deleting the other.

Backstory is live at backstory.fly.dev. The code is on GitHub.

---

## After the take

- Export 1080p, 16:9, under 3:00.
- Upload unlisted.
- Submit the form: repo, https://backstory.fly.dev/, video.
- Deadline: 20 August 2026, 11:59 PM PT.

On the form, describe the product and the Hydra graph. Do not paste benchmark numbers unless you are looking at the validation doc and quoting it in full, including that it is a 12-question oracle slice and not LongMemEval-S.
