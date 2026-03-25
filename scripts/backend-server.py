"""
WCC Contract Generator — Backend API Server (v2)

Serves endpoints for the HubSpot CRM card:
  GET  /program-data   — Full contract preview data (contact, program, intakes, fees)
  POST /generate       — Generate contract for a deal
  POST /reload         — Hot-reload data from Google Sheets
  GET  /health         — Health check

Deploy to: Railway, Render, Fly.io, or any Python host.

Usage:
  python backend-server.py
  # Runs on port 3000 (or PORT env var)
"""

import json
import csv
import os
import sys
import re
import threading
import tempfile
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Pacific Daylight Time (UTC-7) — BC is in PDT most of the year
PST = timezone(timedelta(hours=-7))

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from fee_matching import match_fees, resolve_fee_amounts, is_domestic, DOMESTIC_STATUSES

DATA_DIR = SCRIPT_DIR.parent / "data"


def require_env(name):
    """Return the value of an environment variable or abort at startup."""
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


PORT = int(os.environ.get("PORT", 3000))

GOOGLE_SHEETS_ID = require_env("GOOGLE_SHEETS_ID")
GOOGLE_API_KEY = require_env("GOOGLE_API_KEY")
WEBHOOK_SECRET = require_env("WEBHOOK_SECRET")

# Contact properties to fetch from HubSpot
CONTACT_PROPERTIES = [
    "firstname", "lastname", "email", "phone", "mobilephone",
    "date_of_birth", "address", "city", "state", "zip", "country",
    "residence_status", "citizenship", "gender",
]


# ---------------------------------------------------------------------------
# Google Sheets write client (for Contract Log)
# ---------------------------------------------------------------------------

_gspread_client = None

def get_gspread_client_server():
    """Return a gspread spreadsheet for writing (Contract Log).
    Uses GOOGLE_SERVICE_ACCOUNT_JSON env var. Returns None if not configured."""
    global _gspread_client
    if _gspread_client is not None:
        return _gspread_client

    sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    if not sa_json:
        return None

    try:
        import gspread
        from google.oauth2.service_account import Credentials
        creds_dict = json.loads(sa_json)
        scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(credentials)
        _gspread_client = client.open_by_key(GOOGLE_SHEETS_ID)
        return _gspread_client
    except Exception as e:
        print(f"Warning: Could not init gspread for contract log: {e}")
        return None


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def parse_csv_file(filepath):
    rows = []
    with open(filepath, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append({k.strip(): v.strip() for k, v in row.items()})
    return rows


def fetch_google_sheet_tab(tab_name):
    """Fetch a tab from Google Sheets and return as list of dicts."""
    import urllib.request as urlreq
    from urllib.parse import quote
    url = (
        f"https://sheets.googleapis.com/v4/spreadsheets/{GOOGLE_SHEETS_ID}"
        f"/values/{quote(tab_name)}?key={GOOGLE_API_KEY}"
    )
    req = urlreq.Request(url)
    with urlreq.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())
    values = data.get("values", [])
    if len(values) < 2:
        return []
    headers = [h.strip() for h in values[0]]
    rows = []
    for row in values[1:]:
        obj = {}
        for i, h in enumerate(headers):
            obj[h] = row[i].strip() if i < len(row) else ""
        rows.append(obj)
    return rows


def load_all_data():
    """Load Programs, Fees, and Outline Map from Google Sheets or CSV.

    Returns a single dict for atomic swap.
    Intakes are fetched live per request (they change frequently).
    """
    programs, fees, outline_map = [], [], {}

    if GOOGLE_SHEETS_ID and GOOGLE_API_KEY:
        try:
            programs = fetch_google_sheet_tab("Programs")
            fees = fetch_google_sheet_tab("Fees")
            try:
                outline_rows = fetch_google_sheet_tab("Outline Map")
                for row in outline_rows:
                    drive_id = row.get("google_drive_file_id", "").strip()
                    if drive_id:
                        outline_map[row["program_name"].lower()] = {
                            "outline_filename": row.get("outline_filename", "").strip(),
                            "google_drive_file_id": drive_id,
                        }
            except Exception:
                pass
            print(f"  Loaded from Google Sheets: {len(programs)} programs, {len(fees)} fees, {len(outline_map)} outlines")
            return {"programs": programs, "fees": fees, "outline_map": outline_map}
        except Exception as e:
            print(f"  Google Sheets failed ({e}), falling back to local CSV")

    # Fallback to local CSV
    programs = parse_csv_file(DATA_DIR / "demo-programs.csv")
    fees = parse_csv_file(DATA_DIR / "demo-fees.csv")
    map_path = DATA_DIR / "program-outline-map.csv"
    if map_path.exists():
        for row in parse_csv_file(map_path):
            drive_id = row.get("google_drive_file_id", "").strip()
            if drive_id:
                outline_map[row["program_name"].lower()] = {
                    "outline_filename": row.get("outline_filename", "").strip(),
                    "google_drive_file_id": drive_id,
                }
    print(f"  Loaded from local CSV: {len(programs)} programs, {len(fees)} fees, {len(outline_map)} outlines")
    return {"programs": programs, "fees": fees, "outline_map": outline_map}


