"""Select a stratified LongMemEval subset. Official types from the README."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


WANTED = [
    "knowledge-update",
    "temporal-reasoning",
    "multi-session",
    "single-session-user",
    "single-session-preference",
    "abstention",
]


def load_dataset(path: Path) -> list[dict]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"Expected a JSON list in {path}")
    return raw


def item_type(item: dict) -> str:
    if str(item.get("question_id", "")).endswith("_abs"):
        return "abstention"
    return str(item.get("question_type") or "unknown")


def slice_items(items: list[dict], per_type: int) -> list[dict]:
    buckets: dict[str, list[dict]] = {name: [] for name in WANTED}
    for item in items:
        kind = item_type(item)
        if kind in buckets and len(buckets[kind]) < per_type:
            buckets[kind].append(item)
    out: list[dict] = []
    for name in WANTED:
        out.extend(buckets[name])
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--per-type", type=int, default=2)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    items = slice_items(load_dataset(Path(args.dataset)), args.per_type)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", out, "n=", len(items))
    for item in items:
        print(item_type(item), item["question_id"])


if __name__ == "__main__":
    main()
