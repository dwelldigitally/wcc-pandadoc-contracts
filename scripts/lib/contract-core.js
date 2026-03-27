/**
 * Shared contract generation logic.
 *
 * Used by both generate-contract.js (CLI) and webhook-handler.js (HTTP).
 * Single source of truth — schema changes only need to happen here.
 */

const fs = require('fs');
const path = require('path');

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

const CONFIG = {
  pandadoc: {
    apiKey: process.env.PANDADOC_API_KEY || '',
    baseUrl: 'https://api.pandadoc.com/public/v1',
    templateId: 'peVdjKSdA2TWjZEBUNzUA6',
  },
  hubspot: {
    token: process.env.HUBSPOT_TOKEN || '',
    baseUrl: 'https://api.hubapi.com',
    accountId: '22692499',
  },
  google: {
    sheetsId: process.env.GOOGLE_SHEETS_ID || 'YOUR_GOOGLE_SHEET_ID_HERE',
    apiKey: process.env.GOOGLE_API_KEY || 'YOUR_GOOGLE_API_KEY_HERE',
  },
  domesticStatuses: [
    'Canadian Citizen',
    'Permanent Resident',
    'Refugee',
    'Citizen/PR',
  ],
  contentLibrary: {
    studentRights: 'snfvad5LqzsY2uJnhqgUtE',
    termsAndConditions: '3Sx4WPhrSMgwmkhup2NZLZ',
    studentDeclaration: 'dXqxi2R3JZZMoJzVFtoRSj',
    ptiruStatement: 'hXQubJ6usUmNnFwf3GCPbN',
    intStudentClauses: '9M4d5GkXf8Ba9hBNarTfKJ',
  },
  institution: {
    name: 'Western Community College Inc.',
    address: '#201 8313 120th Street, Surrey, BC V3W 3N4',
    number: '3758',
  },
};

// ---------------------------------------------------------------------------
// Google Sheets Reader
// ---------------------------------------------------------------------------

