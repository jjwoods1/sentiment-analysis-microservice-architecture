import json
import io
from typing import Optional
from minio import Minio
from minio.error import S3Error
from .config import settings


class StorageManager:
    """Manages MinIO object storage operations."""

    def __init__(self):
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """Ensure the storage bucket exists, create if not."""
        try:
            if not self.client.bucket_exists(settings.MINIO_BUCKET):
                self.client.make_bucket(settings.MINIO_BUCKET)
                print(f"Created bucket: {settings.MINIO_BUCKET}")
        except S3Error as e:
            print(f"Error ensuring bucket exists: {e}")

    def upload_json(self, object_path: str, data: dict) -> str:
        """
        Upload JSON data to storage.

        Args:
            object_path: Path in bucket (e.g., "transcripts/job-id/left.json")
            data: Dictionary to store as JSON

        Returns:
            Full path to stored object
        """
        json_data = json.dumps(data, indent=2)
        json_bytes = json_data.encode('utf-8')

        self.client.put_object(
            settings.MINIO_BUCKET,
            object_path,
            data=io.BytesIO(json_bytes),
            length=len(json_bytes),
            content_type='application/json'
        )

        return f"{settings.MINIO_BUCKET}/{object_path}"

    def download_json(self, object_path: str) -> Optional[dict]:
        """
        Download and parse JSON from storage.

        Args:
            object_path: Path in bucket

        Returns:
            Parsed JSON as dictionary, or None if not found
        """
        try:
            response = self.client.get_object(settings.MINIO_BUCKET, object_path)
            data = response.read()
            return json.loads(data.decode('utf-8'))
        except S3Error as e:
            if e.code == 'NoSuchKey':
                return None
            raise
        finally:
            if 'response' in locals():
                response.close()
                response.release_conn()

    def get_presigned_url(self, object_path: str, expires_seconds: int = 3600) -> str:
        """
        Generate a presigned URL for direct download.

        Args:
            object_path: Path in bucket
            expires_seconds: URL expiration time in seconds (default 1 hour)

        Returns:
            Presigned URL
        """
        from datetime import timedelta
        url = self.client.presigned_get_object(
            settings.MINIO_BUCKET,
            object_path,
            expires=timedelta(seconds=expires_seconds)
        )
        return url

    def delete_object(self, object_path: str) -> bool:
        """
        Delete an object from storage.

        Args:
            object_path: Path in bucket

        Returns:
            True if successful
        """
        try:
            self.client.remove_object(settings.MINIO_BUCKET, object_path)
            return True
        except S3Error:
            return False

    def list_objects(self, prefix: str = "") -> list:
        """
        List objects in storage with optional prefix.

        Args:
            prefix: Filter by prefix (e.g., "transcripts/job-id/")

        Returns:
            List of object names
        """
        try:
            objects = self.client.list_objects(
                settings.MINIO_BUCKET,
                prefix=prefix,
                recursive=True
            )
            return [obj.object_name for obj in objects]
        except S3Error:
            return []

    def object_exists(self, object_path: str) -> bool:
        """
        Check if an object exists in storage.

        Args:
            object_path: Path in bucket

        Returns:
            True if object exists
        """
        try:
            self.client.stat_object(settings.MINIO_BUCKET, object_path)
            return True
        except S3Error:
            return False


# Global storage manager instance
storage_manager = StorageManager()
