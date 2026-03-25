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

# ---------------------------------------------------------------------------
# Google Sheets connection
# ---------------------------------------------------------------------------


@st.cache_resource(ttl=300)
def get_gspread_client():
    """Return an authorized gspread client using the service account."""
    creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    if not creds_json:
        st.error("GOOGLE_SERVICE_ACCOUNT_JSON environment variable is not set.")
        st.stop()

    creds_dict = json.loads(creds_json)
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(credentials)


def open_spreadsheet():
    """Open the target spreadsheet by ID."""
    sheet_id = os.environ.get("GOOGLE_SHEETS_ID", "")
    if not sheet_id:
        st.error("GOOGLE_SHEETS_ID environment variable is not set.")
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
        expected = os.environ.get("ADMIN_PASSWORD", "")
        if not expected:
            st.error("ADMIN_PASSWORD environment variable is not set.")
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


def render_programs_tab():
    st.header("Programs")

    df = read_sheet(SHEET_PROGRAMS)
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No programs found.")

    st.divider()

    # --- Add ---
    with st.expander("Add Program"):
        with st.form("add_program", clear_on_submit=True):
            name = st.text_input("Program Name *")
            code = st.text_input("Program Code *")
            credential = st.selectbox("Credential *", CREDENTIAL_OPTIONS)
            submitted = st.form_submit_button("Add Program")

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
                st.success(f"Program '{name.strip()}' added.")
                st.rerun()

    # --- Edit ---
    with st.expander("Edit Program"):
        if df.empty:
            st.info("Nothing to edit.")
        else:
            sel = st.selectbox("Select program to edit", df["program_name"].tolist(), key="edit_prog_sel")
            row_data = df[df["program_name"] == sel].iloc[0].to_dict()

            with st.form("edit_program"):
                new_code = st.text_input("Program Code", value=str(row_data.get("program_code", "")))
                new_cred = st.selectbox(
                    "Credential",
                    CREDENTIAL_OPTIONS,
                    index=CREDENTIAL_OPTIONS.index(row_data["credential"])
                    if row_data.get("credential") in CREDENTIAL_OPTIONS else 0,
                )
                submitted = st.form_submit_button("Save Changes")

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
                    st.success("Program updated.")
                    st.rerun()

    # --- Delete ---
    with st.expander("Delete Program"):
        if df.empty:
            st.info("Nothing to delete.")
        else:
            sel_del = st.selectbox("Select program to delete", df["program_name"].tolist(), key="del_prog_sel")
            if st.button("Delete Program", type="primary"):
                idx = find_row_index(SHEET_PROGRAMS, "program_name", sel_del)
                if idx:
                    old = df[df["program_name"] == sel_del].iloc[0].to_dict()
                    delete_row(SHEET_PROGRAMS, idx)
                    log_delete(SHEET_PROGRAMS, sel_del, old)
                    st.success(f"Program '{sel_del}' deleted.")
                    st.rerun()


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


# ---------------------------------------------------------------------------
# Tab: Intakes
# ---------------------------------------------------------------------------


