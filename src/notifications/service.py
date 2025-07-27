import os
import logging
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete
from .models import DeviceToken
from apns2.client import APNsClient
from apns2.payload import Payload
from apns2.credentials import TokenCredentials

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self):
        self.apns_client = None
        self._initialize_apns_client()

    def _initialize_apns_client(self):
        """Initialize APNs client with authentication key"""
        try:
            key_path = os.environ.get('APNS_AUTH_KEY_PATH')
            team_id = os.environ.get('APNS_TEAM_ID')
            key_id = os.environ.get('APNS_KEY_ID')
            use_sandbox = os.environ.get('APNS_USE_SANDBOX', 'true').lower() == 'true'

            if not all([key_path, team_id, key_id]):
                logger.warning("APNs configuration incomplete. Push notifications will not work.")
                return

            if not os.path.exists(key_path):
                logger.warning(f"APNs key file not found at {key_path}. Push notifications will not work.")
                return

            credentials = TokenCredentials(
                auth_key_path=key_path,
                team_id=team_id,
                key_id=key_id
            )

            self.apns_client = APNsClient(
                credentials=credentials,
                use_sandbox=use_sandbox,
                use_alternative_port=False
            )
            logger.info("APNs client initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize APNs client: {e}")
            self.apns_client = None

    async def register_device_token(
        self,
        db: AsyncSession,
        user_id: int,
        device_token: str,
        platform: str = "ios",
        app_version: str = "1.0.0",
        system_version: str = "17.0"
    ) -> DeviceToken:
        """Register a device token for push notifications"""
        try:
            # Check if device token already exists for this user
            query = select(DeviceToken).where(
                DeviceToken.user_id == user_id,
                DeviceToken.device_token == device_token
            )
            result = await db.execute(query)
            existing_token = result.scalars().first()

            if existing_token:
                # Update existing token
                existing_token.platform = platform
                existing_token.app_version = app_version
                existing_token.system_version = system_version
                await db.commit()
                await db.refresh(existing_token)
                logger.info(f"Updated existing device token for user {user_id}")
                return existing_token

            # Create new device token
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
            logger.info(f"Registered new device token for user {user_id}")
            return new_token

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to register device token: {e}")
            raise

    async def unregister_device_token(
        self,
        db: AsyncSession,
        user_id: int,
        device_token: str
    ) -> bool:
        """Unregister a device token"""
        try:
            query = delete(DeviceToken).where(
                DeviceToken.user_id == user_id,
                DeviceToken.device_token == device_token
            )
            result = await db.execute(query)
            await db.commit()

            deleted_count = result.rowcount
            if deleted_count > 0:
                logger.info(f"Unregistered device token for user {user_id}")
                return True
            else:
                logger.warning(f"No device token found for user {user_id}")
                return False

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
        category: str = "default",
        badge: int = 1
    ) -> bool:
        """Send push notification to user's devices"""
        if not self.apns_client:
            logger.error("APNs client not initialized. Cannot send push notification.")
            return False

        try:
            # Get all device tokens for the user
            query = select(DeviceToken).where(DeviceToken.user_id == user_id)
            result = await db.execute(query)
            device_tokens = result.scalars().all()

            if not device_tokens:
                logger.warning(f"No device tokens found for user {user_id}")
                return False

            # Prepare notification payload
            alert = {
                'title': title,
                'body': body
            }

            payload = Payload(
                alert=alert,
                sound='default',
                badge=badge,
                category=category
            )

            if data:
                payload.custom = data

            topic = os.environ.get('APNS_TOPIC', 'com.alimkhan-yergebayev.adet')

            # Send to all user's devices
            success_count = 0
            for device_token in device_tokens:
                try:
                    response = self.apns_client.send_notification(
                        device_token.device_token,
                        payload,
                        topic
                    )

                    if response.is_successful:
                        success_count += 1
                        logger.info(f"Push notification sent successfully to device {device_token.device_token}")
                    else:
                        logger.error(f"Failed to send push notification to device {device_token.device_token}: {response.description}")

                        # If token is invalid, remove it
                        if response.status_code == 410:  # Unregistered
                            await self.unregister_device_token(db, user_id, device_token.device_token)

                except Exception as e:
                    logger.error(f"Error sending push notification to device {device_token.device_token}: {e}")

            return success_count > 0

        except Exception as e:
            logger.error(f"Failed to send push notification: {e}")
            return False