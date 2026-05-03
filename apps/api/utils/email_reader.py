import requests
from config import AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, EMAIL_ACCOUNT


def get_access_token():
    url = f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/oauth2/v2.0/token"

    data = {
        "client_id": AZURE_CLIENT_ID,
        "client_secret": AZURE_CLIENT_SECRET,
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials",
    }

    response = requests.post(url, data=data)
    result = response.json()

    if response.status_code != 200:
        raise Exception(f"Token error: {result}")

    token = result.get("access_token")

    if not token or "." not in token:
        raise Exception(f"Invalid token returned: {result}")

    return token


def read_replies():
    token = get_access_token()

    url = (
        f"https://graph.microsoft.com/v1.0/users/{EMAIL_ACCOUNT}"
        "/mailFolders/inbox/messages?$top=25"
    )

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    response = requests.get(url, headers=headers)
    result = response.json()

    if response.status_code != 200:
        raise Exception(f"Graph email read error: {result}")

    replies = []

    for msg in result.get("value", []):
        subject = msg.get("subject", "")
        body = msg.get("body", {}).get("content", "")

        if "YES" in body.upper():
            replies.append({
                "subject": subject,
                "body": body,
            })

    return replies