# WCC Contract Automation — Google Sheets Design

## Overview

One Google Sheet with 3 tabs. Institute staff edit this sheet freely.
The contract generation script reads it live each time a contract is created.

---

## Tab 1: Programs

One row per program. Contains program metadata + program outline content library IDs.

| Column | Example | Notes |
|--------|---------|-------|
| program_name | Health Care Assistant Diploma | Must match HubSpot `program_of_study` exactly |
| program_code | HCA | Short code for internal reference |
| category | Health Care | Program category |
| credential | Diploma | Diploma / Certificate / Post-Graduate Diploma / Bachelor |
| program_outline_id | H9TBoFAFWAgHUs3LcgVrvB | PandaDoc Content Library item ID |
| active | TRUE | Set FALSE to disable a program |

Note: hours, weeks, and delivery method are now on the **Intakes** tab (per-cohort).

---

## Tab 2: Fees

One row per program + intake + residency tier. Each fee type is a **column**.
Only columns with a non-empty numeric value are included on the contract.

### Key columns (required)

| Column | Example | Notes |
|--------|---------|-------|
| program_name | Health Care Assistant Diploma | Must match Tab 1 exactly |
| intake_date | 2026-05-05 | Must match Tab 3 exactly (YYYY-MM-DD) |
| residency | domestic | `domestic` or `international` |

### Fee type columns (all optional — leave blank if N/A)

Each column header is the **display name** that appears on the contract.
The script dynamically reads ALL columns that aren't key columns — so Finance
can add new fee type columns without any code changes.

| Column Header | Example Value | Notes |
|---------------|---------------|-------|
| Application Fee | 250 | Number only, no $ sign |
| Tuition Fee | 7000 | Main tuition |
| Course Materials | 75 | Supplies, materials |
| Books | 175 | Textbooks |
| Book Fee | | Additional book fee (some programs) |
| Annual Technology Fee | | Tech fee (some programs) |
| Ground School Fee | | Aviation programs |
| Flight Dual | | Aviation dual instruction hours |
| Flight Solo | | Aviation solo hours |
| Flight Time Building | | Aviation time building hours |
| Flight Prep Ground | | Aviation PGI/GB |
| Fuel | | Aviation fuel |
| Scholarship | -2000 | **Always negative.** Reduces total. |
| Total | =SUM(...) | **Excel formula** — not read by script |

### Rules

1. **Scholarship is always negative** — Excel data validation enforces `<= 0`
2. **Total column** is an Excel `=SUM()` formula — the script ignores it
3. **Empty = not applicable** — only non-zero numeric cells become fee line items
4. **Two rows per program+intake** — one `domestic`, one `international`
5. **Column order = display order** on the contract (left to right)
6. **Adding a new fee type** — just add a new column. Script picks it up automatically.

### Example rows for HCA (May 2026 intake):

| program_name | intake_date | residency | Application Fee | Tuition Fee | Course Materials | Books | Scholarship | Total |
|---|---|---|---|---|---|---|---|---|
| Health Care Assistant Diploma | 2026-05-05 | domestic | 250 | 7000 | 75 | 175 | | 7500 |
| Health Care Assistant Diploma | 2026-05-05 | international | 250 | 9000 | 75 | 175 | -2000 | 7500 |

### Example rows for Aviation PPL:

| program_name | intake_date | residency | Application Fee | Ground School Fee | Flight Dual | Flight Solo | Flight Prep Ground | Course Materials | Fuel | Books | Scholarship | Total |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Aviation PPL Diploma | 2026-06-01 | domestic | 250 | 500 | 8700 | 3375 | 1050 | 750 | 2250 | 175 | | 17050 |

---

## Tab 3: Intakes

One row per intake date per program. Each intake carries its own hours, weeks,
and delivery method (these vary per cohort, not per program).

| Column | Example | Notes |
|--------|---------|-------|
| program_name | Health Care Assistant Diploma | Must match Tab 1 exactly |
| intake_date | 2026-05-05 | Start date (YYYY-MM-DD) |
| end_date | 2026-10-30 | End date (YYYY-MM-DD) |
| campus | Surrey - Scott Road | Campus location |
| schedule | Full-Time | Full-Time or Part-Time |
| hours | 775 | Total program hours for this cohort |
| weeks | 26 | Duration in weeks for this cohort |
| domestic_delivery | In-class | Delivery method for domestic students |
| international_delivery | Distance-Synchronous | Delivery method for international students |
| spots_available | 5 | Optional: remaining spots |
| status | Open | Open / Closed / Waitlist |

### How contract dates work:
- Script reads the NEXT upcoming Open intake for the student's program
- Or advisor can override by selecting a specific intake from HubSpot
- Contract start date = intake_date, end date = end_date from this tab

---

## How the script uses these tabs

```
1. Student's deal in HubSpot has:
   - program_of_study = "Health Care Assistant Diploma"
   - residence_status = "Canadian Citizen" (→ domestic)

2. Script reads Tab 1 (Programs):
   → credential=Diploma, outline_id=H9TBoFAFWAgHUs3LcgVrvB

3. Script reads Tab 3 (Intakes), finds next open intake:
   → intake_date=2026-05-05, end_date=2026-10-30, campus=Surrey
   → hours=775, weeks=26, domestic_delivery=In-class

4. Script reads Tab 2 (Fees), finds row matching:
   program_name + intake_date + residency="domestic"
   → Reads ALL non-empty fee columns (Application Fee=250, Tuition Fee=7000, ...)
   → Each non-zero column becomes a fee line item on the contract
   → Scholarship column (if present) appears as a negative line item
   → Script does NOT compute totals — Excel's Total column is for admin reference only

5. Script calls PandaDoc API with everything populated
```

---

## Who edits what

| Person | What they edit | Tab |
|--------|---------------|-----|
| Registrar / Admin | Add new programs, update hours/weeks | Programs |
| Finance | Update fee amounts, add/remove fee items | Fees |
| Admissions Manager | Add new intakes, close filled intakes | Intakes |
| Advisors | Nothing — they just use HubSpot as usual | — |
