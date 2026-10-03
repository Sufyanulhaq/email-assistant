"""Settings read from environment variables. Everything has a default so the demo starts with none."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str | None = None
    model: str = "claude-haiku-4-5"
    inbox_cap: int = 200

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY") or None,
            model=os.environ.get("EMAIL_MODEL", cls.model),
            inbox_cap=int(os.environ.get("INBOX_CAP", cls.inbox_cap)),
        )
