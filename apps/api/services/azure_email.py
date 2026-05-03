import os
import requests
from dotenv import load_dotenv

load_dotenv()

TENANT_ID = os.getenv("AZURE_TENANT_ID")
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
EMAIL_ACCOUNT = os.getenv("EMAIL_ACCOUNT")


def get_access_token():
    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"

    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials",
    }

    res = requests.post(url, data=data)

    if res.status_code != 200:
        raise Exception(f"Token error: {res.text}")

    return res.json()["access_token"]


def send_email(to_email: str, subject: str, body: str):
    token = get_access_token()

    url = f"https://graph.microsoft.com/v1.0/users/{EMAIL_ACCOUNT}/sendMail"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    payload = {
        "message": {
            "subject": subject,
            "body": {
                "contentType": "HTML",
                "content": body,
            },
            "toRecipients": [
                {"emailAddress": {"address": to_email}}
            ],
        }
    }

    res = requests.post(url, headers=headers, json=payload)

    if res.status_code != 202:
        raise Exception(f"Email failed: {res.text}")