import { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function Login({ backendUrl, onLogin }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState(null);
  const navigate = useNavigate(); // ✅ navigation hook

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch(`${backendUrl}/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: email, password }),
      });

      const data = await res.json();

      if (!res.ok) throw new Error(data.detail || "Login failed");

      localStorage.setItem("token", data.access_token);

      onLogin(data.access_token); // ✅ updates token in App
      navigate("/home"); // ✅ redirect to /home
    } catch (err) {
      console.error("Login error:", err);
      setMessage({ type: "error", text: err.message || "Network error" });
    }
  };

  return (
    <div className="app-viewport">
      <div className="card">
        <h1 className="h1">Welcome back</h1>
        <p className="h2">Log in to manage your API tokens</p>

        <form className="form" onSubmit={handleLogin}>
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
            placeholder="Your password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <button className="btn btn-primary" type="submit">
            Login
          </button>
        </form>

        {message && (
          <div className={`message ${message.type}`}>{message.text}</div>
        )}

        <p className="footer">
          Don’t have an account?{" "}
          <button
            type="button"
            className="btn-link"
            onClick={() => navigate("/signup")}
          >
            Sign up
          </button>
        </p>
      </div>
    </div>
  );
}
