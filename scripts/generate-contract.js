/**
 * WCC Contract Generation Script (CLI)
 *
 * Reads program data from a Google Sheet, student/deal data from HubSpot,
 * and creates a fully populated PandaDoc enrollment contract.
 *
 * Usage:
 *   node generate-contract.js <hubspot-deal-id>
 *
 * Environment variables:
 *   PANDADOC_API_KEY    - PandaDoc API key
 *   HUBSPOT_TOKEN       - HubSpot private app token
 *   GOOGLE_SHEETS_ID    - Google Sheet ID (from the URL)
 *   GOOGLE_API_KEY      - Google Sheets API key (for public/link-shared sheets)
 *
 * Google Sheet must have 3 tabs: "Programs", "Fees", "Intakes"
 * See data/sheets-design.md for the expected structure.
 */

const {
  CONFIG,
  loadSheetData,
  loadLocalData,
  getDealData,
  isDomestic,
  lookupProgram,
  lookupFees,
  lookupNextIntake,
  buildDocument,
  createPandaDocDocument,
} = require('./lib/contract-core');

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  const dealId = process.argv[2];

  if (!dealId) {
    console.error('Usage: node generate-contract.js <hubspot-deal-id>');
    console.error('');
    console.error('Example:');
    console.error('  node generate-contract.js 58197228338');
    console.error('');
    console.error('Environment variables:');
    console.error('  PANDADOC_API_KEY    PandaDoc API key');
    console.error('  HUBSPOT_TOKEN       HubSpot private app token');
    console.error('  GOOGLE_SHEETS_ID    Google Sheet ID');
    console.error('  GOOGLE_API_KEY      Google API key');
    process.exit(1);
  }

  try {
    // Step 1: Load program data from Google Sheets (or local CSV fallback)
    console.log('Loading program data...');
    let sheetData;
    if (
      CONFIG.google.sheetsId !== 'YOUR_GOOGLE_SHEET_ID_HERE' &&
      CONFIG.google.apiKey !== 'YOUR_GOOGLE_API_KEY_HERE'
    ) {
      console.log('  → Reading from Google Sheets...');
      sheetData = await loadSheetData();
    } else {
      console.log('  → Google Sheets not configured, using local CSV files...');
      sheetData = loadLocalData();
    }
    console.log(
      `  → Loaded ${sheetData.programs.length} programs, ${sheetData.fees.length} fee rows, ${sheetData.intakes.length} intakes`
    );

    // Step 2: Get deal and contact data from HubSpot
    console.log(`\nFetching HubSpot deal ${dealId}...`);
    const hubspotData = await getDealData(dealId);
    const programName =
      hubspotData.deal.program_of_study ||
      hubspotData.contact.program_of_study;
    const residenceStatus = hubspotData.contact.residence_status;

    console.log(`  → Student: ${hubspotData.contact.firstname} ${hubspotData.contact.lastname}`);
    console.log(`  → Email: ${hubspotData.contact.email}`);
    console.log(`  → Program: ${programName}`);
    console.log(`  → Residence: ${residenceStatus}`);

    if (!programName) {
      throw new Error(
        'No program_of_study found on deal or contact. Set it in HubSpot first.'
      );
    }

    // Step 3: Look up program details, fees, and next intake
    const domestic = isDomestic(residenceStatus);
    const tier = domestic ? 'domestic' : 'international';
    console.log(`  → Fee tier: ${tier}`);

    const program = lookupProgram(sheetData.programs, programName);
    if (!program) {
      throw new Error(
        `Program "${programName}" not found in sheet. Check that the name matches exactly.`
      );
    }
    console.log(
      `  → Found program: ${program.program_code} | ${program.credential}`
    );

    const intake = lookupNextIntake(sheetData.intakes, programName);
    if (intake) {
      console.log(
        `  → Next intake: ${intake.intake_date} → ${intake.end_date} at ${intake.campus} (${intake.schedule})`
      );
      console.log(
        `  → Cohort: ${intake.hours}h | ${intake.weeks}wk | delivery: ${domestic ? intake.domestic_delivery_method : intake.international_delivery_method}`
      );
    } else {
      console.log('  → No upcoming intake found (advisor will fill dates manually)');
    }

    // Look up fees by program + residency, effective_from <= intake date
    const intakeDate = intake?.intake_date || '';
    const fees = lookupFees(sheetData.fees, programName, intakeDate, tier);
    if (fees.length === 0) {
      throw new Error(
        `No fees found for "${programName}" / ${tier} with effective_from <= ${intakeDate || '(no intake)'}.`
      );
    }
    console.log(`  → Found ${fees.length} fee items:`);
    fees.forEach((f) => {
      console.log(`     ${f.fee_name}: $${f.amount}`);
    });

    // Step 4: Build the PandaDoc document payload
    console.log('\nBuilding PandaDoc document...');
    const document = buildDocument(hubspotData, program, fees, intake, domestic);

    // Step 5: Create the document in PandaDoc
    console.log('Creating document in PandaDoc...');
    const result = await createPandaDocDocument(document);

    console.log('\n========================================');
    console.log('CONTRACT CREATED SUCCESSFULLY');
    console.log('========================================');
    console.log(`Document ID:   ${result.id}`);
    console.log(`Status:        ${result.status}`);
    console.log(`View:          https://app.pandadoc.com/a/#/documents/${result.id}`);
    console.log('');
    console.log('Advisor next steps:');
    if (!intake) {
      console.log('  → Fill in Contract Start Date and End Date');
    }
    console.log('  → Review all auto-populated fields');
    console.log('  → Fill in PEN (Personal Education Number)');
    console.log('  → Click Send to deliver to student for signature');

    return result;
  } catch (err) {
    console.error(`\nERROR: ${err.message}`);
    process.exit(1);
  }
}

main();
