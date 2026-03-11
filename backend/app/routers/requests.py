from datetime import datetime, date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import (
    Request, RequestType, User, Comment,
    RequestStatus, Priority, UserRole, CommentActionType
)
from ..schemas import (
    RequestCreate, RequestUpdate, RequestOut, RequestListOut,
    StatusTransition, CommentCreate, CommentOut,
    EmployeeDashboard, ApproverDashboard
)
from ..auth import get_current_user, require_approver_or_admin
from ..services import (
    generate_request_number, calculate_target_date,
    validate_transition, send_email_notification, build_submission_email
)

router = APIRouter(prefix="/api/requests", tags=["Requests"])


# ─── Create ────────────────────────────────────────────────────────────────────

@router.post("/", response_model=RequestOut, status_code=201)
def create_request(
    payload: RequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rt = db.query(RequestType).filter(
        RequestType.id == payload.request_type_id, RequestType.is_active == True
    ).first()
    if not rt:
        raise HTTPException(status_code=404, detail="Request type not found")

    now = datetime.utcnow()
    req_number = generate_request_number(db)
    target_date = calculate_target_date(rt, payload.priority, now.date())

    req = Request(
        request_number=req_number,
        request_type_id=payload.request_type_id,
        requester_id=current_user.id,
        short_description=payload.short_description,
        justification=payload.justification,
        priority=payload.priority,
        requested_date=payload.requested_date,
        created_date=now,
        target_resolution_date=target_date,
        status=RequestStatus.submitted,
    )
    db.add(req)
    db.flush()

    # Submission comment
    comment = Comment(
        request_id=req.id,
        author_id=current_user.id,
        content="Request submitted.",
        action_type=CommentActionType.submission,
    )
    db.add(comment)
    db.commit()
    db.refresh(req)

    # Email notification
    recipients = [current_user.email]
    if current_user.manager_email:
        recipients.append(current_user.manager_email)
    send_email_notification(
        recipients,
        f"[Nila] Request Submitted: {req.request_number}",
        build_submission_email(req, current_user),
    )

    return req


# ─── List ──────────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[RequestListOut])
def list_requests(
    request_type_id: Optional[int] = Query(None),
    status: Optional[RequestStatus] = Query(None),
    priority: Optional[Priority] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    date_field: str = Query("created_date", regex="^(created_date|target_resolution_date)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Request)
    # Employees only see their own
    if current_user.role == UserRole.employee:
        q = q.filter(Request.requester_id == current_user.id)

    if request_type_id:
        q = q.filter(Request.request_type_id == request_type_id)
    if status:
        q = q.filter(Request.status == status)
    if priority:
        q = q.filter(Request.priority == priority)
    if date_from:
        field = Request.created_date if date_field == "created_date" else Request.target_resolution_date
        q = q.filter(field >= date_from)
    if date_to:
        field = Request.created_date if date_field == "created_date" else Request.target_resolution_date
        q = q.filter(field <= date_to)

    return q.order_by(Request.created_date.desc()).all()


# ─── Detail ────────────────────────────────────────────────────────────────────

@router.get("/{req_id}", response_model=RequestOut)
def get_request(
    req_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    req = db.query(Request).filter(Request.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if current_user.role == UserRole.employee and req.requester_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")
    return req


# ─── Update ────────────────────────────────────────────────────────────────────

@router.put("/{req_id}", response_model=RequestOut)
def update_request(
    req_id: int,
    payload: RequestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    req = db.query(Request).filter(Request.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.requester_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")
    if req.status != RequestStatus.submitted:
        raise HTTPException(status_code=400, detail="Requests can only be edited while in 'Submitted' status")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(req, field, value)

    # Recalculate target date if relevant fields changed
    if payload.request_type_id or payload.priority:
        rt = db.query(RequestType).filter(RequestType.id == req.request_type_id).first()
        req.target_resolution_date = calculate_target_date(rt, req.priority, req.created_date.date())

    db.commit()
    db.refresh(req)
    return req


# ─── Status Transition ─────────────────────────────────────────────────────────

@router.post("/{req_id}/transition", response_model=RequestOut)
def transition_status(
    req_id: int,
    payload: StatusTransition,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    req = db.query(Request).filter(Request.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    # Permission checks per transition
    new_status = payload.new_status
    is_requester = req.requester_id == current_user.id
    is_staff = current_user.role in (UserRole.approver, UserRole.admin)

    if new_status == RequestStatus.under_review and not is_staff:
        raise HTTPException(status_code=403, detail="Only approvers/admins can move to Under Review")
    if new_status in (RequestStatus.approved, RequestStatus.rejected) and not is_staff:
        raise HTTPException(status_code=403, detail="Only approvers/admins can approve/reject")
    if new_status == RequestStatus.fulfilled and not is_staff:
        raise HTTPException(status_code=403, detail="Only approvers/admins can mark as fulfilled")
    if new_status == RequestStatus.closed and not is_requester and not is_staff:
        raise HTTPException(status_code=403, detail="Not allowed")
    # Rejection must include comment
    if new_status == RequestStatus.rejected and not payload.comment:
        raise HTTPException(status_code=400, detail="A comment is required when rejecting a request")
    # Re-submit (rejected -> submitted) must be requester
    if new_status == RequestStatus.submitted and req.status == RequestStatus.rejected and not is_requester:
        raise HTTPException(status_code=403, detail="Only the requester can re-submit")

    try:
        validate_transition(req.status, new_status, req.request_type.requires_approval)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Apply transition
    req.status = new_status
    now = datetime.utcnow()

    action_map = {
        RequestStatus.approved: CommentActionType.approval,
        RequestStatus.rejected: CommentActionType.rejection,
        RequestStatus.fulfilled: CommentActionType.fulfillment,
        RequestStatus.closed: CommentActionType.closure,
        RequestStatus.submitted: CommentActionType.submission,
    }

    if new_status == RequestStatus.approved:
        req.approval_date = now
        req.approver_id = current_user.id
    elif new_status == RequestStatus.fulfilled:
        req.fulfillment_date = now
    elif new_status == RequestStatus.closed:
        req.closed_date = now

    comment_text = payload.comment or f"Status changed to {new_status.value}"
    comment = Comment(
        request_id=req.id,
        author_id=current_user.id,
        content=comment_text,
        action_type=action_map.get(new_status, CommentActionType.status_change),
    )
    db.add(comment)
    db.commit()
    db.refresh(req)
    return req


# ─── Comments ──────────────────────────────────────────────────────────────────

@router.post("/{req_id}/comments", response_model=CommentOut, status_code=201)
def add_comment(
    req_id: int,
    payload: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    req = db.query(Request).filter(Request.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.status == RequestStatus.closed:
        raise HTTPException(status_code=400, detail="Cannot comment on a closed request")
    if current_user.role == UserRole.employee and req.requester_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")

    comment = Comment(
        request_id=req.id,
        author_id=current_user.id,
        content=payload.content,
        action_type=CommentActionType.comment,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


@router.get("/{req_id}/comments", response_model=List[CommentOut])
def get_comments(
    req_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    req = db.query(Request).filter(Request.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if current_user.role == UserRole.employee and req.requester_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")
    return req.comments


# ─── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard/employee", response_model=EmployeeDashboard)
def employee_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    today = date.today()
    my_requests = (
        db.query(Request)
        .filter(Request.requester_id == current_user.id)
        .order_by(Request.created_date.desc())
        .all()
    )
    active = sum(
        1 for r in my_requests
        if r.status not in (RequestStatus.closed, RequestStatus.rejected)
    )
    pending = sum(
        1 for r in my_requests
        if r.status in (RequestStatus.submitted, RequestStatus.under_review)
    )
    fulfilled_today = sum(
        1 for r in my_requests
        if r.fulfillment_date and r.fulfillment_date.date() == today
    )
    last_fulfilled = next(
        (r for r in my_requests if r.status == RequestStatus.fulfilled), None
    )
    return EmployeeDashboard(
        active_requests=active,
        pending_approval=pending,
        fulfilled_today=fulfilled_today,
        last_fulfilled=last_fulfilled,
        my_requests=my_requests[:20],
    )


@router.get("/dashboard/approver", response_model=ApproverDashboard)
def approver_dashboard(
    db: Session = Depends(get_db),
    _: User = Depends(require_approver_or_admin),
):
    today = date.today()
    all_requests = (
        db.query(Request)
        .order_by(Request.created_date.desc())
        .all()
    )
    pending_review = sum(
        1 for r in all_requests
        if r.status in (RequestStatus.submitted, RequestStatus.under_review)
    )
    high_priority = sum(
        1 for r in all_requests
        if r.priority == Priority.high
        and r.status not in (RequestStatus.fulfilled, RequestStatus.closed, RequestStatus.rejected)
    )
    fulfilled_today = sum(
        1 for r in all_requests
        if r.fulfillment_date and r.fulfillment_date.date() == today
    )
    return ApproverDashboard(
        pending_review=pending_review,
        high_priority_count=high_priority,
        fulfilled_today=fulfilled_today,
        recent_requests=all_requests[:50],
    )
