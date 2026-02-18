import requests
from urllib.parse import urlparse
from sickle import Sickle
from owslib.csw import CatalogueServiceWeb
from pystac_client import Client

requests.packages.urllib3.disable_warnings()


PORTALS = [
    "https://stac.ecodatacube.eu/",
    "https://data.rivm.nl/meta/srv/dut/catalog.search#/home",
    "https://dataverse.nioz.nl/",
    "https://api.gbif.org/",
    "https://nationaalgeoregister.nl/geonetwork/srv/dut/catalog.search#/home",
    "https://opendata.cbs.nl/statline/portal.html",
]


KNOWN_APIS = {
    "stac.ecodatacube.eu": ("STAC", "https://stac.ecodatacube.eu/api/stac"),
    "data.rivm.nl": ("GeoNetwork", "https://data.rivm.nl/meta/srv/api/records"),
    "dataverse.nioz.nl": ("OAI-PMH", "https://dataverse.nioz.nl/oai"),
    "api.gbif.org": ("OAI-PMH", "https://api.gbif.org/v1/oai-pmh/registry"),
    "nationaalgeoregister.nl": ("CSW", "https://nationaalgeoregister.nl/geonetwork/srv/eng/csw"),
    "opendata.cbs.nl": ("OData", "https://opendata.cbs.nl/ODataApi/OData/82070NED"),
}


def normalize_base(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def detect_protocol(url: str):
    """Detect or infer the correct protocol and endpoint."""
    base = normalize_base(url)
    host = urlparse(base).netloc

    # 1️⃣ Known patterns
    if host in KNOWN_APIS:
        proto, api = KNOWN_APIS[host]
        print(f"ℹ️  Using known mapping for {host} → {proto}")
        return proto, api

    # 2️⃣ Probe common endpoints (fallback)
    for path in ["stac/search", "api/stac/search", "oai?verb=Identify", "srv/api/records"]:
        try:
            test_url = f"{base.rstrip('/')}/{path}"
            r = requests.get(test_url, timeout=10, verify=False)
            text = r.text.lower()
            if "stac_version" in text:
                return "STAC", base + "/api/stac"
            if "<oai-pmh" in text:
                return "OAI-PMH", test_url.split("?")[0]
            if "geonetwork" in text:
                return "GeoNetwork", test_url
        except Exception:
            continue

    return "Unknown", base


# --- Harvesters ---

class OAIHarvester:
    def __init__(self, url): self.url = url
    def harvest(self, max_records=5):
        print(f"📚 Harvesting OAI-PMH from {self.url}")
        try:
            sickle = Sickle(self.url)
            records = sickle.ListRecords(metadataPrefix='oai_dc')
            return [r.raw for _, r in zip(range(max_records), records)]
        except Exception as e:
            print("⚠️ OAI-PMH harvest failed:", e)
            return []


class CSWHarvester:
    def __init__(self, url): self.url = url
    def harvest(self, max_records=5):
        print(f"📚 Harvesting CSW from {self.url}")
        try:
            csw = CatalogueServiceWeb(self.url, timeout=30)
            csw.getrecords2(maxrecords=max_records)
            return [r.xml for r in csw.records.values()]
        except Exception as e:
            print("⚠️ CSW harvest failed:", e)
            return []


class GeoNetworkHarvester:
    def __init__(self, url): self.url = url
    def harvest(self, max_records=5):
        print(f"📚 Harvesting GeoNetwork from {self.url}")
        try:
            r = requests.get(self.url, timeout=10)
            return r.json().get("records", [])[:max_records]
        except Exception as e:
            print("⚠️ GeoNetwork harvest failed:", e)
            return []


class STACHarvester:
    def __init__(self, url): self.url = url
    def harvest(self, max_records=5):
        print(f"📚 Harvesting STAC from {self.url}")
        try:
            client = Client.open(self.url)
            return [i.to_dict() for i in client.search().items()[:max_records]]
        except Exception as e:
            print("⚠️ STAC harvest failed:", e)
            return []


class ODataHarvester:
    def __init__(self, url): self.url = url
    def harvest(self, max_records=5):
        print(f"📚 Harvesting OData from {self.url}")
        try:
            r = requests.get(self.url, timeout=10)
            data = r.json()
            return list(data.values())[:max_records]
        except Exception as e:
            print("⚠️ OData harvest failed:", e)
            return []


def get_harvester(url, proto):
    if proto == "OAI-PMH": return OAIHarvester(url)
    if proto == "CSW": return CSWHarvester(url)
    if proto == "GeoNetwork": return GeoNetworkHarvester(url)
    if proto == "STAC": return STACHarvester(url)
    if proto == "OData": return ODataHarvester(url)
    return None


def main():
    for portal in PORTALS:
        print(f"\n🔍 Detecting {portal} ...")
        proto, api = detect_protocol(portal)
        print(f"➡️ Detected: {proto}\n🔗 API URL: {api}")

        harvester = get_harvester(api, proto)
        if not harvester:
            print(f"⚠️ No harvester available for {proto}")
            continue

        records = harvester.harvest()
        print(f"✅ Harvested {len(records)} records from {portal}\n")


if __name__ == "__main__":
    main()
