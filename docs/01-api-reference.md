# PandaDoc API Reference

## Base URL
```
https://api.pandadoc.com
```

## Authentication

Two methods supported:

### API Key
```
Authorization: API-Key YOUR_API_KEY
Content-Type: application/json
```

### OAuth2
```
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json
```

### Node SDK Setup
```typescript
import * as pd_api from 'pandadoc-node-client';

const configuration = pd_api.createConfiguration({
  authMethods: { apiKey: `API-Key ${API_KEY}` }
});
const apiInstance = new pd_api.DocumentsApi(configuration);
```

---

## Documents API

### Create Document from Template
`POST /public/v1/documents`

**Minimum payload:**
```json
{
  "name": "My document",
  "template_uuid": "ustHNnVaPCD6MzuoNBbZ8L",
  "recipients": [{ "email": "nobody@example.com" }]
}
```

**Full payload options:**
| Field | Type | Description |
|-------|------|-------------|
| `template_uuid` | string | **Required.** Template ID |
| `name` | string | **Required.** Document name |
| `folder_uuid` | string | Target folder |
| `owner` | object | `email` or `membership_id` |
| `recipients` | array | Email, name, role, signing_order, delivery_methods (email/sms), redirect config |
| `tokens` | array | Name/value pairs for token replacement |
| `fields` | object | Pre-fill merge fields (text, boolean, date RFC 3339) |
| `images` | array | Upload images into image blocks by name and URL |
| `pricing_tables` | array | Pricing table config with sections, rows, discounts, currency |
| `texts` | array | Rich text/markdown for text blocks |
| `tags` | array | String tags |
| `metadata` | object | Custom metadata |
| `content_placeholders` | array | Content Library items to insert |
| `detect_title_variables` | boolean | Detect variables in document title |

**Response:** Returns `id`, `status` (`"document.uploaded"`), `date_created`, `date_modified`.

> **Note:** Document creation is **asynchronous** — may take a few seconds to become fully available.

### List Documents
`GET /public/v1/documents`

### Get Document Status
`GET /public/v1/documents/{id}`

### Get Document Details
`GET /public/v1/documents/{id}/details`

### Update Document (Draft Only)
`PATCH /public/v1/documents/{id}`

### Delete Document
`DELETE /public/v1/documents/{id}`

### Change Document Status
`PATCH /public/v1/documents/{id}/status`

### Send Document for Signature
`POST /public/v1/documents/{id}/send`

```json
{
  "message": "Hello! Please review and sign.",
  "subject": "Document for your signature",
  "silent": true,
  "forwarding_settings": {
    "forwarding_allowed": true,
    "forwarding_with_reassigning_allowed": true
  }
}
```

### Create Shareable Document Link
`POST /public/v1/documents/{id}/session`

```json
{
  "recipient": "josh@example.com",
  "lifetime": 900
}
```

### Download Document
`GET /public/v1/documents/{id}/download`

### Download Protected Document
`GET /public/v1/documents/{id}/download-protected`

### Move to Folder
`POST /public/v1/documents/{id}/move-to-folder/{folder_id}`

### Transfer Document Ownership
`PATCH /public/v1/documents/{id}/ownership`

### Transfer All Documents Ownership
`PATCH /public/v1/documents/ownership`

---

## Linked Objects

### Create Linked Object
`POST /public/v1/documents/{id}/linked-objects`

### List Linked Objects
`GET /public/v1/documents/{id}/linked-objects`

### Delete Linked Object
`DELETE /public/v1/documents/{id}/linked-objects/{linked_object_id}`

---

## Content Library / Content Placeholders

Templates can contain **Content Placeholder blocks** populated at document creation with library items.

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

Each content library item supports:
- `id` — The content library item ID
- `pricing_tables` — Pricing config specific to that item
- `fields` — Field pre-fills within that item
- `recipients` — Recipients scoped to that item

---

## Fields

Pre-fill fields via the `fields` object:

```json
{
  "fields": {
    "CustomerName": { "value": "John Doe" },
    "AgreeToTerms": { "value": true },
    "DeliveryDate": { "value": "2019-12-31T00:00:00.000Z" }
  }
}
```

**Supported types:**
- Text → string
- Checkbox → boolean
- Dropdown → string
- Date → RFC 3339 format

> **Signature fields CANNOT be pre-filled.**

Fields can be assigned to specific recipient roles using the `role` property.

---

## Recipients Configuration

```json
{
  "recipients": [
    {
      "email": "student@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "role": "Student",
      "signing_order": 1,
      "delivery_methods": { "email": true, "sms": false },
      "redirect": {
        "url": "https://example.com/thank-you",
        "is_active": true
      }
    }
  ]
}
```

---

## Tokens

Name/value pairs for simple text replacement in templates:

```json
{
  "tokens": [
    { "name": "Student.Name", "value": "Jane Smith" },
    { "name": "Program.Name", "value": "Nursing" },
    { "name": "Start.Date", "value": "September 2026" }
  ]
}
```

---

## Context7 Library IDs (for future lookups)

| Library | ID | Snippets |
|---------|-----|----------|
| PandaDoc API Reference | `/websites/developers_pandadoc_reference` | 2400 |
| PandaDoc for Developers | `/websites/developers_pandadoc` | 335 |
| PandaDoc Node Client SDK | `/pandadoc/pandadoc-api-node-client` | 110 |
