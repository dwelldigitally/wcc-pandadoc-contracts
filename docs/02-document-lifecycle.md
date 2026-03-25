# PandaDoc Document Lifecycle

## Document Statuses

| Status | Description |
|--------|-------------|
| **Draft** | Created/edited but not sent. Documents returned for editing revert here. |
| **Sent** | Delivered to recipient(s) but not yet opened. |
| **Viewed** | Recipient has opened the document. |
| **Waiting for Approval** | Internal approval workflow pending before signing. |
| **Suggest Edits** | Recipient requested changes (redlining/negotiation). |
| **Waiting for Payment** | Signed but payment pending (if payment block included). |
| **Completed** | All recipients signed and all conditions met. |
| **Paid** | Payment collected. |
| **Expired** | Passed expiration date without completion. |
| **Declined** | Recipient declined or manually declined. |
| **Voided** | Sender canceled; no longer accessible to recipients. |

Admins can manually change status to: Completed, Expired, Paid, or Declined.

## Typical Enrollment Flow

```
Draft → Sent → Viewed → Completed
                  ↘ Declined
                  ↘ Expired
```

## Best Practices for Enrollment

- Set document **expiration dates** aligned with enrollment deadlines
- Use **auto-reminders** (e.g., 3 days, 7 days after send) for students who viewed but didn't sign
- Monitor the **Viewed → Completed** conversion for follow-up targeting
