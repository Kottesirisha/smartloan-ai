import { useEffect, useMemo, useState } from "react";
import DashboardStats from "./DashboardStats";
import ApplicationTable from "./ApplicationTable";
import {
  getApplications,
  getApplicationSummary,
  submitOfficerReview,
  getDocumentDownloadUrl,
  getDocumentsZipUrl,
} from "../services/api";

const FILTERS = [
  "All",
  "Eligible",
  "Not Eligible",
  "Manual Review",
  "Document Pending",
  "Approved",
  "Rejected",
];

export default function OfficerDashboard({ user, onLogout }) {
  const [applications, setApplications] = useState([]);
  const [filter, setFilter] = useState("All");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedId, setSelectedId] = useState(null);
  const [summary, setSummary] = useState(null);
  const [notes, setNotes] = useState("");
  const [reviewLoading, setReviewLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);

  const loadApplications = async () => {
    try {
      setError("");
      const response = await getApplications();
      setApplications(response.data.applications || []);
    } catch (err) {
      setApplications([]);
      setError(
        err.response?.data?.detail ||
          err.message ||
          "Unable to load applications. Is the backend running on port 8001?"
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadApplications();
  }, []);

  const filtered = useMemo(() => {
    if (filter === "All") return applications;
    return applications.filter((app) => app.status === filter);
  }, [applications, filter]);

  const openReview = async (applicationId) => {
    setSelectedId(applicationId);
    setDetailLoading(true);
    setNotes("");
    setError("");
    try {
      const response = await getApplicationSummary(applicationId);
      setSummary(response.data);
    } catch {
      setError("Unable to load application summary.");
      setSummary(null);
    } finally {
      setDetailLoading(false);
    }
  };

  const closeReview = () => {
    setSelectedId(null);
    setSummary(null);
    setNotes("");
  };

  const handleDecision = async (decision) => {
    if (!selectedId) return;
    setReviewLoading(true);
    try {
      await submitOfficerReview(
        selectedId,
        decision,
        notes,
        user?.employeeId || "Loan Officer"
      );
      await loadApplications();
      closeReview();
    } catch (err) {
      setError(
        err.response?.data?.detail || "Unable to submit officer decision."
      );
    } finally {
      setReviewLoading(false);
    }
  };

  const application = summary?.application;
  const documents = summary?.documents || [];
  const cross = summary?.cross_validation || {};
  const ai = summary?.ai_summary || {};

  return (
    <main className="dashboard-page">
      <header className="dashboard-header officer-header">
        <div>
          <p className="brand-label">SMARTLOAN AI</p>
          <h1>Loan Officer Review Station</h1>
        </div>
        <button className="outline-button" onClick={onLogout}>
          Logout
        </button>
      </header>

      <div className="dashboard-container">
        <div className="welcome-section">
          <p>Human-in-the-loop workspace</p>
          <h2>Application overview</h2>
          <span>Logged in as {user?.employeeId || "Loan Officer"}</span>
        </div>

        <div className="filter-chips">
          {FILTERS.map((item) => (
            <button
              key={item}
              type="button"
              className={`chip-button ${filter === item ? "active" : ""}`}
              onClick={() => setFilter(item)}
            >
              {item}
            </button>
          ))}
        </div>

        {error && <div className="error-message">{error}</div>}

        {loading ? (
          <div className="panel">Loading applications...</div>
        ) : (
          <>
            <DashboardStats applications={applications} />
            <div className="table-space">
              <ApplicationTable
                applications={filtered}
                onSelect={openReview}
              />
            </div>
          </>
        )}
      </div>

      {selectedId && (
        <div className="modal-backdrop" onClick={closeReview}>
          <div
            className="modal-panel review-workspace"
            onClick={(event) => event.stopPropagation()}
          >
            {detailLoading || !application ? (
              <p>Loading review dossier...</p>
            ) : (
              <>
                <div className="section-heading">
                  <h2>Review workspace</h2>
                  <p>
                    {application.applicant_name} · Status: {application.status}
                  </p>
                </div>

                <div className="review-grid">
                  <div className="dossier-card">
                    <h3>Declared application</h3>
                    <p>Income: ₹{Number(application.annual_income).toLocaleString("en-IN")}</p>
                    <p>Loan: ₹{Number(application.loan_amount).toLocaleString("en-IN")}</p>
                    <p>CIBIL: {application.cibil_score ?? "—"}</p>
                    <p>Term: {application.loan_term ?? "—"} months</p>
                    <p>Education: {application.education ?? "—"}</p>
                    <p>Loan ID: {application.loan_id ?? "—"}</p>
                  </div>

                  <div className="dossier-card">
                    <h3>AI reasoning</h3>
                    <p>{ai.executive_summary || "No AI summary stored yet."}</p>
                    <ul className="flag-list">
                      {(cross.discrepancies || []).map((item, index) => (
                        <li key={index} className={`sev-${item.severity}`}>
                          <span className="sev-badge">{item.severity}</span>
                          {item.message}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                <div className="dossier-card">
                  <h3>Documents</h3>
                  <div className="doc-links">
                    {documents.length === 0 && <p>No documents attached.</p>}
                    {documents.length > 0 && (
                      <a
                        className="primary-button"
                        href={getDocumentsZipUrl(selectedId)}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Download all (ZIP)
                      </a>
                    )}
                    {documents.map((doc) => (
                      <a
                        key={doc.document_id}
                        className="outline-button"
                        href={getDocumentDownloadUrl(doc.document_id)}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {doc.document_type} — {doc.original_filename}
                      </a>
                    ))}
                  </div>
                </div>

                <textarea
                  className="review-notes"
                  placeholder="Officer notes..."
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={3}
                />

                <div className="review-actions">
                  <button
                    type="button"
                    className="primary-button"
                    disabled={reviewLoading}
                    onClick={() => handleDecision("approve")}
                  >
                    Approve Loan
                  </button>
                  <button
                    type="button"
                    className="danger-button"
                    disabled={reviewLoading}
                    onClick={() => handleDecision("reject")}
                  >
                    Reject Application
                  </button>
                  <button
                    type="button"
                    className="outline-button"
                    disabled={reviewLoading}
                    onClick={() => handleDecision("request_reupload")}
                  >
                    Request Re-upload
                  </button>
                  <button
                    type="button"
                    className="outline-button"
                    onClick={closeReview}
                  >
                    Close
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </main>
  );
}
