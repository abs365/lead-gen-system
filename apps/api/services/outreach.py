def generate_outreach_message(prospect, plumber, score):
    business = prospect.name or "your business"
    plumber_name = plumber.name or "our team"

    signals = (prospect.score_breakdown or "").lower()

    # --------------------------------------------------
    # CONTEXT
    # --------------------------------------------------
    context_parts = []

    if prospect.category:
        context_parts.append(prospect.category.lower())

    if prospect.borough:
        context_parts.append(f"in {prospect.borough}")

    context = " ".join(context_parts)

    # --------------------------------------------------
    # SIGNAL-DRIVEN ANGLE
    # --------------------------------------------------
    if "new_food_business" in signals:
        opening = f"I saw {business} is a relatively new {context}, and wanted to reach out."
        angle = "New setups often run into plumbing or drainage issues early on."
    elif "new_company" in signals:
        opening = f"I came across {business} recently and thought I'd get in touch."
        angle = "New businesses usually need reliable plumbing support as things scale."
    elif "no_website" in signals:
        opening = f"I found {business} and wanted to reach out directly."
        angle = "Many businesses without an online presence rely on trusted local suppliers."
    else:
        opening = f"I came across {business} and wanted to reach out."
        angle = "We support local businesses with ongoing plumbing and maintenance."

    # --------------------------------------------------
    # SCORE-BASED URGENCY
    # --------------------------------------------------
    if score >= 90:
        urgency = "We can respond quickly if anything urgent comes up."
    elif score >= 70:
        urgency = "We help businesses stay ahead of plumbing issues before they escalate."
    else:
        urgency = "Happy to be a backup contact if you ever need help."

    # --------------------------------------------------
    # SUBJECT
    # --------------------------------------------------
    subject = f"{business} — quick plumbing support"

    # --------------------------------------------------
    # MESSAGE
    # --------------------------------------------------
    message = f"""
Hi,

{opening}

{angle}

We typically help with:
- blocked drains
- leaks and emergency repairs
- kitchen plumbing
- ongoing maintenance

{urgency}

{plumber_name} works with local businesses and can step in quickly when needed.

Would it make sense to have a quick chat?

Best regards
""".strip()

    return {
        "subject": subject,
        "message": message
    }