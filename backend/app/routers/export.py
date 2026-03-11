"""
Export router: PDF summary and CSV/Excel register export.
"""
import io
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Request, RequestStatus, Priority, User, UserRole
from ..auth import get_current_user, require_approver_or_admin
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import pandas as pd

router = APIRouter(prefix="/api/export", tags=["Export"])


# ─── PDF Summary ───────────────────────────────────────────────────────────────

@router.get("/requests/{req_id}/pdf")
def export_pdf(
    req_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    req = db.query(Request).filter(Request.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if current_user.role == UserRole.employee and req.requester_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=20 * mm, leftMargin=20 * mm,
        topMargin=20 * mm, bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "NilaTitle", parent=styles["Title"],
        textColor=colors.HexColor("#6c63ff"),
        fontSize=22, spaceAfter=6,
    )
    header_style = ParagraphStyle(
        "NilaHeader", parent=styles["Heading2"],
        textColor=colors.HexColor("#1a1a2e"),
        fontSize=14, spaceAfter=4,
    )
    body_style = styles["Normal"]
    label_style = ParagraphStyle(
        "Label", parent=styles["Normal"],
        textColor=colors.HexColor("#666666"), fontSize=9,
    )

    story = []

    # Header
    story.append(Paragraph("NILA ACCESS SYSTEM", title_style))
    story.append(Paragraph("Request Summary", header_style))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#6c63ff")))
    story.append(Spacer(1, 6 * mm))

    # Core details table
    priority_colors = {
        "High": "#ef4444", "Medium": "#f59e0b", "Low": "#22c55e"
    }
    status_colors = {
        "Submitted": "#6366f1", "Under Review": "#3b82f6",
        "Approved": "#22c55e", "Rejected": "#ef4444",
        "Fulfilled": "#10b981", "Closed": "#6b7280",
    }

    def cell(label, value):
        return [Paragraph(label, label_style), Paragraph(str(value) if value else "—", body_style)]

    data = [
        ["Field", "Value"],
        ["Request ID", req.request_number],
        ["Request Type", req.request_type.name],
        ["Requester", req.requester.name],
        ["Requester Email", req.requester.email],
        ["Priority", req.priority.value],
        ["Status", req.status.value],
        ["Short Description", req.short_description],
        ["Created Date", str(req.created_date.date())],
        ["Requested Date", str(req.requested_date)],
        ["Target Resolution Date", str(req.target_resolution_date)],
        ["Approval Date", str(req.approval_date.date()) if req.approval_date else "—"],
        ["Approved By", req.approver.name if req.approver else "—"],
        ["Fulfillment Date", str(req.fulfillment_date.date()) if req.fulfillment_date else "—"],
        ["Closed Date", str(req.closed_date.date()) if req.closed_date else "—"],
    ]

    table = Table(data, colWidths=[60 * mm, 110 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#6c63ff")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 11),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f9f9ff"), colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e0e0e0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(table)
    story.append(Spacer(1, 8 * mm))

    # Justification
    story.append(Paragraph("Justification / Comments", header_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e0e0e0")))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(req.justification, body_style))
    story.append(Spacer(1, 8 * mm))

    # Activity history
    if req.comments:
        story.append(Paragraph("Activity History", header_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e0e0e0")))
        story.append(Spacer(1, 3 * mm))
        history_data = [["Timestamp", "Author", "Action", "Comment"]]
        for c in req.comments:
            history_data.append([
                str(c.timestamp.strftime("%Y-%m-%d %H:%M")),
                c.author.name,
                c.action_type.value.replace("_", " ").title(),
                c.content[:100] + ("..." if len(c.content) > 100 else ""),
            ])
        htable = Table(history_data, colWidths=[35 * mm, 35 * mm, 30 * mm, 70 * mm])
        htable.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f0f0ff"), colors.white]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e0e0e0")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("WORDWRAP", (3, 1), (3, -1), True),
        ]))
        story.append(htable)

    # Footer
    story.append(Spacer(1, 10 * mm))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e0e0e0")))
    story.append(Paragraph(
        "Generated by Nila AI Workplace Access System · Confidential",
        ParagraphStyle("Footer", parent=styles["Normal"], fontSize=8,
                       textColor=colors.HexColor("#aaaaaa"), alignment=TA_CENTER)
    ))

    doc.build(story)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{req.request_number}.pdf"'},
    )


# ─── CSV / Excel Export ────────────────────────────────────────────────────────

@router.get("/requests/csv")
def export_csv(
    request_type_id: Optional[int] = Query(None),
    status: Optional[RequestStatus] = Query(None),
    priority: Optional[Priority] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    fmt: str = Query("csv", regex="^(csv|excel)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Request)
    if current_user.role == UserRole.employee:
        q = q.filter(Request.requester_id == current_user.id)
    if request_type_id:
        q = q.filter(Request.request_type_id == request_type_id)
    if status:
        q = q.filter(Request.status == status)
    if priority:
        q = q.filter(Request.priority == priority)
    if date_from:
        q = q.filter(Request.created_date >= date_from)
    if date_to:
        q = q.filter(Request.created_date <= date_to)

    rows = q.order_by(Request.created_date.desc()).all()

    data = []
    for r in rows:
        data.append({
            "Request ID": r.request_number,
            "Request Type": r.request_type.name,
            "Requester": r.requester.name,
            "Requester Email": r.requester.email,
            "Short Description": r.short_description,
            "Priority": r.priority.value,
            "Status": r.status.value,
            "Created Date": str(r.created_date.date()),
            "Requested Date": str(r.requested_date),
            "Target Resolution Date": str(r.target_resolution_date),
            "Approval Date": str(r.approval_date.date()) if r.approval_date else "",
            "Approved By": r.approver.name if r.approver else "",
            "Fulfillment Date": str(r.fulfillment_date.date()) if r.fulfillment_date else "",
            "Closed Date": str(r.closed_date.date()) if r.closed_date else "",
        })

    df = pd.DataFrame(data)
    buffer = io.BytesIO()

    if fmt == "excel":
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Requests")
        buffer.seek(0)
        return StreamingResponse(
            buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=nila_requests.xlsx"},
        )
    else:
        df.to_csv(buffer, index=False)
        buffer.seek(0)
        return StreamingResponse(
            buffer,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=nila_requests.csv"},
        )
