from pathlib import Path

import pytest

from app import inbox, policies
from app.draft_rules import OfflineAnalyzer

DATA = Path(__file__).resolve().parent.parent / "data"


@pytest.fixture(scope="session")
def pols():
    return policies.load(DATA / "policies.json")


@pytest.fixture(scope="session")
def samples():
    return {e.id: e for e in inbox.load_samples(DATA / "sample_emails.json")}


@pytest.fixture
def offline(pols):
    return OfflineAnalyzer(pols)


def make_email(body, subject="Question", sender="Sam Lee <sam@example.com>", email_id="t1"):
    return inbox.build(sender, subject, body, "2026-10-01T09:00:00+00:00", email_id)