def render_intakes_tab():
    st.header("Intakes")

    df = read_sheet(SHEET_INTAKES)
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No intakes found.")

    programs = get_program_names()
    if not programs:
        st.warning("Add programs first before managing intakes.")
        return

    st.divider()

    # --- Add ---
    with st.expander("Add Intake"):
        with st.form("add_intake", clear_on_submit=True):
            prog = st.selectbox("Program Name *", programs, key="add_int_prog")
            col1, col2 = st.columns(2)
            with col1:
                intake_dt = st.date_input("Intake Date *", key="add_int_dt")
            with col2:
                end_dt = st.date_input("End Date *", key="add_int_end")
            campus = st.selectbox("Campus *", CAMPUS_OPTIONS)
            hours = st.text_input("Hours (optional)")
            weeks = st.text_input("Weeks (optional)")
            spots = st.number_input("Spots Available", min_value=0, value=0, step=1)
            status = st.selectbox("Status *", STATUS_OPTIONS)
            dom_del = st.selectbox("Domestic Delivery Method *", DELIVERY_OPTIONS, key="add_int_dom")
            intl_del = st.selectbox("International Delivery Method *", DELIVERY_OPTIONS, key="add_int_intl")
            submitted = st.form_submit_button("Add Intake")

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
                st.success("Intake added.")
                st.rerun()

    # --- Edit ---
    with st.expander("Edit Intake"):
        if df.empty:
            st.info("Nothing to edit.")
        else:
            df["_label"] = df.apply(
                lambda r: f"{r.get('program_name','')} | {r.get('intake_date','')} | {r.get('campus','')}",
                axis=1,
            )
            sel = st.selectbox("Select intake to edit", df["_label"].tolist(), key="edit_int_sel")
            sel_idx = df[df["_label"] == sel].index[0]
            row_data = df.iloc[sel_idx].to_dict()

            with st.form("edit_intake"):
                new_campus = st.selectbox(
                    "Campus",
                    CAMPUS_OPTIONS,
                    index=CAMPUS_OPTIONS.index(row_data["campus"])
                    if row_data.get("campus") in CAMPUS_OPTIONS else 0,
                )
                new_hours = st.text_input("Hours", value=str(row_data.get("hours", "")))
                new_weeks = st.text_input("Weeks", value=str(row_data.get("weeks", "")))
                new_spots = st.number_input(
                    "Spots Available", min_value=0,
                    value=safe_int(row_data.get("spots_available", 0)),
                    step=1,
                )
                new_status = st.selectbox(
                    "Status",
                    STATUS_OPTIONS,
                    index=STATUS_OPTIONS.index(row_data["status"])
                    if row_data.get("status") in STATUS_OPTIONS else 0,
                )
                new_dom = st.selectbox(
                    "Domestic Delivery Method",
                    DELIVERY_OPTIONS,
                    index=DELIVERY_OPTIONS.index(row_data["domestic_delivery_method"])
                    if row_data.get("domestic_delivery_method") in DELIVERY_OPTIONS else 0,
                    key="edit_int_dom",
                )
                new_intl = st.selectbox(
                    "International Delivery Method",
                    DELIVERY_OPTIONS,
                    index=DELIVERY_OPTIONS.index(row_data["international_delivery_method"])
                    if row_data.get("international_delivery_method") in DELIVERY_OPTIONS else 0,
                    key="edit_int_intl",
                )
                submitted = st.form_submit_button("Save Changes")

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
                    identifier = f"{row_data['program_name']}|{row_data['intake_date']}|{row_data.get('campus','')}"
                    log_update(SHEET_INTAKES, identifier, row_data, new_row)
                    st.success("Intake updated.")
                    st.rerun()

    # --- Delete ---
    with st.expander("Delete Intake"):
        if df.empty:
            st.info("Nothing to delete.")
        else:
            if "_label" not in df.columns:
                df["_label"] = df.apply(
                    lambda r: f"{r.get('program_name','')} | {r.get('intake_date','')} | {r.get('campus','')}",
                    axis=1,
                )
            sel_del = st.selectbox("Select intake to delete", df["_label"].tolist(), key="del_int_sel")
            if st.button("Delete Intake", type="primary"):
                sel_idx = df[df["_label"] == sel_del].index[0]
                row_data = df.iloc[sel_idx].to_dict()
                match_dict = {
                    "program_name": row_data["program_name"],
                    "intake_date": str(row_data["intake_date"]),
                    "campus": str(row_data.get("campus", "")),
                }
                idx = find_row_index_multi(SHEET_INTAKES, match_dict)
                if idx:
                    old = {k: v for k, v in row_data.items() if k != "_label"}
                    delete_row(SHEET_INTAKES, idx)
                    identifier = f"{row_data['program_name']}|{row_data['intake_date']}|{row_data.get('campus','')}"
                    log_delete(SHEET_INTAKES, identifier, old)
                    st.success("Intake deleted.")
                    st.rerun()


def _validate_intake(intake_dt, end_dt) -> list[str]:
    errors = []
    if end_dt <= intake_dt:
        errors.append("End Date must be after Intake Date.")
    return errors


# ---------------------------------------------------------------------------
# Tab: Fees
# ---------------------------------------------------------------------------


