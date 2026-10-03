from email import message_from_bytes, policy
from email.message import EmailMessage

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def client():
    c = TestClient(create_app(Settings(), mode="offline"))
    c.post("/api/samples")
    return c


def test_health_and_listing(client):
    assert client.get("/api/health").json() == {"ok": True, "mode": "offline", "emails": 9}
    rows = {r["id"]: r for r in client.get("/api/emails").json()}
    assert rows["e3"]["needs_human"] and rows["e3"]["status"] == "needs_human"
    assert rows["e2"]["status"] == "draft_ready" and rows["e8"]["status"] == "spam"


def test_loading_the_samples_twice_does_not_duplicate_them(client):
    client.post("/api/samples")
    assert len(client.get("/api/emails").json()) == 9


def test_detail_shows_the_analysis_flags_and_policy_behind_the_draft(client):
    d = client.get("/api/emails/e9").json()
    assert d["triage"]["order_numbers"] == ["NW-30555"] and d["triage"]["amount"] == 850
    assert d["review"]["needs_human"] and d["draft"]["policies"][0]["id"] == "refunds"
    assert client.get("/api/emails/e8").json()["draft"] is None


def test_a_flagged_email_cannot_be_approved_without_acknowledging_the_flags(client):
    assert client.post("/api/emails/e9/approve").status_code == 409
    assert client.post("/api/emails/e9/approve", json={"acknowledge_flags": False}).status_code == 409
    assert client.post("/api/emails/e9/approve", json={"acknowledge_flags": True}).json()["draft"]["approved"]


def test_an_unflagged_email_is_approved_directly(client):
    assert client.post("/api/emails/e2/approve").json()["status"] == "approved"


def test_the_download_needs_approval_and_is_a_valid_email(client):
    assert client.get("/api/emails/e2/draft.eml").status_code == 409
    client.post("/api/emails/e2/approve")
    r = client.get("/api/emails/e2/draft.eml")
    assert r.status_code == 200 and r.headers["content-type"].startswith("message/rfc822")
    assert "reply-e2.eml" in r.headers["content-disposition"]
    m = message_from_bytes(r.content, policy=policy.default)
    assert m["To"].addresses[0].addr_spec == "tom.becker@example.com"
    assert m["Subject"] == "Re: Where is my order?" and m["In-Reply-To"] == "<e2@inbox.local>"
    assert "Brightline Support" in m.get_content()


def test_editing_the_draft_requires_approving_again(client):
    client.post("/api/emails/e2/approve")
    d = client.put("/api/emails/e2/draft", json={"text": "Hi Tom, my own words."}).json()
    assert d["draft"]["text"] == "Hi Tom, my own words." and d["draft"]["edited"] and not d["draft"]["approved"]
    assert client.get("/api/emails/e2/draft.eml").status_code == 409


def test_regenerating_replaces_an_edited_draft(client):
    client.put("/api/emails/e2/draft", json={"text": "edited"})
    d = client.post("/api/emails/e2/regenerate").json()
    assert d["draft"]["edited"] is False and d["draft"]["text"].startswith("Hi Tom")


@pytest.mark.parametrize("body", [{"text": ""}, {"text": "x" * 3001}, {}])
def test_draft_edits_are_validated(client, body):
    assert client.put("/api/emails/e2/draft", json=body).status_code == 422


def test_whitespace_only_draft_is_rejected(client):
    assert client.put("/api/emails/e2/draft", json={"text": "   "}).status_code == 422


def test_spam_has_no_draft_to_edit_approve_or_download(client):
    assert client.put("/api/emails/e8/draft", json={"text": "x"}).status_code == 404
    assert client.post("/api/emails/e8/approve").status_code == 404
    assert client.get("/api/emails/e8/draft.eml").status_code == 409


def test_unknown_ids_are_404(client):
    assert client.get("/api/emails/nope").status_code == 404
    assert client.post("/api/emails/nope/approve").status_code == 404
    assert client.post("/api/emails/nope/regenerate").status_code == 404


def test_a_pasted_email_is_analysed(client):
    r = client.post("/api/emails", json={"from": "Sam Lee <sam@example.com>", "subject": "Cancel", "body": "Please cancel my Care plan."})
    assert r.status_code == 200 and r.json()["triage"]["category"] == "cancellation"
    assert len(client.get("/api/emails").json()) == 10


@pytest.mark.parametrize("payload", [
    {"from": "nobody", "subject": "s", "body": "text"},
    {"from": "a@b.co", "subject": "s", "body": "   "},
    {"from": "a@b.co", "subject": "s"},
    {"from": "a@b.co", "subject": "s", "body": "x" * 5001},
])
def test_bad_pasted_emails_are_refused(client, payload):
    assert client.post("/api/emails", json=payload).status_code in (400, 422)


def test_an_eml_upload_is_analysed(client):
    m = EmailMessage()
    m["From"], m["Subject"] = "Ana Ruiz <ana@example.com>", "Invoice please"
    m.set_content("Could you send me a copy of my invoice for order AB-12345?")
    r = client.post("/api/emails/upload", files={"file": ("mail.eml", bytes(m), "message/rfc822")})
    assert r.status_code == 200 and r.json()["triage"]["category"] == "billing"
    assert r.json()["triage"]["order_numbers"] == ["AB-12345"]


def test_a_bad_upload_is_refused(client):
    r = client.post("/api/emails/upload", files={"file": ("x.eml", b"\x00\x01nonsense", "message/rfc822")})
    assert r.status_code == 400


def test_a_full_inbox_is_a_clear_400():
    c = TestClient(create_app(Settings(inbox_cap=1), mode="offline"))
    ok = {"from": "a@b.co", "subject": "s", "body": "where is my order"}
    assert c.post("/api/emails", json=ok).status_code == 200
    r = c.post("/api/emails", json=ok)
    assert r.status_code == 400 and "full" in r.json()["detail"]


def test_the_page_is_served(client):
    page = client.get("/")
    assert page.status_code == 200 and "AI Email Assistant" in page.text
