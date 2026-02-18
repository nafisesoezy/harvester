import requests
import xml.etree.ElementTree as ET
from collections import defaultdict
from collections import defaultdict

from urllib.parse import urlparse
from datetime import datetime

from protocols.oai import harvest_oai
from protocols.csw import harvest_csw
from protocols.stac import harvest_stac
from protocols.geonetwork import harvest_geonetwork
from protocols.odata import harvest_odata
from converters.schema_detector import detect_schema
from converters.dc_converter import map_dublin_core_to_lterlife
from converters.lterlife_mapper import map_record_to_lterlife
from converters.lterlife_mapper import map_record_to_lterlife
from converters.lterlife_mapper import LTERLIFE_MAPPING  # reuse mapping
from exporters.jsonld_exporter import export_jsonld_records, JSONLD_CONTEXT
from exporters.zip_utils import create_zip
import os


requests.packages.urllib3.disable_warnings()

# =====================================================
# ✅ KNOWN API MAPPINGS
# =====================================================
KNOWN_APIS = {
    "stac.ecodatacube.eu": ("STAC", "https://stac.ecodatacube.eu/api/stac"),
    "data.rivm.nl": ("GeoNetwork", "https://data.rivm.nl/meta/srv/api/records"),
    "dataverse.nioz.nl": ("OAI-PMH", "https://dataverse.nioz.nl/oai"),
    "dataverse.nl": ("OAI-PMH", "https://dataverse.nl/oai"),  # ✅ ADDED
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
# ✅ Helper
# =====================================================

def extract_raw_fields(xml_string: str) -> dict:
    """
    Returns:
    {
      "dc:title": [...],
      "dc:creator": [...],
      ...
    }
    """
    root = ET.fromstring(xml_string)
    fields = defaultdict(list)

    for elem in root.iter():
        if elem.text and elem.text.strip():
            tag = elem.tag.split("}")[-1]  # strip namespace
            fields[tag].append(elem.text.strip())

    return fields

# =====================================================
# ✅ DISPATCHER (MAIN ENTRY POINT)
# =====================================================

#def run_harvest(portal_url: str, start_date=None, end_date=None, max_records=20):
def run_harvest(portal_url: str, start_date=None, end_date=None, max_records=None):
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

    for idx, record_xml in enumerate(records):
        mapped_fields = map_record_to_lterlife(record_xml)

        for lter_field, payload in mapped_fields.items():
            output_records.append({
                "lterlife_field": lter_field,
                "raw_field": ", ".join(payload["raw_fields"]),
                "value": payload["value"],
            })

        if idx < len(records) - 1:
            output_records.append({"separator": True})

        # -----------------------------
        # Export phase (ONCE)
        # -----------------------------
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    JSONLD_DIR = os.path.join(BASE_DIR, "jsonld")
    ZIP_PATH = os.path.join(BASE_DIR, "jsonld_records.zip")

    export_jsonld_records(
        records=records,
        output_dir=JSONLD_DIR,
        context=JSONLD_CONTEXT,
    )

    create_zip(JSONLD_DIR, ZIP_PATH)

    return  {
        "xml_records": records,        # raw XML
        "ui_records": output_records,  # table rows
    }

if __name__ == "__main__":
    print("Run through FastAPI UI only.")
