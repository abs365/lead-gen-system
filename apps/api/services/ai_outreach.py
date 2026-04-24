import os
import uuid
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def generate_ai_outreach(prospect, plumber, score):
    prompt = f"""
You are a B2B sales expert.

Write a short, high-converting outreach email.

Business:
- Name: {prospect.name}
- Category: {prospect.category}
- Location: {prospect.borough}
- Score: {score}
- Signals: {prospect.score_breakdown}

Plumber:
- Name: {plumber.name}

Rules:
- Keep it under 120 words
- Make it sound natural (not robotic)
- Focus on real problems (plumbing, leaks, maintenance)
- Soft call-to-action
"""

    # CALL AI
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )

    message = response.choices[0].message.content.strip()

    # TRACKING
    tracking_id = str(uuid.uuid4())

    tracking_pixel = f"http://127.0.0.1:8000/track/open/{tracking_id}"
    tracking_link = f"http://127.0.0.1:8000/track/click/{tracking_id}"

    message += f"\n\n<img src='{tracking_pixel}' width='1' height='1' />"
    message += f"\n\n<a href='{tracking_link}'>View details</a>"

    subject = f"{prospect.name} — quick plumbing support"

    return {
        "subject": subject,
        "message": message,
        "tracking_id": tracking_id
    }