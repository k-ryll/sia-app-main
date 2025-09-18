import { useState } from "react";

export default function Signup({ backendUrl, setPage }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState(null);

  const handleSignup = async (e) => {
    e.preventDefault();
    setMessage(null);

    try {
      const res = await fetch(`${backendUrl}/signup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: email, password }),
      });

      const data = await res.json();
      if (res.ok) {
        setMessage({ type: "success", text: data.message });
        setTimeout(() => setPage("login"), 1500); // redirect after signup
      } else {
        setMessage({ type: "error", text: data.detail || "Signup failed" });
      }
    } catch {
      setMessage({ type: "error", text: "Network error" });
    }
  };

  return (
    <div className="app-viewport">
      <div className="card">
        <h1 className="h1">Create Account</h1>
        <p className="h2">Sign up to get your API tokens</p>

        <form className="form" onSubmit={handleSignup}>
          <input
            className="input"
            type="email"
            placeholder="Email address"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <input
            className="input"
            type="password"
            placeholder="Choose a password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <button className="btn btn-primary" type="submit">
            Sign Up
          </button>
        </form>

        {message && (
          <div className={`message ${message.type}`}>{message.text}</div>
        )}

        <p className="footer">
          Already have an account?{" "}
          <button
            type="button"
            className="btn-link"
            onClick={() => setPage("login")}
          >
            Login
          </button>
        </p>
      </div>
    </div>
  );
}
