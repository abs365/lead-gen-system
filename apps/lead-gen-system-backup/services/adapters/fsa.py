import requests


def search_demand(location: str, category: str, page: int = 1, page_size: int = 50):
    url = "https://api.ratings.food.gov.uk/Establishments"

    headers = {
        "x-api-version": "2",
        "Accept": "application/json",
    }

    params = {
        "name": location,
        "businessType": category,
        "pageNumber": page,
        "pageSize": page_size,
    }

    response = requests.get(url, headers=headers, params=params, timeout=30)
    response.raise_for_status()

    data = response.json()
    establishments = data.get("establishments", [])

    results = []

    for item in establishments:
        address_parts = [
            item.get("AddressLine1"),
            item.get("AddressLine2"),
            item.get("AddressLine3"),
            item.get("AddressLine4"),
        ]
        address = ", ".join([part for part in address_parts if part])

        postcode = item.get("PostCode")
        postcode_district = None
        if postcode:
            postcode_district = postcode.split(" ")[0]

        results.append(
            {
                "name": item.get("BusinessName"),
                "address": address,
                "borough": item.get("LocalAuthorityName"),
                "postcode": postcode,
                "category": item.get("BusinessType"),
                "fsa_establishment_id": str(item.get("FHRSID")),
                "last_inspection_date": item.get("RatingDate"),
                "demand_score": 0,
                "source": "fsa",
                "freshness_label": item.get("RatingDate"),
                "fsa_rating": str(item.get("RatingValue")) if item.get("RatingValue") is not None else None,
            }
        )

    return results