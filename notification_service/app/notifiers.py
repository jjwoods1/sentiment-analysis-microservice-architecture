import asyncio
import httpx
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional
from datetime import datetime
from jinja2 import Template

from .config import settings
from .schemas import NotificationRequest, NotificationSeverity


class EmailNotifier:
    """Send email notifications via SMTP."""

    @staticmethod
    async def send(notification: NotificationRequest) -> Dict[str, Any]:
        """Send email notification."""
        if not settings.ENABLE_EMAIL:
            return {"success": False, "error": "Email notifications disabled"}

        if not settings.SMTP_HOST or not settings.SMTP_USERNAME:
            return {"success": False, "error": "Email configuration missing"}

        recipients = settings.get_email_list()
        if not recipients:
            return {"success": False, "error": "No email recipients configured"}

        try:
            # Create email message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[{notification.severity.upper()}] {notification.title}"
            msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
            msg["To"] = ", ".join(recipients)

            # Create HTML body
            html_body = EmailNotifier._create_html_body(notification)
            text_body = EmailNotifier._create_text_body(notification)

            msg.attach(MIMEText(text_body, "plain"))
            msg.attach(MIMEText(html_body, "html"))

            # Send email
            await aiosmtplib.send(
                msg,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USERNAME,
                password=settings.SMTP_PASSWORD,
                use_tls=settings.SMTP_USE_TLS,
            )

            return {
                "success": True,
                "recipients": recipients,
                "sent_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def _create_html_body(notification: NotificationRequest) -> str:
        """Create HTML email body."""
        severity_colors = {
            NotificationSeverity.INFO: "#17a2b8",
            NotificationSeverity.WARNING: "#ffc107",
            NotificationSeverity.ERROR: "#dc3545",
            NotificationSeverity.CRITICAL: "#721c24"
        }

        color = severity_colors.get(notification.severity, "#6c757d")

        html_template = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: {{ color }}; color: white; padding: 20px; border-radius: 5px 5px 0 0; }
        .content { background-color: #f8f9fa; padding: 20px; border: 1px solid #dee2e6; }
        .footer { background-color: #e9ecef; padding: 10px; text-align: center; font-size: 12px; border-radius: 0 0 5px 5px; }
        .info-row { margin: 10px 0; }
        .label { font-weight: bold; color: #495057; }
        .error-box { background-color: #fff3cd; border: 1px solid #ffc107; padding: 15px; margin: 10px 0; border-radius: 5px; }
        code { background-color: #f1f3f5; padding: 2px 6px; border-radius: 3px; font-family: monospace; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2 style="margin: 0;">{{ title }}</h2>
            <p style="margin: 5px 0 0 0;">{{ severity_label }} - {{ timestamp }}</p>
        </div>
        <div class="content">
            <div class="info-row">
                <span class="label">Type:</span> {{ type }}
            </div>
            {% if job_id %}
            <div class="info-row">
                <span class="label">Job ID:</span> <code>{{ job_id }}</code>
            </div>
            {% endif %}
            {% if job_filename %}
            <div class="info-row">
                <span class="label">Filename:</span> {{ job_filename }}
            </div>
            {% endif %}
            <div class="info-row">
                <span class="label">Message:</span>
                <p>{{ message }}</p>
            </div>
            {% if error_message %}
            <div class="error-box">
                <strong>Error Details:</strong>
                <p style="margin: 5px 0;">{{ error_message }}</p>
            </div>
            {% endif %}
            {% if stack_trace %}
            <div class="info-row">
                <details>
                    <summary><strong>Stack Trace</strong></summary>
                    <pre style="background-color: #f8f9fa; padding: 10px; overflow-x: auto;">{{ stack_trace }}</pre>
                </details>
            </div>
            {% endif %}
            {% if metadata %}
            <div class="info-row">
                <span class="label">Additional Info:</span>
                <pre style="background-color: #f8f9fa; padding: 10px; overflow-x: auto;">{{ metadata_json }}</pre>
            </div>
            {% endif %}
        </div>
        <div class="footer">
            Audio Processing Microservice Architecture<br>
            Generated by Claude Code
        </div>
    </div>
</body>
</html>
"""

        template = Template(html_template)
        return template.render(
            color=color,
            title=notification.title,
            severity_label=notification.severity.upper(),
            timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            type=notification.type.value,
            job_id=notification.job_id,
            job_filename=notification.job_filename,
            message=notification.message,
            error_message=notification.error_message,
            stack_trace=notification.stack_trace,
            metadata=notification.metadata,
            metadata_json=str(notification.metadata) if notification.metadata else None
        )

    @staticmethod
    def _create_text_body(notification: NotificationRequest) -> str:
        """Create plain text email body."""
        lines = [
            f"[{notification.severity.upper()}] {notification.title}",
            f"Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"Type: {notification.type.value}",
            ""
        ]

        if notification.job_id:
            lines.append(f"Job ID: {notification.job_id}")
        if notification.job_filename:
            lines.append(f"Filename: {notification.job_filename}")

        lines.extend(["", f"Message:", notification.message, ""])

        if notification.error_message:
            lines.extend(["Error Details:", notification.error_message, ""])

        if notification.stack_trace:
            lines.extend(["Stack Trace:", notification.stack_trace, ""])

        if notification.metadata:
            lines.extend(["Additional Info:", str(notification.metadata)])

        return "\n".join(lines)


class WebhookNotifier:
    """Send webhook notifications."""

    @staticmethod
    async def send(notification: NotificationRequest) -> Dict[str, Any]:
        """Send webhook notification."""
        if not settings.ENABLE_WEBHOOK:
            return {"success": False, "error": "Webhook notifications disabled"}

        if not settings.WEBHOOK_URL:
            return {"success": False, "error": "Webhook URL not configured"}

        try:
            payload = {
                "type": notification.type.value,
                "severity": notification.severity.value,
                "title": notification.title,
                "message": notification.message,
                "job_id": notification.job_id,
                "job_filename": notification.job_filename,
                "error_message": notification.error_message,
                "stack_trace": notification.stack_trace,
                "metadata": notification.metadata,
                "timestamp": datetime.utcnow().isoformat()
            }

            headers = {"Content-Type": "application/json"}
            if settings.WEBHOOK_SECRET:
                headers["X-Webhook-Secret"] = settings.WEBHOOK_SECRET

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    settings.WEBHOOK_URL,
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()

            return {
                "success": True,
                "webhook_url": settings.WEBHOOK_URL,
                "status_code": response.status_code,
                "sent_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            return {"success": False, "error": str(e)}


class SlackNotifier:
    """Send Slack notifications."""

    @staticmethod
    async def send(notification: NotificationRequest) -> Dict[str, Any]:
        """Send Slack notification."""
        if not settings.ENABLE_SLACK:
            return {"success": False, "error": "Slack notifications disabled"}

        if not settings.SLACK_WEBHOOK_URL:
            return {"success": False, "error": "Slack webhook URL not configured"}

        try:
            # Severity emoji and color
            severity_config = {
                NotificationSeverity.INFO: {"emoji": ":information_source:", "color": "#17a2b8"},
                NotificationSeverity.WARNING: {"emoji": ":warning:", "color": "#ffc107"},
                NotificationSeverity.ERROR: {"emoji": ":x:", "color": "#dc3545"},
                NotificationSeverity.CRITICAL: {"emoji": ":rotating_light:", "color": "#721c24"}
            }

            config = severity_config.get(notification.severity, {"emoji": ":bell:", "color": "#6c757d"})

            # Build Slack message
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"{config['emoji']} {notification.title}"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Severity:*\n{notification.severity.upper()}"},
                        {"type": "mrkdwn", "text": f"*Type:*\n{notification.type.value}"}
                    ]
                }
            ]

            if notification.job_id:
                blocks.append({
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Job ID:*\n`{notification.job_id}`"},
                        {"type": "mrkdwn", "text": f"*Filename:*\n{notification.job_filename or 'N/A'}"}
                    ]
                })

            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Message:*\n{notification.message}"}
            })

            if notification.error_message:
                blocks.append({
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*Error:*\n```{notification.error_message[:500]}```"}
                })

            payload = {
                "blocks": blocks,
                "attachments": [{
                    "color": config['color'],
                    "footer": "Audio Processing System",
                    "ts": int(datetime.utcnow().timestamp())
                }]
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    settings.SLACK_WEBHOOK_URL,
                    json=payload
                )
                response.raise_for_status()

            return {
                "success": True,
                "sent_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            return {"success": False, "error": str(e)}
