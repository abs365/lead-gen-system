import requests
import os

API_KEY = os.getenv("COMPANIES_HOUSE_API_KEY")

BASE_URL = "https://api.company-information.service.gov.uk/search/companies"


def search_companies(query="restaurant", location="London", page=1, per_page=20):
    start_index = (page - 1) * per_page

    params = {
        "q": f"{query} {location}",
        "start_index": start_index,
        "items_per_page": per_page,
    }

    response = requests.get(
        BASE_URL,
        params=params,
        auth=(API_KEY, "")
    )

    if response.status_code != 200:
        return []

    data = response.json()

    results = []

    for item in data.get("items", []):
        results.append({
            "name": item.get("title"),
            "company_number": item.get("company_number"),
            "address": item.get("address_snippet"),
            "category": "company",
        })

    return results