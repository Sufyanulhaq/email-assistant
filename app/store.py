"""The inbox, kept in memory. Fine for a demo, and the README says what a real one would need."""
from __future__ import annotations

import threading

from .models import Draft
from .pipeline import Record


class InboxFull(Exception):
    pass


class Inbox:
    def __init__(self, cap: int = 200) -> None:
        self.cap = cap
        self._records: dict[str, Record] = {}
        self._lock = threading.Lock()

    def put(self, record: Record) -> None:
        with self._lock:
            if record.email.id not in self._records and len(self._records) >= self.cap:
                raise InboxFull(f"The inbox is full ({self.cap} emails).")
            self._records[record.email.id] = record

    def get(self, email_id: str) -> Record | None:
        with self._lock:
            return self._records.get(email_id)

    def all(self) -> list[Record]:
        with self._lock:
            return sorted(self._records.values(), key=lambda r: (r.email.date, r.email.id), reverse=True)

    def edit(self, email_id: str, text: str) -> Record | None:
        with self._lock:
            record = self._records.get(email_id)
            if record is None or record.draft is None:
                return None
            record.draft = Draft(record.draft.subject, text, record.draft.policy_ids)
            record.edited, record.approved = True, False  # an edited draft has to be approved again
            return record

    def approve(self, email_id: str) -> Record | None:
        with self._lock:
            record = self._records.get(email_id)
            if record is None or record.draft is None:
                return None
            record.approved = True
            return record
