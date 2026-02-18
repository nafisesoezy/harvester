import xml.etree.ElementTree as ET
from collections import defaultdict
from typing import Dict, List, Union


# =====================================================
# LTER-LIFE ← Dataverse mapping with coverage semantics
# =====================================================

LTERLIFE_MAPPING: Dict[str, Dict[str, Union[List[str], str]]] = {
    # ---------- CITATION METADATA ----------
    "Date (metadata record)": {
        "sources": ["dateofdeposit", "dsdescriptiondate", "date", "createtime", "publicationdate"],
        "coverage": "partial",
    },
    "Language (metadata)": {
        "sources": ["language"],
        "coverage": "exact",
    },
    "Responsible party": {
        "sources": ["depositor", "contributor", "datacollector"],
        "coverage": "partial",
    },
    "Email of the responsible organization or individual": {
        "sources": ["email"],
        "coverage": "partial",
    },
    "Landing page": {
        "sources": ["alternativeurl", "identifier"],
        "coverage": "partial",
    },
    "Title": {
        "sources": ["title"],
        "coverage": "exact",
    },
    "Description": {
        "sources": ["description", "text", "socialsciencenotestext"],
        "coverage": "exact",
    },
    "Identifier": {
        "sources": ["identifier", "datasetpersistentid"],
        "coverage": "exact",
    },
    "Resource type": {
        "sources": ["kindofdata", "type", "datasettype"],
        "coverage": "partial",
    },
    "Keyword": {
        "sources": ["keyword", "subject"],
        "coverage": "exact",
    },
    "Creator": {
        "sources": [
            "authorname",
            "creator",
            "producername",
            "givenname",
            "familyname",
            "nametype",
        ],
        "coverage": "partial",
    },
    "Contact point": {
        "sources": ["datasetcontactname", "contactforaccess", "contributor"],
        "coverage": "partial",
    },
    "Publisher": {
        "sources": ["publisher", "distributorname"],
        "coverage": "partial",
    },

    # ---------- GEOSPATIAL ----------
    "Spatial coverage": {
        "sources": [
            "productionplace",
            "geographiccoverage",
            "country",
            "state",
            "city",
            "othergeographiccoverage",
            "westlongitude",
            "eastlongitude",
            "northlatitude",
            "southlatitude",
        ],
        "coverage": "partial",
    },

    # ---------- TEMPORAL ----------
    "Temporal coverage": {
        "sources": [
            "timeperiodcovered",
            "dateofcollection",
            "productiondate",
            "date",
            "timemethod",
        ],
        "coverage": "partial",
    },
    "Temporal resolution": {
        "sources": ["frequencyofdatacollection"],
        "coverage": "partial",
    },

    # ---------- TERMS ----------
    "License": {
        "sources": ["license"],
        "coverage": "exact",
    },
    "Access rights": {
        "sources": ["restrictions"],
        "coverage": "partial",
    },
    "Access URL": {
        "sources": ["dataaccessplace"],
        "coverage": "partial",
    },

    # ---------- NO COVERAGE FIELDS ----------
    "spatialResolutionInMeters": {"sources": [], "coverage": "none"},
    "levelOfDetail": {"sources": [], "coverage": "none"},
    "Reference system": {"sources": [], "coverage": "none"},
    "Dataset format (distributionFormat)": {"sources": [], "coverage": "none"},
    "Size (byte size)": {"sources": [], "coverage": "none"},
}


# =====================================================
# Helpers
# =====================================================

def _strip_ns(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def _collect_fields(root: ET.Element) -> Dict[str, List[str]]:
    fields = defaultdict(list)

    for elem in root.iter():
        tag = _strip_ns(elem.tag).lower()
        text = (elem.text or "").strip()
        if text:
            fields[tag].append(text)

    return fields


# =====================================================
# Public API
# =====================================================

def map_record_to_lterlife(xml_string: str) -> Dict[str, Union[str, List[str]]]:
    """
    Maps a harvested XML metadata record into the LTER-LIFE schema.

    Rules:
    - All LTER-LIFE fields are always present
    - Exact coverage → value as-is
    - Partial coverage → prepend '*'
    - No coverage → '-'
    - Multiple values → list
    """

    try:
        root = ET.fromstring(xml_string)
        extracted = _collect_fields(root)
    except ET.ParseError:
        # Return empty but complete record
        return {field: "-" for field in LTERLIFE_MAPPING}

    mapped: Dict[str, Union[str, List[str]]] = {}

    for lter_field, cfg in LTERLIFE_MAPPING.items():
        sources = cfg["sources"]
        coverage = cfg["coverage"]

        values: List[str] = []

        for src in sources:
            if src in extracted:
                for val in extracted[src]:
                    if coverage == "partial":
                        values.append(f"*{val}")
                    else:
                        values.append(val)

        if values:
            mapped[lter_field] = {
                "value": values if len(values) > 1 else values[0],
                "raw_fields": sources,
            }
        else:
            mapped[lter_field] = {
                "value": "-",
                "raw_fields": ["-"],
            }

    return mapped
