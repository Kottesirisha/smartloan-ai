import VerificationTimeline from "./VerificationTimeline";

function formatMoney(value) {
  if (value == null || value === "") return "—";
  return `₹${Number(value).toLocaleString("en-IN")}`;
}

export default function EligibilityResult({ result, onReset }) {
  if (!result) {
    return (
      <section className="panel empty-panel">
        <span>STEP 3</span>
        <h2>AI Review & Verification Dossier</h2>
        <p>Complete document processing to view the dossier.</p>
      </section>
    );
  }

  const eligibility = result.eligibility_result || result;
  const status =
    result.status ||
    eligibility.status ||
    (result.eligible ? "Eligible" : "Manual Review");
  const ai = result.ai_summary || eligibility.ai_summary || {};
  const cross = result.cross_validation || eligibility.cross_validation || {};
  const discrepancies = cross.discrepancies || ai.discrepancies || [];
  const missing = cross.missing_documents || [];
  const ml = ai.ml_risk_analysis || {};
  const scorecard = ai.document_scorecard || {};
  const extracted = cross.extracted_by_type || {};
  const incomeComparison = cross.income_comparison || [];

  const statusLower = String(status).toLowerCase();
  const isApproved =
    result.eligible === true ||
    statusLower === "eligible" ||
    statusLower === "approved";
  const isRejected =
    statusLower === "rejected" || statusLower === "not eligible";

  const decisionClass = isApproved
    ? "eligible-panel"
    : isRejected
      ? "rejected-panel"
      : "review-panel";
  const badgeClass = isApproved ? "eligible" : isRejected ? "rejected" : "review";
  const badgeText = isApproved
    ? "✓ Eligible / Approve"
    : isRejected
      ? "✕ Not Eligible"
      : "⚠ Manual Review";

  return (
    <section className={`panel result-panel dossier-panel ${decisionClass}`}>
      <div className="section-heading">
        <span>STEP 3</span>
        <h2>AI Review & Verification Dossier</h2>
        <p>Audit-ready GenAI loan processing summary.</p>
      </div>

      <VerificationTimeline currentStage={8} />

      <div className={`decision-badge ${badgeClass}`}>{badgeText}</div>

      <div className="dossier-grid">
        <div className="dossier-card">
          <h3>Verification summary</h3>
          <p>
            <strong>Status:</strong> {status}
          </p>
          <p>
            <strong>Risk:</strong> {result.risk_level || eligibility.risk_level}
          </p>
          <p>
            <strong>Verification score:</strong>{" "}
            {result.verification_score ??
              eligibility.verification_score ??
              scorecard.verification_score ??
              "—"}
            /100
          </p>
          <p>
            <strong>Reason:</strong> {result.reason || eligibility.reason}
          </p>
          {ai.executive_summary && (
            <p className="executive-summary">{ai.executive_summary}</p>
          )}
        </div>

        <div className="dossier-card">
          <h3>Kaggle ML risk assessment</h3>
          <p>
            <strong>Prediction:</strong>{" "}
            {ml.prediction || eligibility.model_prediction || "—"}
          </p>
          <p>
            <strong>Model confidence:</strong>{" "}
            {ml.confidence ?? eligibility.confidence ?? "—"}%
          </p>
          <p>
            <strong>Approval probability:</strong>{" "}
            {ml.approval_probability ??
              eligibility.approval_probability ??
              "—"}
            %
          </p>
          <p>
            <strong>CIBIL:</strong> {ml.cibil_score ?? "—"}
          </p>
          <p>
            <strong>Dataset label:</strong> {ml.dataset_status ?? "—"}
          </p>
        </div>
      </div>

      {missing.length > 0 && (
        <div className="alert-banner missing-docs">
          <strong>Missing documents:</strong> {missing.join(", ")}
        </div>
      )}

      <div className="dossier-card">
        <h3>Cross-document inconsistencies & red flags</h3>
        {discrepancies.length === 0 ? (
          <p className="ok-text">No discrepancies detected.</p>
        ) : (
          <ul className="flag-list">
            {discrepancies.map((item, index) => (
              <li key={`${item.code}-${index}`} className={`sev-${item.severity}`}>
                <span className="sev-badge">{item.severity}</span>
                {item.message}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="dossier-card">
        <h3>Declared vs extracted income</h3>
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Source</th>
                <th>Value</th>
              </tr>
            </thead>
            <tbody>
              {incomeComparison.length === 0 ? (
                <tr>
                  <td colSpan="2">No income points extracted.</td>
                </tr>
              ) : (
                incomeComparison.map((row) => (
                  <tr key={row.source}>
                    <td>{row.source}</td>
                    <td>{formatMoney(row.value)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        {cross.income_variance_pct != null && (
          <p>
            Income variance: <strong>{cross.income_variance_pct}%</strong>
          </p>
        )}
      </div>

      <div className="dossier-card">
        <h3>Extracted fields by document</h3>
        <div className="extracted-grid">
          {Object.keys(extracted).length === 0 && (
            <p>No structured fields available.</p>
          )}
          {Object.entries(extracted).map(([docType, fields]) => (
            <div key={docType} className="extracted-block">
              <h4>{docType}</h4>
              <ul>
                {Object.entries(fields || {}).map(([key, value]) => (
                  <li key={key}>
                    <span>{key}</span>
                    <strong>
                      {typeof value === "number" && key.toLowerCase().includes("salary")
                        ? formatMoney(value)
                        : typeof value === "number" &&
                            (key.toLowerCase().includes("income") ||
                              key.toLowerCase().includes("balance") ||
                              key.toLowerCase().includes("pay"))
                          ? formatMoney(value)
                          : String(value ?? "—")}
                    </strong>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>

      <div className="dossier-card">
        <h3>Recommended officer actions</h3>
        <ol className="next-steps">
          {(ai.recommended_actions || ["Proceed with standard review."]).map(
            (step) => (
              <li key={step}>{step}</li>
            )
          )}
        </ol>
        {ai.audit_trail && (
          <>
            <h4>Audit trail</h4>
            <ul className="audit-list">
              {ai.audit_trail.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </>
        )}
      </div>

      {onReset && (
        <button type="button" className="outline-button" onClick={onReset}>
          Start new application
        </button>
      )}
    </section>
  );
}
