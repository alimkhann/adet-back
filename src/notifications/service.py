import os
import logging
from typing import Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from .models import DeviceToken
from src.auth.models import User

logger = logging.getLogger(__name__)

try:
    from apns2.client import APNsClient
    from apns2.payload import Payload
    from apns2.credentials import TokenCredentials
    APNS_AVAILABLE = True
except ImportError:
    APNS_AVAILABLE = False
    logger.warning("apns2 not installed. Push notifications will not work.")

class NotificationService:
    def __init__(self):
        self.apns_key_id = os.getenv("APNS_KEY_ID")
        self.apns_team_id = os.getenv("APNS_TEAM_ID")
        self.apns_auth_key_path = os.getenv("APNS_AUTH_KEY_PATH")
        self.apns_topic = os.getenv("APNS_TOPIC")  # Bundle ID
        self.apns_use_sandbox = os.getenv("APNS_USE_SANDBOX", "true").lower() == "true"
        self.apns_client = None
        if APNS_AVAILABLE and self.apns_key_id and self.apns_team_id and self.apns_auth_key_path and self.apns_topic:
            try:
                credentials = TokenCredentials(
                    auth_key_path=self.apns_auth_key_path,
                    auth_key_id=self.apns_key_id,
                    team_id=self.apns_team_id
                )
                self.apns_client = APNsClient(
                    credentials,
                    use_sandbox=self.apns_use_sandbox,
                    use_alternative_port=False
                )
                logger.info("APNs client initialized.")
            except Exception as e:
                logger.error(f"Failed to initialize APNs client: {e}")
                self.apns_client = None
        else:
            logger.warning("APNs credentials not set. Push notifications will not be sent.")

    async def register_device_token(self, db: AsyncSession, user_id: int, device_token: str, platform: str = "ios", app_version: Optional[str] = None, system_version: Optional[str] = None):
        # Upsert device token
        from sqlalchemy import select
        result = await db.execute(select(DeviceToken).where(DeviceToken.device_token == device_token))
        token = result.scalar_one_or_none()
        if token:
            token.user_id = user_id
            token.platform = platform
            token.app_version = app_version
            token.system_version = system_version
        else:
            token = DeviceToken(
                user_id=user_id,
                device_token=device_token,
                platform=platform,
                app_version=app_version,
                system_version=system_version
            )
            db.add(token)
        await db.commit()
        await db.refresh(token)
        return token

    async def unregister_device_token(self, db: AsyncSession, user_id: int, device_token: str):
        from sqlalchemy import select
        result = await db.execute(select(DeviceToken).where(DeviceToken.user_id == user_id, DeviceToken.device_token == device_token))
        token = result.scalar_one_or_none()
        if token:
            await db.delete(token)
            await db.commit()
            return True
        return False

    async def send_push(self, db: AsyncSession, user_id: int, title: str, body: str, data: Optional[Dict[str, str]] = None, category: Optional[str] = None) -> bool:
        if not APNS_AVAILABLE or not self.apns_client:
            logger.warning("APNs not available. Skipping push notification.")
            return False
        from sqlalchemy import select
        result = await db.execute(select(DeviceToken).where(DeviceToken.user_id == user_id))
        tokens = result.scalars().all()
        if not tokens:
            logger.info(f"No device tokens found for user {user_id}")
            return False
        payload = Payload(alert={"title": title, "body": body}, sound="default", badge=1, custom=data or {})
        success = True
        for token in tokens:
            try:
                self.apns_client.send_notification(token.device_token, payload, self.apns_topic)
                logger.info(f"Sent push notification to user {user_id} (token: {token.device_token})")
            except Exception as e:
                logger.error(f"Failed to send push to {token.device_token}: {e}")
                success = False
        return success