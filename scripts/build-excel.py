"""
Build WCC_Contract_Data.xlsx with the v2 schema:
  1. Instructions (green tab)
  2. Programs (identity only: program_name, program_code, credential)
  3. Intakes (core entity with hours, weeks, delivery methods)
  4. Fees (with effective_from date)
  5. Outline Map

Run: python scripts/build-excel.py
"""
import csv
import random
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import CellIsRule, FormulaRule
from datetime import datetime, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# ---------------------------------------------------------------------------
# Styling constants
# ---------------------------------------------------------------------------
HEADER_FONT = Font(bold=True, color="FFFFFF", size=11)
HEADER_FILL = PatternFill(start_color="2F5496", end_color="2F5496", fill_type="solid")
HEADER_ALIGN = Alignment(horizontal="center", vertical="center", wrap_text=True)
THIN_BORDER = Border(
    left=Side(style="thin"),
    right=Side(style="thin"),
    top=Side(style="thin"),
    bottom=Side(style="thin"),
)

GREEN_FILL = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
RED_FILL = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
YELLOW_FILL = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
LIGHT_BLUE_FILL = PatternFill(start_color="DAEEF3", end_color="DAEEF3", fill_type="solid")

# ---------------------------------------------------------------------------
# Dropdown option lists
# ---------------------------------------------------------------------------
CREDENTIALS = ["Diploma", "Certificate", "Bachelor", "Post-Graduate Diploma"]
CAMPUSES = ["Burnaby", "New Westminster", "Surrey", "Online"]
STATUSES = ["Open", "Closed", "Waitlist"]
DELIVERY_METHODS = ["In-Class", "Distance", "Combined", "Hybrid"]
IS_TUITION_OPTIONS = ["TRUE", "FALSE"]
FEE_NAMES = [
    "Application Fee",
    "Administration Fee",
    "Registration Fee",
    "Assessment Fee",
    "Tuition Fee",
    "Tuition Fee Per Credit",
    "Course Materials",
    "Books",
    "Textbooks",
    "Ground School Fee",
    "Flight Hours",
    "Fuel",
    "Preparatory Ground",
    "Annual Technology Fee",
    "Scholarship",
    "Other",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def style_header(ws, num_cols):
    """Apply header styling, autofilter, and freeze panes."""
    for col in range(1, num_cols + 1):
        cell = ws.cell(row=1, column=col)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = HEADER_ALIGN
        cell.border = THIN_BORDER
    ws.auto_filter.ref = ws.dimensions
    ws.freeze_panes = "A2"


def auto_width(ws):
    """Auto-fit column widths based on content length."""
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            if cell.value is not None:
                max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = min(max_len + 3, 55)


def load_csv(filepath):
    """Return (fieldnames, rows) from a CSV file."""
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return reader.fieldnames, list(reader)


def make_list_validation(options, allow_blank=True):
    """Create a DataValidation dropdown from a Python list."""
    formula = '"' + ",".join(options) + '"'
    dv = DataValidation(type="list", formula1=formula, allow_blank=allow_blank)
    dv.error = "Please select a value from the dropdown list."
    dv.errorTitle = "Invalid Entry"
    dv.showErrorMessage = True
    return dv


def make_ref_validation(ref_formula, allow_blank=False):
    """Create a DataValidation dropdown referencing a named range / cell range."""
    dv = DataValidation(type="list", formula1=ref_formula, allow_blank=allow_blank)
    dv.error = "Value must match a program_name in the Programs tab."
    dv.errorTitle = "Invalid Program Name"
    dv.showErrorMessage = True
    return dv


def make_whole_validation(min_val=0, max_val=999999, allow_blank=True):
    """Whole-number validation with min/max."""
    dv = DataValidation(
        type="whole",
        operator="between",
        formula1=str(min_val),
        formula2=str(max_val),
        allow_blank=allow_blank,
    )
    dv.error = f"Enter a whole number between {min_val} and {max_val}."
    dv.errorTitle = "Invalid Number"
    dv.showErrorMessage = True
    return dv


def make_decimal_validation(min_val=-999999, max_val=999999, allow_blank=True):
    """Decimal validation with min/max."""
    dv = DataValidation(
        type="decimal",
        operator="between",
        formula1=str(min_val),
        formula2=str(max_val),
        allow_blank=allow_blank,
    )
    dv.error = f"Enter a number between {min_val} and {max_val}."
    dv.errorTitle = "Invalid Amount"
    dv.showErrorMessage = True
    return dv


def make_date_validation(allow_blank=True):
    """Date validation (any valid date)."""
    dv = DataValidation(
        type="date",
        operator="between",
        formula1="1900-01-01",
        formula2="2099-12-31",
        allow_blank=allow_blank,
    )
    dv.error = "Enter a valid date in YYYY-MM-DD format."
    dv.errorTitle = "Invalid Date"
    dv.showErrorMessage = True
    return dv


def col_range(col_letter, start_row=2, end_row=500):
    """Return a cell range string like 'A2:A500'."""
    return f"{col_letter}{start_row}:{col_letter}{end_row}"


# ---------------------------------------------------------------------------
# Intake generation
# ---------------------------------------------------------------------------


def generate_intakes(programs):
    """Generate 2-3 dummy intakes per program using the new schema columns."""
    random.seed(42)

    intakes = []
    for prog in programs:
        name = prog["program_name"]

        # Pull hours and weeks from the old programs CSV
        hours_str = prog.get("hours", "")
        weeks_str = prog.get("weeks_full_time", "")
        try:
            hours = int(float(hours_str)) if hours_str else ""
        except ValueError:
            hours = ""
        try:
            weeks = int(float(weeks_str)) if weeks_str else ""
        except ValueError:
            weeks = ""

        # Determine delivery method from old data
        old_delivery = prog.get("delivery_method", "In-class")
        domestic_dm = "In-Class"
        if old_delivery and "distance" in old_delivery.lower():
            domestic_dm = "Distance"
        international_dm = "In-Class"

        # How many weeks for end_date calculation
        duration_weeks = weeks if isinstance(weeks, int) and weeks > 0 else 24

        num_intakes = random.choice([2, 2, 3])
        possible_starts = [
            datetime(2026, 4, random.choice([7, 14, 21])),
            datetime(2026, 5, random.choice([5, 12, 19])),
            datetime(2026, 9, random.choice([8, 15, 22])),
            datetime(2026, 10, random.choice([5, 12])),
            datetime(2027, 1, random.choice([6, 13, 20])),
            datetime(2027, 2, random.choice([3, 10, 17])),
        ]
        chosen_starts = sorted(
            random.sample(possible_starts, min(num_intakes, len(possible_starts)))
        )

        for start in chosen_starts:
            end = start + timedelta(weeks=duration_weeks)
            campus = random.choice(CAMPUSES)
            status = random.choice(["Open", "Open", "Open", "Closed", "Waitlist"])
            spots = (
                random.randint(2, 25)
                if status == "Open"
                else (0 if status == "Closed" else random.randint(0, 3))
            )

            intakes.append(
                {
                    "program_name": name,
                    "intake_date": start.strftime("%Y-%m-%d"),
                    "end_date": end.strftime("%Y-%m-%d"),
                    "campus": campus,
                    "hours": hours,
                    "weeks": weeks,
                    "spots_available": spots,
                    "status": status,
                    "domestic_delivery_method": domestic_dm,
                    "international_delivery_method": international_dm,
                }
            )

    intakes.sort(key=lambda x: (x["program_name"], x["intake_date"]))
    return intakes


# ---------------------------------------------------------------------------
# Build workbook
# ---------------------------------------------------------------------------


def main():
    # ------------------------------------------------------------------
    # Load source data
    # ------------------------------------------------------------------
    _, programs_raw = load_csv(DATA_DIR / "demo-programs.csv")
    _, fees_raw = load_csv(DATA_DIR / "demo-fees.csv")
    _, outlines_raw = load_csv(DATA_DIR / "program-outline-map.csv")

    intakes = generate_intakes(programs_raw)
    print(f"Generated {len(intakes)} dummy intakes for {len(programs_raw)} programs")

    # Extract program names for reference validation
    program_names = [p["program_name"] for p in programs_raw]

    wb = openpyxl.Workbook()

    # ==================================================================
    # TAB 1 — Instructions (green tab, first position)
    # ==================================================================
    ws_instr = wb.active
    ws_instr.title = "Instructions"
    ws_instr.sheet_properties.tabColor = "00B050"

    instructions = [
        ["WCC Contract Data — Instructions"],
        [""],
        [
            "This workbook feeds the Contract Generator and HubSpot CRM card app."
        ],
        [
            "Program names MUST match HubSpot 'Program of Study' property values EXACTLY."
        ],
        [""],
        ["Tab", "Purpose", "Key Rules"],
        [
            "Programs",
            "Identity list: name, code, credential",
            "program_name must be unique and match HubSpot exactly",
        ],
        [
            "Intakes",
            "Enrollment windows per program",
            "intake_date < end_date; status must be Open/Closed/Waitlist",
        ],
        [
            "Fees",
            "Fee line items with effective_from date",
            "Amounts are numbers only — no $ signs; sort_order controls display order",
        ],
        [
            "Outline Map",
            "Maps programs to PDF outline filenames",
            "One row per program",
        ],
        [""],
        ["CRITICAL RULES:"],
        [
            '1. program_name must match the HubSpot "Program of Study" property value EXACTLY'
        ],
        ["2. Fee amounts are numbers only — no dollar signs, no commas"],
        ["3. Intake status must be: Open, Closed, or Waitlist"],
        ["4. intake_date and end_date format: YYYY-MM-DD"],
        ["5. sort_order in Fees determines the display order on the contract"],
        [
            "6. effective_from in Fees sets the date from which that fee schedule applies"
        ],
        [
            "7. Credential must be one of: Diploma, Certificate, Bachelor, Post-Graduate Diploma"
        ],
        [
            "8. Delivery method must be one of: In-Class, Distance, Combined, Hybrid"
        ],
        [""],
        ["CONDITIONAL FORMATTING LEGEND:"],
        ["RED cells — blank required field or Closed status"],
        ["YELLOW cells — $0 fee amount (verify if intentional) or Waitlist status"],
        ["GREEN cells — Open status"],
        ["LIGHT BLUE cells — Scholarship row (negative amount)"],
        [""],
        [
            "DUMMY INTAKES: The Intakes tab has sample data for testing. Replace with real dates before go-live."
        ],
        [""],
        [
            "Last updated: 2026-03-24 — Rebuilt with v2 schema (slimmed Programs, expanded Intakes, effective_from on Fees)"
        ],
    ]
    for ri, row_data in enumerate(instructions, 1):
        for ci, val in enumerate(row_data, 1):
            cell = ws_instr.cell(row=ri, column=ci, value=val)
            if ri == 1:
                cell.font = Font(bold=True, size=14)
            elif ri == 6:
                cell.font = Font(bold=True, size=11)
            elif ri == 12:
                cell.font = Font(bold=True, color="CC0000", size=11)
            elif ri == 22:
                cell.font = Font(bold=True, size=11)
    ws_instr.column_dimensions["A"].width = 80
    ws_instr.column_dimensions["B"].width = 50
    ws_instr.column_dimensions["C"].width = 60

    # ==================================================================
    # TAB 2 — Programs (identity only)
    # ==================================================================
    ws_prog = wb.create_sheet("Programs")
    prog_headers = ["program_name", "program_code", "credential"]
    for ci, h in enumerate(prog_headers, 1):
        ws_prog.cell(row=1, column=ci, value=h)

    for ri, prog in enumerate(programs_raw, 2):
        ws_prog.cell(row=ri, column=1, value=prog.get("program_name", ""))
        ws_prog.cell(row=ri, column=2, value=prog.get("program_code", ""))
        ws_prog.cell(row=ri, column=3, value=prog.get("credential", ""))

    style_header(ws_prog, len(prog_headers))
    auto_width(ws_prog)

    # Validations — credential dropdown
    dv_credential = make_list_validation(CREDENTIALS, allow_blank=False)
    dv_credential.add(col_range("C", 2, 200))
    ws_prog.add_data_validation(dv_credential)

    # Conditional formatting — blank program_name (col A)
    ws_prog.conditional_formatting.add(
        col_range("A", 2, 200),
        FormulaRule(formula=['ISBLANK(A2)'], fill=RED_FILL),
    )

    # ==================================================================
    # TAB 3 — Intakes (core entity)
    # ==================================================================
    ws_intakes = wb.create_sheet("Intakes")
    intake_headers = [
        "program_name",
        "intake_date",
        "end_date",
        "campus",
        "hours",
        "weeks",
        "spots_available",
        "status",
        "domestic_delivery_method",
        "international_delivery_method",
    ]
    for ci, h in enumerate(intake_headers, 1):
        ws_intakes.cell(row=1, column=ci, value=h)

    for ri, intake in enumerate(intakes, 2):
        ws_intakes.cell(row=ri, column=1, value=intake["program_name"])
        ws_intakes.cell(row=ri, column=2, value=intake["intake_date"])
        ws_intakes.cell(row=ri, column=3, value=intake["end_date"])
        ws_intakes.cell(row=ri, column=4, value=intake["campus"])
        # hours — write as number if available
        h_val = intake["hours"]
        ws_intakes.cell(row=ri, column=5, value=h_val if h_val != "" else None)
        # weeks — write as number if available
        w_val = intake["weeks"]
        ws_intakes.cell(row=ri, column=6, value=w_val if w_val != "" else None)
        ws_intakes.cell(row=ri, column=7, value=int(intake["spots_available"]))
        ws_intakes.cell(row=ri, column=8, value=intake["status"])
        ws_intakes.cell(row=ri, column=9, value=intake["domestic_delivery_method"])
        ws_intakes.cell(row=ri, column=10, value=intake["international_delivery_method"])

    style_header(ws_intakes, len(intake_headers))
    auto_width(ws_intakes)

    # --- Intakes validations ---
    max_intake_row = 500

    # program_name dropdown from Programs tab
    dv_intake_prog = make_ref_validation("=Programs!$A$2:$A$200")
    dv_intake_prog.add(col_range("A", 2, max_intake_row))
    ws_intakes.add_data_validation(dv_intake_prog)

    # campus dropdown
    dv_campus = make_list_validation(CAMPUSES, allow_blank=False)
    dv_campus.add(col_range("D", 2, max_intake_row))
    ws_intakes.add_data_validation(dv_campus)

    # hours — decimal > 0
    dv_hours = make_decimal_validation(min_val=1, max_val=99999, allow_blank=True)
    dv_hours.add(col_range("E", 2, max_intake_row))
    ws_intakes.add_data_validation(dv_hours)

    # weeks — decimal > 0
    dv_weeks = make_decimal_validation(min_val=1, max_val=9999, allow_blank=True)
    dv_weeks.add(col_range("F", 2, max_intake_row))
    ws_intakes.add_data_validation(dv_weeks)

    # spots_available — whole >= 0
    dv_spots = make_whole_validation(min_val=0, max_val=999)
    dv_spots.add(col_range("G", 2, max_intake_row))
    ws_intakes.add_data_validation(dv_spots)

    # status dropdown
    dv_status = make_list_validation(STATUSES, allow_blank=False)
    dv_status.add(col_range("H", 2, max_intake_row))
    ws_intakes.add_data_validation(dv_status)

    # domestic_delivery_method dropdown
    dv_dom_dm = make_list_validation(DELIVERY_METHODS, allow_blank=True)
    dv_dom_dm.add(col_range("I", 2, max_intake_row))
    ws_intakes.add_data_validation(dv_dom_dm)

    # international_delivery_method dropdown
    dv_intl_dm = make_list_validation(DELIVERY_METHODS, allow_blank=True)
    dv_intl_dm.add(col_range("J", 2, max_intake_row))
    ws_intakes.add_data_validation(dv_intl_dm)

    # date validations
    dv_intake_date = make_date_validation(allow_blank=False)
    dv_intake_date.add(col_range("B", 2, max_intake_row))
    ws_intakes.add_data_validation(dv_intake_date)

    dv_end_date = make_date_validation(allow_blank=False)
    dv_end_date.add(col_range("C", 2, max_intake_row))
    ws_intakes.add_data_validation(dv_end_date)

    # --- Intakes conditional formatting ---
    # Blank required: program_name (A), intake_date (B)
    ws_intakes.conditional_formatting.add(
        col_range("A", 2, max_intake_row),
        FormulaRule(formula=['ISBLANK(A2)'], fill=RED_FILL),
    )
    ws_intakes.conditional_formatting.add(
        col_range("B", 2, max_intake_row),
        FormulaRule(formula=['ISBLANK(B2)'], fill=RED_FILL),
    )

    # Status colours: Open=green, Closed=red, Waitlist=yellow
    ws_intakes.conditional_formatting.add(
        col_range("H", 2, max_intake_row),
        CellIsRule(operator="equal", formula=['"Open"'], fill=GREEN_FILL),
    )
    ws_intakes.conditional_formatting.add(
        col_range("H", 2, max_intake_row),
        CellIsRule(operator="equal", formula=['"Closed"'], fill=RED_FILL),
    )
    ws_intakes.conditional_formatting.add(
        col_range("H", 2, max_intake_row),
        CellIsRule(operator="equal", formula=['"Waitlist"'], fill=YELLOW_FILL),
    )

    # ==================================================================
    # TAB 4 — Fees (with effective_from)
    # ==================================================================
    ws_fees = wb.create_sheet("Fees")
    fee_headers = [
        "program_name",
        "effective_from",
        "fee_name",
        "domestic_amount",
        "international_amount",
        "is_tuition",
        "sort_order",
    ]
    for ci, h in enumerate(fee_headers, 1):
        ws_fees.cell(row=1, column=ci, value=h)

    for ri, fee in enumerate(fees_raw, 2):
        ws_fees.cell(row=ri, column=1, value=fee.get("program_name", ""))
        ws_fees.cell(row=ri, column=2, value="2026-01-01")  # effective_from default
        ws_fees.cell(row=ri, column=3, value=fee.get("fee_name", ""))

        # domestic_amount
        da = fee.get("domestic_amount", "")
        try:
            da = float(da)
            da = int(da) if da == int(da) else da
        except (ValueError, TypeError):
            pass
        ws_fees.cell(row=ri, column=4, value=da)

        # international_amount
        ia = fee.get("international_amount", "")
        try:
            ia = float(ia)
            ia = int(ia) if ia == int(ia) else ia
        except (ValueError, TypeError):
            pass
        ws_fees.cell(row=ri, column=5, value=ia)

        ws_fees.cell(row=ri, column=6, value=fee.get("is_tuition", "FALSE"))

        so = fee.get("sort_order", "")
        try:
            so = int(so)
        except (ValueError, TypeError):
            pass
        ws_fees.cell(row=ri, column=7, value=so)

    style_header(ws_fees, len(fee_headers))
    auto_width(ws_fees)

    max_fee_row = 500

    # --- Fees validations ---
    # program_name dropdown
    dv_fee_prog = make_ref_validation("=Programs!$A$2:$A$200")
    dv_fee_prog.add(col_range("A", 2, max_fee_row))
    ws_fees.add_data_validation(dv_fee_prog)

    # effective_from date
    dv_eff_date = make_date_validation(allow_blank=False)
    dv_eff_date.add(col_range("B", 2, max_fee_row))
    ws_fees.add_data_validation(dv_eff_date)

    # fee_name dropdown
    dv_fee_name = make_list_validation(FEE_NAMES, allow_blank=False)
    dv_fee_name.add(col_range("C", 2, max_fee_row))
    ws_fees.add_data_validation(dv_fee_name)

    # domestic_amount — allow negatives for scholarships
    dv_dom_amt = make_decimal_validation(min_val=-999999, max_val=999999)
    dv_dom_amt.add(col_range("D", 2, max_fee_row))
    ws_fees.add_data_validation(dv_dom_amt)

    # international_amount
    dv_intl_amt = make_decimal_validation(min_val=-999999, max_val=999999)
    dv_intl_amt.add(col_range("E", 2, max_fee_row))
    ws_fees.add_data_validation(dv_intl_amt)

    # is_tuition TRUE/FALSE dropdown
    dv_is_tuition = make_list_validation(IS_TUITION_OPTIONS, allow_blank=False)
    dv_is_tuition.add(col_range("F", 2, max_fee_row))
    ws_fees.add_data_validation(dv_is_tuition)

    # sort_order — whole >= 1
    dv_sort = make_whole_validation(min_val=1, max_val=999)
    dv_sort.add(col_range("G", 2, max_fee_row))
    ws_fees.add_data_validation(dv_sort)

    # --- Fees conditional formatting ---
    # Blank required: program_name (A), fee_name (C)
    ws_fees.conditional_formatting.add(
        col_range("A", 2, max_fee_row),
        FormulaRule(formula=['ISBLANK(A2)'], fill=RED_FILL),
    )
    ws_fees.conditional_formatting.add(
        col_range("C", 2, max_fee_row),
        FormulaRule(formula=['ISBLANK(C2)'], fill=RED_FILL),
    )

    # Yellow on $0 domestic_amount (review if intentional)
    ws_fees.conditional_formatting.add(
        col_range("D", 2, max_fee_row),
        CellIsRule(operator="equal", formula=["0"], fill=YELLOW_FILL),
    )
    # Yellow on $0 international_amount
    ws_fees.conditional_formatting.add(
        col_range("E", 2, max_fee_row),
        CellIsRule(operator="equal", formula=["0"], fill=YELLOW_FILL),
    )

    # Light blue on Scholarship rows — negative domestic_amount
    ws_fees.conditional_formatting.add(
        f"A2:G{max_fee_row}",
        FormulaRule(formula=['$D2<0'], fill=LIGHT_BLUE_FILL),
    )
    # Light blue on fee_name = "Scholarship"
    ws_fees.conditional_formatting.add(
        f"A2:G{max_fee_row}",
        FormulaRule(formula=['$C2="Scholarship"'], fill=LIGHT_BLUE_FILL),
    )

    # ==================================================================
    # TAB 5 — Outline Map
    # ==================================================================
    ws_outline = wb.create_sheet("Outline Map")
    outline_headers = ["program_name", "outline_filename"]
    for ci, h in enumerate(outline_headers, 1):
        ws_outline.cell(row=1, column=ci, value=h)

    for ri, row in enumerate(outlines_raw, 2):
        ws_outline.cell(row=ri, column=1, value=row.get("program_name", ""))
        ws_outline.cell(row=ri, column=2, value=row.get("outline_filename", ""))

    style_header(ws_outline, len(outline_headers))
    auto_width(ws_outline)

    # program_name dropdown
    dv_outline_prog = make_ref_validation("=Programs!$A$2:$A$200")
    dv_outline_prog.add(col_range("A", 2, 200))
    ws_outline.add_data_validation(dv_outline_prog)

    # Blank program_name highlight
    ws_outline.conditional_formatting.add(
        col_range("A", 2, 200),
        FormulaRule(formula=['ISBLANK(A2)'], fill=RED_FILL),
    )

    # ==================================================================
    # Save
    # ==================================================================
    outpath = DATA_DIR / "WCC_Contract_Data.xlsx"
    wb.save(outpath)

    # --- Report ---
    prog_count = ws_prog.max_row - 1
    intake_count = ws_intakes.max_row - 1
    fee_count = ws_fees.max_row - 1
    outline_count = ws_outline.max_row - 1

    print(f"\nSaved: {outpath}")
    print(f"  Instructions: info tab (green)")
    print(f"  Programs:     {prog_count} rows")
    print(f"  Intakes:      {intake_count} rows")
    print(f"  Fees:         {fee_count} rows")
    print(f"  Outline Map:  {outline_count} rows")
    print(f"\nTotal data validations applied:")
    print(f"  Programs:     {len(ws_prog.data_validations.dataValidation)} rules")
    print(f"  Intakes:      {len(ws_intakes.data_validations.dataValidation)} rules")
    print(f"  Fees:         {len(ws_fees.data_validations.dataValidation)} rules")
    print(f"  Outline Map:  {len(ws_outline.data_validations.dataValidation)} rules")


if __name__ == "__main__":
    main()
