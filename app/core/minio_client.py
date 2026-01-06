from minio import Minio
from minio.error import S3Error
from app.core.config import settings
import logging
from typing import Optional
from io import BytesIO

logger = logging.getLogger(__name__)


class MinIOClient:
    def __init__(self):
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )
        self.bucket = settings.MINIO_BUCKET
        self._ensure_bucket()
    
    def _ensure_bucket(self):
        """Ensure bucket exists"""
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
                logger.info(f"Created MinIO bucket: {self.bucket}")
        except S3Error as e:
            logger.error(f"Error ensuring bucket exists: {e}")
    
    def upload_file(self, object_name: str, file_path: str, content_type: Optional[str] = None) -> bool:
        """Upload file from path"""
        try:
            self.client.fput_object(
                self.bucket,
                object_name,
                file_path,
                content_type=content_type
            )
            logger.info(f"Uploaded file to MinIO: {object_name}")
            return True
        except S3Error as e:
            logger.error(f"Error uploading file to MinIO: {e}")
            return False
    
    def upload_data(self, object_name: str, data: bytes, content_type: Optional[str] = None) -> bool:
        """Upload data from bytes"""
        try:
            self.client.put_object(
                self.bucket,
                object_name,
                BytesIO(data),
                length=len(data),
                content_type=content_type
            )
            logger.info(f"Uploaded data to MinIO: {object_name}")
            return True
        except S3Error as e:
            logger.error(f"Error uploading data to MinIO: {e}")
            return False
    
    def get_object(self, object_name: str) -> Optional[bytes]:
        """Get object data"""
        try:
            response = self.client.get_object(self.bucket, object_name)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except S3Error as e:
            logger.error(f"Error getting object from MinIO: {e}")
            return None
    
    def get_presigned_url(self, object_name: str, expires_seconds: int = 3600) -> Optional[str]:
        """Get presigned URL for object"""
        try:
            from datetime import timedelta
            url = self.client.presigned_get_object(
                self.bucket,
                object_name,
                expires=timedelta(seconds=expires_seconds)
            )
            return url
        except S3Error as e:
            logger.error(f"Error generating presigned URL: {e}")
            return None
    
    def check_connection(self) -> bool:
        """Check if MinIO is accessible"""
        try:
            self.client.bucket_exists(self.bucket)
            return True
        except Exception as e:
            logger.error(f"MinIO connection check failed: {e}")
            return False


# Global MinIO client instance
minio_client = MinIOClient()
