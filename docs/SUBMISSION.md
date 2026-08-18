# Hack Hydra submission pack

Deadline is hard. An agent cannot record the 3-minute video or submit
the Google Form. A person has to do both.

## Required pieces

| Piece | Status in this repo | What you do |
|---|---|---|
| Public GitHub | https://github.com/Datwebguy/Backstory | Confirm `master` is pushed |
| Live demo | https://backstory.fly.dev/ | Sign in, run the four scenario cards |
| ≤3 minute video | Script only: [DEMO_SCRIPT.md](DEMO_SCRIPT.md) | Record against the live demo |
| Official form | Not submitted from here | Paste repo + video + demo URLs |

## What not to claim on the form or in the video

- Official number you can back up: **9/12 (0.75)** on the 12-question
  **oracle slice**, judge `evaluate_qa.py gpt-4o` (`gpt-4o-2024-08-06`),
  abstention **2/2**. Artifact:
  `runs/lme/strat12_hybrid/hypotheses.jsonl.eval-results-gpt-4o`.
- That is **not** a LongMemEval-S 500 / 115k score. Do not write that.
- Do not say you beat RAG as a leaderboard result. The 5K update
  (`25:50` vs stale `27:12`) is a single qualitative contrast.
- LME-V2 adapter is not an official LME-V2 run.
- BEAM runner is judged against published rubrics, not
  `compute_metrics.py`.

## Suggested form answers

- Track: 03 Memory and Context Retrieval
- Hydra used how: HydraDB OSS `graph-node` is the source of truth for
  facts, entities, SUPERSEDES, CONTRADICTS. SQLite sidecar never answers.
- Hydra Cloud: not used
