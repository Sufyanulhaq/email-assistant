import pytest

from app.pipeline import process
from app.store import Inbox, InboxFull
from tests.conftest import make_email


def test_status_follows_the_review(offline, samples):
    assert process(samples["e2"], offline).status == "draft_ready"
    assert process(samples["e3"], offline).status == "needs_human"
    assert process(samples["e8"], offline).status == "spam"


def test_approval_makes_the_status_approved(offline, samples):
    record = process(samples["e2"], offline)
    record.approved = True
    assert record.status == "approved"


def test_editing_a_draft_withdraws_the_approval(offline, samples):
    box = Inbox()
    box.put(process(samples["e2"], offline))
    box.approve("e2")
    assert box.get("e2").approved
    box.edit("e2", "A new reply")
    r = box.get("e2")
    assert r.draft.text == "A new reply" and r.edited and not r.approved and r.status == "draft_ready"


def test_nothing_to_edit_or_approve_on_spam_or_unknown_ids(offline, samples):
    box = Inbox()
    box.put(process(samples["e8"], offline))
    assert box.edit("e8", "x") is None and box.approve("e8") is None and box.edit("nope", "x") is None


def test_inbox_is_newest_first_and_capped(offline):
    box = Inbox(cap=2)
    box.put(process(make_email("where is my order", email_id="a"), offline))
    box.put(process(make_email("cancel please", email_id="b"), offline))
    with pytest.raises(InboxFull):
        box.put(process(make_email("invoice please", email_id="c"), offline))
    box.put(process(make_email("replaced", email_id="a"), offline))  # same id replaces, so it is allowed
    assert [r.email.id for r in box.all()] == ["b", "a"]  # same date, so newest first falls back to the id
