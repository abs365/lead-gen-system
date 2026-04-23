import os
import requests

API_KEY = "AIzaSyAXwgnWWyZo89QcCZsGWSIwJWUz_VxZlmw"


def _extract_address_parts(address_components):
    borough = None
    postcode = None

    for component in address_components or []:
        types = component.get("types", [])

        if "postal_code" in types:
            postcode = component.get("long_name")

        if "postal_town" in types or "administrative_area_level_2" in types or "locality" in types:
            if not borough:
                borough = component.get("long_name")

    return borough, postcode


def get_place_details(place_id: str):
    url = "https://maps.googleapis.com/maps/api/place/details/json"

    params = {
        "place_id": place_id,
        "key": API_KEY,
    }

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    result = data.get("result", {})
    # comment it out
# print("Fetched:", name, "|", phone)

    result = data.get("result", {})

    return {
        "phone": result.get("formatted_phone_number"),
        "website": result.get("website"),
        "address": result.get("formatted_address"),
        "borough": None,
        "postcode": None,
    }


def search_plumbers(keyword: str, location: str):
    if not API_KEY:
        raise RuntimeError("GOOGLE_API_KEY is missing")

    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"

    params = {
        "query": f"{keyword} in {location}",
        "key": API_KEY,
    }

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    status = data.get("status")
    if status not in ("OK", "ZERO_RESULTS"):
        error_message = data.get("error_message", "")
        raise RuntimeError(f"Google Text Search failed: status={status}, error={error_message}")

    places = data.get("results", [])
    results = []

    for place in places:
        place_id = place.get("place_id")
        if not place_id:
            continue

        details = get_place_details(place_id)

        formatted_address = details.get("address") or place.get("formatted_address")

        results.append(
            {
                "name": place.get("name"),
                "address": formatted_address,
                "borough": details.get("borough"),
                "postcode": details.get("postcode"),
                "phone": details.get("phone"),
                "website": details.get("website"),
                "google_place_id": place_id,
                "source": "google_places",
            }
        )

    return results