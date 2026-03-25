"""
WCC Contract Generator — Streamlit Admin Panel

Reads/writes Google Sheets data for Programs, Intakes, Fees, Outline Map.
Provides validated CRUD with field-level audit logging.

Environment variables:
    ADMIN_PASSWORD              — Password for admin login
    GOOGLE_SHEETS_ID            — Google Sheets spreadsheet ID
    GOOGLE_SERVICE_ACCOUNT_JSON — Service account credentials JSON string
"""

import json
import os
from datetime import datetime, date

import gspread
import pandas as pd
import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CREDENTIAL_OPTIONS = ["Certificate", "Diploma", "Bachelor"]
CAMPUS_OPTIONS = ["Burnaby", "Surrey", "New Westminster", "Online"]
STATUS_OPTIONS = ["Open", "Closed", "Waitlist"]
DELIVERY_OPTIONS = ["In-Class", "Distance", "Combined", "Hybrid"]
FEE_NAME_OPTIONS = [
    "Application Fee",
    "Administration Fee",
    "Registration Fee",
    "Assessment Fee",
    "Tuition Fee",
    "Tuition Fee Per Credit",
    "Book Fee",
    "Course Materials",
    "Ground School Fee",
    "Other Fee",
    "Scholarship",
]

SHEET_PROGRAMS = "Programs"
SHEET_INTAKES = "Intakes"
SHEET_FEES = "Fees"
SHEET_OUTLINE_MAP = "Outline Map"
SHEET_AUDIT_LOG = "Audit Log"
SHEET_CONTRACT_LOG = "Contract Log"

AUDIT_HEADERS = [
    "timestamp",
    "user",
    "action",
    "tab_name",
    "row_identifier",
    "field_name",
    "old_value",
    "new_value",
]

STATUS_COLORS = {
    "Open": "#22c55e",
    "Closed": "#ef4444",
    "Waitlist": "#eab308",
}

NAV_ITEMS = [
    "Programs",
    "Intakes",
    "Fees",
    "Outline Map",
    "Audit Log",
    "Contract Log",
]

NAV_ICONS = {
    "Programs": "🎓",
    "Intakes": "📅",
    "Fees": "💰",
    "Outline Map": "📋",
    "Audit Log": "📝",
    "Contract Log": "📄",
}

# ---------------------------------------------------------------------------
# Google Sheets connection
# ---------------------------------------------------------------------------


@st.cache_resource(ttl=300)
def get_gspread_client():
    """Return an authorized gspread client using the service account.

    Supports two formats:
    1. GOOGLE_SERVICE_ACCOUNT_JSON env var (JSON string)
    2. Streamlit secrets TOML section [GOOGLE_SERVICE_ACCOUNT] (dict)
    """
    creds_dict = None

    # Try Streamlit secrets TOML section first
    if hasattr(st, "secrets"):
        try:
            sa = st.secrets.get("GOOGLE_SERVICE_ACCOUNT")
            if sa:
                creds_dict = dict(sa)
        except Exception:
            pass

        # Try JSON string in secrets
        if creds_dict is None:
            try:
                creds_json = st.secrets.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
                if creds_json:
                    creds_dict = json.loads(creds_json)
            except Exception:
                pass

    # Fall back to env var
    if creds_dict is None:
        creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
        if creds_json:
            creds_dict = json.loads(creds_json)

    if not creds_dict:
        st.error("Service account credentials not found. Set GOOGLE_SERVICE_ACCOUNT in Streamlit secrets or GOOGLE_SERVICE_ACCOUNT_JSON env var.")
        st.stop()

    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(credentials)


def open_spreadsheet():
    """Open the target spreadsheet by ID."""
    sheet_id = ""
    # Try Streamlit secrets first, then env var
    if hasattr(st, "secrets"):
        sheet_id = st.secrets.get("GOOGLE_SHEETS_ID", "")
    if not sheet_id:
        sheet_id = os.environ.get("GOOGLE_SHEETS_ID", "")
    if not sheet_id:
        st.error("GOOGLE_SHEETS_ID not found in secrets or environment.")
        st.stop()

    client = get_gspread_client()
    return client.open_by_key(sheet_id)


def read_sheet(sheet_name: str) -> pd.DataFrame:
    """Read a worksheet into a DataFrame. Returns empty DataFrame if sheet missing."""
    try:
        spreadsheet = open_spreadsheet()
        worksheet = spreadsheet.worksheet(sheet_name)
        records = worksheet.get_all_records()
        return pd.DataFrame(records) if records else pd.DataFrame()
    except gspread.exceptions.WorksheetNotFound:
        return pd.DataFrame()
    except Exception as exc:
        st.error(f"Error reading sheet '{sheet_name}': {exc}")
        return pd.DataFrame()


def ensure_audit_sheet():
    """Create the Audit Log sheet if it does not exist."""
    spreadsheet = open_spreadsheet()
    try:
        spreadsheet.worksheet(SHEET_AUDIT_LOG)
    except gspread.exceptions.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=SHEET_AUDIT_LOG, rows=1000, cols=8)
        ws.append_row(AUDIT_HEADERS, value_input_option="RAW")


def append_row(sheet_name: str, row_values: list):
    """Append a single row to a worksheet."""
    spreadsheet = open_spreadsheet()
    worksheet = spreadsheet.worksheet(sheet_name)
    worksheet.append_row(row_values, value_input_option="USER_ENTERED")


def update_row(sheet_name: str, row_index: int, row_values: list):
    """Overwrite a row in the worksheet. row_index is 1-based and includes header."""
    spreadsheet = open_spreadsheet()
    worksheet = spreadsheet.worksheet(sheet_name)
    col_count = len(row_values)
    end_col = gspread.utils.rowcol_to_a1(row_index, col_count).split("!")[-1]
    start_col = gspread.utils.rowcol_to_a1(row_index, 1).split("!")[-1]
    cell_range = f"{start_col}:{end_col}"
    worksheet.update(cell_range, [row_values], value_input_option="USER_ENTERED")


def delete_row(sheet_name: str, row_index: int):
    """Delete a row from the worksheet. row_index is 1-based and includes header."""
    spreadsheet = open_spreadsheet()
    worksheet = spreadsheet.worksheet(sheet_name)
    worksheet.delete_rows(row_index)


# ---------------------------------------------------------------------------
# Audit logging
# ---------------------------------------------------------------------------


def log_audit(action: str, tab_name: str, row_identifier: str,
              field_name: str, old_value: str, new_value: str):
    """Write a single audit record."""
    ensure_audit_sheet()
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    user = "admin"
    append_row(SHEET_AUDIT_LOG, [
        timestamp, user, action, tab_name, row_identifier,
        field_name, str(old_value), str(new_value),
    ])


