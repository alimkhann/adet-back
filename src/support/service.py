from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc, and_, select
from typing import List, Optional
from datetime import datetime
import logging
from fastapi import HTTPException

from .models import (
    SupportRequest, BugReport, SupportResponse,
    SupportRequestCreate, BugReportCreate, SupportResponseCreate,
    SUPPORT_CATEGORIES, BUG_CATEGORIES, SEVERITY_LEVELS,
    STATUS_OPTIONS, BUG_STATUS_OPTIONS, PRIORITY_OPTIONS
)
from .email_service import email_service
from ..auth.models import User
from .crud import (
    create_waitlist_email, get_waitlist_emails, get_waitlist_count, bulk_create_waitlist_emails,
    create_support_request, get_support_requests, get_support_request_by_id, update_support_request, get_support_requests_count,
    create_bug_report, get_bug_reports, get_bug_report_by_id, update_bug_report, get_bug_reports_count
)
from .schemas import (
    WaitlistEmailCreate, WaitlistEmailResponse, WaitlistEmailList,
    SupportRequestCreate, SupportRequestResponse, SupportRequestUpdate,
    BugReportCreate, BugReportResponse, BugReportUpdate
)

logger = logging.getLogger(__name__)


class SupportService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # Support Request Methods
    def create_support_request(self, user_id: Optional[str], request_data: SupportRequestCreate) -> SupportRequest:
        """Create a new support request"""
        if request_data.category not in SUPPORT_CATEGORIES:
            raise ValueError(f"Invalid category. Must be one of: {SUPPORT_CATEGORIES}")

        support_request = SupportRequest(
            user_id=user_id,
            category=request_data.category,
            subject=request_data.subject,
            message=request_data.message,
            system_info=request_data.system_info.dict() if request_data.system_info else None
        )

        self.db.add(support_request)
        self.db.commit()
        self.db.refresh(support_request)

        logger.info(f"Created support request {support_request.id} for user {user_id}")

        # Send email notifications
        try:
            # Get user email from database
            if user_id:
                user = self.db.query(User).filter(User.clerk_id == user_id).first()
                if user and user.email:
                    email_service.send_support_request_notification(
                        user.email, support_request.id, support_request.category, support_request.subject
                    )
                    email_service.send_admin_notification(
                        "support", support_request.id, user.email, support_request.category, support_request.subject
                    )
        except Exception as e:
            logger.error(f"Failed to send email notifications for support request {support_request.id}: {e}")

        return support_request

    def get_support_request(self, request_id: int, user_id: str) -> Optional[SupportRequest]:
        """Get a specific support request by ID"""
        return self.db.query(SupportRequest).filter(
            and_(
                SupportRequest.id == request_id,
                SupportRequest.user_id == user_id
            )
        ).first()

    def get_user_support_history(self, user_id: str, limit: int = 50, offset: int = 0) -> List[SupportRequest]:
        """Get support request history for a user"""
        return self.db.query(SupportRequest).filter(
            SupportRequest.user_id == user_id
        ).order_by(desc(SupportRequest.created_at)).offset(offset).limit(limit).all()

    def update_support_request(self, request_id: int, user_id: str, update_data: dict) -> Optional[SupportRequest]:
        """Update a support request (admin only)"""
        support_request = self.get_support_request(request_id, user_id)
        if not support_request:
            return None

        for field, value in update_data.items():
            if hasattr(support_request, field) and value is not None:
                if field == "status" and value not in STATUS_OPTIONS:
                    raise ValueError(f"Invalid status. Must be one of: {STATUS_OPTIONS}")
                if field == "priority" and value not in PRIORITY_OPTIONS:
                    raise ValueError(f"Invalid priority. Must be one of: {PRIORITY_OPTIONS}")

                setattr(support_request, field, value)

        if update_data.get("status") == "resolved" and not support_request.resolved_at:
            support_request.resolved_at = datetime.utcnow()

        support_request.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(support_request)

        logger.info(f"Updated support request {request_id}")
        return support_request

    def add_support_response(self, request_id: int, responder_id: str, response_data: SupportResponseCreate) -> SupportResponse:
        """Add a response to a support request"""
        support_request = self.db.query(SupportRequest).filter(SupportRequest.id == request_id).first()
        if not support_request:
            raise ValueError("Support request not found")

        response = SupportResponse(
            support_request_id=request_id,
            responder_id=responder_id,
            message=response_data.message,
            is_internal=response_data.is_internal
        )

        self.db.add(response)
        self.db.commit()
        self.db.refresh(response)

        logger.info(f"Added response to support request {request_id}")
        return response

    # Bug Report Methods
    def create_bug_report(self, user_id: str, bug_data: BugReportCreate) -> BugReport:
        """Create a new bug report"""
        if bug_data.category not in BUG_CATEGORIES:
            raise ValueError(f"Invalid category. Must be one of: {BUG_CATEGORIES}")
        if bug_data.severity not in SEVERITY_LEVELS:
            raise ValueError(f"Invalid severity. Must be one of: {SEVERITY_LEVELS}")

        bug_report = BugReport(
            user_id=user_id,
            category=bug_data.category,
            severity=bug_data.severity,
            title=bug_data.title,
            description=bug_data.description,
            steps_to_reproduce=bug_data.steps_to_reproduce,
            expected_behavior=bug_data.expected_behavior,
            actual_behavior=bug_data.actual_behavior,
            system_info=bug_data.system_info.dict() if bug_data.system_info else None,
            include_screenshots=bug_data.include_screenshots
        )

        self.db.add(bug_report)
        self.db.commit()
        self.db.refresh(bug_report)

        logger.info(f"Created bug report {bug_report.id} for user {user_id}")

        # Send email notifications
        try:
            # Get user email from database
            user = self.db.query(User).filter(User.clerk_id == user_id).first()
            if user and user.email:
                email_service.send_bug_report_notification(
                    user.email, bug_report.id, bug_report.category, bug_report.severity, bug_report.title
                )
                email_service.send_admin_notification(
                    "bug", bug_report.id, user.email, bug_report.category, bug_report.title, bug_report.severity
                )
        except Exception as e:
            logger.error(f"Failed to send email notifications for bug report {bug_report.id}: {e}")

        return bug_report

    def get_bug_report(self, report_id: int, user_id: str) -> Optional[BugReport]:
        """Get a specific bug report by ID"""
        return self.db.query(BugReport).filter(
            and_(
                BugReport.id == report_id,
                BugReport.user_id == user_id
            )
        ).first()

    def get_user_bug_history(self, user_id: str, limit: int = 50, offset: int = 0) -> List[BugReport]:
        """Get bug report history for a user"""
        return self.db.query(BugReport).filter(
            BugReport.user_id == user_id
        ).order_by(desc(BugReport.created_at)).offset(offset).limit(limit).all()

    def update_bug_report(self, report_id: int, user_id: str, update_data: dict) -> Optional[BugReport]:
        """Update a bug report (admin only)"""
        bug_report = self.get_bug_report(report_id, user_id)
        if not bug_report:
            return None

        for field, value in update_data.items():
            if hasattr(bug_report, field) and value is not None:
                if field == "status" and value not in BUG_STATUS_OPTIONS:
                    raise ValueError(f"Invalid status. Must be one of: {BUG_STATUS_OPTIONS}")

                setattr(bug_report, field, value)

        if update_data.get("status") == "resolved" and not bug_report.resolved_at:
            bug_report.resolved_at = datetime.utcnow()

        bug_report.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(bug_report)

        logger.info(f"Updated bug report {report_id}")
        return bug_report

    def add_bug_response(self, report_id: int, responder_id: str, response_data: SupportResponseCreate) -> SupportResponse:
        """Add a response to a bug report"""
        bug_report = self.db.query(BugReport).filter(BugReport.id == report_id).first()
        if not bug_report:
            raise ValueError("Bug report not found")

        response = SupportResponse(
            bug_report_id=report_id,
            responder_id=responder_id,
            message=response_data.message,
            is_internal=response_data.is_internal
        )

        self.db.add(response)
        self.db.commit()
        self.db.refresh(response)

        logger.info(f"Added response to bug report {report_id}")
        return response

    # Admin Methods
    def get_all_support_requests(self, status: Optional[str] = None, limit: int = 50, offset: int = 0) -> List[SupportRequest]:
        """Get all support requests (admin only)"""
        query = self.db.query(SupportRequest)
        if status:
            query = query.filter(SupportRequest.status == status)
        return query.order_by(desc(SupportRequest.created_at)).offset(offset).limit(limit).all()

    def get_all_bug_reports(self, status: Optional[str] = None, severity: Optional[str] = None, limit: int = 50, offset: int = 0) -> List[BugReport]:
        """Get all bug reports (admin only)"""
        query = self.db.query(BugReport)
        if status:
            query = query.filter(BugReport.status == status)
        if severity:
            query = query.filter(BugReport.severity == severity)
        return query.order_by(desc(BugReport.created_at)).offset(offset).limit(limit).all()

    def get_support_statistics(self) -> dict:
        """Get support system statistics"""
        total_requests = self.db.query(SupportRequest).count()
        open_requests = self.db.query(SupportRequest).filter(SupportRequest.status == "open").count()
        resolved_requests = self.db.query(SupportRequest).filter(SupportRequest.status == "resolved").count()

        total_bugs = self.db.query(BugReport).count()
        open_bugs = self.db.query(BugReport).filter(BugReport.status == "open").count()
        resolved_bugs = self.db.query(BugReport).filter(BugReport.status == "resolved").count()

        high_severity_bugs = self.db.query(BugReport).filter(
            and_(BugReport.severity == "high", BugReport.status == "open")
        ).count()

        return {
            "support_requests": {
                "total": total_requests,
                "open": open_requests,
                "resolved": resolved_requests
            },
            "bug_reports": {
                "total": total_bugs,
                "open": open_bugs,
                "resolved": resolved_bugs,
                "high_severity_open": high_severity_bugs
            }
        }

    # Async Waitlist Methods
    async def add_waitlist_email(self, email_data: WaitlistEmailCreate) -> WaitlistEmailResponse:
        """Add a new email to the waitlist"""
        try:
            db_email = await create_waitlist_email(self.db, email_data.email, email_data.country, email_data.status or 'success')
            return WaitlistEmailResponse(
                id=db_email.id,
                email=db_email.email,
                created_at=db_email.created_at,
                country=db_email.country,
                status=db_email.status
            )
        except ValueError as e:
            logger.error(f"Waitlist error: {e}")
            raise HTTPException(status_code=409, detail=str(e))
        except Exception as e:
            logger.error(f"Error adding waitlist email: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    async def get_waitlist_emails_service(self, skip: int = 0, limit: int = 100, filter: str = None, date: str = None) -> WaitlistEmailList:
        """Get paginated list of waitlist emails with optional filtering"""
        try:
            emails = await get_waitlist_emails(self.db, skip=skip, limit=limit, filter=filter, date=date)
            total_count = await get_waitlist_count(self.db)

            return WaitlistEmailList(
                emails=[
                    WaitlistEmailResponse(
                        id=email.id,
                        email=email.email,
                        created_at=email.created_at,
                        country=getattr(email, 'country', None),
                        status=getattr(email, 'status', None)
                    ) for email in emails
                ],
                total_count=total_count
            )
        except Exception as e:
            logger.error(f"Error getting waitlist emails: {e}")
            raise

    async def get_waitlist_count_service(self) -> int:
        """Get total count of waitlist emails"""
        try:
            return await get_waitlist_count(self.db)
        except Exception as e:
            logger.error(f"Error getting waitlist count: {e}")
            raise

    async def bulk_add_waitlist_emails(self, emails: list[str]) -> list[WaitlistEmailResponse]:
        """Bulk add emails to waitlist"""
        try:
            db_emails = await bulk_create_waitlist_emails(self.db, emails)
            return [
                WaitlistEmailResponse(
                    id=email.id,
                    email=email.email,
                    created_at=email.created_at
                ) for email in db_emails
            ]
        except Exception as e:
            logger.error(f"Error bulk adding waitlist emails: {e}")
            raise

    # Async Support Request Methods
    async def create_support_request(self, request_data: SupportRequestCreate) -> SupportRequestResponse:
        """Create a new support request (async)"""
        try:
            # For now, using a placeholder user_id since we don't have auth context
            user_id = "admin"  # This should come from auth context in real implementation
            db_request = await create_support_request(
                self.db, user_id, request_data.category, request_data.subject,
                request_data.message, request_data.system_info.dict() if request_data.system_info else None
            )
            return SupportRequestResponse.from_orm(db_request)
        except Exception as e:
            logger.error(f"Error creating support request: {e}")
            raise

    async def get_support_requests_service(self, skip: int = 0, limit: int = 100, status: str = None) -> List[SupportRequestResponse]:
        """Get paginated list of support requests (async)"""
        try:
            requests = await get_support_requests(self.db, skip=skip, limit=limit, status=status)
            return [SupportRequestResponse.from_orm(req) for req in requests]
        except Exception as e:
            logger.error(f"Error getting support requests: {e}")
            raise

    async def get_support_request_by_id_service(self, request_id: int) -> Optional[SupportRequestResponse]:
        """Get a specific support request by ID (async)"""
        try:
            request = await get_support_request_by_id(self.db, request_id)
            return SupportRequestResponse.from_orm(request) if request else None
        except Exception as e:
            logger.error(f"Error getting support request by ID: {e}")
            raise

    async def update_support_request_service(self, request_id: int, update_data: SupportRequestUpdate) -> Optional[SupportRequestResponse]:
        """Update a support request (async)"""
        try:
            update_dict = update_data.dict(exclude_unset=True)
            request = await update_support_request(self.db, request_id, **update_dict)
            return SupportRequestResponse.from_orm(request) if request else None
        except Exception as e:
            logger.error(f"Error updating support request: {e}")
            raise

    async def get_support_requests_count_service(self, status: str = None) -> int:
        """Get count of support requests (async)"""
        try:
            return await get_support_requests_count(self.db, status=status)
        except Exception as e:
            logger.error(f"Error getting support requests count: {e}")
            raise

    # Async Bug Report Methods
    async def create_bug_report(self, report_data: BugReportCreate) -> BugReportResponse:
        """Create a new bug report (async)"""
        try:
            # For now, using a placeholder user_id since we don't have auth context
            user_id = "admin"  # This should come from auth context in real implementation
            db_report = await create_bug_report(
                self.db, user_id, report_data.category, report_data.severity,
                report_data.title, report_data.description, report_data.steps_to_reproduce,
                report_data.expected_behavior, report_data.actual_behavior,
                report_data.system_info.dict() if report_data.system_info else None,
                report_data.include_screenshots
            )
            return BugReportResponse.from_orm(db_report)
        except Exception as e:
            logger.error(f"Error creating bug report: {e}")
            raise

    async def get_bug_reports_service(self, skip: int = 0, limit: int = 100, status: str = None) -> List[BugReportResponse]:
        """Get paginated list of bug reports (async)"""
        try:
            reports = await get_bug_reports(self.db, skip=skip, limit=limit, status=status)
            return [BugReportResponse.from_orm(report) for report in reports]
        except Exception as e:
            logger.error(f"Error getting bug reports: {e}")
            raise

    async def get_bug_report_by_id_service(self, report_id: int) -> Optional[BugReportResponse]:
        """Get a specific bug report by ID (async)"""
        try:
            report = await get_bug_report_by_id(self.db, report_id)
            return BugReportResponse.from_orm(report) if report else None
        except Exception as e:
            logger.error(f"Error getting bug report by ID: {e}")
            raise

    async def update_bug_report_service(self, report_id: int, update_data: BugReportUpdate) -> Optional[BugReportResponse]:
        """Update a bug report (async)"""
        try:
            update_dict = update_data.dict(exclude_unset=True)
            report = await update_bug_report(self.db, report_id, **update_dict)
            return BugReportResponse.from_orm(report) if report else None
        except Exception as e:
            logger.error(f"Error updating bug report: {e}")
            raise

    async def get_bug_reports_count_service(self, status: str = None) -> int:
        """Get count of bug reports (async)"""
        try:
            return await get_bug_reports_count(self.db, status=status)
        except Exception as e:
            logger.error(f"Error getting bug reports count: {e}")
            raise

    async def create_support_request_from_public(self, email: str, question: str):
        # Store a support request from a public (unauthenticated) user
        # Use generic values for category/subject, and store email in subject/message
        category = "general"
        subject = f"Public Support: {email}"
        message = question
        user_id = None  # for public requests
        return await create_support_request(
            self.db,
            user_id=user_id,
            category=category,
            subject=subject,
            message=message,
            system_info=None
        )

