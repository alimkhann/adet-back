from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, cast, Date
from .models import WaitlistEmail, SupportRequest, BugReport
from sqlalchemy.exc import IntegrityError

async def create_waitlist_email(db: AsyncSession, email: str, country: str = None, status: str = "success") -> WaitlistEmail:
    db_email = WaitlistEmail(email=email, country=country, status=status)
    db.add(db_email)
    try:
        await db.commit()
        await db.refresh(db_email)
        return db_email
    except IntegrityError:
        await db.rollback()
        raise ValueError("This email is already on the waitlist.")

async def get_waitlist_emails(db: AsyncSession, skip: int = 0, limit: int = 100, filter: str = None, date: str = None) -> list[WaitlistEmail]:
    query = select(WaitlistEmail)
    conditions = []
    if filter:
        conditions.append(WaitlistEmail.email.ilike(f"%{filter}%"))
    if date:
        conditions.append(cast(WaitlistEmail.created_at, Date) == date)
    if conditions:
        query = query.where(and_(*conditions))
    query = query.offset(skip).limit(limit).order_by(WaitlistEmail.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()

async def get_waitlist_count(db: AsyncSession) -> int:
    result = await db.execute(select(func.count(WaitlistEmail.id)))
    return result.scalar()

async def bulk_create_waitlist_emails(db: AsyncSession, emails: list[str]) -> list[WaitlistEmail]:
    db_emails = []
    for email in emails:
        # Check if email already exists
        result = await db.execute(select(WaitlistEmail).where(WaitlistEmail.email == email))
        existing = result.scalar_one_or_none()
        if not existing:
            db_email = WaitlistEmail(email=email)
            db_emails.append(db_email)

    if db_emails:
        db.add_all(db_emails)
        await db.commit()
        for email in db_emails:
            await db.refresh(email)

    return db_emails

async def create_support_request(db: AsyncSession, user_id: str, category: str, subject: str, message: str, system_info: dict = None) -> SupportRequest:
    db_request = SupportRequest(
        user_id=user_id,
        category=category,
        subject=subject,
        message=message,
        system_info=system_info
    )
    db.add(db_request)
    await db.commit()
    await db.refresh(db_request)
    return db_request

async def get_support_requests(db: AsyncSession, skip: int = 0, limit: int = 100, status: str = None) -> list[SupportRequest]:
    query = select(SupportRequest)
    if status:
        query = query.where(SupportRequest.status == status)
    query = query.offset(skip).limit(limit).order_by(SupportRequest.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()

async def get_support_request_by_id(db: AsyncSession, request_id: int) -> SupportRequest:
    result = await db.execute(select(SupportRequest).where(SupportRequest.id == request_id))
    return result.scalar_one_or_none()

async def update_support_request(db: AsyncSession, request_id: int, **kwargs) -> SupportRequest:
    result = await db.execute(select(SupportRequest).where(SupportRequest.id == request_id))
    request = result.scalar_one_or_none()
    if request:
        for key, value in kwargs.items():
            if hasattr(request, key):
                setattr(request, key, value)
        await db.commit()
        await db.refresh(request)
    return request

async def get_support_requests_count(db: AsyncSession, status: str = None) -> int:
    query = select(func.count(SupportRequest.id))
    if status:
        query = query.where(SupportRequest.status == status)
    result = await db.execute(query)
    return result.scalar()

async def create_bug_report(db: AsyncSession, user_id: str, category: str, severity: str, title: str, description: str,
                           steps_to_reproduce: str = None, expected_behavior: str = None, actual_behavior: str = None,
                           system_info: dict = None, include_screenshots: bool = False) -> BugReport:
    db_report = BugReport(
        user_id=user_id,
        category=category,
        severity=severity,
        title=title,
        description=description,
        steps_to_reproduce=steps_to_reproduce,
        expected_behavior=expected_behavior,
        actual_behavior=actual_behavior,
        system_info=system_info,
        include_screenshots=include_screenshots
    )
    db.add(db_report)
    await db.commit()
    await db.refresh(db_report)
    return db_report

async def get_bug_reports(db: AsyncSession, skip: int = 0, limit: int = 100, status: str = None) -> list[BugReport]:
    query = select(BugReport)
    if status:
        query = query.where(BugReport.status == status)
    query = query.offset(skip).limit(limit).order_by(BugReport.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()

async def get_bug_report_by_id(db: AsyncSession, report_id: int) -> BugReport:
    result = await db.execute(select(BugReport).where(BugReport.id == report_id))
    return result.scalar_one_or_none()

async def update_bug_report(db: AsyncSession, report_id: int, **kwargs) -> BugReport:
    result = await db.execute(select(BugReport).where(BugReport.id == report_id))
    report = result.scalar_one_or_none()
    if report:
        for key, value in kwargs.items():
            if hasattr(report, key):
                setattr(report, key, value)
        await db.commit()
        await db.refresh(report)
    return report

async def get_bug_reports_count(db: AsyncSession, status: str = None) -> int:
    query = select(func.count(BugReport.id))
    if status:
        query = query.where(BugReport.status == status)
    result = await db.execute(query)
    return result.scalar()
