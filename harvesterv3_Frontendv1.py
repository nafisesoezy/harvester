import requests
from urllib.parse import urlparse
from datetime import datetime

from protocols.oai import harvest_oai
from protocols.csw import harvest_csw
from protocols.stac import harvest_stac
from protocols.geonetwork import harvest_geonetwork
from protocols.odata import harvest_odata
from converters.schema_detector import detect_schema
from converters.dc_converter import map_dublin_core_to_lterlife


requests.packages.urllib3.disable_warnings()

# =====================================================
# ✅ KNOWN API MAPPINGS
# =====================================================
KNOWN_APIS = {
    "stac.ecodatacube.eu": ("STAC", "https://stac.ecodatacube.eu/api/stac"),
    "data.rivm.nl": ("GeoNetwork", "https://data.rivm.nl/meta/srv/api/records"),
    "dataverse.nioz.nl": ("OAI-PMH", "https://dataverse.nioz.nl/oai"),
    "api.gbif.org": ("OAI-PMH", "https://api.gbif.org/v1/oai-pmh/registry"),
    "nationaalgeoregister.nl": ("CSW", "https://nationaalgeoregister.nl/geonetwork/srv/eng/csw"),
    "opendata.cbs.nl": ("OData", "https://opendata.cbs.nl/ODataApi/OData/82070NED"),
}


# =====================================================
# ✅ PROTOCOL DETECTION
# =====================================================
def normalize_base(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"

def detect_protocol(url: str):
    base = normalize_base(url)
    host = urlparse(base).netloc

    if host in KNOWN_APIS:
        return KNOWN_APIS[host]

    return "Unknown", base


# =====================================================
# ✅ DISPATCHER (MAIN ENTRY POINT)
# =====================================================

def run_harvest(portal_url: str, start_date=None, end_date=None, max_records=20):
    proto, api = detect_protocol(portal_url)

    print(f"➡️ Detected protocol: {proto}")
    print(f"🔗 API endpoint: {api}")

    # =============================
    # ✅ HARVEST PHASE
    # =============================
    if proto == "OAI-PMH":
        records = harvest_oai(api, max_records, start_date, end_date)

    elif proto == "CSW":
        records = harvest_csw(api, max_records)

    elif proto == "STAC":
        records = harvest_stac(api, max_records)

    elif proto == "GeoNetwork":
        records = harvest_geonetwork(api, max_records)

    elif proto == "OData":
        records = harvest_odata(api, max_records)

    else:
        print("⚠️ Unsupported protocol")
        return []

    # =============================
    # ✅ SCHEMA DETECTION + MAPPING
    # =============================
    output_records = []

    for record_xml in records:
        schema = detect_schema(record_xml)

        # RAW BLOCK (unchanged)
        raw_block = {
            "schema": schema,
            "record": record_xml
        }

        # MAPPED BLOCK
        if schema == "dublin_core":
            mapped_block = {
                "target_schema": "lterlife",
                "fields": map_dublin_core_to_lterlife(record_xml)
            }
        else:
            mapped_block = {
                "target_schema": "lterlife",
                "fields": {}
            }

        # ✅ FINAL TWO-COLUMN OBJECT
        output_records.append({
            "raw_metadata": raw_block,
            "mapped_metadata": mapped_block
        })

        print(f"📄 Schema detected and mapped: {schema} → lterlife")

    return output_records




if __name__ == "__main__":
    print("Run through FastAPI UI only.")