import requests
from urllib.parse import urlparse
import pandas as pd

requests.packages.urllib3.disable_warnings()

# ---------------------------------------------------------------------
# 🌍 List of all candidate portals
# ---------------------------------------------------------------------
PORTALS = [
    "https://stac.ecodatacube.eu/",
    "https://data.rivm.nl/meta/srv/dut/catalog.search#/home",
    "https://www.nioz.nl/",
    "https://dataverse.nioz.nl/",
    "https://www.gbif.org/",
    "https://api.gbif.org/",
    "https://portal.edirepository.org/nis/advancedSearch.jsp",
    "https://www.pdok.nl/",
    "https://opendata.cbs.nl/statline/portal.html",
    "https://www.satellietdataportaal.nl/",
    "https://nationaalgeoregister.nl/geonetwork/srv/dut/catalog.search#/home",
    "https://waterinfo.rws.nl/"
]

# ---------------------------------------------------------------------
# 🔗 Known mappings (based on documentation and prior analysis)
# ---------------------------------------------------------------------
KNOWN_APIS = {
    "stac.ecodatacube.eu": ("STAC", "https://stac.ecodatacube.eu/api/stac"),
    "data.rivm.nl": ("GeoNetwork", "https://data.rivm.nl/meta/srv/api/records"),
    "dataverse.nioz.nl": ("OAI-PMH", "https://dataverse.nioz.nl/oai"),
    "api.gbif.org": ("OAI-PMH", "https://api.gbif.org/v1/oai-pmh/registry"),
    "nationaalgeoregister.nl": ("CSW", "https://nationaalgeoregister.nl/geonetwork/srv/eng/csw"),
    "opendata.cbs.nl": ("OData", "https://opendata.cbs.nl/ODataApi/OData/82070NED"),
    "portal.edirepository.org": ("EML / REST", "https://portal.edirepository.org/nis/"),
    "www.pdok.nl": ("CSW (via NGR)", "https://nationaalgeoregister.nl/geonetwork/srv/eng/csw"),
    "www.gbif.org": ("OAI-PMH (Registry)", "https://api.gbif.org/v1/oai-pmh/registry"),
    "www.nioz.nl": ("Unknown", ""),
    "www.satellietdataportaal.nl": ("STAC / REST", "https://www.satellietdataportaal.nl/api/"),
    "waterinfo.rws.nl": ("Custom REST API", "https://waterinfo.rws.nl/api/"),
}

# ---------------------------------------------------------------------
# 🧩 Helper functions
# ---------------------------------------------------------------------
def normalize_base(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def detect_protocol(url: str):
    """Detect or infer the correct protocol and endpoint."""
    base = normalize_base(url)
    host = urlparse(base).netloc

    # 1️⃣ Known API mapping
    if host in KNOWN_APIS:
        proto, api = KNOWN_APIS[host]
        return proto, api

    # 2️⃣ Probe common patterns (fallback)
    for path in [
        "stac/search", "api/stac/search",
        "oai?verb=Identify",
        "srv/api/records", "geonetwork/srv/api/records",
        "csw?service=CSW&request=GetCapabilities"
    ]:
        try:
            test_url = f"{base.rstrip('/')}/{path}"
            r = requests.get(test_url, timeout=10, verify=False)
            text = r.text.lower()
            if "stac_version" in text:
                return "STAC", base + "/api/stac"
            if "<oai-pmh" in text:
                return "OAI-PMH", test_url.split("?")[0]
            if "<csw:capabilities" in text or "ogc:csw" in text:
                return "CSW", test_url
            if "geonetwork" in text:
                return "GeoNetwork", test_url
        except Exception:
            continue

    # 3️⃣ Default fallback
    return "Unknown", base


# ---------------------------------------------------------------------
# 🧮 Main function
# ---------------------------------------------------------------------
def main():
    results = []
    for portal in PORTALS:
        proto, api = detect_protocol(portal)
        results.append({"Portal": portal, "Detected Protocol": proto, "API URL": api})
        print(f"✅ {portal} → {proto} ({api})")

    df = pd.DataFrame(results)
    print("\n===== DETECTION RESULTS =====")
    print(df.to_markdown(index=False))

    df.to_csv("all_portal_protocols.csv", index=False)
    print("\n💾 Saved to all_portal_protocols.csv")


# ---------------------------------------------------------------------
# 🚀 Run
# ---------------------------------------------------------------------
if __name__ == "__main__":
    main()