def log_create(tab_name: str, row_identifier: str, fields: dict):
    """Log a CREATE action for every field."""
    for field_name, value in fields.items():
        log_audit("CREATE", tab_name, row_identifier, field_name, "", str(value))


def log_update(tab_name: str, row_identifier: str, old_row: dict, new_row: dict):
    """Log an UPDATE action for each changed field."""
    for key in new_row:
        old_val = str(old_row.get(key, ""))
        new_val = str(new_row[key])
        if old_val != new_val:
            log_audit("UPDATE", tab_name, row_identifier, key, old_val, new_val)


def log_delete(tab_name: str, row_identifier: str, fields: dict):
    """Log a DELETE action for every field."""
    for field_name, value in fields.items():
        log_audit("DELETE", tab_name, row_identifier, field_name, str(value), "")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def get_program_names() -> list[str]:
    """Return sorted list of program names from the Programs sheet."""
    df = read_sheet(SHEET_PROGRAMS)
    if df.empty or "program_name" not in df.columns:
        return []
    return sorted(df["program_name"].dropna().unique().tolist())


def find_row_index(sheet_name: str, match_col: str, match_val: str) -> int | None:
    """Return 1-based row index (including header) of the first matching row."""
    spreadsheet = open_spreadsheet()
    worksheet = spreadsheet.worksheet(sheet_name)
    all_values = worksheet.get_all_values()
    if not all_values:
        return None
    headers = all_values[0]
    if match_col not in headers:
        return None
    col_idx = headers.index(match_col)
    for i, row in enumerate(all_values[1:], start=2):
        if len(row) > col_idx and row[col_idx] == match_val:
            return i
    return None


def find_row_index_multi(sheet_name: str, match_dict: dict) -> int | None:
    """Return 1-based row index matching multiple column values."""
    spreadsheet = open_spreadsheet()
    worksheet = spreadsheet.worksheet(sheet_name)
    all_values = worksheet.get_all_values()
    if not all_values:
        return None
    headers = all_values[0]
    col_indices = {}
    for col_name in match_dict:
        if col_name not in headers:
            return None
        col_indices[col_name] = headers.index(col_name)

    for i, row in enumerate(all_values[1:], start=2):
        if all(
            len(row) > col_indices[c] and row[col_indices[c]] == str(match_dict[c])
            for c in match_dict
        ):
            return i
    return None


def safe_float(value, default=0.0):
    """Convert to float safely."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value, default=0):
    """Convert to int safely."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def filter_dataframe(df: pd.DataFrame, search_text: str) -> pd.DataFrame:
    """Filter DataFrame rows by a case-insensitive text search across all columns."""
    if not search_text or not search_text.strip():
        return df
    query = search_text.strip().lower()
    mask = df.apply(
        lambda row: any(query in str(val).lower() for val in row),
        axis=1,
    )
    return df[mask]


def colored_status(status: str) -> str:
    """Return an HTML-colored status badge string."""
    color = STATUS_COLORS.get(status, "#6b7280")
    return f'<span style="background:{color};color:white;padding:2px 10px;border-radius:12px;font-size:0.85em;font-weight:600;">{status}</span>'


def init_session_key(key: str, default=None):
    """Initialize a session state key if not already set."""
    if key not in st.session_state:
        st.session_state[key] = default


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


def check_auth():
    """Simple password-based authentication."""
    if st.session_state.get("authenticated"):
        return True

    st.title("WCC Admin Panel — Login")
    password = st.text_input("Password", type="password", key="login_pw")
    if st.button("Login"):
        expected = ""
        if hasattr(st, "secrets"):
            expected = st.secrets.get("ADMIN_PASSWORD", "")
        if not expected:
            expected = os.environ.get("ADMIN_PASSWORD", "")
        if not expected:
            st.error("ADMIN_PASSWORD not found in secrets or environment.")
            return False
        if password == expected:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    return False


# ---------------------------------------------------------------------------
# Tab: Programs
# ---------------------------------------------------------------------------


def _validate_program(name: str, code: str, existing_df: pd.DataFrame) -> list[str]:
    errors = []
    if not name or not name.strip():
        errors.append("Program Name is required.")
    if not code or not code.strip():
        errors.append("Program Code is required.")
    if not existing_df.empty:
        if name.strip() in existing_df["program_name"].values:
            errors.append(f"Program Name '{name.strip()}' already exists.")
        if code.strip().upper() in existing_df["program_code"].str.upper().values:
            errors.append(f"Program Code '{code.strip().upper()}' already exists.")
    return errors


