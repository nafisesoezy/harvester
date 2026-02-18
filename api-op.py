from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
import os
import requests
import glob
import json
from typing import Optional
from harvesterv3_Frontend import run_harvest
from exporters.jsonld_exporter import export_jsonld_records, JSONLD_CONTEXT
from exporters.zip_utils import create_zip
from fastapi.staticfiles import StaticFiles

# =====================================================
# GeoNetwork configuration
# =====================================================
GEONETWORK_BASE_URL = os.getenv(
    "GEONETWORK_BASE_URL",
    "https://lter-life-catalogue.qcdis.org/geonetwork"
)
GEONETWORK_PORTAL = os.getenv("GEONETWORK_PORTAL", "srv")
GEONETWORK_GROUP_ID = os.getenv("GEONETWORK_GROUP_ID", "7")

# =====================================================
# Persistent HTTP session (IMPORTANT for GeoNetwork)
# =====================================================
session = requests.Session()
session.verify = False  # keep same behavior as before

# =====================================================
# Keycloak configuration (Service 1)
# =====================================================
KEYCLOAK_AUTH_SERVER_URL = os.getenv(
    "KEYCLOAK_AUTH_SERVER_URL",
    "https://lifewatch.lab.uvalight.net/auth"
)
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "vre")
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "lter-life-catalogue-harvester")
KEYCLOAK_CLIENT_SECRET = os.getenv(
    "KEYCLOAK_CLIENT_SECRET",
    "9hgligHr6TIGoI5jA7aKfy08J46h1w7T"
)
KEYCLOAK_USERNAME = os.getenv("KEYCLOAK_USERNAME", "harvester-service-account")
KEYCLOAK_PASSWORD = os.getenv("KEYCLOAK_PASSWORD", "nWkcPDm9ooFhsmJZ472fo5z97JNaAfuE")

# =====================================================
# App & templates
# =====================================================
app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# =====================================================
# Paths
# =====================================================
JSONLD_DIR = os.path.join(BASE_DIR, "jsonld")
ZIP_PATH = os.path.join(BASE_DIR, "jsonld_records.zip")

# =====================================================
# Helper: Keycloak token
# =====================================================
def get_keycloak_token() -> str:
    token_url = (
        f"{KEYCLOAK_AUTH_SERVER_URL.rstrip('/')}"
        f"/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"
    )

    resp = requests.post(
        token_url,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "password",
            "client_id": KEYCLOAK_CLIENT_ID,
            "client_secret": KEYCLOAK_CLIENT_SECRET,
            "username": KEYCLOAK_USERNAME,
            "password": KEYCLOAK_PASSWORD,
        },
        timeout=15,
        verify=False,
    )

    if resp.status_code != 200:
        raise HTTPException(
            status_code=401,
            detail=f"Keycloak token request failed: {resp.text}",
        )

    return resp.json()["access_token"]

# =====================================================
# UI FORM
# =====================================================
@app.get("/", response_class=HTMLResponse)
def ui_form(request: Request):
    return templates.TemplateResponse("form.html", {"request": request})

# =====================================================
# RUN HARVEST
# =====================================================
@app.post("/run", response_class=HTMLResponse)
def run_harvest_ui(
    request: Request,
    node_name: str = Form(...),
    url: str = Form(...),
    from_date: str = Form(None),
    until_date: str = Form(None),
    export_format: str = Form("jsonld"),
):
    result = run_harvest(
        portal_url=url,
        start_date=from_date or None,
        end_date=until_date or None,
    )

    xml_records = result.get("xml_records", [])
    ui_records = result.get("ui_records", [])

    record_count = (
        sum(1 for r in ui_records if isinstance(r, dict) and r.get("separator")) + 1
        if ui_records else 0
    )

    if export_format == "jsonld" and xml_records:
        export_jsonld_records(
            records=xml_records,
            output_dir=JSONLD_DIR,
            context=JSONLD_CONTEXT,
        )
        create_zip(JSONLD_DIR, ZIP_PATH)

    return templates.TemplateResponse(
        "form.html",
        {
            "request": request,
            "node_name": node_name,
            "url": url,
            "from_date": from_date,
            "until_date": until_date,
            "records": ui_records,
            "record_count": record_count,
            "export_format": export_format,
        },
    )

# =====================================================
# DOWNLOAD JSON-LD ZIP
# =====================================================
@app.get("/download/jsonld")
def download_jsonld_zip():
    if not os.path.exists(ZIP_PATH):
        raise HTTPException(status_code=404, detail="ZIP file not found")

    return FileResponse(
        ZIP_PATH,
        media_type="application/zip",
        filename="lterlife_jsonld_records.zip",
    )