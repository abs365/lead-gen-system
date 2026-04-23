from __future__ import annotations

def generate_outreach_message(prospect, plumber, match_score: int) -> dict:
    subject = f"New local plumbing job opportunity in {prospect.borough}"

    message = f"""
Hi {plumber.name},

We’ve identified a potential plumbing opportunity in your area.

Business: {prospect.name}
Type: {prospect.category}
Location: {prospect.address}

This business may require plumbing services soon based on our data.

Match score: {match_score}/100

If you're interested, we can connect you directly.

Best regards,
Lead Engine
""".strip()

    return {
        "subject": subject,
        "message": message
    }