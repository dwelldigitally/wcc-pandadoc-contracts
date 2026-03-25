# PandaDoc Smart Content & Conditional Logic

## Smart Content Block — Pre-Selected Content

Lets you **pre-define a set of content library items** that document creators choose from. Restricts ad-hoc editing and ensures only approved content is used.

### Setup
1. Drag a **Smart Content** block into template
2. Link to specific Content Library items
3. When creating a document, user selects from pre-approved options

---

## Conditional Content (Enterprise Plan)

**Automatically** populates content library items based on variable values or pricing table data.

### Configuration

1. Add a Smart Content block to template
2. In the **"If"** section, set condition:
   - Choose variable (custom, system, pricing table, or CRM)
   - Select operator: **equal**, **not equal**, **empty**, **not empty**, **contains**, **does not contain**
   - Specify value to match
3. In the **"Then"** section:
   - Select Content Library items to insert (up to **10 items per condition**)
4. Set **default behavior** (if no conditions match):
   - **Hide the block** on sending, OR
   - Insert **default content library items**

### Operators Available

| Operator | Use Case |
|----------|----------|
| `equal` | Exact match: `[Program.Type]` equal "Full-Time" |
| `not equal` | Exclude: `[Program.Type]` not equal "Online" |
| `empty` | Field not filled |
| `not empty` | Field has any value |
| `contains` | Partial match: `[Program.Name]` contains "Nursing" |
| `does not contain` | Exclude partial: `[Program.Name]` does not contain "Certificate" |

---

## Enrollment Use Cases

### Program-Specific Terms
```
IF [Program.Type] equals "Full-Time"
  THEN → Insert "Full-Time Enrollment Terms" + "Full-Time Fee Schedule"

IF [Program.Type] equals "Part-Time"
  THEN → Insert "Part-Time Enrollment Terms" + "Part-Time Fee Schedule"

DEFAULT → Hide block (or show generic terms)
```

### Campus-Specific Clauses
```
IF [Program.Campus] equals "Main Campus"
  THEN → Insert "Main Campus Policies" + "Parking Agreement"

IF [Program.Campus] equals "Online"
  THEN → Insert "Online Learning Agreement" + "Technology Requirements"
```

### Financial Aid Conditional
```
IF [FinancialAid.Type] not empty
  THEN → Insert "Financial Aid Disclosure" + "Satisfactory Academic Progress Policy"

IF [FinancialAid.Type] empty
  THEN → Hide block
```

### Age-Based (Minor vs Adult)
```
IF [Student.Age] contains "Minor"
  THEN → Insert "Parental Consent Form" + "Minor Student Policies"

DEFAULT → Insert "Adult Student Acknowledgment"
```

---

## Conditional Fields

Fields that show/hide based on other field values:
- Example: Show additional address field only if "Different mailing address" checkbox is checked
- Configured in the field properties
