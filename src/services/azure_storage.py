import os
import uuid
from typing import Optional
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import AzureError
import logging

logger = logging.getLogger(__name__)

class AzureStorageService:
    """Service for handling file uploads to Azure Blob Storage"""

    def __init__(self):
        self.connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        self.container_name = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "profile-images")
        self.blob_service_client = None

        if self.connection_string:
            try:
                self.blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)
                self._ensure_container_exists()
            except Exception as e:
                logger.warning(f"Failed to initialize Azure Blob Storage: {e}")

    def _ensure_container_exists(self):
        """Ensure the container exists, create if it doesn't"""
        try:
            container_client = self.blob_service_client.get_container_client(self.container_name)
            if not container_client.exists():
                container_client.create_container(public_access="blob")
                logger.info(f"Created Azure container: {self.container_name}")
        except Exception as e:
            logger.error(f"Failed to ensure container exists: {e}")

    def is_available(self) -> bool:
        """Check if Azure Storage is properly configured"""
        return self.blob_service_client is not None

    async def upload_file(self, file_data: bytes, file_name: str, content_type: str) -> Optional[str]:
        """
        Upload file to Azure Blob Storage

        Args:
            file_data: The file content as bytes
            file_name: Original filename (will be made unique)
            content_type: MIME type of the file

        Returns:
            The public URL of the uploaded file, or None if upload failed
        """
        if not self.is_available():
            logger.error("Azure Storage not available")
            return None

        try:
            # Generate unique filename
            file_extension = file_name.split('.')[-1] if '.' in file_name else 'jpg'
            unique_filename = f"profile_{uuid.uuid4()}.{file_extension}"

            # Upload to Azure
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=unique_filename
            )

            blob_client.upload_blob(
                file_data,
                content_type=content_type,
                overwrite=True
            )

            # Return the public URL
            blob_url = blob_client.url
            logger.info(f"Successfully uploaded file to Azure: {blob_url}")
            return blob_url

        except AzureError as e:
            logger.error(f"Azure upload error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected upload error: {e}")
            return None

    async def delete_file(self, file_url: str) -> bool:
        """
        Delete file from Azure Blob Storage

        Args:
            file_url: The full URL of the file to delete

        Returns:
            True if deletion was successful, False otherwise
        """
        if not self.is_available():
            return False

        try:
            # Extract blob name from URL
            blob_name = file_url.split('/')[-1]

            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )

            blob_client.delete_blob()
            logger.info(f"Successfully deleted file from Azure: {blob_name}")
            return True

        except AzureError as e:
            logger.error(f"Azure deletion error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected deletion error: {e}")
            return False

# Global instance
azure_storage = AzureStorageService()

