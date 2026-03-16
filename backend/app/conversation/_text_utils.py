from __future__ import annotations


def normalize_spaces(text: str) -> str:
    return " ".join(text.strip().split())
