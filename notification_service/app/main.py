from fastapi import FastAPI, HTTPException
from typing import List
import asyncio
from datetime import datetime
import uuid
import logging

from . import schemas
from .config import settings
from .notifiers import EmailNotifier, WebhookNotifier, SlackNotifier

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Notification Service API",
    description="Microservice for sending error and status notifications via multiple channels",
    version="1.0.0"
)

# In-memory notification history (in production, use a database)
notification_history = []


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Notification Service",
        "enabled_channels": {
            "email": settings.ENABLE_EMAIL,
            "webhook": settings.ENABLE_WEBHOOK,
            "slack": settings.ENABLE_SLACK
        }
    }


@app.post("/notify", response_model=schemas.NotificationResponse)
async def send_notification(request: schemas.NotificationRequest):
    """
    Send a notification via configured channels.

    Supports:
    - Email (SMTP)
    - Webhook (HTTP POST)
    - Slack (Incoming Webhook)
    """
    channels_sent = []
    channels_failed = []
    details = {}

    # Determine which channels to use
    if request.channels:
        # Use specified channels
        use_channels = request.channels
    else:
        # Use all enabled channels
        use_channels = []
        if settings.ENABLE_EMAIL:
            use_channels.append(schemas.NotificationChannel.EMAIL)
        if settings.ENABLE_WEBHOOK:
            use_channels.append(schemas.NotificationChannel.WEBHOOK)
        if settings.ENABLE_SLACK:
            use_channels.append(schemas.NotificationChannel.SLACK)

    # Send to each channel with retry logic
    for channel in use_channels:
        result = await _send_with_retry(channel, request)

        if result["success"]:
            channels_sent.append(channel.value)
        else:
            channels_failed.append(channel.value)

        details[channel.value] = result

    # Save to history
    history_entry = {
        "id": str(uuid.uuid4()),
        "type": request.type,
        "severity": request.severity,
        "title": request.title,
        "message": request.message,
        "job_id": request.job_id,
        "channels_sent": channels_sent,
        "created_at": datetime.utcnow(),
        "success": len(channels_failed) == 0
    }
    notification_history.append(history_entry)

    # Keep only last 1000 notifications in memory
    if len(notification_history) > 1000:
        notification_history.pop(0)

    success = len(channels_sent) > 0

    return schemas.NotificationResponse(
        success=success,
        message=f"Notification sent to {len(channels_sent)} channel(s)" if success else "Failed to send notification",
        channels_sent=channels_sent,
        channels_failed=channels_failed,
        details=details
    )


async def _send_with_retry(channel: schemas.NotificationChannel, request: schemas.NotificationRequest) -> dict:
    """Send notification with retry logic."""
    for attempt in range(settings.NOTIFICATION_MAX_RETRIES):
        try:
            if channel == schemas.NotificationChannel.EMAIL:
                result = await EmailNotifier.send(request)
            elif channel == schemas.NotificationChannel.WEBHOOK:
                result = await WebhookNotifier.send(request)
            elif channel == schemas.NotificationChannel.SLACK:
                result = await SlackNotifier.send(request)
            else:
                result = {"success": False, "error": f"Unknown channel: {channel}"}

            if result["success"]:
                return result

            # If failed and not last attempt, wait before retry
            if attempt < settings.NOTIFICATION_MAX_RETRIES - 1:
                await asyncio.sleep(settings.NOTIFICATION_RETRY_DELAY * (2 ** attempt))

        except Exception as e:
            result = {"success": False, "error": str(e)}
            if attempt < settings.NOTIFICATION_MAX_RETRIES - 1:
                await asyncio.sleep(settings.NOTIFICATION_RETRY_DELAY * (2 ** attempt))

    return result


@app.post("/notify/job-failed")
async def notify_job_failed(
    job_id: str,
    filename: str,
    error_message: str,
    stack_trace: str = None
):
    """
    Convenience endpoint for job failure notifications.
    """
    if not settings.NOTIFY_ON_JOB_FAILURE:
        return {"message": "Job failure notifications are disabled"}

    request = schemas.NotificationRequest(
        type=schemas.NotificationType.JOB_FAILED,
        severity=schemas.NotificationSeverity.ERROR,
        title=f"Job Failed: {filename}",
        message=f"Audio processing job {job_id} has failed.",
        job_id=job_id,
        job_filename=filename,
        error_message=error_message,
        stack_trace=stack_trace
    )

    return await send_notification(request)


