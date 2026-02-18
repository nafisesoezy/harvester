# LTER-LIFE Metadata Harvester

A FastAPI-based metadata harvester and GeoNetwork publisher for the LTER-LIFE catalogue.

This service harvests metadata from supported endpoints, converts records into LTER-LIFE JSON-LD format, checks for duplicates in GeoNetwork, and uploads only new records using batched imports.

---

## Functionality

### Harvest (`/run`)
- Detect protocol automatically (OAI-PMH, CSW, STAC, GeoNetwork, OData)
- Harvest records from the given URL
- Convert records to LTER-LIFE JSON-LD
- Export JSON-LD files into `./jsonld/`
- Create `jsonld_records.zip`

### Publish (`/push-to-catalog`)
- Extract title from each JSON-LD file
- Search GeoNetwork catalogue for duplicates

---

## Project Structure

```bash
harvester/
  api.py
  protocols/
  converters/
  exporters/
  templates/
  static/
  .env (not committed)
```

---

## Installation

### 1. Clone the repository
```bash
git clone https://github.com/nafisesoezy/harvester.git
cd harvester
```
### 2. Create virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate
```
### 3. Install dependencies
```bash
pip install fastapi uvicorn requests jinja2 python-multipart sickle python-dotenv OWSLib pystac-client
```
---

## Configuration
```bash
Create a `.env` file in the project root:
KEYCLOAK_AUTH_SERVER_URL=...
KEYCLOAK_REALM=...
KEYCLOAK_CLIENT_ID=...
KEYCLOAK_CLIENT_SECRET=...
KEYCLOAK_USERNAME=...
KEYCLOAK_PASSWORD=...
GEONETWORK_BASE_URL=...
GEONETWORK_PORTAL=srv
GEONETWORK_GROUP_ID=7
GN_IMPORT_BATCH_SIZE=15
```
The `.env` file is excluded via `.gitignore` and must not be committed.

---

## Run Locally
```bash
uvicorn api:app --host 0.0.0.0 --port 8000
```
Open in browser:
http://localhost:8000

---

## Deployment on VM
```bash
git clone https://github.com/nafisesoezy/harvester.git
cd harvester
python3 -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn requests jinja2 python-multipart sickle python-dotenv OWSLib pystac-client
uvicorn api:app --host 0.0.0.0 --port 8000
```
Then open:
http://<VM-IP>:8000

---

