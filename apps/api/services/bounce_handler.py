"""
Bounce handler service.
Reads NDR (non-delivery report) emails from the outreach inbox
and automatically nulls the email address on the plumber record.
"""
import os
import re
import requests
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models import Plumber, OutreachLog, Match

logger = logging.getLogger(__name__)

TENANT_ID = os.getenv("AZURE_TENANT_ID")
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
SENDER_EMAIL = os.getenv("EMAIL_ACCOUNT")

BOUNCE_SUBJECT_PATTERNS = [
    "undeliverable",
    "delivery has failed",
    "delivery failure",
    "mail delivery failure",
    "returned mail",
    "non-delivery",
    "could not be delivered",
    "couldn't be delivered",
    "delivery status notification",
    "failure notice",
    "mail delivery failed",
    "message not delivered",
    "relay access denied",
]

BOUNCE_EMAIL_PATTERNS = [
    r"recipient address:\s*([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})",
    r"recipient:\s*([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})",
    r"failed recipient:\s*([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})",
    r"mailbox\s+([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})\s+unknown",
    r"to:\s*([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})",
    r"<([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})>",
    r"([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})",
]

HARD_BOUNCE_CODES = [
    "550", "551", "552", "553", "554",
    "5.1.0", "5.1.1", "