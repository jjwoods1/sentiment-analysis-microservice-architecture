from pydantic_settings import BaseSettings
from typing import Optional, List


class Settings(BaseSettings):
    # Notification Channels - Enable/Disable
    ENABLE_EMAIL: bool = True
    ENABLE_WEBHOOK: bool = True
    ENABLE_SLACK: bool = False

    # Email Configuration (SMTP)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: Optional[str] = None
    SMTP_FROM_NAME: str = "Audio Processing System"
    SMTP_USE_TLS: bool = True

    # Notification Recipients
    NOTIFICATION_EMAILS: str = ""  # Comma-separated list

    # Webhook Configuration
    WEBHOOK_URL: Optional[str] = None
    WEBHOOK_SECRET: Optional[str] = None

    # Slack Configuration
    SLACK_WEBHOOK_URL: Optional[str] = None

    # Notification Settings
    NOTIFY_ON_JOB_FAILURE: bool = True
    NOTIFY_ON_JOB_SUCCESS: bool = False
    NOTIFY_ON_TASK_FAILURE: bool = True
    NOTIFY_ON_SYSTEM_ERROR: bool = True

    # Retry Settings
    NOTIFICATION_MAX_RETRIES: int = 3
    NOTIFICATION_RETRY_DELAY: int = 5  # seconds

    class Config:
        env_file = ".env"
        case_sensitive = True

    def get_email_list(self) -> List[str]:
        """Parse comma-separated email list."""
        if not self.NOTIFICATION_EMAILS:
            return []
        return [email.strip() for email in self.NOTIFICATION_EMAILS.split(",") if email.strip()]


settings = Settings()
