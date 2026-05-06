import os
import requests

TENANT_ID = os.getenv("AZURE_TENANT_ID")
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
SENDER_EMAIL = os.getenv("EMAIL_ACCOUNT")


def get_access_token():
    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"

    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials"
    }

    response = requests.post(url, data=data)

    if response.status_code != 200:
        raise Exception(f"Token error: {response.text}")

    return response.json()["access_token"]


def send_email(to_email: str, subject: str, body: str):
    token = get_access_token()

    url = f"https://graph.microsoft.com/v1.0/users/{SENDER_EMAIL}/sendMail"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "message": {
            "subject": subject,
            "body": {
                "contentType": "HTML",
                "content": body
            },
            "toRecipients": [
                {
                    "emailAddress": {
                        "address": to_email
                    }
                }
            ]
        }
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code != 202:
        raise Exception(f"Email failed: {response.text}")