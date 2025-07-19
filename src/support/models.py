from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from ..database import Base


# Database Models
class SupportRequest(Base):
    __tablename__ = "support_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.clerk_id"), nullable=True)
    category = Column(String(50), nullable=False)
    subject = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    status = Column(String(20), default="open")
    priority = Column(String(20), default="medium")
    system_info = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    assigned_to = Column(String, ForeignKey("users.clerk_id"), nullable=True)
    admin_notes = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="support_requests")
    assignee = relationship("User", foreign_keys=[assigned_to])
    responses = relationship("SupportResponse", back_populates="support_request", cascade="all, delete-orphan")


class BugReport(Base):
    __tablename__ = "bug_reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.clerk_id"), nullable=False)
    category = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    steps_to_reproduce = Column(Text, nullable=True)
    expected_behavior = Column(Text, nullable=True)
    actual_behavior = Column(Text, nullable=True)
    status = Column(String(20), default="open")
    system_info = Column(JSON)
    include_screenshots = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    assigned_to = Column(String, ForeignKey("users.clerk_id"), nullable=True)
    admin_notes = Column(Text, nullable=True)
    github_issue_url = Column(String(500), nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="bug_reports")
    assignee = relationship("User", foreign_keys=[assigned_to])
    responses = relationship("SupportResponse", back_populates="bug_report", cascade="all, delete-orphan")


class SupportResponse(Base):
    __tablename__ = "support_responses"

    id = Column(Integer, primary_key=True, index=True)
    support_request_id = Column(Integer, ForeignKey("support_requests.id"), nullable=True)
    bug_report_id = Column(Integer, ForeignKey("bug_reports.id"), nullable=True)
    responder_id = Column(String, ForeignKey("users.clerk_id"), nullable=False)
    message = Column(Text, nullable=False)
    is_internal = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    responder = relationship("User", foreign_keys=[responder_id])
    support_request = relationship("SupportRequest", back_populates="responses")
    bug_report = relationship("BugReport", back_populates="responses")


class WaitlistEmail(Base):
    __tablename__ = "waitlist_emails"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    country = Column(String(64), nullable=True, default=None)
    status = Column(String(32), nullable=False, default="success")


# Pydantic Models for API
class SystemInfo(BaseModel):
    app_version: str
    build_number: str
    ios_version: str
    device_model: str
    device_name: str
    language: str
    timezone: str
    timestamp: datetime


class SupportRequestCreate(BaseModel):
    category: str = Field(..., description="Support category")
    subject: str = Field(..., min_length=1, max_length=255, description="Brief description of the issue")
    message: str = Field(..., min_length=1, description="Detailed description of the issue")
    system_info: Optional[SystemInfo] = None


class SupportRequestUpdate(BaseModel):
    status: Optional[str] = Field(None, description="New status")
    priority: Optional[str] = Field(None, description="New priority")
    assigned_to: Optional[str] = Field(None, description="User ID to assign to")
    admin_notes: Optional[str] = Field(None, description="Internal admin notes")


class SupportRequestResponse(BaseModel):
    id: int
    category: str
    subject: str
    message: str
    status: str
    priority: str
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    assigned_to: Optional[str] = None
    system_info: Optional[SystemInfo] = None

    class Config:
        from_attributes = True


class BugReportCreate(BaseModel):
    category: str = Field(..., description="Bug category")
    severity: str = Field(..., description="Bug severity level")
    title: str = Field(..., min_length=1, max_length=255, description="Brief description of the bug")
    description: str = Field(..., min_length=1, description="Detailed description of the bug")
    steps_to_reproduce: Optional[str] = Field(None, description="Steps to reproduce the bug")
    expected_behavior: Optional[str] = Field(None, description="What should have happened")
    actual_behavior: Optional[str] = Field(None, description="What actually happened")
    system_info: Optional[SystemInfo] = None
    include_screenshots: bool = False


class BugReportUpdate(BaseModel):
    status: Optional[str] = Field(None, description="New status")
    assigned_to: Optional[str] = Field(None, description="User ID to assign to")
    admin_notes: Optional[str] = Field(None, description="Internal admin notes")
    github_issue_url: Optional[str] = Field(None, description="GitHub issue URL")


class BugReportResponse(BaseModel):
    id: int
    category: str
    severity: str
    title: str
    description: str
    status: str
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    assigned_to: Optional[str] = None
    system_info: Optional[SystemInfo] = None
    include_screenshots: bool
    github_issue_url: Optional[str] = None

    class Config:
        from_attributes = True


class SupportResponseCreate(BaseModel):
    message: str = Field(..., min_length=1, description="Response message")
    is_internal: bool = Field(False, description="Whether this is an internal note")


class SupportResponseResponse(BaseModel):
    id: int
    message: str
    is_internal: bool
    created_at: datetime
    responder_id: str

    class Config:
        from_attributes = True


class SupportHistoryResponse(BaseModel):
    tickets: List[SupportRequestResponse]
    count: int


class BugReportHistoryResponse(BaseModel):
    bug_reports: List[BugReportResponse]
    count: int


# Enums for validation
SUPPORT_CATEGORIES = [
    "general", "technical", "billing", "feature", "bug", "account", "privacy"
]

BUG_CATEGORIES = [
    "general", "ui", "performance", "crash", "authentication",
    "habits", "friends", "chat", "notifications"
]

SEVERITY_LEVELS = ["low", "medium", "high", "critical"]

STATUS_OPTIONS = ["open", "in_progress", "resolved", "closed"]

BUG_STATUS_OPTIONS = ["open", "investigating", "confirmed", "in_progress", "resolved", "closed"]

PRIORITY_OPTIONS = ["low", "medium", "high", "critical"]
