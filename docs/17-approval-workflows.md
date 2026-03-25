# PandaDoc Approval Workflows

## Overview

Route documents to internal approvers **before** sending to external recipients. Available on Business and Enterprise plans.

## Setup

**Navigation:** Template editor > **Manage roles** tab > Toggle **"Approval required"**

1. Open template
2. Go to **Manage roles** tab
3. Enable **"Approval required"** toggle
4. Designate approvers

## Who Can Approve?

- Account Owner
- Admins
- Managers within the workspace
- **NOT** standard Members

## Workflow Process

```
Creator finishes draft
    ↓
Clicks "Send for Approval"
    ↓
Status → "To approve"
    ↓
Approver gets email notification
    ↓
Approver opens document
    ↓
┌─────────────┬─────────────┐
│   Approve   │   Reject    │
└──────┬──────┴──────┬──────┘
       ↓             ↓
  Creator can    Creator revises
  send to        and resubmits
  recipients
```

Approvers can add comments explaining their decision.

## Conditional Approvals (Enterprise / CPQ)

Route to specific approvers based on criteria:
- Contracts over $X require VP approval
- Custom terms require legal review
- Non-standard discounts require finance approval

## Enrollment Approval Setup

| Scenario | Approver | Trigger |
|----------|----------|---------|
| Standard enrollment | Department Head | All contracts |
| Scholarship/discount | Financial Aid Director | Discount > 10% |
| Non-standard terms | Registrar | Custom clause added |
| High-value program | VP Academic Affairs | Tuition > $X threshold |
