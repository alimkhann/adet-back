from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.database import get_async_db
from .schemas import DeviceTokenRegister, DeviceTokenResponse, NotificationSendRequest
from .service import NotificationService
from .models import DeviceToken
import logging

router = APIRouter(prefix="/notifications", tags=["Notifications"])
notification_service = NotificationService()
logger = logging.getLogger(__name__)

@router.post("/device", response_model=DeviceTokenResponse)
async def register_device_token(
    payload: DeviceTokenRegister,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    token = await notification_service.register_device_token(
        db=db,
        user_id=current_user.id,
        device_token=payload.device_token,
        platform=payload.platform,
        app_version=payload.app_version,
        system_version=payload.system_version
    )
    return DeviceTokenResponse(
        id=token.id,
        device_token=token.device_token,
        platform=token.platform,
        app_version=token.app_version,
        system_version=token.system_version,
        created_at=token.created_at.isoformat()
    )

@router.delete("/device", status_code=status.HTTP_204_NO_CONTENT)
async def unregister_device_token(
    device_token: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    success = await notification_service.unregister_device_token(
        db=db,
        user_id=current_user.id,
        device_token=device_token
    )
    if not success:
        raise HTTPException(status_code=404, detail="Device token not found")
    return

@router.post("/test", status_code=200)
async def send_test_notification(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    title = "Test Notification"
    body = "This is a test push notification from ädet backend."
    sent = await notification_service.send_push(
        db=db,
        user_id=current_user.id,
        title=title,
        body=body,
        data={"type": "test"},
        category="test"
    )
    if not sent:
        raise HTTPException(status_code=500, detail="Failed to send test notification")
    return {"success": True, "message": "Test notification sent"}

@router.post("/send", status_code=200)
async def send_notification_internal(
    payload: NotificationSendRequest,
    db: AsyncSession = Depends(get_async_db)
):
    # TODO: Add internal auth check (admin or service)
    sent = await notification_service.send_push(
        db=db,
        user_id=payload.user_id,
        title=payload.title,
        body=payload.body,
        data=payload.data,
        category=payload.category
    )
    if not sent:
        raise HTTPException(status_code=500, detail="Failed to send notification")
    return {"success": True, "message": "Notification sent"}