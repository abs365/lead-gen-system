import requests

# Known Socrata-based London borough open data portals
candidates = [
    ("Hackney", "https://data.hackney.gov.uk/api/explore/v2.1/catalog/datasets/planning-applications/records?limit=2"),
    ("Lambeth", "https://data.lambeth.gov.uk/api/explore/v2.1/catalog/datasets/planning-applications/records?limit=2"),
    ("Southwark", "https://data.southwark.gov.uk/api/explore/v2.1/catalog/datasets/planning-applications/records?limit=2"),
    ("Tower Hamlets", "https://data.towerhamlets.gov.uk/api/explore/v2.1/catalog/datasets/planning-applications/records?limit=2"),
    ("Islington", "https://data.islington.gov.uk/api/explore/v2.1/catalog/datasets/planning-applications/records?limit=2"),
    ("Wandsworth", "https://data.wandsworth.gov.uk/api/explore/v2.1/catalog/datasets/planning-applications/records?limit=2"),
    ("Newham", "https://data.newham.gov.uk/api/explore/v2.1/catalog/datasets/planning-applications/records?limit=2"),
]

for name, url in candidates:
    try:
        r = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        print(f"{name}: {r.status_code} - {r.text[:80]}")
    except Exception as e:
        print(f"{name}: ERROR - {str(e)[:60]}")