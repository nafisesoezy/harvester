from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
import os
import requests
import glob


from harvesterv3_Frontend import run_harvest
from exporters.jsonld_exporter import export_jsonld_records, JSONLD_CONTEXT
from exporters.zip_utils import create_zip


# =====================================================
# GeoNetwork configuration
# =====================================================

GEONETWORK_BASE_URL = os.getenv(
    "GEONETWORK_BASE_URL",
    "http://145.100.135.123:8080/geonetwork"
)
GEONETWORK_PORTAL = os.getenv("GEONETWORK_PORTAL", "srv")
GEONETWORK_GROUP_ID = os.getenv("GEONETWORK_GROUP_ID", "7")

# =====================================================
# Persistent HTTP session (IMPORTANT for GeoNetwork)
# =====================================================

session = requests.Session()
session.verify = False   # keep same behavior as before

# =====================================================
# Keycloak configuration (Service 1)
# =====================================================

KEYCLOAK_AUTH_SERVER_URL = os.getenv(
    "KEYCLOAK_AUTH_SERVER_URL",
    "https://lifewatch.lab.uvalight.net/auth"
)
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "lwmetadata")
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "geonetwork-vm-nafiseh")
KEYCLOAK_CLIENT_SECRET = os.getenv(
    "KEYCLOAK_CLIENT_SECRET",
    "7wPdDYC7plqT3V0KWCsa3bQ0FqSvRoa3"
)

KEYCLOAK_USERNAME = os.getenv("KEYCLOAK_USERNAME", "harvester-service-account")
KEYCLOAK_PASSWORD = os.getenv("KEYCLOAK_PASSWORD", "LterLife2025")


# =====================================================
# App & templates
# =====================================================

app = FastAPI()
templates = Jinja2Templates(directory="templates")


# =====================================================
# Paths
# =====================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
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
        verify=False,  # remove if TLS is trusted
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
        }
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


# =====================================================
# PUSH TO GEONETWORK (KEYCLOAK)
# =====================================================
@app.post("/push-to-catalog", response_class=HTMLResponse)
def push_to_catalog(request: Request):
    """
    Push ONLY the first harvested JSON-LD record to GeoNetwork.
    Minimal single-record import for debugging.

    Key points:
    - Use /geonetwork/srv/api/... endpoints for this deployment.
    - Use a persistent requests.Session() (sticky JSESSIONID).
    - Include XSRF header for POST if GeoNetwork enforces CSRF.
    """

    # 0) Find JSON-LD files
    jsonld_files = sorted(glob.glob(os.path.join(JSONLD_DIR, "*.jsonld")))
    if not jsonld_files:
        raise HTTPException(status_code=400, detail="No JSON-LD files found. Run harvest first.")

    # Only take the first record
    jsonld_path = jsonld_files[0]
    filename = os.path.basename(jsonld_path)
    print("Importing single record:", filename)

    # 1) Get Keycloak token
    access_token = get_keycloak_token()

    # 2) Ensure sticky session + cookies (cluster/load balancer)
    # Touch GeoNetwork once (allow redirects) to get JSESSIONID + possibly XSRF-TOKEN
    try:
        session.get(f"{GEONETWORK_BASE_URL}/", timeout=10, allow_redirects=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reach GeoNetwork base URL: {e}")

    # 3) Verify API is reachable on the SAME session
    api_base = f"{GEONETWORK_BASE_URL}/srv/api"
    site_url = f"{api_base}/site"
    site_resp = session.get(
        site_url,
        headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        timeout=20,
    )

    print("SITE URL =", site_url)
    print("site status:", site_resp.status_code)
    print("site body:", site_resp.text[:300])

    if site_resp.status_code != 200:
        raise HTTPException(
            status_code=500,
            detail=f"GeoNetwork site check failed: {site_resp.status_code} {site_resp.text}",
        )

    # 4) Prepare CSRF/XSRF header if GeoNetwork requires it for POST
    # (GeoNetwork often sets XSRF-TOKEN cookie on GETs; requests.Session keeps it.)
    xsrf = session.cookies.get("XSRF-TOKEN")
    print("XSRF cookie:", xsrf)

    post_headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }
    if xsrf:
        post_headers["X-XSRF-TOKEN"] = xsrf

    # 5) Import the single JSON-LD file
    import_url = f"{api_base}/records"
    with open(jsonld_path, "rb") as f:
        resp = session.post(
            import_url,
            files={"file": (filename, f, "application/ld+json")},
            data={
                # Must match your Importer + JsonldVisitor selection
                "file_type": "jsonld",
                "fileType": "jsonld",

                "metadataType": "METADATA",
                "uuidProcessing": "GENERATEUUID",
                "group": GEONETWORK_GROUP_ID,  # "7" = Later Life
                "publishToAll": "false",
                "rejectIfInvalid": "false",
                "assignToCatalog": "true",
            },
            headers=post_headers,   # ✅ use the CSRF-aware headers
            timeout=60,
        )

    # 6) Debug output
    print("=== IMPORT DEBUG ===")
    print("file:", filename)
    print("status:", resp.status_code)
    print("content-type:", resp.headers.get("content-type"))
    print("body:", resp.text[:4000])
    print("====================")

    if resp.status_code not in (200, 201):
        raise HTTPException(status_code=500, detail=f"GeoNetwork import failed: {resp.status_code} {resp.text}")

    # 7) Return success to UI
    try:
        report = resp.json()
    except Exception:
        report = {"status": resp.status_code, "body": resp.text}

    return templates.TemplateResponse("form.html", {"request": request, "push_report": report})
