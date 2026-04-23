import csv
from io import StringIO


def generate_csv(matches):
    output = StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "match_id",
        "score",
        "business_name",
        "business_address",
        "plumber_name",
        "plumber_phone",
        "plumber_email",
    ])

    # Rows
    for m in matches:
        writer.writerow([
            m.id,
            m.match_score,
            m.demand_prospect.name if m.demand_prospect else "",
            m.demand_prospect.address if m.demand_prospect else "",
            m.plumber.name if m.plumber else "",
            m.plumber.phone if m.plumber else "",
            m.plumber.email if m.plumber else "",
        ])

    return output.getvalue()