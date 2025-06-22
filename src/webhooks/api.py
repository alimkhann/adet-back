import os
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from svix.webhooks import Webhook, WebhookVerificationError

from ..database import get_async_db
from ..auth.crud import UserDAO
from .schemas import ClerkWebhookPayload, UserDeletedData
from ..config import settings

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

@router.post("/clerk")
async def handle_clerk_webhook(
    request: Request,
    svix_id: str = Header(None),
    svix_timestamp: str = Header(None),
    svix_signature: str = Header(None),
    db: AsyncSession = Depends(get_async_db),
):
    if not settings.clerk_webhook_secret:
        raise HTTPException(status_code=500, detail="Webhook secret is not configured.")

    headers = {
        "svix-id": svix_id,
        "svix-timestamp": svix_timestamp,
        "svix-signature": svix_signature,
    }

    payload = await request.body()

    try:
        wh = Webhook(settings.clerk_webhook_secret)
        evt = wh.verify(payload, headers)
    except WebhookVerificationError as e:
        raise HTTPException(status_code=400, detail=f"Webhook verification failed: {e}")

    event_data = ClerkWebhookPayload.model_validate(evt)

    if event_data.type == "user.deleted":
        user_data = UserDeletedData.model_validate(event_data.data)
        if user_data.id and user_data.deleted:
            await UserDAO.delete_user_by_clerk_id(db, clerk_id=user_data.id)
            return {"status": "ok", "message": f"User {user_data.id} deleted successfully."}

    return {"status": "ok", "message": "Webhook received but no action taken."}