"""
WCC Contract Generator — Streamlit Admin Panel

Dialog-based CRUD dashboard for Programs, Intakes, Fees, Outline Map.
Uses @st.dialog modals for Add, Edit, and Delete operations with
read-only data tables and row selection.

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

NAV_ITEMS = [
    "Programs",
    "Intakes",
    "Fees",
    "Outline Map",
    "---",
    "Audit Log",
    "Contract Log",
]

NAV_ICONS = {
    "Programs": "\U0001f393",
    "Intakes": "\U0001f4c5",
    "Fees": "\U0001f4b2",
    "Outline Map": "\U0001f4cb",
    "Audit Log": "\U0001f4dd",
    "Contract Log": "\U0001f4c4",
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
        st.error(
            "Service account credentials not found. "
            "Set GOOGLE_SERVICE_ACCOUNT in Streamlit secrets "
            "or GOOGLE_SERVICE_ACCOUNT_JSON env var."
        )
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


@st.cache_data(ttl=60)
def read_sheet(sheet_name: str) -> pd.DataFrame:
    """Read a worksheet into a DataFrame. Cached for 60s to avoid API rate limits."""
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


def invalidate_sheet_cache():
    """Clear the read_sheet cache after writes."""
    read_sheet.clear()


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


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


def check_auth():
    """Simple password-based authentication."""
    if st.session_state.get("authenticated"):
        return True

    st.markdown(
        '<div style="display:flex;justify-content:center;padding-top:60px;">'
        '<div style="width:400px;">',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<h1 style="text-align:center;color:#1E293B;">WCC Admin</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p style="text-align:center;color:#64748B;margin-bottom:32px;">'
        "Sign in to manage contract data</p>",
        unsafe_allow_html=True,
    )
    password = st.text_input("Password", type="password", key="login_pw")
    if st.button("Sign In", type="primary", use_container_width=True):
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
            invalidate_sheet_cache()
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.markdown("</div></div>", unsafe_allow_html=True)
    return False


# ---------------------------------------------------------------------------
# Shared UI components
# ---------------------------------------------------------------------------


def render_metric_card(label, value, prefix=""):
    """Render a single metric inside a styled container."""
    display_val = f"{prefix}{value}" if prefix else str(value)
    st.metric(label=label, value=display_val)


def render_search_bar(key, placeholder="Search..."):
    """Render a search input and return the current text."""
    return st.text_input(
        "Search",
        key=key,
        placeholder=placeholder,
        label_visibility="collapsed",
    )


def ensure_columns(df, columns, defaults=None):
    """Ensure a DataFrame has the expected columns. Add missing ones with defaults."""
    defaults = defaults or {}
    result = df.copy()
    for col in columns:
        if col not in result.columns:
            result[col] = defaults.get(col, "")
    return result[columns]


def _parse_date_safe(val):
    """Parse a date string to a date object, returning None on failure."""
    if isinstance(val, date):
        return val
    if not val or not str(val).strip():
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(str(val).strip(), fmt).date()
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# Tab: Programs
# ---------------------------------------------------------------------------


@st.dialog("Add Program")
def add_program_dialog():
    """Dialog to add a new program."""
    name = st.text_input("Program Name *")
    code = st.text_input("Program Code *")
    credential = st.selectbox("Credential *", CREDENTIAL_OPTIONS)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Save", type="primary", use_container_width=True):
            if not name.strip():
                st.error("Program Name is required.")
                return
            if not code.strip():
                st.error("Program Code is required.")
                return
            with st.spinner("Saving..."):
                append_row(SHEET_PROGRAMS, [name.strip(), code.strip(), credential])
                log_create(SHEET_PROGRAMS, name.strip(), {
                    "program_name": name.strip(),
                    "program_code": code.strip(),
                    "credential": credential,
                })
                invalidate_sheet_cache()
            invalidate_sheet_cache()
            st.rerun()
    with col2:
        if st.button("Cancel", use_container_width=True):
            st.rerun()


@st.dialog("Edit Program")
def edit_program_dialog(row_data):
    """Dialog to edit an existing program."""
    st.caption(f"Editing: {row_data['program_name']}")

    new_name = st.text_input("Program Name *", value=row_data.get("program_name", ""))
    new_code = st.text_input("Program Code *", value=row_data.get("program_code", ""))
    cred_index = (
        CREDENTIAL_OPTIONS.index(row_data["credential"])
        if row_data.get("credential") in CREDENTIAL_OPTIONS
        else 0
    )
    new_cred = st.selectbox("Credential *", CREDENTIAL_OPTIONS, index=cred_index)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Save Changes", type="primary", use_container_width=True):
            if not new_name.strip():
                st.error("Program Name is required.")
                return
            if not new_code.strip():
                st.error("Program Code is required.")
                return
            new_row = {
                "program_name": new_name.strip(),
                "program_code": new_code.strip(),
                "credential": new_cred,
            }
            idx = find_row_index(SHEET_PROGRAMS, "program_name", row_data["program_name"])
            if idx:
                with st.spinner("Saving..."):
                    update_row(SHEET_PROGRAMS, idx, list(new_row.values()))
                    log_update(SHEET_PROGRAMS, row_data["program_name"], row_data, new_row)
                    invalidate_sheet_cache()
                if "selected_program" in st.session_state:
                    del st.session_state["selected_program"]
                invalidate_sheet_cache()
                st.rerun()
            else:
                st.error("Could not find the row to update.")
    with col2:
        if st.button("Cancel", use_container_width=True):
            st.rerun()


@st.dialog("Delete Program")
def delete_program_dialog(row_data):
    """Dialog to confirm deletion of a program."""
    st.warning(f"Are you sure you want to delete **{row_data['program_name']}**?")
    st.markdown("This action cannot be undone.")

    for k, v in row_data.items():
        st.text(f"{k}: {v}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("\U0001f5d1\ufe0f Delete", type="primary", use_container_width=True):
            idx = find_row_index(SHEET_PROGRAMS, "program_name", row_data["program_name"])
            if idx:
                with st.spinner("Deleting..."):
                    delete_row(SHEET_PROGRAMS, idx)
                    log_delete(SHEET_PROGRAMS, row_data["program_name"], row_data)
                    invalidate_sheet_cache()
                if "selected_program" in st.session_state:
                    del st.session_state["selected_program"]
                invalidate_sheet_cache()
                st.rerun()
            else:
                st.error("Could not find the row to delete.")
    with col2:
        if st.button("Cancel", use_container_width=True):
            st.rerun()


def render_programs_tab():
    df = read_sheet(SHEET_PROGRAMS)

    expected_cols = ["program_name", "program_code", "credential"]
    if df.empty:
        df = pd.DataFrame(columns=expected_cols)
    else:
        df = ensure_columns(df, expected_cols)

    # Metrics row
    total = len(df)
    cred_counts = df["credential"].value_counts().to_dict() if not df.empty else {}

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        render_metric_card("Total Programs", total)
    with m2:
        render_metric_card("Certificates", cred_counts.get("Certificate", 0))
    with m3:
        render_metric_card("Diplomas", cred_counts.get("Diploma", 0))
    with m4:
        render_metric_card("Bachelors", cred_counts.get("Bachelor", 0))

    st.markdown("---")

    # Search
    search = render_search_bar("prog_search", "Search programs by name, code...")

    # Data table (read-only with selection)
    display_df = filter_dataframe(df, search) if not df.empty else df

    event = st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="prog_table",
        column_config={
            "program_name": st.column_config.TextColumn("Program Name", width="large"),
            "program_code": st.column_config.TextColumn("Program Code"),
            "credential": st.column_config.TextColumn("Credential"),
        },
    )

    # Track selection
    if event and event.selection and event.selection.rows:
        selected_idx = event.selection.rows[0]
        st.session_state["selected_program"] = display_df.iloc[selected_idx].to_dict()
    else:
        if "selected_program" in st.session_state:
            del st.session_state["selected_program"]

    # Action buttons AFTER table (so selection is already processed)
    has_selection = "selected_program" in st.session_state
    b1, b2, b3, b4 = st.columns([1, 1, 1, 2])
    with b1:
        if st.button("➕ Add", use_container_width=True, key="prog_add"):
            add_program_dialog()
    with b2:
        if st.button(
            "✏️ Edit",
            use_container_width=True,
            disabled=not has_selection,
            key="prog_edit",
        ):
            edit_program_dialog(st.session_state.get("selected_program", {}))
    with b3:
        if st.button(
            "🗑️ Delete",
            use_container_width=True,
            disabled=not has_selection,
            key="prog_del",
        ):
            delete_program_dialog(st.session_state.get("selected_program", {}))
    with b4:
        if has_selection:
            sel = st.session_state["selected_program"]
            st.info(f"Selected: **{sel['program_name']}**")

    if not df.empty:
        st.caption(f"{len(display_df)} program{'s' if len(display_df) != 1 else ''} shown")


# ---------------------------------------------------------------------------
# Tab: Intakes
# ---------------------------------------------------------------------------


@st.dialog("Add Intake")
def add_intake_dialog():
    """Dialog to add a new intake."""
    programs = get_program_names()
    if not programs:
        st.warning("Add programs first before adding intakes.")
        if st.button("Close", use_container_width=True):
            st.rerun()
        return

    program_name = st.selectbox("Program *", programs)

    d1, d2 = st.columns(2)
    with d1:
        intake_date = st.date_input("Intake Date *", value=None, key="add_int_idate")
    with d2:
        end_date = st.date_input("End Date *", value=None, key="add_int_edate")

    campus = st.selectbox("Campus *", CAMPUS_OPTIONS)

    h1, h2 = st.columns(2)
    with h1:
        hours = st.text_input("Hours")
    with h2:
        weeks = st.text_input("Weeks")

    spots_available = st.number_input("Spots Available", min_value=0, step=1, value=0)
    status = st.selectbox("Status *", STATUS_OPTIONS)

    dm1, dm2 = st.columns(2)
    with dm1:
        domestic_delivery = st.selectbox("Domestic Delivery Method", [""] + DELIVERY_OPTIONS)
    with dm2:
        intl_delivery = st.selectbox("International Delivery Method", [""] + DELIVERY_OPTIONS)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Save", type="primary", use_container_width=True):
            if not intake_date:
                st.error("Intake Date is required.")
                return
            if not end_date:
                st.error("End Date is required.")
                return
            row_values = [
                program_name,
                str(intake_date),
                str(end_date),
                campus,
                hours.strip(),
                weeks.strip(),
                str(spots_available),
                status,
                domestic_delivery,
                intl_delivery,
            ]
            field_dict = {
                "program_name": program_name,
                "intake_date": str(intake_date),
                "end_date": str(end_date),
                "campus": campus,
                "hours": hours.strip(),
                "weeks": weeks.strip(),
                "spots_available": str(spots_available),
                "status": status,
                "domestic_delivery_method": domestic_delivery,
                "international_delivery_method": intl_delivery,
            }
            identifier = f"{program_name} | {intake_date} | {campus}"
            with st.spinner("Saving..."):
                append_row(SHEET_INTAKES, row_values)
                log_create(SHEET_INTAKES, identifier, field_dict)
                invalidate_sheet_cache()
            invalidate_sheet_cache()
            st.rerun()
    with col2:
        if st.button("Cancel", use_container_width=True):
            st.rerun()


@st.dialog("Edit Intake")
def edit_intake_dialog(row_data):
    """Dialog to edit an existing intake."""
    programs = get_program_names()
    identifier = f"{row_data.get('program_name', '')} | {row_data.get('intake_date', '')} | {row_data.get('campus', '')}"
    st.caption(f"Editing: {identifier}")

    prog_index = (
        programs.index(row_data["program_name"])
        if row_data.get("program_name") in programs
        else 0
    )
    program_name = st.selectbox("Program *", programs, index=prog_index)

    d1, d2 = st.columns(2)
    with d1:
        parsed_intake = _parse_date_safe(row_data.get("intake_date", ""))
        intake_date = st.date_input(
            "Intake Date *",
            value=parsed_intake,
            key="edit_int_idate",
        )
    with d2:
        parsed_end = _parse_date_safe(row_data.get("end_date", ""))
        end_date = st.date_input(
            "End Date *",
            value=parsed_end,
            key="edit_int_edate",
        )

    campus_index = (
        CAMPUS_OPTIONS.index(row_data["campus"])
        if row_data.get("campus") in CAMPUS_OPTIONS
        else 0
    )
    campus = st.selectbox("Campus *", CAMPUS_OPTIONS, index=campus_index)

    h1, h2 = st.columns(2)
    with h1:
        hours = st.text_input("Hours", value=str(row_data.get("hours", "")))
    with h2:
        weeks = st.text_input("Weeks", value=str(row_data.get("weeks", "")))

    spots_available = st.number_input(
        "Spots Available",
        min_value=0,
        step=1,
        value=safe_int(row_data.get("spots_available", 0), 0),
    )

    status_index = (
        STATUS_OPTIONS.index(row_data["status"])
        if row_data.get("status") in STATUS_OPTIONS
        else 0
    )
    status = st.selectbox("Status *", STATUS_OPTIONS, index=status_index)

    dm1, dm2 = st.columns(2)
    dom_options = [""] + DELIVERY_OPTIONS
    intl_options = [""] + DELIVERY_OPTIONS
    with dm1:
        dom_index = (
            dom_options.index(row_data["domestic_delivery_method"])
            if row_data.get("domestic_delivery_method") in dom_options
            else 0
        )
        domestic_delivery = st.selectbox(
            "Domestic Delivery Method", dom_options, index=dom_index,
        )
    with dm2:
        intl_index = (
            intl_options.index(row_data["international_delivery_method"])
            if row_data.get("international_delivery_method") in intl_options
            else 0
        )
        intl_delivery = st.selectbox(
            "International Delivery Method", intl_options, index=intl_index,
        )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Save Changes", type="primary", use_container_width=True):
            if not intake_date:
                st.error("Intake Date is required.")
                return
            if not end_date:
                st.error("End Date is required.")
                return
            new_row = {
                "program_name": program_name,
                "intake_date": str(intake_date),
                "end_date": str(end_date),
                "campus": campus,
                "hours": hours.strip(),
                "weeks": weeks.strip(),
                "spots_available": str(spots_available),
                "status": status,
                "domestic_delivery_method": domestic_delivery,
                "international_delivery_method": intl_delivery,
            }
            match_dict = {
                "program_name": str(row_data.get("program_name", "")),
                "intake_date": str(row_data.get("intake_date", "")),
                "campus": str(row_data.get("campus", "")),
            }
            idx = find_row_index_multi(SHEET_INTAKES, match_dict)
            if idx:
                with st.spinner("Saving..."):
                    update_row(SHEET_INTAKES, idx, list(new_row.values()))
                    log_update(SHEET_INTAKES, identifier, row_data, new_row)
                    invalidate_sheet_cache()
                if "selected_intake" in st.session_state:
                    del st.session_state["selected_intake"]
                invalidate_sheet_cache()
                st.rerun()
            else:
                st.error("Could not find the row to update.")
    with col2:
        if st.button("Cancel", use_container_width=True):
            st.rerun()


@st.dialog("Delete Intake")
def delete_intake_dialog(row_data):
    """Dialog to confirm deletion of an intake."""
    identifier = f"{row_data.get('program_name', '')} | {row_data.get('intake_date', '')} | {row_data.get('campus', '')}"
    st.warning(f"Are you sure you want to delete this intake?\n\n**{identifier}**")
    st.markdown("This action cannot be undone.")

    for k, v in row_data.items():
        st.text(f"{k}: {v}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("\U0001f5d1\ufe0f Delete", type="primary", use_container_width=True):
            match_dict = {
                "program_name": str(row_data.get("program_name", "")),
                "intake_date": str(row_data.get("intake_date", "")),
                "campus": str(row_data.get("campus", "")),
            }
            idx = find_row_index_multi(SHEET_INTAKES, match_dict)
            if idx:
                with st.spinner("Deleting..."):
                    delete_row(SHEET_INTAKES, idx)
                    log_delete(SHEET_INTAKES, identifier, row_data)
                    invalidate_sheet_cache()
                if "selected_intake" in st.session_state:
                    del st.session_state["selected_intake"]
                invalidate_sheet_cache()
                st.rerun()
            else:
                st.error("Could not find the row to delete.")
    with col2:
        if st.button("Cancel", use_container_width=True):
            st.rerun()


def render_intakes_tab():
    df = read_sheet(SHEET_INTAKES)
    programs = get_program_names()

    expected_cols = [
        "program_name", "intake_date", "end_date", "campus",
        "hours", "weeks", "spots_available", "status",
        "domestic_delivery_method", "international_delivery_method",
    ]
    if df.empty:
        df = pd.DataFrame(columns=expected_cols)
    else:
        df = ensure_columns(df, expected_cols)

    # Cast numeric columns
    if not df.empty:
        df["spots_available"] = df["spots_available"].apply(lambda x: safe_int(x, 0))
        df["hours"] = df["hours"].apply(lambda x: str(x) if x else "")
        df["weeks"] = df["weeks"].apply(lambda x: str(x) if x else "")

    # Metrics
    total = len(df)
    status_counts = df["status"].value_counts().to_dict() if not df.empty else {}

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        render_metric_card("Total Intakes", total)
    with m2:
        render_metric_card("Open", status_counts.get("Open", 0))
    with m3:
        render_metric_card("Closed", status_counts.get("Closed", 0))
    with m4:
        render_metric_card("Waitlist", status_counts.get("Waitlist", 0))

    st.markdown("---")

    # Filters
    fc1, fc2, fc3 = st.columns([2, 1, 2])
    with fc1:
        prog_filter = st.selectbox(
            "Filter by Program",
            ["All Programs"] + programs,
            key="int_prog_filter",
        )
    with fc2:
        status_filter = st.selectbox(
            "Filter by Status",
            ["All"] + STATUS_OPTIONS,
            key="int_status_filter",
        )
    with fc3:
        search = render_search_bar("int_search", "Search intakes...")

    display_df = df.copy()
    if not display_df.empty:
        if prog_filter != "All Programs" and "program_name" in display_df.columns:
            display_df = display_df[display_df["program_name"] == prog_filter]
        if status_filter != "All" and "status" in display_df.columns:
            display_df = display_df[display_df["status"] == status_filter]
        display_df = filter_dataframe(display_df, search)

    if not programs:
        st.warning("Add programs first before managing intakes.")

    # Data table (read-only with selection)
    event = st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="int_table",
        column_config={
            "program_name": st.column_config.TextColumn("Program", width="large"),
            "intake_date": st.column_config.TextColumn("Intake Date"),
            "end_date": st.column_config.TextColumn("End Date"),
            "campus": st.column_config.TextColumn("Campus"),
            "hours": st.column_config.TextColumn("Hours"),
            "weeks": st.column_config.TextColumn("Weeks"),
            "spots_available": st.column_config.NumberColumn("Spots", min_value=0),
            "status": st.column_config.TextColumn("Status"),
            "domestic_delivery_method": st.column_config.TextColumn("Dom. Delivery"),
            "international_delivery_method": st.column_config.TextColumn("Intl. Delivery"),
        },
    )

    # Track selection
    if event and event.selection and event.selection.rows:
        selected_idx = event.selection.rows[0]
        st.session_state["selected_intake"] = display_df.iloc[selected_idx].to_dict()
    else:
        if "selected_intake" in st.session_state:
            del st.session_state["selected_intake"]

    # Action buttons AFTER table (so selection is already processed)
    has_selection = "selected_intake" in st.session_state
    b1, b2, b3, b4 = st.columns([1, 1, 1, 2])
    with b1:
        if st.button("\u2795 Add", use_container_width=True, key="int_add"):
            add_intake_dialog()
    with b2:
        if st.button(
            "\u270f\ufe0f Edit",
            use_container_width=True,
            disabled=not has_selection,
            key="int_edit",
        ):
            edit_intake_dialog(st.session_state.get("selected_intake", {}))
    with b3:
        if st.button(
            "\U0001f5d1\ufe0f Delete",
            use_container_width=True,
            disabled=not has_selection,
            key="int_del",
        ):
            delete_intake_dialog(st.session_state.get("selected_intake", {}))
    with b4:
        if has_selection:
            sel = st.session_state["selected_intake"]
            st.info(
                f"Selected: **{sel['program_name']}** | "
                f"{sel['intake_date']} | {sel['campus']}"
            )

    if total > 0:
        st.caption(f"Showing {len(display_df)} of {total} intakes")


# ---------------------------------------------------------------------------
# Tab: Fees
# ---------------------------------------------------------------------------


@st.dialog("Add Fee")
def add_fee_dialog():
    """Dialog to add a new fee."""
    programs = get_program_names()
    if not programs:
        st.warning("Add programs first before adding fees.")
        if st.button("Close", use_container_width=True):
            st.rerun()
        return

    program_name = st.selectbox("Program *", programs)
    effective_from = st.text_input("Effective From", placeholder="e.g. 2025-01-01")
    fee_name = st.selectbox("Fee Name *", FEE_NAME_OPTIONS)

    a1, a2 = st.columns(2)
    with a1:
        domestic_amount = st.number_input(
            "Domestic Amount ($)", min_value=0.0, step=0.01, value=0.0, format="%.2f",
        )
    with a2:
        international_amount = st.number_input(
            "International Amount ($)", min_value=0.0, step=0.01, value=0.0, format="%.2f",
        )

    is_tuition = st.checkbox("Is Tuition?", value=False)
    sort_order = st.number_input("Sort Order", min_value=1, step=1, value=1)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Save", type="primary", use_container_width=True):
            row_values = [
                program_name,
                effective_from.strip(),
                fee_name,
                str(domestic_amount),
                str(international_amount),
                str(is_tuition).upper(),
                str(sort_order),
            ]
            field_dict = {
                "program_name": program_name,
                "effective_from": effective_from.strip(),
                "fee_name": fee_name,
                "domestic_amount": str(domestic_amount),
                "international_amount": str(international_amount),
                "is_tuition": str(is_tuition).upper(),
                "sort_order": str(sort_order),
            }
            identifier = f"{program_name} | {fee_name}"
            with st.spinner("Saving..."):
                append_row(SHEET_FEES, row_values)
                log_create(SHEET_FEES, identifier, field_dict)
                invalidate_sheet_cache()
            invalidate_sheet_cache()
            st.rerun()
    with col2:
        if st.button("Cancel", use_container_width=True):
            st.rerun()


@st.dialog("Edit Fee")
def edit_fee_dialog(row_data):
    """Dialog to edit an existing fee."""
    programs = get_program_names()
    identifier = f"{row_data.get('program_name', '')} | {row_data.get('fee_name', '')}"
    st.caption(f"Editing: {identifier}")

    prog_index = (
        programs.index(row_data["program_name"])
        if row_data.get("program_name") in programs
        else 0
    )
    program_name = st.selectbox("Program *", programs, index=prog_index)
    effective_from = st.text_input(
        "Effective From",
        value=str(row_data.get("effective_from", "")),
    )

    fee_index = (
        FEE_NAME_OPTIONS.index(row_data["fee_name"])
        if row_data.get("fee_name") in FEE_NAME_OPTIONS
        else 0
    )
    fee_name = st.selectbox("Fee Name *", FEE_NAME_OPTIONS, index=fee_index)

    a1, a2 = st.columns(2)
    with a1:
        domestic_amount = st.number_input(
            "Domestic Amount ($)",
            min_value=0.0,
            step=0.01,
            value=safe_float(row_data.get("domestic_amount", 0.0), 0.0),
            format="%.2f",
        )
    with a2:
        international_amount = st.number_input(
            "International Amount ($)",
            min_value=0.0,
            step=0.01,
            value=safe_float(row_data.get("international_amount", 0.0), 0.0),
            format="%.2f",
        )

    is_tuition_val = str(row_data.get("is_tuition", "")).strip().upper() in ("TRUE", "1")
    is_tuition = st.checkbox("Is Tuition?", value=is_tuition_val)
    sort_order = st.number_input(
        "Sort Order",
        min_value=1,
        step=1,
        value=safe_int(row_data.get("sort_order", 1), 1),
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Save Changes", type="primary", use_container_width=True):
            new_row = {
                "program_name": program_name,
                "effective_from": effective_from.strip(),
                "fee_name": fee_name,
                "domestic_amount": str(domestic_amount),
                "international_amount": str(international_amount),
                "is_tuition": str(is_tuition).upper(),
                "sort_order": str(sort_order),
            }
            match_dict = {
                "program_name": str(row_data.get("program_name", "")),
                "fee_name": str(row_data.get("fee_name", "")),
                "sort_order": str(safe_int(row_data.get("sort_order", 1), 1)),
            }
            idx = find_row_index_multi(SHEET_FEES, match_dict)
            if idx:
                old_row = {
                    "program_name": str(row_data.get("program_name", "")),
                    "effective_from": str(row_data.get("effective_from", "")),
                    "fee_name": str(row_data.get("fee_name", "")),
                    "domestic_amount": str(row_data.get("domestic_amount", "")),
                    "international_amount": str(row_data.get("international_amount", "")),
                    "is_tuition": str(row_data.get("is_tuition", "")),
                    "sort_order": str(row_data.get("sort_order", "")),
                }
                with st.spinner("Saving..."):
                    update_row(SHEET_FEES, idx, list(new_row.values()))
                    log_update(SHEET_FEES, identifier, old_row, new_row)
                    invalidate_sheet_cache()
                if "selected_fee" in st.session_state:
                    del st.session_state["selected_fee"]
                invalidate_sheet_cache()
                st.rerun()
            else:
                st.error("Could not find the row to update.")
    with col2:
        if st.button("Cancel", use_container_width=True):
            st.rerun()


@st.dialog("Delete Fee")
def delete_fee_dialog(row_data):
    """Dialog to confirm deletion of a fee."""
    identifier = f"{row_data.get('program_name', '')} | {row_data.get('fee_name', '')}"
    st.warning(f"Are you sure you want to delete this fee?\n\n**{identifier}**")
    st.markdown("This action cannot be undone.")

    for k, v in row_data.items():
        st.text(f"{k}: {v}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("\U0001f5d1\ufe0f Delete", type="primary", use_container_width=True):
            match_dict = {
                "program_name": str(row_data.get("program_name", "")),
                "fee_name": str(row_data.get("fee_name", "")),
                "sort_order": str(safe_int(row_data.get("sort_order", 1), 1)),
            }
            idx = find_row_index_multi(SHEET_FEES, match_dict)
            if idx:
                clean = {k: str(v) for k, v in row_data.items()}
                with st.spinner("Deleting..."):
                    delete_row(SHEET_FEES, idx)
                    log_delete(SHEET_FEES, identifier, clean)
                    invalidate_sheet_cache()
                if "selected_fee" in st.session_state:
                    del st.session_state["selected_fee"]
                invalidate_sheet_cache()
                st.rerun()
            else:
                st.error("Could not find the row to delete.")
    with col2:
        if st.button("Cancel", use_container_width=True):
            st.rerun()


def render_fees_tab():
    df = read_sheet(SHEET_FEES)
    programs = get_program_names()

    expected_cols = [
        "program_name", "effective_from", "fee_name",
        "domestic_amount", "international_amount", "is_tuition", "sort_order",
    ]
    if df.empty:
        df = pd.DataFrame(columns=expected_cols)
    else:
        df = ensure_columns(df, expected_cols)

    # Cast numeric and boolean columns
    if not df.empty:
        df["domestic_amount"] = df["domestic_amount"].apply(lambda x: safe_float(x, 0.0))
        df["international_amount"] = df["international_amount"].apply(lambda x: safe_float(x, 0.0))
        df["sort_order"] = df["sort_order"].apply(lambda x: safe_int(x, 1))
        df["is_tuition"] = df["is_tuition"].apply(
            lambda x: str(x).strip().upper() == "TRUE"
        )

    # Metrics
    total = len(df)
    total_domestic = df["domestic_amount"].sum() if not df.empty else 0.0
    total_intl = df["international_amount"].sum() if not df.empty else 0.0

    m1, m2, m3 = st.columns(3)
    with m1:
        render_metric_card("Total Fee Items", total)
    with m2:
        render_metric_card("Domestic Total", f"${total_domestic:,.2f}")
    with m3:
        render_metric_card("International Total", f"${total_intl:,.2f}")

    st.markdown("---")

    # Filter
    fc1, fc2 = st.columns([2, 3])
    with fc1:
        prog_filter = st.selectbox(
            "Filter by Program",
            ["All Programs"] + programs,
            key="fee_prog_filter",
        )
    with fc2:
        search = render_search_bar("fee_search", "Search fees...")

    display_df = df.copy()
    if not display_df.empty:
        if prog_filter != "All Programs" and "program_name" in display_df.columns:
            display_df = display_df[display_df["program_name"] == prog_filter]
        display_df = filter_dataframe(display_df, search)

    if not programs:
        st.warning("Add programs first before managing fees.")

    # Data table (read-only with selection)
    event = st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="fee_table",
        column_config={
            "program_name": st.column_config.TextColumn("Program", width="large"),
            "effective_from": st.column_config.TextColumn("Effective From"),
            "fee_name": st.column_config.TextColumn("Fee Name"),
            "domestic_amount": st.column_config.NumberColumn(
                "Domestic $", format="$%.2f",
            ),
            "international_amount": st.column_config.NumberColumn(
                "International $", format="$%.2f",
            ),
            "is_tuition": st.column_config.CheckboxColumn("Tuition?"),
            "sort_order": st.column_config.NumberColumn("Sort"),
        },
    )

    # Track selection
    if event and event.selection and event.selection.rows:
        selected_idx = event.selection.rows[0]
        st.session_state["selected_fee"] = display_df.iloc[selected_idx].to_dict()
    else:
        if "selected_fee" in st.session_state:
            del st.session_state["selected_fee"]

    # Action buttons AFTER table (so selection is already processed)
    has_selection = "selected_fee" in st.session_state
    b1, b2, b3, b4 = st.columns([1, 1, 1, 2])
    with b1:
        if st.button("\u2795 Add", use_container_width=True, key="fee_add"):
            add_fee_dialog()
    with b2:
        if st.button(
            "\u270f\ufe0f Edit",
            use_container_width=True,
            disabled=not has_selection,
            key="fee_edit",
        ):
            edit_fee_dialog(st.session_state.get("selected_fee", {}))
    with b3:
        if st.button(
            "\U0001f5d1\ufe0f Delete",
            use_container_width=True,
            disabled=not has_selection,
            key="fee_del",
        ):
            delete_fee_dialog(st.session_state.get("selected_fee", {}))
    with b4:
        if has_selection:
            sel = st.session_state["selected_fee"]
            st.info(
                f"Selected: **{sel['program_name']}** | {sel['fee_name']} "
                f"(Dom: ${safe_float(sel.get('domestic_amount', 0)):,.2f} / "
                f"Intl: ${safe_float(sel.get('international_amount', 0)):,.2f})"
            )

    if total > 0:
        st.caption(f"Showing {len(display_df)} of {total} fee rows")

    # Per-program totals when filtered
    if prog_filter != "All Programs" and not display_df.empty:
        dom_total = display_df["domestic_amount"].sum()
        intl_total = display_df["international_amount"].sum()
        tc1, tc2 = st.columns(2)
        with tc1:
            render_metric_card(f"{prog_filter} Domestic", f"${dom_total:,.2f}")
        with tc2:
            render_metric_card(f"{prog_filter} International", f"${intl_total:,.2f}")


# ---------------------------------------------------------------------------
# Tab: Outline Map
# ---------------------------------------------------------------------------


@st.dialog("Add Outline Mapping")
def add_outline_dialog():
    """Dialog to add a new outline mapping."""
    programs = get_program_names()
    if not programs:
        st.warning("Add programs first before adding outline mappings.")
        if st.button("Close", use_container_width=True):
            st.rerun()
        return

    program_name = st.selectbox("Program *", programs)
    outline_filename = st.text_input("Outline Filename")
    google_drive_file_id = st.text_input("Google Drive File ID")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Save", type="primary", use_container_width=True):
            if not program_name:
                st.error("Program is required.")
                return
            row_values = [
                program_name,
                outline_filename.strip(),
                google_drive_file_id.strip(),
            ]
            field_dict = {
                "program_name": program_name,
                "outline_filename": outline_filename.strip(),
                "google_drive_file_id": google_drive_file_id.strip(),
            }
            with st.spinner("Saving..."):
                append_row(SHEET_OUTLINE_MAP, row_values)
                log_create(SHEET_OUTLINE_MAP, program_name, field_dict)
                invalidate_sheet_cache()
            invalidate_sheet_cache()
            st.rerun()
    with col2:
        if st.button("Cancel", use_container_width=True):
            st.rerun()


@st.dialog("Edit Outline Mapping")
def edit_outline_dialog(row_data):
    """Dialog to edit an existing outline mapping."""
    programs = get_program_names()
    st.caption(f"Editing: {row_data.get('program_name', '')}")

    prog_index = (
        programs.index(row_data["program_name"])
        if row_data.get("program_name") in programs
        else 0
    )
    program_name = st.selectbox("Program *", programs, index=prog_index)
    outline_filename = st.text_input(
        "Outline Filename",
        value=row_data.get("outline_filename", ""),
    )
    google_drive_file_id = st.text_input(
        "Google Drive File ID",
        value=row_data.get("google_drive_file_id", ""),
    )

    if google_drive_file_id.strip():
        preview_url = f"https://drive.google.com/file/d/{google_drive_file_id.strip()}/view"
        st.markdown(f"[Preview in Google Drive]({preview_url})")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Save Changes", type="primary", use_container_width=True):
            new_row = {
                "program_name": program_name,
                "outline_filename": outline_filename.strip(),
                "google_drive_file_id": google_drive_file_id.strip(),
            }
            idx = find_row_index(
                SHEET_OUTLINE_MAP, "program_name", row_data["program_name"],
            )
            if idx:
                with st.spinner("Saving..."):
                    update_row(SHEET_OUTLINE_MAP, idx, list(new_row.values()))
                    log_update(
                        SHEET_OUTLINE_MAP,
                        row_data["program_name"],
                        row_data,
                        new_row,
                    )
                    invalidate_sheet_cache()
                if "selected_outline" in st.session_state:
                    del st.session_state["selected_outline"]
                invalidate_sheet_cache()
                st.rerun()
            else:
                st.error("Could not find the row to update.")
    with col2:
        if st.button("Cancel", use_container_width=True):
            st.rerun()


@st.dialog("Delete Outline Mapping")
def delete_outline_dialog(row_data):
    """Dialog to confirm deletion of an outline mapping."""
    st.warning(
        f"Are you sure you want to delete the outline mapping for "
        f"**{row_data.get('program_name', '')}**?"
    )
    st.markdown("This action cannot be undone.")

    for k, v in row_data.items():
        st.text(f"{k}: {v}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("\U0001f5d1\ufe0f Delete", type="primary", use_container_width=True):
            idx = find_row_index(
                SHEET_OUTLINE_MAP, "program_name", row_data["program_name"],
            )
            if idx:
                clean = {k: str(v) for k, v in row_data.items()}
                with st.spinner("Deleting..."):
                    delete_row(SHEET_OUTLINE_MAP, idx)
                    log_delete(SHEET_OUTLINE_MAP, row_data["program_name"], clean)
                    invalidate_sheet_cache()
                if "selected_outline" in st.session_state:
                    del st.session_state["selected_outline"]
                invalidate_sheet_cache()
                st.rerun()
            else:
                st.error("Could not find the row to delete.")
    with col2:
        if st.button("Cancel", use_container_width=True):
            st.rerun()


def render_outline_map_tab():
    df = read_sheet(SHEET_OUTLINE_MAP)
    programs = get_program_names()

    expected_cols = ["program_name", "outline_filename", "google_drive_file_id"]
    if df.empty:
        df = pd.DataFrame(columns=expected_cols)
    else:
        df = ensure_columns(df, expected_cols)

    # Metrics
    total_mappings = len(df)
    total_programs = len(programs)
    has_outline = 0
    if not df.empty and "google_drive_file_id" in df.columns:
        has_outline = df["google_drive_file_id"].apply(
            lambda x: bool(str(x).strip())
        ).sum()
    missing_outline = total_mappings - has_outline
    programs_without = max(0, total_programs - total_mappings)

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        render_metric_card("Total Mapped", total_mappings)
    with m2:
        render_metric_card("With Drive Link", has_outline)
    with m3:
        render_metric_card("Missing Link", missing_outline)
    with m4:
        render_metric_card("Unmapped Programs", programs_without)

    st.markdown("---")

    # Search
    search = render_search_bar("outline_search", "Search outline mappings...")

    display_df = filter_dataframe(df, search) if not df.empty else df

    # Add preview link column for display
    display_with_links = display_df.copy()
    if "google_drive_file_id" in display_with_links.columns:
        display_with_links["preview_link"] = display_with_links["google_drive_file_id"].apply(
            lambda fid: f"https://drive.google.com/file/d/{fid}/view"
            if str(fid).strip() else ""
        )
    else:
        display_with_links["preview_link"] = ""

    if not programs:
        st.warning("Add programs first before managing outline mappings.")

    # Data table (read-only with selection)
    event = st.dataframe(
        display_with_links,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="outline_table",
        column_config={
            "program_name": st.column_config.TextColumn("Program", width="large"),
            "outline_filename": st.column_config.TextColumn(
                "Outline Filename", width="medium",
            ),
            "google_drive_file_id": st.column_config.TextColumn(
                "Drive File ID", width="medium",
            ),
            "preview_link": st.column_config.LinkColumn(
                "Preview", display_text="Open", width="small",
            ),
        },
        column_order=[
            "program_name", "outline_filename",
            "google_drive_file_id", "preview_link",
        ],
    )

    # Track selection (use display_df without preview_link for stored data)
    if event and event.selection and event.selection.rows:
        selected_idx = event.selection.rows[0]
        st.session_state["selected_outline"] = display_df.iloc[selected_idx].to_dict()
    else:
        if "selected_outline" in st.session_state:
            del st.session_state["selected_outline"]

    # Action buttons AFTER table (so selection is already processed)
    has_selection = "selected_outline" in st.session_state
    b1, b2, b3, b4 = st.columns([1, 1, 1, 2])
    with b1:
        if st.button("\u2795 Add", use_container_width=True, key="outline_add"):
            add_outline_dialog()
    with b2:
        if st.button(
            "\u270f\ufe0f Edit",
            use_container_width=True,
            disabled=not has_selection,
            key="outline_edit",
        ):
            edit_outline_dialog(st.session_state.get("selected_outline", {}))
    with b3:
        if st.button(
            "\U0001f5d1\ufe0f Delete",
            use_container_width=True,
            disabled=not has_selection,
            key="outline_del",
        ):
            delete_outline_dialog(st.session_state.get("selected_outline", {}))
    with b4:
        if has_selection:
            sel = st.session_state["selected_outline"]
            st.info(
                f"Selected: **{sel['program_name']}** "
                f"({sel.get('outline_filename', 'no filename')})"
            )

    if total_mappings > 0:
        st.caption(f"Showing {len(display_df)} of {total_mappings} mappings")

    # Programs missing outlines
    if programs:
        mapped = (
            set(df["program_name"].tolist())
            if not df.empty and "program_name" in df.columns
            else set()
        )
        missing = sorted(set(programs) - mapped)
        if missing:
            with st.expander(f"Programs missing outline mapping ({len(missing)})"):
                for prog_name in missing:
                    st.markdown(f"- {prog_name}")


# ---------------------------------------------------------------------------
# Tab: Audit Log (read-only)
# ---------------------------------------------------------------------------


def render_audit_log_tab():
    st.caption("Read-only view of all changes to the data sheets.")

    df = read_sheet(SHEET_AUDIT_LOG)
    if df.empty:
        st.info("No audit records yet.")
        return

    # Metrics
    total = len(df)
    action_counts = df["action"].value_counts().to_dict() if "action" in df.columns else {}

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        render_metric_card("Total Records", total)
    with m2:
        render_metric_card("Creates", action_counts.get("CREATE", 0))
    with m3:
        render_metric_card("Updates", action_counts.get("UPDATE", 0))
    with m4:
        render_metric_card("Deletes", action_counts.get("DELETE", 0))

    st.markdown("---")

    # Filters
    col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
    with col1:
        tab_filter = st.multiselect(
            "Filter by Tab",
            options=sorted(df["tab_name"].dropna().unique().tolist())
            if "tab_name" in df.columns else [],
        )
    with col2:
        action_filter = st.multiselect(
            "Filter by Action",
            options=sorted(df["action"].dropna().unique().tolist())
            if "action" in df.columns else [],
        )
    with col3:
        if "timestamp" in df.columns and not df["timestamp"].empty:
            date_range = st.date_input(
                "Date range",
                value=[],
                key="audit_date_range",
            )
        else:
            date_range = []
    with col4:
        search = render_search_bar(
            "audit_search",
            "Search by identifier, field, value...",
        )

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

    # Reverse chronological
    filtered = filtered.iloc[::-1].reset_index(drop=True)

    st.dataframe(
        filtered,
        use_container_width=True,
        hide_index=True,
        column_config={
            "timestamp": st.column_config.TextColumn("Timestamp", width="medium"),
            "user": st.column_config.TextColumn("User", width="small"),
            "action": st.column_config.TextColumn("Action", width="small"),
            "tab_name": st.column_config.TextColumn("Tab", width="small"),
            "row_identifier": st.column_config.TextColumn("Row ID", width="medium"),
            "field_name": st.column_config.TextColumn("Field", width="medium"),
            "old_value": st.column_config.TextColumn("Old Value", width="medium"),
            "new_value": st.column_config.TextColumn("New Value", width="medium"),
        },
    )
    st.caption(f"Showing {len(filtered)} of {total} records (newest first).")


# ---------------------------------------------------------------------------
# Tab: Contract Log (read-only)
# ---------------------------------------------------------------------------


def render_contract_log_tab():
    st.caption("Read-only view of all generated contracts.")

    df = read_sheet(SHEET_CONTRACT_LOG)
    if df.empty:
        st.info("No contracts generated yet.")
        return

    # Metrics
    total = len(df)
    status_counts = df["status"].value_counts().to_dict() if "status" in df.columns else {}
    prog_count = df["program_name"].nunique() if "program_name" in df.columns else 0

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        render_metric_card("Total Contracts", total)
    with m2:
        render_metric_card("Programs", prog_count)
    with m3:
        completed = (
            status_counts.get("completed", 0) + status_counts.get("Completed", 0)
        )
        render_metric_card("Completed", completed)
    with m4:
        pending = (
            status_counts.get("pending", 0) + status_counts.get("Pending", 0)
        )
        render_metric_card("Pending", pending)

    st.markdown("---")

    # Filters
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
        search = render_search_bar(
            "contract_search",
            "Search by student name, program, status...",
        )

    filtered = df.copy()
    if prog_filter:
        filtered = filtered[filtered["program_name"].isin(prog_filter)]
    if status_filter:
        filtered = filtered[filtered["status"].isin(status_filter)]
    filtered = filter_dataframe(filtered, search)

    # Reverse chronological
    filtered = filtered.iloc[::-1].reset_index(drop=True)

    st.dataframe(filtered, use_container_width=True, hide_index=True)
    st.caption(f"Showing {len(filtered)} of {total} records (newest first).")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    st.set_page_config(
        page_title="WCC Contract Admin",
        page_icon="\U0001f4cb",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Custom CSS — theme-aware (no hardcoded text/background colors on main page)
    st.markdown("""
    <style>
        /* Sidebar nav styling — theme-aware */
        [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label {
            padding: 8px 12px;
            border-radius: 6px;
            margin-bottom: 2px;
            transition: background-color 0.15s ease;
        }
        [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:hover {
            background-color: rgba(37, 99, 235, 0.1);
        }
        [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label[data-checked="true"] {
            background-color: #2563EB;
            color: #FFFFFF !important;
        }

        /* Metric cards — adapt to theme */
        [data-testid="stMetric"] {
            padding: 16px 20px;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
            border: 1px solid rgba(128,128,128,0.2);
        }
        div[data-testid="stMetricValue"] {
            font-size: 28px;
            color: #2563EB;
            font-weight: 700;
        }
        div[data-testid="stMetricLabel"] {
            font-size: 13px;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        /* Data table styling */
        .stDataFrame, .stDataEditor {
            font-size: 14px;
        }
        [data-testid="stDataFrameResizable"] {
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        }

        /* Primary button accent */
        .stButton > button[kind="primary"] {
            background-color: #2563EB;
            border-color: #2563EB;
        }
        .stButton > button[kind="primary"]:hover {
            background-color: #1D4ED8;
            border-color: #1D4ED8;
        }

        /* Search input */
        .stTextInput > div > div > input {
            border-color: #E2E8F0;
            border-radius: 6px;
        }
        .stTextInput > div > div > input:focus {
            border-color: #3B82F6;
            box-shadow: 0 0 0 2px rgba(59,130,246,0.15);
        }
    </style>
    """, unsafe_allow_html=True)

    if not check_auth():
        return

    # --- Sidebar navigation ---
    with st.sidebar:
        st.markdown("## WCC Contract Admin")
        st.caption("Data Management Dashboard")

        st.markdown("---")

        # Build nav items (skip separator entries)
        selectable_items = [item for item in NAV_ITEMS if item != "---"]
        selected_tab = st.radio(
            "Navigation",
            selectable_items,
            format_func=lambda x: f"{NAV_ICONS.get(x, '\U0001f4c4')} {x}",
            label_visibility="collapsed",
        )

        st.markdown("---")

        if st.button(
            "\U0001f504 Refresh Data",
            use_container_width=True,
        ):
            invalidate_sheet_cache()
            st.rerun()

        st.markdown("---")

        if st.button(
            "\U0001f6aa Logout",
            use_container_width=True,
            type="secondary",
        ):
            st.session_state["authenticated"] = False
            st.rerun()

        st.markdown("")
        st.caption("WCC Contract Generator v3.0")

    # --- Main content area ---
    icon = NAV_ICONS.get(selected_tab, "\U0001f4c4")
    st.title(f"{icon} {selected_tab}")

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