def render_programs_tab():
    df = read_sheet(SHEET_PROGRAMS)

    # --- Summary metrics ---
    m1, m2, m3, m4 = st.columns(4)
    total = len(df) if not df.empty else 0
    cred_counts = {}
    if not df.empty and "credential" in df.columns:
        cred_counts = df["credential"].value_counts().to_dict()
    m1.metric("Total Programs", total)
    m2.metric("Certificates", cred_counts.get("Certificate", 0))
    m3.metric("Diplomas", cred_counts.get("Diploma", 0))
    m4.metric("Bachelors", cred_counts.get("Bachelor", 0))

    st.divider()

    # --- Search bar ---
    search = st.text_input("Search programs...", key="prog_search", placeholder="Type to filter by name, code, or credential")
    display_df = filter_dataframe(df, search) if not df.empty else df

    # --- Data table ---
    if not display_df.empty:
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "program_name": st.column_config.TextColumn("Program Name", width="large"),
                "program_code": st.column_config.TextColumn("Code", width="small"),
                "credential": st.column_config.TextColumn("Credential", width="medium"),
            },
        )
    else:
        st.info("No programs found." if not search else "No programs match your search.")

    st.divider()

    # --- Action buttons ---
    init_session_key("prog_mode", None)
    init_session_key("prog_edit_name", None)
    init_session_key("prog_delete_name", None)

    btn_cols = st.columns([1, 1, 1, 4])
    with btn_cols[0]:
        if st.button("Add New", key="prog_add_btn", use_container_width=True):
            st.session_state["prog_mode"] = "add"
            st.session_state["prog_edit_name"] = None
            st.session_state["prog_delete_name"] = None
    with btn_cols[1]:
        if st.button("Edit", key="prog_edit_btn", use_container_width=True, disabled=df.empty):
            st.session_state["prog_mode"] = "edit"
            st.session_state["prog_delete_name"] = None
    with btn_cols[2]:
        if st.button("Delete", key="prog_del_btn", use_container_width=True, disabled=df.empty, type="secondary"):
            st.session_state["prog_mode"] = "delete"
            st.session_state["prog_edit_name"] = None

    mode = st.session_state.get("prog_mode")

    # --- Add form ---
    if mode == "add":
        st.subheader("Add Program")
        with st.form("add_program", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                name = st.text_input("Program Name *")
            with c2:
                code = st.text_input("Program Code *")
            with c3:
                credential = st.selectbox("Credential *", CREDENTIAL_OPTIONS)
            fc1, fc2 = st.columns([1, 6])
            with fc1:
                submitted = st.form_submit_button("Add Program", type="primary")
            with fc2:
                cancel = st.form_submit_button("Cancel")

        if cancel:
            st.session_state["prog_mode"] = None
            st.rerun()
        if submitted:
            errors = _validate_program(name, code, df)
            if errors:
                for e in errors:
                    st.error(e)
            else:
                row = [name.strip(), code.strip().upper(), credential]
                append_row(SHEET_PROGRAMS, row)
                log_create(SHEET_PROGRAMS, name.strip(), {
                    "program_name": name.strip(),
                    "program_code": code.strip().upper(),
                    "credential": credential,
                })
                st.session_state["prog_mode"] = None
                st.toast(f"Program '{name.strip()}' added successfully!")
                st.rerun()

    # --- Edit form ---
    if mode == "edit" and not df.empty:
        st.subheader("Edit Program")
        sel = st.selectbox("Select program to edit", df["program_name"].tolist(), key="edit_prog_sel")
        if sel:
            row_data = df[df["program_name"] == sel].iloc[0].to_dict()
            with st.form("edit_program"):
                c1, c2 = st.columns(2)
                with c1:
                    new_code = st.text_input("Program Code", value=str(row_data.get("program_code", "")))
                with c2:
                    new_cred = st.selectbox(
                        "Credential",
                        CREDENTIAL_OPTIONS,
                        index=CREDENTIAL_OPTIONS.index(row_data["credential"])
                        if row_data.get("credential") in CREDENTIAL_OPTIONS else 0,
                    )
                fc1, fc2 = st.columns([1, 6])
                with fc1:
                    submitted = st.form_submit_button("Save Changes", type="primary")
                with fc2:
                    cancel = st.form_submit_button("Cancel")

            if cancel:
                st.session_state["prog_mode"] = None
                st.rerun()
            if submitted:
                new_row = {
                    "program_name": sel,
                    "program_code": new_code.strip().upper(),
                    "credential": new_cred,
                }
                idx = find_row_index(SHEET_PROGRAMS, "program_name", sel)
                if idx:
                    update_row(SHEET_PROGRAMS, idx, list(new_row.values()))
                    log_update(SHEET_PROGRAMS, sel, row_data, new_row)
                    st.session_state["prog_mode"] = None
                    st.toast("Program updated successfully!")
                    st.rerun()

    # --- Delete with confirmation ---
    if mode == "delete" and not df.empty:
        st.subheader("Delete Program")
        sel_del = st.selectbox("Select program to delete", df["program_name"].tolist(), key="del_prog_sel")
        if sel_del:
            old = df[df["program_name"] == sel_del].iloc[0].to_dict()
            st.warning(f"You are about to delete **{sel_del}** (Code: {old.get('program_code', 'N/A')}, Credential: {old.get('credential', 'N/A')})")
            st.caption("This action cannot be undone.")
            dc1, dc2, dc3 = st.columns([1, 1, 5])
            with dc1:
                if st.button("Confirm Delete", type="primary", key="prog_confirm_del"):
                    idx = find_row_index(SHEET_PROGRAMS, "program_name", sel_del)
                    if idx:
                        delete_row(SHEET_PROGRAMS, idx)
                        log_delete(SHEET_PROGRAMS, sel_del, old)
                        st.session_state["prog_mode"] = None
                        st.toast(f"Program '{sel_del}' deleted.")
                        st.rerun()
            with dc2:
                if st.button("Cancel", key="prog_cancel_del"):
                    st.session_state["prog_mode"] = None
                    st.rerun()


# ---------------------------------------------------------------------------
# Tab: Intakes
# ---------------------------------------------------------------------------


def _validate_intake(intake_dt, end_dt) -> list[str]:
    errors = []
    if end_dt <= intake_dt:
        errors.append("End Date must be after Intake Date.")
    return errors


def render_intakes_tab():
    df = read_sheet(SHEET_INTAKES)
    programs = get_program_names()

    # --- Summary metrics ---
    m1, m2, m3, m4 = st.columns(4)
    total = len(df) if not df.empty else 0
    status_counts = {}
    if not df.empty and "status" in df.columns:
        status_counts = df["status"].value_counts().to_dict()
    m1.metric("Total Intakes", total)
    m2.metric("Open", status_counts.get("Open", 0))
    m3.metric("Closed", status_counts.get("Closed", 0))
    m4.metric("Waitlist", status_counts.get("Waitlist", 0))

    st.divider()

    # --- Filters ---
    fc1, fc2, fc3 = st.columns([2, 1, 3])
    with fc1:
        prog_filter = st.selectbox("Filter by Program", ["All Programs"] + programs, key="int_prog_filter")
    with fc2:
        status_filter = st.selectbox("Filter by Status", ["All"] + STATUS_OPTIONS, key="int_status_filter")
    with fc3:
        search = st.text_input("Search intakes...", key="int_search", placeholder="Type to search across all fields")

    display_df = df.copy() if not df.empty else df
    if not display_df.empty:
        if prog_filter != "All Programs" and "program_name" in display_df.columns:
            display_df = display_df[display_df["program_name"] == prog_filter]
        if status_filter != "All" and "status" in display_df.columns:
            display_df = display_df[display_df["status"] == status_filter]
        display_df = filter_dataframe(display_df, search)

    # --- Data table with color-coded status ---
    if not display_df.empty:
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "program_name": st.column_config.TextColumn("Program", width="large"),
                "intake_date": st.column_config.TextColumn("Intake Date", width="small"),
                "end_date": st.column_config.TextColumn("End Date", width="small"),
                "campus": st.column_config.TextColumn("Campus", width="small"),
                "hours": st.column_config.TextColumn("Hours", width="small"),
                "weeks": st.column_config.TextColumn("Weeks", width="small"),
                "spots_available": st.column_config.NumberColumn("Spots", width="small"),
                "status": st.column_config.TextColumn("Status", width="small"),
                "domestic_delivery_method": st.column_config.TextColumn("Dom. Delivery", width="small"),
                "international_delivery_method": st.column_config.TextColumn("Intl. Delivery", width="small"),
            },
        )
        st.caption(f"Showing {len(display_df)} of {total} intakes")
    else:
        st.info("No intakes found." if not search else "No intakes match your filters.")

    if not programs:
        st.warning("Add programs first before managing intakes.")
        return

    st.divider()

    # --- Action buttons ---
    init_session_key("int_mode", None)

    btn_cols = st.columns([1, 1, 1, 4])
    with btn_cols[0]:
        if st.button("Add New", key="int_add_btn", use_container_width=True):
            st.session_state["int_mode"] = "add"
    with btn_cols[1]:
        if st.button("Edit", key="int_edit_btn", use_container_width=True, disabled=df.empty):
            st.session_state["int_mode"] = "edit"
    with btn_cols[2]:
        if st.button("Delete", key="int_del_btn", use_container_width=True, disabled=df.empty, type="secondary"):
            st.session_state["int_mode"] = "delete"

    mode = st.session_state.get("int_mode")

    # --- Add form ---
    if mode == "add":
        st.subheader("Add Intake")
        with st.form("add_intake", clear_on_submit=True):
            r1c1, r1c2 = st.columns(2)
            with r1c1:
                prog = st.selectbox("Program Name *", programs, key="add_int_prog")
            with r1c2:
                campus = st.selectbox("Campus *", CAMPUS_OPTIONS)

            r2c1, r2c2, r2c3, r2c4 = st.columns(4)
            with r2c1:
                intake_dt = st.date_input("Intake Date *", key="add_int_dt")
            with r2c2:
                end_dt = st.date_input("End Date *", key="add_int_end")
            with r2c3:
                hours = st.text_input("Hours", placeholder="optional")
            with r2c4:
                weeks = st.text_input("Weeks", placeholder="optional")

            r3c1, r3c2, r3c3 = st.columns(3)
            with r3c1:
                spots = st.number_input("Spots Available", min_value=0, value=0, step=1)
            with r3c2:
                dom_del = st.selectbox("Domestic Delivery *", DELIVERY_OPTIONS, key="add_int_dom")
            with r3c3:
                intl_del = st.selectbox("International Delivery *", DELIVERY_OPTIONS, key="add_int_intl")

            r4c1, r4c2 = st.columns([1, 1])
            with r4c1:
                status = st.selectbox("Status *", STATUS_OPTIONS)

            fc1, fc2 = st.columns([1, 6])
            with fc1:
                submitted = st.form_submit_button("Add Intake", type="primary")
            with fc2:
                cancel = st.form_submit_button("Cancel")

        if cancel:
            st.session_state["int_mode"] = None
            st.rerun()
        if submitted:
            errors = _validate_intake(intake_dt, end_dt)
            if errors:
                for e in errors:
                    st.error(e)
            else:
                row_vals = [
                    prog,
                    str(intake_dt),
                    str(end_dt),
                    campus,
                    hours if hours else "",
                    weeks if weeks else "",
                    int(spots),
                    status,
                    dom_del,
                    intl_del,
                ]
                append_row(SHEET_INTAKES, row_vals)
                identifier = f"{prog}|{intake_dt}|{campus}"
                field_dict = dict(zip(
                    ["program_name", "intake_date", "end_date", "campus",
                     "hours", "weeks", "spots_available", "status",
                     "domestic_delivery_method", "international_delivery_method"],
                    [str(v) for v in row_vals],
                ))
                log_create(SHEET_INTAKES, identifier, field_dict)
                st.session_state["int_mode"] = None
                st.toast("Intake added successfully!")
                st.rerun()

    # --- Edit form ---
    if mode == "edit" and not df.empty:
        st.subheader("Edit Intake")
        df_edit = df.copy()
        df_edit["_label"] = df_edit.apply(
            lambda r: f"{r.get('program_name', '')} | {r.get('intake_date', '')} | {r.get('campus', '')}",
            axis=1,
        )
        sel = st.selectbox("Select intake to edit", df_edit["_label"].tolist(), key="edit_int_sel")
        sel_idx = df_edit[df_edit["_label"] == sel].index[0]
        row_data = df_edit.iloc[sel_idx].to_dict()

        with st.form("edit_intake"):
            r1c1, r1c2, r1c3 = st.columns(3)
            with r1c1:
                new_campus = st.selectbox(
                    "Campus",
                    CAMPUS_OPTIONS,
                    index=CAMPUS_OPTIONS.index(row_data["campus"])
                    if row_data.get("campus") in CAMPUS_OPTIONS else 0,
                )
            with r1c2:
                new_hours = st.text_input("Hours", value=str(row_data.get("hours", "")))
            with r1c3:
                new_weeks = st.text_input("Weeks", value=str(row_data.get("weeks", "")))

            r2c1, r2c2, r2c3 = st.columns(3)
            with r2c1:
                new_spots = st.number_input(
                    "Spots Available", min_value=0,
                    value=safe_int(row_data.get("spots_available", 0)),
                    step=1,
                )
            with r2c2:
                new_status = st.selectbox(
                    "Status",
                    STATUS_OPTIONS,
                    index=STATUS_OPTIONS.index(row_data["status"])
                    if row_data.get("status") in STATUS_OPTIONS else 0,
                )
            with r2c3:
                pass  # spacer

            r3c1, r3c2 = st.columns(2)
            with r3c1:
                new_dom = st.selectbox(
                    "Domestic Delivery Method",
                    DELIVERY_OPTIONS,
                    index=DELIVERY_OPTIONS.index(row_data["domestic_delivery_method"])
                    if row_data.get("domestic_delivery_method") in DELIVERY_OPTIONS else 0,
                    key="edit_int_dom",
                )
            with r3c2:
                new_intl = st.selectbox(
                    "International Delivery Method",
                    DELIVERY_OPTIONS,
                    index=DELIVERY_OPTIONS.index(row_data["international_delivery_method"])
                    if row_data.get("international_delivery_method") in DELIVERY_OPTIONS else 0,
                    key="edit_int_intl",
                )

            fc1, fc2 = st.columns([1, 6])
            with fc1:
                submitted = st.form_submit_button("Save Changes", type="primary")
            with fc2:
                cancel = st.form_submit_button("Cancel")

        if cancel:
            st.session_state["int_mode"] = None
            st.rerun()
        if submitted:
            new_row = {
                "program_name": row_data["program_name"],
                "intake_date": row_data["intake_date"],
                "end_date": row_data["end_date"],
                "campus": new_campus,
                "hours": new_hours,
                "weeks": new_weeks,
                "spots_available": int(new_spots),
                "status": new_status,
                "domestic_delivery_method": new_dom,
                "international_delivery_method": new_intl,
            }
            match_dict = {
                "program_name": row_data["program_name"],
                "intake_date": str(row_data["intake_date"]),
                "campus": str(row_data.get("campus", "")),
            }
            idx = find_row_index_multi(SHEET_INTAKES, match_dict)
            if idx:
                update_row(SHEET_INTAKES, idx, [str(v) for v in new_row.values()])
                identifier = f"{row_data['program_name']}|{row_data['intake_date']}|{row_data.get('campus', '')}"
                log_update(SHEET_INTAKES, identifier, row_data, new_row)
                st.session_state["int_mode"] = None
                st.toast("Intake updated successfully!")
                st.rerun()

    # --- Delete with confirmation ---
    if mode == "delete" and not df.empty:
        st.subheader("Delete Intake")
        df_del = df.copy()
        if "_label" not in df_del.columns:
            df_del["_label"] = df_del.apply(
                lambda r: f"{r.get('program_name', '')} | {r.get('intake_date', '')} | {r.get('campus', '')}",
                axis=1,
            )
        sel_del = st.selectbox("Select intake to delete", df_del["_label"].tolist(), key="del_int_sel")
        sel_idx = df_del[df_del["_label"] == sel_del].index[0]
        row_data = df_del.iloc[sel_idx].to_dict()

        st.warning(
            f"You are about to delete intake: **{row_data.get('program_name', '')}** "
            f"({row_data.get('intake_date', '')} - {row_data.get('end_date', '')}), "
            f"Campus: {row_data.get('campus', '')}, Status: {row_data.get('status', '')}"
        )
        st.caption("This action cannot be undone.")
        dc1, dc2, dc3 = st.columns([1, 1, 5])
        with dc1:
            if st.button("Confirm Delete", type="primary", key="int_confirm_del"):
                match_dict = {
                    "program_name": row_data["program_name"],
                    "intake_date": str(row_data["intake_date"]),
                    "campus": str(row_data.get("campus", "")),
                }
                idx = find_row_index_multi(SHEET_INTAKES, match_dict)
                if idx:
                    old = {k: v for k, v in row_data.items() if k != "_label"}
                    delete_row(SHEET_INTAKES, idx)
                    identifier = f"{row_data['program_name']}|{row_data['intake_date']}|{row_data.get('campus', '')}"
                    log_delete(SHEET_INTAKES, identifier, old)
                    st.session_state["int_mode"] = None
                    st.toast("Intake deleted.")
                    st.rerun()
        with dc2:
            if st.button("Cancel", key="int_cancel_del"):
                st.session_state["int_mode"] = None
                st.rerun()


