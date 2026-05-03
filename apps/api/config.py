import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Core
    DATABASE_URL: str
    API_KEY: str | None = None

    # APIs
    GOOGLE_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None
    RESEND_API_KEY: str | None = None
    COMPANIES_HOUSE_API_KEY: str | None = None

    # SMTP
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    EMAIL_USER: str | None = None
    EMAIL_PASS: str | None = None
    FROM_EMAIL: str | None = None

    # Gmail IMAP (legacy / optional)
    GMAIL_IMAP_EMAIL: str | None = None
    GMAIL_IMAP_APP_PASSWORD: str | None = None
    GMAIL_IMAP_HOST: str = "imap.gmail.com"
    GMAIL_IMAP_FOLDER: str = "INBOX"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

    @property
    def active_smtp_user(self) -> str:
        return self.SMTP_USER or self.EMAIL_USER or ""

    @property
    def active_smtp_password(self) -> str:
        return self.SMTP_PASSWORD or self.EMAIL_PASS or ""


# ✅ SINGLE INSTANCE (ONLY ONCE)
settings = Settings()


# ✅ AZURE CONFIG (OUTSIDE CLASS)
AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID")
AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
AZURE_CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
EMAIL_ACCOUNT = os.getenv("EMAIL_ACCOUNT")