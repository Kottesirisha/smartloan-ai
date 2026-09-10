import { useState } from "react";

export default function UserLogin({ onLogin, onBack }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = (event) => {
    event.preventDefault();

    onLogin({
      role: "user",
      email,
    });
  };

  return (
    <main className="login-page user-login-page">
      <form className="login-card" onSubmit={handleSubmit}>
        <button
          type="button"
          className="back-button"
          onClick={onBack}
        >
          ← Back
        </button>

        <p className="brand-label">APPLICANT PORTAL</p>

        <h1>Welcome back</h1>

        <p className="subtitle">
          Login to manage your loan application.
        </p>

        <label>Email address</label>
        <input
          type="email"
          placeholder="you@example.com"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          required
        />

        <label>Password</label>
        <input
          type="password"
          placeholder="Enter your password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          required
        />

        <button className="primary-button" type="submit">
          Login as Applicant
        </button>

        <small>Demo login is enabled for now.</small>
      </form>
    </main>
  );
}