# ---------------------------------------------------------------------------
# Tab: Fees
# ---------------------------------------------------------------------------


def render_fees_tab():
    df = read_sheet(SHEET_FEES)
    programs = get_program_names()

    # --- Summary metrics ---
    total = len(df) if not df.empty else 0
    total_domestic = 0.0
    total_intl = 0.0
    unique_programs = 0
    if not df.empty:
        if "domestic_amount" in df.columns:
            total_domestic = safe_float(df["domestic_amount"].apply(safe_float).sum())
        if "international_amount" in df.columns:
            total_intl = safe_float(df["international_amount"].apply(safe_float).sum())
        if "program_name" in df.columns:
            unique_programs = df["program_name"].nunique()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Fee Rows", total)
    m2.metric("Programs with Fees", unique_programs)
    m3.metric("Dom. Total", f"${total_domestic:,.2f}")
    m4.metric("Intl. Total", f"${total_intl:,.2f}")

    st.divider()

    # --- Filters ---
    fc1, fc2 = st.columns([1, 2])
    with fc1:
        prog_filter = st.selectbox("Filter by Program", ["All Programs"] + programs, key="fee_prog_filter")
    with fc2:
        search = st.text_input("Search fees...", key="fee_search", placeholder="Type to search across all fields")

    display_df = df.copy() if not df.empty else df
    if not display_df.empty:
        if prog_filter != "All Programs" and "program_name" in display_df.columns:
            display_df = display_df[display_df["program_name"] == prog_filter]
        display_df = filter_dataframe(display_df, search)

    # --- Data table with currency formatting ---
    if not display_df.empty:
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "program_name": st.column_config.TextColumn("Program", width="large"),
                "effective_from": st.column_config.TextColumn("Effective From", width="small"),
                "fee_name": st.column_config.TextColumn("Fee Name", width="medium"),
                "domestic_amount": st.column_config.NumberColumn(
                    "Domestic ($)", format="$%.2f", width="small",
                ),
                "international_amount": st.column_config.NumberColumn(
                    "International ($)", format="$%.2f", width="small",
                ),
                "is_tuition": st.column_config.TextColumn("Tuition?", width="small"),
                "sort_order": st.column_config.NumberColumn("Sort", width="small"),
            },
        )
        st.caption(f"Showing {len(display_df)} of {total} fee rows")

        # Show per-program totals when filtering to a single program
        if prog_filter != "All Programs":
            st.divider()
            dom_total = display_df["domestic_amount"].apply(safe_float).sum() if "domestic_amount" in display_df.columns else 0
            intl_total = display_df["international_amount"].apply(safe_float).sum() if "international_amount" in display_df.columns else 0
            tc1, tc2 = st.columns(2)
            tc1.metric(f"{prog_filter} - Domestic Total", f"${dom_total:,.2f}")
            tc2.metric(f"{prog_filter} - International Total", f"${intl_total:,.2f}")
    else:
        st.info("No fees found." if not search else "No fees match your filters.")

    if not programs:
        st.warning("Add programs first before managing fees.")
        return

    st.divider()

    # --- Action buttons ---
    init_session_key("fee_mode", None)

    btn_cols = st.columns([1, 1, 1, 4])
    with btn_cols[0]:
        if st.button("Add New", key="fee_add_btn", use_container_width=True):
            st.session_state["fee_mode"] = "add"
    with btn_cols[1]:
        if st.button("Edit", key="fee_edit_btn", use_container_width=True, disabled=df.empty):
            st.session_state["fee_mode"] = "edit"
    with btn_cols[2]:
        if st.button("Delete", key="fee_del_btn", use_container_width=True, disabled=df.empty, type="secondary"):
            st.session_state["fee_mode"] = "delete"

    mode = st.session_state.get("fee_mode")

    # --- Add form ---
    if mode == "add":
        st.subheader("Add Fee")
        with st.form("add_fee", clear_on_submit=True):
            r1c1, r1c2, r1c3 = st.columns(3)
            with r1c1:
                prog = st.selectbox("Program Name *", programs, key="add_fee_prog")
            with r1c2:
                eff_date = st.date_input("Effective From *", key="add_fee_eff")
            with r1c3:
                fee_name = st.selectbox("Fee Name *", FEE_NAME_OPTIONS, key="add_fee_name")

            r2c1, r2c2, r2c3, r2c4 = st.columns(4)
            with r2c1:
                dom_amt = st.number_input("Domestic Amount ($) *", min_value=0.0, step=0.01, key="add_fee_dom")
            with r2c2:
                intl_amt = st.number_input("International Amount ($) *", min_value=0.0, step=0.01, key="add_fee_intl")
            with r2c3:
                is_tuition = st.checkbox("Is Tuition?", key="add_fee_tuit")
            with r2c4:
                sort_order = st.number_input("Sort Order *", min_value=1, value=1, step=1, key="add_fee_sort")

            fc1, fc2 = st.columns([1, 6])
            with fc1:
                submitted = st.form_submit_button("Add Fee", type="primary")
            with fc2:
                cancel = st.form_submit_button("Cancel")

        if cancel:
            st.session_state["fee_mode"] = None
            st.rerun()
        if submitted:
            row_vals = [
                prog,
                str(eff_date),
                fee_name,
                float(dom_amt),
                float(intl_amt),
                str(is_tuition).upper(),
                int(sort_order),
            ]
            append_row(SHEET_FEES, row_vals)
            identifier = f"{prog}|{eff_date}|{fee_name}"
            field_dict = dict(zip(
                ["program_name", "effective_from", "fee_name",
                 "domestic_amount", "international_amount", "is_tuition", "sort_order"],
                [str(v) for v in row_vals],
            ))
            log_create(SHEET_FEES, identifier, field_dict)
            st.session_state["fee_mode"] = None
            st.toast("Fee added successfully!")
            st.rerun()

    # --- Edit form ---
    if mode == "edit" and not df.empty:
        st.subheader("Edit Fee")
        df_edit = df.copy()
        df_edit["_label"] = df_edit.apply(
            lambda r: f"{r.get('program_name', '')} | {r.get('fee_name', '')} | sort:{r.get('sort_order', '')}",
            axis=1,
        )
        sel = st.selectbox("Select fee to edit", df_edit["_label"].tolist(), key="edit_fee_sel")
        sel_idx = df_edit[df_edit["_label"] == sel].index[0]
        row_data = df_edit.iloc[sel_idx].to_dict()

        with st.form("edit_fee"):
            r1c1, r1c2 = st.columns(2)
            with r1c1:
                new_fee_name = st.selectbox(
                    "Fee Name",
                    FEE_NAME_OPTIONS,
                    index=FEE_NAME_OPTIONS.index(row_data["fee_name"])
                    if row_data.get("fee_name") in FEE_NAME_OPTIONS else 0,
                )
            with r1c2:
                new_sort = st.number_input(
                    "Sort Order", min_value=1,
                    value=safe_int(row_data.get("sort_order", 1), 1),
                    step=1, key="edit_fee_sort",
                )

            r2c1, r2c2, r2c3 = st.columns(3)
            with r2c1:
                new_dom = st.number_input(
                    "Domestic Amount ($)", min_value=0.0,
                    value=safe_float(row_data.get("domestic_amount", 0)),
                    step=0.01, key="edit_fee_dom",
                )
            with r2c2:
                new_intl = st.number_input(
                    "International Amount ($)", min_value=0.0,
                    value=safe_float(row_data.get("international_amount", 0)),
                    step=0.01, key="edit_fee_intl",
                )
            with r2c3:
                is_tuit_val = str(row_data.get("is_tuition", "FALSE")).upper() == "TRUE"
                new_is_tuition = st.checkbox("Is Tuition?", value=is_tuit_val, key="edit_fee_tuit")

            fc1, fc2 = st.columns([1, 6])
            with fc1:
                submitted = st.form_submit_button("Save Changes", type="primary")
            with fc2:
                cancel = st.form_submit_button("Cancel")

        if cancel:
            st.session_state["fee_mode"] = None
            st.rerun()
        if submitted:
            new_row = {
                "program_name": row_data["program_name"],
                "effective_from": row_data["effective_from"],
                "fee_name": new_fee_name,
                "domestic_amount": float(new_dom),
                "international_amount": float(new_intl),
                "is_tuition": str(new_is_tuition).upper(),
                "sort_order": int(new_sort),
            }
            match_dict = {
                "program_name": str(row_data["program_name"]),
                "effective_from": str(row_data["effective_from"]),
                "fee_name": str(row_data["fee_name"]),
                "sort_order": str(row_data["sort_order"]),
            }
            idx = find_row_index_multi(SHEET_FEES, match_dict)
            if idx:
                update_row(SHEET_FEES, idx, [str(v) for v in new_row.values()])
                identifier = f"{row_data['program_name']}|{row_data['effective_from']}|{row_data['fee_name']}"
                log_update(SHEET_FEES, identifier, row_data, new_row)
                st.session_state["fee_mode"] = None
                st.toast("Fee updated successfully!")
                st.rerun()

    # --- Delete with confirmation ---
    if mode == "delete" and not df.empty:
        st.subheader("Delete Fee")
        df_del = df.copy()
        if "_label" not in df_del.columns:
            df_del["_label"] = df_del.apply(
                lambda r: f"{r.get('program_name', '')} | {r.get('fee_name', '')} | sort:{r.get('sort_order', '')}",
                axis=1,
            )
        sel_del = st.selectbox("Select fee to delete", df_del["_label"].tolist(), key="del_fee_sel")
        sel_idx = df_del[df_del["_label"] == sel_del].index[0]
        row_data = df_del.iloc[sel_idx].to_dict()

        st.warning(
            f"You are about to delete fee: **{row_data.get('fee_name', '')}** for "
            f"{row_data.get('program_name', '')} "
            f"(Dom: ${safe_float(row_data.get('domestic_amount', 0)):,.2f} / "
            f"Intl: ${safe_float(row_data.get('international_amount', 0)):,.2f})"
        )
        st.caption("This action cannot be undone.")
        dc1, dc2, dc3 = st.columns([1, 1, 5])
        with dc1:
            if st.button("Confirm Delete", type="primary", key="fee_confirm_del"):
                match_dict = {
                    "program_name": str(row_data["program_name"]),
                    "effective_from": str(row_data["effective_from"]),
                    "fee_name": str(row_data["fee_name"]),
                    "sort_order": str(row_data["sort_order"]),
                }
                idx = find_row_index_multi(SHEET_FEES, match_dict)
                if idx:
                    old = {k: v for k, v in row_data.items() if k != "_label"}
                    delete_row(SHEET_FEES, idx)
                    identifier = f"{row_data['program_name']}|{row_data['effective_from']}|{row_data['fee_name']}"
                    log_delete(SHEET_FEES, identifier, old)
                    st.session_state["fee_mode"] = None
                    st.toast("Fee deleted.")
                    st.rerun()
        with dc2:
            if st.button("Cancel", key="fee_cancel_del"):
                st.session_state["fee_mode"] = None
                st.rerun()


