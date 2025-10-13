from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime
from uuid import UUID
from .models import JobStatus


class SentimentResultSchema(BaseModel):
    id: UUID
    job_id: UUID
    competitor_name: str
    result_json: dict
    created_at: datetime

    class Config:
        from_attributes = True


class JobBase(BaseModel):
    filename: str


class JobCreate(JobBase):
    pass


class JobResponse(JobBase):
    id: UUID
    status: JobStatus
    error_message: Optional[str] = None
    left_channel_url: Optional[str] = None
    right_channel_url: Optional[str] = None
    left_transcript_path: Optional[str] = None
    right_transcript_path: Optional[str] = None
    competitors_found: Optional[List[str]] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    sentiment_results: List[SentimentResultSchema] = []

    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    total: int
    jobs: List[JobResponse]


class UploadResponse(BaseModel):
    job_id: UUID
    message: str
    status: JobStatus


class WebhookRequest(BaseModel):
    filename: str
    file_url: Optional[str] = None