def render_fees_tab():
    st.header("Fees")

    df = read_sheet(SHEET_FEES)
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No fees found.")

    programs = get_program_names()
    if not programs:
        st.warning("Add programs first before managing fees.")
        return

    st.divider()

    # --- Add ---
    with st.expander("Add Fee"):
        with st.form("add_fee", clear_on_submit=True):
            prog = st.selectbox("Program Name *", programs, key="add_fee_prog")
            eff_date = st.date_input("Effective From *", key="add_fee_eff")
            fee_name = st.selectbox("Fee Name *", FEE_NAME_OPTIONS, key="add_fee_name")
            col1, col2 = st.columns(2)
            with col1:
                dom_amt = st.number_input("Domestic Amount *", min_value=0.0, step=0.01, key="add_fee_dom")
            with col2:
                intl_amt = st.number_input("International Amount *", min_value=0.0, step=0.01, key="add_fee_intl")
            is_tuition = st.checkbox("Is Tuition?", key="add_fee_tuit")
            sort_order = st.number_input("Sort Order *", min_value=1, value=1, step=1, key="add_fee_sort")
            submitted = st.form_submit_button("Add Fee")

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
            st.success("Fee added.")
            st.rerun()

    # --- Edit ---
    with st.expander("Edit Fee"):
        if df.empty:
            st.info("Nothing to edit.")
        else:
            df["_label"] = df.apply(
                lambda r: f"{r.get('program_name','')} | {r.get('fee_name','')} | sort:{r.get('sort_order','')}",
                axis=1,
            )
            sel = st.selectbox("Select fee to edit", df["_label"].tolist(), key="edit_fee_sel")
            sel_idx = df[df["_label"] == sel].index[0]
            row_data = df.iloc[sel_idx].to_dict()

            with st.form("edit_fee"):
                new_fee_name = st.selectbox(
                    "Fee Name",
                    FEE_NAME_OPTIONS,
                    index=FEE_NAME_OPTIONS.index(row_data["fee_name"])
                    if row_data.get("fee_name") in FEE_NAME_OPTIONS else 0,
                )
                col1, col2 = st.columns(2)
                with col1:
                    new_dom = st.number_input(
                        "Domestic Amount", min_value=0.0,
                        value=safe_float(row_data.get("domestic_amount", 0)),
                        step=0.01, key="edit_fee_dom",
                    )
                with col2:
                    new_intl = st.number_input(
                        "International Amount", min_value=0.0,
                        value=safe_float(row_data.get("international_amount", 0)),
                        step=0.01, key="edit_fee_intl",
                    )
                is_tuit_val = str(row_data.get("is_tuition", "FALSE")).upper() == "TRUE"
                new_is_tuition = st.checkbox("Is Tuition?", value=is_tuit_val, key="edit_fee_tuit")
                new_sort = st.number_input(
                    "Sort Order", min_value=1,
                    value=safe_int(row_data.get("sort_order", 1), 1),
                    step=1, key="edit_fee_sort",
                )
                submitted = st.form_submit_button("Save Changes")

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
                    st.success("Fee updated.")
                    st.rerun()

    # --- Delete ---
    with st.expander("Delete Fee"):
        if df.empty:
            st.info("Nothing to delete.")
        else:
            if "_label" not in df.columns:
                df["_label"] = df.apply(
                    lambda r: f"{r.get('program_name','')} | {r.get('fee_name','')} | sort:{r.get('sort_order','')}",
                    axis=1,
                )
            sel_del = st.selectbox("Select fee to delete", df["_label"].tolist(), key="del_fee_sel")
            if st.button("Delete Fee", type="primary"):
                sel_idx = df[df["_label"] == sel_del].index[0]
                row_data = df.iloc[sel_idx].to_dict()
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
                    st.success("Fee deleted.")
                    st.rerun()


# ---------------------------------------------------------------------------
# Tab: Outline Map
# ---------------------------------------------------------------------------


