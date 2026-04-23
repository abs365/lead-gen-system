import re
from urllib.parse import urljoin

import requests


EMAIL_REGEX = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
PHONE_REGEX = r"\+?\d[\d\s\-\(\)]{7,}"


def _fetch_html(url: str) -> str:
    response = requests.get(
        url,
        timeout=10,
        headers={
            "User-Agent": "Mozilla/5.0"
        },
        allow_redirects=True,
    )
    response.raise_for_status()
    return response.text


def _find_email(text: str):
    emails = re.findall(EMAIL_REGEX, text or "")
    for email in emails:
        email = email.strip().lower()
        if email.endswith((".png", ".jpg", ".jpeg", ".webp", ".svg")):
            continue
        if "example.com" in email:
            continue
        return email
    return None


def _find_phone(text: str):
    phones = re.findall(PHONE_REGEX, text or "")
    for phone in phones:
        cleaned = " ".join(phone.split()).strip()
        if len(cleaned) >= 8:
            return cleaned
    return None


def extract_email_from_website(url: str):
    try:
        urls_to_try = [
            url,
            urljoin(url, "/contact"),
            urljoin(url, "/contact-us"),
            urljoin(url, "/about"),
            urljoin(url, "/get-in-touch"),
        ]

        seen = set()

        for candidate in urls_to_try:
            if candidate in seen:
                continue
            seen.add(candidate)

            try:
                html = _fetch_html(candidate)
            except Exception:
                continue

            email = _find_email(html)
            if email:
                return email

        return None

    except Exception:
        return None


def extract_contact_details(url: str):
    try:
        urls_to_try = [
            url,
            urljoin(url, "/contact"),
            urljoin(url, "/contact-us"),
            urljoin(url, "/about"),
            urljoin(url, "/get-in-touch"),
        ]

        seen = set()
        best_email = None
        best_phone = None

        for candidate in urls_to_try:
            if candidate in seen:
                continue
            seen.add(candidate)

            try:
                html = _fetch_html(candidate)
            except Exception:
                continue

            if not best_email:
                best_email = _find_email(html)

            if not best_phone:
                best_phone = _find_phone(html)

            if best_email and best_phone:
                break

        return best_email, best_phone

    except Exception:
        return None, None