async function fetchSheet(tabName) {
  const url =
    `https://sheets.googleapis.com/v4/spreadsheets/${CONFIG.google.sheetsId}` +
    `/values/${encodeURIComponent(tabName)}?key=${CONFIG.google.apiKey}`;

  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Google Sheets error for "${tabName}": ${res.status} ${await res.text()}`);
  }
  const data = await res.json();
  const [headers, ...rows] = data.values || [];
  return rows.map((row) => {
    const obj = {};
    headers.forEach((h, i) => {
      obj[h.trim()] = (row[i] || '').trim();
    });
    return obj;
  });
}

async function loadSheetData() {
  const [programs, fees, intakes] = await Promise.all([
    fetchSheet('Programs'),
    fetchSheet('Fees'),
    fetchSheet('Intakes'),
  ]);
  return { programs, fees, intakes };
}

// ---------------------------------------------------------------------------
// Local CSV fallback (demo / offline use)
// ---------------------------------------------------------------------------

function parseCSV(filePath) {
  const content = fs.readFileSync(filePath, 'utf-8');
  const lines = content.split('\n').filter((l) => l.trim());
  const headers = lines[0].split(',').map((h) => h.trim());
  return lines.slice(1).map((line) => {
    const values = [];
    let current = '';
    let inQuotes = false;
    for (const ch of line) {
      if (ch === '"') {
        inQuotes = !inQuotes;
      } else if (ch === ',' && !inQuotes) {
        values.push(current.trim());
        current = '';
      } else {
        current += ch;
      }
    }
    values.push(current.trim());
    const obj = {};
    headers.forEach((h, i) => {
      obj[h] = values[i] || '';
    });
    return obj;
  });
}

function loadLocalData() {
  const dataDir = path.join(__dirname, '..', '..', 'data');
  const programs = parseCSV(path.join(dataDir, 'demo-programs.csv'));
  const fees = parseCSV(path.join(dataDir, 'demo-fees.csv'));
  return { programs, fees, intakes: [] };
}

// ---------------------------------------------------------------------------
// HubSpot API
// ---------------------------------------------------------------------------

async function hubspotGet(endpoint) {
  const res = await fetch(`${CONFIG.hubspot.baseUrl}${endpoint}`, {
    headers: { Authorization: `Bearer ${CONFIG.hubspot.token}` },
  });
  if (!res.ok) {
    throw new Error(`HubSpot error: ${res.status} ${await res.text()}`);
  }
  return res.json();
}

async function getDealData(dealId) {
  const dealProps = [
    'dealname',
    'program_of_study',
    'program_hours',
    'program_duration_weeks',
    'program_credential',
    'pipeline',
    'dealstage',
  ].join(',');

  const deal = await hubspotGet(
    `/crm/v3/objects/deals/${dealId}?properties=${dealProps}`
  );

  const assoc = await hubspotGet(
    `/crm/v3/objects/deals/${dealId}/associations/contacts`
  );
  const contactId = assoc.results?.[0]?.id;
  if (!contactId) {
    throw new Error(`No contact associated with deal ${dealId}`);
  }

  const contactProps = [
    'firstname',
    'lastname',
    'email',
    'phone',
    'mobilephone',
    'date_of_birth',
    'address',
    'city',
    'state',
    'zip',
    'country',
    'program_of_study',
    'residence_status',
    'citizenship',
    'gender',
  ].join(',');

  const contact = await hubspotGet(
    `/crm/v3/objects/contacts/${contactId}?properties=${contactProps}`
  );

  return {
    deal: deal.properties,
    contact: contact.properties,
    dealId,
    contactId,
  };
}

// ---------------------------------------------------------------------------
// Fee & Program Lookup
// ---------------------------------------------------------------------------

function isDomestic(residenceStatus) {
  if (!residenceStatus) return true;
  return CONFIG.domesticStatuses.some(
    (s) => s.toLowerCase() === residenceStatus.toLowerCase()
  );
}

function lookupProgram(programs, programName) {
  return programs.find(
    (p) => p.program_name.toLowerCase() === programName.toLowerCase()
  );
}

// Columns in the Fees tab that are keys, not fee amounts
const FEE_KEY_COLUMNS = ['program_name', 'effective_from', 'residency', 'total'];

/**
 * Looks up fees for a program + residency tier using effective_from date logic.
 * Finds the most recent fee row where effective_from <= intakeDate.
 * When intakeDate is empty, falls back to the most recent fee row (no date filter).
 * Returns an array of { fee_name, amount } extracted from all non-empty fee columns.
 */
function lookupFees(feeRows, programName, intakeDate, residencyTier) {
  const hasIntakeDate = !!intakeDate;

  const candidates = feeRows.filter((r) => {
    if (r.program_name.toLowerCase() !== programName.toLowerCase()) return false;
    if (r.residency.toLowerCase() !== residencyTier.toLowerCase()) return false;
    // When no intake date, skip the date filter — return all matching rows
    if (!hasIntakeDate) return true;
    // Compare as Date objects for safety (handles YYYY-MM-DD and other formats)
    const effDate = new Date(r.effective_from);
    const intDate = new Date(intakeDate);
    return !isNaN(effDate) && !isNaN(intDate) && effDate <= intDate;
  });

  if (candidates.length === 0) return [];

  // Pick the row with the latest effective_from (most recent fee schedule)
  const row = candidates.sort((a, b) =>
    new Date(b.effective_from) - new Date(a.effective_from)
  )[0];

  // Every column that isn't a key column and has a non-zero numeric value is a fee
  const fees = [];
  for (const [column, value] of Object.entries(row)) {
    if (FEE_KEY_COLUMNS.includes(column.toLowerCase())) continue;
    const trimmed = String(value).replace(/[$,]/g, '').trim();
    const amount = Number(trimmed);
    if (!trimmed || isNaN(amount) || amount === 0) continue;
    fees.push({ fee_name: column, amount });
  }
  return fees;
}

function lookupNextIntake(intakes, programName) {
  const now = new Date();
  return intakes
    .filter(
      (i) =>
        i.program_name.toLowerCase() === programName.toLowerCase() &&
        i.status === 'Open' &&
        new Date(i.intake_date) >= now
    )
    .sort((a, b) => new Date(a.intake_date) - new Date(b.intake_date))[0];
}

// ---------------------------------------------------------------------------
// PandaDoc Document Builder
// ---------------------------------------------------------------------------

function buildDocument(hubspotData, program, fees, intake, domestic) {
  const { deal, contact } = hubspotData;
  const programName = deal.program_of_study || contact.program_of_study || '';
  const residenceStatus = contact.residence_status || '';
  const isInt = !domestic;

  const addressParts = [
    contact.address,
    contact.city,
    contact.state,
    contact.zip,
    contact.country,
  ].filter(Boolean);
  const mailingAddress = addressParts.join(', ') || '';

  // fees is already an array of { fee_name, amount } from lookupFees()
  const feeRows = fees.map((fee) => ({
    options: {
      optional: false,
      optional_selected: true,
      qty_editable: false,
    },
    data: {
      name: fee.fee_name,
      price: fee.amount,
      qty: 1,
    },
  }));

  const startDate = intake?.intake_date || '';
  const endDate = intake?.end_date || '';
  const campus = intake?.campus || '';
  const schedule = intake?.schedule || '';

  // Hours and weeks come from the intake (per-cohort), not the program
  const hours = intake?.hours || deal.program_hours || '';
  const weeks = intake?.weeks || deal.program_duration_weeks || '';

  // Delivery method varies by residency within the same cohort
  const deliveryMethod = domestic
    ? (intake?.domestic_delivery_method || '')
    : (intake?.international_delivery_method || '');

  // Build content placeholders
  const contentPlaceholders = [];

  if (program?.program_outline_id) {
    contentPlaceholders.push({
      block_id: 'Program Outline',
      content_library_items: [{ id: program.program_outline_id }],
    });
  }

  if (isInt) {
    contentPlaceholders.push({
      block_id: 'International Student Clauses',
      content_library_items: [{ id: CONFIG.contentLibrary.intStudentClauses }],
    });
  }

  const document = {
    name: `${contact.firstname} ${contact.lastname} - ${programName} Enrollment Contract`,
    template_uuid: CONFIG.pandadoc.templateId,
    recipients: [
      {
        email: contact.email,
        first_name: contact.firstname || '',
        last_name: contact.lastname || '',
        role: 'Student',
        signing_order: 1,
      },
      {
        email: 'admissions@wcc.ca',
        first_name: 'Admissions',
        last_name: 'Representative',
        role: 'Admissions Rep',
        signing_order: 2,
      },
    ],
    tokens: [
      { name: 'Student.FirstName', value: contact.firstname || '' },
      { name: 'Student.LastName', value: contact.lastname || '' },
      { name: 'Student.Email', value: contact.email || '' },
      { name: 'Student.Phone', value: contact.phone || contact.mobilephone || '' },
      { name: 'Student.MailingAddress', value: mailingAddress },
      { name: 'Student.DOB', value: contact.date_of_birth || '' },
      { name: 'Student.ResidenceStatus', value: residenceStatus },
      { name: 'Student.Citizenship', value: contact.citizenship || '' },
      { name: 'Student.Gender', value: contact.gender || '' },
      { name: 'Program.Title', value: programName },
      { name: 'Program.Hours', value: hours },
      { name: 'Program.DurationWeeks', value: weeks },
      { name: 'Program.Credential', value: program?.credential || deal.program_credential || '' },
      { name: 'Program.Schedule', value: schedule },
      { name: 'Program.DeliveryMethod', value: deliveryMethod },
      { name: 'Program.Campus', value: campus },
      { name: 'Program.Language', value: 'English' },
      { name: 'Contract.StartDate', value: startDate },
      { name: 'Contract.EndDate', value: endDate },
      { name: 'Institution.Name', value: CONFIG.institution.name },
      { name: 'Institution.Address', value: CONFIG.institution.address },
      { name: 'Institution.Number', value: CONFIG.institution.number },
    ],
    pricing_tables: [
      {
        name: 'Program Costs',
        options: { currency: 'CAD' },
        sections: [
          { title: 'Program Fees', default: true, rows: feeRows },
        ],
      },
    ],
    ...(contentPlaceholders.length > 0 && { content_placeholders: contentPlaceholders }),
    metadata: {
      hubspot_deal_id: hubspotData.dealId,
      hubspot_contact_id: hubspotData.contactId,
      program_code: program?.program_code || '',
      residence_tier: domestic ? 'domestic' : 'international',
    },
    tags: [
      program?.program_code || '',
      domestic ? 'Domestic' : 'International',
      program?.category || '',
    ].filter(Boolean),
    parse_form_fields: false,
  };

  return document;
}

// ---------------------------------------------------------------------------
// PandaDoc API
// ---------------------------------------------------------------------------

async function createPandaDocDocument(document) {
  const res = await fetch(`${CONFIG.pandadoc.baseUrl}/documents`, {
    method: 'POST',
    headers: {
      Authorization: `API-Key ${CONFIG.pandadoc.apiKey}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(document),
  });

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`PandaDoc error: ${res.status} ${body}`);
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Exports
// ---------------------------------------------------------------------------

module.exports = {
  CONFIG,
  fetchSheet,
  loadSheetData,
  parseCSV,
  loadLocalData,
  hubspotGet,
  getDealData,
  isDomestic,
  lookupProgram,
  lookupFees,
  lookupNextIntake,
  buildDocument,
  createPandaDocDocument,
};
