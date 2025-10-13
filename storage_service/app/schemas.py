from pydantic import BaseModel, Field
from typing import Optional, List, Any


class UploadRequest(BaseModel):
    """Request schema for uploading JSON data."""
    object_path: str = Field(..., description="Path in storage bucket (e.g., 'transcripts/job-id/left.json')")
    data: dict = Field(..., description="JSON data to store")


class UploadResponse(BaseModel):
    """Response schema for upload operations."""
    success: bool
    object_path: str
    full_path: str
    message: str


class DownloadResponse(BaseModel):
    """Response schema for download operations."""
    success: bool
    object_path: str
    data: Optional[dict] = None
    message: str


class PresignedUrlResponse(BaseModel):
    """Response schema for presigned URL generation."""
    success: bool
    object_path: str
    url: str
    expires_in_seconds: int


class DeleteResponse(BaseModel):
    """Response schema for delete operations."""
    success: bool
    object_path: str
    message: str


class ListResponse(BaseModel):
    """Response schema for listing objects."""
    success: bool
    prefix: str
    objects: List[str]
    count: int


class ExistsResponse(BaseModel):
    """Response schema for existence check."""
    exists: bool
    object_path: str
