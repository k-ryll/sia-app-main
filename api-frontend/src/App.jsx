import React, { useState } from "react";
import { BrowserRouter as Router, Routes, Route, Link } from "react-router-dom";
import Home from "./pages/Home";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import "./App.css";

function App() {
  const [token, setToken] = useState(localStorage.getItem("token"));
  const backendUrl = "http://localhost:8000/auth";

  const handleLogout = () => {
    localStorage.removeItem("token");
    setToken(null);
  };

  return (
    <Router>
      <div className="app">
        <header>
          <h1>API Frontend</h1>
          {token && <button onClick={handleLogout}>Logout</button>}
        </header>

        <main>
          <Routes>
            <Route path="/signup" element={<Signup backendUrl={backendUrl} />} />
            <Route
          path="/login"
          element={
            <Login
              backendUrl={backendUrl}
              onLogin={(token) => {
                setToken(token);
                // ✅ no more setPage
              }}
            />
          }
        />
        <Route
          path="/home"
          element={
            token ? (
              <Home backendUrl={backendUrl} token={token} />
            ) : (
              <Login backendUrl={backendUrl} onLogin={setToken} />
            )
          }
        />
          </Routes>
        </main>

        <footer>
          <Link to="/login">Login</Link>
          <Link to="/signup">Signup</Link>
          {token && <Link to="/home">Home</Link>}
        </footer>
      </div>
    </Router>
  );
}

export default App;
