"""
Storage Service - Abstraction layer for file storage.
Supports both local storage (development) and Cloudflare R2 (production).
"""

import os
import asyncio
import logging
from typing import Optional
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class StorageService:
    """
    Unified storage service supporting local filesystem and Cloudflare R2.

    Environment variables for R2:
    - R2_ACCOUNT_ID: Cloudflare account ID
    - R2_ACCESS_KEY_ID: R2 access key
    - R2_SECRET_ACCESS_KEY: R2 secret key
    - R2_BUCKET_NAME: Bucket name (default: torched-workspace-images)
    - R2_PUBLIC_URL: Public URL for serving files (optional, for presigned URLs)
    - USE_R2_STORAGE: Set to "true" to enable R2 (default: false for local dev)
    """

    def __init__(self):
        self.use_r2 = os.getenv('USE_R2_STORAGE', 'false').lower() == 'true'
        self.bucket_name = os.getenv('R2_BUCKET_NAME', 'torched-workspace-images')
        self.local_base_path = os.getenv('LOCAL_STORAGE_PATH', 'static/document_images')

        if self.use_r2:
            self._init_r2_client()
        else:
            logger.info("Storage Service initialized with LOCAL storage")
            # Ensure local directory exists
            os.makedirs(self.local_base_path, exist_ok=True)

    def _init_r2_client(self):
        """Initialize the Cloudflare R2 client (S3-compatible)."""
        account_id = os.getenv('R2_ACCOUNT_ID')
        access_key = os.getenv('R2_ACCESS_KEY_ID')
        secret_key = os.getenv('R2_SECRET_ACCESS_KEY')

        if not all([account_id, access_key, secret_key]):
            raise ValueError(
                "R2 storage enabled but missing credentials. "
                "Set R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY"
            )

        self.r2_endpoint = f"https://{account_id}.r2.cloudflarestorage.com"
        self.r2_public_url = os.getenv('R2_PUBLIC_URL', '')

        self.s3_client = boto3.client(
            's3',
            endpoint_url=self.r2_endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(
                signature_version='s3v4',
                s3={'addressing_style': 'path'}
            ),
            region_name='auto'  # R2 requires 'auto' region
        )

        logger.info(f"Storage Service initialized with R2 storage (bucket: {self.bucket_name})")

    def _get_storage_key(self, document_id: str, filename: str) -> str:
        """Generate storage key/path for a file."""
        return f"documents/{document_id}/{filename}"

    async def save_image(
        self,
        document_id: str,
        image_data: bytes,
        filename: str,
        content_type: str = 'image/png'
    ) -> str:
        """
        Save an image to storage.

        Args:
            document_id: UUID of the document
            image_data: Binary image data
            filename: Filename for the image (e.g., "p1_i0_abc123.png")
            content_type: MIME type of the image

        Returns:
            Storage path/key that can be used to retrieve the image
        """
        storage_key = self._get_storage_key(document_id, filename)

        if self.use_r2:
            return await self._save_to_r2(storage_key, image_data, content_type)
        else:
            return await self._save_to_local(storage_key, image_data)

    async def _save_to_r2(
        self,
        key: str,
        data: bytes,
        content_type: str
    ) -> str:
        """Save data to Cloudflare R2."""
        try:
            await asyncio.to_thread(
                self.s3_client.put_object,
                Bucket=self.bucket_name,
                Key=key,
                Body=data,
                ContentType=content_type
            )
            logger.debug(f"Saved to R2: {key}")
            return key
        except ClientError as e:
            logger.error(f"Failed to save to R2: {e}")
            raise

    async def _save_to_local(self, key: str, data: bytes) -> str:
        """Save data to local filesystem."""
        file_path = os.path.join(self.local_base_path, key)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        import aiofiles
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(data)

        logger.debug(f"Saved to local: {file_path}")
        return file_path  # Return full path for local storage

    async def get_image(self, storage_path: str) -> Optional[bytes]:
        """
        Retrieve image data from storage.

        Args:
            storage_path: The path/key returned from save_image

        Returns:
            Binary image data or None if not found
        """
        if self.use_r2:
            return await self._get_from_r2(storage_path)
        else:
            return await self._get_from_local(storage_path)

    async def _get_from_r2(self, key: str) -> Optional[bytes]:
        """Retrieve data from Cloudflare R2."""
        try:
            response = await asyncio.to_thread(
                self.s3_client.get_object,
                Bucket=self.bucket_name,
                Key=key
            )
            return response['Body'].read()
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return None
            logger.error(f"Failed to get from R2: {e}")
            raise

    async def _get_from_local(self, path: str) -> Optional[bytes]:
        """Retrieve data from local filesystem."""
        if not os.path.exists(path):
            return None

        import aiofiles
        async with aiofiles.open(path, 'rb') as f:
            return await f.read()

    def generate_presigned_url(
        self,
        storage_path: str,
        expiration: int = 3600,
        for_upload: bool = False
    ) -> str:
        """
        Generate a presigned URL for accessing an image.

        For R2: Returns a signed URL that grants temporary access
        For Local: Returns the file path (or API endpoint path)

        Args:
            storage_path: The path/key returned from save_image
            expiration: URL expiration time in seconds (default: 1 hour)
            for_upload: If True, generate URL for PUT operation

        Returns:
            URL string for accessing the image
        """
        if self.use_r2:
            return self._generate_r2_presigned_url(storage_path, expiration, for_upload)
        else:
            # For local, return the API endpoint path
            return f"/api/files/images/local/{storage_path}"

    def _generate_r2_presigned_url(
        self,
        key: str,
        expiration: int,
        for_upload: bool
    ) -> str:
        """Generate presigned URL for R2."""
        try:
            method = 'put_object' if for_upload else 'get_object'
            url = self.s3_client.generate_presigned_url(
                method,
                Params={
                    'Bucket': self.bucket_name,
                    'Key': key
                },
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise

    async def delete_image(self, storage_path: str) -> bool:
        """
        Delete an image from storage.

        Args:
            storage_path: The path/key returned from save_image

        Returns:
            True if deletion was successful
        """
        if self.use_r2:
            return await self._delete_from_r2(storage_path)
        else:
            return await self._delete_from_local(storage_path)

    async def _delete_from_r2(self, key: str) -> bool:
        """Delete object from R2."""
        try:
            await asyncio.to_thread(
                self.s3_client.delete_object,
                Bucket=self.bucket_name,
                Key=key
            )
            logger.debug(f"Deleted from R2: {key}")
            return True
        except ClientError as e:
            logger.error(f"Failed to delete from R2: {e}")
            return False

    async def _delete_from_local(self, path: str) -> bool:
        """Delete file from local filesystem."""
        try:
            if os.path.exists(path):
                await asyncio.to_thread(os.remove, path)
                # Try to remove parent directory if empty
                parent_dir = os.path.dirname(path)
                if os.path.exists(parent_dir) and not os.listdir(parent_dir):
                    await asyncio.to_thread(os.rmdir, parent_dir)
                logger.debug(f"Deleted from local: {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete from local: {e}")
            return False

    async def delete_document_images(self, document_id: str) -> bool:
        """
        Delete all images for a document.

        Args:
            document_id: UUID of the document

        Returns:
            True if all deletions were successful
        """
        if self.use_r2:
            return await self._delete_r2_folder(f"documents/{document_id}/")
        else:
            return await self._delete_local_folder(document_id)

    async def _delete_r2_folder(self, prefix: str) -> bool:
        """Delete all objects with a given prefix from R2."""
        try:
            # List all objects with prefix
            response = await asyncio.to_thread(
                self.s3_client.list_objects_v2,
                Bucket=self.bucket_name,
                Prefix=prefix
            )

            objects = response.get('Contents', [])
            if not objects:
                return True

            # Delete objects in batches
            delete_objects = [{'Key': obj['Key']} for obj in objects]
            await asyncio.to_thread(
                self.s3_client.delete_objects,
                Bucket=self.bucket_name,
                Delete={'Objects': delete_objects}
            )

            logger.info(f"Deleted {len(delete_objects)} objects from R2 with prefix: {prefix}")
            return True
        except ClientError as e:
            logger.error(f"Failed to delete R2 folder: {e}")
            return False

    async def _delete_local_folder(self, document_id: str) -> bool:
        """Delete local folder for a document."""
        import shutil
        folder_path = os.path.join(self.local_base_path, "documents", document_id)
        try:
            if os.path.exists(folder_path):
                await asyncio.to_thread(shutil.rmtree, folder_path)
                logger.debug(f"Deleted local folder: {folder_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete local folder: {e}")
            return False

    def is_r2_enabled(self) -> bool:
        """Check if R2 storage is enabled."""
        return self.use_r2

    def get_storage_info(self) -> dict:
        """Get information about storage configuration."""
        if self.use_r2:
            return {
                'type': 'cloudflare_r2',
                'bucket': self.bucket_name,
                'endpoint': self.r2_endpoint
            }
        else:
            return {
                'type': 'local',
                'path': self.local_base_path
            }


# Global instance (singleton pattern)
_storage_service: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    """Get the global storage service instance."""
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service