# ---------------------------------------------------------------------------
# Tab: Outline Map
# ---------------------------------------------------------------------------


def render_outline_map_tab():
    df = read_sheet(SHEET_OUTLINE_MAP)
    programs = get_program_names()

    # --- Summary metrics ---
    total_mappings = len(df) if not df.empty else 0
    total_programs = len(programs)
    has_outline = 0
    missing_outline = 0
    if not df.empty and "google_drive_file_id" in df.columns:
        has_outline = df["google_drive_file_id"].apply(lambda x: bool(str(x).strip())).sum()
        missing_outline = total_mappings - has_outline
    programs_without_mapping = total_programs - total_mappings

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Mappings", total_mappings)
    m2.metric("With Drive Link", has_outline)
    m3.metric("Missing Drive Link", missing_outline)
    m4.metric("Programs Without Mapping", max(0, programs_without_mapping))

    st.divider()

    # --- Search ---
    search = st.text_input("Search outline mappings...", key="outline_search", placeholder="Type to filter")
    display_df = filter_dataframe(df, search) if not df.empty else df

    # --- Data table with preview links ---
    if not display_df.empty:
        view_df = display_df.copy()
        if "google_drive_file_id" in view_df.columns:
            view_df["preview_link"] = view_df["google_drive_file_id"].apply(
                lambda fid: f"https://drive.google.com/file/d/{fid}/view" if str(fid).strip() else ""
            )
        st.dataframe(
            view_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "program_name": st.column_config.TextColumn("Program", width="large"),
                "outline_filename": st.column_config.TextColumn("Filename", width="medium"),
                "google_drive_file_id": st.column_config.TextColumn("Drive File ID", width="medium"),
                "preview_link": st.column_config.LinkColumn("Preview", display_text="Open", width="small"),
            },
        )
        st.caption(f"Showing {len(display_df)} of {total_mappings} mappings")
    else:
        st.info("No outline mappings found." if not search else "No mappings match your search.")

    # Show programs missing outlines
    if not df.empty and programs:
        mapped_programs = set(df["program_name"].tolist()) if "program_name" in df.columns else set()
        missing = sorted(set(programs) - mapped_programs)
        if missing:
            with st.expander(f"Programs missing outline mapping ({len(missing)})"):
                for prog_name in missing:
                    st.markdown(f"- {prog_name}")

    if not programs:
        st.warning("Add programs first before managing outline mappings.")
        return

    st.divider()

    # --- Action buttons ---
    init_session_key("outline_mode", None)

    btn_cols = st.columns([1, 1, 1, 4])
    with btn_cols[0]:
        if st.button("Add New", key="outline_add_btn", use_container_width=True):
            st.session_state["outline_mode"] = "add"
    with btn_cols[1]:
        if st.button("Edit", key="outline_edit_btn", use_container_width=True, disabled=df.empty):
            st.session_state["outline_mode"] = "edit"
    with btn_cols[2]:
        if st.button("Delete", key="outline_del_btn", use_container_width=True, disabled=df.empty, type="secondary"):
            st.session_state["outline_mode"] = "delete"

    mode = st.session_state.get("outline_mode")

    # --- Add form ---
    if mode == "add":
        st.subheader("Add Outline Mapping")
        with st.form("add_outline", clear_on_submit=True):
            r1c1, r1c2, r1c3 = st.columns(3)
            with r1c1:
                prog = st.selectbox("Program Name *", programs, key="add_outline_prog")
            with r1c2:
                filename = st.text_input("Outline Filename")
            with r1c3:
                drive_id = st.text_input("Google Drive File ID")
            st.caption("Paste the file ID from the Google Drive sharing URL.")

            fc1, fc2 = st.columns([1, 6])
            with fc1:
                submitted = st.form_submit_button("Add Mapping", type="primary")
            with fc2:
                cancel = st.form_submit_button("Cancel")

        if cancel:
            st.session_state["outline_mode"] = None
            st.rerun()
        if submitted:
            if not prog:
                st.error("Program Name is required.")
            else:
                row_vals = [prog, filename.strip(), drive_id.strip()]
                append_row(SHEET_OUTLINE_MAP, row_vals)
                log_create(SHEET_OUTLINE_MAP, prog, {
                    "program_name": prog,
                    "outline_filename": filename.strip(),
                    "google_drive_file_id": drive_id.strip(),
                })
                st.session_state["outline_mode"] = None
                st.toast("Outline mapping added!")
                st.rerun()

    # --- Edit form ---
    if mode == "edit" and not df.empty:
        st.subheader("Edit Outline Mapping")
        sel = st.selectbox(
            "Select mapping to edit",
            df["program_name"].tolist(),
            key="edit_outline_sel",
        )
        row_data = df[df["program_name"] == sel].iloc[0].to_dict()

        with st.form("edit_outline"):
            r1c1, r1c2 = st.columns(2)
            with r1c1:
                new_fn = st.text_input("Outline Filename", value=str(row_data.get("outline_filename", "")))
            with r1c2:
                new_id = st.text_input("Google Drive File ID", value=str(row_data.get("google_drive_file_id", "")))

            fc1, fc2 = st.columns([1, 6])
            with fc1:
                submitted = st.form_submit_button("Save Changes", type="primary")
            with fc2:
                cancel = st.form_submit_button("Cancel")

        if cancel:
            st.session_state["outline_mode"] = None
            st.rerun()
        if submitted:
            new_row = {
                "program_name": sel,
                "outline_filename": new_fn.strip(),
                "google_drive_file_id": new_id.strip(),
            }
            idx = find_row_index(SHEET_OUTLINE_MAP, "program_name", sel)
            if idx:
                update_row(SHEET_OUTLINE_MAP, idx, list(new_row.values()))
                log_update(SHEET_OUTLINE_MAP, sel, row_data, new_row)
                st.session_state["outline_mode"] = None
                st.toast("Outline mapping updated!")
                st.rerun()

    # --- Delete with confirmation ---
    if mode == "delete" and not df.empty:
        st.subheader("Delete Outline Mapping")
        sel_del = st.selectbox(
            "Select mapping to delete",
            df["program_name"].tolist(),
            key="del_outline_sel",
        )
        old = df[df["program_name"] == sel_del].iloc[0].to_dict()
        st.warning(
            f"You are about to delete the outline mapping for **{sel_del}** "
            f"(File: {old.get('outline_filename', 'N/A')})"
        )
        st.caption("This action cannot be undone.")
        dc1, dc2, dc3 = st.columns([1, 1, 5])
        with dc1:
            if st.button("Confirm Delete", type="primary", key="outline_confirm_del"):
                idx = find_row_index(SHEET_OUTLINE_MAP, "program_name", sel_del)
                if idx:
                    delete_row(SHEET_OUTLINE_MAP, idx)
                    log_delete(SHEET_OUTLINE_MAP, sel_del, old)
                    st.session_state["outline_mode"] = None
                    st.toast("Outline mapping deleted.")
                    st.rerun()
        with dc2:
            if st.button("Cancel", key="outline_cancel_del"):
                st.session_state["outline_mode"] = None
                st.rerun()


