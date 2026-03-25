# PandaDoc Content Library

## What Is It?

A centralized repository of reusable content blocks — clauses, sections, full pages, images, tables, templates — that can be dragged into any document or template. Eliminates repetitive drafting and ensures consistency.

## Types of Content You Can Store

- Individual blocks (text, image, table)
- Whole pages (entire page layout with multiple blocks)
- Full templates/documents (saved as library items)
- Legal clauses, disclaimers, terms & conditions
- Pricing table configurations
- Branded sections (headers, footers, cover pages)

## Creating Content Library Items

**Navigation:** Templates > Content Library > +Content Item

### Method 1 — From Scratch
1. Click **+Content item**
2. Use the Content Builder (same editor as templates) to design
3. Save

### Method 2 — From Existing Document/Template
1. Select a block, page, or full document
2. Choose "Save to Content Library"
3. Create new item or append to existing one

### Method 3 — Upload
Upload a file directly as a library item

## Organizing the Library

| Feature | Usage |
|---------|-------|
| **Tags** | Categorize items (e.g., "Legal", "Pricing", "Onboarding") |
| **Filters** | Filter by Date, Owner, Tags, Roles |
| **Featured** | Mark frequently used items for quick access |

## Inserting Library Items into Documents

1. Open document/template in editor
2. Click **Content Library icon** on right sidebar
3. Browse under **Recent** or **Featured** tab
4. **Drag and drop** into document (blue indicator shows placement)

## Update Behavior

- Library items CAN be updated after creation
- Changes apply to **future uses only**
- Existing documents that already used the item are **NOT retroactively changed**

## API: Content Placeholders

Templates can contain Content Placeholder blocks populated at document creation:

```json
{
  "content_placeholders": [
    {
      "block_id": "Content Placeholder 1",
      "content_library_items": [
        {
          "id": "content_library_item_id",
          "pricing_tables": [...],
          "fields": {
            "Date": { "value": "2019-12-31T00:00:00.000Z" }
          },
          "recipients": [...]
        }
      ]
    }
  ]
}
```

## Enrollment Library Items to Create

| Item | Tag | Description |
|------|-----|-------------|
| Enrollment Terms | Legal, Enrollment | Standard enrollment T&C |
| Refund Policy | Legal, Financial | Cancellation/refund clause |
| FERPA Release | Legal, Compliance | FERPA authorization |
| Financial Responsibility | Legal, Financial | Payment obligation clause |
| Program Description — Nursing | Program, Nursing | Program-specific details |
| Program Description — Business | Program, Business | Program-specific details |
| Fee Schedule — Full-Time | Financial, Full-Time | Full-time fee breakdown |
| Fee Schedule — Part-Time | Financial, Part-Time | Part-time fee breakdown |
| Signature Block | Signatures | Standard signature section |
| School Header | Branding | Logo + school info header |
