# WCC Master Student Enrollment Contract — Implementation Guide

**Last Updated:** 2026-03-20
**Template ID:** `peVdjKSdA2TWjZEBUNzUA6`
**Template URL:** https://app.pandadoc.com/a/#/templates/peVdjKSdA2TWjZEBUNzUA6

---

## What's Already Done

| Item | Status |
|------|--------|
| PandaDoc template uploaded (original contract, 16 pages, logo) | Done |
| Roles: Student (1) → Admissions Rep (2), signing order ON | Done |
| Student Signature + Date fields placed | Done |
| Admissions Rep Signature + Date fields placed | Done |
| 4 static Content Library items created & populated | Done |
| HubSpot deal properties: program_hours, program_duration_weeks, program_credential | Done |
| HubSpot test deal (Tushar - HCA) with 4 line items | Done |
| PandaDoc research docs saved locally (17 files) | Done |
| HubSpot workflow shell: "PandaDoc - Copy Contact Props to Deal" (trigger set) | Done |

---

## Part 1: PandaDoc Template Configuration

### 1.1 Add Pricing Table Block (5 min)

**Where:** Program Costs section (page 2 of template)

1. Open template: https://app.pandadoc.com/a/#/templates/peVdjKSdA2TWjZEBUNzUA6
2. Scroll to the **PROGRAM COSTS** section (page 2) — you'll see the static table with Registration Fee, Textbooks Fee, Course Materials Fee, Tuition Fee, Scholarship, TOTAL PROGRAM COST
3. Click the **"+"** button that appears between uploaded blocks (between the page with Program Costs and the page with Payment Terms)
4. From the sidebar, drag **"Pricing table"** into that spot
5. Configure the pricing table:
   - **Columns:** Name, Description, Price, QTY, Subtotal
   - Click the **⋮ (three dots)** on the pricing table → **Settings**
   - Enable **"Data merge"** — this allows HubSpot deal line items to auto-populate
   - Set currency to **CAD**
6. Add a discount row: click **"+ Discount"** at the bottom of the pricing table → name it **"Scholarship"** → set type to flat amount
7. Optionally: Delete the old static fee table in the uploaded block above (click on it → ⋮ → Delete block) since the pricing table replaces it

### 1.2 Add Smart Content Block — Program Outline (5 min)

**Where:** After the "PROGRAM OUTLINE" section (page 1-2)

1. Scroll to the **PROGRAM OUTLINE** section which says "Program Information: Refer to the Attached Program Outline"
2. Click the **"+"** between uploaded blocks right after that section
3. From the sidebar, drag **"Smart content"** into that spot
4. Click on the Smart Content block → Select **"Conditional content"**
5. Set the condition variable: click the variable dropdown and find the HubSpot CRM token that matches `program_of_study` (it may appear as `Deal.ProgramOfStudy` or `Contact.ProgramOfStudy`)
6. Add conditions (one per program you have content library items for):

| Condition | Content Library Item |
|-----------|---------------------|
| IF `program_of_study` **equals** `Health Care Assistant Diploma` | HCA PO Domestic (`H9TBoFAFWAgHUs3LcgVrvB`) |
| IF `program_of_study` **equals** `Education Assistant Diploma` | EA PO (`m7jpnTkaUU2ujqbRencCbZ`) |
| IF `program_of_study` **equals** `Early Childhood Education Assistant` | ECEA PO (`ugQBogw6cVWd3eAENw3EHa`) |
| IF `program_of_study` **equals** `Medical Office Assistant Diploma` | MOA PO (`X24vZTRf4ACwqHpFuHejxg`) |
| IF `program_of_study` **equals** `Medical Laboratory Assistant` | MLA PO (`2Vwx3RVDmzuSqGLuv4KtJP`) |
| IF `program_of_study` **equals** `Live in Caregiver Certificate` | LICG PO (`35RCS7aNnkDHVpFUS9MRn4`) |
| IF `program_of_study` **equals** `Community Support Worker Diploma` | CSW — use CSWD Dom PO or Int PO |
| IF `program_of_study` **equals** `Dental Assistant Diploma` | DA PO (`X9ueQrNCeUo5xBHiVGLJoV`) |
| IF `program_of_study` **equals** `Business Management Diploma` | DBM PO (`4Tkrq2wybAY8vSDKCaKqLj`) |
| IF `program_of_study` **equals** `Registered Massage Therapy Program` | RMTB PO (`UEgWPYCGybEttqSrgrtgtP`) |
| IF `program_of_study` **equals** `Medical Device Reprocessing Technician Certificate` | MDRT PO (`kHan6UCyXSoZ8Dba9HwWe6`) |

