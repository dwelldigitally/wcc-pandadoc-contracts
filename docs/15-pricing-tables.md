# PandaDoc Pricing Tables

## Overview

Interactive, calculable tables for line items, fees, costs, discounts, and taxes. Ideal for tuition/fee breakdowns.

## Adding a Pricing Table

1. Drag **Pricing Table** block from Content tab
2. Type in **Name** column — auto-suggest from Product Catalog
3. Or click **+Products** to browse catalog
4. Or right-click > **Insert from catalog**

## Default Columns

| Column | Description |
|--------|-------------|
| **Name** | Product/service name |
| **Description** | Details |
| **QTY** | Quantity |
| **Price** | Unit price |
| **Subtotal** | Auto-calculated (QTY × Price) |

## Customizing Columns

| Action | How |
|--------|-----|
| **Add column** | Click **+** on right side, or right-click > Add column |
| **Hide column** | Click cell > arrow in upper-right > **Hide column** (still calculates) |
| **Multiplier column** | Custom multiplier (e.g., Price × QTY × Duration) |
| **Plain text column** | For non-calculated data |

## Sections

Group line items into categories:
1. Click the pricing table
2. Click **+ Section** at bottom-left
3. Name it (e.g., "Registration Fees", "Materials", "Monthly Recurring")
4. Each section gets its own subtotal

## Discounts & Taxes

| Feature | How |
|---------|-----|
| **Line-item discount** | Click **+** or right-click > **Discount**. Flat or percentage |
| **Tax** | Add tax rates (percentage). Apply to items or whole table |
| **Subtotals** | Auto-calculated per section and overall |

## Recipient Interaction

- Recipients can select optional line items (if configured)
- `[Document.Value]` displays total anywhere in document body

---

## Enrollment Fee Structure Examples

### Approach 1: Sections Within One Table

```
ENROLLMENT FEES
┌─────────────────────────────────┬──────┬──────────┬──────────┐
│ Name                            │ QTY  │ Price    │ Subtotal │
├─────────────────────────────────┼──────┼──────────┼──────────┤
│ ── One-Time Fees ──             │      │          │          │
│ Registration Fee                │ 1    │ $150.00  │ $150.00  │
│ Enrollment Deposit              │ 1    │ $500.00  │ $500.00  │
│ Materials & Books               │ 1    │ $350.00  │ $350.00  │
│                      Section Sub│total │          │$1,000.00 │
├─────────────────────────────────┼──────┼──────────┼──────────┤
│ ── Recurring Fees (Monthly) ──  │      │          │          │
│ Tuition                         │ 12   │$1,250.00 │$15,000.00│
│ Activity Fee                    │ 12   │  $50.00  │  $600.00 │
│ Technology Fee                  │ 12   │  $25.00  │  $300.00 │
│                      Section Sub│total │          │$15,900.00│
├─────────────────────────────────┼──────┼──────────┼──────────┤
│                           TOTAL │      │          │$16,900.00│
└─────────────────────────────────┴──────┴──────────┴──────────┘
```

### Approach 2: Separate Tables

**Table 1 — One-Time Fees**
- Registration, deposit, materials

**Table 2 — Recurring Fees**
- Monthly tuition, meal plan, activity fees

### Approach 3: With Discounts

```
Tuition (12 months)          $15,000.00
  Scholarship Discount (20%)  -$3,000.00
                              $12,000.00
```
