import requests
from urllib.parse import urlparse
from sickle import Sickle
from owslib.csw import CatalogueServiceWeb
from pystac_client import Client
import xml.etree.ElementTree as ET

requests.packages.urllib3.disable_warnings()

# ---------------------------------------------------------------------
# 🌍 List of portals
# ---------------------------------------------------------------------
PORTALS = [
    "https://stac.ecodatacube.eu/",
    "https://data.rivm.nl/meta/srv/dut/catalog.search#/home",
    "https://dataverse.nioz.nl/",
    "https://api.gbif.org/",
    "https://nationaalgeoregister.nl/geonetwork/srv/dut/catalog.search#/home",
    "https://opendata.cbs.nl/statline/portal.html",
]

# ---------------------------------------------------------------------
# 🔗 Known mappings
# ---------------------------------------------------------------------
KNOWN_APIS = {
    "stac.ecodatacube.eu": ("STAC", "https://stac.ecodatacube.eu/api/stac"),
    "data.rivm.nl": ("GeoNetwork", "https://data.rivm.nl/meta/srv/api/records"),
    "dataverse.nioz.nl": ("OAI-PMH", "https://dataverse.nioz.nl/oai"),
    "api.gbif.org": ("OAI-PMH", "https://api.gbif.org/v1/oai-pmh/registry"),
    "nationaalgeoregister.nl": ("CSW", "https://nationaalgeoregister.nl/geonetwork/srv/eng/csw"),
    "opendata.cbs.nl": ("OData", "https://opendata.cbs.nl/ODataApi/OData/82070NED"),
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

    if host in KNOWN_APIS:
        proto, api = KNOWN_APIS[host]
        print(f"ℹ️  Using known mapping for {host} → {proto}")
        return proto, api

    # Try probing some typical API endpoints
    for path in [
        "stac/search", "api/stac/search", "oai?verb=Identify",
        "srv/api/records", "geonetwork/srv/api/records",
        "csw?service=CSW&request=GetCapabilities"
    ]:
        try:
            test_url = f"{base.rstrip('/')}/{path}"
            r = requests.get(test_url, timeout=10, verify=False)
            text = r.text.lower()
            if r.status_code == 200:
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

    return "Unknown", base

# ---------------------------------------------------------------------
# 🧰 Harvester Classes
# ---------------------------------------------------------------------
class OAIHarvester:
    def __init__(self, url): self.url = url
    def harvest(self, max_records=5):
        print(f"📚 Harvesting OAI-PMH from {self.url}")
        try:
            sickle = Sickle(self.url)
            records = sickle.ListRecords(metadataPrefix="oai_dc")
            results = [r.raw for _, r in zip(range(max_records), records)]
            for i, rec in enumerate(results, 1):
                print(f"\n🔸 Record {i}:\n{rec[:400]}...\n")
            return results
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
            results = [r.xml for r in csw.records.values()]
            for i, rec in enumerate(results, 1):
                print(f"\n🔸 Record {i}:\n{rec[:400]}...\n")
            return results
        except Exception as e:
            print("⚠️ CSW harvest failed:", e)
            return []

class GeoNetworkHarvester:
    def __init__(self, url): self.url = url

    def harvest(self, max_records=5):
        print(f"📚 Harvesting GeoNetwork from {self.url}")
        try:
            headers = {"Accept": "application/json, application/xml, text/xml, application/rdf+xml"}
            r = requests.get(self.url, timeout=15, headers=headers, verify=False)
            ctype = r.headers.get("Content-Type", "").lower()

            # --- Case 1: JSON ---
            if "json" in ctype:
                data = r.json()
                records = data.get("records", data)
                results = records[:max_records]
                for i, rec in enumerate(results, 1):
                    print(f"\n🔸 Record {i} (JSON):\n{str(rec)[:400]}...\n")
                return results

            # --- Case 2: RDF/XML or ISO XML ---
            elif "xml" in ctype or "rdf" in ctype:
                root = ET.fromstring(r.text)
                ns = {
                    "dcat": "http://www.w3.org/ns/dcat#",
                    "dct": "http://purl.org/dc/terms/",
                    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
                }
                datasets = []
                for ds in root.findall(".//dcat:Dataset", ns):
                    title = ds.find("dct:title", ns)
                    dist = ds.find(".//dcat:distribution", ns)
                    datasets.append({
                        "title": title.text if title is not None else "(no title)",
                        "distribution": dist.attrib.get("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource") if dist is not None else None
                    })
                    if len(datasets) >= max_records:
                        break
                for i, rec in enumerate(datasets, 1):
                    print(f"\n🔸 Record {i} (RDF/XML):\n{rec}\n")
                return datasets

            # --- Case 3: Fallback plain text or HTML ---
            else:
                print("⚠️ Unrecognized content type:", ctype)
                print(r.text[:300])
                return []

        except Exception as e:
            print("⚠️ GeoNetwork harvest failed:", e)
            return []

class STACHarvester:
    def __init__(self, url): self.url = url
    def harvest(self, max_records=5):
        print(f"📚 Harvesting STAC from {self.url}")
        try:
            client = Client.open(self.url)
            items = list(client.search().items())
            results = [i.to_dict() for i in items[:max_records]]
            for i, rec in enumerate(results, 1):
                print(f"\n🔸 Record {i}:\n{str(rec)[:400]}...\n")
            return results
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
            results = list(data.values())[:max_records]
            for i, rec in enumerate(results, 1):
                print(f"\n🔸 Record {i}:\n{str(rec)[:400]}...\n")
            return results
        except Exception as e:
            print("⚠️ OData harvest failed:", e)
            return []

# ---------------------------------------------------------------------
# 🔍 Harvester selection
# ---------------------------------------------------------------------
def get_harvester(url, proto):
    if proto == "OAI-PMH": return OAIHarvester(url)
    if proto == "CSW": return CSWHarvester(url)
    if proto == "GeoNetwork": return GeoNetworkHarvester(url)
    if proto == "STAC": return STACHarvester(url)
    if proto == "OData": return ODataHarvester(url)
    return None

# ---------------------------------------------------------------------
# 🚀 Main runner
# ---------------------------------------------------------------------
def main():
    for portal in PORTALS:
        print("\n" + "=" * 90)
        print(f"🔍 Detecting {portal} ...")

        proto, api = detect_protocol(portal)
        print(f"➡️  Detected Protocol: {proto}")
        print(f"🔗 API URL: {api}")

        harvester = get_harvester(api, proto)
        if not harvester:
            print(f"⚠️ No harvester available for {proto}")
            continue

        records = harvester.harvest(max_records=5)
        print(f"✅ Total {len(records)} records harvested from {portal}\n")

if __name__ == "__main__":
    main()