7. Set **default behavior**: Hide block
8. You can add up to 50 conditions per Smart Content block. For remaining programs, create their Content Library items first, then add conditions here.

### 1.3 Add Smart Content Block — International Student Clauses (3 min)

**Where:** In the Refund Policy section, near "Additional note for International Students"

1. Scroll to the **Refund Policy** section (pages 3-5)
2. Click **"+"** between blocks near the international student refund text
3. Drag **"Smart content"** from sidebar
4. Set condition:
   - IF `residence_status` **contains** `International` → insert Content Library item **"Int Student"** (`9M4d5GkXf8Ba9hBNarTfKJ`)
   - IF `residence_status` **equals** `Work Permit` → insert same item
   - IF `residence_status` **equals** `Visitor` → insert same item
5. Default: **Hide block**

### 1.4 Connect HubSpot Variables to Student Info Fields (10 min)

For each empty cell in the **STUDENT INFORMATION** table on page 1, click into the cell and type `[` to trigger PandaDoc's variable picker. Select the matching HubSpot CRM token.

**Important:** When creating documents from a HubSpot **Deal**, only basic contact fields (name, email, phone) auto-map. For other contact fields, the token names follow the pattern `Contact.PropertyName` or `Deal.PropertyName`. Check what tokens are available by clicking `[` in any cell.

| Table Cell | Token to Select |
|---|---|
| Last Name: | `[Contact.LastName]` or `[Student.LastName]` |
| Usual First Name: | `[Contact.FirstName]` or `[Student.FirstName]` |
| First Name & Middle Name: | `[Contact.FirstName]` |
| Student Email Address: | `[Contact.Email]` or `[Student.Email]` |
| Student Telephone Number: | `[Contact.Phone]` |
| Personal Education Number: | **Leave empty** — Advisor fills manually (or add a Text Field assigned to Admissions Rep role) |
| Mailing Address: | `[Contact.MailingAddress]` or `[Contact.Address]` |
| Date of Birth: | `[Contact.DateOfBirth]` or `[Contact.StudentDateOfBirth]` |
| Mailing Address in Canada: | **Leave empty** — Advisor fills if needed |
| Immigration Status: | `[Contact.ResidenceStatus]` |
| Citizenship: | `[Contact.Citizenship]` |
| Gender: | `[Contact.Gender]` |
| Study Permit: | **Leave empty** or derive from residence_status |

**For PROGRAM INFORMATION section:**

| Table Cell | Token to Select |
|---|---|
| Program Title: | `[Contact.ProgramOfStudy]` or `[Deal.ProgramOfStudy]` |
| Hours of Instruction: | `[Deal.ProgramHours]` |
| Program Duration in Weeks: | `[Deal.ProgramDurationWeeks]` |
| Contract Start Date: | **Leave empty** — Drag a **Date** field from sidebar (assign to Admissions Rep role) |
| Contract End Date: | **Leave empty** — Drag a **Date** field from sidebar (assign to Admissions Rep role) |
| Credential: | `[Deal.ProgramCredential]` |
| Program Schedule: | **Leave empty** — Drag a **Dropdown** field (options: Full-Time, Part-Time) assigned to Admissions Rep |

**Tip:** If a token doesn't appear in the picker, type the exact HubSpot internal property name (e.g., `program_of_study`). PandaDoc will create a custom variable that maps when documents are generated from HubSpot.

### 1.5 Add Advisor Input Fields (5 min)