# ---------------------------------------------------------------------------
# Tab: Audit Log
# ---------------------------------------------------------------------------


def render_audit_log_tab():
    st.caption("Read-only view of all changes to the data sheets.")

    df = read_sheet(SHEET_AUDIT_LOG)
    if df.empty:
        st.info("No audit records yet.")
        return

    # --- Summary metrics ---
    m1, m2, m3, m4 = st.columns(4)
    total = len(df)
    action_counts = df["action"].value_counts().to_dict() if "action" in df.columns else {}
    m1.metric("Total Records", total)
    m2.metric("Creates", action_counts.get("CREATE", 0))
    m3.metric("Updates", action_counts.get("UPDATE", 0))
    m4.metric("Deletes", action_counts.get("DELETE", 0))

    st.divider()

    # --- Filters ---
    col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
    with col1:
        tab_filter = st.multiselect(
            "Filter by Tab",
            options=sorted(df["tab_name"].dropna().unique().tolist()) if "tab_name" in df.columns else [],
        )
    with col2:
        action_filter = st.multiselect(
            "Filter by Action",
            options=sorted(df["action"].dropna().unique().tolist()) if "action" in df.columns else [],
        )
    with col3:
        if "timestamp" in df.columns and not df["timestamp"].empty:
            date_range = st.date_input("Date range", value=[], key="audit_date_range")
        else:
            date_range = []
    with col4:
        search = st.text_input("Search audit log...", key="audit_search", placeholder="Search by identifier, field, value...")

    filtered = df.copy()
    if tab_filter:
        filtered = filtered[filtered["tab_name"].isin(tab_filter)]
    if action_filter:
        filtered = filtered[filtered["action"].isin(action_filter)]
    if date_range and len(date_range) == 2 and "timestamp" in filtered.columns:
        start, end = date_range
        filtered["_ts"] = pd.to_datetime(filtered["timestamp"], errors="coerce")
        filtered = filtered[
            (filtered["_ts"].dt.date >= start) & (filtered["_ts"].dt.date <= end)
        ]
        filtered = filtered.drop(columns=["_ts"])
    filtered = filter_dataframe(filtered, search)

    # Reverse chronological order
    filtered = filtered.iloc[::-1].reset_index(drop=True)

    st.dataframe(filtered, use_container_width=True, hide_index=True)
    st.caption(f"Showing {len(filtered)} of {len(df)} records (newest first).")


