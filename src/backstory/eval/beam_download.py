"""Fetch a slice of the BEAM dataset.

BEAM ships its conversations inside the repository rather than as a
release artifact, so this pulls only the files the evaluation needs
(the conversation and its probing questions) for the requested
conversation ids, instead of cloning every size tier.

Source: https://github.com/mohammadtavakoli78/BEAM
"""

from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path

RAW = "https://raw.githubusercontent.com/mohammadtavakoli78/BEAM/main/chats"


def fetch(url: str, timeout: int = 120) -> bytes:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return response.read()


def download_conversation(tier: str, conv_id: str, out_dir: Path) -> bool:
    target = out_dir / tier / conv_id
    target.mkdir(parents=True, exist_ok=True)
    wanted = {
        "chat.json": f"{RAW}/{tier}/{conv_id}/chat.json",
        "probing_questions.json": f"{RAW}/{tier}/{conv_id}/probing_questions/probing_questions.json",
    }
    for name, url in wanted.items():
        path = target / name
        if path.exists() and path.stat().st_size > 0:
            print(f"  have {tier}/{conv_id}/{name}")
            continue
        try:
            payload = fetch(url)
        except Exception as exc:  # noqa: BLE001 - report and skip, do not abort the slice
            print(f"  MISS {tier}/{conv_id}/{name}: {exc}")
            return False
        path.write_bytes(payload)
        print(f"  got  {tier}/{conv_id}/{name} ({len(payload):,} bytes)")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tier", default="100K", help="100K, 500K, 1M, or 10M")
    parser.add_argument("--ids", default="1,2,3", help="comma separated conversation ids")
    parser.add_argument("--out", default="data/beam")
    args = parser.parse_args()

    out_dir = Path(args.out)
    ids = [part.strip() for part in args.ids.split(",") if part.strip()]
    ok = 0
    for conv_id in ids:
        print(f"{args.tier}/{conv_id}:")
        if download_conversation(args.tier, conv_id, out_dir):
            ok += 1
    print(f"\n{ok}/{len(ids)} conversations available under {out_dir / args.tier}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
