"""
WCC Contract Generator — Streamlit Admin Panel

Inline-editable data grid dashboard for Programs, Intakes, Fees, Outline Map.
Provides spreadsheet-style CRUD with field-level audit logging to Google Sheets.

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
    "Programs": "🎓",
    "Intakes": "📅",
    "Fees": "💲",
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
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.markdown("</div></div>", unsafe_allow_html=True)
    return False


# ---------------------------------------------------------------------------
# Change detection and save logic
# ---------------------------------------------------------------------------


def detect_changes(original_df, edited_df, key_columns, data_columns):
    """Compare original and edited DataFrames.

    Returns a dict with keys: edited, added, deleted.
    - edited: list of dicts describing cell-level changes
    - added: list of dicts for new rows
    - deleted: list of dicts for rows marked for deletion
    """
    changes = {"edited": [], "added": [], "deleted": []}

    # Work on copies to avoid mutation
    work_edited = edited_df.copy()

    # Detect deletes (rows with delete checkbox checked)
    if "delete" in work_edited.columns:
        to_delete = work_edited[work_edited["delete"] == True]  # noqa: E712
        changes["deleted"] = to_delete.to_dict("records")
        work_edited = work_edited[work_edited["delete"] != True]  # noqa: E712

    # Detect new rows (rows beyond the original length, after removing deletes)
    original_count = len(original_df)
    # Account for deleted rows that were in original range
    deleted_in_original = 0
    for rec in changes["deleted"]:
        # Check if this deleted row was from the original set
        for idx in range(original_count):
            orig_row = original_df.iloc[idx]
            match = all(
                str(orig_row.get(kc, "")) == str(rec.get(kc, ""))
                for kc in key_columns
                if kc in orig_row.index and kc in rec
            )
            if match:
                deleted_in_original += 1
                break

    # New rows are those in edited_df (with delete=False) that don't match originals
    if len(work_edited) > (original_count - deleted_in_original):
        new_count = len(work_edited) - (original_count - deleted_in_original)
        new_rows = work_edited.tail(new_count)
        changes["added"] = new_rows.to_dict("records")

    # Detect edits (compare cell-by-cell for existing rows that aren't deleted)
    compare_cols = [c for c in data_columns if c != "delete"]
    surviving_original_count = original_count - deleted_in_original
    compare_count = min(surviving_original_count, len(work_edited) - len(changes["added"]))

    # Build a mapping from remaining edited rows back to original rows
    edited_existing = work_edited.head(compare_count)
    orig_idx = 0
    for edit_idx in range(compare_count):
        # Skip original rows that were deleted
        while orig_idx < original_count:
            orig_row = original_df.iloc[orig_idx]
            was_deleted = False
            for rec in changes["deleted"]:
                match = all(
                    str(orig_row.get(kc, "")) == str(rec.get(kc, ""))
                    for kc in key_columns
                    if kc in orig_row.index and kc in rec
                )
                if match:
                    was_deleted = True
                    break
            if not was_deleted:
                break
            orig_idx += 1

        if orig_idx >= original_count:
            break

        edited_row = edited_existing.iloc[edit_idx]
        orig_row = original_df.iloc[orig_idx]

        for col in compare_cols:
            old_val = str(orig_row.get(col, ""))
            new_val = str(edited_row.get(col, ""))
            if old_val != new_val:
                identifier = str(edited_row.get(key_columns[0], f"row-{edit_idx}"))
                changes["edited"].append({
                    "row_sheet_index": orig_idx,
                    "col": col,
                    "old": old_val,
                    "new": new_val,
                    "identifier": identifier,
                })
        orig_idx += 1

    return changes


def build_change_summary(changes):
    """Return a human-readable summary string for changes."""
    parts = []
    n_edited = len(changes["edited"])
    n_added = len(changes["added"])
    n_deleted = len(changes["deleted"])

    if n_edited > 0:
        parts.append(f"{n_edited} cell{'s' if n_edited != 1 else ''} edited")
    if n_added > 0:
        parts.append(f"{n_added} row{'s' if n_added != 1 else ''} added")
    if n_deleted > 0:
        parts.append(f"{n_deleted} row{'s' if n_deleted != 1 else ''} to delete")

    if not parts:
        return ""
    return ", ".join(parts)


def apply_changes(sheet_name, changes, key_columns, data_columns, original_df):
    """Apply detected changes to Google Sheets and log each action.

    Returns (success_count, error_messages).
    """
    success = 0
    errors = []
    columns_no_delete = [c for c in data_columns if c != "delete"]

    # Process deletes first (in reverse order to keep row indices stable)
    delete_indices = []
    for rec in changes["deleted"]:
        match = {k: str(rec.get(k, "")) for k in key_columns if k in rec}
        if len(match) == 1:
            col_name = list(match.keys())[0]
            idx = find_row_index(sheet_name, col_name, match[col_name])
        else:
            idx = find_row_index_multi(sheet_name, match)
        if idx is not None:
            delete_indices.append((idx, rec))
        else:
            identifier = str(rec.get(key_columns[0], "unknown"))
            errors.append(f"Could not find row to delete: {identifier}")

    # Sort in reverse so higher row indices are deleted first
    delete_indices.sort(key=lambda x: x[0], reverse=True)
    for idx, rec in delete_indices:
        clean = {k: v for k, v in rec.items() if k != "delete"}
        identifier = str(rec.get(key_columns[0], "unknown"))
        try:
            delete_row(sheet_name, idx)
            log_delete(sheet_name, identifier, clean)
            success += 1
        except Exception as exc:
            errors.append(f"Delete failed for {identifier}: {exc}")

    # Process edits (grouped by row)
    edited_rows = {}
    for change in changes["edited"]:
        row_idx = change["row_sheet_index"]
        if row_idx not in edited_rows:
            edited_rows[row_idx] = []
        edited_rows[row_idx].append(change)

    for row_idx, cell_changes in edited_rows.items():
        orig_row = original_df.iloc[row_idx]
        # Build the updated row values
        new_row_dict = {c: str(orig_row.get(c, "")) for c in columns_no_delete}
        for cc in cell_changes:
            new_row_dict[cc["col"]] = cc["new"]

        match = {k: str(orig_row.get(k, "")) for k in key_columns}
        if len(match) == 1:
            col_name = list(match.keys())[0]
            sheet_idx = find_row_index(sheet_name, col_name, match[col_name])
        else:
            sheet_idx = find_row_index_multi(sheet_name, match)

        if sheet_idx is not None:
            row_values = [new_row_dict.get(c, "") for c in columns_no_delete]
            try:
                update_row(sheet_name, sheet_idx, row_values)
                identifier = cell_changes[0]["identifier"]
                for cc in cell_changes:
                    log_audit(
                        "UPDATE", sheet_name, identifier,
                        cc["col"], cc["old"], cc["new"],
                    )
                success += 1
            except Exception as exc:
                errors.append(f"Update failed for row {row_idx}: {exc}")
        else:
            errors.append(f"Could not find row to update at original index {row_idx}")

    # Process adds
    for rec in changes["added"]:
        row_values = [str(rec.get(c, "")) for c in columns_no_delete]
        identifier = str(rec.get(key_columns[0], "new"))
        try:
            append_row(sheet_name, row_values)
            field_dict = {c: str(rec.get(c, "")) for c in columns_no_delete}
            log_create(sheet_name, identifier, field_dict)
            success += 1
        except Exception as exc:
            errors.append(f"Add failed for {identifier}: {exc}")

    return success, errors


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


def render_save_button(changes, key):
    """Render the save changes button with a change summary.

    Returns True if the user confirmed save.
    """
    summary = build_change_summary(changes)
    has_changes = bool(summary)

    if not has_changes:
        st.button(
            "No changes to save",
            key=key,
            disabled=True,
            use_container_width=True,
        )
        return False

    # Show confirmation flow
    confirm_key = f"{key}_confirmed"
    if confirm_key not in st.session_state:
        st.session_state[confirm_key] = False

    col1, col2 = st.columns([3, 1])
    with col1:
        if st.button(
            f"Save Changes ({summary})",
            key=key,
            type="primary",
            use_container_width=True,
        ):
            st.session_state[confirm_key] = True
            st.rerun()
    with col2:
        if st.session_state.get(confirm_key):
            if st.button("Cancel", key=f"{key}_cancel", use_container_width=True):
                st.session_state[confirm_key] = False
                st.rerun()

    if st.session_state.get(confirm_key):
        st.warning(f"Confirm: {summary}. This cannot be undone.")
        if st.button(
            "Confirm and Apply",
            key=f"{key}_apply",
            type="primary",
        ):
            st.session_state[confirm_key] = False
            return True

    return False


def ensure_columns(df, columns, defaults=None):
    """Ensure a DataFrame has the expected columns. Add missing ones with defaults."""
    defaults = defaults or {}
    result = df.copy()
    for col in columns:
        if col not in result.columns:
            result[col] = defaults.get(col, "")
    return result[columns]


# ---------------------------------------------------------------------------
# Tab: Programs
# ---------------------------------------------------------------------------


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

    # Search + filter row
    search_col, _ = st.columns([2, 3])
    with search_col:
        search = render_search_bar("prog_search", "Search programs by name, code...")

    # Prepare editable dataframe
    display_df = filter_dataframe(df, search) if not df.empty else df
    display_df = display_df.copy()
    display_df["delete"] = False

    # Store original for comparison (the filtered view only)
    original_df = df.copy()

    edited_df = st.data_editor(
        display_df,
        column_config={
            "program_name": st.column_config.TextColumn(
                "Program Name",
                required=True,
                width="large",
            ),
            "program_code": st.column_config.TextColumn(
                "Program Code",
                required=True,
            ),
            "credential": st.column_config.SelectboxColumn(
                "Credential",
                options=CREDENTIAL_OPTIONS,
                required=True,
            ),
            "delete": st.column_config.CheckboxColumn(
                "Delete",
                default=False,
                width="small",
            ),
        },
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key="programs_editor",
    )

    if not df.empty or len(edited_df) > len(display_df):
        st.caption(f"{len(display_df)} program{'s' if len(display_df) != 1 else ''} shown")

    # Detect changes
    changes = detect_changes(
        original_df=display_df.drop(columns=["delete"], errors="ignore"),
        edited_df=edited_df,
        key_columns=["program_name"],
        data_columns=["program_name", "program_code", "credential", "delete"],
    )

    st.markdown("")
    confirmed = render_save_button(changes, "prog_save")

    if confirmed:
        with st.spinner("Saving changes to Google Sheets..."):
            ok, errs = apply_changes(
                SHEET_PROGRAMS,
                changes,
                key_columns=["program_name"],
                data_columns=["program_name", "program_code", "credential", "delete"],
                original_df=display_df.drop(columns=["delete"], errors="ignore"),
            )
        if errs:
            for e in errs:
                st.error(e)
        if ok > 0:
            st.success(f"Saved {ok} change{'s' if ok != 1 else ''} successfully.")
            st.cache_resource.clear()
            st.rerun()


# ---------------------------------------------------------------------------
# Tab: Intakes
# ---------------------------------------------------------------------------


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

    display_df = display_df.copy()
    display_df["delete"] = False

    if not programs:
        st.warning("Add programs first before managing intakes.")

    edited_df = st.data_editor(
        display_df,
        column_config={
            "program_name": st.column_config.SelectboxColumn(
                "Program",
                options=programs,
                required=True,
                width="large",
            ),
            "intake_date": st.column_config.TextColumn(
                "Intake Date",
                required=True,
            ),
            "end_date": st.column_config.TextColumn(
                "End Date",
                required=True,
            ),
            "campus": st.column_config.SelectboxColumn(
                "Campus",
                options=CAMPUS_OPTIONS,
                required=True,
            ),
            "hours": st.column_config.TextColumn("Hours"),
            "weeks": st.column_config.TextColumn("Weeks"),
            "spots_available": st.column_config.NumberColumn(
                "Spots",
                min_value=0,
                step=1,
            ),
            "status": st.column_config.SelectboxColumn(
                "Status",
                options=STATUS_OPTIONS,
                required=True,
            ),
            "domestic_delivery_method": st.column_config.SelectboxColumn(
                "Dom. Delivery",
                options=DELIVERY_OPTIONS,
            ),
            "international_delivery_method": st.column_config.SelectboxColumn(
                "Intl. Delivery",
                options=DELIVERY_OPTIONS,
            ),
            "delete": st.column_config.CheckboxColumn(
                "Delete",
                default=False,
                width="small",
            ),
        },
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key="intakes_editor",
    )

    if total > 0 or len(edited_df) > len(display_df):
        st.caption(f"Showing {len(display_df)} of {total} intakes")

    # Detect changes
    changes = detect_changes(
        original_df=display_df.drop(columns=["delete"], errors="ignore"),
        edited_df=edited_df,
        key_columns=["program_name", "intake_date", "campus"],
        data_columns=expected_cols + ["delete"],
    )

    st.markdown("")
    confirmed = render_save_button(changes, "int_save")

    if confirmed:
        with st.spinner("Saving changes to Google Sheets..."):
            ok, errs = apply_changes(
                SHEET_INTAKES,
                changes,
                key_columns=["program_name", "intake_date", "campus"],
                data_columns=expected_cols + ["delete"],
                original_df=display_df.drop(columns=["delete"], errors="ignore"),
            )
        if errs:
            for e in errs:
                st.error(e)
        if ok > 0:
            st.success(f"Saved {ok} change{'s' if ok != 1 else ''} successfully.")
            st.cache_resource.clear()
            st.rerun()


# ---------------------------------------------------------------------------
# Tab: Fees
# ---------------------------------------------------------------------------


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

    display_df = display_df.copy()
    display_df["delete"] = False

    if not programs:
        st.warning("Add programs first before managing fees.")

    edited_df = st.data_editor(
        display_df,
        column_config={
            "program_name": st.column_config.SelectboxColumn(
                "Program",
                options=programs,
                required=True,
                width="large",
            ),
            "effective_from": st.column_config.TextColumn(
                "Effective From",
                required=True,
            ),
            "fee_name": st.column_config.SelectboxColumn(
                "Fee Name",
                options=FEE_NAME_OPTIONS,
                required=True,
            ),
            "domestic_amount": st.column_config.NumberColumn(
                "Domestic $",
                format="$%.2f",
                min_value=0.0,
                step=0.01,
            ),
            "international_amount": st.column_config.NumberColumn(
                "International $",
                format="$%.2f",
                min_value=0.0,
                step=0.01,
            ),
            "is_tuition": st.column_config.CheckboxColumn(
                "Tuition?",
                default=False,
            ),
            "sort_order": st.column_config.NumberColumn(
                "Sort",
                min_value=1,
                step=1,
            ),
            "delete": st.column_config.CheckboxColumn(
                "Delete",
                default=False,
                width="small",
            ),
        },
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key="fees_editor",
    )

    if total > 0 or len(edited_df) > len(display_df):
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

    # Detect changes — need to handle is_tuition conversion for sheets
    changes = detect_changes(
        original_df=display_df.drop(columns=["delete"], errors="ignore"),
        edited_df=edited_df,
        key_columns=["program_name", "fee_name", "sort_order"],
        data_columns=expected_cols + ["delete"],
    )

    st.markdown("")
    confirmed = render_save_button(changes, "fee_save")

    if confirmed:
        # Convert is_tuition back to string for Google Sheets
        for rec in changes["added"]:
            rec["is_tuition"] = str(rec.get("is_tuition", False)).upper()
        for change in changes["edited"]:
            if change["col"] == "is_tuition":
                change["new"] = str(change["new"]).upper()

        with st.spinner("Saving changes to Google Sheets..."):
            ok, errs = apply_changes(
                SHEET_FEES,
                changes,
                key_columns=["program_name", "fee_name", "sort_order"],
                data_columns=expected_cols + ["delete"],
                original_df=display_df.drop(columns=["delete"], errors="ignore"),
            )
        if errs:
            for e in errs:
                st.error(e)
        if ok > 0:
            st.success(f"Saved {ok} change{'s' if ok != 1 else ''} successfully.")
            st.cache_resource.clear()
            st.rerun()


# ---------------------------------------------------------------------------
# Tab: Outline Map
# ---------------------------------------------------------------------------


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
    search_col, _ = st.columns([2, 3])
    with search_col:
        search = render_search_bar("outline_search", "Search outline mappings...")

    display_df = filter_dataframe(df, search) if not df.empty else df
    display_df = display_df.copy()

    # Add preview link column for display
    if "google_drive_file_id" in display_df.columns:
        display_df["preview_link"] = display_df["google_drive_file_id"].apply(
            lambda fid: f"https://drive.google.com/file/d/{fid}/view"
            if str(fid).strip() else ""
        )
    else:
        display_df["preview_link"] = ""

    display_df["delete"] = False

    edited_df = st.data_editor(
        display_df,
        column_config={
            "program_name": st.column_config.SelectboxColumn(
                "Program",
                options=programs,
                required=True,
                width="large",
            ),
            "outline_filename": st.column_config.TextColumn(
                "Outline Filename",
                width="medium",
            ),
            "google_drive_file_id": st.column_config.TextColumn(
                "Drive File ID",
                width="medium",
            ),
            "preview_link": st.column_config.LinkColumn(
                "Preview",
                display_text="Open",
                width="small",
                disabled=True,
            ),
            "delete": st.column_config.CheckboxColumn(
                "Delete",
                default=False,
                width="small",
            ),
        },
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key="outline_editor",
        column_order=[
            "program_name", "outline_filename",
            "google_drive_file_id", "preview_link", "delete",
        ],
    )

    if total_mappings > 0:
        st.caption(f"Showing {len(display_df)} of {total_mappings} mappings")

    # Programs missing outlines
    if programs:
        mapped = set(df["program_name"].tolist()) if not df.empty and "program_name" in df.columns else set()
        missing = sorted(set(programs) - mapped)
        if missing:
            with st.expander(f"Programs missing outline mapping ({len(missing)})"):
                for prog_name in missing:
                    st.markdown(f"- {prog_name}")

    if not programs:
        st.warning("Add programs first before managing outline mappings.")

    # Detect changes (exclude preview_link from comparison)
    changes = detect_changes(
        original_df=display_df.drop(columns=["delete", "preview_link"], errors="ignore"),
        edited_df=edited_df.drop(columns=["preview_link"], errors="ignore"),
        key_columns=["program_name"],
        data_columns=expected_cols + ["delete"],
    )

    st.markdown("")
    confirmed = render_save_button(changes, "outline_save")

    if confirmed:
        with st.spinner("Saving changes to Google Sheets..."):
            ok, errs = apply_changes(
                SHEET_OUTLINE_MAP,
                changes,
                key_columns=["program_name"],
                data_columns=expected_cols + ["delete"],
                original_df=display_df.drop(
                    columns=["delete", "preview_link"], errors="ignore"
                ),
            )
        if errs:
            for e in errs:
                st.error(e)
        if ok > 0:
            st.success(f"Saved {ok} change{'s' if ok != 1 else ''} successfully.")
            st.cache_resource.clear()
            st.rerun()


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
        page_icon="📋",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Custom CSS for data-dense dashboard
    st.markdown("""
    <style>
        /* Page background */
        .stApp { background-color: #F8FAFC; }

        /* Sidebar styling */
        [data-testid="stSidebar"] {
            background-color: #1E293B;
        }
        [data-testid="stSidebar"] .stMarkdown,
        [data-testid="stSidebar"] .stMarkdown p,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] .stRadio label {
            color: #F8FAFC !important;
        }
        [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label {
            color: #CBD5E1 !important;
            padding: 8px 12px;
            border-radius: 6px;
            margin-bottom: 2px;
            transition: background-color 0.15s ease;
        }
        [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:hover {
            background-color: #334155;
            color: #F8FAFC !important;
        }
        [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label[data-checked="true"] {
            background-color: #2563EB;
            color: #FFFFFF !important;
        }

        /* Metric cards */
        [data-testid="stMetric"] {
            background: white;
            padding: 16px 20px;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
            border: 1px solid #E2E8F0;
        }
        div[data-testid="stMetricValue"] {
            font-size: 28px;
            color: #2563EB;
            font-weight: 700;
        }
        div[data-testid="stMetricLabel"] {
            color: #64748B;
            font-size: 13px;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        /* Data editor / dataframe styling */
        .stDataFrame, .stDataEditor {
            font-size: 14px;
        }
        [data-testid="stDataFrameResizable"] {
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        }

        /* Table header styling */
        .stDataFrame thead th {
            background-color: #F1F5F9 !important;
            color: #475569 !important;
            font-weight: 600 !important;
            text-transform: uppercase;
            font-size: 12px;
            letter-spacing: 0.05em;
        }

        /* Table row hover */
        .stDataFrame tbody tr:hover {
            background-color: #F8FAFC !important;
        }

        /* Alternate row colors */
        .stDataFrame tbody tr:nth-child(even) {
            background-color: #FAFBFC;
        }

        /* Title text */
        h1 { color: #1E293B; }

        /* Primary button accent */
        .stButton > button[kind="primary"] {
            background-color: #2563EB;
            border-color: #2563EB;
        }
        .stButton > button[kind="primary"]:hover {
            background-color: #1D4ED8;
            border-color: #1D4ED8;
        }

        /* Save button CTA styling */
        .stButton > button[kind="primary"][data-testid*="save"] {
            background-color: #F97316;
            border-color: #F97316;
        }
        .stButton > button[kind="primary"][data-testid*="save"]:hover {
            background-color: #EA580C;
            border-color: #EA580C;
        }

        /* Caption styling */
        .stCaption {
            color: #94A3B8;
        }

        /* Divider */
        hr {
            border-color: #E2E8F0;
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
        st.markdown(
            '<h2 style="color:#F8FAFC;margin-bottom:0;padding-left:4px;">'
            "WCC Contract Admin</h2>",
            unsafe_allow_html=True,
        )
        st.markdown(
            '<p style="color:#94A3B8;font-size:13px;margin-top:0;padding-left:4px;">'
            "Data Management Dashboard</p>",
            unsafe_allow_html=True,
        )

        st.markdown("---")

        # Build nav items (skip separator entries)
        selectable_items = [item for item in NAV_ITEMS if item != "---"]
        selected_tab = st.radio(
            "Navigation",
            selectable_items,
            format_func=lambda x: f"{NAV_ICONS.get(x, '📄')} {x}",
            label_visibility="collapsed",
        )

        st.markdown("---")

        if st.button(
            "🔄 Refresh Data",
            use_container_width=True,
        ):
            st.cache_resource.clear()
            st.rerun()

        st.markdown("---")

        if st.button(
            "🚪 Logout",
            use_container_width=True,
            type="secondary",
        ):
            st.session_state["authenticated"] = False
            st.rerun()

        st.markdown("")
        st.markdown(
            '<p style="color:#64748B;font-size:11px;text-align:center;">'
            "WCC Contract Generator v3.0</p>",
            unsafe_allow_html=True,
        )

    # --- Main content area ---
    icon = NAV_ICONS.get(selected_tab, "📄")
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
