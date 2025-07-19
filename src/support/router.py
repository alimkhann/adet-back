from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import logging

from ..database import get_async_db
from ..auth.dependencies import get_current_user
from ..models import User
from .models import (
    SupportRequestCreate, SupportRequestResponse, SupportRequestUpdate,
    BugReportCreate, BugReportResponse, BugReportUpdate,
    SupportResponseCreate, SupportResponseResponse,
    SupportHistoryResponse, BugReportHistoryResponse
)
from .schemas import (
    WaitlistEmailCreate, WaitlistEmailResponse, WaitlistEmailList,
    SupportRequestCreate as SchemaSupportRequestCreate,
    SupportRequestResponse as SchemaSupportRequestResponse,
    SupportRequestUpdate as SchemaSupportRequestUpdate,
    BugReportCreate as SchemaBugReportCreate,
    BugReportResponse as SchemaBugReportResponse,
    BugReportUpdate as SchemaBugReportUpdate,
    PublicSupportRequestCreate
)
from .service import SupportService
from .admin_middleware import get_admin_user
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(tags=["support"])


# Support Request Endpoints
@router.post("/request", response_model=SupportRequestResponse)
async def create_support_request(
    request_data: SupportRequestCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Create a new support request"""
    try:
        service = SupportService(db)
        support_request = service.create_support_request(current_user.clerk_id, request_data)
        return SupportRequestResponse.from_orm(support_request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating support request: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/history", response_model=SupportHistoryResponse)
async def get_support_history(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get user's support request history"""
    try:
        service = SupportService(db)
        tickets = service.get_user_support_history(current_user.clerk_id, limit, offset)
        return SupportHistoryResponse(
            tickets=[SupportRequestResponse.from_orm(ticket) for ticket in tickets],
            count=len(tickets)
        )
    except Exception as e:
        logger.error(f"Error getting support history: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/request/{request_id}", response_model=SupportRequestResponse)
async def get_support_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get a specific support request"""
    try:
        service = SupportService(db)
        support_request = service.get_support_request(request_id, current_user.clerk_id)
        if not support_request:
            raise HTTPException(status_code=404, detail="Support request not found")
        return SupportRequestResponse.from_orm(support_request)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting support request: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/request/{request_id}", response_model=SupportRequestResponse)
async def update_support_request(
    request_id: int,
    update_data: SupportRequestUpdate,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Update a support request (admin only)"""
    try:
        service = SupportService(db)
        support_request = service.update_support_request(
            request_id,
            current_user.clerk_id,
            update_data.dict(exclude_unset=True)
        )
        if not support_request:
            raise HTTPException(status_code=404, detail="Support request not found")
        return SupportRequestResponse.from_orm(support_request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating support request: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/request/{request_id}/respond", response_model=SupportResponseResponse)
async def add_support_response(
    request_id: int,
    response_data: SupportResponseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Add a response to a support request"""
    try:
        service = SupportService(db)
        response = service.add_support_response(request_id, current_user.clerk_id, response_data)
        return SupportResponseResponse.from_orm(response)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding support response: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Bug Report Endpoints
@router.post("/bug-report", response_model=BugReportResponse)
async def create_bug_report(
    bug_data: BugReportCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Create a new bug report"""
    try:
        service = SupportService(db)
        bug_report = service.create_bug_report(current_user.clerk_id, bug_data)
        return BugReportResponse.from_orm(bug_report)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating bug report: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")





@router.get("/bug-report/{report_id}", response_model=BugReportResponse)
async def get_bug_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get a specific bug report"""
    try:
        service = SupportService(db)
        bug_report = service.get_bug_report(report_id, current_user.clerk_id)
        if not bug_report:
            raise HTTPException(status_code=404, detail="Bug report not found")
        return BugReportResponse.from_orm(bug_report)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting bug report: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/bug-report/{report_id}", response_model=BugReportResponse)
async def update_bug_report(
    report_id: int,
    update_data: BugReportUpdate,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Update a bug report (admin only)"""
    try:
        service = SupportService(db)
        bug_report = service.update_bug_report(
            report_id,
            current_user.clerk_id,
            update_data.dict(exclude_unset=True)
        )
        if not bug_report:
            raise HTTPException(status_code=404, detail="Bug report not found")
        return BugReportResponse.from_orm(bug_report)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating bug report: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/bug-report/{report_id}/respond", response_model=SupportResponseResponse)
async def add_bug_response(
    report_id: int,
    response_data: SupportResponseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Add a response to a bug report"""
    try:
        service = SupportService(db)
        response = service.add_bug_response(report_id, current_user.clerk_id, response_data)
        return SupportResponseResponse.from_orm(response)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding bug response: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Admin Endpoints
@router.get("/admin/requests", response_model=List[SupportRequestResponse])
async def get_all_support_requests(
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get all support requests (admin only)"""
    try:
        service = SupportService(db)
        requests = service.get_all_support_requests(status=status, limit=limit, offset=offset)
        return [SupportRequestResponse.from_orm(request) for request in requests]
    except Exception as e:
        logger.error(f"Error getting all support requests: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/admin/bug-reports", response_model=List[BugReportResponse])
async def get_all_bug_reports(
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get all bug reports (admin only)"""
    try:
        service = SupportService(db)
        reports = service.get_all_bug_reports(status=status, severity=severity, limit=limit, offset=offset)
        return [BugReportResponse.from_orm(report) for report in reports]
    except Exception as e:
        logger.error(f"Error getting all bug reports: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/admin/statistics")
async def get_support_statistics(
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get support system statistics (admin only)"""
    try:
        service = SupportService(db)
        return service.get_support_statistics()
    except Exception as e:
        logger.error(f"Error getting support statistics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Waitlist Endpoints
@router.post("/waitlist", response_model=WaitlistEmailResponse)
async def create_waitlist_email(
    email_data: WaitlistEmailCreate,
    db: AsyncSession = Depends(get_async_db)
):
    """Add a new email to the waitlist"""
    service = SupportService(db)
    return await service.add_waitlist_email(email_data)

@router.get("/waitlist", response_model=WaitlistEmailList)
async def get_waitlist_emails(
    skip: int = 0,
    limit: int = 100,
    filter: Optional[str] = Query(None),
    date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_async_db)
):
    """Get paginated list of waitlist emails with optional filtering"""
    service = SupportService(db)
    return await service.get_waitlist_emails_service(skip=skip, limit=limit, filter=filter, date=date)

@router.get("/waitlist/count")
async def get_waitlist_count(db: AsyncSession = Depends(get_async_db)):
    """Get total count of waitlist emails"""
    service = SupportService(db)
    return {"count": await service.get_waitlist_count_service()}

@router.post("/waitlist/bulk")
async def bulk_add_waitlist_emails_endpoint(
    emails: list[str],
    db: AsyncSession = Depends(get_async_db)
):
    """Bulk add emails to waitlist (admin only)"""
    service = SupportService(db)
    return await service.bulk_add_waitlist_emails(emails)

# New Admin Endpoints for Issues and Bug Reports (without auth for now)
@router.post("/issues", response_model=SchemaSupportRequestResponse)
async def create_support_request_admin(
    request_data: SchemaSupportRequestCreate,
    db: AsyncSession = Depends(get_async_db)
):
    """Create a new support request (admin endpoint)"""
    service = SupportService(db)
    return await service.create_support_request(request_data)

@router.get("/issues", response_model=List[SchemaSupportRequestResponse])
async def get_support_requests_admin(
    skip: int = 0,
    limit: int = 100,
    status: str = None,
    db: AsyncSession = Depends(get_async_db)
):
    """Get paginated list of support requests (admin endpoint)"""
    service = SupportService(db)
    return await service.get_support_requests_service(skip=skip, limit=limit, status=status)

@router.get("/issues/count")
async def get_support_requests_count_admin(
    status: str = None,
    db: AsyncSession = Depends(get_async_db)
):
    """Get count of support requests (admin endpoint)"""
    service = SupportService(db)
    return {"count": await service.get_support_requests_count_service(status=status)}

@router.get("/issues/{request_id}", response_model=SchemaSupportRequestResponse)
async def get_support_request_admin(
    request_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Get a specific support request by ID (admin endpoint)"""
    service = SupportService(db)
    request = await service.get_support_request_by_id_service(request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Support request not found")
    return request

@router.put("/issues/{request_id}", response_model=SchemaSupportRequestResponse)
async def update_support_request_admin(
    request_id: int,
    request_data: SchemaSupportRequestUpdate,
    db: AsyncSession = Depends(get_async_db)
):
    """Update a support request (admin endpoint)"""
    service = SupportService(db)
    request = await service.update_support_request_service(request_id, request_data)
    if not request:
        raise HTTPException(status_code=404, detail="Support request not found")
    return request

@router.post("/bug-reports", response_model=SchemaBugReportResponse)
async def create_bug_report_admin(
    report_data: SchemaBugReportCreate,
    db: AsyncSession = Depends(get_async_db)
):
    """Create a new bug report (admin endpoint)"""
    service = SupportService(db)
    return await service.create_bug_report(report_data)

@router.get("/bug-reports", response_model=List[SchemaBugReportResponse])
async def get_bug_reports_admin(
    skip: int = 0,
    limit: int = 100,
    status: str = None,
    db: AsyncSession = Depends(get_async_db)
):
    """Get paginated list of bug reports (admin endpoint)"""
    service = SupportService(db)
    return await service.get_bug_reports_service(skip=skip, limit=limit, status=status)

@router.get("/bug-reports/count")
async def get_bug_reports_count_admin(
    status: str = None,
    db: AsyncSession = Depends(get_async_db)
):
    """Get count of bug reports (admin endpoint)"""
    service = SupportService(db)
    return {"count": await service.get_bug_reports_count_service(status=status)}

@router.get("/bug-reports/{report_id}", response_model=SchemaBugReportResponse)
async def get_bug_report_admin(
    report_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Get a specific bug report by ID (admin endpoint)"""
    service = SupportService(db)
    report = await service.get_bug_report_by_id_service(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Bug report not found")
    return report

@router.put("/bug-reports/{report_id}", response_model=SchemaBugReportResponse)
async def update_bug_report_admin(
    report_id: int,
    report_data: SchemaBugReportUpdate,
    db: AsyncSession = Depends(get_async_db)
):
    """Update a bug report (admin endpoint)"""
    service = SupportService(db)
    report = await service.update_bug_report_service(report_id, report_data)
    if not report:
        raise HTTPException(status_code=404, detail="Bug report not found")
    return report

@router.post("/support-requests", tags=["support"])
async def create_public_support_request(
    data: PublicSupportRequestCreate,
    db: AsyncSession = Depends(get_async_db)
):
    """Public endpoint for landing page support form (email, question)."""
    try:
        # Store as a support request with generic category/subject
        service = SupportService(db)
        # You may want to customize this logic as needed
        support_request = await service.create_support_request_from_public(
            email=data.email,
            question=data.question
        )
        return {"success": True, "id": support_request.id}
    except Exception as e:
        logger.error(f"Error creating public support request: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