Switch the sidebar role to **Admissions Rep** and drag these fields into the document:

1. **Contract Start Date** — Drag a **Date** field into the "Contract Start Date" cell
2. **Contract End Date** — Drag a **Date** field into the "Contract End Date" cell
3. **Program Schedule** — Drag a **Dropdown** field → add options: `Full-Time`, `Part-Time`
4. **Delivery Method** — The existing checkboxes in the template may work. Alternatively, drag **Checkbox** fields from sidebar for: In-class, Distance-Synchronous, Distance-Asynchronous, Combined — assign all to Admissions Rep
5. **PEN** — Drag a **Text field** into the "Personal Education Number" cell — assign to Admissions Rep
6. **Payment Method** — Optionally replace existing checkboxes in Payment Terms section with PandaDoc Checkbox fields assigned to Admissions Rep

### 1.6 Delete Parent/Guardian Signature Row (1 min)

Since parent/guardian signatures never happen:
1. Scroll to the signature page (page 16)
2. The "Signature of Parent or Legal Guardian" row is between the Student and Institution signature sections
3. Click on the uploaded block containing that row
4. If you can edit the text, delete that row. If it's part of the uploaded block and can't be edited inline, leave it — it will just appear as empty cells in the signed document

---

## Part 2: HubSpot Workflow Configuration

### 2.1 Workflow: "PandaDoc - Copy Contact Props to Deal"

**URL:** https://app.hubspot.com/workflows/22692499/platform/flow/1793830515/edit
**Trigger:** Already set — Deal created
**Status:** Trigger configured, needs actions

**Note:** This workflow may NOT be needed. When PandaDoc creates documents from a HubSpot deal, it auto-maps many contact properties via the integration. Test first without this workflow — create a document from HubSpot and check which tokens auto-populate. Only build this workflow for properties that don't auto-map.

**If needed, add these actions:**

1. Click the **"+"** button below the trigger to add an action
2. Select **CRM** → **Edit record**
3. Record type: **Deal (Current object)**
4. For each property to copy:
   - Click **"Property to edit"** → select the deal property (e.g., `program_hours`)
   - Change value type from "Static value" to **"Copy property value"**
   - Source: **Associated contact** → select the matching contact property
   - Click **Save**
5. Click **"+"** below that action to add the next one
6. Repeat for each property pair:

| Deal Property | Copy From Contact Property |
|---|---|
| `program_of_study` (create if needed) | `program_of_study` |
| `residence_status` (create if needed) | `residence_status` |
| `citizenship` (create if needed) | `citizenship` |
| `gender` (create if needed) | `gender` |
| `date_of_birth` (create if needed) | `date_of_birth` |
| `mailing_address` (create if needed) | `mailing_address` |

**Note:** You'll need to create these as Deal properties first (Settings → Properties → Deal properties → Create property) if they don't already exist. They should all be **Single-line text** type.

### 2.2 Workflow: "PandaDoc - Populate Program Data"

**Purpose:** When a deal's program_of_study is set, auto-populate program_hours, program_duration_weeks, and program_credential.

**Create new workflow:**

1. Go to: https://app.hubspot.com/workflows/22692499/create/flow
2. Trigger: **Data values** → **Property value changed** → Object: **Deal** → Property: `program_of_study`
3. Click **Next** through Eligible records and Settings → **Save and continue**
4. Add action: **Branch** (IF/THEN)
5. Branch 1: IF `program_of_study` **is any of** `Health Care Assistant Diploma`
   - THEN: **Edit record** → Set:
     - `program_hours` = `775`
     - `program_duration_weeks` = `26`
     - `program_credential` = `Diploma`
6. Branch 2: IF `program_of_study` **is any of** `Education Assistant Diploma`
   - THEN: **Edit record** → Set:
     - `program_hours` = `900`
     - `program_duration_weeks` = `34`
     - `program_credential` = `Diploma`
7. Continue adding branches for each program...

**HCA Program Data (for reference):**
- Hours: 775
- Weeks: 26 (Full Time) / 38 (Part Time)
- Credential: Diploma

