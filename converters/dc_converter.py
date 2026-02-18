# dc_converter.py
# ------------------------------------------------------
# Dublin Core  →  LTERLife Metadata Schema Converter
# ------------------------------------------------------

import xml.etree.ElementTree as ET

DC_NS = {
    "dc": "http://purl.org/dc/elements/1.1/"
}


def map_dublin_core_to_lterlife(raw_xml: str) -> dict:
    """
    Maps a Dublin Core (OAI-DC) XML record into the LTERLife metadata schema.
    Mandatory fields not available in Dublin Core are filled with 'UNKNOWN'.
    """

    root = ET.fromstring(raw_xml)

    def get_one(tag: str) -> str:
        el = root.find(f".//dc:{tag}", DC_NS)
        return el.text.strip() if el is not None and el.text else "UNKNOWN"

    def get_all(tag: str) -> list:
        return [el.text.strip() for el in root.findall(f".//dc:{tag}", DC_NS) if el.text]

    mapped = {

        # =================================================
        # Metadata on Metadata
        # =================================================
        "Identifier": get_one("identifier"),
        "Publication Date": get_one("date"),
        "Language": "UNKNOWN",

        "Responsible Party": get_one("publisher"),
        "Email of the Responsible Organization or Individual": "UNKNOWN",

        # =================================================
        # Identification
        # =================================================
        "LandingPage": get_one("identifier"),
        "Title": get_one("title"),
        "Description": get_one("description"),
        "Dataset Identifier": get_one("identifier"),
        "Resource Type": "Dataset",

        # =================================================
        # Keyword Set
        # =================================================
        "Keyword": get_all("subject"),

        # =================================================
        # Data Contact Information
        # =================================================
        "Creator": get_all("creator"),
        "Contact Point": get_all("contributor"),
        "Publisher": get_one("publisher"),

        # =================================================
        # Spatial Properties
        # =================================================
        "Spatial Resolution": "UNKNOWN",
        "Spatial Resolution In Meters": "UNKNOWN",
        "Level of Details": "UNKNOWN",
        "Spatial Coverage": "UNKNOWN",
        "Reference System": "UNKNOWN",

        # =================================================
        # Temporal Properties
        # =================================================
        "Temporal Coverage": get_one("date"),
        "Temporal Resolution": "UNKNOWN",

        # =================================================
        # Intellectual Rights
        # =================================================
        "License": "UNKNOWN",
        "Access Rights": "UNKNOWN",

        # =================================================
        # Distribution
        # =================================================
        "Access URL": get_one("identifier"),
        "Dataset Format": "UNKNOWN",
        "Size": "UNKNOWN",

        # =================================================
        # Provenance / Internal Control
        # =================================================
        "Source Schema": "dublin_core",
        "Target Schema": "lterlife"
    }

    return mapped
