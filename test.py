import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# -----------------------------------------------------
# Portal configuration
# -----------------------------------------------------
PORTAL_URL = "https://stac.ecodatacube.eu/"

# Optional: Some portals require headers to mimic a browser
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
}

# -----------------------------------------------------
# 1️⃣ Fetch the HTML content
# -----------------------------------------------------
r = requests.get(PORTAL_URL, headers=HEADERS, timeout=10, verify=False)
r.raise_for_status()

soup = BeautifulSoup(r.text, "html.parser")

# -----------------------------------------------------
# 2️⃣ Extract possible dataset links and titles
# -----------------------------------------------------
datasets = []

# Common HTML patterns for dataset listings
for a in soup.find_all("a", href=True):
    href = a["href"]
    text = a.get_text(strip=True)
    # Filter to likely dataset links (you can adjust this rule)
    if any(word in href.lower() for word in ["dataset", "record", "data", "collection"]):
        full_url = urljoin(PORTAL_URL, href)
        datasets.append({"title": text or "(no title)", "url": full_url})

# -----------------------------------------------------
# 3️⃣ Display results
# -----------------------------------------------------
print(f"\n✅ Found {len(datasets)} potential dataset links:\n")
for d in datasets[:20]:  # limit to 20 results for clarity
    print(f"- {d['title']}: {d['url']}")

if not datasets:
    print("⚠️ No dataset links found — this site might load data dynamically (JS app).")
