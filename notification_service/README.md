# Notification Service

Multi-channel notification system for sending error alerts and system notifications.

## Overview

The Notification Service provides a centralized notification system that supports multiple channels (Email, Webhook, Slack) with automatic retry logic and flexible configuration.

## Features

- **Multiple Channels**: Email (SMTP), Webhooks, Slack
- **Auto-Retry**: Configurable retry logic with exponential backoff
- **Rich Notifications**: HTML emails with job context and stack traces
- **Flexible Configuration**: Enable/disable channels and notification triggers
- **Non-Blocking**: Notification failures don't affect main workflow
- **History Tracking**: In-memory notification history

## Supported Channels

### 1. Email (SMTP)
- HTML and plain text emails
- Hostinger SMTP pre-configured
- Color-coded severity levels
- Stack trace support
- Multiple recipients

### 2. Webhook
- HTTP POST with JSON payload
- Optional webhook secret for authentication
- Retry logic built-in

### 3. Slack
- Incoming webhook support
- Block Kit formatting
- Severity-based colors and emojis

## Configuration

### Email Setup (Hostinger)
```env
ENABLE_EMAIL=true
SMTP_HOST=smtp.hostinger.com
SMTP_PORT=465
SMTP_USERNAME=your-email@yourdomain.com
SMTP_PASSWORD=your-password
SMTP_FROM_EMAIL=your-email@yourdomain.com
SMTP_FROM_NAME=Audio Processing System
SMTP_USE_TLS=true
NOTIFICATION_EMAILS=admin@yourdomain.com,dev@yourdomain.com
```

### Webhook Setup
```env
ENABLE_WEBHOOK=true
WEBHOOK_URL=https://your-webhook-endpoint.com/notifications
WEBHOOK_SECRET=your-secret-key
```

### Slack Setup
```env
ENABLE_SLACK=true
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### Notification Triggers
```env
NOTIFY_ON_JOB_FAILURE=true
NOTIFY_ON_JOB_SUCCESS=false
NOTIFY_ON_TASK_FAILURE=true
NOTIFY_ON_SYSTEM_ERROR=true
```

### Retry Settings
```env
NOTIFICATION_MAX_RETRIES=3
NOTIFICATION_RETRY_DELAY=5
```

## API Endpoints

### Send Generic Notification
```http
POST /notify
Content-Type: application/json

{
  "type": "job_failed",
  "severity": "error",
  "title": "Job Processing Failed",
  "message": "Audio processing job encountered an error",
  "job_id": "uuid",
  "job_filename": "audio.mp3",
  "error_message": "Transcription service timeout",
  "stack_trace": "...",
  "channels": ["email", "slack"]
}
```

### Convenience Endpoints

#### Job Failed
```http
POST /notify/job-failed
{
  "job_id": "uuid",
  "filename": "audio.mp3",
  "error_message": "Error details",
  "stack_trace": "..."
}
```

#### Job Completed
```http
POST /notify/job-completed
{
  "job_id": "uuid",
  "filename": "audio.mp3",
  "competitors_found": 3
}
```

#### Task Failed
```http
POST /notify/task-failed
{
  "task_name": "transcribe_audio",
  "job_id": "uuid",
  "error_message": "Error details",
  "stack_trace": "..."
}
```

#### System Error
```http
POST /notify/system-error
{
  "title": "Database Connection Lost",
  "message": "Critical system error occurred",
  "error_message": "Error details",
  "stack_trace": "..."
}
```

### Get Notification History
```http
GET /history?limit=100
```

### Get Configuration
```http
GET /config
```

### Health Check
```http
GET /health
```

## Notification Types

- `job_failed`: Job processing failures
- `job_completed`: Successful job completions
- `task_failed`: Individual task failures
- `system_error`: Critical system errors
- `custom`: Custom notifications

## Severity Levels

- `info`: Informational messages (blue)
- `warning`: Warning messages (yellow)
- `error`: Error messages (red)
- `critical`: Critical errors (dark red)

## Email Template

HTML emails include:
- Color-coded header based on severity
- Job ID and filename
- Error message in highlighted box
- Collapsible stack trace
- Additional metadata
- Professional footer

## Integration

The notification service is automatically integrated into all Celery tasks in the orchestrator service. Notifications are sent when:

- Transcription fails after 3 retries
- Competitor analysis fails
- Sentiment analysis fails
- Job finalization fails
- Pipeline initialization fails

## Testing

```bash
# Test email notification
curl -X POST http://localhost:8003/notify/job-failed \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "test-123",
    "filename": "test.mp3",
    "error_message": "Test error",
    "stack_trace": "Test stack trace"
  }'
```

## Running Locally

```bash
cd notification_service
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8003
```

## API Documentation

Visit http://localhost:8003/docs for interactive API documentation.

## Production Considerations

1. **Email Deliverability**: Configure SPF, DKIM, and DMARC records
2. **Rate Limiting**: Consider rate limits on notification channels
3. **Database**: Replace in-memory history with persistent storage
4. **Monitoring**: Monitor notification delivery success rates
5. **Security**: Rotate webhook secrets regularly
6. **Privacy**: Sanitize sensitive data in notifications
