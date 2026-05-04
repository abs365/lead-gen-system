import requests

candidates = [
    # Camden (known working - Socrata)
    ("Camden", "https://opendata.camden.gov.uk/resource/2eiu-s2cw.json?$limit=2"),
    # Westminster open data
    ("Westminster", "https://opendata.westminster.gov.uk/resource/planning-applications.json?$limit=2"),
    # Barnet open data
    ("Barnet", "https://opendata.barnet.gov.uk/resource/planning-applications.json?$limit=2"),
    # Bromley
    ("Bromley", "https://data.bromley.gov.uk/api/explore/v2.1/catalog/datasets/planning-applications/records?limit=2"),
    # Croydon
    ("Croydon", "https://data.croydon.gov.uk/api/explore/v2.1/catalog/datasets/planning-applications/records?limit=2"),
    # Ealing
    ("Ealing", "https://data.ealing.gov.uk/api/explore/v2.1/catalog/datasets/planning-applications/records?limit=2"),
    # Greenwich
    ("Greenwich", "https://data.royalgreenwich.gov.uk/api/explore/v2.1/catalog/datasets/planning-applications/records?limit=2"),
    # Harrow
    ("Harrow", "https://data.harrow.gov.uk/api/explore/v2.1/catalog/datasets/planning-applications/records?limit=2"),
    # Brent
    ("Brent", "https://data.brent.gov.uk/api/explore/v2.1/catalog/datasets/planning-applications/records?limit=2"),
    # Enfield
    ("Enfield", "https://data.enfield.gov.uk/api/explore/v2.1/catalog/datasets/planning-applications/records?limit=2"),
]

for name, url in candidates:
    try:
        r = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        print(f"{name}: {r.status_code} - {r.text[:100]}")
    except Exception as e:
        print(f"{name}: ERROR - {str(e)[:80]}")