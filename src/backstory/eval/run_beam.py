"""Run Backstory against a slice of BEAM.

BEAM (https://github.com/mohammadtavakoli78/BEAM) probes ten long term
memory abilities over multi session conversations. Seven of them map
directly onto mechanisms this project implements (abstention,
contradiction resolution, knowledge update, multi session reasoning,
temporal reasoning, event ordering, preference following), which makes
it a closer fit to Backstory than LongMemEval's answer-recall framing.

Scoring honesty
---------------
This does NOT run BEAM's official `src/evaluation/compute_metrics.py`,
which additionally needs sentence-transformers and a LangChain model.
It scores each answer with an LLM against *BEAM's own published rubric*
for that question, and labels the result accordingly. Treat the number
as "Backstory judged against BEAM rubrics", not as an official BEAM
score. Per-question records are written out so the official scorer can
be run over them later.
"""

from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from pathlib import Path

from backstory.config import Settings
from backstory.engine.memory import MemoryEngine
from backstory.eval.beam_adapter import discover, load_conversation, load_questions
from backstory.hydra.client import HydraClient

JUDGE_PROMPT = """You are grading one answer from a memory system.

Question:
{question}

Reference answer:
{ideal}

Grading rubric (the answer should satisfy these):
{rubric}

Answer under test:
{hypothesis}

Reply with JSON only: {{"verdict": "pass" | "fail", "why": "<one short sentence>"}}
Judge only whether the answer satisfies the rubric. Wording may differ from
the reference. If the rubric says the information is unavailable and the
answer correctly declines to invent it, that is a pass.
"""


def judge(
    question: str,
    ideal: str,
    rubric: list[str],
    hypothesis: str,
    *,
    api_key: str,
    base_url: str,
    model: str,
) -> tuple[bool, str]:
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=base_url)
    rubric_text = "\n".join(f"- {item}" for item in rubric) or "- (none supplied)"
    completion = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[
            {"role": "system", "content": "You are a strict, fair grader. Reply with JSON only."},
            {
                "role": "user",
                "content": JUDGE_PROMPT.format(
                    question=question,
                    ideal=ideal or "(none supplied)",
                    rubric=rubric_text,
                    hypothesis=hypothesis,
                ),
            },
        ],
    )
    raw = (completion.choices[0].message.content or "").strip()
    start, end = raw.find("{"), raw.rfind("}")
    if start >= 0 and end > start:
        try:
            payload = json.loads(raw[start : end + 1])
            return str(payload.get("verdict", "")).lower() == "pass", str(payload.get("why", ""))
        except json.JSONDecodeError:
            pass
    return False, f"unparseable judge reply: {raw[:120]}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data/beam")
    parser.add_argument("--tier", default="100K")
    parser.add_argument("--ids", default="", help="comma separated ids; default all discovered")
    parser.add_argument("--out-dir", default="runs/beam")
    parser.add_argument("--limit-questions", type=int, default=0, help="0 = all")
    parser.add_argument("--skip-judge", action="store_true")
    args = parser.parse_args()

    settings = Settings()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    found = discover(Path(args.data), args.tier)
    if args.ids:
        wanted = {part.strip() for part in args.ids.split(",") if part.strip()}
        found = [item for item in found if item[0] in wanted]
    if not found:
        print(f"No conversations under {args.data}/{args.tier}. Run backstory.eval.beam_download first.")
        return 1

    engine = MemoryEngine(settings=settings, hydra=HydraClient(settings))
    if not engine.hydra.ready():
        print("HydraDB is not ready")
        return 2

    records: list[dict] = []
    try:
        for conv_id, chat_path, questions_path in found:
            sessions = load_conversation(chat_path)
            questions = load_questions(questions_path)
            if args.limit_questions:
                questions = questions[: args.limit_questions]
            user_key = f"beam:{args.tier}:{conv_id}"

            started = time.time()
            turns = sum(len(s["turns"]) for s in sessions)
            print(f"\nconv {conv_id}: ingesting {len(sessions)} sessions / {turns} turns", flush=True)
            for session in sessions:
                engine.ingest_session(
                    user_key=user_key,
                    session_key=f"{conv_id}-{session['session_key']}",
                    occurred_at=session["occurred_at"],
                    turns=session["turns"],
                    title=session["session_key"],
                )
            print(f"conv {conv_id}: ingested in {time.time() - started:.0f}s", flush=True)

            for item in questions:
                answer = engine.ask(
                    user_key=user_key,
                    question=item["question"],
                    question_date=sessions[-1]["occurred_at"] if sessions else "",
                )
                records.append(
                    {
                        "conversation_id": conv_id,
                        "tier": args.tier,
                        "ability": item["ability"],
                        "question_id": f"{conv_id}:{item['question_id']}",
                        "question": item["question"],
                        "ideal_response": item["ideal_response"],
                        "rubric": item["rubric"],
                        "difficulty": item["difficulty"],
                        "hypothesis": answer.text,
                        "action": answer.action,
                        "reason": answer.reason,
                    }
                )
                print(f"  [{item['ability']}] {answer.action}", flush=True)
    finally:
        engine.close()

    hyp_path = out_dir / f"beam_{args.tier}_hypotheses.jsonl"
    with hyp_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"\nwrote {hyp_path} ({len(records)} records)")

    if args.skip_judge or not settings.openai_api_key:
        print("judge skipped (no OPENAI_API_KEY or --skip-judge)")
        return 0

    print("\njudging against BEAM rubrics ...", flush=True)
    by_ability: dict[str, list[bool]] = defaultdict(list)
    for record in records:
        passed, why = judge(
            record["question"],
            record["ideal_response"],
            record["rubric"],
            record["hypothesis"],
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=settings.backstory_answer_model,
        )
        record["rubric_pass"] = passed
        record["rubric_why"] = why
        by_ability[record["ability"]].append(passed)
        print(f"  {'PASS' if passed else 'FAIL'} [{record['ability']}] {why[:70]}", flush=True)

    with hyp_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    total = sum(1 for r in records if r.get("rubric_pass"))
    summary = {
        "note": (
            "Backstory judged against BEAM's published rubrics with an LLM. "
            "This is NOT BEAM's official compute_metrics.py score."
        ),
        "tier": args.tier,
        "conversations": [item[0] for item in found],
        "questions": len(records),
        "rubric_pass": total,
        "by_ability": {
            ability: {"n": len(v), "pass": sum(1 for x in v if x)}
            for ability, v in sorted(by_ability.items())
        },
    }
    summary_path = out_dir / f"beam_{args.tier}_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("\n" + json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
