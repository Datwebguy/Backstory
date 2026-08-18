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

- No official LongMemEval number. `evaluate_qa.py gpt-4o` needs
  `OPENAI_API_KEY`. Unofficial contains-match is not a score.
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