def render_outline_map_tab():
    st.header("Outline Map")

    df = read_sheet(SHEET_OUTLINE_MAP)
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No outline mappings found.")

    programs = get_program_names()
    if not programs:
        st.warning("Add programs first before managing outline mappings.")
        return

    st.divider()

    # --- Add ---
    with st.expander("Add Outline Mapping"):
        with st.form("add_outline", clear_on_submit=True):
            prog = st.selectbox("Program Name *", programs, key="add_outline_prog")
            filename = st.text_input("Outline Filename")
            drive_id = st.text_input("Google Drive File ID")
            submitted = st.form_submit_button("Add Mapping")

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
                st.success("Outline mapping added.")
                st.rerun()

    # --- Edit ---
    with st.expander("Edit Outline Mapping"):
        if df.empty:
            st.info("Nothing to edit.")
        else:
            sel = st.selectbox(
                "Select mapping to edit",
                df["program_name"].tolist(),
                key="edit_outline_sel",
            )
            row_data = df[df["program_name"] == sel].iloc[0].to_dict()

            with st.form("edit_outline"):
                new_fn = st.text_input("Outline Filename", value=str(row_data.get("outline_filename", "")))
                new_id = st.text_input("Google Drive File ID", value=str(row_data.get("google_drive_file_id", "")))
                submitted = st.form_submit_button("Save Changes")

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
                    st.success("Outline mapping updated.")
                    st.rerun()

    # --- Delete ---
    with st.expander("Delete Outline Mapping"):
        if df.empty:
            st.info("Nothing to delete.")
        else:
            sel_del = st.selectbox(
                "Select mapping to delete",
                df["program_name"].tolist(),
                key="del_outline_sel",
            )
            if st.button("Delete Mapping", type="primary"):
                idx = find_row_index(SHEET_OUTLINE_MAP, "program_name", sel_del)
                if idx:
                    old = df[df["program_name"] == sel_del].iloc[0].to_dict()
                    delete_row(SHEET_OUTLINE_MAP, idx)
                    log_delete(SHEET_OUTLINE_MAP, sel_del, old)
                    st.success("Outline mapping deleted.")
                    st.rerun()


# ---------------------------------------------------------------------------
# Tab: Audit Log
# ---------------------------------------------------------------------------


def render_audit_log_tab():
    st.header("Audit Log")
    st.caption("Read-only view of all changes to the data sheets.")

    df = read_sheet(SHEET_AUDIT_LOG)
    if df.empty:
        st.info("No audit records yet.")
        return

    # Filters
    col1, col2, col3 = st.columns(3)
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

    st.dataframe(filtered, use_container_width=True, hide_index=True)
    st.caption(f"Showing {len(filtered)} of {len(df)} records.")


# ---------------------------------------------------------------------------
# Tab: Contract Log
# ---------------------------------------------------------------------------


def render_contract_log_tab():
    st.header("Contract Log")
    st.caption("Read-only view of all generated contracts.")

    df = read_sheet(SHEET_CONTRACT_LOG)
    if df.empty:
        st.info("No contracts generated yet.")
        return

    # Filters
    col1, col2 = st.columns(2)
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

    filtered = df.copy()
    if prog_filter:
        filtered = filtered[filtered["program_name"].isin(prog_filter)]
    if status_filter:
        filtered = filtered[filtered["status"].isin(status_filter)]

    st.dataframe(filtered, use_container_width=True, hide_index=True)
    st.caption(f"Showing {len(filtered)} of {len(df)} records.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    st.set_page_config(
        page_title="WCC Admin Panel",
        page_icon="🎓",
        layout="wide",
    )

    if not check_auth():
        return

    st.title("WCC Contract Generator — Admin Panel")

    tab_programs, tab_intakes, tab_fees, tab_outline, tab_audit, tab_contracts = st.tabs([
        "Programs",
        "Intakes",
        "Fees",
        "Outline Map",
        "Audit Log",
        "Contract Log",
    ])

    with tab_programs:
        render_programs_tab()

    with tab_intakes:
        render_intakes_tab()

    with tab_fees:
        render_fees_tab()

    with tab_outline:
        render_outline_map_tab()

    with tab_audit:
        render_audit_log_tab()

    with tab_contracts:
        render_contract_log_tab()


if __name__ == "__main__":
    main()