try:
    _DATA = load_all_data()
except Exception as e:
    print(f"WARNING: Failed to load data at startup: {e}")
    _DATA = {"programs": [], "fees": [], "outline_map": {}}


# ---------------------------------------------------------------------------
# Per-deal generation lock to prevent concurrent generation
# ---------------------------------------------------------------------------

_generation_locks = {}
_locks_mutex = threading.Lock()


def acquire_deal_lock(deal_id):
    """Try to acquire a lock for a deal. Returns True if acquired, False if already locked."""
    with _locks_mutex:
        if deal_id in _generation_locks:
            return False
        _generation_locks[deal_id] = datetime.now(PST)
        return True


def release_deal_lock(deal_id):
    """Release a deal lock."""
    with _locks_mutex:
        _generation_locks.pop(deal_id, None)


def cleanup_stale_locks():
    """Remove locks older than 5 minutes (in case of crash)."""
    with _locks_mutex:
        now = datetime.now(PST)
        stale = [k for k, v in _generation_locks.items()
                 if (now - v).total_seconds() > 300]
        for k in stale:
            del _generation_locks[k]


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def fetch_intakes_live(program_name):
    """Fetch intakes from Google Sheets (live, not cached). Returns all open future intakes."""
    intakes = []
    if GOOGLE_SHEETS_ID and GOOGLE_API_KEY:
        try:
            all_intakes = fetch_google_sheet_tab("Intakes")
            now = datetime.now(PST).strftime("%Y-%m-%d")
            intakes = [
                i for i in all_intakes
                if i.get("program_name", "").lower() == program_name.lower()
                and i.get("status", "").lower() == "open"
                and i.get("intake_date", "") >= now
            ]
            intakes.sort(key=lambda x: x.get("intake_date", ""))
        except Exception as e:
            print(f"Intakes fetch error: {e}")
    return intakes


def fetch_intakes_live_all():
    """Fetch ALL intakes from Google Sheets (not filtered by program)."""
    if GOOGLE_SHEETS_ID and GOOGLE_API_KEY:
        try:
            return fetch_google_sheet_tab("Intakes")
        except Exception as e:
            print(f"Intakes fetch error: {e}")
    return []


def fetch_contact(deal_id):
    """Fetch the associated contact for a deal from HubSpot.

    Returns (contact_props, contact_missing) where contact_props is a dict
    of property values and contact_missing is a list of missing required fields.
    """
    import urllib.request as urlreq

    empty_contact = {prop: "" for prop in CONTACT_PROPERTIES}
    hs_token = require_env("HUBSPOT_TOKEN")

    # Get associated contact ID
    req = urlreq.Request(
        f"https://api.hubapi.com/crm/v3/objects/deals/{deal_id}/associations/contacts"
    )
    req.add_header("Authorization", f"Bearer {hs_token}")
    with urlreq.urlopen(req, timeout=15) as resp:
        assoc = json.loads(resp.read().decode())

    results = assoc.get("results", [])
    if not results:
        return empty_contact, ["No contact associated with deal"]

    contact_id = results[0].get("id")
    if not contact_id:
        return empty_contact, ["No contact associated with deal"]

    # Fetch contact properties
    props_param = ",".join(CONTACT_PROPERTIES)
    req2 = urlreq.Request(
        f"https://api.hubapi.com/crm/v3/objects/contacts/{contact_id}?properties={props_param}"
    )
    req2.add_header("Authorization", f"Bearer {hs_token}")
    with urlreq.urlopen(req2, timeout=15) as resp2:
        raw = json.loads(resp2.read().decode())

    props = raw.get("properties", {})

    # Build clean contact object
    contact = {}
    for key in CONTACT_PROPERTIES:
        contact[key] = props.get(key) or ""

    # Use phone or mobilephone
    if not contact["phone"] and contact.get("mobilephone"):
        contact["phone"] = contact["mobilephone"]

    # Check for missing required fields
    missing = []
    if not contact["firstname"]:
        missing.append("First Name")
    if not contact["lastname"]:
        missing.append("Last Name")
    if not contact["email"]:
        missing.append("Email")
    if not contact["residence_status"]:
        missing.append("Residence Status")

    # Address completeness
    addr_parts = [contact["address"], contact["city"], contact["state"], contact["zip"]]
    addr_filled = sum(1 for p in addr_parts if p)
    if addr_filled == 0:
        missing.append("Mailing Address (all fields empty)")
    elif addr_filled < 3:
        missing.append("Mailing Address (incomplete)")

    return contact, missing


