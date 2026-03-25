"""
Shared fee matching module.

Used by both backend-server.py and generate-contract-v2.py to ensure
identical fee resolution logic.

Fee matching rule:
  Given a program_name and a reference_date (typically the intake start date),
  find all fee rows where effective_from <= reference_date, then pick the group
  with the most recent (maximum) effective_from date.
"""

from datetime import datetime


def parse_date(date_str):
    """Parse a YYYY-MM-DD string to a date object. Returns None on failure."""
    if not date_str or not isinstance(date_str, str):
        return None
    date_str = date_str.strip()
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None


def match_fees(all_fees, program_name, reference_date_str):
    """Match fees for a program using effective_from date logic.

    Args:
        all_fees: list of fee dicts with keys:
            program_name, effective_from, fee_name, domestic_amount,
            international_amount, is_tuition, sort_order
        program_name: the program to match (case-insensitive)
        reference_date_str: YYYY-MM-DD string (typically intake_date or today)

    Returns:
        (matched_fees, effective_from_date_str)
        - matched_fees: list of fee dicts sorted by sort_order, or empty list
        - effective_from_date_str: the matched effective_from date string, or ""
    """
    if not program_name or not all_fees:
        return [], ""

    reference_date = parse_date(reference_date_str)
    if reference_date is None:
        return [], ""

    program_lower = program_name.lower().strip()

    # Step 1: Filter by program name
    program_fees = [
        f for f in all_fees
        if f.get("program_name", "").lower().strip() == program_lower
    ]
    if not program_fees:
        return [], ""

    # Step 2: Filter to effective_from <= reference_date
    eligible = []
    for f in program_fees:
        eff_date = parse_date(f.get("effective_from", ""))
        if eff_date is not None and eff_date <= reference_date:
            eligible.append((eff_date, f))

    if not eligible:
        return [], ""

    # Step 3: Find the most recent effective_from date
    max_eff_date = max(eff_date for eff_date, _ in eligible)

    # Step 4: Select all fees from that group
    matched = [f for eff_date, f in eligible if eff_date == max_eff_date]

    # Step 5: Sort by sort_order
    def safe_sort(fee):
        try:
            return int(fee.get("sort_order", 0))
        except (ValueError, TypeError):
            return 0

    matched.sort(key=safe_sort)

    effective_from_str = max_eff_date.strftime("%Y-%m-%d")
    return matched, effective_from_str


def resolve_fee_amounts(fees, is_domestic):
    """Resolve the correct amount column and compute total.

    Args:
        fees: list of matched fee dicts
        is_domestic: True for domestic, False for international, None for unknown

    Returns:
        (fee_items, total)
        - fee_items: list of {name, amount, isTuition} dicts
        - total: sum of all amounts (float)
    """
    if is_domestic is None:
        amount_col = "domestic_amount"
    else:
        amount_col = "domestic_amount" if is_domestic else "international_amount"

    fee_items = []
    total = 0.0
    for f in fees:
        raw = f.get(amount_col, 0)
        try:
            amount = float(raw) if raw else 0.0
        except (ValueError, TypeError):
            amount = 0.0

        is_tuition = f.get("is_tuition", "FALSE").upper() == "TRUE"

        fee_items.append({
            "name": f.get("fee_name", ""),
            "amount": amount,
            "isTuition": is_tuition,
        })
        total += amount

    return fee_items, round(total, 2)
