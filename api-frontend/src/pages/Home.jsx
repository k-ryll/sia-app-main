import { useState, useEffect } from "react";

export default function Home({ backendUrl, token, onLogout }) {
  const [apiTokens, setApiTokens] = useState([]);
  const [message, setMessage] = useState(null);

  // ✅ Fetch tokens
  const fetchTokens = async () => {
    try {
      const res = await fetch(`${backendUrl}/my-tokens`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (res.ok) {
        setApiTokens(data.api_tokens);
      } else {
        setMessage({ type: "error", text: data.detail || "Error fetching tokens" });
      }
    } catch {
      setMessage({ type: "error", text: "Network error" });
    }
  };

  // ✅ Generate new token
  const generateToken = async () => {
    setMessage(null);
    try {
      const res = await fetch(`${backendUrl}/generate-token`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      });
      const data = await res.json();
      if (res.ok) {
        fetchTokens(); // refresh list
      } else {
        setMessage({ type: "error", text: data.detail || "Error" });
      }
    } catch {
      setMessage({ type: "error", text: "Network error" });
    }
  };

  // ✅ Delete a token
  const deleteToken = async (id) => {
    try {
      const res = await fetch(`${backendUrl}/delete-token/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (res.ok) {
        fetchTokens(); // refresh list
      } else {
        setMessage({ type: "error", text: data.detail || "Error deleting token" });
      }
    } catch {
      setMessage({ type: "error", text: "Network error" });
    }
  };

  useEffect(() => {
    fetchTokens();
  }, []);

  return (
    <div className="app-viewport">
      <div className="card">
        <div className="topnav">
          <button className="btn btn-ghost" onClick={onLogout}>Logout</button>
        </div>

        <h1 className="h1">Dashboard</h1>
        <p className="h2">Generate and manage your API tokens</p>

        <div className="form">
          <button className="btn btn-primary" onClick={generateToken}>
            Generate New Token
          </button>
        </div>

        <h2 className="h2">Your Tokens</h2>
        {apiTokens.length === 0 ? (
          <p>No tokens yet.</p>
        ) : (
          <ul>
            {apiTokens.map((t) => (
              <li key={t.id} className="token-item">
                <textarea
                  className="token-box"
                  value={`${t.token}\nExpires: ${t.expires_at}`}
                  readOnly
                  rows={2}
                />
                <button
                  className="btn btn-danger"
                  onClick={() => deleteToken(t.id)}
                >
                  Delete
                </button>
              </li>
            ))}
          </ul>
        )}

        {message && (
          <div className={`message ${message.type}`}>{message.text}</div>
        )}
      </div>
    </div>
  );
}
