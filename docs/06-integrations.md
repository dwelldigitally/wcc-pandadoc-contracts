# PandaDoc Integrations

## Native CRM Integrations

### HubSpot
- Works natively inside HubSpot CRM
- Auto-fill documents from contact/deal records
- Track document status within HubSpot
- Trigger workflows on status changes (e.g., student signs → update to "Enrolled")

### Salesforce
- Create proposals/contracts from Salesforce records
- Bidirectional data sync
- Track documents without leaving Salesforce

### Other CRMs
- Pipedrive
- Monday.com
- Attio

## Automation Platforms

### Zapier / Make
- Connect PandaDoc to 5,000+ apps
- Trigger actions on document status changes:
  - Send welcome email when enrollment completed
  - Create student record in SIS
  - Update spreadsheet/database
  - Notify admissions team

## Developer Tools

### Webhooks
- Real-time HTTP callbacks on document events
- Events: created, sent, viewed, completed, declined, etc.
- Build custom integrations with student information systems
- Configure at: Settings → Integrations → Webhooks

### API
- Full REST API for document lifecycle management
- See `01-api-reference.md` for complete endpoint list

## Payment Processors

Collect payments directly within documents:
- Stripe
- PayPal
- Square

Useful for enrollment deposits or tuition down payments.

## Enrollment Integration Strategy

1. **If using HubSpot:** Create enrollment docs from contact records, auto-update pipeline stages
2. **If using Salesforce:** Same flow via Salesforce integration
3. **If custom SIS:** Use API + Webhooks for bidirectional sync
4. **Use Zapier** for: confirmation emails, SIS updates, onboarding sequences
