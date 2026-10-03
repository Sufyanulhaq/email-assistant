"""The company's written policies. Drafts may only state what is in here."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Policy:
    id: str
    title: str
    text: str


def load(path: Path) -> dict[str, Policy]:
    return {p["id"]: Policy(p["id"], p["title"], p["text"]) for p in json.loads(path.read_text())}
