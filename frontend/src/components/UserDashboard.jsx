import { useState } from "react";
import ApplicationForm from "./ApplicationForm";
import DocumentUpload from "./DocumentUpload";
import EligibilityResult from "./EligibilityResult";

export default function UserDashboard({ onLogout }) {
  const [application, setApplication] = useState(null);
  const [eligibilityResult, setEligibilityResult] = useState(null);

  const reset = () => {
    setApplication(null);
    setEligibilityResult(null);
  };

  return (
    <main className="dashboard dashboard-page">
      <header className="dashboard-header">
        <div>
          <p className="brand-label">SMARTLOAN AI</p>
          <h1>Applicant workspace</h1>
        </div>
        {onLogout && (
          <button className="outline-button" onClick={onLogout}>
            Logout
          </button>
        )}
      </header>

      <div className="dashboard-container">
        <div className="section-heading">
          <span>USER DASHBOARD</span>
          <h2>GenAI loan document verification</h2>
          <p>
            Select a Kaggle profile, generate or upload documents, then review
            the AI verification dossier.
          </p>
        </div>

        {!application && <ApplicationForm onCreated={setApplication} />}

        {application && !eligibilityResult && (
          <DocumentUpload
            applicationId={application.application_id}
            onCompleted={setEligibilityResult}
          />
        )}

        {eligibilityResult && (
          <EligibilityResult result={eligibilityResult} onReset={reset} />
        )}
      </div>
    </main>
  );
}
