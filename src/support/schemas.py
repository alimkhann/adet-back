from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

# Waitlist schemas
class WaitlistEmailCreate(BaseModel):
    email: str
    country: Optional[str] = None
    status: Optional[str] = None

class WaitlistEmailResponse(BaseModel):
    id: int
    email: str
    created_at: datetime
    country: Optional[str] = None
    status: Optional[str] = None

    class Config:
        from_attributes = True

class WaitlistEmailList(BaseModel):
    emails: list[WaitlistEmailResponse]
    total_count: int

# Support Request schemas
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

# Bug Report schemas
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

