import React, { useState, useEffect, useRef } from "react";
import {
  hubspot,
  Text,
  Button,
  Flex,
  Alert,
  LoadingSpinner,
  Select,
  Divider,
  DescriptionList,
  DescriptionListItem,
  Tag,
  Link,
} from "@hubspot/ui-extensions";

// Backend URL — update after deploying to Railway/Render
const BACKEND_URL = "https://wcc-contract-generator-production.up.railway.app";
// IMPORTANT: Set this to match WEBHOOK_SECRET env var on Railway
const WEBHOOK_SECRET = "9da41df1ab58401682e2c69c91702e2d";

hubspot.extend(({ actions, context }) => <ContractGenerator actions={actions} context={context} />);

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const fmt = (amount) => {
  if (amount == null || amount === "") return "--";
  const n = typeof amount === "number" ? amount : parseFloat(amount);
  if (isNaN(n)) return "--";
  const prefix = n < 0 ? "-$" : "$";
  return prefix + Math.abs(n).toLocaleString("en-CA", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

const ContractGenerator = ({ actions, context }) => {
  const { fetchCrmObjectProperties, onCrmPropertiesUpdate } = actions;

  const [dealProps, setDealProps] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [programData, setProgramData] = useState(null);
  const [selectedIntake, setSelectedIntake] = useState(null);
  const dealPropsRef = useRef(null);
  const isGeneratingRef = useRef(false);

  useEffect(() => { dealPropsRef.current = dealProps; }, [dealProps]);

  // Fetch deal properties on load
  useEffect(() => {
    fetchCrmObjectProperties([
      "hs_object_id",
      "dealname",
      "program_of_study",
      "hubspot_owner_id",
    ])
      .then((props) => {
        setDealProps(props);
        if (props.program_of_study) {
          return fetchProgramData(props.hs_object_id, props.program_of_study);
        }
        return null;
      })
      .then((data) => { if (data) setProgramData(data); })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  // Listen for property changes
  useEffect(() => {
    onCrmPropertiesUpdate(
      ["program_of_study", "hubspot_owner_id"],
      (updatedProps) => {
        setDealProps((prev) => ({ ...prev, ...updatedProps }));
        setResult(null);
        setProgramData(null);
        setSelectedIntake(null);
        if (updatedProps.program_of_study && dealPropsRef.current?.hs_object_id) {
          fetchProgramData(dealPropsRef.current.hs_object_id, updatedProps.program_of_study)
            .then((data) => { if (data) setProgramData(data); });
        }
      }
    );
  }, []);

  // Fetch program data from backend
  const fetchProgramData = async (dealId, programName, intakeDate) => {
    try {
      let url = `${BACKEND_URL}/program-data?program_name=${encodeURIComponent(programName)}&deal_id=${dealId}`;
      if (intakeDate) url += `&intake_date=${encodeURIComponent(intakeDate)}`;
      const resp = await hubspot.fetch(url);
      if (!resp.ok) throw new Error(`Backend error: ${resp.status}`);
      return await resp.json();
    } catch (err) {
      console.error("Failed to fetch program data:", err);
      setError("Could not load program data. Try refreshing.");
      return null;
    }
  };

  // Handle intake selection — re-fetch fees for the selected intake date
  const handleIntakeChange = async (intakeDateValue) => {
    const intake = programData?.intakes?.find((i) => i.intake_date === intakeDateValue) || null;
    setSelectedIntake(intake);

    if (intake && dealProps?.hs_object_id && dealProps?.program_of_study) {
      const data = await fetchProgramData(
        dealProps.hs_object_id,
        dealProps.program_of_study,
        intake.intake_date
      );
      if (data) {
        // Preserve intakes from the original fetch (fee re-fetch shouldn't change intake list)
        setProgramData((prev) => ({
          ...data,
          intakes: prev?.intakes || data.intakes,
        }));
      }
    }
  };

  // Reset and re-fetch
  const handleReset = async () => {
    setResult(null);
    setError(null);
    setSelectedIntake(null);
    setProgramData(null);
    setLoading(true);
    try {
      const props = await fetchCrmObjectProperties([
        "hs_object_id", "dealname", "program_of_study", "hubspot_owner_id",
      ]);
      setDealProps(props);
      if (props.program_of_study) {
        const data = await fetchProgramData(props.hs_object_id, props.program_of_study);
        if (data) setProgramData(data);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Generate contract
  const handleGenerate = async () => {
    if (isGeneratingRef.current) return;
    isGeneratingRef.current = true;
    setGenerating(true);
    setError(null);
    setResult(null);
    try {
      const resp = await hubspot.fetch(`${BACKEND_URL}/generate`, {
        method: "POST",
        headers: { Authorization: `Bearer ${WEBHOOK_SECRET}` },
        body: JSON.stringify({
          dealId: dealProps.hs_object_id,
          intakeDate: selectedIntake?.intake_date || "",
        }),
      });
      if (!resp.ok) {
        const errData = await resp.json();
        throw new Error(errData.error || `HTTP ${resp.status}`);
      }
      const data = await resp.json();
      setResult(data);
      // Auto-open the PandaDoc document in a new tab
      if (data.documentUrl) {
        try {
          actions.openInNewTab(data.documentUrl);
        } catch (_) {
          // Fallback: openInNewTab may not be available in all HubSpot versions
        }
      }
    } catch (err) {
      setError(err.message || "Failed to generate contract");
    } finally {
      isGeneratingRef.current = false;
      setGenerating(false);
    }
  };

  // --- Loading state ---
  if (loading) {
    return (
      <Flex direction="column" align="center" gap="medium">
        <LoadingSpinner />
        <Text>Loading deal data...</Text>
      </Flex>
    );
  }

  // --- No program selected ---
  if (!dealProps?.program_of_study) {
    return (
      <Alert title="Program of Study Required" variant="warning">
        Set the Program of Study on this deal before generating a contract.
      </Alert>
    );
  }

  // --- Generating state ---
  if (generating) {
    return (
      <Flex direction="column" align="center" gap="medium">
        <LoadingSpinner />
        <Text>Generating contract...</Text>
        <Text variant="microcopy">Filling data, matching fees, uploading to PandaDoc...</Text>
      </Flex>
    );
  }

  // --- Success state ---
  if (result && result.documentUrl) {
    return (
      <Flex direction="column" gap="medium">
        <Alert title="Contract Created" variant="success">
          Contract is ready for review and signing.
        </Alert>
        <DescriptionList direction="row">
          <DescriptionListItem label="Student">
            <Text>{result.student || ""}</Text>
          </DescriptionListItem>
          <DescriptionListItem label="Program">
            <Text>{result.program || ""}</Text>
          </DescriptionListItem>
          <DescriptionListItem label="Fee Tier">
            <Tag>{result.feeTier || ""}</Tag>
          </DescriptionListItem>
          <DescriptionListItem label="Total">
            <Text format={{ fontWeight: "bold" }}>{result.total || ""}</Text>
          </DescriptionListItem>
        </DescriptionList>
        <Link href={result.documentUrl}>Open in PandaDoc</Link>
        <Divider />
        <Button variant="secondary" onClick={handleReset}>Regenerate Contract</Button>
      </Flex>
    );
  }

  // --- Main preview state (5 sections) ---
  const contact = programData?.contact || {};
  const program = programData?.program || {};
  const fees = programData?.fees || {};
  const intakes = programData?.intakes || [];
  const contactMissing = programData?.contactMissing || [];
  const dealMissing = programData?.dealMissing || [];
  const feeTier = fees.tier || "Unknown";
  const feeItems = fees.items || [];
  const hasOutline = programData?.hasOutline || false;
  const intakeRequired = intakes.length > 0 && !selectedIntake;

  // Delivery method based on residency
  let deliveryMethod = "";
  if (selectedIntake) {
    deliveryMethod = feeTier === "International"
      ? selectedIntake.international_delivery_method || ""
      : selectedIntake.domestic_delivery_method || "";
  }

  // Build warnings list
  const allWarnings = [];

  // Contact field warnings
  contactMissing.forEach((f) => allWarnings.push({ type: "error", msg: `${f} (Contact)` }));
  dealMissing.forEach((f) => allWarnings.push({ type: "error", msg: `${f} (Deal)` }));

  // Fee warnings
  if (feeItems.length === 0) {
    allWarnings.push({ type: "error", msg: "No fee schedule found for this program" });
  }
  if (feeTier === "Unknown") {
    allWarnings.push({ type: "error", msg: "Fee tier unknown — set Residence Status on the contact" });
  }

  // Outline warning
  if (!hasOutline) {
    allWarnings.push({ type: "warning", msg: "No program outline PDF mapped for this program" });
  }

  // Intake warnings
  if (intakes.length === 0) {
    allWarnings.push({ type: "info", msg: "No open intakes — advisor fills dates in PandaDoc" });
  }

  const errorCount = allWarnings.filter((w) => w.type === "error").length;
  const warningCount = allWarnings.length;

  // Can generate: must have program data loaded, no critical blockers
  const canGenerate =
    programData !== null &&
    !programData.error &&
    !intakeRequired;

  return (
    <Flex direction="column" gap="medium">
      <Text format={{ fontWeight: "bold" }}>Generate Enrollment Contract</Text>

      {/* ---- SECTION 1: Student Info ---- */}
      <Divider />
      <Text format={{ fontWeight: "bold" }}>Student Information</Text>
      <DescriptionList direction="row">
        <DescriptionListItem label="Name">
          <Text>{contact.firstname} {contact.lastname}</Text>
        </DescriptionListItem>
        <DescriptionListItem label="Email">
          <Text>{contact.email || "--"}</Text>
        </DescriptionListItem>
        <DescriptionListItem label="Phone">
          <Text>{contact.phone || "--"}</Text>
        </DescriptionListItem>
      </DescriptionList>
      <DescriptionList direction="row">
        <DescriptionListItem label="Address">
          <Text>
            {[contact.address, contact.city, contact.state, contact.zip]
              .filter(Boolean).join(", ") || "--"}
          </Text>
        </DescriptionListItem>
        <DescriptionListItem label="DOB">
          <Text>{contact.date_of_birth || "--"}</Text>
        </DescriptionListItem>
      </DescriptionList>
      <DescriptionList direction="row">
        <DescriptionListItem label="Residence Status">
          <Text>{contact.residence_status || "--"}</Text>
        </DescriptionListItem>
        <DescriptionListItem label="Fee Tier">
          <Tag variant={feeTier === "Domestic" ? "default" : feeTier === "International" ? "warning" : "error"}>
            {feeTier}
          </Tag>
        </DescriptionListItem>
        <DescriptionListItem label="Gender">
          <Text>{contact.gender || "--"}</Text>
        </DescriptionListItem>
      </DescriptionList>

      {/* ---- SECTION 2: Program & Intake ---- */}
      <Divider />
      <Text format={{ fontWeight: "bold" }}>Program & Intake</Text>
      <DescriptionList direction="row">
        <DescriptionListItem label="Program">
          <Text>{program.programName || dealProps.program_of_study}</Text>
        </DescriptionListItem>
        <DescriptionListItem label="Code">
          <Text>{program.programCode || "--"}</Text>
        </DescriptionListItem>
        <DescriptionListItem label="Credential">
          <Text>{program.credential || "--"}</Text>
        </DescriptionListItem>
      </DescriptionList>

      {intakes.length > 0 ? (
        <Select
          label="Select Intake *"
          options={intakes.map((i) => ({
            label: `${i.intake_date} - ${i.campus || "?"} (${i.spots_available || "?"} spots)`,
            value: i.intake_date,
          }))}
          onChange={handleIntakeChange}
          placeholder="Choose an intake date..."
        />
      ) : (
        <Alert title="No Intakes Available" variant="info">
          No open intakes for this program. Contract will be generated without dates.
        </Alert>
      )}

      {selectedIntake && (
        <>
          <DescriptionList direction="row">
            <DescriptionListItem label="Start Date">
              <Text>{selectedIntake.intake_date}</Text>
            </DescriptionListItem>
            <DescriptionListItem label="End Date">
              <Text>{selectedIntake.end_date || "--"}</Text>
            </DescriptionListItem>
            <DescriptionListItem label="Campus">
              <Text>{selectedIntake.campus || "--"}</Text>
            </DescriptionListItem>
          </DescriptionList>
          <DescriptionList direction="row">
            <DescriptionListItem label="Hours">
              <Text>{selectedIntake.hours || "--"}</Text>
            </DescriptionListItem>
            <DescriptionListItem label="Weeks">
              <Text>{selectedIntake.weeks || "--"}</Text>
            </DescriptionListItem>
            <DescriptionListItem label="Delivery Method">
              <Tag>{deliveryMethod || "--"}</Tag>
            </DescriptionListItem>
          </DescriptionList>
        </>
      )}

      {/* ---- SECTION 3: Fee Breakdown ---- */}
      <Divider />
      <Text format={{ fontWeight: "bold" }}>
        Fee Breakdown ({feeTier})
        {fees.effectiveFrom ? ` — effective ${fees.effectiveFrom}` : ""}
      </Text>

      {feeItems.length > 0 ? (
        <>
          {feeItems.map((item, idx) => (
            <DescriptionList direction="row" key={idx}>
              <DescriptionListItem label={item.isTuition ? `${item.name} *` : item.name}>
                <Text format={item.isTuition ? { fontWeight: "bold" } : {}}>
                  {fmt(item.amount)}
                </Text>
              </DescriptionListItem>
            </DescriptionList>
          ))}
          <DescriptionList direction="row">
            <DescriptionListItem label="TOTAL">
              <Text format={{ fontWeight: "bold" }}>{fees.formattedTotal || fmt(fees.total)}</Text>
            </DescriptionListItem>
          </DescriptionList>
        </>
      ) : (
        <Alert title="No Fees Found" variant="error">
          No fee schedule found for this program. Check the data spreadsheet.
        </Alert>
      )}

      {/* ---- SECTION 4: Warnings (inline, non-blocking) ---- */}
      {allWarnings.length > 0 && (
        <>
          <Divider />
          <Text format={{ fontWeight: "bold" }}>
            Pre-flight Check ({errorCount > 0 ? `${errorCount} issues` : `${warningCount} notices`})
          </Text>
          {allWarnings.filter((w) => w.type === "error").length > 0 && (
            <Alert title="Missing Required Data" variant="error">
              {allWarnings.filter((w) => w.type === "error").map((w) => w.msg).join(", ")}
            </Alert>
          )}
          {allWarnings.filter((w) => w.type === "warning").length > 0 && (
            <Alert title="Warnings" variant="warning">
              {allWarnings.filter((w) => w.type === "warning").map((w) => w.msg).join(", ")}
            </Alert>
          )}
          {allWarnings.filter((w) => w.type === "info").length > 0 && (
            <Alert title="Info" variant="info">
              {allWarnings.filter((w) => w.type === "info").map((w) => w.msg).join(", ")}
            </Alert>
          )}
        </>
      )}

      {/* ---- SECTION 5: Generate ---- */}
      <Divider />
      {error && (
        <Alert title="Error" variant="error">{error}</Alert>
      )}

      <Button
        variant="primary"
        onClick={handleGenerate}
        disabled={!canGenerate}
      >
        {canGenerate
          ? `Generate Contract${warningCount > 0 ? ` (${warningCount} notices)` : ""}`
          : intakeRequired
            ? "Select an intake first"
            : "Loading..."}
      </Button>
    </Flex>
  );
};
