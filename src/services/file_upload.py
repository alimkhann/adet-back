"""
File Upload Service for Proof Submissions

Handles uploading proof files (photos, videos, audio) to Azure Blob Storage
and provides secure URLs for access.
"""

import os
import uuid
import logging
import mimetypes
from typing import Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path

try:
    from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
    from azure.core.exceptions import AzureError
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Azure Blob Storage dependencies not installed. File upload will use local storage.")

import aiofiles

logger = logging.getLogger(__name__)

class FileUploadService:
    def __init__(self):
        # Get Azure storage credentials from environment
        self.account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
        self.account_key = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")
        self.pfp_container_name = os.getenv("AZURE_STORAGE_PFP_CONTAINER_NAME", "profile-images")
        self.proof_container_name = os.getenv("AZURE_STORAGE_PROOF_CONTAINER_NAME", "proof-posts")

        if not AZURE_AVAILABLE or not self.account_name or not self.account_key:
            if not AZURE_AVAILABLE:
                logger.warning("Azure Blob Storage not available. Using local file storage.")
            else:
                logger.warning("Azure storage credentials not found. Using local file storage.")
            self.blob_service_client = None
        else:
            try:
                connection_string = f"DefaultEndpointsProtocol=https;AccountName={self.account_name};AccountKey={self.account_key};EndpointSuffix=core.windows.net"
                self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
                # Ensure both containers exist
                self._ensure_container_exists(self.pfp_container_name)
                self._ensure_container_exists(self.proof_container_name)
                logger.info(f"Azure Blob Storage initialized for containers: {self.pfp_container_name}, {self.proof_container_name}")
            except Exception as e:
                logger.error(f"Failed to initialize Azure Blob Storage: {e}")
                self.blob_service_client = None

    def _ensure_container_exists(self, container_name):
        """Ensure the blob container exists"""
        if not self.blob_service_client:
            return
        try:
            container_client = self.blob_service_client.get_container_client(container_name)
            if not container_client.exists():
                container_client.create_container()
                logger.info(f"Created container: {container_name}")
        except Exception as e:
            logger.error(f"Error ensuring container exists: {e}")

    def _generate_blob_name(self, user_id: str, task_id: int, file_extension: str) -> str:
        """Generate a unique blob name for the file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"proofs/{user_id}/{task_id}/{timestamp}_{unique_id}.{file_extension}"

    def _generate_pfp_blob_name(self, user_id: str, file_extension: str) -> str:
        """Generate a unique blob name for a profile image"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"{user_id}/{timestamp}_{unique_id}.{file_extension}"

    def _get_file_extension(self, filename: str, content_type: str) -> str:
        """Get file extension from filename or content type"""
        if filename and '.' in filename:
            return filename.split('.')[-1].lower()

        # Fallback to content type
        extension_map = {
            'image/jpeg': 'jpg',
            'image/png': 'png',
            'image/gif': 'gif',
            'image/webp': 'webp',
            'video/mp4': 'mp4',
            'video/quicktime': 'mov',
            'video/x-msvideo': 'avi',
            'audio/mpeg': 'mp3',
            'audio/wav': 'wav',
            'audio/aac': 'aac',
            'audio/ogg': 'ogg',
            'text/plain': 'txt'
        }

        return extension_map.get(content_type, 'bin')

    async def upload_proof_file(
        self,
        file_data: bytes,
        filename: str,
        content_type: str,
        user_id: str,
        task_id: int,
        container: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Upload a proof file to Azure Blob Storage or local storage
        Args:
            file_data: Raw file data
            filename: Original filename
            content_type: MIME type of the file
            user_id: User ID (for organizing files)
            task_id: Task ID (for organizing files)
            container: Which container to use (proof or pfp)
        Returns:
            Tuple of (success, file_url, error_message)
        """
        try:
            # Validate file size (max 50MB)
            max_size = 50 * 1024 * 1024  # 50MB
            if len(file_data) > max_size:
                return False, None, f"File too large. Maximum size is {max_size // 1024 // 1024}MB"

            # Validate file type
            allowed_types = [
                'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp',
                'video/mp4', 'video/quicktime', 'video/x-msvideo',
                'audio/mpeg', 'audio/wav', 'audio/aac', 'audio/ogg',
                'text/plain'
            ]

            if content_type not in allowed_types:
                return False, None, f"File type {content_type} not allowed"

            # Try Azure first, fallback to local storage
            if self.blob_service_client:
                use_container = container or self.proof_container_name
                return await self._upload_to_azure(file_data, filename, content_type, user_id, task_id, use_container)
            else:
                return await self._save_local_file(file_data, filename, user_id, task_id)

        except Exception as e:
            logger.error(f"Unexpected error uploading file: {e}")
            return False, None, f"Upload error: {str(e)}"

    async def upload_pfp_file(
        self,
        file_data: bytes,
        filename: str,
        content_type: str,
        user_id: str
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Upload a profile image to Azure Blob Storage or local storage
        """
        file_extension = self._get_file_extension(filename, content_type)
        blob_name = self._generate_pfp_blob_name(user_id, file_extension)
        if self.blob_service_client:
            return await self._upload_to_azure(
                file_data, filename, content_type, user_id, task_id=0, container=self.pfp_container_name, blob_name=blob_name
            )
        else:
            # Save locally in uploads/profile-images/{user_id}/
            upload_dir = Path("uploads/profile-images") / user_id
            upload_dir.mkdir(parents=True, exist_ok=True)
            file_path = upload_dir / blob_name.split("/")[-1]
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(file_data)
            local_url = f"/uploads/profile-images/{user_id}/{blob_name.split('/')[-1]}"
            return True, local_url, None

    async def _upload_to_azure(
        self,
        file_data: bytes,
        filename: str,
        content_type: str,
        user_id: str,
        task_id: int,
        container: str,
        blob_name: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Upload file to Azure Blob Storage"""
        try:
            file_extension = self._get_file_extension(filename, content_type)
            if not blob_name:
                blob_name = self._generate_blob_name(user_id, task_id, file_extension)
            blob_client = self.blob_service_client.get_blob_client(
                container=container,
                blob=blob_name
            )
            blob_client.upload_blob(
                file_data,
                content_type=content_type,
                overwrite=True,
                metadata={
                    'user_id': user_id,
                    'task_id': str(task_id),
                    'original_filename': filename,
                    'upload_time': datetime.now().isoformat()
                }
            )
            blob_url = blob_client.url
            logger.info(f"Successfully uploaded file to Azure for user {user_id}, task {task_id}: {blob_name} in container {container}")
            return True, blob_url, None
        except Exception as e:
            logger.error(f"Azure error uploading file: {e}")
            return await self._save_local_file(file_data, filename, user_id, task_id)

    async def _save_local_file(
        self,
        file_data: bytes,
        filename: str,
        user_id: str,
        task_id: int
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Save file locally (fallback when Azure is not available)"""
        try:
            # Create upload directory
            upload_dir = Path("uploads/proofs") / user_id / str(task_id)
            upload_dir.mkdir(parents=True, exist_ok=True)

            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            file_extension = filename.split('.')[-1] if '.' in filename else 'bin'
            new_filename = f"{timestamp}_{unique_id}.{file_extension}"

            file_path = upload_dir / new_filename

            # Save file
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(file_data)

            # Create a local URL (you might want to serve this via your web server)
            local_url = f"/uploads/proofs/{user_id}/{task_id}/{new_filename}"

            logger.info(f"Saved file locally: {file_path}")
            return True, local_url, None

        except Exception as e:
            logger.error(f"Error saving file locally: {e}")
            return False, None, str(e)

    def generate_signed_url(self, blob_url: str, container: Optional[str] = None, expiry_hours: Optional[int] = 24) -> Optional[str]:
        """Generate a signed URL for secure access to a blob. If expiry_hours=None, generate a non-expiring SAS (for permanent private access)."""
        if not self.blob_service_client or not AZURE_AVAILABLE:
            return blob_url  # Return original URL if no Azure client
        try:
            # Extract blob name from URL
            if not container:
                # Try to infer container from URL
                if self.pfp_container_name in blob_url:
                    container = self.pfp_container_name
                else:
                    container = self.proof_container_name
            blob_name = blob_url.split(f"{container}/")[-1]
            # Generate SAS token
            if expiry_hours is None:
                # Permanent SAS: set expiry far in the future (e.g. 100 years)
                expiry = datetime.utcnow() + timedelta(days=365*100)
            else:
                expiry = datetime.utcnow() + timedelta(hours=expiry_hours)
            sas_token = generate_blob_sas(
                account_name=self.account_name,
                container_name=container,
                blob_name=blob_name,
                account_key=self.account_key,
                permission=BlobSasPermissions(read=True),
                expiry=expiry
            )
            return f"{blob_url}?{sas_token}"
        except Exception as e:
            logger.error(f"Error generating signed URL: {e}")
            return blob_url  # Return original URL as fallback

    def generate_permanent_signed_url(self, blob_url: str, container: Optional[str] = None) -> Optional[str]:
        """Generate a non-expiring signed URL for a blob (for private proofs that should not expire)."""
        return self.generate_signed_url(blob_url, container=container, expiry_hours=None)

    async def delete_proof_file(self, blob_url: str, container: Optional[str] = None) -> bool:
        """
        Delete a proof file from Azure Blob Storage
        Args:
            blob_url: The blob URL to delete
            container: Which container to use
        Returns:
            True if deleted successfully, False otherwise
        """
        if not self.blob_service_client:
            return False
        try:
            if not container:
                if self.pfp_container_name in blob_url:
                    container = self.pfp_container_name
                else:
                    container = self.proof_container_name
            blob_name = blob_url.split(f"{container}/")[-1]
            blob_client = self.blob_service_client.get_blob_client(
                container=container,
                blob=blob_name
            )
            blob_client.delete_blob()
            logger.info(f"Successfully deleted blob: {blob_name} from container {container}")
            return True
        except Exception as e:
            logger.error(f"Error deleting blob: {e}")
            return False

# Global instance
file_upload_service = FileUploadService()