**You'll need the hours/weeks/credential for each of your 65 programs.** Start with the programs you have content library items for (HCA, EA, ECEA, MOA, MLA, LICG, CSW, DA, DBM, RMT, MDRT) and add the rest over time.

### 2.3 Workflow: "PandaDoc - Auto Add Line Items"

**Purpose:** When a deal is created with program_of_study + residence_status set, automatically add the correct fee line items.

**Create new workflow:**

1. Go to: https://app.hubspot.com/workflows/22692499/create/flow
2. Trigger: **Data values** → **Record created** → Object: **Deal**
3. Add enrollment condition: `program_of_study` **is known**
4. Click **Next** → **Save and continue**
5. Add action: **CRM** → **Add line item to deal**
6. First line item: **Application Fee** ($250) — this is universal
   - Product: Search for "Application Fee $250" in your product catalog
   - OR set: Name = "Application Fee", Price = 250, Quantity = 1
7. Add **Branch** action for tuition (domestic vs international):
   - IF `residence_status` **is any of** `Canadian Citizen`, `Permanent Resident`, `Refugee`, `Citizen/PR`
     - THEN: Add line item → Domestic tuition for the program
   - ELSE:
     - Add line item → International tuition for the program
8. Add another action for **Textbook Fee** (program-specific)
9. Add another action for **Course Materials Fee** (if applicable)

**Alternative simpler approach:** Instead of building this complex branching workflow, have advisors manually add line items from the HubSpot product catalog when creating deals. The products already exist (131 products). This is 2 clicks per line item and avoids the complex 65×2 branching workflow.

---

## Part 3: End-to-End Testing

### 3.1 Test with HCA Domestic Student

1. Open the test deal in HubSpot: https://app.hubspot.com/contacts/22692499/record/0-3/58197228338
   - Deal: "Tushar Malhotra - HCA"
   - Contact: Tushar Malhotra (malhotratushar37@gmail.com)
   - Line items: Application Fee ($250) + Tuition Domestic ($7000) + Textbook ($175) + Materials ($75)
   - Deal properties: program_hours=775, program_duration_weeks=26, program_credential=Diploma

2. In the PandaDoc widget on the deal record, click **"Create Document"**

3. Select **"WCC Master Student Enrollment Contract"** template

4. Verify in the PandaDoc editor:
   - [ ] Student name, email, phone auto-populated from contact
   - [ ] Program title shows "Health Care Assistant Diploma"
   - [ ] Program hours shows "775"
   - [ ] Program duration shows "26"
   - [ ] Credential shows "Diploma"
   - [ ] Pricing table shows 4 line items from HubSpot deal
   - [ ] Smart Content shows HCA program outline (if configured)
   - [ ] Signature fields are in place for Student and Admissions Rep

5. Fill in the advisor fields:
   - Contract Start Date: pick a date
   - Contract End Date: pick a date
   - Program Schedule: Full-Time
   - Delivery Method: check In-class
   - PEN: enter a test number

6. Click **Send** → verify student (malhotratushar37@gmail.com) receives the document

7. Open the document link, sign as student

8. Verify advisor receives countersign notification

9. After both signatures, verify completed contract syncs back to HubSpot deal

### 3.2 Test with International Student

1. Create a new contact with `residence_status` = "International Study Permit"
2. Create a deal with HCA International line items (tuition $9000)
3. Repeat steps 2-9 above
4. Additionally verify:
   - [ ] International student refund clauses appear (Smart Content)
   - [ ] International student consent section appears
   - [ ] Correct international tuition amount in pricing table

---

## Part 4: Scaling to All 65 Programs

### 4.1 Content Library Items Needed

For each new program, create 2-3 Content Library items:
- **Program Outline** (PO) — convert the program outline PDF into a content library item
- **Fee Domestic** — (only if using Smart Content for fees instead of pricing table)
- **Fee International** — (only if using Smart Content for fees instead of pricing table)

