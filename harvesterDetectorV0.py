import requests
from urllib.parse import urlparse
import pandas as pd

# --- Configuration ---
requests.packages.urllib3.disable_warnings()

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

ENDPOINTS = {
    "OAI-PMH": [
        "oai?verb=Identify",
        "oai-pmh?verb=Identify",
        "v1/oai-pmh/registry?verb=Identify",
    ],
    "CSW": [
        "csw?service=CSW&request=GetCapabilities",
        "geonetwork/srv/eng/csw?service=CSW&request=GetCapabilities",
        "geonetwork/srv/dut/csw?service=CSW&request=GetCapabilities"
    ],
    "GeoNetwork": [
        "srv/api/records",
        "geonetwork/srv/api/records",
        "meta/srv/api/records"
    ],
    "STAC": [
        "stac/search",
        "api/stac/search",
        "catalog/stac/search"
    ],
    "CKAN": [
        "api/3/action/package_search"
    ],
    "OData": [
        "ODataApi/OData"
    ]
}


def normalize_base(url: str) -> str:
    """Extract a clean base URL."""
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def check_endpoint(base_url: str, endpoint: str) -> str:
    """Test an endpoint and classify the response."""
    url = base_url.rstrip("/") + "/" + endpoint
    try:
        r = requests.get(url, timeout=10, verify=False, allow_redirects=True)
        text = r.text[:500].lower()
        ctype = r.headers.get("Content-Type", "").lower()

        if r.status_code == 200:
            # Content-based detections
            if "<oai-pmh" in text:
                return "OAI-PMH ✅"
            if "<csw:capabilities" in text or "ogc:csw" in text:
                return "CSW ✅"
            if '"records"' in text or "geonetwork" in text:
                return "GeoNetwork ✅"
            if '"type":"featurecollection"' in text or '"stac_version"' in text:
                return "STAC ✅"
            if '"help":"ckan api"' in text or "ckan_version" in text:
                return "CKAN ✅"
            if "odata.metadata" in text or "odatav4" in text:
                return "OData ✅"
            if "application/xml" in ctype:
                return "XML ✅"
            if "application/json" in ctype:
                return "JSON ✅"
            return "HTML ⚠️"

        # Some APIs return 400 for missing params (still valid)
        if r.status_code == 400 and any(x in text for x in ["oai-pmh", "csw", "geonetwork"]):
            return f"{r.status_code} (Exists)"
        if r.status_code in (401, 403):
            return f"{r.status_code} (Auth Required)"
        return f"{r.status_code} ❌"

    except requests.exceptions.ConnectionError:
        return "Connection Error ❌"
    except requests.exceptions.SSLError:
        return "SSL Error ❌"
    except Exception as e:
        return f"Error ❌ ({type(e).__name__})"


def classify_by_domain(base: str) -> str:
    """Fallback classification for known domains."""
    if "dataverse.nioz.nl" in base:
        return "OAI-PMH (Dataverse)"
    if "gbif.org" in base:
        return "OAI-PMH (GBIF Registry)"
    if "rivm.nl" in base:
        return "GeoNetwork"
    if "nationaalgeoregister.nl" in base:
        return "GeoNetwork / CSW"
    if "pdok.nl" in base:
        return "GeoNetwork (via NGR)"
    if "cbs.nl" in base:
        return "CKAN / OData"
    if "edirepository.org" in base:
        return "EML / REST"
    if "waterinfo.rws.nl" in base:
        return "Custom REST"
    if "satellietdataportaal.nl" in base:
        return "STAC / REST"
    if "stac.ecodatacube.eu" in base:
        return "STAC"
    return "Unknown"


def detect_protocols(portal_url: str) -> dict:
    """Test all endpoint patterns for one portal."""
    base = normalize_base(portal_url)
    result = {"Portal": portal_url, "Base": base}

    found = []
    for proto, patterns in ENDPOINTS.items():
        for endpoint in patterns:
            status = check_endpoint(base, endpoint)
            if "✅" in status or "Exists" in status:
                found.append(proto)
                break
    result["Detected"] = ", ".join(found) if found else classify_by_domain(base)
    return result


def main():
    results = []
    for portal in PORTALS:
        print(f"🔎 Checking {portal} ...")
        result = detect_protocols(portal)
        results.append(result)

    df = pd.DataFrame(results)
    print("\n===== HARVESTING PROTOCOL DETECTION RESULTS =====")
    print(df.to_markdown(index=False))
    df.to_csv("harvest_protocol_results.csv", index=False)
    print("\n✅ Results saved to harvest_protocol_results.csv")


if __name__ == "__main__":
    main()
