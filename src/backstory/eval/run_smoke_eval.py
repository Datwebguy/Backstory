"""Smallest official-format evaluation we can run without the 115k haystacks.

Writes a LongMemEval-shaped JSON file from the four demos, asks Backstory,
and scores with exact/contains checks. If OPENAI_API_KEY is set, also invokes
the official evaluate_qa.py judge.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from backstory.config import Settings
from backstory.demo.load_demo import ask_all, load
from backstory.demo.scenarios import QUESTIONS, USER, all_sessions
from backstory.engine.memory import MemoryEngine
from backstory.hydra.client import HydraClient


def write_official_fixture(path: Path) -> None:
    instances = []
    sessions = all_sessions()
    for q in QUESTIONS:
        instances.append(
            {
                "question_id": q["id"] + ("_abs" if q["expect_action"] == "abstain" else ""),
                "question_type": {
                    "knowledge-update": "knowledge-update",
                    "multi-session": "multi-session",
                    "abstention": "single-session-user",
                    "decision-history": "multi-session",
                }[q["capability"]],
                "question": q["question"],
                "answer": q["expect_contains"][0],
                "question_date": q["question_date"],
                "haystack_session_ids": [s["session_key"] for s in sessions],
                "haystack_dates": [s["occurred_at"] for s in sessions],
                "haystack_sessions": [s["turns"] for s in sessions],
                "answer_session_ids": [],
            }
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(instances, indent=2), encoding="utf-8")


def main() -> int:
    data_dir = Path("runs/smoke/sidecar")
    if data_dir.exists():
        for child in data_dir.glob("*"):
            child.unlink()
    settings = Settings(backstory_data_dir=data_dir)
    engine = MemoryEngine(settings=settings, hydra=HydraClient(settings))
    try:
        if not engine.hydra.ready():
            print("HydraDB not ready")
            return 1
        load(engine, USER)
        rows = ask_all(engine, USER)
    finally:
        engine.close()

    out_dir = Path("runs/smoke")
    out_dir.mkdir(parents=True, exist_ok=True)
    fixture = Path("data/lme/backstory_smoke.json")
    write_official_fixture(fixture)
    hyp = out_dir / "hypotheses.jsonl"
    with hyp.open("w", encoding="utf-8") as handle:
        for row in rows:
            qid = row["id"] + ("_abs" if row["action"] == "abstain" else "")
            handle.write(json.dumps({"question_id": qid, "hypothesis": row["hypothesis"]}) + "\n")

    ok = 0
    for row, spec in zip(rows, QUESTIONS, strict=False):
        hit = all(token.lower() in row["hypothesis"].lower() for token in spec["expect_contains"])
        action_ok = row["action"] == spec["expect_action"] or (
            spec["expect_action"] == "abstain" and "enough information" in row["hypothesis"].lower()
        )
        passed = hit and action_ok
        ok += int(passed)
        print(("PASS" if passed else "FAIL"), spec["id"], row["action"], row["hypothesis"][:120])
    print(f"smoke {ok}/{len(QUESTIONS)}")

    if os.getenv("OPENAI_API_KEY"):
        cmd = [
            sys.executable,
            "vendor/longmemeval/evaluate_qa.py",
            "gpt-4o",
            str(hyp),
            str(fixture),
        ]
        print("Running official judge:", " ".join(cmd))
        return subprocess.call(cmd)
    print("OPENAI_API_KEY not set; skipped official evaluate_qa.py")
    return 0 if ok == len(QUESTIONS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
