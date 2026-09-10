import { useState } from "react";

export default function OfficerLogin({ onLogin, onBack }) {
  const [employeeId, setEmployeeId] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = (event) => {
    event.preventDefault();

    onLogin({
      role: "officer",
      employeeId,
    });
  };

  return (
    <main className="login-page officer-login-page">
      <form className="login-card dark-login-card" onSubmit={handleSubmit}>
        <button
          type="button"
          className="back-button dark-back"
          onClick={onBack}
        >
          ← Back
        </button>

        <p className="brand-label">OFFICER WORKSPACE</p>

        <h1>Secure officer login</h1>

        <p className="subtitle">
          Access loan applications and AI risk assessments.
        </p>

        <label>Employee ID</label>
        <input
          value={employeeId}
          onChange={(event) => setEmployeeId(event.target.value)}
          placeholder="LO-1001"
          required
        />

        <label>Password</label>
        <input
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          placeholder="Enter your password"
          required
        />

        <button className="primary-button" type="submit">
          Login as Loan Officer
        </button>

        <small>Authorized personnel only.</small>
      </form>
    </main>
  );
}