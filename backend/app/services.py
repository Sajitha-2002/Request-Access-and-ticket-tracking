"""
Core business logic helpers for request management:
  - Auto-ID generation (REQ-YYYY-XXXX)
  - Target date calculation
  - Status transition validation
  - Email notifications
"""
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from .models import (
    Request, RequestSequence, RequestType, RequestStatus,
    Priority, Comment, CommentActionType, User
)
import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from .config import settings

# Priority offset in days
PRIORITY_OFFSETS = {
    Priority.low: 5,
    Priority.medium: 3,
    Priority.high: 1,
}

# Allowed transitions: current_status -> list of valid next statuses
VALID_TRANSITIONS: dict[RequestStatus, list[RequestStatus]] = {
    RequestStatus.submitted: [RequestStatus.under_review, RequestStatus.rejected],
    RequestStatus.under_review: [RequestStatus.approved, RequestStatus.rejected, RequestStatus.fulfilled],
    RequestStatus.approved: [RequestStatus.fulfilled, RequestStatus.rejected],
    RequestStatus.rejected: [RequestStatus.submitted],  # re-submit
    RequestStatus.fulfilled: [RequestStatus.closed],
    RequestStatus.closed: [],
}


def generate_request_number(db: Session, year: int | None = None) -> str:
    if year is None:
        year = datetime.utcnow().year
    seq = db.query(RequestSequence).filter(RequestSequence.year == year).first()
    if not seq:
        seq = RequestSequence(year=year, last_number=0)
        db.add(seq)
    seq.last_number += 1
    db.flush()
    return f"REQ-{year}-{seq.last_number:04d}"


def calculate_target_date(
    request_type: RequestType, priority: Priority, created_date: date | None = None
) -> date:
    base = created_date or datetime.utcnow().date()
    total_days = request_type.turnaround_days + PRIORITY_OFFSETS.get(priority, 3)
    return base + timedelta(days=total_days)


def validate_transition(
    current: RequestStatus,
    new: RequestStatus,
    requires_approval: bool,
) -> None:
    allowed = VALID_TRANSITIONS.get(current, [])
    if new not in allowed:
        raise ValueError(
            f"Cannot transition from '{current.value}' to '{new.value}'."
        )
    # Extra rule: if requires_approval, can't go Under Review -> Fulfilled
    if requires_approval and current == RequestStatus.under_review and new == RequestStatus.fulfilled:
        raise ValueError(
            "This request type requires approval before fulfilment."
        )


def send_email_notification(
    to_emails: list[str],
    subject: str,
    body_html: str,
) -> None:
    """Fire-and-forget email using SMTP. Silently fails if not configured."""
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        return
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>"
        msg["To"] = ", ".join(to_emails)
        msg.attach(MIMEText(body_html, "html"))
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.EMAIL_FROM, to_emails, msg.as_string())
    except Exception:
        pass  # email is non-blocking; log in production


def build_submission_email(request: Request, requester: User) -> str:
    return f"""
    <html><body style="font-family:Arial,sans-serif;color:#1a1a2e">
    <div style="max-width:600px;margin:auto;padding:24px;border:1px solid #e0e0e0;border-radius:8px">
      <h2 style="color:#6c63ff">Nila — Request Submitted</h2>
      <p>Dear <strong>{requester.name}</strong>,</p>
      <p>Your request has been submitted successfully. Here are the details:</p>
      <table style="width:100%;border-collapse:collapse">
        <tr><td style="padding:8px;background:#f5f5f5"><strong>Request ID</strong></td>
            <td style="padding:8px">{request.request_number}</td></tr>
        <tr><td style="padding:8px;background:#f5f5f5"><strong>Type</strong></td>
            <td style="padding:8px">{request.request_type.name}</td></tr>
        <tr><td style="padding:8px;background:#f5f5f5"><strong>Description</strong></td>
            <td style="padding:8px">{request.short_description}</td></tr>
        <tr><td style="padding:8px;background:#f5f5f5"><strong>Priority</strong></td>
            <td style="padding:8px">{request.priority.value}</td></tr>
        <tr><td style="padding:8px;background:#f5f5f5"><strong>Status</strong></td>
            <td style="padding:8px">{request.status.value}</td></tr>
        <tr><td style="padding:8px;background:#f5f5f5"><strong>Target Resolution</strong></td>
            <td style="padding:8px">{request.target_resolution_date}</td></tr>
      </table>
      <p style="margin-top:16px;color:#888">This is an automated message from the Nila Access System.</p>
    </div></body></html>
    """
