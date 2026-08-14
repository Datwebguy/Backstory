"""Lexical embedding fallback.

A real embedding API can replace this later. The retrieval path still
requires HydraDB traversal after seeds are chosen.
"""

from __future__ import annotations

import re


def lexical_embed(text: str, dims: int = 64) -> list[float]:
    vec = [0.0] * dims
    for token in re.findall(r"[a-z0-9]+", (text or "").lower()):
        vec[hash(token) % dims] += 1.0
    return vec
