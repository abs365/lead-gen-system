import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

load_dotenv()

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")


def send_email(to_email: str, subject: str, body: str):
    print("SENDING TO:", to_email)

    if not EMAIL_USER or not EMAIL_PASS:
        raise Exception("EMAIL credentials missing")

    msg = MIMEMultipart()
    msg["From"] = EMAIL_USER
    msg["To"] = to_email
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "html"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.set_debuglevel(1)  # SHOW SMTP LOGS
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)

        print("EMAIL SENT SUCCESS:", to_email)

    except Exception as e:
        print("EMAIL FAILED:", e)
        raise