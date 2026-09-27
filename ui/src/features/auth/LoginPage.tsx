import { useState, type FormEvent } from "react";
import { Navigate } from "react-router-dom";

import { useAuth } from "../../auth/AuthContext";

export function LoginPage() {
  const { isAuthenticated, isLoading, error, signIn } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  if (isAuthenticated) return <Navigate to="/" replace />;

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    void signIn(username, password);
  }

  return (
    <div className="authscreen">
      <section className="panel" aria-label="Sign in">
        <div className="brandmark">ERP Platform</div>
        <form className="stack" onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="username">Username</label>
            <input className="input" id="username" value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required />
          </div>
          <div className="field">
            <label htmlFor="password">Password</label>
            <input
              className="input"
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </div>
          {error && <span className="formerr">{error}</span>}
          <button className="erp-btn erp-btn--primary" type="submit" disabled={isLoading}>
            {isLoading ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </section>
    </div>
  );
}