def get_program_data(program_name, residence_status, intake_date=None, contact=None, contact_missing=None):
    """Return full contract preview data for the CRM card."""

    # Find program
    program = None
    for p in _DATA["programs"]:
        if p["program_name"].lower() == program_name.lower():
            program = p
            break

    if not program:
        return {"error": f"Program '{program_name}' not found"}

    # Determine fee tier
    domestic = is_domestic(residence_status)
    if domestic is None:
        tier = "Unknown"
    else:
        tier = "Domestic" if domestic else "International"

    # Fetch intakes live
    intakes = fetch_intakes_live(program_name)

    # Fee matching: use intake_date if provided, otherwise today
    reference_date = intake_date or datetime.now(PST).strftime("%Y-%m-%d")
    matched_fees, effective_from = match_fees(_DATA["fees"], program_name, reference_date)
    fee_items, total = resolve_fee_amounts(matched_fees, domestic)

    # Outline check — requires a Google Drive file ID
    outline_entry = _DATA["outline_map"].get(program_name.lower())
    has_outline = bool(outline_entry and outline_entry.get("google_drive_file_id"))

    return {
        "program": {
            "programName": program.get("program_name", ""),
            "programCode": program.get("program_code", ""),
            "credential": program.get("credential", ""),
        },
        "intakes": intakes,
        "fees": {
            "tier": tier,
            "effectiveFrom": effective_from,
            "items": fee_items,
            "total": total,
            "formattedTotal": f"${total:,.2f}",
            "count": len(fee_items),
        },
        "contact": contact or {prop: "" for prop in CONTACT_PROPERTIES},
        "contactMissing": contact_missing or [],
        "dealMissing": [],
        "hasOutline": has_outline,
    }


# ---------------------------------------------------------------------------
# HTTP Server
# ---------------------------------------------------------------------------

