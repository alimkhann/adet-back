import os
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError
import logging

from aioapns import APNs, NotificationRequest, PushType
import ssl

from .models import DeviceToken
from src.auth.models import User

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self):
        self.apns_client: Optional[APNs] = None
        self._initialize_apns_client()

    def _initialize_apns_client(self):
        """Initialize APNs client with configuration from environment variables."""
        try:
            key_path = os.getenv('APNS_AUTH_KEY_PATH')
            key_id = os.getenv('APNS_KEY_ID')
            team_id = os.getenv('APNS_TEAM_ID')
            topic = os.getenv('APNS_TOPIC')
            use_sandbox = os.getenv('APNS_USE_SANDBOX', 'true').lower() == 'true'

            if not all([key_path, key_id, team_id, topic]):
                logger.warning("APNs configuration incomplete. Push notifications will be disabled.")
                return

            if not os.path.exists(key_path):
                logger.warning(f"APNs key file not found at {key_path}. Push notifications will be disabled.")
                return

            self.apns_client = APNs(
                key=key_path,
                key_id=key_id,
                team_id=team_id,
                topic=topic,
                use_sandbox=use_sandbox
            )

            logger.info(f"APNs client initialized successfully. Sandbox: {use_sandbox}")

        except Exception as e:
            logger.error(f"Failed to initialize APNs client: {e}")
            self.apns_client = None

    async def register_device_token(
        self,
        db: AsyncSession,
        user_id: int,
        device_token: str,
        platform: str = "ios",
        app_version: Optional[str] = None,
        system_version: Optional[str] = None
    ) -> DeviceToken:
        """Register or update a device token for push notifications."""
        try:
            # Check if token already exists for this user
            stmt = select(DeviceToken).where(
                DeviceToken.user_id == user_id,
                DeviceToken.device_token == device_token
            )
            result = await db.execute(stmt)
            existing_token = result.scalar_one_or_none()

            if existing_token:
                # Update existing token
                existing_token.app_version = app_version
                existing_token.system_version = system_version
                existing_token.updated_at = datetime.utcnow()
                await db.commit()
                await db.refresh(existing_token)
                return existing_token
            else:
                # Create new token
                new_token = DeviceToken(
                    user_id=user_id,
                    device_token=device_token,
                    platform=platform,
                    app_version=app_version,
                    system_version=system_version
                )
                db.add(new_token)
                await db.commit()
                await db.refresh(new_token)
                return new_token

        except IntegrityError as e:
            await db.rollback()
            logger.error(f"Failed to register device token: {e}")
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"Unexpected error registering device token: {e}")
            raise

    async def unregister_device_token(
        self,
        db: AsyncSession,
        user_id: int,
        device_token: str
    ) -> bool:
        """Remove a device token."""
        try:
            stmt = delete(DeviceToken).where(
                DeviceToken.user_id == user_id,
                DeviceToken.device_token == device_token
            )
            result = await db.execute(stmt)
            await db.commit()
            return result.rowcount > 0
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to unregister device token: {e}")
            return False

    async def send_push(
        self,
        db: AsyncSession,
        user_id: int,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        category: Optional[str] = None,
        badge: Optional[int] = None
    ) -> bool:
        """Send a push notification to all devices for a user."""
        if not self.apns_client:
            logger.warning("APNs client not available. Skipping push notification.")
            return False

        try:
            # Get all device tokens for user
            stmt = select(DeviceToken).where(DeviceToken.user_id == user_id)
            result = await db.execute(stmt)
            device_tokens = result.scalars().all()

            if not device_tokens:
                logger.info(f"No device tokens found for user {user_id}")
                return False

            # Prepare notification
            notification_data = {
                "aps": {
                    "alert": {
                        "title": title,
                        "body": body
                    },
                    "sound": "default"
                }
            }

            if badge is not None:
                notification_data["aps"]["badge"] = badge

            if category:
                notification_data["aps"]["category"] = category

            if data:
                notification_data.update(data)

            # Send to all devices
            sent_count = 0
            for device_token in device_tokens:
                try:
                    request = NotificationRequest(
                        device_token=device_token.device_token,
                        message=notification_data,
                        push_type=PushType.ALERT
                    )

                    await self.apns_client.send_notification(request)
                    sent_count += 1
                    logger.info(f"Push notification sent to device {device_token.device_token[:10]}...")

                except Exception as e:
                    logger.error(f"Failed to send push to device {device_token.device_token[:10]}...: {e}")
                    # TODO: Handle invalid tokens by removing them from database

            return sent_count > 0

        except Exception as e:
            logger.error(f"Failed to send push notifications: {e}")
            return False