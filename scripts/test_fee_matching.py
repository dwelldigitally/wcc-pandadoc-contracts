"""Unit tests for fee_matching.py"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from fee_matching import match_fees, resolve_fee_amounts

# Test data
FEES = [
    # HCA - effective 2026-01-01
    {"program_name": "Health Care Assistant Diploma", "effective_from": "2026-01-01", "fee_name": "Application Fee", "domestic_amount": "250", "international_amount": "250", "is_tuition": "FALSE", "sort_order": "1"},
    {"program_name": "Health Care Assistant Diploma", "effective_from": "2026-01-01", "fee_name": "Tuition Fee", "domestic_amount": "7000", "international_amount": "9000", "is_tuition": "TRUE", "sort_order": "2"},
    {"program_name": "Health Care Assistant Diploma", "effective_from": "2026-01-01", "fee_name": "Books", "domestic_amount": "175", "international_amount": "175", "is_tuition": "FALSE", "sort_order": "3"},
    # HCA - effective 2026-09-01 (fee increase)
    {"program_name": "Health Care Assistant Diploma", "effective_from": "2026-09-01", "fee_name": "Application Fee", "domestic_amount": "250", "international_amount": "250", "is_tuition": "FALSE", "sort_order": "1"},
    {"program_name": "Health Care Assistant Diploma", "effective_from": "2026-09-01", "fee_name": "Tuition Fee", "domestic_amount": "7500", "international_amount": "9500", "is_tuition": "TRUE", "sort_order": "2"},
    {"program_name": "Health Care Assistant Diploma", "effective_from": "2026-09-01", "fee_name": "Books", "domestic_amount": "175", "international_amount": "175", "is_tuition": "FALSE", "sort_order": "3"},
    {"program_name": "Health Care Assistant Diploma", "effective_from": "2026-09-01", "fee_name": "Scholarship", "domestic_amount": "-500", "international_amount": "-500", "is_tuition": "FALSE", "sort_order": "4"},
    # Future-only program
    {"program_name": "Future Program", "effective_from": "2027-06-01", "fee_name": "Tuition Fee", "domestic_amount": "5000", "international_amount": "8000", "is_tuition": "TRUE", "sort_order": "1"},
    # Another program
    {"program_name": "Accounting Diploma", "effective_from": "2026-01-01", "fee_name": "Tuition Fee", "domestic_amount": "8490", "international_amount": "11700", "is_tuition": "TRUE", "sort_order": "1"},
]

passed = 0
failed = 0

def test(name, actual, expected):
    global passed, failed
    if actual == expected:
        passed += 1
        print(f"  PASS: {name}")
    else:
        failed += 1
        print(f"  FAIL: {name}")
        print(f"    Expected: {expected}")
        print(f"    Actual:   {actual}")


print("=== Fee Matching Tests ===\n")

# Test 1: Basic match — single group, intake after effective_from
fees, eff = match_fees(FEES, "Health Care Assistant Diploma", "2026-04-14")
test("Basic match returns 3 items (Jan group)", len(fees), 3)
test("Basic match effective_from", eff, "2026-01-01")
test("Basic match first item is Application Fee", fees[0]["fee_name"], "Application Fee")

# Test 2: Multiple groups — picks most recent <= intake_date
fees, eff = match_fees(FEES, "Health Care Assistant Diploma", "2026-10-01")
test("Multiple groups picks Sep group", eff, "2026-09-01")
test("Sep group has 4 items (incl scholarship)", len(fees), 4)
test("Sep group tuition is 7500", fees[1]["domestic_amount"], "7500")

# Test 3: Boundary — intake_date equals effective_from exactly
fees, eff = match_fees(FEES, "Health Care Assistant Diploma", "2026-09-01")
test("Boundary: intake == effective_from matches", eff, "2026-09-01")
test("Boundary: returns Sep group", len(fees), 4)

# Test 4: Before any effective_from — Aug intake picks Jan group
fees, eff = match_fees(FEES, "Health Care Assistant Diploma", "2026-08-31")
test("Aug intake picks Jan group", eff, "2026-01-01")
test("Jan group has 3 items", len(fees), 3)

# Test 5: Future fees only — no match
fees, eff = match_fees(FEES, "Future Program", "2026-12-01")
test("Future-only: no match", len(fees), 0)
test("Future-only: empty effective_from", eff, "")

# Test 6: Program not found
fees, eff = match_fees(FEES, "Nonexistent Program", "2026-04-14")
test("Program not found: empty", len(fees), 0)

# Test 7: Case insensitive matching
fees, eff = match_fees(FEES, "health care assistant diploma", "2026-04-14")
test("Case insensitive match", len(fees), 3)

# Test 8: Empty inputs
fees, eff = match_fees([], "HCA", "2026-04-14")
test("Empty fees list", len(fees), 0)
fees, eff = match_fees(FEES, "", "2026-04-14")
test("Empty program name", len(fees), 0)
fees, eff = match_fees(FEES, "HCA", "")
test("Empty date", len(fees), 0)

# Test 9: Invalid date
fees, eff = match_fees(FEES, "Health Care Assistant Diploma", "not-a-date")
test("Invalid date returns empty", len(fees), 0)

# Test 10: resolve_fee_amounts — domestic
print("\n=== resolve_fee_amounts Tests ===\n")

fees, _ = match_fees(FEES, "Health Care Assistant Diploma", "2026-04-14")
items, total = resolve_fee_amounts(fees, True)
test("Domestic total for Jan group", total, 7425.0)
test("Domestic items count", len(items), 3)
test("Tuition item isTuition flag", items[1]["isTuition"], True)
test("Application Fee isTuition flag", items[0]["isTuition"], False)

# Test 11: resolve_fee_amounts — international
items, total = resolve_fee_amounts(fees, False)
test("International total for Jan group", total, 9425.0)
test("International tuition amount", items[1]["amount"], 9000.0)

# Test 12: Scholarship handling (negative amounts)
fees, _ = match_fees(FEES, "Health Care Assistant Diploma", "2026-10-01")
items, total = resolve_fee_amounts(fees, True)
test("Sep domestic total (with -500 scholarship)", total, 7425.0)
scholarship = [i for i in items if i["name"] == "Scholarship"]
test("Scholarship item exists", len(scholarship), 1)
test("Scholarship amount is negative", scholarship[0]["amount"], -500.0)

# Test 13: Unknown residency (domestic=None)
fees, _ = match_fees(FEES, "Health Care Assistant Diploma", "2026-04-14")
items, total = resolve_fee_amounts(fees, None)
test("Unknown residency defaults to domestic amounts", total, 7425.0)

# Summary
print(f"\n{'=' * 40}")
print(f"Results: {passed} passed, {failed} failed")
if failed == 0:
    print("ALL TESTS PASSED")
else:
    print("SOME TESTS FAILED")
    sys.exit(1)
