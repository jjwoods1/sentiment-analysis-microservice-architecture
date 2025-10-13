from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class NotificationSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class NotificationType(str, Enum):
    JOB_FAILED = "job_failed"
    JOB_COMPLETED = "job_completed"
    TASK_FAILED = "task_failed"
    SYSTEM_ERROR = "system_error"
    CUSTOM = "custom"


class NotificationChannel(str, Enum):
    EMAIL = "email"
    WEBHOOK = "webhook"
    SLACK = "slack"


class NotificationRequest(BaseModel):
    """Request to send a notification."""
    type: NotificationType
    severity: NotificationSeverity
    title: str
    message: str
    job_id: Optional[str] = None
    job_filename: Optional[str] = None
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    channels: Optional[List[NotificationChannel]] = None  # If None, use all enabled


class NotificationResponse(BaseModel):
    """Response from notification attempt."""
    success: bool
    message: str
    channels_sent: List[str]
    channels_failed: List[str]
    details: Dict[str, Any] = {}


class NotificationHistory(BaseModel):
    """Historical notification record."""
    id: str
    type: NotificationType
    severity: NotificationSeverity
    title: str
    message: str
    job_id: Optional[str]
    channels_sent: List[str]
    created_at: datetime
    success: bool
