"""Map LongMemEval-V2 agent trajectories onto Backstory sessions.

Honesty
-------
This is a first-class adapter, not a completed official LME-V2 evaluation.

Official LME-V2 scores come from the LongMemEval-V2 harness
(https://github.com/xiaowu0162/LongMemEval-V2) over web and enterprise
agent trajectories: accessibility trees, actions, and screenshots, with
haystacks of 100–500 trajectories. Backstory is a conversational memory
layer. This adapter flattens each trajectory state's thought / action /
URL text into dated turns so the same ingest → graph → ask → abstain
path can be probed. Screenshots are ignored. Numbers produced here are
not LME-V2 leaderboard scores and must not be reported as such.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def load_questions(root: Path) -> list[dict[str, Any]]:
    path = root / "questions.jsonl"
    if not path.exists():
        raise FileNotFoundError(
            f"LME-V2 questions.jsonl not found at {path}. "
            "Download the public set from Hugging Face "
            "(xiaowu0162/longmemeval-v2) first."
        )
    return load_jsonl(path)


def load_trajectories(root: Path) -> dict[str, dict[str, Any]]:
    path = root / "trajectories.jsonl"
    if not path.exists():
        raise FileNotFoundError(f"LME-V2 trajectories.jsonl not found at {path}")
    return {row["id"]: row for row in load_jsonl(path) if row.get("id")}


def load_haystack(root: Path, tier: str) -> dict[str, list[str]]:
    name = "lme_v2_small.json" if tier == "small" else "lme_v2_medium.json"
    path = root / "haystacks" / name
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a question_id → trajectory_ids map in {path}")
    return {str(k): list(v) for k, v in payload.items()}


def states_to_turns(trajectory: dict[str, Any]) -> list[dict[str, str]]:
    """Flatten one agent trajectory into Backstory turns.

    Thoughts become assistant turns; URL + action + a clipped
    accessibility tree become user turns. Images are dropped on purpose.
    """
    turns: list[dict[str, str]] = []
    goal = (trajectory.get("goal") or "").strip()
    if goal:
        turns.append({"role": "user", "content": f"Goal: {goal}"})
    for state in trajectory.get("states") or []:
        thought = (state.get("thought") or "").strip()
        if thought:
            turns.append({"role": "assistant", "content": thought[:700]})
        bits = []
        url = (state.get("url") or "").strip()
        action = state.get("action")
        tree = (state.get("accessibility_tree") or "").strip()
        if url:
            bits.append(f"url: {url}")
        if action:
            bits.append(f"action: {action}")
        if tree:
            bits.append(tree[:400])
        if bits:
            turns.append({"role": "user", "content": "\n".join(bits)})
    return turns


def question_sessions(
    question: dict[str, Any],
    trajectories: dict[str, dict[str, Any]],
    haystack: dict[str, list[str]],
) -> list[dict[str, Any]]:
    qid = str(question.get("id") or "")
    traj_ids = haystack.get(qid) or []
    if not traj_ids and question.get("trajectory_id"):
        traj_ids = [str(question["trajectory_id"])]
    sessions = []
    for index, tid in enumerate(traj_ids):
        traj = trajectories.get(tid)
        if not traj:
            continue
        turns = states_to_turns(traj)
        if not turns:
            continue
        sessions.append(
            {
                "session_key": tid,
                "occurred_at": f"2024-01-{min(index + 1, 28):02d}T00:00:00",
                "turns": turns,
                "title": (traj.get("goal") or tid)[:80],
            }
        )
    return sessions


def to_lme_like(question: dict[str, Any]) -> dict[str, Any]:
    """Official-shaped record so the rest of the eval stack can consume it."""
    return {
        "question_id": question.get("id") or "",
        "question_type": question.get("question_type") or "unknown",
        "question": question.get("question") or "",
        "answer": question.get("answer") or "",
        "domain": question.get("domain") or "",
        "eval_function": question.get("eval_function") or "",
        "note": "lme-v2-adapter; not official LongMemEval-V2 scoring",
    }
