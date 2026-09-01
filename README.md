# LTER-LIFE Metadata Harvester

The **LTER-LIFE Metadata Harvester** is a FastAPI-based software pipeline for discovering, harmonising, enriching, and integrating metadata from heterogeneous scientific repositories into the **LTER-LIFE Digital Twin Catalogue**.

The harvester connects to repositories and catalogues through multiple metadata protocols, transforms heterogeneous metadata into the **LTER-LIFE metadata schema**, generates machine-actionable **JSON-LD**, and supports publication of new records to the LTER-LIFE GeoNetwork catalogue.

An optional **LLM-assisted enrichment** step complements conventional metadata harvesting by extracting missing information from resource landing pages while preserving metadata already obtained from the original source.

## Workflow

```text
External Scientific Repositories
            ↓
     Protocol Detection
            ↓
   Metadata Harvesting
            ↓
  Filtering and Normalisation
            ↓
  LTER-LIFE Schema Mapping
            ↓
 Optional LLM Enrichment
            ↓
     JSON-LD Generation
            ↓
     Duplicate Detection
            ↓
    Batched GeoNetwork Import
            ↓
 LTER-LIFE Digital Twin Catalogue
```

## Main Functionality

### Metadata harvesting

The harvester automatically detects and interacts with supported repository interfaces, including:

* **OAI-PMH**
* **CSW** (Catalogue Service for the Web)
* **STAC** (SpatioTemporal Asset Catalog)
* **GeoNetwork**
* **OData**

This allows metadata from independently developed scientific repositories to be accessed through a common harvesting workflow.

### LTER-LIFE metadata mapping

Harvested records may use different metadata structures and terminology. The conversion layer maps these heterogeneous records to the common **LTER-LIFE metadata model**.

The mapping process normalises source metadata and prepares a consistent representation that can be used across the catalogue.

### LLM-assisted metadata enrichment

Repository metadata can be incomplete even when additional information is available on the resource's landing page.

The optional LLM-assisted enrichment component addresses this by:

1. identifying LTER-LIFE fields that remain missing after conventional harvesting and mapping;
2. sending the resource landing page to the LLM enrichment service;
3. extracting potentially relevant metadata from the page;
4. filling only fields that are still missing; and
5. preserving values obtained from the original metadata source.

LLM enrichment therefore complements rather than replaces deterministic metadata harvesting and schema mapping.

### JSON-LD generation

Mapped records are exported as **JSON-LD**, providing a structured and machine-actionable representation of the harvested resources.

Generated records are stored in:

```text
jsonld/
```

and can also be packaged as:

```text
jsonld_records.zip
```

### Duplicate detection and catalogue publication

Before publishing harvested records, the system checks the target GeoNetwork catalogue for existing resources.

The publication workflow:

* extracts identifying information from generated records;
* searches the catalogue for existing resources;
* skips detected duplicates;
* retains new records for publication; and
* uploads new records to GeoNetwork in configurable batches.

Batching is used to support more reliable ingestion of larger collections.

## API

The FastAPI application provides the main interface to the harvesting pipeline.

Important endpoints include:

```text
GET  /
POST /run
POST /push-to-catalog
GET  /download/jsonld
GET  /download/jsonld-filtered
```

The web interface allows users to configure and run harvesting operations and inspect the resulting records.

## Project Structure

```text
harvester/
│
├── api.py
├── harvesterv3_Frontendv1.py
├── llm_harvester_client.py
│
├── protocols/
│   ├── oai.py
│   ├── csw.py
│   ├── stac.py
│   ├── geonetwork.py
│   └── odata.py
│
├── converters/
│   ├── lterlife_mapper.py
│   ├── dc_converter.py
│   └── schema_detector.py
│
├── exporters/
│   ├── jsonld_exporter.py
│   └── zip_utils.py
│
├── templates/
├── static/
│
└── .env
```

The `.env` file contains deployment-specific configuration and credentials and is **not included in the repository**.

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/nafisesoezy/harvester.git
cd harvester
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install fastapi uvicorn requests jinja2 python-multipart sickle python-dotenv OWSLib pystac-client
```

## Configuration

Create a `.env` file in the project root and provide the required configuration:

```text
KEYCLOAK_AUTH_SERVER_URL=...
KEYCLOAK_REALM=...
KEYCLOAK_CLIENT_ID=...
KEYCLOAK_CLIENT_SECRET=...
KEYCLOAK_USERNAME=...
KEYCLOAK_PASSWORD=...

GEONETWORK_BASE_URL=...
GEONETWORK_PORTAL=srv
GEONETWORK_GROUP_ID=...
GN_IMPORT_BATCH_SIZE=15

LLM_HARVESTER_BASE_URL=...
LLM_HARVESTER_API_KEY=...
LLM_HARVESTER_MODEL=...
LLM_HARVESTER_TIMEOUT_SEC=120
LLM_HARVESTER_POLL_INTERVAL_SEC=2
```

The `.env` file is excluded through `.gitignore` and must not be committed to version control.

## Run Locally

Start the FastAPI application:

```bash
uvicorn api:app --reload
```

Then open:

```text
http://127.0.0.1:8000
```

## Research Context

This software was developed within **LTER-LIFE** to support the discovery and integration of distributed scientific resources used in Digital Twin research.

The harvester complements the LTER-LIFE Digital Twin Catalogue by providing an automated path from heterogeneous external repositories to **structured, enriched, machine-actionable catalogue records**.

The work contributes to research on making distributed models, datasets, software, workflows, and other scientific assets more **discoverable, interoperable, reusable, and suitable for automated processing and composition**.

## Status

Research software under active development.
