def score_demand_prospect(prospect):
    score = 0

    # Category scoring (strong signal)
    if prospect.category:
        category = prospect.category.lower()

        if "restaurant" in category:
            score += 25
        elif "cafe" in category:
            score += 20
        elif "takeaway" in category:
            score += 20
        elif "pub" in category:
            score += 15

    # FSA rating (low rating = higher need)
    if prospect.fsa_rating:
        try:
            rating = int(prospect.fsa_rating)
            if rating <= 2:
                score += 25
            elif rating == 3:
                score += 15
        except:
            pass

    # Fresh inspection = active business
    if prospect.last_inspection_date:
        score += 10

    # Has no website/email = opportunity
    if not prospect.website:
        score += 5

    if not prospect.email:
        score += 5

    return min(score, 100)


def score_reason_summary(prospect):
    reasons = []

    if prospect.category:
        reasons.append(f"{prospect.category}")

    if prospect.fsa_rating:
        reasons.append(f"FSA rating: {prospect.fsa_rating}")

    if prospect.last_inspection_date:
        reasons.append("recent inspection")

    return ", ".join(reasons)