"""
Shared fee matching module.

Used by both backend-server.py and generate-contract-v2.py to ensure
identical fee resolution logic.

Schema: column-based fees (v3)
  Each row has: program_name, effective_from, residency, then one column
  per fee type (Application Fee, Tuition Fee, Scholarship, etc.).
  Non-key columns with non-zero numeric values are fee line items.

Fee matching rule:
  Given a program_name, residency tier, and reference_date, find the row
  where effective_from <= reference_date with the most recent effective_from.
  When reference_date is empty, fall back to the most recent row.
"""

from __future__ import annotations

from datetime import datetime

DOMESTIC_STATUSES = ["canadian citizen", "permanent resident", "refugee", "citizen/pr"]

# Columns in the Fees tab that are keys, not fee amounts
FEE_KEY_COLUMNS = {"program_name", "effective_from", "residency", "total"}


def is_domestic(status: str | None) -> bool | None:
    if not status:
        return None
    return status.lower().strip() in DOMESTIC_STATUSES


def parse_date(date_str: str | None):
    """Parse a YYYY-MM-DD string to a date object. Returns None on failure."""
    if not date_str or not isinstance(date_str, str):
        return None
    date_str = date_str.strip()
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None


def match_fees(
    all_fees: list[dict],
    program_name: str,
    reference_date_str: str,
    residency_tier: str = "",
) -> tuple[list[dict], str]:
    """Match fees for a program + residency using effective_from date logic.

    Args:
        all_fees: list of fee row dicts from the column-based Fees tab.
            Keys include program_name, effective_from, residency, plus
            dynamic fee-type columns (Application Fee, Tuition Fee, etc.)
        program_name: the program to match (case-insensitive)
        reference_date_str: YYYY-MM-DD string (typically intake_date or today).
            When empty, returns the most recent fee row (no date filter).
        residency_tier: "domestic" or "international" (case-insensitive).
            When empty, no residency filter is applied.

    Returns:
        (matched_row_list, effective_from_date_str)
        - matched_row_list: list containing the single matched fee row, or empty
        - effective_from_date_str: the matched effective_from date string, or ""
    """
    if not program_name or not all_fees:
        return [], ""

    program_lower = program_name.lower().strip()
    residency_lower = residency_tier.lower().strip() if residency_tier else ""
    has_reference_date = bool(reference_date_str and reference_date_str.strip())
    reference_date = parse_date(reference_date_str) if has_reference_date else None

    # If a reference date was provided but couldn't be parsed, fail
    if has_reference_date and reference_date is None:
        return [], ""

    # Step 1: Filter by program name + residency
    candidates = []
    for f in all_fees:
        if f.get("program_name", "").lower().strip() != program_lower:
            continue
        if residency_lower and f.get("residency", "").lower().strip() != residency_lower:
            continue

        eff_date = parse_date(f.get("effective_from", ""))
        if eff_date is None:
            continue

        # Step 2: Filter by effective_from <= reference_date (skip if no date)
        if reference_date is not None and eff_date > reference_date:
            continue

        candidates.append((eff_date, f))

    if not candidates:
        return [], ""

    # Step 3: Pick the row with the most recent effective_from
    max_eff_date = max(eff_date for eff_date, _ in candidates)
    matched = [f for eff_date, f in candidates if eff_date == max_eff_date]

    effective_from_str = max_eff_date.strftime("%Y-%m-%d")
    return matched, effective_from_str


def resolve_fee_amounts(
    fee_rows: list[dict],
    is_domestic_student: bool | None = None,
) -> tuple[list[dict], float]:
    """Extract fee line items from a column-based fee row.

    In the v3 schema, each fee type is a column. Any column that isn't a key
    column and has a non-zero numeric value becomes a fee line item.

    Args:
        fee_rows: list of matched fee row dicts (typically 1 row)
        is_domestic_student: ignored in v3 (residency is already filtered
            by match_fees), kept for backward compatibility

    Returns:
        (fee_items, total)
        - fee_items: list of {name, amount, isTuition} dicts
        - total: sum of all amounts (float)
    """
    if not fee_rows:
        return [], 0.0

    # Use the first (most recent) matched row
    row = fee_rows[0]

    fee_items = []
    total = 0.0

    for column, value in row.items():
        if column.lower() in FEE_KEY_COLUMNS:
            continue

        # Parse numeric value
        cleaned = str(value).replace("$", "").replace(",", "").strip()
        if not cleaned:
            continue
        try:
            amount = float(cleaned)
        except (ValueError, TypeError):
            continue
        if amount == 0:
            continue

        is_tuition = column.lower() in ("tuition fee", "tuition fee per credit")

        fee_items.append({
            "name": column,
            "amount": amount,
            "isTuition": is_tuition,
        })
        total += amount

    return fee_items, round(total, 2)