**Steps to create a Program Outline content library item:**
1. Go to PandaDoc → Templates → Content Library tab
2. Click **"+ Content Item"**
3. Name it: "[PROGRAM_CODE] PO" (e.g., "BKA PO")
4. Upload or paste the program outline content
5. Save

### 4.2 HubSpot Product Library

For each program, ensure these products exist in HubSpot:
- `[Program Name] - Domestic` (tuition)
- `[Program Name] - International` (tuition)
- `[Program Name] - Textbook Fee` (if unique per program)
- `[Program Name] - Course Materials Fee` (if applicable)

**Check existing products:** https://app.hubspot.com/contacts/22692499/objects/0-7/views/all/list
Currently 131 products exist — many programs already have domestic/international pairs.

### 4.3 Smart Content Conditions

Add conditions to the Program Outline Smart Content block for each new program.
- Max 50 conditions per block
- If you exceed 50, add a second Smart Content block for the overflow

### 4.4 Workflow Branches

Add a branch to the "Populate Program Data" workflow for each new program with its hours, weeks, and credential values.

---

## Quick Reference: Key IDs and URLs

### PandaDoc
| Item | ID/URL |
|------|--------|
| Master Template | `peVdjKSdA2TWjZEBUNzUA6` — https://app.pandadoc.com/a/#/templates/peVdjKSdA2TWjZEBUNzUA6 |
| API Key (Sandbox) | Set via PANDADOC_API_KEY env var |
| Statement of Student Rights | `snfvad5LqzsY2uJnhqgUtE` |
| Contract Terms & Conditions | `3Sx4WPhrSMgwmkhup2NZLZ` |
| Student Declaration | `dXqxi2R3JZZMoJzVFtoRSj` |
| PTIRU Statement | `hXQubJ6usUmNnFwf3GCPbN` |

### HubSpot
| Item | ID/URL |
|------|--------|
| Account | 22692499 |
| Test Deal (Tushar - HCA) | 58197228338 — https://app.hubspot.com/contacts/22692499/record/0-3/58197228338 |
| Test Contact (Tushar) | 185551413157 |
| Workflow: Copy Contact Props | 1793830515 — https://app.hubspot.com/workflows/22692499/platform/flow/1793830515/edit |
| Private App Token | Set via HUBSPOT_TOKEN env var |

### HubSpot Deal Properties (Custom)
| Label | Internal Name | Type |
|-------|--------------|------|
| Program Hours | `program_hours` | Single-line text |
| Program Duration Weeks | `program_duration_weeks` | Single-line text |
| Program Credential | `program_credential` | Dropdown (Diploma, Certificate, Post-Graduate Diploma) |

### Fee Structure (HCA Example)
| Fee | Domestic | International |
|-----|----------|---------------|
| Application Fee | $250 | $250 |
| Tuition | $7,000 | $9,000 |
| Textbook Fee | $175 | $175 |
| Course Materials Fee | $75 | $75 |

### Residence Status → Fee Tier Mapping
| Domestic | International |
|----------|---------------|
| Canadian Citizen | International Study Permit |
| Permanent Resident | Work Permit |
| Refugee | Visitor |
| Citizen/PR | Currently Not Residing in Canada |
| | Permit/Visa |

---

## Estimated Time to Complete

| Task | Time |
|------|------|
| 1.1 Pricing Table | 5 min |
| 1.2 Smart Content — Program Outline (HCA only) | 5 min |
| 1.3 Smart Content — International Clauses | 3 min |
| 1.4 Connect HubSpot Variables | 10 min |
| 1.5 Add Advisor Input Fields | 5 min |
| 1.6 Delete Parent/Guardian Row | 1 min |
| 2.1 Workflow: Copy Contact Props (if needed) | 15 min |
| 2.2 Workflow: Populate Program Data (HCA branch only) | 10 min |
| 2.3 Workflow: Auto Add Line Items (or do manually) | 15 min |
| 3.1 End-to-End Test | 10 min |
| **Total for HCA proof of concept** | **~80 min** |
| **Scaling to all 65 programs** | **~4-6 hours** |
