# PandaDoc Template Builder

## Overview

Drag-and-drop WYSIWYG builder. Templates are reusable starting points with structure, branding, fields, and roles.

**Navigation:** Templates > +Template (or open existing)

---

## Content Blocks

Drag from the **Content** tab on the right sidebar:

| Block Type | Description |
|------------|-------------|
| **Text Block** | Rich text: headings (H1-H4), lists, links, formatting |
| **Image Block** | GIF, JPG, PNG. Resizable, left/right/center alignment |
| **Table Block** | Standard data tables (not pricing) |
| **Pricing Table** | Line items, fees, discounts, taxes, subtotals |
| **Table of Contents** | Auto-generated from headings, clickable links |
| **Smart Content Block** | Pre-selected or conditional content from Content Library |
| **Quote Builder Block** | Interactive quote config (Admin/Manager/Owner only) |
| **Page Break** | Forces a visual page break |

### Block Properties
- **Min-height** — configurable
- **Block spacing** — margins/padding
- Access via: floating toolbar > Properties button > Properties tab
- Grid-like alignment system

---

## Fields (Interactive Elements for Recipients)

Drag from the **Fields** tab, assign to roles:

| Field Type | Behavior |
|------------|----------|
| **Signature** | Required by default (can be optional). Digital signature capture |
| **Initials** | Can go in headers/footers to appear on every page |
| **Text Field** | Multiline by default (toggleable). Free-form text entry |
| **Date** | Configurable format and available date range |
| **Checkbox** | Multiple checkboxes for multi-select |
| **Dropdown** | Single-select from predefined options |

### Field Tags for Uploaded PDFs
```
{signature______}
{textfield*________}
{date____}
{checkbox*}
{initials___}
```

---

## Design & Branding

**Navigation:** Click **Design** on right panel

| Element | Options |
|---------|---------|
| **Text styles** | Font family, size, color for body |
| **Heading styles** | Customize H1-H4 |
| **Table styles** | Borders, backgrounds, alignment |
| **Page Background** | Color or image |
| **Header & Footer** | Logos, page numbers, contact details (Blank page type only) |
| **Themes** | Reusable brand themes — apply across all templates |

---

## Roles

### What Are Roles?
Placeholders representing future recipients. Pre-assign fields before knowing actual signers.

### Creating Roles
**Navigation:** Top right of editor > **+Add roles** (or **Manage**)

1. Click **+Add roles**
2. Type role name (e.g., "Student", "Parent/Guardian", "Administrator")
3. Click **Add**

### Assigning Fields to Roles
1. Select a role from dropdown on right sidebar
2. Drag fields onto document — auto-assign to selected role
3. Or: drag field first, then assign via field properties

**Color coding:** Each role gets a unique color. All fields for that role display in that color.

### Recipient Types

| Type | Signs? | Fills Fields? | Notes |
|------|--------|--------------|-------|
| **Signer** | Yes | Yes | Primary type. Draft status only |
| **CC** | No | No | Receives copy. Draft/Sent/Completed |
| **Approver** | No | No | Internal only. Pre-send approval |

### Signing Order
Drag recipients into sequence. Recipient 2 receives doc only after Recipient 1 completes.

---

## Recommended Template Structure for Enrollment

```
1. Header/Cover
   └── School logo, document title (via theme)

2. Student & Parent Information
   └── Variables: [Student.Name], [Student.DOB], [Parent.Name],
       [Parent.Email], [Parent.Phone]

3. Program Details
   └── Smart Content block → Content Library by [Program.Type]

4. Tuition & Fee Schedule
   └── Pricing table with sections:
       - One-time fees (registration, materials, enrollment deposit)
       - Recurring fees (monthly tuition, meal plan, activities)

5. Terms & Conditions
   └── Content Library item (legal-approved, version-controlled)

6. Cancellation/Refund Policy
   └── Content Library item (conditional by program type)

7. Acknowledgments
   └── Checkbox fields assigned to Parent/Guardian role

8. Signature Block
   └── Signature + Date fields for each role

9. Footer
   └── School contact info, page numbers
```