# ---------------------------------------------------------------------------
# Tab: Contract Log
# ---------------------------------------------------------------------------


def render_contract_log_tab():
    st.caption("Read-only view of all generated contracts.")

    df = read_sheet(SHEET_CONTRACT_LOG)
    if df.empty:
        st.info("No contracts generated yet.")
        return

    # --- Summary metrics ---
    m1, m2, m3, m4 = st.columns(4)
    total = len(df)
    status_counts = df["status"].value_counts().to_dict() if "status" in df.columns else {}
    prog_count = df["program_name"].nunique() if "program_name" in df.columns else 0
    m1.metric("Total Contracts", total)
    m2.metric("Programs", prog_count)
    m3.metric("Completed", status_counts.get("completed", 0) + status_counts.get("Completed", 0))
    m4.metric("Pending", status_counts.get("pending", 0) + status_counts.get("Pending", 0))

    st.divider()

    # --- Filters ---
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if "program_name" in df.columns:
            prog_filter = st.multiselect(
                "Filter by Program",
                options=sorted(df["program_name"].dropna().unique().tolist()),
            )
        else:
            prog_filter = []
    with col2:
        if "status" in df.columns:
            status_filter = st.multiselect(
                "Filter by Status",
                options=sorted(df["status"].dropna().unique().tolist()),
            )
        else:
            status_filter = []
    with col3:
        search = st.text_input("Search contracts...", key="contract_search", placeholder="Search by student name, program, status...")

    filtered = df.copy()
    if prog_filter:
        filtered = filtered[filtered["program_name"].isin(prog_filter)]
    if status_filter:
        filtered = filtered[filtered["status"].isin(status_filter)]
    filtered = filter_dataframe(filtered, search)

    # Reverse chronological order
    filtered = filtered.iloc[::-1].reset_index(drop=True)

    st.dataframe(filtered, use_container_width=True, hide_index=True)
    st.caption(f"Showing {len(filtered)} of {len(df)} records (newest first).")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    st.set_page_config(
        page_title="WCC Contract Admin",
        page_icon="🎓",
        layout="wide",
    )

    if not check_auth():
        return

    # --- Sidebar navigation ---
    with st.sidebar:
        st.title("🎓 WCC Contract Admin")
        st.divider()

        selected_tab = st.radio(
            "Navigation",
            NAV_ITEMS,
            format_func=lambda x: f"{NAV_ICONS.get(x, '')} {x}",
            label_visibility="collapsed",
        )

        st.divider()

        # Refresh data button
        if st.button("Refresh Data", use_container_width=True):
            st.cache_resource.clear()
            st.rerun()

        st.divider()

        if st.button("Logout", use_container_width=True, type="secondary"):
            st.session_state["authenticated"] = False
            st.rerun()

        st.caption("WCC Contract Generator v2.0")

    # --- Main content area ---
    st.title(f"{NAV_ICONS.get(selected_tab, '')} {selected_tab}")

    if selected_tab == "Programs":
        render_programs_tab()
    elif selected_tab == "Intakes":
        render_intakes_tab()
    elif selected_tab == "Fees":
        render_fees_tab()
    elif selected_tab == "Outline Map":
        render_outline_map_tab()
    elif selected_tab == "Audit Log":
        render_audit_log_tab()
    elif selected_tab == "Contract Log":
        render_contract_log_tab()


if __name__ == "__main__":
    main()
