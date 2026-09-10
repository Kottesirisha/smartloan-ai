export default function RoleSelection({ onSelectRole }) {
  return (
    <main className="role-page">
      <div className="role-container">
        <p className="brand-label">SMARTLOAN AI</p>

        <h1>Intelligent Loan Processing</h1>

        <p className="subtitle">
          Choose your workspace to continue.
        </p>

        <div className="role-grid">
          <button
            className="role-card applicant-card"
            onClick={() => onSelectRole("user")}
          >
            <div className="role-icon">👤</div>
            <h2>Applicant Portal</h2>
            <p>
              Apply for a loan, upload documents, and track your
              application.
            </p>
            <span>Continue as Applicant →</span>
          </button>

          <button
            className="role-card officer-card"
            onClick={() => onSelectRole("officer")}
          >
            <div className="role-icon">🧑‍💼</div>
            <h2>Loan Officer Portal</h2>
            <p>
              Review applications, inspect AI decisions, and manage
              loan risks.
            </p>
            <span>Continue as Loan Officer →</span>
          </button>
        </div>
      </div>
    </main>
  );
}