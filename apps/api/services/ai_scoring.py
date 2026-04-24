from datetime import datetime


def parse_date_safe(value):
    if not value:
        return None

    formats = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%Y-%m-%dT%H:%M:%S",
        "%d %B %Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except Exception:
            continue

    return None


def calculate_freshness_multiplier(date_value):
    dt = parse_date_safe(date_value)

    if not dt:
        return 1.0, "freshness_unknown:+0%"

    days_old = (datetime.utcnow() - dt).days

    if days_old <= 7:
        return 1.25, "freshness_0_7_days:+25%"
    if days_old <= 30:
        return 1.10, "freshness_8_30_days:+10%"
    if days_old <= 90:
        return 1.00, "freshness_31_90_days:+0%"
    return 0.85, "freshness_90_plus_days:-15%"


def calculate_demand_score(signals, source, inspection_date=None):
    base_score = 0
    breakdown = []

    for signal in signals:
        if signal == "new_food_business":
            base_score += 30
            breakdown.append("new_food_business:+30")

        elif signal == "high_water_usage":
            base_score += 20
            breakdown.append("high_water_usage:+20")

        elif signal == "no_website":
            base_score += 10
            breakdown.append("no_website:+10")

        elif signal == "new_company":
            base_score += 25
            breakdown.append("new_company:+25")

    if source == "fsa":
        base_score += 10
        breakdown.append("source_fsa:+10")
    elif source == "companies_house":
        base_score += 15
        breakdown.append("source_companies_house:+15")

    freshness_multiplier, freshness_reason = calculate_freshness_multiplier(inspection_date)
    breakdown.append(freshness_reason)

    final_score = int(round(base_score * freshness_multiplier))

    if final_score > 100:
        final_score = 100

    return final_score, ",".join(breakdown)