"""The web API. Start it with: uvicorn app.main:create_app --factory"""
from __future__ import annotations

from email.message import EmailMessage
from email.utils import formatdate
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import inbox as mail
from . import policies as policy_store
from .config import Settings
from .draft_rules import OfflineAnalyzer
from .pipeline import Record, process
from .store import Inbox, InboxFull

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"
DATA = ROOT / "data"
SUPPORT_ADDRESS = "Brightline Support <support@brightlinedesks.example>"


class NewEmail(BaseModel):
    sender: str = Field(alias="from", min_length=3, max_length=200)
    subject: str = Field(max_length=mail.MAX_SUBJECT)
    body: str = Field(min_length=1, max_length=mail.MAX_BODY)

    model_config = {"populate_by_name": True}


class DraftEdit(BaseModel):
    text: str = Field(min_length=1, max_length=3000)


class Approval(BaseModel):
    acknowledge_flags: bool = False


def build_analyzer(settings: Settings, policies):
    """Claude when an API key is set, templates over the policies otherwise."""
    offline = OfflineAnalyzer(policies)
    if not settings.anthropic_api_key:
        return offline, "offline"
    import anthropic

    from .analyze_llm import ClaudeAnalyzer

    return ClaudeAnalyzer(anthropic.Anthropic(api_key=settings.anthropic_api_key), policies, offline, settings.model), "claude"


def row(r: Record) -> dict:
    return {
        "id": r.email.id, "from": r.email.sender_name, "subject": r.email.subject, "date": r.email.date,
        "category": r.triage.category, "urgency": r.triage.urgency, "status": r.status, "needs_human": r.review.needs_human,
    }


def detail(r: Record, policies) -> dict:
    return {
        **row(r),
        "email": {"from": r.email.sender_name, "address": r.email.sender_email, "body": r.email.body},
        "triage": {"category": r.triage.category, "urgency": r.triage.urgency, "sentiment": r.triage.sentiment,
                   "summary": r.triage.summary, "order_numbers": r.triage.order_numbers, "amount": r.triage.amount},
        "review": {"needs_human": r.review.needs_human, "reasons": r.review.reasons},
        "draft": None if r.draft is None else {
            "subject": r.draft.subject, "text": r.draft.text, "edited": r.edited, "approved": r.approved,
            "policies": [{"id": i, "title": policies[i].title, "text": policies[i].text} for i in r.draft.policy_ids if i in policies],
        },
    }


def create_app(settings: Settings | None = None, analyzer=None, mode: str | None = None, policies_path: Path = DATA / "policies.json", samples_path: Path = DATA / "sample_emails.json") -> FastAPI:
    settings = settings or Settings.from_env()
    policies = policy_store.load(policies_path)
    if analyzer is None:
        analyzer, detected = build_analyzer(settings, policies)
        mode = mode or detected
    mode = mode or "custom"
    box = Inbox(settings.inbox_cap)

    app = FastAPI(title="AI Email Assistant")

    def add(email: mail.Email) -> Record:
        record = process(email, analyzer)
        try:
            box.put(record)
        except InboxFull as exc:
            raise HTTPException(400, str(exc)) from exc
        return record

    def find(email_id: str) -> Record:
        record = box.get(email_id)
        if record is None:
            raise HTTPException(404, "no such email")
        return record

    @app.get("/api/health")
    def health():
        return {"ok": True, "mode": mode, "emails": len(box.all())}

    @app.get("/api/emails")
    def emails():
        return [row(r) for r in box.all()]

    @app.get("/api/emails/{email_id}")
    def one(email_id: str):
        return detail(find(email_id), policies)

    @app.post("/api/emails")
    def new(body: NewEmail):
        try:
            email = mail.build(body.sender, body.subject, body.body, formatdate(usegmt=True))
        except mail.EmailError as exc:
            raise HTTPException(400, str(exc)) from exc
        return detail(add(email), policies)

    @app.post("/api/emails/upload")
    def upload(file: UploadFile):
        try:
            email = mail.from_eml(file.file.read(mail.MAX_RAW + 1))
        except mail.EmailError as exc:
            raise HTTPException(400, str(exc)) from exc
        return detail(add(email), policies)

    @app.post("/api/samples")
    def samples():
        return [row(add(e)) for e in mail.load_samples(samples_path)]

    @app.post("/api/emails/{email_id}/regenerate")
    def regenerate(email_id: str):
        return detail(add(find(email_id).email), policies)

    @app.put("/api/emails/{email_id}/draft")
    def edit(email_id: str, body: DraftEdit):
        text = body.text.strip()
        if not text:
            raise HTTPException(422, "the draft is empty")
        record = box.edit(email_id, text)
        if record is None:
            raise HTTPException(404, "no draft for this email")
        return detail(record, policies)

    @app.post("/api/emails/{email_id}/approve")
    def approve(email_id: str, body: Approval | None = None):
        record = find(email_id)
        if record.draft is None:
            raise HTTPException(404, "no draft for this email")
        if record.review.needs_human and not (body and body.acknowledge_flags):
            raise HTTPException(409, "This email was flagged for a person. Confirm that you have read the flags to approve it.")
        box.approve(email_id)
        return detail(record, policies)

    @app.get("/api/emails/{email_id}/draft.eml")
    def export(email_id: str):
        record = find(email_id)
        if record.draft is None or not record.approved:
            raise HTTPException(409, "Approve the draft before downloading it.")
        message = EmailMessage()
        message["From"] = SUPPORT_ADDRESS
        message["To"] = f"{record.email.sender_name} <{record.email.sender_email}>"
        message["Subject"] = record.draft.subject
        message["Date"] = formatdate(usegmt=True)
        message["In-Reply-To"] = f"<{record.email.id}@inbox.local>"
        message.set_content(record.draft.text)
        return Response(
            bytes(message), media_type="message/rfc822",
            headers={"Content-Disposition": f'attachment; filename="reply-{record.email.id}.eml"'},
        )

    @app.get("/")
    def index():
        return FileResponse(STATIC / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    return app
