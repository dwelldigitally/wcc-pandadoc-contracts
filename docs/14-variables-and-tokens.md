# PandaDoc Variables & Tokens

## Variables vs Fields vs Tokens

| Concept | Purpose | Filled By | Syntax |
|---------|---------|-----------|--------|
| **Variables** | Auto-filled text placeholders | Document creator or API (before sending) | `[Variable.Name]` |
| **Fields** | Interactive elements | Recipient (during signing) | Drag-and-drop in editor |
| **Tokens** | API-only text replacement | API at document creation | `tokens` array in API payload |

---

## Variables

### Syntax
```
[Variable.Name]
```

### Examples
- `[Student.Name]`
- `[Student.DOB]`
- `[Parent.Name]`
- `[Program.Name]`
- `[Start.Date]`
- `[Tuition.Amount]`
- `[Document.Value]` (system — pricing table total)

### Creating Custom Variables

**Method 1 — Inline:**
1. In any text block, type `[`
2. Type the variable name
3. Press **Enter** to create

**Method 2 — Variables Panel:**
1. Open **Variables** section on right sidebar
2. Click **+Add custom variable**
3. Enter name, click **Add variable**
4. Copy and paste into text blocks

### Where Variables Work
- Template/document body text ✅
- Document titles (with `detect_title_variables` via API) ✅
- Pricing table: Name, Description, Plain text columns ✅
- Inside fields (signature, checkbox, etc.) ❌

### System Variables (Auto-populated)
- `[Document.Value]` — Total from pricing tables
- Date variables
- Pricing table summaries (subtotal, tax, discount, total)
- CRM-synced variables (HubSpot, Salesforce)

### Populating Variables

**Manually:**
Click variable in document or open Variables list → enter value → populates everywhere

**Via API (Tokens):**
```json
{
  "tokens": [
    { "name": "Student.Name", "value": "Jane Smith" },
    { "name": "Program.Name", "value": "Nursing" },
    { "name": "Start.Date", "value": "September 2026" },
    { "name": "Tuition.Amount", "value": "$15,000" }
  ]
}
```

**Via CRM Integration:**
Variables mapped to CRM fields auto-populate from records.

---

## Enrollment Variables Checklist

### Student Information
| Variable | Description |
|----------|-------------|
| `[Student.FirstName]` | Student's first name |
| `[Student.LastName]` | Student's last name |
| `[Student.DOB]` | Date of birth |
| `[Student.Address]` | Mailing address |
| `[Student.Phone]` | Phone number |
| `[Student.Email]` | Email address |
| `[Student.ID]` | Student ID number |

### Parent/Guardian Information
| Variable | Description |
|----------|-------------|
| `[Parent.FirstName]` | Parent/guardian first name |
| `[Parent.LastName]` | Parent/guardian last name |
| `[Parent.Phone]` | Phone number |
| `[Parent.Email]` | Email address |
| `[Parent.Address]` | Mailing address |

### Program Information
| Variable | Description |
|----------|-------------|
| `[Program.Name]` | Program name |
| `[Program.Type]` | Full-Time / Part-Time |
| `[Program.Code]` | Internal program code |
| `[Program.StartDate]` | Program start date |
| `[Program.EndDate]` | Program end date |
| `[Program.Campus]` | Campus/location |

### Financial Information
| Variable | Description |
|----------|-------------|
| `[Tuition.Total]` | Total tuition amount |
| `[Tuition.Monthly]` | Monthly payment amount |
| `[Registration.Fee]` | Registration fee |
| `[Document.Value]` | System: pricing table total |