@app.post("/notify/job-completed")
async def notify_job_completed(
    job_id: str,
    filename: str,
    competitors_found: int = 0
):
    """
    Convenience endpoint for job completion notifications.
    """
    if not settings.NOTIFY_ON_JOB_SUCCESS:
        return {"message": "Job completion notifications are disabled"}

    request = schemas.NotificationRequest(
        type=schemas.NotificationType.JOB_COMPLETED,
        severity=schemas.NotificationSeverity.INFO,
        title=f"Job Completed: {filename}",
        message=f"Audio processing job {job_id} completed successfully. Found {competitors_found} competitor(s).",
        job_id=job_id,
        job_filename=filename,
        metadata={"competitors_found": competitors_found}
    )

    return await send_notification(request)


@app.post("/notify/task-failed")
async def notify_task_failed(
    task_name: str,
    job_id: str = None,
    error_message: str = "",
    stack_trace: str = None
):
    """
    Convenience endpoint for task failure notifications.
    """
    if not settings.NOTIFY_ON_TASK_FAILURE:
        return {"message": "Task failure notifications are disabled"}

    request = schemas.NotificationRequest(
        type=schemas.NotificationType.TASK_FAILED,
        severity=schemas.NotificationSeverity.WARNING,
        title=f"Task Failed: {task_name}",
        message=f"Background task '{task_name}' failed.",
        job_id=job_id,
        error_message=error_message,
        stack_trace=stack_trace
    )

    return await send_notification(request)


@app.post("/notify/system-error")
async def notify_system_error(
    title: str,
    message: str,
    error_message: str = None,
    stack_trace: str = None
):
    """
    Convenience endpoint for system error notifications.
    """
    if not settings.NOTIFY_ON_SYSTEM_ERROR:
        return {"message": "System error notifications are disabled"}

    request = schemas.NotificationRequest(
        type=schemas.NotificationType.SYSTEM_ERROR,
        severity=schemas.NotificationSeverity.CRITICAL,
        title=title,
        message=message,
        error_message=error_message,
        stack_trace=stack_trace
    )

    return await send_notification(request)


@app.get("/history", response_model=List[schemas.NotificationHistory])
async def get_notification_history(limit: int = 100):
    """
    Get recent notification history.
    """
    return notification_history[-limit:]


@app.get("/config")
async def get_config():
    """
    Get current notification configuration (sanitized).
    """
    return {
        "enabled_channels": {
            "email": settings.ENABLE_EMAIL,
            "webhook": settings.ENABLE_WEBHOOK,
            "slack": settings.ENABLE_SLACK
        },
        "notification_settings": {
            "notify_on_job_failure": settings.NOTIFY_ON_JOB_FAILURE,
            "notify_on_job_success": settings.NOTIFY_ON_JOB_SUCCESS,
            "notify_on_task_failure": settings.NOTIFY_ON_TASK_FAILURE,
            "notify_on_system_error": settings.NOTIFY_ON_SYSTEM_ERROR
        },
        "email_configured": bool(settings.SMTP_HOST and settings.SMTP_USERNAME),
        "email_recipients": len(settings.get_email_list()),
        "webhook_configured": bool(settings.WEBHOOK_URL),
        "slack_configured": bool(settings.SLACK_WEBHOOK_URL),
        "retry_settings": {
            "max_retries": settings.NOTIFICATION_MAX_RETRIES,
            "retry_delay_seconds": settings.NOTIFICATION_RETRY_DELAY
        }
    }


@app.get("/health")
async def health_check():
    """
    Comprehensive health check.
    """
    enabled_channels = [
        channel for channel, enabled in {
            "email": settings.ENABLE_EMAIL,
            "webhook": settings.ENABLE_WEBHOOK,
            "slack": settings.ENABLE_SLACK
        }.items() if enabled
    ]

    logger.info(f"Health check: Notification service is healthy with {len(enabled_channels)} channels enabled")
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "notification-api",
        "enabled_channels": enabled_channels,
        "notifications_sent": len(notification_history)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
