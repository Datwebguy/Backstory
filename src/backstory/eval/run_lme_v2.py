"""Run the LongMemEval-V2 adapter through Backstory.

This is not the official LME-V2 harness. It writes
`{question_id, hypothesis}` jsonl from flattened trajectory text so
the same engine can be inspected. Do not report the unofficial
contains-match as an LME-V2 score.

Download first:
  huggingface datasets xiaowu0162/longmemeval-v2 → data/lme-v2/
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from backstory.config import Settings
from backstory.engine.memory import MemoryEngine
from backstory.eval.lme_v2_adapter import (
    load_haystack,
    load_questions,
    load_trajectories,
    question_sessions,
    to_lme_like,
)
from backstory.eval.run_official import unofficial_contains, warn_if_local_store, write_trace
from backstory.hydra.client import HydraClient


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", default="data/lme-v2")
    parser.add_argument("--tier", default="small", choices=("small", "medium"))
    parser.add_argument("--limit", type=int, default=2)
    parser.add_argument("--out-dir", default="runs/lme-v2")
    args = parser.parse_args()

    warn_if_local_store("lme-v2")
    root = Path(args.data_root)
    try:
        questions = load_questions(root)
        trajectories = load_trajectories(root)
    except FileNotFoundError as exc:
        print(exc)
        print("Adapter is wired; the public LME-V2 files are not in this checkout.")
        return 0

    haystack = load_haystack(root, args.tier)
    if args.limit:
        questions = questions[: args.limit]

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    settings = Settings(backstory_data_dir=out_dir / "sidecar")
    engine = MemoryEngine(settings=settings, hydra=HydraClient(settings))
    if not engine.hydra.ready():
        print("HydraDB is not ready")
        return 2

    hyp_path = out_dir / "hypotheses.jsonl"
    rows = []
    try:
        with hyp_path.open("w", encoding="utf-8") as handle:
            for raw in questions:
                item = to_lme_like(raw)
                qid = item["question_id"]
                print("INGEST", qid, item["question_type"], flush=True)
                user_key = f"lmev2:{qid}"
                for session in question_sessions(raw, trajectories, haystack):
                    engine.ingest_session(
                        user_key=user_key,
                        session_key=session["session_key"],
                        occurred_at=session["occurred_at"],
                        turns=session["turns"],
                        title=session.get("title") or "",
                    )
                answer = engine.ask(user_key=user_key, question=item["question"])
                rec = {"question_id": qid, "hypothesis": answer.text}
                handle.write(json.dumps(rec, ensure_ascii=False) + "\n")
                write_trace(out_dir / "traces" / f"{qid}.json", item, answer, [])
                hit = unofficial_contains(str(item.get("answer") or ""), answer.text)
                rows.append({**rec, "type": item["question_type"], "action": answer.action, "unofficial_contains": hit})
                print("ASK", qid, answer.action, "contains", hit, flush=True)
    finally:
        engine.close()

    summary = {
        "n": len(rows),
        "unofficial_contains": sum(1 for r in rows if r["unofficial_contains"]),
        "official_lme_v2": False,
        "note": (
            "Adapter only. Official LME-V2 scoring is the LongMemEval-V2 "
            "harness, not this file. unofficial_contains is diagnostic."
        ),
    }
    (out_dir / "summary_unofficial.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