class RequestHandler(BaseHTTPRequestHandler):
    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_OPTIONS(self):
        self.send_json({})

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/health":
            self.send_json({
                "status": "ok",
                "service": "wcc-contract-generator",
                "schema": "v2",
                "programs": len(_DATA["programs"]),
                "feeItems": len(_DATA["fees"]),
                "outlines": len(_DATA["outline_map"]),
            })
            return

        if parsed.path == "/program-data":
            params = parse_qs(parsed.query)
            program_name = params.get("program_name", [""])[0]
            deal_id = params.get("deal_id", [""])[0]
            intake_date = params.get("intake_date", [""])[0]

            if not program_name:
                self.send_json({"error": "program_name is required"}, 400)
                return

            # Fetch contact from HubSpot
            contact = {prop: "" for prop in CONTACT_PROPERTIES}
            contact_missing = []
            deal_missing = []
            residence_status = ""

            if deal_id:
                try:
                    contact, contact_missing = fetch_contact(deal_id)
                    residence_status = contact.get("residence_status", "")
                except Exception as e:
                    print(f"HubSpot contact lookup error: {e}")
                    contact_missing.append("Contact lookup failed")

            result = get_program_data(
                program_name,
                residence_status,
                intake_date=intake_date or None,
                contact=contact,
                contact_missing=contact_missing,
            )
            result["dealMissing"] = deal_missing
            self.send_json(result)
            return

        self.send_json({"error": "Not found"}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)

        # --- /reload ---
        if parsed.path == "/reload":
            auth_header = self.headers.get("Authorization", "")
            if auth_header != f"Bearer {WEBHOOK_SECRET}":
                self.send_json({"error": "Unauthorized"}, 401)
                return

            global _DATA
            old_counts = (len(_DATA["programs"]), len(_DATA["fees"]), len(_DATA["outline_map"]))
            try:
                _DATA = load_all_data()  # single reference swap is atomic in CPython
                new_counts = (len(_DATA["programs"]), len(_DATA["fees"]), len(_DATA["outline_map"]))
                print(f"Data reloaded: programs {old_counts[0]}->{new_counts[0]}, fees {old_counts[1]}->{new_counts[1]}, outlines {old_counts[2]}->{new_counts[2]}")
                self.send_json({
                    "status": "reloaded",
                    "programs": new_counts[0],
                    "fees": new_counts[1],
                    "outlines": new_counts[2],
                })
            except Exception as e:
                print(f"Reload failed: {e}")
                self.send_json({"error": "Reload failed. Check server logs."}, 500)
            return

        # --- /generate ---
        if parsed.path == "/generate":
            auth_header = self.headers.get("Authorization", "")
            if auth_header != f"Bearer {WEBHOOK_SECRET}":
                self.send_json({"error": "Unauthorized"}, 401)
                return

            try:
                content_length = int(self.headers.get("Content-Length", 0))
            except (ValueError, TypeError):
                self.send_json({"error": "Invalid Content-Length"}, 400)
                return
            body = self.rfile.read(content_length).decode()

            try:
                data = json.loads(body) if body else {}
                if isinstance(data, str):
                    data = json.loads(data)
            except json.JSONDecodeError:
                self.send_json({"error": "Invalid JSON"}, 400)
                return

            deal_id = data.get("dealId")
            if not deal_id:
                self.send_json({"error": "dealId is required"}, 400)
                return

            if not re.match(r'^\d{1,20}$', str(deal_id)):
                self.send_json({"error": "Invalid dealId format"}, 400)
                return

            intake_date = data.get("intakeDate", "")
            if intake_date and not re.match(r'^\d{4}-\d{2}-\d{2}$', intake_date):
                self.send_json({"error": "Invalid intakeDate format (expected YYYY-MM-DD)"}, 400)
                return

            # Clean up any stale locks
            cleanup_stale_locks()

            # Acquire per-deal lock
            if not acquire_deal_lock(str(deal_id)):
                self.send_json({"error": "Contract generation already in progress for this deal. Please wait."}, 429)
                return

            data_file_path = None
            try:
                # Write cached data to temp file so the script doesn't need to call Google Sheets
                data_for_script = {
                    "programs": _DATA["programs"],
                    "fees": _DATA["fees"],
                    "outline_map": {k: v for k, v in _DATA["outline_map"].items()},
                }
                # Also fetch intakes live (they change frequently)
                intakes = fetch_intakes_live_all()
                data_for_script["intakes"] = intakes

                data_file = tempfile.NamedTemporaryFile(
                    mode='w', suffix='.json', delete=False, dir=tempfile.gettempdir()
                )
                json.dump(data_for_script, data_file)
                data_file.close()
                data_file_path = data_file.name

                # Build CLI args
                import subprocess
                cmd = [sys.executable, str(SCRIPT_DIR / "generate-contract-v2.py"), str(deal_id)]
                if intake_date:
                    cmd.append(intake_date)
                cmd.extend(["--data-file", data_file_path])

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=180,
                )

                if result.returncode != 0:
                    error_detail = result.stderr.strip() or result.stdout.strip()
                    print(f"Contract generation failed for deal {deal_id}: {error_detail}")

                    # Try to clean up orphaned PandaDoc document
                    orphan_doc_id = ""
                    for line in (result.stdout or "").split("\n"):
                        if "Document ID:" in line:
                            orphan_doc_id = line.split("Document ID:")[-1].strip()
                            break
                    if orphan_doc_id:
                        try:
                            import urllib.request
                            pandadoc_key = os.environ.get("PANDADOC_API_KEY", "")
                            if pandadoc_key:
                                del_req = urllib.request.Request(
                                    f"https://api.pandadoc.com/public/v1/documents/{orphan_doc_id}",
                                    method="DELETE",
                                )
                                del_req.add_header("Authorization", f"API-Key {pandadoc_key}")
                                urllib.request.urlopen(del_req, timeout=10)
                                print(f"Cleaned up orphaned document: {orphan_doc_id}")
                        except Exception as cleanup_err:
                            print(f"Could not clean up orphaned document {orphan_doc_id}: {cleanup_err}")

                    self.send_json({"error": "Contract generation failed. Check server logs."}, 500)
                    return

                # Parse output
                output = result.stdout
                doc_id = ""
                doc_url = ""
                student = ""
                program = ""
                fee_tier = ""
                total = ""
                fee_count = ""

                for line in output.split("\n"):
                    if "Document ID:" in line:
                        doc_id = line.split("Document ID:")[-1].strip()
                    if "View:" in line:
                        doc_url = line.split("View:")[-1].strip()
                    if "Student:" in line and not student:
                        student = line.split("Student:")[-1].strip()
                    if "Program:" in line and not program:
                        program = line.split("Program:")[-1].strip()
                    if "Fee tier:" in line or "-> Domestic" in line or "-> International" in line:
                        fee_tier = "Domestic" if "Domestic" in line else "International"
                    if "TOTAL:" in line:
                        total = line.split("TOTAL:")[-1].strip()
                    if "fee items" in line:
                        parts = line.strip().split()
                        if parts[0].isdigit():
                            fee_count = parts[0]

                # Write to Contract Log in Google Sheets
                try:
                    contract_log_row = [
                        f"CTR-{deal_id}-{datetime.now(PST).strftime('%H%M%S')}",
                        datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
                        str(deal_id),
                        student,
                        program,
                        intake_date or "",
                        fee_tier,
                        total,
                        "standard",
                        doc_id,
                        doc_url,
                        "draft",
                    ]
                    spreadsheet = get_gspread_client_server()
                    try:
                        log_ws = spreadsheet.worksheet("Contract Log")
                    except Exception:
                        log_ws = spreadsheet.add_worksheet(title="Contract Log", rows=1000, cols=12)
                        log_ws.append_row([
                            "contract_id", "generated_at", "deal_id", "student_name",
                            "program_name", "intake_date", "fee_tier", "total_amount",
                            "contract_type", "pandadoc_document_id", "pandadoc_url", "status",
                        ], value_input_option="RAW")
                    log_ws.append_row(contract_log_row, value_input_option="USER_ENTERED")
                    print(f"Contract logged: CTR-{deal_id}")
                except Exception as e:
                    print(f"Warning: Could not write contract log: {e}")

                has_outline = "Outline added" in output

                self.send_json({
                    "documentId": doc_id,
                    "documentUrl": doc_url,
                    "student": student,
                    "program": program,
                    "feeTier": fee_tier,
                    "total": total,
                    "feeCount": fee_count,
                    "hasOutline": has_outline,
                })
            finally:
                release_deal_lock(str(deal_id))
                # Clean up temp data file
                try:
                    if data_file_path and os.path.exists(data_file_path):
                        os.unlink(data_file_path)
                except Exception:
                    pass
            return

        self.send_json({"error": "Not found"}, 404)

    def log_message(self, format, *args):
        print(f"[{datetime.now(PST).strftime('%H:%M:%S')}] {format % args}")


def main():
    server = ThreadingHTTPServer(("0.0.0.0", PORT), RequestHandler)
    print(f"WCC Contract Generator Backend (v2)")
    print(f"  Listening on port {PORT}")
    print(f"  Programs: {len(_DATA['programs'])}")
    print(f"  Fee items: {len(_DATA['fees'])}")
    print(f"  Outline mappings: {len(_DATA['outline_map'])}")
    print(f"")
    print(f"Endpoints:")
    print(f"  GET  /health          Health check + data counts")
    print(f"  GET  /program-data    Full contract preview for CRM card")
    print(f"  POST /generate        Generate contract from deal ID")
    print(f"  POST /reload          Hot-reload data from Google Sheets")
    print(f"")
    print(f"Test:")
    print(f"  curl http://localhost:{PORT}/health")
    print(f'  curl "http://localhost:{PORT}/program-data?program_name=Health+Care+Assistant+Diploma&deal_id=58197228338"')
    print(f'  curl "http://localhost:{PORT}/program-data?program_name=Health+Care+Assistant+Diploma&deal_id=58197228338&intake_date=2026-04-14"')
    server.serve_forever()


if __name__ == "__main__":
    main()
