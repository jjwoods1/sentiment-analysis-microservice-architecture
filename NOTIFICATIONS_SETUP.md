# Notification Service Setup Guide

Quick setup guide for configuring error notifications.

## Quick Setup (Email Only)

1. **Edit your `.env` file** and add:

```env
# Email Notifications (Hostinger)
ENABLE_EMAIL=true
SMTP_HOST=smtp.hostinger.com
SMTP_PORT=465
SMTP_USERNAME=your-email@yourdomain.com
SMTP_PASSWORD=your-email-password
SMTP_FROM_EMAIL=your-email@yourdomain.com
SMTP_FROM_NAME=Audio Processing System
SMTP_USE_TLS=true

# Who gets notified (comma-separated)
NOTIFICATION_EMAILS=admin@yourdomain.com,dev@yourdomain.com

# What triggers notifications
NOTIFY_ON_JOB_FAILURE=true
NOTIFY_ON_JOB_SUCCESS=false
NOTIFY_ON_TASK_FAILURE=true
NOTIFY_ON_SYSTEM_ERROR=true
```

2. **Restart services**:
```bash
docker-compose restart orchestrator-api worker notification-api
```

3. **Test it**:
```bash
curl -X POST http://localhost:8003/notify/job-failed \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "test-123",
    "filename": "test.mp3",
    "error_message": "Test notification",
    "stack_trace": "This is a test"
  }'
```

Check your email!

## What You'll Receive

When a job fails, you'll get an email with:
- **Subject**: `[ERROR] Job Failed: filename.mp3`
- **Color-coded header**: Red for errors, yellow for warnings
- **Job details**: ID, filename, status
- **Error message**: Highlighted in a box
- **Stack trace**: Collapsible section
- **Timestamp**: When the error occurred

## Optional: Add Webhook Notifications

```env
ENABLE_WEBHOOK=true
WEBHOOK_URL=https://your-endpoint.com/notifications
WEBHOOK_SECRET=your-secret-key
```

The webhook will receive:
```json
{
  "type": "job_failed",
  "severity": "error",
  "title": "Job Failed: audio.mp3",
  "message": "Audio processing job failed",
  "job_id": "uuid",
  "job_filename": "audio.mp3",
  "error_message": "Transcription timeout",
  "stack_trace": "...",
  "timestamp": "2025-01-15T12:00:00Z"
}
```

## Optional: Add Slack Notifications

1. Create a Slack Incoming Webhook:
   - Go to https://api.slack.com/messaging/webhooks
   - Create a new webhook for your channel
   - Copy the webhook URL

2. Add to `.env`:
```env
ENABLE_SLACK=true
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

## Notification Triggers

Control what events send notifications:

```env
# Get notified when jobs fail (recommended)
NOTIFY_ON_JOB_FAILURE=true

# Get notified when jobs complete successfully
NOTIFY_ON_JOB_SUCCESS=false

# Get notified when individual tasks fail
NOTIFY_ON_TASK_FAILURE=true

# Get notified about critical system errors
NOTIFY_ON_SYSTEM_ERROR=true
```

## When Notifications Are Sent

Automatic notifications are sent for:

1. **Job Failures**:
   - Transcription fails after 3 retries
   - Competitor analysis fails
   - Pipeline initialization fails

2. **Task Failures**:
   - Individual transcription channel fails
   - Sentiment analysis fails

3. **System Errors**:
   - Database connection issues
   - External service unavailable

## Disable Notifications

To disable all notifications:
```env
ENABLE_EMAIL=false
ENABLE_WEBHOOK=false
ENABLE_SLACK=false
```

Or disable specific triggers:
```env
NOTIFY_ON_JOB_FAILURE=false
NOTIFY_ON_TASK_FAILURE=false
```

## Troubleshooting

### Not receiving emails?

1. **Check SMTP credentials**:
```bash
docker-compose logs notification-api | grep -i "email"
```

2. **Test SMTP connection** from container:
```bash
docker-compose exec notification-api python -c "
import aiosmtplib
import asyncio
from email.mime.text import MIMEText

async def test():
    msg = MIMEText('Test')
    msg['Subject'] = 'Test'
    msg['From'] = 'your-email@yourdomain.com'
    msg['To'] = 'test@example.com'

    await aiosmtplib.send(
        msg,
        hostname='smtp.hostinger.com',
        port=465,
        username='your-email@yourdomain.com',
        password='your-password',
        use_tls=True
    )
    print('Success!')

asyncio.run(test())
"
```

3. **Check spam folder**

4. **Verify firewall** allows outbound SMTP (port 465)

### View notification history

```bash
curl http://localhost:8003/history?limit=50
```

### Check configuration

```bash
curl http://localhost:8003/config
```

## Security Best Practices

1. **Use strong passwords** for SMTP
2. **Rotate webhook secrets** regularly
3. **Don't commit** .env file to git
4. **Sanitize sensitive data** in error messages
5. **Use app-specific passwords** for email accounts
6. **Restrict notification recipients** to authorized personnel

## Production Recommendations

1. **Use a dedicated email account** for notifications
2. **Set up email authentication** (SPF, DKIM, DMARC)
3. **Monitor notification delivery rates**
4. **Configure rate limiting** to avoid spam
5. **Use a transactional email service** (SendGrid, AWS SES) for reliability
6. **Implement notification digest** for high-volume systems
7. **Add PagerDuty/OpsGenie** for critical alerts

## Support

For issues:
- Check logs: `docker-compose logs notification-api`
- View API docs: http://localhost:8003/docs
- Test endpoint: http://localhost:8003/health
