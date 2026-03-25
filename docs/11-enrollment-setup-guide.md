# PandaDoc Enrollment Setup Guide — Practical Recommendations

## 1. Template Design

Create a master enrollment agreement template with variables for:
- Student name, email, phone
- Program name and code
- Start date, end date
- Tuition amount, fees
- Financial aid details
- Campus/location

Brand it with institution's theme (logo, colors, fonts).

## 2. Approval Workflow

Route contracts through department head approval before sending to students:
- Use "Waiting for Approval" status
- Set up approval chain: Counselor → Department Head → Registrar
- Only approved contracts reach students

## 3. Bulk Send Workflow

Each enrollment cycle:
1. Export admitted student list from SIS as CSV
2. Map columns to template variables
3. Bulk-send personalized enrollment agreements
4. Monitor completion dashboard

## 4. Document Bundling

Bundle related documents for single signing session:
- Enrollment Agreement
- Financial Responsibility Disclosure
- FERPA Release
- Program-specific Addenda
- Housing Contract (if applicable)

## 5. CRM Integration

### If using HubSpot:
- Create enrollment docs from contact records
- Auto-move students through pipeline stages on signing
- Trigger onboarding workflows

### If custom SIS:
- Use API + Webhooks for sync
- Use Zapier as middleware

## 6. Reminders & Expiration

- Auto-reminders: 3 days, 7 days after send
- Document expiration: Aligned with enrollment deadlines
- Follow-up sequence for viewed-but-unsigned

## 7. Audit & Compliance

- Rely on built-in audit trail for financial aid audits
- Signature certificates for accreditation reviews
- FERPA-compliant handling of student records
- Archive completed contracts in organized folders

## 8. Reporting

- Weekly dashboard reports during enrollment periods
- Track: sent vs viewed vs signed conversion
- Time-to-sign metrics
- Export to BI tools for cross-referencing

## 9. Folder Structure

```
Templates/
  ├── Enrollment Agreements/
  │     ├── Enrollment Agreement - Fall 2026 v1
  │     └── Enrollment Agreement - Spring 2027 v1
  ├── Financial Forms/
  ├── Housing Contracts/
  └── Archive/

Documents/
  ├── Fall 2026/
  │     ├── Nursing Program/
  │     ├── Business Program/
  │     └── General Studies/
  ├── Spring 2027/
  └── Archive/
```

## 10. Team Setup

| Role | PandaDoc Role | Access |
|------|--------------|--------|
| IT/System Admin | Account Owner | Everything |
| Registrar | Admin | Admissions workspace |
| Enrollment Counselors | Member | Create & send in Admissions |
| Department Heads | Collaborator | Review only |
| Financial Aid | Member | Financial Aid workspace |
