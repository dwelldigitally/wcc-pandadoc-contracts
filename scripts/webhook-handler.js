/**
 * WCC Contract Webhook Handler
 *
 * Lightweight HTTP server that HubSpot workflows can call via webhook.
 * When triggered, it runs the contract generation for the given deal.
 *
 * Deploy this to: Vercel, Netlify Functions, Railway, or any Node.js host.
 *
 * HubSpot Workflow Setup:
 *   Trigger: Deal stage changed to "Send Contract"
 *   Action:  Webhook → POST https://your-server.com/generate
 *   Body:    { "dealId": "{{dealId}}" }
 *
 * For local testing:
 *   node webhook-handler.js
 *   curl -X POST http://localhost:3000/generate -H "Content-Type: application/json" -d '{"dealId":"58197228338"}'
 */

const http = require('http');

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

const PORT = process.env.PORT || 3000;
const MAX_BODY_SIZE = 1024; // 1 KB — more than enough for { "dealId": "..." }
const WEBHOOK_SECRET = process.env.WEBHOOK_SECRET || '';

// ---------------------------------------------------------------------------
// HTTP Server
// ---------------------------------------------------------------------------

const server = http.createServer(async (req, res) => {
  // Health check
  if (req.method === 'GET' && req.url === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'ok', service: 'wcc-contract-generator' }));
    return;
  }

  // Generate contract endpoint
  if (req.method === 'POST' && req.url === '/generate') {
    // Authenticate if WEBHOOK_SECRET is configured
    if (WEBHOOK_SECRET && req.headers['x-webhook-secret'] !== WEBHOOK_SECRET) {
      res.writeHead(401, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Unauthorized' }));
      return;
    }

    let body = '';
    let aborted = false;

    req.on('data', (chunk) => {
      body += chunk;
      if (body.length > MAX_BODY_SIZE) {
        aborted = true;
        res.writeHead(413, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Payload too large' }));
        req.destroy();
      }
    });

    req.on('end', async () => {
      if (aborted) return;

      try {
        const { dealId } = JSON.parse(body);
        if (!dealId) {
          res.writeHead(400, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: 'dealId is required' }));
          return;
        }

        console.log(`[${new Date().toISOString()}] Generating contract for deal ${dealId}...`);

        // Load sheet data
        let sheetData;
        const hasSheets = process.env.GOOGLE_SHEETS_ID && process.env.GOOGLE_API_KEY;
        if (hasSheets) {
          sheetData = await loadSheetData();
        } else {
          sheetData = loadLocalData();
        }

        // Get HubSpot data
        const hubspotData = await getDealData(dealId);
        const programName = hubspotData.deal.program_of_study || hubspotData.contact.program_of_study;
        if (!programName) throw new Error('No program_of_study on deal or contact');

        const domestic = isDomestic(hubspotData.contact.residence_status);
        const tier = domestic ? 'domestic' : 'international';

        // Look up everything
        const program = lookupProgram(sheetData.programs, programName);
        if (!program) throw new Error(`Program "${programName}" not found in sheet`);

        const intake = lookupNextIntake(sheetData.intakes, programName);
        const intakeDate = intake?.intake_date || '';

        const fees = lookupFees(sheetData.fees, programName, intakeDate, tier);
        if (fees.length === 0) {
          throw new Error(`No fees for "${programName}" / ${tier} with effective_from <= ${intakeDate || '(no intake)'}`);
        }

        // Build and create document
        const document = buildDocument(hubspotData, program, fees, intake, domestic);
        const result = await createPandaDocDocument(document);

        console.log(`[${new Date().toISOString()}] Contract created: ${result.id}`);

        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({
          success: true,
          documentId: result.id,
          documentUrl: `https://app.pandadoc.com/a/#/documents/${result.id}`,
          student: `${hubspotData.contact.firstname} ${hubspotData.contact.lastname}`,
          program: programName,
          feeTier: tier,
          feeCount: fees.length,
          hasIntake: !!intake,
        }));
      } catch (err) {
        console.error(`[${new Date().toISOString()}] ERROR: ${err.message}`);
        res.writeHead(500, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: err.message }));
      }
    });
    return;
  }

  // 404
  res.writeHead(404, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ error: 'Not found. Use POST /generate or GET /health' }));
});

server.listen(PORT, () => {
  console.log(`WCC Contract Generator listening on port ${PORT}`);
  console.log(`  POST /generate  → Create contract from HubSpot deal`);
  console.log(`  GET  /health    → Health check`);
  if (WEBHOOK_SECRET) {
    console.log(`  Auth: X-Webhook-Secret header required`);
  }
  console.log('');
  console.log('Test with:');
  console.log(`  curl -X POST http://localhost:${PORT}/generate -H "Content-Type: application/json" -d '{"dealId":"58197228338"}'`);
});
