from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, EmailStr, field_validator
from .models import UserRole, RequestStatus, Priority, CommentActionType


# ─── Auth ──────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


# ─── Users ─────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: UserRole = UserRole.employee
    manager_email: Optional[EmailStr] = None


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: UserRole
    manager_email: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[UserRole] = None
    manager_email: Optional[EmailStr] = None
    is_active: Optional[bool] = None


# ─── Request Types ─────────────────────────────────────────────────────────────

class RequestTypeCreate(BaseModel):
    name: str
    description: Optional[str] = None
    requires_approval: bool = True
    turnaround_days: int = 5


class RequestTypeOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    requires_approval: bool
    turnaround_days: int
    is_active: bool

    class Config:
        from_attributes = True


class RequestTypeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    requires_approval: Optional[bool] = None
    turnaround_days: Optional[int] = None
    is_active: Optional[bool] = None


# ─── Requests ──────────────────────────────────────────────────────────────────

class RequestCreate(BaseModel):
    request_type_id: int
    short_description: str
    justification: str
    priority: Priority = Priority.medium
    requested_date: date


class RequestUpdate(BaseModel):
    request_type_id: Optional[int] = None
    short_description: Optional[str] = None
    justification: Optional[str] = None
    priority: Optional[Priority] = None
    requested_date: Optional[date] = None


class StatusTransition(BaseModel):
    new_status: RequestStatus
    comment: Optional[str] = None


class RequestOut(BaseModel):
    id: int
    request_number: str
    request_type: RequestTypeOut
    requester: UserOut
    approver: Optional[UserOut] = None
    short_description: str
    justification: str
    priority: Priority
    requested_date: date
    created_date: datetime
    target_resolution_date: date
    status: RequestStatus
    approval_date: Optional[datetime] = None
    fulfillment_date: Optional[datetime] = None
    closed_date: Optional[datetime] = None

    class Config:
        from_attributes = True


class RequestListOut(BaseModel):
    id: int
    request_number: str
    request_type: RequestTypeOut
    requester: UserOut
    short_description: str
    priority: Priority
    created_date: datetime
    target_resolution_date: date
    status: RequestStatus

    class Config:
        from_attributes = True


# ─── Comments ──────────────────────────────────────────────────────────────────

class CommentCreate(BaseModel):
    content: str
    action_type: CommentActionType = CommentActionType.comment


class CommentOut(BaseModel):
    id: int
    request_id: int
    author: UserOut
    content: str
    timestamp: datetime
    action_type: CommentActionType

    class Config:
        from_attributes = True


# ─── Agent ─────────────────────────────────────────────────────────────────────

class AgentInput(BaseModel):
    message: str
    language: str = "en"


class AgentOutput(BaseModel):
    intent: str
    response: str
    action: Optional[str] = None
    pre_fill: Optional[dict] = None
    route: Optional[str] = None


# ─── Dashboard ─────────────────────────────────────────────────────────────────

class EmployeeDashboard(BaseModel):
    active_requests: int
    pending_approval: int
    fulfilled_today: int
    last_fulfilled: Optional[RequestListOut] = None
    my_requests: List[RequestListOut]


class ApproverDashboard(BaseModel):
    pending_review: int
    high_priority_count: int
    fulfilled_today: int
    recent_requests: List[RequestListOut]


# ─── Export ────────────────────────────────────────────────────────────────────

class ExportFilters(BaseModel):
    request_type_id: Optional[int] = None
    status: Optional[RequestStatus] = None
    priority: Optional[Priority] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None


Token.model_rebuild()
