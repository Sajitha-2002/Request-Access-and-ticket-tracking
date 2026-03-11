import enum
from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Boolean, Text, Date, DateTime,
    ForeignKey, Enum as SAEnum, UniqueConstraint
)
from sqlalchemy.orm import relationship
from .database import Base


class UserRole(str, enum.Enum):
    admin = "admin"
    approver = "approver"
    employee = "employee"


class RequestStatus(str, enum.Enum):
    submitted = "Submitted"
    under_review = "Under Review"
    approved = "Approved"
    rejected = "Rejected"
    fulfilled = "Fulfilled"
    closed = "Closed"


class Priority(str, enum.Enum):
    low = "Low"
    medium = "Medium"
    high = "High"


class CommentActionType(str, enum.Enum):
    comment = "comment"
    status_change = "status_change"
    approval = "approval"
    rejection = "rejection"
    fulfillment = "fulfillment"
    closure = "closure"
    submission = "submission"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SAEnum(UserRole), default=UserRole.employee, nullable=False)
    manager_email = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    requests = relationship("Request", back_populates="requester", foreign_keys="Request.requester_id")
    comments = relationship("Comment", back_populates="author")


class RequestType(Base):
    __tablename__ = "request_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    requires_approval = Column(Boolean, default=True)
    turnaround_days = Column(Integer, default=5)
    is_active = Column(Boolean, default=True)

    requests = relationship("Request", back_populates="request_type")


class Request(Base):
    __tablename__ = "requests"

    id = Column(Integer, primary_key=True, index=True)
    request_number = Column(String(20), unique=True, index=True, nullable=False)
    request_type_id = Column(Integer, ForeignKey("request_types.id"), nullable=False)
    requester_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    approver_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    short_description = Column(String(255), nullable=False)
    justification = Column(Text, nullable=False)
    priority = Column(SAEnum(Priority), default=Priority.medium, nullable=False)
    requested_date = Column(Date, nullable=False)
    created_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    target_resolution_date = Column(Date, nullable=False)
    status = Column(SAEnum(RequestStatus), default=RequestStatus.submitted, nullable=False)
    approval_date = Column(DateTime, nullable=True)
    fulfillment_date = Column(DateTime, nullable=True)
    closed_date = Column(DateTime, nullable=True)

    request_type = relationship("RequestType", back_populates="requests")
    requester = relationship("User", back_populates="requests", foreign_keys=[requester_id])
    approver = relationship("User", foreign_keys=[approver_id])
    comments = relationship("Comment", back_populates="request", cascade="all, delete-orphan",
                            order_by="Comment.timestamp")


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("requests.id"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    action_type = Column(SAEnum(CommentActionType), default=CommentActionType.comment)

    request = relationship("Request", back_populates="comments")
    author = relationship("User", back_populates="comments")


class RequestSequence(Base):
    """Tracks auto-increment counters per year for REQ-YYYY-XXXX IDs."""
    __tablename__ = "request_sequences"

    id = Column(Integer, primary_key=True)
    year = Column(Integer, unique=True, nullable=False)
    last_number = Column(Integer, default=0, nullable=False)
